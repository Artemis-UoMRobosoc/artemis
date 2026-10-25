import * as THREE from 'three';
import './style.css';

type Snapshot = {
  sim_time: number;
  attitude_deg: number[];
  angular_velocity_deg_s: number[];
  motor_outputs: number[];
  motor_thrusts: number[];
  rc_channels: number[];
  rc_valid: boolean;
  rc_age_s: number;
  failsafe: boolean;
  running: boolean;
  control_mode: 'rate' | 'angle';
  target_attitude_deg: number[] | null;
  target_rate_deg_s: number[];
  input_mode: 'virtual' | 'live' | 'replay';
  serial: { connected: boolean; port: string | null; last_error: string | null; sample_age_s: number | null };
  recording: boolean;
  replay_loaded: boolean;
  config: { mass_kg: number; arm_radius_m: number; max_motor_thrust_n: number; motor_time_constant_s: number; yaw_mix_gain: number; linear_drag: number; angular_drag: number; max_angle_deg: number; angle_response: number };
  channel_mapping: { roll: number; pitch: number; throttle: number; yaw: number };
};

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const WS_API = new URL('/ws/state', API).href.replace(/^http/, 'ws');
const channelOptions = Array.from({ length: 16 }, (_, index) => `<option value="${index}">CH${index + 1}</option>`).join('');
const defaultChannels = Array(16).fill(1500) as number[];
defaultChannels[3] = 1000;
const initialState: Snapshot = {
  sim_time: 0,
  attitude_deg: [0, 0, 0],
  angular_velocity_deg_s: [0, 0, 0],
  motor_outputs: [0, 0, 0, 0, 0, 0],
  motor_thrusts: [0, 0, 0, 0, 0, 0],
  rc_channels: defaultChannels,
  rc_valid: false,
  rc_age_s: Infinity,
  failsafe: true,
  running: false,
  control_mode: 'rate',
  target_attitude_deg: null,
  target_rate_deg_s: [0, 0, 0],
  input_mode: 'virtual',
  serial: { connected: false, port: null, last_error: null, sample_age_s: null },
  recording: false,
  replay_loaded: false,
  config: { mass_kg: 2.2, arm_radius_m: 0.34, max_motor_thrust_n: 12, motor_time_constant_s: 0.08, yaw_mix_gain: 1, linear_drag: 0.18, angular_drag: 0.12, max_angle_deg: 45, angle_response: 4 },
  channel_mapping: { roll: 0, pitch: 1, throttle: 3, yaw: 2 },
};

let state = initialState;
let virtualChannels = [...initialState.rc_channels];
let serialNotice: string | null = null;
let controlModeNotice: string | null = null;
let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let aircraft: THREE.Group;
let rotorMeshes: THREE.Mesh[] = [];
let armMeshes: THREE.Mesh[] = [];

