"""Optional, read-only serial bridge from Betaflight MSP telemetry to RC data."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from .msp import MSP_RC, MSP_STATUS_EX, MspV1Parser, Status, parse_rc, parse_status_ex, request


@dataclass
class RadioSample:
    channels: list[int]
    status: Status | None
    received_at: float


class SerialBridge:
    """Poll a Betaflight serial port with only MSP_RC/MSP_STATUS_EX queries."""

    def __init__(self, on_sample: Callable[[RadioSample], None] | None = None) -> None:
        self.on_sample = on_sample
        self.port_name: str | None = None
        self.connected = False
        self.last_sample: RadioSample | None = None
        self.last_error: str | None = None
        self._serial = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._parser = MspV1Parser()
        self._lock = threading.Lock()

    @staticmethod
    def list_ports() -> list[dict[str, str | None]]:
        try:
            from serial.tools import list_ports
        except ImportError:
            return []
        return [
            {"device": item.device, "description": item.description, "manufacturer": item.manufacturer}
            for item in list_ports.comports()
        ]

    def connect(self, port: str, baudrate: int = 115200) -> None:
        self.disconnect()
        import serial

        # Use non-blocking reads so a quiet USB endpoint cannot delay the next
        # RC poll or leave a partial MSP frame sitting in the OS buffer.
        self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=0, write_timeout=0.2)
        self.port_name = port
        self.connected = True
        self.last_error = None
        self._stop.clear()
        self._thread = threading.Thread(target=self._poll_loop, name="artemis-msp", daemon=True)
        self._thread.start()

    def disconnect(self) -> None:
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=0.5)
        self._thread = None
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        self.connected = False

    def _poll_loop(self) -> None:
        assert self._serial is not None
        next_rc_poll = time.monotonic()
        next_status_poll = next_rc_poll
        pending_status: Status | None = None
        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_rc_poll:
                try:
                    # These are the only commands written by the bridge, and
                    # both are read-only telemetry requests.
                    self._serial.write(request(MSP_RC))
                    next_rc_poll = now + 0.02
                    if now >= next_status_poll:
                        self._serial.write(request(MSP_STATUS_EX))
                        # Status is safety metadata; polling it at 5 Hz avoids
                        # competing with the 50 Hz RC stream on USB VCP.
                        next_status_poll = now + 0.2
                except Exception as exc:
                    self.last_error = str(exc)
                    self.connected = False
                    break
            try:
                data = self._serial.read_all()
                if not data:
                    time.sleep(0.001)
                    continue
                for frame in self._parser.feed(data):
                    if frame.command == MSP_STATUS_EX and frame.direction == ">":
                        try:
                            pending_status = parse_status_ex(frame.payload)
                        except ValueError as exc:
                            self.last_error = str(exc)
                    elif frame.command == MSP_RC and frame.direction == ">":
                        try:
                            sample = RadioSample(parse_rc(frame.payload), pending_status, time.monotonic())
                        except ValueError as exc:
                            self.last_error = str(exc)
                            continue
                        with self._lock:
                            self.last_sample = sample
                        if self.on_sample:
                            self.on_sample(sample)
            except Exception as exc:
                self.last_error = str(exc)
                self.connected = False
                break

    def snapshot(self) -> dict:
        with self._lock:
            sample = self.last_sample
        return {
            "connected": self.connected,
            "port": self.port_name,
            "last_error": self.last_error,
            "sample_age_s": None if sample is None else max(0.0, time.monotonic() - sample.received_at),
            "channels": None if sample is None else sample.channels,
            "status": None
            if sample is None or sample.status is None
            else {
                "flight_mode_flags": sample.status.flight_mode_flags,
                "arming_disable_flags": sample.status.arming_disable_flags,
                "receiver_failsafe": sample.status.receiver_failsafe,
                "failsafe": sample.status.failsafe,
            },
        }
