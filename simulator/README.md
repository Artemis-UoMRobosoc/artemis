# Artemis Tarot 680 Simulator

The simulator is a local software sandbox for the Tarot Iron Man 680 hexacopter. It reads RC telemetry from a SpeedyBee F405 V5 running Betaflight, or accepts virtual and recorded channel input, then runs a six-motor flight-dynamics model and displays the result in a Three.js view.

The simulated controller and all six motor outputs exist only in this application. The serial bridge is read-only: it sends Betaflight `MSP_RC` (105) and `MSP_STATUS_EX` (150) requests. It does not send arming, motor, calibration, or configuration commands, and it does not change the flight-controller firmware or settings. This is not Betaflight SITL and is not evidence of flight readiness.

## Requirements

- macOS or Linux (commands below use a POSIX shell)
- Python 3.12
- Node.js and npm
- For live RC input: a SpeedyBee F405 V5 connected over USB, Betaflight running, and the RadioMaster Pocket bound to the ELRS RP1 receiver

## Install

From the repository root, create a Python environment and install the backend dependencies:

```bash
cd simulator
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Install the frontend dependencies in a second terminal:

```bash
cd simulator/frontend
npm ci
```

## Run

Start the backend from the `simulator` directory with the Python environment active:

```bash
cd simulator
source .venv/bin/activate
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000
```

Start the frontend from `simulator/frontend` in another terminal:

```bash
cd simulator/frontend
npm run dev
```

Open the local URL printed by Vite, normally `http://127.0.0.1:5173/`. The backend API is at `http://127.0.0.1:8000/`; its live state WebSocket is at `ws://127.0.0.1:8000/ws/state`.

## Use Virtual RC

The page starts in Virtual RC mode. Its channel sliders let you test input without a connected flight controller. Select `ANGLE / SELF LEVEL` to test angle targets, then move the `ROLL`, `PITCH`, `YAW`, or `THROTTLE` slider. The simulator clock advances only while `START` is active. Use `PAUSE` to stop it and `RESET` to clear the simulated attitude and outputs.

The default channel map matches the current RadioMaster Pocket setup:

| Channel | Control | Stick axis |
| --- | --- | --- |
| CH1 | Roll | Right stick left / right |
| CH2 | Pitch | Right stick back / forward |
| CH3 | Yaw | Left stick left / right |
| CH4 | Throttle | Left stick down / up |

The default channel assignments and physics settings can be changed in the page. Those changes apply to the simulator only and are not saved to Betaflight. `ANGLE / SELF LEVEL` is also simulator-only: it requests roll and pitch tilt targets, while yaw remains rate-controlled. It does not enable Betaflight ANGLE mode or configure an AUX switch.

## Use Live RC

The live path is RadioMaster Pocket -> ELRS RP1 -> F405 -> USB -> simulator. Betaflight Configurator must release the serial port before the simulator connects.

1. Keep the flight controller disarmed.
2. Close Betaflight Configurator's connection to the F405.
3. Connect the F405 to the computer over USB.
4. Select its USB serial port in the simulator and press `CONNECT`.
5. Select `LIVE F405` if the page has not switched to it automatically.
6. Check the channel monitor for the expected stick response. Press `START` to run the simulation.

The bridge polls RC channels at 50 Hz and status at 5 Hz. An active receiver failsafe, a short RC packet, or a live-sample timeout clears simulated motor outputs and pauses the simulation. Restore the receiver signal and press `START` to resume. The bridge does not read raw ELRS radio packets; it reads the channels Betaflight has decoded.

## Record And Replay

Press `RECORD` to capture channel values and press `STOP` to download a CSV file. Load a recording with `LOAD CSV`, select `REPLAY`, and press `START` to play the channel samples against simulation time. The CSV contains `time_s` and `ch1` through `ch16` columns, so the same input sequence can be replayed with the same simulator settings.

## Model And Limits

The Python backend runs a fixed 500 Hz six-degree-of-freedom model and broadcasts state to the browser at about 60 Hz. The view shows attitude, channel values, and six independent virtual motor outputs. The controller is a simulator-local rate PID with an optional angle outer loop; it is not Betaflight's firmware controller.

Airframe mass, inertia, motor thrust, motor response, and yaw authority are initial estimates. The model has not been calibrated against measured motors, ESCs, propellers, or the assembled airframe. Use it for software experiments and input-direction checks only, not to predict real flight performance or to authorize a flight.

## Verify

Run the backend tests and frontend production build from the repository root:

```bash
python3 -m pytest -q simulator/backend/tests
npm --prefix simulator/frontend run build
```