const app = document.querySelector<HTMLDivElement>('#app')!;
app.innerHTML = `
  <div class="shell">
    <header class="topbar">
      <div class="brand-lockup"><span class="brand-mark">A</span><div><p class="eyebrow">ARTEMIS CONTROL LAB</p><h1>Tarot 680 / Flight Sandbox</h1></div></div>
      <div class="top-status"><span class="status-dot" id="system-dot"></span><span id="system-label">BACKEND OFFLINE</span><span class="divider"></span><span class="mono" id="sim-clock">T+00:00.000</span></div>
    </header>
    <main class="workspace">
      <section class="hero-panel panel">
        <div class="panel-head"><div><p class="eyebrow">LIVE AIRFRAME</p><h2>Hexacopter attitude</h2></div><div class="badge badge-warn" id="flight-badge">FAILSAFE</div></div>
        <div class="scene-wrap" id="scene-wrap"><div class="scene-hud hud-top-left"><span>MODEL / HEX6X</span><span>680 MM FRAME</span></div><div class="scene-hud hud-bottom-right"><span>ROLL <b id="roll-readout">0.0°</b></span><span>PITCH <b id="pitch-readout">0.0°</b></span><span>YAW <b id="yaw-readout">0.0°</b></span></div></div>
        <div class="attitude-strip"><div><span>ROLL RATE</span><strong id="roll-rate">0.0°/s</strong></div><div><span>PITCH RATE</span><strong id="pitch-rate">0.0°/s</strong></div><div><span>YAW RATE</span><strong id="yaw-rate">0.0°/s</strong></div><div><span>SIM TIME</span><strong id="sim-time">0.000 s</strong></div></div>
      </section>
      <aside class="control-column">
        <section class="panel panel-tight connection-panel"><div class="panel-head"><div><p class="eyebrow">I/O LINK</p><h2>Radio source</h2></div><span class="tiny-label" id="input-label">VIRTUAL</span></div><div class="connection-row"><select id="port-select"><option value="">Select F405 USB port</option></select><button class="button button-primary" id="connect-button">CONNECT</button></div><div class="connection-meta"><span id="serial-label" role="status" aria-live="polite">No serial bridge</span><span class="mono">MSP_RC / 105</span></div><div class="mode-switch"><button class="mode-button active" data-mode="virtual">VIRTUAL RC</button><button class="mode-button" data-mode="live">LIVE F405</button><button class="mode-button" data-mode="replay">REPLAY</button></div><div class="notice">Read-only telemetry path. The bridge never sends arming, motor, or configuration commands.</div></section>
        <section class="panel panel-tight"><div class="panel-head"><div><p class="eyebrow">RC INPUT</p><h2>Channel monitor</h2></div><span class="tiny-label mono" id="rc-health">NO SIGNAL</span></div><div class="control-mode"><div class="control-mode-head"><span>FLIGHT CONTROL MODE</span><span class="tiny-label">SIMULATOR ONLY</span></div><div class="flight-mode-switch" role="group" aria-label="Simulator flight control mode"><button class="flight-mode-button active" data-control-mode="rate" aria-pressed="true">RATE</button><button class="flight-mode-button" data-control-mode="angle" aria-pressed="false">ANGLE / SELF LEVEL</button></div><p class="angle-target" id="angle-target">Rate targets follow stick deflection</p></div><div id="channel-list" class="channel-list"></div><div class="stick-grid"><label>ROLL<input id="roll-stick" type="range" min="1000" max="2000" value="1500"></label><label>PITCH<input id="pitch-stick" type="range" min="1000" max="2000" value="1500"></label><label>THROTTLE<input id="throttle-stick" type="range" min="1000" max="2000" value="1000"></label><label>YAW<input id="yaw-stick" type="range" min="1000" max="2000" value="1500"></label></div></section>
        <section class="panel panel-tight"><div class="panel-head"><div><p class="eyebrow">RUN CONTROL</p><h2>Experiment loop</h2></div><span class="tiny-label" id="run-label">RUNNING</span></div><div class="action-grid"><button class="button" id="start-button">START</button><button class="button" id="pause-button">PAUSE</button><button class="button" id="reset-button">RESET</button><button class="button" id="record-button">RECORD</button></div><div class="replay-line"><span id="replay-label">No replay loaded</span><label class="file-button button">LOAD CSV<input id="replay-file" type="file" accept=".csv,text/csv"></label></div></section>
      </aside>
      <section class="panel motors-panel"><div class="panel-head"><div><p class="eyebrow">OUTPUT VECTOR</p><h2>Six-motor mixer</h2></div><span class="tiny-label mono">THRUST MODEL / ESTIMATED</span></div><div id="motor-list" class="motor-list"></div><div class="motor-foot"><span>Outputs are simulator values only.</span><span class="mono" id="thrust-total">TOTAL 0.00 N</span></div></section>
        <section class="panel tuning-panel"><div class="panel-head"><div><p class="eyebrow">CONTROLLER</p><h2>Rate PID + Angle outer loop</h2></div><span class="tiny-label">LOCAL ONLY</span></div><div class="pid-grid" id="pid-grid"><div class="pid-head"><span>AXIS</span><span>Kp</span><span>Ki</span><span>Kd</span></div><div class="pid-row"><strong>ROLL</strong><input data-axis="roll" data-key="kp" type="number" step="0.01" value="0.18"><input data-axis="roll" data-key="ki" type="number" step="0.01" value="0.045"><input data-axis="roll" data-key="kd" type="number" step="0.001" value="0.012"></div><div class="pid-row"><strong>PITCH</strong><input data-axis="pitch" data-key="kp" type="number" step="0.01" value="0.18"><input data-axis="pitch" data-key="ki" type="number" step="0.01" value="0.045"><input data-axis="pitch" data-key="kd" type="number" step="0.001" value="0.012"></div><div class="pid-row"><strong>YAW</strong><input data-axis="yaw" data-key="kp" type="number" step="0.01" value="0.16"><input data-axis="yaw" data-key="ki" type="number" step="0.01" value="0.035"><input data-axis="yaw" data-key="kd" type="number" step="0.001" value="0.008"></div></div><div class="parameter-grid"><div><p class="eyebrow">CHANNEL MAP</p><div class="map-grid"><label>ROLL<select data-map="roll"><option value="0" selected>CH1</option><option value="1">CH2</option><option value="2">CH3</option><option value="3">CH4</option><option value="4">CH5</option></select></label><label>PITCH<select data-map="pitch"><option value="0">CH1</option><option value="1" selected>CH2</option><option value="2">CH3</option><option value="3">CH4</option><option value="4">CH5</option></select></label><label>THROTTLE<select data-map="throttle"><option value="0">CH1</option><option value="1">CH2</option><option value="2">CH3</option><option value="3" selected>CH4</option><option value="4">CH5</option></select></label><label>YAW<select data-map="yaw"><option value="0">CH1</option><option value="1">CH2</option><option value="2" selected>CH3</option><option value="3">CH4</option><option value="4">CH5</option></select></label></div></div><div><p class="eyebrow">PHYSICS / ANGLE ESTIMATES</p><div class="physics-grid"><label>MASS (KG)<input data-config="mass_kg" type="number" step="0.1" value="2.2"></label><label>ARM (M)<input data-config="arm_radius_m" type="number" step="0.01" value="0.34"></label><label>MAX THRUST (N)<input data-config="max_motor_thrust_n" type="number" step="0.5" value="12"></label><label>MOTOR LAG (S)<input data-config="motor_time_constant_s" type="number" step="0.01" value="0.08"></label><label>YAW MIX GAIN<input data-config="yaw_mix_gain" type="number" step="0.1" value="1"></label><label>LINEAR DRAG<input data-config="linear_drag" type="number" step="0.01" value="0.18"></label><label>ANGULAR DRAG<input data-config="angular_drag" type="number" step="0.01" value="0.12"></label><label>MAX TILT (DEG)<input data-config="max_angle_deg" type="number" step="1" value="45"></label><label>ANGLE RESPONSE<input data-config="angle_response" type="number" step="0.1" value="4"></label></div></div></div><p class="calibration-note"><span class="accent-line"></span>Airframe mass, inertia and propulsion values are initial estimates. Calibrate against measured hardware before drawing flight conclusions.</p></section>
    </main>
    <footer class="footer"><span>ARTEMIS / SIMULATOR V1.0</span><span>Tarot Iron Man 680 · SpeedyBee F405 V5 · Betaflight telemetry</span></footer>
  </div>
`;

