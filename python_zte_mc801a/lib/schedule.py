"""Time-of-day probe scheduling: short probes in active hours, long off-hours.

STATUS: not yet wired into any command. It feeds the download-test path
(Epic J) -- the secondary/background complement to the live monitor (C5) --
which is deferred; the project will likely move to the Rust port before it
lands. Kept as tested reference logic.

Pure functions only (no I/O), so the decision logic is fully unit-testable
and ports directly to the planned Rust core.
"""
from datetime import datetime
from datetime import time as dtime

# Sensible caps if the config omits per-tier overrides.
_DEFAULT_SHORT = {"max_bytes": 20_000_000, "max_seconds": 8}
_DEFAULT_LONG = {"max_bytes": 100_000_000, "max_seconds": 25}


def _parse_hhmm(value: str) -> dtime:
    hh, mm = value.strip().split(":")
    return dtime(int(hh), int(mm))


def parse_window(spec: str) -> tuple:
    """Parse "HH:MM-HH:MM" into a (start, end) pair of datetime.time."""
    start, end = spec.split("-")
    return _parse_hhmm(start), _parse_hhmm(end)


def in_windows(now_time: dtime, windows: list) -> bool:
    """True if now_time falls in any (start, end) window.

    Windows may wrap past midnight (start > end), e.g. 23:00-08:00. The end is
    treated as exclusive.
    """
    for start, end in windows:
        if start <= end:
            if start <= now_time < end:
                return True
        elif now_time >= start or now_time < end:  # wraps midnight
            return True
    return False


def decide(now: datetime, cfg: dict, last_probe_ts: datetime = None) -> dict:
    """Decide what the scheduler should do at ``now``.

    Returns one of:
      {"action": "paused"}
      {"action": "idle",  "tier": "short"|"long", "due_in_s": float}
      {"action": "probe", "tier": "short"|"long", "caps": {...}}

    ``cfg`` keys: active_hours (list of "HH:MM-HH:MM"), active_probe_interval_min,
    offhours_probe_interval_min, active_probe / offhours_probe (cap overrides),
    paused (bool).
    """
    if cfg.get("paused"):
        return {"action": "paused"}

    windows = [parse_window(w) for w in cfg.get("active_hours", [])]
    active = in_windows(now.time(), windows)
    tier = "short" if active else "long"

    if active:
        interval_min = cfg.get("active_probe_interval_min", 30)
        caps = cfg.get("active_probe", _DEFAULT_SHORT)
    else:
        interval_min = cfg.get("offhours_probe_interval_min", 120)
        caps = cfg.get("offhours_probe", _DEFAULT_LONG)

    if last_probe_ts is None:
        return {"action": "probe", "tier": tier, "caps": caps}

    interval_s = interval_min * 60
    elapsed = (now - last_probe_ts).total_seconds()
    if elapsed >= interval_s:
        return {"action": "probe", "tier": tier, "caps": caps}
    return {"action": "idle", "tier": tier, "due_in_s": round(interval_s - elapsed, 1)}
