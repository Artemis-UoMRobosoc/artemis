"""Read-only Betaflight MSP v1 helpers.

The bridge deliberately supports only MSP_RC and MSP_STATUS_EX. Both are
outgoing telemetry queries; no configuration, arming, calibration, or motor
commands are ever emitted by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

MSP_RC = 105
MSP_STATUS_EX = 150
READ_ONLY_COMMANDS = frozenset({MSP_RC, MSP_STATUS_EX})
BOXFAILSAFE = 6
ARMING_DISABLED_FAILSAFE = 1 << 1
ARMING_DISABLED_RX_FAILSAFE = 1 << 2
ARMING_DISABLED_BOXFAILSAFE = 1 << 4
ARMING_FAILSAFE_MASK = ARMING_DISABLED_FAILSAFE | ARMING_DISABLED_RX_FAILSAFE | ARMING_DISABLED_BOXFAILSAFE


def request(command: int) -> bytes:
    """Build an MSP v1 request with an empty payload."""

    if command not in READ_ONLY_COMMANDS:
        raise ValueError(f"MSP command {command} is not allowed by the bridge")
    payload_length = 0
    checksum = payload_length ^ command
    return b"$M<" + bytes((payload_length, command, checksum))


@dataclass(frozen=True)
class MspFrame:
    direction: str
    command: int
    payload: bytes


class MspV1Parser:
    """Incremental parser for MSP v1 response frames."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes | bytearray) -> list[MspFrame]:
        self._buffer.extend(data)
        frames: list[MspFrame] = []
        while True:
            start = self._buffer.find(b"$M")
            if start < 0:
                self._buffer.clear()
                break
            if start:
                del self._buffer[:start]
            if len(self._buffer) < 6:
                break
            direction = chr(self._buffer[2])
            if direction not in ">!":
                del self._buffer[0]
                continue
            length = self._buffer[3]
            frame_size = 6 + length
            if len(self._buffer) < frame_size:
                break
            command = self._buffer[4]
            payload = bytes(self._buffer[5 : 5 + length])
            checksum = self._buffer[5 + length]
            expected = length ^ command
            for value in payload:
                expected ^= value
            del self._buffer[:frame_size]
            if checksum == expected:
                frames.append(MspFrame(direction, command, payload))
        return frames


def parse_rc(payload: bytes) -> list[int]:
    """Decode MSP_RC's little-endian 16-bit channel values."""

    if len(payload) % 2:
        raise ValueError("MSP_RC payload must contain 16-bit channel pairs")
    return [payload[index] | (payload[index + 1] << 8) for index in range(0, len(payload), 2)]


@dataclass(frozen=True)
class Status:
    flight_mode_flags: int
    arming_disable_flags: int
    raw_payload: bytes

    @property
    def receiver_failsafe(self) -> bool:
        return bool(self.flight_mode_flags & (1 << BOXFAILSAFE))

    @property
    def failsafe(self) -> bool:
        """Return true for either an active failsafe mode or disable flag."""

        return self.receiver_failsafe or bool(self.arming_disable_flags & ARMING_FAILSAFE_MASK)


def parse_status_ex(payload: bytes) -> Status:
    """Decode the status fields needed for simulator safety gating.

    Betaflight 4.5.x writes the first 4-byte flight-mode bitmask at offset 6.
    MSP_STATUS_EX then stores the PID profile count and control-rate profile
    before the extension-length byte at offset 13. The extension is followed
    by an arming-disable count byte and a 32-bit bitmask.
    """

    if len(payload) < 14:
        raise ValueError("MSP_STATUS_EX payload is too short")
    flight_mode_flags = int.from_bytes(payload[6:10], "little")
    offset = 13  # cycle time, errors, sensors, flags, pid/profile/rate fields
    extension_length = payload[offset]
    offset += 1 + extension_length
    if offset >= len(payload):
        return Status(flight_mode_flags, 0, payload)
    arming_count = payload[offset]
    offset += 1
    if arming_count <= 0 or offset + 4 > len(payload):
        return Status(flight_mode_flags, 0, payload)
    arming_flags = int.from_bytes(payload[offset : offset + 4], "little")
    return Status(flight_mode_flags, arming_flags, payload)


def build_frame(command: int, payload: Iterable[int] = (), direction: str = ">") -> bytes:
    """Build a response frame for parser tests."""

    data = bytes(payload)
    if not 0 <= len(data) <= 255:
        raise ValueError("MSP v1 payload must fit in one byte")
    checksum = len(data) ^ command
    for value in data:
        checksum ^= value
    return b"$M" + direction.encode("ascii") + bytes((len(data), command)) + data + bytes((checksum,))