function el<T extends HTMLElement>(selector: string): T {
  return document.querySelector<T>(selector)!;
}

document.querySelectorAll<HTMLSelectElement>('[data-map]').forEach((select) => {
  const selected = select.value;
  select.innerHTML = channelOptions;
  select.value = selected;
});
const configBounds: Record<string, [number, number]> = {
  mass_kg: [0.2, 50],
  arm_radius_m: [0.06, 2],
  max_motor_thrust_n: [0.5, 100],
  motor_time_constant_s: [0.01, 2],
  yaw_mix_gain: [0.01, 5],
  linear_drag: [0, 5],
  angular_drag: [0, 5],
  max_angle_deg: [1, 80],
  angle_response: [0.1, 20],
};
document.querySelectorAll<HTMLInputElement>('[data-config]').forEach((input) => {
  const bounds = configBounds[input.dataset.config ?? ''];
  if (bounds) [input.min, input.max] = bounds.map(String);
  input.step = 'any';
  input.required = true;
});
document.querySelectorAll<HTMLInputElement>('.pid-row input').forEach((input) => {
  input.min = '0';
  input.max = '10';
  input.step = 'any';
  input.required = true;
});

function initScene(): void {
  const wrap = el<HTMLDivElement>('#scene-wrap');
  scene = new THREE.Scene();
  scene.background = new THREE.Color('#12191d');
  camera = new THREE.PerspectiveCamera(35, wrap.clientWidth / wrap.clientHeight, 0.1, 100);
  camera.position.set(1.2, 1.0, 1.55);
  camera.lookAt(0, 0, 0);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  const resizeScene = (): void => {
    const aspect = wrap.clientWidth / wrap.clientHeight;
    const zoomOut = 1 + Math.max(0, 1.15 - aspect) * 1.1;
    camera.aspect = aspect;
    camera.position.set(1.2 * zoomOut, 1.0 * zoomOut, 1.55 * zoomOut);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  };
  resizeScene();
  wrap.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight('#e9f4ed', '#25313a', 2.5));
  const key = new THREE.DirectionalLight('#d9ff65', 3.8);
  key.position.set(2, 3, 4);
  key.castShadow = true;
  scene.add(key);
  const grid = new THREE.GridHelper(2.2, 12, '#33433d', '#1d292b');
  grid.rotation.x = 0;
  grid.position.y = -0.16;
  scene.add(grid);

  aircraft = new THREE.Group();
  const center = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.08, 6), new THREE.MeshStandardMaterial({ color: '#d9ff65', metalness: 0.65, roughness: 0.28 }));
  aircraft.add(center);
  const armGeometry = new THREE.BoxGeometry(0.65, 0.035, 0.045);
  const armMaterial = new THREE.MeshStandardMaterial({ color: '#c8d2cc', metalness: 0.8, roughness: 0.26 });
  const rotorGeometry = new THREE.TorusGeometry(0.12, 0.009, 8, 32);
  const rotorMaterial = new THREE.MeshStandardMaterial({ color: '#ff9566', emissive: '#5d2617', emissiveIntensity: 0.25 });
  const rotorPositions = [[0.30, 0.52], [0.30, -0.52], [-0.30, 0.52], [-0.30, -0.52], [0.60, 0], [-0.60, 0]];
  rotorPositions.forEach(([x, z], index) => {
    const arm = new THREE.Mesh(armGeometry, armMaterial);
    const angle = Math.atan2(z, x);
    arm.rotation.y = -angle;
    arm.position.set(x / 2, 0, z / 2);
    aircraft.add(arm);
    armMeshes.push(arm);
    const rotor = new THREE.Mesh(rotorGeometry, rotorMaterial.clone());
    rotor.position.set(x, 0.04, z);
    rotor.rotation.x = Math.PI / 2;
    rotor.userData.motor = index;
    aircraft.add(rotor);
    rotorMeshes.push(rotor);
  });
  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.18, 4), new THREE.MeshStandardMaterial({ color: '#ff9566', metalness: 0.25, roughness: 0.38 }));
  nose.rotation.x = -Math.PI / 2;
  nose.position.set(0, 0.04, -0.12);
  aircraft.add(nose);
  scene.add(aircraft);
  window.addEventListener('resize', resizeScene);
  const animate = (): void => {
    rotorMeshes.forEach((rotor, index) => {
      // A stopped motor must produce a stopped rotor in the visual model.
      // The old fixed per-frame increment made the aircraft look like it was
      // spinning even with throttle at its idle cutoff.
      rotor.rotation.z += (state.motor_outputs[index] ?? 0) * 0.22;
      const material = rotor.material as THREE.MeshStandardMaterial;
      material.emissiveIntensity = 0.15 + (state.motor_outputs[index] ?? 0) * 0.7;
    });
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  };
  animate();
}

