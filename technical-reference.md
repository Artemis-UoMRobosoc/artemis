# Artemis — Technical Reference

Updated: 11 October 2026.

This document records existing hardware, identification evidence, manuals, wiring references and bench procedures. Purchase decisions and deliveries belong in the [Weekly Plan](weekly-plan.md). A component being present does not mean that it has passed testing.

## Existing hardware

| Item | Identification | Evidence and remaining work |
| --- | --- | --- |
| Electronic speed controller (ESC) | AIKON Electronics **AK32 35A**, labelled **2–6S**; individual ESC | Label reported on 7 October. Confirm that all installed units match and read their firmware. |
| Motor | Labelled **4006 / 620KV / 4S** | Brand and full part number unconfirmed. Speed control has been reported for the tested setup. |
| Power Distribution Board (PDB) | Existing power-distribution and signal-routing board | **Tarot TL6X002 is a candidate identity**, not a confirmed part number. Record its markings, connections and ratings. |
| Flight controller | **SpeedyBee F405 V5** | Identity confirmed over USB; Betaflight 4.5.2, QUADX and DShot600 recorded. USB sensor readback and a configuration/resource backup are available. |
| ESP32 experiment board | **CrowPanel 2.13-inch ESP32-S3 e-paper display** | Ownership confirmed; physical revision, recovery backup and SDR firmware compatibility remain unverified. |
| SDR receiver | **Nooelec NESDR SMArt v5** | Exact product confirmed; USB identification and recording tests have not been performed. |

The battery has been dispatched, but its specification and receipt are not yet confirmed. It is therefore tracked under deliveries rather than verified inventory. No ELRS transmitter, RF module or receiver is currently owned; recommended radio equipment is listed in the Weekly Plan.

## ESC — AIKON AK32 35A

The reported label is **AIKON Electronics / AK32 / 35A / 2–6S**. The matching manufacturer listing describes an individual ESC, distinct from the similarly named four-in-one products.

| Field | Manufacturer specification or remaining gap |
| --- | --- |
| Input | 2–6S LiPo |
| Continuous / burst current | 35 A / 45 A; captured specification does not establish burst duration or test conditions |
| Dimensions / weight including wires | 18 × 30 mm / 12 g; specification values, not measurements of our unit |
| Listed firmware target | `Aikon_AK32_35A_Multi`; installed target/version require readback |
| Firmware and signalling | BLHeli_32, DShot commands and telemetry listed; record the actual successful test configuration |
| BEC and complete pinout | Not established in the captured specification; identify control-wire functions on the actual unit |

References:

- [AIKON manufacturer listing](https://aikon-electronics.com/index.php?id=12), checked in the project records on 7 October 2026. A separate hardware datasheet PDF and complete pin diagram have not been located.
- [BLHeli_32 firmware manual](https://github.com/bitdump/BLHeli/blob/master/BLHeli_32%20ARM/BLHeli_32%20manual%20ARM%20Rev32.x.pdf). This covers protocols, settings and startup tones; it is not an AIKON hardware datasheet.

## Motor — 4006 620KV

The installed motor was reported as **4006, KV620, 4S**. Do not infer the brand from those markings alone. Tarot **TL68P02** is a comparison reference, not a confirmed identity for our motors.

- [Tarot 4006/620KV TL68P02 comparison listing](https://www.flyingtech.co.uk/product/tarot-4006-620kv-4s-multirotor-brushless-disc-motor-tl68p02/). Its combination and performance figures are not measurements of our aircraft.
- [Tarot frame assembly reference](https://www.mhm-modellbau.de/downloads/680PRO.pdf). The document is headed *IRON MAN 680*; the downloaded filename alone does not establish the revision of our frame.

**Progress reported on 10 October:** motor speed can be controlled. The exact motor/ESC pair, output channel, protocol, command range, supply conditions and stopping result still need to be recorded. This does not establish that all six motors have passed testing or that the aircraft is ready to fly.

## Power Distribution Board

The old aircraft has a board carrying power distribution and signal routing. **TL6X002 remains a tentative identification.** Distinguish this separate board from the frame's PCB centre plate and the individual ESCs.

The [TL6X002 comparison reference](https://www.flyingtech.co.uk/product/tarot-hexacopter-power-distribution-board-signal-hub-tl6x002/) helps identify the category of board. It is not a verified map of our wiring.

Record:

- Board markings and clear views of both sides and every connector.
- Main input/output polarity and continuity with power disconnected.
- Each signal path from the flight controller through the PDB to its ESC.
- Ratings and the function of any auxiliary outputs, supported by documentation or suitable measurements.

Current rating and regulated-output voltages are not yet established. Do not infer a 5 V or 12 V output from a connector shape, wire colour or the candidate product name.

## Flight controller — SpeedyBee F405 V5

The board reports **SPEEDYBEEF405V5** over USB. The recorded firmware is **Betaflight 4.5.2**, configured as **QUADX**, with **DShot600** selected. USB communication, sensor readback and a configuration/resource backup have been obtained.

ArduCopter and a six-motor output arrangement remain proposed development steps. The existing four-motor configuration is not evidence of a completed six-output setup. A configuration backup is also distinct from a full firmware image.

References:

- [SpeedyBee F405 V5 manufacturer information](https://www.speedybee.com/speedybee-f405-v5-55a-stack/).
- [Manufacturer manual portal](https://docs.speedybee.cn/en/fpv/fc-flight-controller/f405v5-flight-control/f405_v5-_ox32-55a_user-manual.html).
- [Manufacturer manual, Chinese PDF](https://spcdn.speedybee.cn/cdn/196552442110808064.pdf).

### Peripheral pin map

The following is the existing manufacturer pin-map reference, reproduced unchanged from the saved manual extract. Its original labels are in Chinese; board labels such as `GND`, `T6`, `R6`, `S5` and `S6` remain visible. It shows manufacturer example peripherals, not the list of devices installed on Artemis or a validated six-motor configuration.

![SpeedyBee F405 V5 manufacturer peripheral pin map](assets/f405-v5-pinout.png)

For our aircraft, a complete wiring record must additionally identify each actual ESC, motor position, signal output, ground connection and direction. Verify signal routing through the old PDB before treating it as a transparent extension of a flight-controller output.

## Bench procedures

These procedures support repeatable tests; they are not completed test results. Remove all propellers for motor bench tests, secure the hardware, and disconnect power before changing wiring.

### ESC signal and motor checks

1. **Identify the inputs.** Distinguish main power, the three motor-phase wires and thin control wires. Establish Signal, reference GND, any BEC output and any required optocoupler supply from the actual device documentation. Do not assign an unidentified third wire to 5 V. Resolve the power path before combining a tester supply, ESC BECs or a USB-powered flight controller.
2. **Observe the unloaded signal.** Measure the control input relative to signal ground. Record high/low levels, pulse widths and repetition interval. Keep a logic analyser within its input-voltage rating. Conventional PWM often uses roughly 1000–2000 microsecond pulses, with device-dependent stopping points and refresh rates. DShot is a digital protocol: a multimeter's average voltage does not verify a valid DShot command.
3. **Establish a compatible reference.** Use a known-compatible tester/receiver or a flight-controller output already verified without motor power. Prepare the stop command and use a supply appropriate for the identified ESC and test. Run a brief low-command test with the motor secured and propeller removed. Do not perform full-throttle power-up calibration on an unidentified ESC.
4. **Trace the output.** Compare the waveform at the F405 output, PDB entry and ESC connector. Save settings before changing protocols, and verify the new output with motor power isolated. A single-ESC test does not require migrating the entire flight-control firmware.
5. **Isolate faults.** Check voltage at the ESC, startup voltage drop, signal, reference ground, protocol and stop endpoint. Disconnect power before exchanging one component in a known-compatible combination. Record whether the fault follows the ESC or motor. Unloaded rotation does not demonstrate loaded reliability, thrust or flight readiness.

Before using an earth-referenced oscilloscope, establish the relationship between signal ground, computer USB, supply and protective earth. Never clip its ordinary ground lead to a motor phase or positive supply, or defeat protective earth. Verify an unclear setup before measuring. Check that the power source can handle startup transients and braking energy rather than repeatedly increasing a current limit. Record current as unmeasured if no suitable instrument is available.

References: [ArduPilot ESC signal protocols](https://ardupilot.org/copter/docs/common-brushless-escs.html) and [Hobbywing tester compatibility](https://support.hobbywingdirect.com/hc/en-us/articles/19157002618131-Using-a-Servo-Tester-to-operate-your-Electronic-Speed-Control). These describe methods and compatibility considerations, not the condition of our equipment.

### Connection checks

| Connection | Check | What success establishes |
| --- | --- | --- |
| USB → F405 | Read board/firmware identity, attitude and Ports/Receiver settings; save evidence | Computer-to-flight-controller communication |
| Phone → F405 Bluetooth | Under the current Betaflight setup, read settings through SpeedyBee App and record failures | Configuration access; it does not establish a flight radio link or Bluetooth support after a firmware migration |
| Radio → receiver → F405 | Identify exact models, protocol, supply and UART; with motor power isolated, check channels and response to receiver loss | Control data and loss detection at the flight controller; a receiver LED alone is insufficient |

For a serial ELRS receiver using CRSF, verify receiver **TX → flight-controller RX**, receiver **RX ← flight-controller TX**, ground and supply against the exact board diagrams. UART6 is a proposed connection and must be checked against current port assignments. USB power does not imply every 5 V pad is powered; a USB-powered 4V5 output must still suit the receiver. See the [ExpressLRS wiring guide](https://www.expresslrs.org/quick-start/receivers/wiring-up/).

## Radio experiments

The CrowPanel ESP32-S3 internal-radio SDR investigation is separate from bringing up a supported ELRS control link. Source review and offline modelling have been carried out, but capture-firmware adaptation, physical capture and ELRS interoperability have not been demonstrated on our board.

The owned NESDR SMArt v5 provides a separate receive-only SDR experiment. Its manufacturer's specified tuning range includes 868/915 MHz, but not 2.4 GHz; it cannot substitute for a 2.4 GHz ELRS transmitter. See the [NESDR SMArt v5 datasheet](https://www.nooelec.com/store/downloads/dl/file/id/111/product/246/nesdr_smart_rtl_sdr_v5_datasheet_revision_1.pdf).

The immediate preparation is to identify the physical boards, establish recoverable firmware/software setups and verify capture/recording. Known signal sources are needed before claiming ELRS reception. Finding a waveform, recovering bytes, maintaining a bidirectional radio link and controlling the aircraft are separate milestones.

## Recording results

Use one row per identified unit and test:

| Date / evidence | Unit ID and exact label | Wiring / channel | Firmware / protocol | Supply | Command / test | Observed result |
| --- | --- | --- | --- | --- | --- | --- |
| To record | To record | To record | To record | To record | To record | To record |

Keep a test plan separate from its result, and identify the source of each claim: label, manufacturer specification, direct measurement or reported observation. Add received hardware here after checking its identity; update ordering and delivery status in the Weekly Plan.
