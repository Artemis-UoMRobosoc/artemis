# Artemis Weekly Plan

**University of Manchester Robotics Society · 2026–27**

**Updated: 11 October 2026**

Artemis aims to build and improve a drone that the team can understand, maintain and use for control experiments. Control development provides the starting point, with routes into visual navigation and learning-based control as the platform and interfaces mature.

The summer-built demonstration aircraft is an ESP32-based quadcopter made by the project leader. The current team platform is the society's existing hexacopter with a **SpeedyBee F405 V5**. The decision to reuse it, made on 30 September, supersedes the earlier proposal to select and buy a new team aircraft.

**Current progress:** on 10 October, the leader reported successful motor-speed control and dispatch of a battery. The tested motor channels, reliable stopping and flight acceptance still require records. The battery is **shipped / awaiting receipt**; its specification, quantity and arrival date remain unrecorded. On 11 October, a radio package was recommended; it has **not been ordered**.

## Intended outcomes and organisation

After 24 active weeks, the project aims to have:

- A working drone with repeatable controlled flight.
- Tested control algorithms and a comparison of their performance.
- Clearly distinguished simulation and flight-test records.
- Versioned code, controller settings, wiring and a bill of materials.

These are targets. A plan, simulation or individual bench test does not establish completion of the platform.

The team has a maximum of **ten people including the leader**. Sessions run for **three hours each Wednesday**, over two twelve-week teaching semesters. Extra work is optional. Roles develop from contributions, with useful starting tasks for beginners and opportunities to work across interfaces.

| Workstream | First contribution | Later direction |
| --- | --- | --- |
| Flight platform and control | Identify and test hardware; establish reproducible control and radio setups | Controller development and repeatable flight experiments |
| Vision and state estimation | Reproduce a dataset or camera/IMU experiment with timestamps and validity information | Integrate usable state estimates with flight control |
| Simulation and learning | Establish a conventional controller and fixed test conditions | Compare a selected learning method against that baseline |

Each task needs an owner, an output, evidence and a next action if blocked. The leader coordinates integration and critical decisions; team members also own measurements, photographs, software reproduction and records.

## 24-week roadmap

Weeks count active sessions, excluding the semester break. Later stages will be revised as measured progress changes the scope.

| Weeks | Planned work | Target |
| --- | --- | --- |
| W1–2 | Run a taster session, review sign-ups, agree roles, inspect the existing platform, identify necessary parts and arrange a flight-cage booking | Initial team, experiments and purchase list |
| W3–6 | Restore the platform and fly after the required checks and booking; test radio links, collect data and explore STM32 on the bench | Repeatable flight; radio and data tests |
| W7–12 | Improve control, integrate hardware and sensing, and compare results | Reliable flight and a tested control baseline |
| W13–18 | Study selected control methods, including reinforcement learning; train and test in simulation; explore visual navigation if resources allow | A working research experiment and initial results |
| W19–20 | Compare algorithms under the same conditions and review errors and failures | Recorded comparison and final scope |
| W21–24 | Repeat tests, fix issues and organise code and hardware records | Tested algorithms, flight results and complete records |

## Preparation — September 2026

| Date | Preparation and outcome |
| --- | --- |
| 17 September | Established the 24-week schedule and parallel hardware, vision and control work. STM32 and an independent radio link were considered for teaching and maintenance. |
| 20–21 September | Prepared a state-feedback browser exercise and revised W1 into a propeller-free inspection and discussion session. The exercise was a teaching demonstration, not an aircraft controller or flight result. |
| 24 September | Defined a marker-detection experiment sending timestamped image offsets over UART, with correctness, rate, delay and failure checks. A visual flight-control loop had not been implemented. |
| 25 September | Confirmed an owned Raspberry Pi Zero 2 W as the preferred first vision bench platform. A separately owned bare H747 chip was not a ready flight controller. Power, payload, latency and interfaces remained unverified. Prepared the project introduction and raised reuse of the society hexacopter. |
| 28–29 September | Investigated recovery costs, wiring and component references. Candidate Tarot parts and illustrations did not identify the components actually installed. |

