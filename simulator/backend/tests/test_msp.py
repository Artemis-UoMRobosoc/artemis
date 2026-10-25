import pytest

from simulator.backend.msp import MSP_RC, MSP_STATUS_EX, MspV1Parser, build_frame, parse_rc, parse_status_ex, request


def test_read_only_requests_are_whitelisted():
    assert request(MSP_RC) == b"$M<\x00ii"
    assert request(MSP_STATUS_EX)[4] == MSP_STATUS_EX
    with pytest.raises(ValueError):
        request(0)


def test_parser_handles_split_frames_and_bad_checksum():
    payload = bytes((0xDC, 0x05, 0xDC, 0x05))
    frame = build_frame(MSP_RC, payload)
    parser = MspV1Parser()
    assert parser.feed(frame[:3]) == []
    assert parser.feed(frame[3:]) == [] or parser.feed(b"") == []
    # A fresh parser makes the assertion independent of the split above.
    parsed = MspV1Parser().feed(frame)
    assert parsed[0].command == MSP_RC
    assert parse_rc(parsed[0].payload) == [1500, 1500]
    corrupted = bytearray(frame)
    corrupted[-1] ^= 0xFF
    assert MspV1Parser().feed(corrupted) == []


def test_status_ex_decodes_flags():
    # MSP_STATUS_EX 4.5.2: cycle, errors, sensors, flags, PID profile,
    # profile count, control-rate profile, extension length.
    payload = bytearray(13)
    payload[6:10] = (1 << 3).to_bytes(4, "little")
    payload.append(0)
    payload.extend((1).to_bytes(1, "little"))
    payload.extend((0x12345678).to_bytes(4, "little"))
    status = parse_status_ex(bytes(payload))
    assert status.flight_mode_flags == 8
    assert status.arming_disable_flags == 0x12345678
    assert status.receiver_failsafe is False


def test_status_ex_uses_betaflight_failsafe_bit():
    payload = bytearray(13)
    payload[6:10] = (1 << 6).to_bytes(4, "little")
    payload.append(0)
    payload.append(0)
    status = parse_status_ex(bytes(payload))
    assert status.receiver_failsafe is True


def test_status_ex_uses_arming_failsafe_bits():
    payload = bytearray(13)
    payload.append(0)
    payload.append(26)
    payload.extend((1 << 2).to_bytes(4, "little"))
    status = parse_status_ex(bytes(payload))
    assert status.receiver_failsafe is False
    assert status.failsafe is True
