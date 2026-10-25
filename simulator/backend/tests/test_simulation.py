import math

from simulator.backend.simulation import PidAxis, PidConfig, SimConfig, TarotHexacopter


def armed_model() -> TarotHexacopter:
    model = TarotHexacopter()
    model.set_rc([1500, 1500, 1500, 1350], valid=True, age_s=0)
    return model


def test_hex_has_six_positions_and_expected_radius():
    model = TarotHexacopter(SimConfig(arm_radius_m=0.34))
    assert len(model.motor_positions) == 6
    assert all(math.isclose(math.hypot(x, y), 0.34) for x, y, _ in model.motor_positions)
    assert model.motor_positions[0][0] < 0 and model.motor_positions[0][1] > 0  # M1 rear-right
    assert model.motor_positions[1][0] > 0 and model.motor_positions[1][1] > 0  # M2 front-right
    assert math.isclose(model.motor_positions[4][0], 0.0, abs_tol=1e-12) and model.motor_positions[4][1] > 0  # M5 right-middle


def test_failsafe_clears_outputs_and_pid_state():
    model = armed_model()
    model.step(0.01)
    assert any(model.state.motor_outputs)
    model.set_rc([1500] * 16, valid=False, age_s=1)
    model.step(0.01)
    assert model.state.motor_outputs == [0.0] * 6
    assert model.pid.roll.integral == 0.0


def test_fixed_step_is_deterministic():
    first = armed_model()
    second = armed_model()
    for _ in range(100):
        first.step(0.002)
        second.step(0.002)
    assert first.snapshot() == second.snapshot()


def test_pitch_input_changes_front_and_rear_mix():
    model = TarotHexacopter(pid=PidConfig())
    model.set_rc([1500, 1700, 1500, 1500], valid=True, age_s=0)
    model.step(0.01)
    assert len(model.state.motor_outputs) == 6
    assert max(model.state.motor_outputs) > min(model.state.motor_outputs)


def test_mixer_roll_pitch_and_yaw_directions():
    model = TarotHexacopter()
    roll = model._mix(0.5, (0.1, 0.0, 0.0))
    pitch = model._mix(0.5, (0.0, 0.1, 0.0))
    yaw = model._mix(0.5, (0.0, 0.0, 0.1))
    assert all(roll[index] > roll[other] for index in (0, 1, 4) for other in (2, 3, 5))
    assert all(pitch[index] > pitch[other] for index in (0, 2) for other in (1, 3))
    assert all(yaw[index] > yaw[other] for index in (2, 3, 4) for other in (0, 1, 5))


def test_yaw_mixer_has_authority_comparable_to_roll_and_pitch():
    model = TarotHexacopter()
    roll = model._mix(0.5, (0.1, 0.0, 0.0))
    yaw = model._mix(0.5, (0.0, 0.0, 0.1))
    roll_span = max(roll) - min(roll)
    yaw_span = max(yaw) - min(yaw)
    assert yaw_span > roll_span * 0.8


def test_yaw_mixer_gain_is_independent_from_airframe_yaw_torque_ratio():
    first = TarotHexacopter(SimConfig(yaw_torque_ratio=0.02, yaw_mix_gain=1.0))
    second = TarotHexacopter(SimConfig(yaw_torque_ratio=0.08, yaw_mix_gain=1.0))
    assert first._mix(0.5, (0.0, 0.0, 0.1)) == second._mix(0.5, (0.0, 0.0, 0.1))


def test_neutral_stick_deadband_ignores_small_channel_noise():
    model = TarotHexacopter()
    for yaw_channel in (1480, 1490, 1500, 1510, 1520):
        model.set_rc([1500, 1500, yaw_channel, 1300], valid=True, age_s=0)
        assert model._targets()[2] == 0.0


def test_left_stick_horizontal_yaw_channel_commands_turn():
    model = TarotHexacopter()
    model.set_rc([1500, 1500, 1800, 1300], valid=True, age_s=0)
    assert model.channel_mapping["yaw"] == 2
    assert model.channel_mapping["throttle"] == 3
    assert model._targets()[2] > 0
    for _ in range(100):
        model.step(0.002)
    assert model.state.angular_velocity[2] > 0
    assert model.state.attitude[2] > 0


def test_default_mapping_uses_ch1_roll_and_ch2_pitch():
    model = TarotHexacopter()
    assert model.channel_mapping == {"roll": 0, "pitch": 1, "throttle": 3, "yaw": 2}

    model.set_rc([1700, 1500, 1500, 1300], valid=True, age_s=0)
    assert model._targets()[0] < 0
    assert model._targets()[1] == 0

    model.set_rc([1500, 1700, 1500, 1300], valid=True, age_s=0)
    assert model._targets()[0] == 0
    assert model._targets()[1] > 0


def test_left_and_right_yaw_inputs_turn_in_opposite_directions():
    yaw_rates = []
    for yaw_channel in (1100, 1900):
        model = TarotHexacopter()
        model.set_rc([1500, 1500, yaw_channel, 1300], valid=True, age_s=0)
        for _ in range(100):
            model.step(0.002)
        yaw_rates.append(model.state.angular_velocity[2])
    assert yaw_rates[0] < 0 < yaw_rates[1]