## W1 — 30 September 2026

### Intended session

Run an open taster with the summer-built drone and browser demonstration, then discuss interests and possible contributions. No prior control theory is required. Times begin after the society introduction and can be compressed.

| Time | Activity |
| --- | --- |
| 0–30 min | Introduce the project; inspect the demonstration drone with propellers removed, including hardware, code and possible improvements |
| 30–60 min | Explain feedback and basic control; discuss how controllers and parameters affect flight |
| 60–80 min | Predict and compare responses in the browser exercise; briefly introduce LQR, leaving mathematics for later |
| 80–110 min | Discuss an improvement in small groups and share hardware, coding and control interests |
| Remaining time | Continue inspection and questions, explain sign-up and collect interest |

Live flight was outside the W1 plan. Flying requires a confirmed cage booking and checked setup. Demonstrating the browser exercise does not establish that LQR runs on the drone.

### Confirmed developments

- **30 September:** selected the existing hexacopter and F405 V5 for recovery, replacing the earlier H743 wiring proposal. USB identification and sensor readback succeeded; configuration and resource mappings were backed up. The recorded setup was **Betaflight 4.5.2 / QUADX / DShot600**. This backup was neither a complete flash image nor a tested restoration procedure.
- **1 October, reported 2 October:** new members joined and the team started work. Attendance and roles still needed complete records. Team launch does not establish that every taster activity occurred.

Carry forward small, concrete tasks: number and photograph the six motor/ESC sets, sketch unpowered PDB connections, reproduce USB sensor readback and identify missing equipment. The planning records did not confirm a flight-cage booking.

## W2 — 7 October 2026

**Planned session: 14:00–17:00.** The leader confirmed availability of the existing hexacopter, F405 and computer. The objective was to identify reusable parts, resolve missing power/control connections and decide necessary purchases.

### Starting facts

- The frame appeared to belong to the **Tarot 680 family**, and the PDB was possibly a **TL6X002**; both identities remained tentative.
- Labels reported on 7 October identified an **AIKON Electronics AK32 35A, 2–6S** ESC and a motor marked **4S / 4006 / 620KV**. The session plan used 4S as its starting point while requiring checks of all six sets, ESC firmware, pin order, BEC arrangements and protocol. This does not identify the battery later dispatched.
- The recorded F405 configuration remained **Betaflight 4.5.2 / QUADX / DShot600**, with MOTOR 5/6 unassigned. M1–M4 plus S5/S6 was a proposed six-output ArduPilot arrangement, not a verified configuration on the board.
- Radio equipment, suitable battery, charger, signal source and available tools required inventory checks. Having instrument documentation did not establish that the instruments were present.

### Intended hardware work

| Time | Task and evidence to retain |
| --- | --- |
| 14:00–14:20 | Remove propellers, photograph original wiring, label the front and six arms, read component labels and inventory equipment. Keep six numbered sets, matching photos and explicit unknowns. |
| 14:20–14:45 | With power disconnected, check polarity and continuity. Isolate motor power, read F405 settings over USB and compare the backup. Measure unloaded supply outputs only after rating and wiring checks. Save a connection map and measured results. |
| 14:45–15:25 | Measure the control signal and test one secured, propeller-free motor/ESC with a compatible source and supply. Record commanded start, low-speed operation and stop, including protocol, waveform and supply. |
| 15:25–16:10 | Use the reference combination to assess other units and trace F405 signal wiring. Record Pass / Fail / Untested per set and test a controller output only after compatibility checks. |
| 16:10–16:30 | With motor power isolated, identify and pair actual radio equipment and inspect channel responses. Optionally check phone-to-F405 Bluetooth configuration connectivity. Record these links separately. |
| 16:30–17:00 | Consolidate evidence and purchases, with specifications, quantities, reasons, owners and next dates for unresolved items. |