function render(): void {
  const [roll, pitch, yaw] = state.attitude_deg;
  // The simulator body frame uses x=forward, y=right, z=up. The mesh uses
  // local -Z as forward, +X as right, and +Y as up, so body roll maps to
  // mesh Z and body pitch maps to mesh X.
  aircraft.rotation.set(
    THREE.MathUtils.degToRad(-pitch),
    THREE.MathUtils.degToRad(-yaw),
    THREE.MathUtils.degToRad(roll),
    'YXZ',
  );
  el('#roll-readout').textContent = `${roll.toFixed(1)}°`;
  el('#pitch-readout').textContent = `${pitch.toFixed(1)}°`;
  el('#yaw-readout').textContent = `${yaw.toFixed(1)}°`;
  el('#roll-rate').textContent = `${state.angular_velocity_deg_s[0].toFixed(1)}°/s`;
  el('#pitch-rate').textContent = `${state.angular_velocity_deg_s[1].toFixed(1)}°/s`;
  el('#yaw-rate').textContent = `${state.angular_velocity_deg_s[2].toFixed(1)}°/s`;
  el('#sim-time').textContent = `${state.sim_time.toFixed(3)} s`;
  el('#sim-clock').textContent = `T+${state.sim_time.toFixed(3).padStart(6, '0')}`;
  el('#run-label').textContent = state.running ? 'RUNNING' : 'PAUSED';
  el('#input-label').textContent = state.input_mode.toUpperCase();
  document.querySelectorAll<HTMLButtonElement>('.flight-mode-button').forEach((button) => {
    const active = button.dataset.controlMode === state.control_mode;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  const target = el<HTMLParagraphElement>('#angle-target');
  if (controlModeNotice) {
    target.textContent = controlModeNotice;
  } else if (state.control_mode === 'angle' && state.target_attitude_deg) {
    target.textContent = `TARGET R ${state.target_attitude_deg[0].toFixed(1)}°  /  P ${state.target_attitude_deg[1].toFixed(1)}°  ·  yaw rate`;
  } else {
    target.textContent = 'Roll / pitch sticks command angular rate';
  }
  el('#system-label').textContent = state.serial.connected ? 'F405 LINK ONLINE' : 'BACKEND ONLINE';
  document.querySelectorAll<HTMLButtonElement>('.mode-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.mode === state.input_mode);
  });
  el<HTMLButtonElement>('#record-button').textContent = state.recording ? 'STOP' : 'RECORD';
  const connectButton = el<HTMLButtonElement>('#connect-button');
  connectButton.textContent = state.serial.connected ? 'DISCONNECT' : 'CONNECT';
  connectButton.classList.toggle('button-primary', !state.serial.connected);
  el<HTMLSpanElement>('#system-dot').className = `status-dot ${state.serial.connected ? 'is-live' : 'is-ready'}`;
  const badge = el('#flight-badge');
  badge.textContent = state.failsafe ? 'FAILSAFE' : state.running ? 'SIM ACTIVE' : 'PAUSED';
  badge.className = `badge ${state.failsafe ? 'badge-warn' : 'badge-good'}`;
  el('#rc-health').textContent = state.rc_valid && !state.failsafe ? 'SIGNAL OK' : 'NO SIGNAL';
  const serialLabel = el<HTMLSpanElement>('#serial-label');
  serialLabel.textContent = state.serial.connected
    ? state.serial.port ?? 'USB connected'
    : serialNotice ?? state.serial.last_error ?? 'No serial bridge';
  serialLabel.classList.toggle('is-error', Boolean(!state.serial.connected && (serialNotice || state.serial.last_error)));
  el('#replay-label').textContent = state.replay_loaded ? 'Replay ready' : 'No replay loaded';
  const config = state.config as Record<string, number>;
  document.querySelectorAll<HTMLSelectElement>('[data-map]').forEach((select) => {
    const axis = select.dataset.map as keyof Snapshot['channel_mapping'] | undefined;
    if (axis) select.value = String(state.channel_mapping[axis]);
  });
  document.querySelectorAll<HTMLInputElement>('[data-config]').forEach((input) => {
    const key = input.dataset.config;
    if (key && key in config) input.value = String(config[key]);
  });
  const stickMapping = { 'roll-stick': 'roll', 'pitch-stick': 'pitch', 'throttle-stick': 'throttle', 'yaw-stick': 'yaw' } as const;
  for (const [id, axis] of Object.entries(stickMapping)) {
    const stick = el<HTMLInputElement>(`#${id}`);
    stick.disabled = state.input_mode !== 'virtual';
    const channel = state.channel_mapping[axis];
    stick.value = String(state.input_mode === 'virtual' ? virtualChannels[channel] : state.rc_channels[channel]);
  }
  renderChannels();
  renderMotors();
}

function channelsFromSticks(): number[] {
  const channels = Array(16).fill(1500) as number[];
  const axes = [
    ['roll-stick', 'roll'],
    ['pitch-stick', 'pitch'],
    ['throttle-stick', 'throttle'],
    ['yaw-stick', 'yaw'],
  ] as const;
  for (const [id, axis] of axes) {
    channels[state.channel_mapping[axis]] = Number(el<HTMLInputElement>(`#${id}`).value);
  }
  return channels;
}

function resetVirtualSticks(): void {
  el<HTMLInputElement>('#roll-stick').value = '1500';
  el<HTMLInputElement>('#pitch-stick').value = '1500';
  el<HTMLInputElement>('#throttle-stick').value = '1000';
  el<HTMLInputElement>('#yaw-stick').value = '1500';
  virtualChannels = channelsFromSticks();
}

function renderChannels(): void {
  const channels = state.rc_channels.slice(0, 8);
  const names = ['CH1 / ROLL', 'CH2 / PITCH', 'CH3 / YAW', 'CH4 / THROTTLE', 'AUX 1', 'AUX 2', 'AUX 3', 'AUX 4'];
  el('#channel-list').innerHTML = channels.map((value, index) => `<div class="channel-row"><span>${names[index]}</span><div class="channel-track"><i style="width:${Math.max(0, Math.min(100, ((value - 1000) / 1000) * 100))}%"></i><em style="left:${Math.max(0, Math.min(100, ((value - 1000) / 1000) * 100))}%"></em></div><b>${value}</b></div>`).join('');
}

function renderMotors(): void {
  const total = state.motor_thrusts.reduce((sum, value) => sum + value, 0);
  el('#thrust-total').textContent = `TOTAL ${total.toFixed(2)} N`;
  el('#motor-list').innerHTML = state.motor_outputs.map((value, index) => `<div class="motor-card"><div class="motor-label"><span>M${index + 1}</span><strong>${(value * 100).toFixed(1)}%</strong></div><div class="motor-gauge"><i style="height:${Math.max(2, value * 100)}%"></i></div><small>${state.motor_thrusts[index].toFixed(2)} N</small></div>`).join('');
}

async function api(path: string, options?: RequestInit): Promise<Response> {
  return fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
}

async function refreshPorts(): Promise<void> {
  try {
    const response = await api('/api/ports');
    if (!response.ok) throw new Error(`Port scan failed (${response.status})`);
    const body = await response.json() as { ports: Array<{ device: string; description: string }> };
    const select = el<HTMLSelectElement>('#port-select');
    const selected = select.value;
    select.innerHTML = '<option value="">Select F405 USB port</option>' + body.ports.map((port) => `<option value="${port.device}">${port.device} · ${port.description}</option>`).join('');
    if (body.ports.some((port) => port.device === selected)) select.value = selected;
  } catch {
    el<HTMLSelectElement>('#port-select').innerHTML = '<option value="">Backend unavailable</option>';
  }
}

async function responseError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json() as { detail?: unknown };
    if (typeof body.detail === 'string' && body.detail.length > 0) return body.detail;
  } catch {
    // Use the fallback when the server did not return JSON.
  }
  return fallback;
}

