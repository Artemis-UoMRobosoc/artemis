"""Deterministic six-degree-of-freedom Tarot 680 simulation model."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Iterable


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def wrap_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


@dataclass
class SimConfig:
    mass_kg: float = 2.2
    arm_radius_m: float = 0.34
    max_motor_thrust_n: float = 12.0
    motor_time_constant_s: float = 0.08
    yaw_torque_ratio: float = 0.055
    # Normalized yaw differential used by the mixer. Keep this separate from
    # yaw_torque_ratio: the latter describes the airframe, while this value
    # controls how much motor authority a normalized PID command requests.
    yaw_mix_gain: float = 1.0
    linear_drag: float = 0.18
    angular_drag: float = 0.12
    inertia_x: float = 0.095
    inertia_y: float = 0.095
    inertia_z: float = 0.16
    gravity: float = 9.81
    max_rate_roll: float = 2.8
    max_rate_pitch: float = 2.8
    max_rate_yaw: float = 2.2
    max_angle_deg: float = 45.0
    angle_response: float = 4.0


@dataclass
class PidAxis:
    kp: float
    ki: float
    kd: float
    integral: float = 0.0
    previous_error: float = 0.0

    def reset(self, previous_error: float = 0.0) -> None:
        self.integral = 0.0
        self.previous_error = previous_error

    def update(self, target: float, measured: float, dt: float) -> float:
        error = target - measured
        derivative = (error - self.previous_error) / dt if dt > 0 else 0.0
        self.previous_error = error
        candidate_integral = clamp(self.integral + error * dt, -2.0, 2.0)
        output = self.kp * error + self.ki * candidate_integral + self.kd * derivative
        pushing_further_into_saturation = (output > 1.0 and error > 0) or (output < -1.0 and error < 0)
        if not pushing_further_into_saturation:
            self.integral = candidate_integral
        else:
            output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return clamp(output, -1.0, 1.0)


@dataclass
class PidConfig:
    roll: PidAxis = field(default_factory=lambda: PidAxis(0.18, 0.045, 0.012))
    pitch: PidAxis = field(default_factory=lambda: PidAxis(0.18, 0.045, 0.012))
    yaw: PidAxis = field(default_factory=lambda: PidAxis(0.16, 0.035, 0.008))


@dataclass
class AircraftState:
    sim_time: float = 0.0
    position: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    attitude: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    angular_velocity: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    motor_outputs: list[float] = field(default_factory=lambda: [0.0] * 6)
    motor_thrusts: list[float] = field(default_factory=lambda: [0.0] * 6)


class TarotHexacopter:
    """A small, transparent physics model for controller development.

    Coordinates use x forward, y right, z up. The body rotates with roll,
    pitch and yaw in radians. The model is intentionally conservative: all
    unmeasured airframe and propulsion values live in SimConfig.
    """

    # x points forward and y points right. Viewed from above with the nose
    # forward, this is M1 rear-right, M2 front-right, M3 rear-left,
    # M4 front-left, M5 right-middle, M6 left-middle.
    motor_angles = tuple(math.radians(value) for value in (150, 30, 210, 330, 90, 270))
    motor_yaw_sign = (-1.0, -1.0, 1.0, 1.0, 1.0, -1.0)
    # Calibrated for the RadioMaster Pocket direction used here: the physical
    # right-stick horizontal input lowers the right side, and the physical
    # right-stick forward input lowers the nose.
    roll_input_sign = -1.0
    pitch_input_sign = 1.0
    stick_deadband_us = 20
    throttle_idle_cutoff = 0.01

    def __init__(self, config: SimConfig | None = None, pid: PidConfig | None = None) -> None:
        self.config = config or SimConfig()
        self.pid = pid or PidConfig()
        self.state = AircraftState()
        self.rc_channels = [1500] * 16
        self.rc_channels[3] = 1000
        self.rc_valid = False
        self.last_rc_age_s = float("inf")
        self.failsafe = True
        # RadioMaster Pocket layout for this setup: CH1 is right-stick
        # horizontal (roll), CH2 is right-stick vertical (pitch), CH3 is yaw,
        # and CH4 is throttle.
        self.channel_mapping = {"roll": 0, "pitch": 1, "throttle": 3, "yaw": 2}
        self.control_mode = "rate"
        self.target_attitude = [0.0, 0.0, 0.0]
        self.target_rates = [0.0, 0.0, 0.0]

    @property
    def motor_positions(self) -> list[tuple[float, float, float]]:
        radius = self.config.arm_radius_m
        return [(radius * math.cos(a), radius * math.sin(a), 0.0) for a in self.motor_angles]

    def reset(self) -> None:
        self.state = AircraftState()
        for axis in (self.pid.roll, self.pid.pitch, self.pid.yaw):
            axis.reset()
        self.target_attitude = [0.0, 0.0, 0.0]
        self.target_rates = [0.0, 0.0, 0.0]

    def set_control_mode(self, mode: str) -> None:
        if mode not in {"rate", "angle"}:
            raise ValueError("control mode must be rate or angle")
        if mode != self.control_mode:
            self.control_mode = mode
            targets = self._targets()
            measured = self.state.angular_velocity
            for axis, target, current in zip((self.pid.roll, self.pid.pitch, self.pid.yaw), targets[:3], measured):
                axis.reset(target - current)
        else:
            self._targets()

    def set_rc(self, channels: Iterable[int], valid: bool = True, age_s: float = 0.0) -> None:
        values = [int(round(value)) for value in channels]
        self.rc_channels = (values + [1500] * 16)[:16]
        self.rc_valid = valid
        self.last_rc_age_s = age_s
        self.failsafe = not valid or age_s > 0.25
        if self.failsafe:
            self.target_attitude = [0.0, 0.0, 0.0]
            self.target_rates = [0.0, 0.0, 0.0]
            self.state.motor_outputs = [0.0] * 6
            self.state.motor_thrusts = [0.0] * 6
            self.state.angular_velocity = [0.0, 0.0, 0.0]
            for axis in (self.pid.roll, self.pid.pitch, self.pid.yaw):
                axis.reset()
        else:
            self._targets()

    def set_channel_mapping(self, mapping: dict[str, int]) -> None:
        if set(mapping) != {"roll", "pitch", "throttle", "yaw"}:
            raise ValueError("channel mapping must define roll, pitch, throttle, and yaw")
        if any(index < 0 or index >= 16 for index in mapping.values()):
            raise ValueError("channel indexes must be between 0 and 15")
        if len(set(mapping.values())) != len(mapping):
            raise ValueError("each control axis must use a different channel")
        self.channel_mapping = dict(mapping)

    def _stick_axis(self, channel: int) -> float:
        offset = channel - 1500
        distance = abs(offset)
        if distance <= self.stick_deadband_us:
            return 0.0
        scaled = (distance - self.stick_deadband_us) / (500 - self.stick_deadband_us)
        return clamp(math.copysign(scaled, offset), -1.0, 1.0)

    def _targets(self) -> tuple[float, float, float, float]:
        roll = self._stick_axis(self.rc_channels[self.channel_mapping["roll"]]) * self.roll_input_sign
        pitch = self._stick_axis(self.rc_channels[self.channel_mapping["pitch"]]) * self.pitch_input_sign
        throttle = clamp((self.rc_channels[self.channel_mapping["throttle"]] - 1000) / 1000)
        yaw = self._stick_axis(self.rc_channels[self.channel_mapping["yaw"]])
        yaw_rate = yaw * self.config.max_rate_yaw
        if self.control_mode == "angle":
            max_angle = math.radians(self.config.max_angle_deg)
            target_roll = roll * max_angle
            target_pitch = pitch * max_angle
            roll_error = wrap_angle(target_roll - self.state.attitude[0])
            pitch_error = wrap_angle(target_pitch - self.state.attitude[1])
            roll_rate = clamp(
                roll_error * self.config.angle_response,
                -self.config.max_rate_roll,
                self.config.max_rate_roll,
            )
            pitch_rate = clamp(
                pitch_error * self.config.angle_response,
                -self.config.max_rate_pitch,
                self.config.max_rate_pitch,
            )
            self.target_attitude = [target_roll, target_pitch, 0.0]
        else:
            roll_rate = roll * self.config.max_rate_roll
            pitch_rate = pitch * self.config.max_rate_pitch
            self.target_attitude = [0.0, 0.0, 0.0]
        self.target_rates = [roll_rate, pitch_rate, yaw_rate]
        return (roll_rate, pitch_rate, yaw_rate, throttle)

    def _mix(self, throttle: float, torque: tuple[float, float, float]) -> list[float]:
        throttle = clamp(throttle)
        roll_torque, pitch_torque, yaw_torque = torque
        increments: list[float] = []
        for index, (x, y, _) in enumerate(self.motor_positions):
            roll_mix = y / self.config.arm_radius_m
            pitch_mix = -x / self.config.arm_radius_m
            yaw_mix = (
                self.motor_yaw_sign[index] * self.config.yaw_mix_gain
                if self.config.yaw_mix_gain > 0
                else 0.0
            )
            increments.append(roll_torque * roll_mix + pitch_torque * pitch_mix + yaw_torque * yaw_mix)
        positive_peak = max(increments, default=0.0)
        negative_peak = min(increments, default=0.0)
        scale = 1.0
        if positive_peak > 0:
            scale = min(scale, (1.0 - throttle) / positive_peak)
        if negative_peak < 0:
            scale = min(scale, throttle / -negative_peak)
        return [clamp(throttle + increment * scale) for increment in increments]

    def _body_to_world(self, vector: tuple[float, float, float]) -> tuple[float, float, float]:
        roll, pitch, yaw = self.state.attitude
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)
        x, y, z = vector
        return (
            (cy * cp) * x + (cy * sp * sr - sy * cr) * y + (cy * sp * cr + sy * sr) * z,
            (sy * cp) * x + (sy * sp * sr + cy * cr) * y + (sy * sp * cr - cy * sr) * z,
            -sp * x + cp * sr * y + cp * cr * z,
        )

    def step(self, dt: float) -> AircraftState:
        dt = max(1e-5, min(dt, 0.02))
        if self.failsafe:
            self.state.motor_outputs = [0.0] * 6
            self.state.motor_thrusts = [0.0] * 6
            for axis in (self.pid.roll, self.pid.pitch, self.pid.yaw):
                axis.reset()
        else:
            target_roll, target_pitch, target_yaw, throttle = self._targets()
            if throttle <= self.throttle_idle_cutoff:
                self.state.motor_outputs = [0.0] * 6
                self.state.motor_thrusts = [0.0] * 6
                for axis in (self.pid.roll, self.pid.pitch, self.pid.yaw):
                    axis.reset()
                # The simulator treats the low-stick state as a hard motor
                # stop. This prevents residual PID momentum from making the
                # rendered airframe keep yawing after the pilot releases the
                # throttle, including after a previous airborne run.
                self.state.angular_velocity = [0.0, 0.0, 0.0]
                if self.state.position[2] <= 0.0:
                    self.state.velocity = [0.0, 0.0, 0.0]
            else:
                measured_roll, measured_pitch, measured_yaw = self.state.angular_velocity
                torque = (
                    self.pid.roll.update(target_roll, measured_roll, dt),
                    self.pid.pitch.update(target_pitch, measured_pitch, dt),
                    self.pid.yaw.update(target_yaw, measured_yaw, dt),
                )
                desired = self._mix(throttle, torque)
                alpha = clamp(dt / self.config.motor_time_constant_s)
                self.state.motor_outputs = [current + alpha * (target - current) for current, target in zip(self.state.motor_outputs, desired)]
                self.state.motor_thrusts = [self.config.max_motor_thrust_n * output * output for output in self.state.motor_outputs]

        total_thrust = sum(self.state.motor_thrusts)
        body_force = (0.0, 0.0, total_thrust)
        world_force = self._body_to_world(body_force)
        acceleration = (
            world_force[0] / self.config.mass_kg - self.config.linear_drag * self.state.velocity[0],
            world_force[1] / self.config.mass_kg - self.config.linear_drag * self.state.velocity[1],
            world_force[2] / self.config.mass_kg - self.config.gravity - self.config.linear_drag * self.state.velocity[2],
        )
        self.state.velocity = [v + a * dt for v, a in zip(self.state.velocity, acceleration)]
        self.state.position = [p + v * dt for p, v in zip(self.state.position, self.state.velocity)]
        if self.state.position[2] < 0.0:
            self.state.position[2] = 0.0
            if self.state.velocity[2] < 0.0:
                self.state.velocity[2] = 0.0

        torque_body = [0.0, 0.0, 0.0]
        for (x, y, _), thrust, yaw_sign in zip(self.motor_positions, self.state.motor_thrusts, self.motor_yaw_sign):
            torque_body[0] += y * thrust
            torque_body[1] += -x * thrust
            torque_body[2] += yaw_sign * self.config.yaw_torque_ratio * thrust
        inertias = (self.config.inertia_x, self.config.inertia_y, self.config.inertia_z)
        angular_acceleration = [
            (torque_body[index] - self.config.angular_drag * self.state.angular_velocity[index]) / inertias[index]
            for index in range(3)
        ]
        self.state.angular_velocity = [w + a * dt for w, a in zip(self.state.angular_velocity, angular_acceleration)]
        self.state.attitude = [wrap_angle(a + w * dt) for a, w in zip(self.state.attitude, self.state.angular_velocity)]
        self.state.sim_time += dt
        return self.state

    def snapshot(self) -> dict:
        if not self.failsafe:
            self._targets()
        return {
            "sim_time": self.state.sim_time,
            "position": self.state.position,
            "velocity": self.state.velocity,
            "attitude": self.state.attitude,
            "angular_velocity": self.state.angular_velocity,
            "attitude_deg": [math.degrees(value) for value in self.state.attitude],
            "angular_velocity_deg_s": [math.degrees(value) for value in self.state.angular_velocity],
            "control_mode": self.control_mode,
            "target_attitude_deg": [math.degrees(value) for value in self.target_attitude] if self.control_mode == "angle" else None,
            "target_rate_deg_s": [math.degrees(value) for value in self.target_rates],
            "motor_outputs": self.state.motor_outputs,
            "motor_thrusts": self.state.motor_thrusts,
            "rc_channels": self.rc_channels,
            "rc_valid": self.rc_valid,
            "rc_age_s": self.last_rc_age_s if math.isfinite(self.last_rc_age_s) else None,
            "failsafe": self.failsafe,
            "config": asdict(self.config),
            "channel_mapping": self.channel_mapping,
        }
