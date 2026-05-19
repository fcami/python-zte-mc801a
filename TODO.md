# TODO — python-zte-mc801a

This list is the prioritized work to make the watchdog actually catch the carrier-aggregation drop that costs ~80 Mbps of downlink throughput.

## Ordered work items

1. **Add a test harness with recorded router fixtures (gap 7)**
   - Create `tests/fixtures/` containing captured JSON responses for at least: LTE-only, 5G NSA, 5G SA, single-band-stuck-on-B3, full CA.
   - Add `pytest` to dev deps in `setup.py` or `pyproject.toml`.
   - Write the first tests against `daemon._check_lte_bands` and `daemon._check_5g_bands` using the fixtures.
   - Goal: any change to drift logic from here on is gated by tests.

2. **Unify live and watchdog into a single monitor terminal mode (gap 3)**
   - Add a new subcommand in `main.py` that runs the watchdog loop in a background thread/task and drives a Rich layout combining the existing status table with a scrolling pane of cycle-by-cycle check results and remediation actions.
   - Keep the `watchdog` subcommand for headless use.
   - Add a `--once` flag for single-cycle runs useful in cron or ad-hoc verification.

3. **Detect active-band regression, not just lock-mask drift (gap 1)**
   - Add `lib/active_state.py` exposing `get_active_lte_bands(info)` (parses `wan_active_band` + `lte_multi_ca_scell_info`) and `get_active_5g_bands(info)`.
   - Add a new check `_check_active_bands` to `daemon.CHECKS` that fires when the active set is a strict subset of the locked set.
   - Add config keys `min_active_lte_bands` and `min_active_nr5g_bands` with defaults derived from the locked set.

4. **Graduated remediation ladder (gap 5)**
   - Refactor each check from "fix or pass" to a `Remediator` returning a stage: (1) re-apply lock, (2) clear lock + re-apply, (3) cycle band-lock off/on, (4) reboot.
   - Track per-check failure streaks in daemon state; advance one stage per consecutive failure; reset on success.
   - Add a `max_remediation_stage` config key to cap escalation.

5. **Fetch and surface realtime throughput (gap 2)**
   - Extend `router_requests.get_signal_data` (or add a new fetcher) to include `realtime_rx_thrpt`, `realtime_tx_thrpt`, `realtime_rx_bytes`, `realtime_tx_bytes`.
   - Display DL/UL Mbps in the status table and the monitor view.
   - Add `min_dl_mbps` as an additional drift trigger feeding the same remediation ladder.

6. **Log to a rotating file in daemon mode (gap 4)**
   - Add `--log-file` and `--log-level` to the watchdog subcommand; wire up `logging.handlers.RotatingFileHandler`.
   - Default to stdout when unset to preserve current UX.
   - Ship a `contrib/python-zte-mc801a.service` systemd unit example.

7. **Harden the daemon loop (gap 6)**
   - Wrap each cycle in `try/except` for `requests.ConnectionError`, `Timeout`, and auth failure; back off exponentially (cap ~5 min).
   - Re-authenticate on cookie expiry.
   - Emit a single warning per run of consecutive failures rather than once per cycle.

8. **Secret handling beyond plaintext YAML (gap 8)**
   - Accept the password from `$ZTE_MC801A_PASSWORD` and, optionally, the `keyring` library (lazy import, optional dep).
   - Update setup to offer keyring storage; mark plaintext YAML as the fallback.
   - Document in README.

## Future: Rust rewrite

Inspect the sibling `zte-mc801a-cpp/` directory first to decide whether to reuse or supersede it. Target crates: `reqwest`, `serde_json`, `serde_yaml`, `clap` (derive), `ratatui` + `crossterm`, `tokio`, `tracing`. Structure as a Cargo workspace with a `zte-mc801a-core` library crate and a `zte-mc801a` binary crate so the library remains reusable. Port order: router HTTP client first, then drift checks with property tests using the captured Python fixtures, then daemon, then TUI last. Deliverable: a single static binary via `cargo build --release` plus a systemd unit. Rust is preferred over C++ because a long-running daemon wants memory safety, single-binary distribution is trivial with Cargo, and the type system makes "lock mask vs active bands vs Mbps" newtypes natural — advantages C++ only achieves with significant scaffolding.