function bindControls(): void {
  document.querySelectorAll<HTMLButtonElement>('.flight-mode-button').forEach((button) => button.addEventListener('click', async () => {
    const mode = button.dataset.controlMode;
    if (mode !== 'rate' && mode !== 'angle') return;
    button.disabled = true;
    controlModeNotice = null;
    render();
    try {
      const response = await api('/api/control-mode', { method: 'POST', body: JSON.stringify({ mode }) });
      if (!response.ok) throw new Error(await responseError(response, `Mode change failed (${response.status})`));
      state = await response.json() as Snapshot;
    } catch (error) {
      controlModeNotice = error instanceof Error ? error.message : 'Could not change simulator mode';
    } finally {
      button.disabled = false;
      render();
    }
  }));
  el('#connect-button').addEventListener('click', async () => {
    if (state.serial.connected) {
      try {
        const response = await api('/api/serial/disconnect', { method: 'POST' });
        if (response.ok) {
          state = await response.json() as Snapshot;
          serialNotice = null;
        } else {
          serialNotice = await responseError(response, `Disconnect failed (${response.status})`);
        }
      } catch {
        serialNotice = 'Backend unavailable';
      }
      render();
      return;
    }

    const select = el<HTMLSelectElement>('#port-select');
    if (!select.value) {
      await refreshPorts();
      serialNotice = select.value ? null : 'Select the F405 USB port first';
      render();
      return;
    }

    serialNotice = 'Connecting…';
    render();
    try {
      const response = await api('/api/serial/connect', { method: 'POST', body: JSON.stringify({ port: select.value }) });
      if (response.ok) {
        state = await response.json() as Snapshot;
        serialNotice = null;
      } else {
        serialNotice = await responseError(response, `Connection failed (${response.status})`);
      }
    } catch {
      serialNotice = 'Backend unavailable';
    }
    render();
  });
  document.querySelectorAll<HTMLButtonElement>('.mode-button').forEach((button) => button.addEventListener('click', async () => {
    const mode = button.dataset.mode;
    if (!mode) return;
    if (mode === 'virtual') resetVirtualSticks();
    const response = mode === 'virtual'
      ? await api('/api/input/virtual', { method: 'POST', body: JSON.stringify({ channels: virtualChannels }) })
      : await api('/api/input/mode', { method: 'POST', body: JSON.stringify({ mode }) });
    if (response.ok) state = await response.json() as Snapshot;
    document.querySelectorAll('.mode-button').forEach((item) => item.classList.toggle('active', item === button));
    render();
  }));
  [['start-button', 'start'], ['pause-button', 'pause'], ['reset-button', 'reset']].forEach(([id, action]) => el(`#${id}`).addEventListener('click', async () => {
    const response = await api(`/api/simulation/${action}`, { method: 'POST' });
    if (response.ok) state = await response.json() as Snapshot;
    render();
  }));
  el('#record-button').addEventListener('click', async () => {
    if (!state.recording) {
      const response = await api('/api/record/start', { method: 'POST' });
      if (response.ok) state = await response.json() as Snapshot;
    } else {
      const response = await api('/api/record/stop', { method: 'POST' });
      if (response.ok) {
        const blob = await response.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'artemis-rc-recording.csv';
        link.click();
        state.recording = false;
      }
    }
    render();
  });
  el<HTMLInputElement>('#replay-file').addEventListener('change', async (event) => {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    const response = await api('/api/replay', { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: await file.text() });
    if (response.ok) {
      state.replay_loaded = true;
      state.input_mode = 'replay';
      render();
    }
  });
  [['roll-stick', 'roll'], ['pitch-stick', 'pitch'], ['throttle-stick', 'throttle'], ['yaw-stick', 'yaw']].forEach(([id]) => el<HTMLInputElement>(`#${id}`).addEventListener('input', () => {
    virtualChannels = channelsFromSticks();
    void api('/api/input/virtual', { method: 'POST', body: JSON.stringify({ channels: virtualChannels }) });
  }));
  document.querySelectorAll<HTMLInputElement>('.pid-row input').forEach((input) => input.addEventListener('change', () => {
    if (!input.reportValidity()) return;
    const axis = input.dataset.axis;
    if (!axis) return;
    const row = input.closest('.pid-row');
    if (!row) return;
    const values = [...row.querySelectorAll<HTMLInputElement>('input')].map((field) => Number(field.value));
    void api('/api/pid', { method: 'POST', body: JSON.stringify({ axis, kp: values[0], ki: values[1], kd: values[2] }) });
  }));
  document.querySelectorAll<HTMLSelectElement>('[data-map]').forEach((select) => select.addEventListener('change', async () => {
    const mapping = Object.fromEntries(
      [...document.querySelectorAll<HTMLSelectElement>('[data-map]')]
        .map((field) => [field.dataset.map ?? '', Number(field.value)]),
    );
    const response = await api('/api/channel-mapping', {
      method: 'POST',
      body: JSON.stringify(mapping),
    });
    if (response.ok) {
      state = await response.json() as Snapshot;
      virtualChannels = channelsFromSticks();
      if (state.input_mode === 'virtual') {
        void api('/api/input/virtual', { method: 'POST', body: JSON.stringify({ channels: virtualChannels }) });
      }
    }
    render();
  }));
  document.querySelectorAll<HTMLInputElement>('[data-config]').forEach((input) => input.addEventListener('change', async () => {
    if (!input.reportValidity()) return;
    const config = Object.fromEntries(
      [...document.querySelectorAll<HTMLInputElement>('[data-config]')]
        .map((field) => [field.dataset.config ?? '', Number(field.value)]),
    );
    const response = await api('/api/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (response.ok) state = await response.json() as Snapshot;
    render();
  }));
}

function connectWebSocket(): void {
  const socket = new WebSocket(WS_API);
  socket.addEventListener('open', () => void refreshPorts());
  socket.addEventListener('message', (event) => {
    state = JSON.parse(event.data) as Snapshot;
    render();
  });
  socket.addEventListener('close', () => window.setTimeout(connectWebSocket, 1500));
}

initScene();
bindControls();
render();
void refreshPorts();
connectWebSocket();
