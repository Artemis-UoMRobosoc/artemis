# Betaflight hexacopter setup — to-do and suggestions

Austin · 20 October 2026

How to move the SpeedyBee F405 V5 from the current **Betaflight 4.5.2 / QUADX / DShot600** setup to six motors. The commands and tables come from the Betaflight 2026.6.2 source and the official `SPEEDYBEEF405V5` board definition. **They have not been tested on our board yet.** Remove all propellers for every motor test, and back up with `diff all` before changing anything.

## To do now

1. **Back up.** In the CLI, run `diff all` and save the output.
2. **Number the arms.** Look from above with the nose up (the nose sits between two arms). Label each arm with its HEX6X motor number from the table below.
3. **Trace the signals.** For each ESC, follow its signal and signal-ground wires through the PDB to the flight controller. Record which pad each one reaches. Check that every ESC signal ground is connected to FC ground.
4. **Move motors 5 and 6 onto S5/S6.** Paste:

   ```
   resource SERVO 1 NONE
   resource SERVO 2 NONE
   resource MOTOR 5 C09
   resource MOTOR 6 C08
   dma pin C09 0
   dma pin C08 0
   mixer HEX6X
   save
   ```

5. **Check after the reboot.** Run `resource show`, `timer show`, `dma show` and `status`. Expected:
   - MOTOR 5 = C09 and MOTOR 6 = C08, both on **TIM8**.
   - DMA2 Stream 7 → MOTOR 5, DMA2 Stream 2 → MOTOR 6, DMA2 Stream 4 → ADC.
   - No two devices sharing a stream, and no errors in `status`.

   Save these outputs. If anything differs, see [If S5/S6 do not work](#if-s5s6-do-not-work).
6. **Check positions.** With props off and a battery connected, spin each motor from the Configurator Motors tab. Confirm that the right arm turns.
7. **Check directions** against the table, and correct any reversed motor in BLHeli_32 Suite.
8. **Read the ESCs.** Through BLHeli_32 passthrough, record the firmware version and settings of all six. Make them match. Count the motor magnets and set `motor_poles`.
9. **Check orientation.** On the Configurator Setup tab, tilt the aircraft nose-down and right. The 3D model should follow; if not, fix the board alignment.
10. **Record results.** Put the outputs and observations in the technical reference.

### HEX6X motor map

From the Betaflight `mixerHex6X` table, viewed from above with `yaw_motors_reversed = OFF`:

| Motor | Position | Direction | Pad if wired directly |
| --- | --- | --- | --- |
| 1 | Rear right | Counter-clockwise | M1 (PB1) |
| 2 | Front right | Counter-clockwise | M2 (PB0) |
| 3 | Rear left | Clockwise | M3 (PB10) |
| 4 | Front left | Clockwise | M4 (PB11) |
| 5 | Right (middle) | Clockwise | S5 (PC9) |
| 6 | Left (middle) | Counter-clockwise | S6 (PC8) |

```
        nose
     4       2
   (CW)    (CCW)
6               5
(CCW)          (CW)
     3       1
   (CW)    (CCW)
```

If the propellers are mounted the other way round, set `yaw_motors_reversed = ON` and reverse **all six**, never only some of them.

## Why S5/S6 need extra steps

In the board definition, M1–M4 are motor outputs with DMA already assigned (on DMA1). S5 and S6 are **servo outputs with no DMA**, so they cannot send DShot until they are reassigned. Electrically they are the same 3.3 V outputs as M1–M4. Once configured, Betaflight treats motors 5 and 6 exactly like 1–4.

| Pad | Pin | Timer | DMA options |
| --- | --- | --- | --- |
| S5 | PC9 | TIM8 CH4 | 0 = DMA2 Stream 7 (only option) |
| S6 | PC8 | TIM8 CH3 | 0 = DMA2 Stream 2; 1 = DMA2 Stream 4 |

- ADC1 already uses DMA2 Stream 4, so S6 must use option 0.
- PC8 and PC9 can also run on TIM3, but TIM3 drives M1/M2. Keep them on TIM8, which is the default.
- Gyro SPI1, UART1 and UART6 can also take DMA2 Streams 2 and 7. `dma show` tells you which ones actually do.
- S5 = PC9 and S6 = PC8 follow from the board definition. Confirm with `resource show` and the manufacturer pin map before wiring.

## Suggestions

### Matching outputs to arms

Pick **one** of these, so the final mapping stays traceable:

1. **Rewire** each ESC signal to the pad in the motor map. Nothing else changes in Betaflight.
2. **Keep the wiring** and use Configurator **Motors → Reorder motors**. The result is stored in `motor_output_reordering`, so `diff all` keeps it.
3. **Swap pins** with `resource MOTOR n <pin>`. Free both pins with `NONE` first, then re-check `dma show`.

### If S5/S6 do not work

Try these in order, and record each result:

1. **Hardware.** Is the wire on the right pad? Check continuity through the PDB and the common ground. Look for a DShot waveform at the pad. Move the motor 5 ESC to M1: does the fault follow the ESC/motor, or the output?
2. **DMA conflict.**
   - If a UART transmit holds DMA2 Stream 7: `dma UART_TX 1 NONE` or `dma UART_TX 6 NONE`.
   - If DMA2 Stream 2 is taken: move the other user (for example `dma SPI_SDI 1 0`), or use `dma pin C08 1` together with `dma ADC 1 0`.

   Re-check `dma show` after every change. Moving one device can create a new clash.
3. **Bitbang DShot.** `dma pin C09 NONE`, `dma pin C08 NONE`, `set dshot_bitbang = ON`, `save`. Bitbang does not need per-pin DMA and still supports bidirectional DShot.
4. **Another pad.** The LED strip pad PA8 (TIM1 CH1) has DMA: `resource LED_STRIP 1 NONE`, then `resource MOTOR 5 A08`.
5. **Slower or analogue protocol.** Try DShot300 first. An analogue protocol such as Oneshot125 needs no DMA, but loses bidirectional DShot and the RPM filter, and needs ESC range calibration with props off.
6. **Different platform.** ArduPilot, or a flight controller with 6–8 native motor outputs. I have not yet checked whether ArduPilot supports this exact board.

Enable bidirectional DShot (`set dshot_bidir = ON`) only after all six motors run on plain DShot, then re-check `dma show` and the RPM readout.

### Tuning and safety for a 680-class hex

- Betaflight defaults are for 5-inch quads. Start with much lower P and D, low rates and Angle mode.
- Lower `dyn_notch_min_hz` and `rpm_filter_min_hz` only after looking at a Blackbox noise spectrum. Large props spin slowly, so the noise sits lower.
- Raise `dshot_idle_value` only if motors stutter at idle.
- A Blackbox rate of 1–2 kHz is enough.
- Calibrate the voltage reading. Set the current meter to none if no sensor is wired.
- With props off, test failsafe by switching the transmitter off. A large aircraft should land or drop rather than keep flying.
- Altitude Hold and GPS Position Hold (Betaflight 2025.12 and later) need a GPS, and preferably a magnetometer. We own neither.

### Software we may write later

Getting the aircraft flying needs configuration, not code. Code is worth writing for:

- Configuration history: `diff all` exports kept in git.
- Blackbox analysis in Python: step response and tracking error, for comparing controllers.
- A Raspberry Pi to F405 link over MSP on UART1: read attitude and IMU data, and later send commands with MSP Override. The transmitter must always be able to take control back.
- Simulation with Betaflight SITL or a Python model, as a controller baseline.
- Our own controllers. Run them as an outer loop on the Pi first. Changing Betaflight's inner loop means modifying and building the C firmware.

## Open issues

| Issue | Status | Next action |
| --- | --- | --- |
| Motors 5/6 unassigned in the current setup | Recorded | Apply step 4 and check step 5 |
| S5/S6 DShot output | Untested; DMA clash possible | `dma show`, then the fallback list |
| Which ESC/arm goes to which output | Not recorded | Steps 2–3 |
| Motor directions and propeller orientation | Not recorded | Step 7 |
| ESC firmware and settings on all six | Not read | Step 8 |
| Common signal ground for every ESC | Not verified | Step 3 |
| Radio link | No receiver owned | CRSF on UART6 once the receiver arrives |
| Tuning for the large frame | Not started | First hover in Angle mode, with Blackbox logging |

## Sources

- [Betaflight `SPEEDYBEEF405V5` board definition](https://github.com/betaflight/config/blob/master/configs/SPBE/SPEEDYBEEF405V5/config.h)
- [Betaflight 2026.6.2 STM32 DMA map](https://github.com/betaflight/betaflight/blob/2026.6.2/src/platform/STM32/dma_reqmap_mcu.c)
- [Betaflight 2026.6.2 STM32F4 timer table](https://github.com/betaflight/betaflight/blob/2026.6.2/src/platform/STM32/timer_stm32f4xx.c)
- [Betaflight 2026.6.2 mixer tables](https://github.com/betaflight/betaflight/blob/2026.6.2/src/main/flight/mixer_init.c)
- [Betaflight 2025.12 release notes](https://betaflight.com/docs/wiki/release/Betaflight-2025-12-Release-Notes)
