"""FastAPI application for the Artemis simulator."""

from __future__ import annotations

import asyncio
import csv
import io
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from .replay import ReplaySample, parse_csv, samples_to_csv
from .serial_bridge import RadioSample, SerialBridge
from .simulation import TarotHexacopter


class VirtualRcRequest(BaseModel):
    channels: list[int] = Field(min_length=4, max_length=16)


class ConnectionRequest(BaseModel):
    port: str
    baudrate: int = Field(default=115200, ge=9600, le=1000000)


class ModeRequest(BaseModel):
    mode: str


class ControlModeRequest(BaseModel):
    mode: str


class PidRequest(BaseModel):
    axis: str
    kp: float = Field(ge=0, le=10)
    ki: float = Field(ge=0, le=10)
    kd: float = Field(ge=0, le=10)


class ChannelMappingRequest(BaseModel):
    roll: int = Field(ge=0, le=15)
    pitch: int = Field(ge=0, le=15)
    throttle: int = Field(ge=0, le=15)
    yaw: int = Field(ge=0, le=15)


class SimulationConfigRequest(BaseModel):
    mass_kg: float = Field(gt=0.1, le=50)
    arm_radius_m: float = Field(gt=0.05, le=2)
    max_motor_thrust_n: float = Field(gt=0.1, le=100)
    motor_time_constant_s: float = Field(gt=0.001, le=2)
    yaw_mix_gain: float = Field(default=1.0, gt=0, le=5)
    linear_drag: float = Field(ge=0, le=5)
    angular_drag: float = Field(ge=0, le=5)
    max_angle_deg: float | None = Field(default=None, gt=0, le=80)
    angle_response: float | None = Field(default=None, gt=0, le=20)


@dataclass
class AppState:
    model: TarotHexacopter = field(default_factory=TarotHexacopter)
    bridge: SerialBridge = field(default_factory=SerialBridge)
    input_mode: str = "virtual"
    running: bool = False
    recording: bool = False
    recording_samples: list[ReplaySample] = field(default_factory=list)
    replay_samples: list[ReplaySample] = field(default_factory=list)
    replay_started_at: float | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    loop_task: asyncio.Task | None = None
    subscribers: set[WebSocket] = field(default_factory=set)

    def on_radio_sample(self, sample: RadioSample) -> None:
        with self.lock:
            if self.input_mode == "live":
                # MSP_RC is the authoritative channel sample. A receiver
                # failsafe mode bit invalidates the sample immediately.
                receiver_failsafe = sample.status.failsafe if sample.status else False
                valid = len(sample.channels) >= 4 and not receiver_failsafe
                self.model.set_rc(sample.channels, valid=valid, age_s=0.0)
                if not valid:
                    self.running = False
                if self.recording:
                    self.recording_samples.append(ReplaySample(self.model.state.sim_time, sample.channels))


state = AppState()
state.bridge.on_sample = state.on_radio_sample


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    state.loop_task = asyncio.create_task(simulation_loop())
    try:
        yield
    finally:
        state.bridge.disconnect()
        if state.loop_task:
            state.loop_task.cancel()
            try:
                await state.loop_task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Artemis Tarot 680 Simulator", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def snapshot() -> dict[str, Any]:
    with state.lock:
        data = state.model.snapshot()
        running = state.running
        input_mode = state.input_mode
        recording = state.recording
        replay_loaded = bool(state.replay_samples)
    data.update(
        {
            "running": running,
            "input_mode": input_mode,
            "serial": state.bridge.snapshot(),
            "recording": recording,
            "replay_loaded": replay_loaded,
        }
    )
    return data


def apply_replay_input() -> None:
    if not state.replay_samples or state.replay_started_at is None:
        return
    elapsed = state.model.state.sim_time - state.replay_started_at
    selected = state.replay_samples[0]
    for sample in state.replay_samples:
        if sample.time_s <= elapsed:
            selected = sample
        else:
            break
    state.model.set_rc(selected.channels, valid=True, age_s=0.0)


async def simulation_loop() -> None:
    tick = 1 / 500
    next_tick = time.perf_counter()
    broadcast_at = 0.0
    while True:
        now = time.perf_counter()
        if now < next_tick:
            await asyncio.sleep(min(next_tick - now, 0.004))
            continue
        next_tick += tick
        subscribers: list[WebSocket] = []
        should_broadcast = False
        payload: dict[str, Any] | None = None
        with state.lock:
            if state.input_mode == "replay":
                apply_replay_input()
            elif state.input_mode == "live":
                radio = state.bridge.snapshot()
                age = radio["sample_age_s"]
                if age is None or age > 0.25:
                    state.model.set_rc(state.model.rc_channels, valid=False, age_s=age or 1.0)
                    state.running = False
            if state.running:
                state.model.step(tick)
            should_broadcast = now >= broadcast_at
            if should_broadcast:
                broadcast_at = now + 1 / 60
                payload = state.model.snapshot()
                payload.update(
                    {
                        "running": state.running,
                        "input_mode": state.input_mode,
                        "serial": state.bridge.snapshot(),
                        "recording": state.recording,
                        "replay_loaded": bool(state.replay_samples),
                    }
                )
                subscribers = list(state.subscribers)
        if should_broadcast and payload is not None and subscribers:
            dead: list[WebSocket] = []
            for subscriber in subscribers:
                try:
                    await subscriber.send_json(payload)
                except Exception:
                    dead.append(subscriber)
            with state.lock:
                for subscriber in dead:
                    state.subscribers.discard(subscriber)


