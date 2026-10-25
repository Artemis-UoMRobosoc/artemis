from fastapi.testclient import TestClient

from simulator.backend.server import app, state


def test_state_endpoint_reports_six_outputs():
    with TestClient(app) as client:
        response = client.get("/api/state")
    assert response.status_code == 200
    body = response.json()
    assert len(body["motor_outputs"]) == 6
    assert body["serial"]["connected"] is False


def test_virtual_input_is_local_only():
    with TestClient(app) as client:
        response = client.post("/api/input/virtual", json={"channels": [1600, 1400, 1300, 1500]})
    assert response.status_code == 200
    assert response.json()["input_mode"] == "virtual"
    assert response.json()["rc_channels"][:4] == [1600, 1400, 1300, 1500]
    assert state.bridge.last_error is None


def test_control_mode_api_updates_simulator_and_rejects_unknown_modes():
    original_mode = state.model.control_mode
    try:
        with TestClient(app) as client:
            accepted = client.post("/api/control-mode", json={"mode": "angle"})
            rejected = client.post("/api/control-mode", json={"mode": "acro"})
        assert accepted.status_code == 200
        assert accepted.json()["control_mode"] == "angle"
        assert rejected.status_code == 400
    finally:
        state.model.set_control_mode(original_mode)


def test_replay_endpoint_reads_plain_text_body():
    csv_text = "time_s," + ",".join(f"ch{index}" for index in range(1, 17)) + "\n0.0," + ",".join(["1500"] * 16) + "\n"
    with TestClient(app) as client:
        response = client.post("/api/replay", content=csv_text, headers={"content-type": "text/plain"})
    assert response.status_code == 200
    assert "loaded 1 samples" in response.text


def test_mapping_and_physics_controls_update_simulator_only():
    original_mapping = dict(state.model.channel_mapping)
    original_config = {
        "mass_kg": state.model.config.mass_kg,
        "arm_radius_m": state.model.config.arm_radius_m,
        "max_motor_thrust_n": state.model.config.max_motor_thrust_n,
        "motor_time_constant_s": state.model.config.motor_time_constant_s,
        "yaw_mix_gain": state.model.config.yaw_mix_gain,
        "linear_drag": state.model.config.linear_drag,
        "angular_drag": state.model.config.angular_drag,
        "max_angle_deg": state.model.config.max_angle_deg,
        "angle_response": state.model.config.angle_response,
    }
    mapping = {"roll": 4, "pitch": 5, "throttle": 2, "yaw": 3}
    config = {
        "mass_kg": 2.6,
        "arm_radius_m": 0.36,
        "max_motor_thrust_n": 13.0,
        "motor_time_constant_s": 0.1,
        "yaw_mix_gain": 1.4,
        "linear_drag": 0.2,
        "angular_drag": 0.14,
        "max_angle_deg": 40.0,
        "angle_response": 5.0,
    }
    try:
        with TestClient(app) as client:
            mapping_response = client.post("/api/channel-mapping", json=mapping)
            config_response = client.post("/api/config", json=config)
        assert mapping_response.status_code == 200
        assert mapping_response.json()["channel_mapping"] == mapping
        assert config_response.status_code == 200
        returned_config = config_response.json()["config"]
        assert {name: returned_config[name] for name in config} == config
    finally:
        with state.lock:
            state.model.set_channel_mapping(original_mapping)
            for name, value in original_config.items():
                setattr(state.model.config, name, value)


def test_config_api_accepts_legacy_payload_without_angle_fields():
    payload = {
        "mass_kg": state.model.config.mass_kg,
        "arm_radius_m": state.model.config.arm_radius_m,
        "max_motor_thrust_n": state.model.config.max_motor_thrust_n,
        "motor_time_constant_s": state.model.config.motor_time_constant_s,
        "linear_drag": state.model.config.linear_drag,
        "angular_drag": state.model.config.angular_drag,
    }
    with TestClient(app) as client:
        response = client.post("/api/config", json=payload)
    assert response.status_code == 200


def test_reset_pauses_simulation():
    with state.lock:
        state.running = True
    with TestClient(app) as client:
        response = client.post("/api/simulation/reset")
    assert response.status_code == 200
    assert response.json()["running"] is False
