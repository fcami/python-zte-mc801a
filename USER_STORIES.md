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

## Epic H — Weather-aware operation

- **H1.** As an operator, I want the watchdog to fetch current weather from a free, no-token-required provider (Open-Meteo at api.open-meteo.com by default, offering current conditions, forecast, archive, and geocoding at a recommended minimum of 1 request per minute), so that I can opt into weather-aware behaviour without signing up for any API account. *(GAP)*
- **H2.** As an operator, I want a second free no-token provider available (MET Norway / Yr.no at api.met.no, requiring only a polite User-Agent header), so that I have a fallback if my primary provider is rate-limited or unreachable. *(GAP)*
- **H3.** As an operator, I configure my location once (lat/lon directly, or a place name resolved via Open-Meteo's free geocoding endpoint), so that weather lookups match my actual install site. *(GAP)*
- **H4.** As an operator, the weather provider is pluggable behind a single interface (fetch_current, fetch_recent), so that swapping or chaining providers is a config change, not a code change. *(GAP)*
- **H5.** As an operator with an OpenWeatherMap or WeatherAPI.com key, I can optionally enable a free-with-token provider as primary or fallback via config, so that I gain richer data when I am willing to manage a key; subscription-only providers are explicitly out of scope. *(GAP)*
- **H6.** As an operator, weather observations are persisted to disk (SQLite under $XDG_STATE_HOME/python-zte-mc801a/weather.db, falling back to ~/.local/state/python-zte-mc801a/weather.db when $XDG_STATE_HOME is unset, with a JSONL fallback when SQLite is unavailable), so that daemon and CLI restarts do not lose history. *(GAP)*
- **H7.** As an operator, the history retention window is configurable (weather.retention_hours, default 48), and rows older than the window are pruned on a periodic sweep rather than on every write, so that the history file does not grow unbounded and stale observations irrelevant to current radio propagation are discarded. *(GAP)*
- **H8.** As an operator, the watchdog computes a rolling "vegetation wetness" estimate from rainfall over the last 12–24 hours combined with current humidity and wind speed, so that decisions correctly treat "rained yesterday but dry and windy now" as effectively dry while "rained 18 hours ago and still humid" correctly reflects drenched-trees attenuation. *(GAP)*
- **H9.** As an operator, the watchdog estimates a "foliage phase" from hemisphere, day-of-year, and recent temperatures (rough buckets: bare / budding / full canopy / shedding), so that the model recognises that summer full-canopy attenuates n78 and B7 more than winter bare branches and is not season-blind. *(GAP)*
- **H10.** As an operator, when the weather model predicts that higher-bandwidth bands are unlikely to hold (heavy continuous rain combined with wet foliage and full-canopy season), the watchdog stops retrying band-forcing after 3 attempts and switches to a weather-watch back-off, so that the radio is not churned against a condition only the weather can resolve. *(GAP)*
- **H11.** As an operator, the weather-vetoed back-off duration is configurable (weather.veto_backoff_minutes, default 30), and the watchdog rechecks weather at that interval before resuming normal cadence, so that operation resumes promptly once conditions improve. *(GAP)*
- **H12.** As an operator, every weather-influenced decision is logged with the inputs that drove it (rainfall_1h, rainfall_12h, humidity, wind_speed, foliage_phase, verdict="attempt"|"defer"), so that I can audit and tune thresholds against my actual install environment. *(GAP)*
- **H13.** As an operator, I can run a CLI weather subcommand and see a --show-weather overlay in the monitor view, both displaying current observations, the rolling rainfall/wetness estimate, the foliage phase, and the watchdog's current verdict, so that I can introspect the model without enabling the daemon. *(GAP)*
- **H14.** As an operator, the daemon functions correctly with no weather provider configured and degrades silently to weather-blind behaviour, so that weather integration is strictly opt-in and existing setups are not broken. *(GAP)*
- **H15.** As an operator, weather fetches respect provider rate limits (minimum 5 minutes between calls for Open-Meteo; minimum 60 seconds for MET Norway, using If-Modified-Since) and are served from the persisted cache between fetches, so that the watchdog's higher-frequency check loop does not hammer the provider. *(GAP)*
- **H16.** As a contributor, the weather decision logic has unit tests driven by synthetic histories (clear-dry-summer, drenched-summer, light-drizzle-winter, post-rain-windy-dry, sustained-heavy-rain), so that threshold tweaks do not silently change veto behaviour. *(GAP)*

## Epic I — Operability and remote debuggability

- **I1.** As an operator running the daemon on my own host, I want the default log output to be detailed enough that the project author can diagnose an issue from the log alone — without ever touching my router or my host — so that bug reports do not require a live debugging session and the project is shippable to people I have never met. *(GAP)*
- **I2.** As an operator filing a bug report, I want all sensitive and identifying values redacted by default in every log line and every diagnostic output (router private IP, WAN public IP, password — never logged at all even redacted, MAC addresses, IMSI, IMEI, MSISDN/phone number, SSID, BSSID, and any auth cookie or token), each replaced by a stable per-run placeholder of the form `<TYPE_N>` (e.g. `<MAC_1>`, `<MAC_2>`, `<WAN_IP>`), so that the relationships between values are preserved while the values themselves never leave my host. *(GAP)*
- **I3.** As an operator debugging on my own host, I can pass `--no-redact` on the CLI (or set `redact: false` in the watchdog config) to see real values, with a single conspicuous warning logged at startup that this mode produces output unsafe to share. Redaction defaults to ON and opting out is always explicit, never implicit. *(GAP)*
- **I4.** As the project author receiving a bug report, I want every outbound HTTP request to the router (method, URL path, redacted request body) and the corresponding response (status code, redacted response body, elapsed time) captured at `DEBUG` level, so that the wire-level interaction with the router can be reconstructed remotely without my own MC801A and without `tcpdump` access to the operator's host. *(GAP)*
- **I5.** As an operator filing a bug, I can run a `report` subcommand that produces a structured, redacted, ready-to-paste diagnostic report grouped into sections — `Environment`, `Versions`, `Configuration summary`, `Recent HTTP transcript`, `Recent decisions`, `Last error` — in GitHub-flavoured Markdown with `<details>` collapsibles for the long sections, so that filing an issue is one command and produces output the maintainer can read at a glance. *(GAP)*
- **I6.** As the project author triaging a report, I want every report to include the tool version, Python version, OS string, router firmware version (`wa_inner_version`), and a redaction-map summary (each placeholder type followed by the *count* of distinct values it stood for, never the values themselves), so that I can tell `<MAC_1>` and `<MAC_2>` are different devices without learning what they are, and so that version-skew issues are diagnosable from the report alone. *(GAP)*
- **I7.** As a contributor, I want tests that assert the redaction layer replaces every sensitive value in a known-leaky synthetic payload (containing an RFC1918 IP, a public IPv4, a password, a MAC, an IMSI, an IMEI, an MSISDN, an SSID, a BSSID, and an auth cookie), and that `--no-redact` mode emits the originals, so that no future change to logging or reporting code can silently leak secrets. *(GAP)*

## Sequencing recommendation

D2, A3, and C1 are the heart of the operator's goal and share a dependency on active-band and throughput helpers, so they should be developed together as a single foundational slice. G1 should land alongside D2 because drift-detection logic decays quickly without test coverage. D3 and D4 unblock real home-service deployment and can follow once the detection loop is solid. D5 is the most ambitious remediation story and should wait until D2 has been validated on real hardware. Weather-aware operation (Epic H) is a parallel track that depends only on persistence and a HTTP client and can land independently of the drift-detection work, with H1, H6, H10, and H14 as the minimum viable slice. Epic I (operability and remote debuggability) is a parallel track that depends only on a logging refactor and a small HTTP transcript hook; the minimum viable slice for "shippable to a stranger" is I2 + I3 + I5 + I7, and it can land independently of the drift, throughput, and weather work.
