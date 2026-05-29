# TODO — python-zte-mc801a

This list is the prioritized work to make the watchdog actually catch the carrier-aggregation drop that costs ~80 Mbps of downlink throughput.

## Done

- **Active-band regression detection (audit gap 1).** Landed in
  `1ad88b0`. Adds `lib/active_state.py` with `get_active_lte_bands` /
  `get_active_5g_bands` (parses `wan_active_band`, `lte_ca_pcell_band`,
  `lte_multi_ca_scell_info`, `nr5g_action_band`), a new
  `_check_active_bands` daemon check, `min_active_lte_bands` /
  `min_active_nr5g_bands` config keys with defaults derived from the locked
  set and clamped against the locked-band count at config-load time,
  band-0 / negative-value filtering in the parser, and 24 unit tests. Field
  formats are still inferred from `main.py` display code rather than
  verified against a captured payload from a live MC801A — closing that gap
  is the first item below.

## Ordered work items

1. **Add a test harness with recorded router fixtures (gap 7) — NEXT**
   - Create `tests/fixtures/` containing captured JSON responses for at
least: LTE-only, 5G NSA, 5G SA, single-band-stuck-on-B3, full CA.
   - Capture inputs via `python-zte-mc801a data --raw` against the user's
live modem; redact any PII before committing (see Epic I MVS below — the
redaction work may need to land first if fixtures will include sensitive
fields).
   - Port `tests/test_check_active_bands.py` and
`tests/test_active_state.py` to drive at least one assertion per fixture,
so the field-format assumptions made for active-band detection are
verified end-to-end.
   - Goal: any change to drift logic from here on is gated by tests
against real payloads.

2. **Unify live and watchdog into a single monitor terminal mode (gap 3)**
   - Add a new subcommand in `main.py` that runs the watchdog loop in a
background thread/task and drives a Rich layout combining the existing
status table with a scrolling pane of cycle-by-cycle check results and
remediation actions.
   - Keep the `watchdog` subcommand for headless use.
   - Add a `--once` flag for single-cycle runs useful in cron or ad-hoc
verification.

3. **Graduated remediation ladder (gap 5)**
   - Refactor each check from "fix or pass" to a `Remediator` returning a
stage: (1) re-apply lock, (2) clear lock + re-apply, (3) cycle band-lock
off/on, (4) reboot.
   - Track per-check failure streaks in daemon state; advance one stage
per consecutive failure; reset on success.
   - Add a `max_remediation_stage` config key to cap escalation.

4. **Fetch and surface realtime throughput (gap 2)**
   - Extend `router_requests.get_signal_data` (or add a new fetcher) to
include `realtime_rx_thrpt`, `realtime_tx_thrpt`, `realtime_rx_bytes`,
`realtime_tx_bytes`.
   - Display DL/UL Mbps in the status table and the monitor view.
   - Add `min_dl_mbps` as an additional drift trigger feeding the same
remediation ladder.

5. **Log to a rotating file in daemon mode (gap 4)**
   - Add `--log-file` and `--log-level` to the watchdog subcommand; wire
up `logging.handlers.RotatingFileHandler`.
   - Default to stdout when unset to preserve current UX.
   - Ship a `contrib/python-zte-mc801a.service` systemd unit example.

6. **Harden the daemon loop (gap 6)**
   - Wrap each cycle in `try/except` for `requests.ConnectionError`,
`Timeout`, and auth failure; back off exponentially (cap ~5 min).
   - Re-authenticate on cookie expiry.
   - Emit a single warning per run of consecutive failures rather than
once per cycle.

7. **Secret handling beyond plaintext YAML (gap 8)**
   - Accept the password from `$ZTE_MC801A_PASSWORD` and, optionally, the
`keyring` library (lazy import, optional dep).
   - Update setup to offer keyring storage; mark plaintext YAML as the
fallback.
   - Document in README.

## Parallel track: Epic I (operability and remote debuggability)

User stories I1–I7 (see `USER_STORIES.md`) form a track independent of
the drift / throughput / weather work above. They make the project
shippable to operators the maintainer has never met:
detailed-but-redacted-by-default logs, an HTTP transcript hook, and a
sectioned `report` subcommand whose output is safe to paste into an issue
tracker.

- **Minimum viable slice:** I2 (redaction by default), I3 (`--no-redact`
  opt-out with startup warning), I5 (`report` subcommand), I7 (redaction
  tests).
- **Depends on:** a small logging refactor and a request/response hook
  around the existing HTTP client.
- **Sequencing relative to the ordered list:** can land in parallel with
  item 1 (fixture harness). If item 1's fixtures will contain sensitive
  fields (WAN IP, IMSI, MAC), land I2 + I7 first so captured payloads can
  be redacted before they enter `tests/fixtures/`.

## Future: Rust rewrite

Inspect the sibling `zte-mc801a-cpp/` directory first to decide whether to reuse or supersede it. Target crates: `reqwest`, `serde_json`, `serde_yaml`, `clap` (derive), `ratatui` + `crossterm`, `tokio`, `tracing`. Structure as a Cargo workspace with a `zte-mc801a-core` library crate and a `zte-mc801a` binary crate so the library remains reusable. Port order: router HTTP client first, then drift checks with property tests using the captured Python fixtures, then daemon, then TUI last. Deliverable: a single static binary via `cargo build --release` plus a systemd unit. Rust is preferred over C++ because a long-running daemon wants memory safety, single-binary distribution is trivial with Cargo, and the type system makes "lock mask vs active bands vs Mbps" newtypes natural — advantages C++ only achieves with significant scaffolding.