The hardware group handles identification and individual tests; the signal/control group handles waveforms, configuration and radio; a recorder consolidates evidence. Roles can combine with smaller attendance. During powered testing, nobody else changes that setup's wiring; parallel work uses isolated hardware or documentation.

Procedures and hardware references belong in the [technical reference](technical-reference.md). Continuity alone does not prove high-current suitability. A stationary motor does not automatically indicate a faulty motor, and one successful channel does not prove six-channel integration.

### Confirmed results and later updates

- **7 October:** the leader supplied the ESC and motor labels above and confirmed that introduction-slide photos were complete.
- **10 October:** the leader confirmed control of motor speed. The motor/ESC/channel, wiring, firmware/protocol, supply and command range still need recording. Six-channel operation, repeatable stopping and flight remain unconfirmed.
- **10 October:** a battery was reported dispatched. Receipt and suitability for this aircraft remain unconfirmed.
- **10–11 October:** ESP32 internal-radio/ExpressLRS research was separated from aircraft recovery. An owned **CrowPanel ESP32-S3** and **Nooelec NESDR SMArt v5** can support experimental work, including a separate 868 MHz recording experiment. No ELRS transmitter, module or receiver is owned. These research plans do not replace a proven aircraft control link; hardware trials have not been completed.

## Purchasing follow-up — 11 October 2026

Classify items as **Reuse**, **Confirmed buy** or **Hold**. A confirmed purchase decision requires an exact compatible specification, quantity, justification, delivered price and funding basis. Existing hardware must retain its actual testing status. Record an owner and next date for every unresolved item.

| Item | Current status | Next action |
| --- | --- | --- |
| Flight battery | **Shipped / awaiting receipt**; quantity unknown | Confirm model, chemistry, cell count, capacity, connector, quantity, destination and arrival date; check compatibility. Identify this shipment before considering another order. |
| Balance charger and leads | **Inventory check; buy only if missing** | Check borrowing/reuse options and match the main and balance leads to the dispatched battery. |
| Radio and handset power | **Recommended, not ordered**: 1 RadioMaster Pocket **ELRS 2.4 GHz**, 1 **RP1 V2** receiver, 2 compatible 18650 cells | Recorded quotation: **£102.47 including VAT, excluding delivery**. Confirm delivered price, funding, firmware/domain pairing and any compatible cells already available. Reuse a verified 5 V bench supply or identify the missing power breakout. |
| Wiring, connectors, insulation and mounts | **List actual shortages** | Measure missing ends, wire sizes, lengths and quantities before buying. |
| Replacement motor, ESC or PDB | **No confirmed replacement requirement** | Identify a fault or documented incompatibility before adding a replacement. |
| Test equipment | **Borrow / check availability first** | Verify suitability of available signal sources, supplies and measurement tools. |
| Current sensor | **Deferred** | Establish monitoring requirements and compatibility; HCS-150A remains an earlier candidate. |
| Camera, Pi accessories, navigation, video or gripper parts | **Later scope** | Reuse owned hardware and define the experiment, interfaces, power and approved budget first. |

The revised funding total and reimbursement conditions remain unrecorded. Battery dispatch does not establish other purchases. The next radio review should check the three recommended items, available accessories and delivered cost; no radio order has been placed.

Radio quotation sources recorded on 10–11 October: [Pocket ELRS (£71.49)](https://www.hobbyrc.co.uk/radiomaster-pocket-transmitter-elrs-charcoal), [RP1 V2 (£18.99)](https://www.hobbyrc.co.uk/radiomaster-rp1-elrs-receiver) and [two 3200 mAh 18650 cells (£11.99)](https://www.hobbyrc.co.uk/radiomaster-3200mah-18650-cells-2pcs). These are dated quotations, not a current stock or price guarantee. Select the ELRS version of the handset, and verify the actual receiver revision and firmware before setup.

At the next session, reproduce and document the reported speed-control result, complete hardware identification and isolated PDB measurements, reproduce USB readback and consolidate purchasing evidence. End with owners and dates for unresolved items, within the shared session time.
