"""Tests for the probe scheduler (pure decision logic)."""
from datetime import datetime
from datetime import time as dtime

from python_zte_mc801a.lib.schedule import decide, in_windows, parse_window


def test_parse_window():
    assert parse_window("08:00-23:00") == (dtime(8, 0), dtime(23, 0))


def test_in_windows_simple():
    w = [parse_window("08:00-23:00")]
    assert in_windows(dtime(12, 0), w) is True
    assert in_windows(dtime(7, 0), w) is False
    assert in_windows(dtime(23, 0), w) is False  # end exclusive


def test_in_windows_wraps_midnight():
    w = [parse_window("23:00-08:00")]
    assert in_windows(dtime(2, 0), w) is True
    assert in_windows(dtime(23, 30), w) is True
    assert in_windows(dtime(12, 0), w) is False


def test_decide_paused():
    assert decide(datetime(2026, 7, 12, 12, 0), {"paused": True}) == {"action": "paused"}


def test_decide_probe_active_tier_when_no_last():
    cfg = {"active_hours": ["08:00-23:00"], "active_probe_interval_min": 30}
    d = decide(datetime(2026, 7, 12, 12, 0), cfg, last_probe_ts=None)
    assert d["action"] == "probe"
    assert d["tier"] == "short"


def test_decide_offhours_long_tier():
    cfg = {"active_hours": ["08:00-23:00"], "offhours_probe_interval_min": 120}
    d = decide(datetime(2026, 7, 12, 3, 0), cfg, last_probe_ts=None)
    assert d["action"] == "probe"
    assert d["tier"] == "long"


def test_decide_idle_when_recent():
    cfg = {"active_hours": ["08:00-23:00"], "active_probe_interval_min": 30}
    now = datetime(2026, 7, 12, 12, 0)
    last = datetime(2026, 7, 12, 11, 50)  # 10 min ago; interval 30
    d = decide(now, cfg, last_probe_ts=last)
    assert d["action"] == "idle"
    assert d["tier"] == "short"
    assert d["due_in_s"] == 20 * 60


def test_decide_probe_when_interval_elapsed():
    cfg = {"active_hours": ["08:00-23:00"], "active_probe_interval_min": 30}
    now = datetime(2026, 7, 12, 12, 0)
    last = datetime(2026, 7, 12, 11, 25)  # 35 min ago
    assert decide(now, cfg, last_probe_ts=last)["action"] == "probe"


def test_decide_uses_cap_overrides():
    cfg = {
        "active_hours": ["08:00-23:00"],
        "active_probe": {"max_bytes": 5, "max_seconds": 2},
    }
    assert decide(datetime(2026, 7, 12, 12, 0), cfg)["caps"] == {"max_bytes": 5, "max_seconds": 2}
