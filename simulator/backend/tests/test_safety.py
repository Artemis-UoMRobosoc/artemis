from simulator.backend.msp import Status
from simulator.backend.server import state
from simulator.backend.serial_bridge import RadioSample


def test_receiver_failsafe_status_clears_simulator_input():
    with state.lock:
        state.input_mode = "live"
        state.running = True
        state.model.set_rc([1500, 1500, 1500, 1400], valid=True, age_s=0)
    state.on_radio_sample(RadioSample([1500] * 16, Status(1 << 6, 0, b""), 0.0))
    with state.lock:
        assert state.model.failsafe is True
        assert state.model.rc_valid is False
        assert state.running is False
        state.input_mode = "virtual"
        state.running = True


def test_arming_failsafe_status_clears_simulator_input():
    with state.lock:
        state.input_mode = "live"
        state.running = True
        state.model.set_rc([1500, 1500, 1500, 1400], valid=True, age_s=0)
    state.on_radio_sample(RadioSample([1500] * 16, Status(0, 1 << 2, b""), 0.0))
    with state.lock:
        assert state.model.failsafe is True
        assert state.model.rc_valid is False
        assert state.running is False
        state.input_mode = "virtual"
        state.running = True


def test_short_rc_packet_pauses_live_simulation():
    with state.lock:
        state.input_mode = "live"
        state.running = True
        state.model.set_rc([1500, 1500, 1500, 1400], valid=True, age_s=0)
    state.on_radio_sample(RadioSample([1500, 1500], None, 0.0))
    with state.lock:
        assert state.model.failsafe is True
        assert state.running is False
        state.input_mode = "virtual"
        state.running = True


def test_invalid_rc_immediately_clears_pid_and_outputs():
    with state.lock:
        state.model.set_rc([1500, 1500, 1500, 1400], valid=True, age_s=0)
        state.model.step(0.01)
        assert any(state.model.state.motor_outputs)
        state.model.set_rc(state.model.rc_channels, valid=False, age_s=1.0)
        assert state.model.state.motor_outputs == [0.0] * 6
        assert state.model.pid.roll.integral == 0.0


def test_model_timeout_clears_outputs():
    with state.lock:
        state.model.set_rc([1500, 1500, 1500, 1400], valid=True, age_s=0)
        state.model.step(0.01)
        state.model.set_rc(state.model.rc_channels, valid=False, age_s=1.0)
        state.model.step(0.01)
        assert state.model.failsafe is True
        assert state.model.state.motor_outputs == [0.0] * 6
