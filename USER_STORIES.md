# User Stories — python-zte-mc801a

This project is a Python library, CLI, and watchdog daemon for the ZTE MC801a 5G CPE router. The operator's primary goal is to keep the modem on its full set of LTE/NR bands, since full carrier aggregation yields roughly 100 Mbps down and 10 Mbps up, while drift to a single band can drop download throughput to around 20 Mbps. The tool is designed to run either as an interactive terminal supervisor showing live status and remediation activity, or as a background daemon writing to a log file.

## Legend

- **DONE** — fully implemented in the current codebase
- **PARTIAL** — some code exists but does not fully meet the story
- **GAP** — not implemented

## Epic A — Core library

- **A1.** As an integrator, I can read router status, signal data, and device info via Python functions. *(DONE)*
- **A2.** As an integrator, I can lock LTE/NR bands, lock a cell, set DNS, set network mode, reboot the router via library calls. *(DONE)*
- **A3.** As an integrator, I can read the currently active aggregated bands (PCell + SCells parsed from lte_multi_ca_scell_info) and the realtime DL/UL throughput (realtime_rx_thrpt, realtime_tx_thrpt) as first-class library outputs. *(GAP)*

## Epic B — One-shot CLI

- **B1.** As an operator, I run a single command to view a comprehensive status table. *(DONE — status)*
- **B2.** As an operator, I run a single command to apply a band lock, cell lock, DNS change, mode change, or reboot. *(DONE)*
- **B3.** As an operator, I see active aggregated bands and current DL/UL Mbps in the status output, not only the lock-mask state. *(GAP)*

## Epic C — Interactive terminal tool (foreground supervisor)

- **C1.** As an operator, I run a single monitor command that combines the live status panel and the watchdog loop in one screen, with cycle-by-cycle output. *(GAP — live and watchdog are separate today)*
- **C2.** As an operator, the live panel highlights when active bands drop below the desired set or DL throughput falls below a threshold, so drift is visible at a glance. *(GAP)*
- **C3.** As an operator, each remediation prints a timestamped before/after line (e.g. "LTE active bands [3] → re-applied lock [3,7,28] → after 5s active bands [3,7]"), so I can confirm the action had an effect. *(GAP)*
- **C4.** As an operator, I can pass --once to run a single check-remediate cycle and exit, for ad-hoc verification or cron use. *(GAP)*

## Epic D — Daemon (background service)

- **D1.** As a sysadmin, I run a long-running daemon that periodically checks for drift and re-applies my desired configuration. *(DONE for lock-mask drift)*
- **D2.** As a sysadmin, the daemon detects active-band regression — fewer aggregated bands than expected, or DL throughput below a threshold — not only lock-mask drift, since the lock can read correct while the radio is stuck on one band. *(GAP — the headline gap)*
- **D3.** As a sysadmin, the daemon writes a structured log file with rotation, configurable via --log-file or YAML, instead of only stdout. *(GAP)*
- **D4.** As a sysadmin, the daemon ships with a systemd unit example and is compatible with journald logging. *(GAP)*
- **D5.** As a sysadmin, the daemon performs graduated remediation: re-apply lock → clear and re-apply lock → cycle the band lock off/on → reboot, escalating only when the previous step did not restore the desired state. *(GAP)*
- **D6.** As a sysadmin, the daemon survives transient router outages (unreachable, auth expired, reboot in progress) with exponential backoff and continues without crashing. *(PARTIAL)*
- **D7.** As a sysadmin, I can run the daemon in --dry-run mode that detects drift and logs what would be done without writing to the router. *(GAP)*

## Epic E — Configuration & secrets

- **E1.** As an operator, I keep router IP and password in settings.yml for convenience. *(DONE)*
- **E2.** As an operator, I can source the router password from an environment variable or system keyring instead of plaintext YAML. *(GAP)*
- **E3.** As an operator, the watchdog config supports thresholds for the new drift signals (e.g. min_active_lte_bands: 2, min_dl_mbps: 50), not only "match this exact lock". *(GAP)*

## Epic F — Observability

- **F1.** As a network nerd, each watchdog cycle appends a JSONL record (timestamp, active bands, DL/UL Mbps, signal levels, remediation taken) to a status file, so I can post-mortem incidents. *(GAP)*
- **F2.** As a network nerd, the daemon optionally exposes a Prometheus textfile or HTTP /metrics endpoint with throughput, signal, and remediation counters. *(GAP — nice-to-have)*

## Epic G — Quality

- **G1.** As a contributor, drift-detection logic has unit tests with fixtures of real router responses (LTE-only, NSA, SA, single-band-stuck, full-CA), so refactors don't silently break it. *(GAP — tests/ is currently empty)*
- **G2.** As a contributor, lint passes (flake8, pylint). *(DONE)*

## Sequencing recommendation

D2, A3, and C1 are the heart of the operator's goal and share a dependency on active-band and throughput helpers, so they should be developed together as a single foundational slice. G1 should land alongside D2 because drift-detection logic decays quickly without test coverage. D3 and D4 unblock real home-service deployment and can follow once the detection loop is solid. D5 is the most ambitious remediation story and should wait until D2 has been validated on real hardware.
