"""Tests for the pure band-monitor renderer (headless via a recording Console)."""
from rich.console import Console

from python_zte_mc801a.lib.monitor_view import render

KEYS = {"reset": "r", "pause": "p", "quit": "q"}


def _text(state: dict) -> str:
    console = Console(width=80, record=True)
    console.print(render(state, KEYS))
    return console.export_text()


def test_render_shows_active_bands_signal_and_legend():
    out = _text({
        "now": "18:42:03", "active_bands": [3, 7, 28], "band_lock": [3, 7, 28],
        "rsrp": "-97", "snr": "4.0", "temp": "80", "mode": "4G",
    })
    assert "B3" in out and "B7" in out and "B28" in out
    assert "700" in out and "780" in out  # nominal[DL centre] for B28
    assert "-97" in out and "4.0" in out
    # hotkey legend is always present
    assert "reset" in out and "pause" in out and "quit" in out


def test_render_flags_paused_and_running_reset():
    out = _text({"active_bands": [28], "paused": True, "reset_status": "running"})
    assert "PAUSED" in out
    assert "running" in out


def test_render_shows_ok_reset_with_time():
    out = _text({"active_bands": [3, 7, 28], "reset_status": "ok", "last_reset": "18:41:00"})
    assert "ok" in out and "18:41:00" in out


def test_render_handles_empty_state():
    out = _text({})
    assert "quit" in out          # legend still rendered
    assert "(none)" in out        # no active bands / no lock


def test_render_shows_reset_target_and_legend_key():
    out = _text({
        "active_bands": [3, 7, 28], "reset_bands": [3, 28], "reset_choice": "2/4",
    })
    assert "Reset target" in out
    assert "B3" in out and "B28" in out
    assert "2/4" in out
    assert "bands" in out  # [b] legend entry