def test_minimum_throttle_stops_yaw_and_clears_ground_rotation():
    model = TarotHexacopter()
    model.state.angular_velocity = [0.4, -0.3, 0.8]
    model.set_rc([1500, 1500, 1800, 1000], valid=True, age_s=0)
    model.step(0.002)
    assert model.state.motor_outputs == [0.0] * 6
    assert model.state.motor_thrusts == [0.0] * 6
    assert model.state.angular_velocity == [0.0, 0.0, 0.0]
    assert model.state.attitude == [0.0, 0.0, 0.0]


def test_minimum_throttle_clears_airborne_yaw_rate_without_changing_heading():
    model = TarotHexacopter()
    model.state.position[2] = 1.0
    model.state.attitude[2] = 0.7
    model.state.angular_velocity[2] = 1.1
    model.set_rc([1500, 1500, 1800, 1000], valid=True, age_s=0)
    model.step(0.002)
    assert model.state.motor_outputs == [0.0] * 6
    assert model.state.angular_velocity == [0.0, 0.0, 0.0]
    assert math.isclose(model.state.attitude[2], 0.7)


def test_mixer_scales_torque_to_keep_all_motors_in_range():
    model = TarotHexacopter()
    outputs = model._mix(0.25, (5.0, -5.0, 8.0))
    assert all(0.0 <= output <= 1.0 for output in outputs)
    assert math.isclose(sum(outputs) / 6, 0.25, rel_tol=0.05)


def test_pid_output_saturation_stops_integral_windup():
    axis = PidAxis(kp=2.0, ki=1.0, kd=0.0)
    outputs = [axis.update(1.0, 0.0, 0.01) for _ in range(1000)]
    assert all(-1.0 <= output <= 1.0 for output in outputs)
    assert axis.integral < 0.02


def test_channel_mapping_changes_control_source():
    model = armed_model()
    model.set_channel_mapping({"roll": 4, "pitch": 1, "throttle": 2, "yaw": 3})
    channels = [1500] * 16
    channels[4] = 1700
    model.set_rc(channels, valid=True, age_s=0)
    model.step(0.01)
    assert max(model.state.motor_outputs) > min(model.state.motor_outputs)


def test_channel_mapping_rejects_duplicate_control_channels():
    model = armed_model()
    try:
        model.set_channel_mapping({"roll": 0, "pitch": 1, "throttle": 0, "yaw": 3})
    except ValueError as exc:
        assert "different channel" in str(exc)
    else:
        raise AssertionError("duplicate axis mapping should be rejected")


def test_angle_mode_uses_centered_sticks_as_level_target():
    model = armed_model()
    model.set_control_mode("angle")
    assert model._targets()[:3] == (0.0, 0.0, 0.0)
    assert model.snapshot()["target_attitude_deg"] == [0.0, 0.0, 0.0]


def test_angle_mode_maps_roll_and_pitch_sticks_to_tilt_targets():
    model = TarotHexacopter()
    model.set_control_mode("angle")
    model.set_rc([1000, 2000, 1500, 1500], valid=True, age_s=0)
    roll_rate, pitch_rate, _, _ = model._targets()
    assert math.isclose(model.snapshot()["target_attitude_deg"][0], 45.0)
    assert math.isclose(model.snapshot()["target_attitude_deg"][1], 45.0)
    assert roll_rate > 0
    assert pitch_rate > 0


def test_angle_mode_stick_directions_match_visible_airframe_tilt():
    # CH1 right lowers the right side; CH1 left lowers the left side.
    # CH2 forward lowers the nose; CH2 back raises the nose. In this radio
    # setup the forward direction is the high side of CH2.
    cases = (
        (0, 1900, 0, -1),
        (0, 1100, 0, 1),
        (1, 1900, 1, 1),
        (1, 1100, 1, -1),
    )
    for channel, value, attitude_axis, expected_sign in cases:
        model = TarotHexacopter()
        model.set_control_mode("angle")
        channels = [1500] * 16
        channels[3] = 1400
        channels[channel] = value
        model.set_rc(channels, valid=True, age_s=0)

        for _ in range(500):
            model.step(0.002)

        assert model.state.attitude[attitude_axis] * expected_sign > 0


def test_angle_mode_corrects_toward_level_when_sticks_are_centered():
    model = armed_model()
    model.set_control_mode("angle")
    model.state.attitude[0] = math.radians(20)
    model.state.attitude[1] = math.radians(-15)
    roll_rate, pitch_rate, _, _ = model._targets()
    assert roll_rate < 0
    assert pitch_rate > 0


def test_changing_control_mode_clears_rate_pid_integrators():
    model = armed_model()
    model.pid.roll.integral = 0.75
    model.pid.pitch.integral = -0.5
    model.pid.yaw.integral = 0.25
    model.set_control_mode("angle")
    assert [model.pid.roll.integral, model.pid.pitch.integral, model.pid.yaw.integral] == [0, 0, 0]


def test_failsafe_clears_angle_targets():
    model = TarotHexacopter()
    model.set_control_mode("angle")
    model.set_rc([1000, 2000, 1500, 1500], valid=True, age_s=0)
    assert model.snapshot()["target_attitude_deg"] == [45.0, 45.0, 0.0]
    model.set_rc([1000, 2000, 1500, 1500], valid=False, age_s=1)
    assert model.snapshot()["target_attitude_deg"] == [0.0, 0.0, 0.0]


def test_ground_plane_prevents_unbounded_fall():
    model = armed_model()
    model.set_rc([1500, 1500, 1500, 1000], valid=True, age_s=0)
    for _ in range(1000):
        model.step(0.01)
    assert model.state.position[2] == 0.0
