# Artemis — Project Overview

**University of Manchester Robotics Society · 2026–27**

Artemis is a student drone project combining practical engineering with experiments in control, sensing and autonomy. Our aim is to build a platform the team can understand, maintain and improve, while sharing what we learn through reproducible experiments.

## Project documents

- [Weekly Plan](weekly-plan.md) — roadmap, weekly activities, progress and purchasing follow-up.
- [Technical Reference](technical-reference.md) — existing hardware, manuals, pin map, wiring checks and test records.
- [Tarot 680 Simulator](simulator/README.md) — setup, RC input, controls, recording and simulation limits.

This README is a general introduction. Dated progress and technical updates belong in the Weekly Plan and Technical Reference; simulator setup and operation are documented in the simulator guide.

## Current work

As of 10 October 2026, the team has started work and is assessing an existing society hexacopter for reuse with a SpeedyBee F405 V5 flight controller.

USB communication and sensor readback have been demonstrated, and the flight-controller configuration has been backed up. Our immediate focus is checking power distribution, motor and electronic speed controller (ESC) connections, control signals and the radio link. The hexacopter has not yet completed motor-system or flight acceptance.

An existing ESP32-based demonstration quadcopter provides another starting point for learning and discussion. Its previous flight demonstration is separate from the hexacopter restoration work.

## Workstreams

| Area | Initial focus | Longer-term direction |
| --- | --- | --- |
| Flight platform and control | Restore the hardware, verify interfaces and establish repeatable tests | Controller development, radio integration and flight experiments |
| Vision and state estimation | Explore recorded datasets, calibration and camera/IMU measurements | Visual-inertial estimation and integration with the flight controller |
| Simulation and learning | Build a conventional control baseline and record its performance | Compare selected learning-based methods under the same test conditions |

We are also investigating ESP32 software-defined radio and ExpressLRS as an exploratory communications topic. Direct ELRS operation using the ESP32 internal radio remains a research question, not a demonstrated project capability.

## Goals

Our first priority is a working platform with repeatable controlled flight. We then aim to:

- Measure and compare control performance under defined conditions.
- Keep useful records of configurations, wiring, test results and failures.
- Develop reproducible simulation experiments before considering hardware deployment.
- Explore visual navigation and learning-based control when the platform, interfaces and resources support them.

Each experiment should have a clear question, a baseline and a result that another member can reproduce. Simulation results, bench tests and flight demonstrations will be reported separately. Flight sessions depend on a checked setup and a confirmed suitable test area.

## Taking part

We plan to work together for three hours on Wednesdays across two teaching semesters. Extra work is optional.

Students interested in mechanical design, electronics, embedded systems, radio, software, control, computer vision or testing are welcome. Beginners can contribute through assembly, data collection, configuration, analysis and documentation, then take ownership of a module as their experience grows.

Each member should have a clear contribution, with time for the team to explain results and combine its work. Early tasks will focus on small, useful outputs that help the next person build or test their part of the system.

## Editing the documents

Repository write access is by invitation from the owner. The project limits access to **ten people including the owner**; accepted collaborators and pending invitations share the remaining nine places. Public reading is unrestricted.

After accepting an invitation, create a branch, edit the relevant document and open a pull request to `main`. Browser editing is fine: use the pencil icon on a file, then choose to create a new branch when committing. Keep the change description specific and distinguish plans, reported observations and measured results.

`main` requires at least one approving review and resolved review conversations. New commits that change reviewed content dismiss stale approvals. Force pushes and deletion of `main` are disabled. The owner retains an administrator exception for initial solo maintenance and emergencies; normal team changes follow the review process.

Without write access, readers can suggest a change through a fork and pull request. Opening the repository link does not automatically grant editing access.