@app.get("/api/ports")
def ports() -> dict[str, Any]:
    return {"ports": SerialBridge.list_ports()}


@app.get("/api/state")
def get_state() -> dict[str, Any]:
    return snapshot()


@app.post("/api/serial/connect")
def connect_serial(payload: ConnectionRequest) -> dict[str, Any]:
    try:
        state.bridge.connect(payload.port, payload.baudrate)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with state.lock:
        state.input_mode = "live"
    return snapshot()


@app.post("/api/serial/disconnect")
def disconnect_serial() -> dict[str, Any]:
    state.bridge.disconnect()
    with state.lock:
        state.input_mode = "virtual"
        state.model.set_rc([1500] * 16, valid=False, age_s=1.0)
    return snapshot()


@app.post("/api/input/mode")
def set_input_mode(payload: ModeRequest) -> dict[str, Any]:
    if payload.mode not in {"virtual", "live", "replay"}:
        raise HTTPException(status_code=400, detail="mode must be virtual, live, or replay")
    with state.lock:
        state.input_mode = payload.mode
        if payload.mode == "replay":
            state.replay_started_at = state.model.state.sim_time
        if payload.mode == "virtual":
            channels = [1500] * 16
            channels[state.model.channel_mapping["throttle"]] = 1000
            state.model.set_rc(channels, valid=True, age_s=0.0)
    return snapshot()


@app.post("/api/input/virtual")
def set_virtual_rc(payload: VirtualRcRequest) -> dict[str, Any]:
    with state.lock:
        state.input_mode = "virtual"
        state.model.set_rc(payload.channels, valid=True, age_s=0.0)
        if state.recording:
            state.recording_samples.append(ReplaySample(state.model.state.sim_time, state.model.rc_channels))
    return snapshot()


@app.post("/api/control-mode")
def set_control_mode(payload: ControlModeRequest) -> dict[str, Any]:
    try:
        with state.lock:
            state.model.set_control_mode(payload.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return snapshot()


@app.post("/api/simulation/{action}")
def simulation_action(action: str) -> dict[str, Any]:
    if action not in {"start", "pause", "reset"}:
        raise HTTPException(status_code=404, detail="unknown simulation action")
    with state.lock:
        if action == "start":
            state.running = True
        elif action == "pause":
            state.running = False
        else:
            state.model.reset()
            state.model.set_rc([1500] * 16, valid=False, age_s=1.0)
            state.replay_started_at = state.model.state.sim_time
            state.running = False
    return snapshot()


@app.post("/api/pid")
def set_pid(payload: PidRequest) -> dict[str, Any]:
    axes = {"roll": state.model.pid.roll, "pitch": state.model.pid.pitch, "yaw": state.model.pid.yaw}
    if payload.axis not in axes:
        raise HTTPException(status_code=400, detail="axis must be roll, pitch, or yaw")
    axis = axes[payload.axis]
    axis.kp, axis.ki, axis.kd = payload.kp, payload.ki, payload.kd
    return snapshot()


@app.post("/api/channel-mapping")
def set_channel_mapping(payload: ChannelMappingRequest) -> dict[str, Any]:
    try:
        state.model.set_channel_mapping(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return snapshot()


@app.post("/api/config")
def set_simulation_config(payload: SimulationConfigRequest) -> dict[str, Any]:
    values = {name: value for name, value in payload.model_dump().items() if value is not None}
    for name, value in values.items():
        setattr(state.model.config, name, value)
    return snapshot()


@app.post("/api/record/start")
def start_recording() -> dict[str, Any]:
    with state.lock:
        state.recording = True
        state.recording_samples = []
    return snapshot()


@app.post("/api/record/stop", response_class=PlainTextResponse)
def stop_recording() -> str:
    with state.lock:
        state.recording = False
        return samples_to_csv(state.recording_samples)


@app.post("/api/replay", response_class=PlainTextResponse)
def load_replay(csv_text: str = Body(..., media_type="text/plain")) -> str:
    try:
        samples = parse_csv(csv_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with state.lock:
        state.replay_samples = samples
        state.input_mode = "replay"
        state.replay_started_at = state.model.state.sim_time
    return f"loaded {len(samples)} samples"


@app.websocket("/ws/state")
async def websocket_state(websocket: WebSocket) -> None:
    await websocket.accept()
    with state.lock:
        state.subscribers.add(websocket)
    try:
        await websocket.send_json(snapshot())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        with state.lock:
            state.subscribers.discard(websocket)
