"""Interactive band monitor (C5): live status + on-demand band reset.

Redraws about 4x/second (RENDER_TICK) while polling the router about once per
second (interval), so the on-screen clock stays live between fetches. Handles
single-key input: r = reset now (collapse to the base band, then restore the
current reset target), b = cycle the reset target for the next r, p = pause,
q = quit. The reset runs on a worker thread so the display keeps updating
while the bands drop and recover. Only terminal I/O lives here; frame
rendering is in lib/monitor_view.

The download/bandwidth probe is intentionally NOT implemented in Python (it
targets the Rust port, per Epic J), so 'p' currently only toggles the paused
indicator -- there is no active probe for it to gate yet.

Not unit-tested end to end (needs a real TTY and a live router); the pure
helpers below and the renderer (tests/test_monitor_view) are covered.
"""
import select
import sys
import termios
import threading
import time
import tty
from datetime import datetime

from rich.live import Live

from python_zte_mc801a.lib.active_state import get_active_lte_bands
from python_zte_mc801a.lib.constants import band_label, lte_mask_to_bands, sort_bands_by_freq
from python_zte_mc801a.lib.monitor_view import render
from python_zte_mc801a.lib.reset import reset_lte_bands
from python_zte_mc801a.lib.router_requests import (
    NETWORK_MODES_REVERSE,
    get_auth_cookies,
    get_network_info,
)

AUTH_REFRESH_S = 20  # router session cookie expires ~30s after login
RENDER_TICK = 0.25  # display/clock refresh cadence, independent of router fetch
DEFAULT_KEYS = {"reset": "r", "pause": "p", "bands": "b", "quit": "q"}


def band_reset_presets(locked_bands: list) -> list:
    """Candidate band sets the 'b' key cycles through for the next reset.

    Ordered from the full lock down to the single lowest-frequency band,
    dropping the highest-frequency band one at a time. Duplicates (which
    occur once only two bands remain) are removed, keeping the first
    occurrence.
    """
    f = sort_bands_by_freq(locked_bands)
    if len(f) < 2:
        return [sorted(locked_bands)]
    candidates = [sorted(f), sorted(f[:-1]), sorted([f[0], f[-1]]), [f[0]]]
    presets = []
    for candidate in candidates:
        if candidate not in presets:
            presets.append(candidate)
    return presets


def _digits_to_band(value):
    digits = "".join(c for c in str(value or "") if c.isdigit())
    n = int(digits) if digits else 0
    return n if n > 0 else None


def anchor_band(info: dict):
    """Current PCell anchor band number, or None if not determinable."""
    return _digits_to_band(info.get("lte_ca_pcell_band")) or _digits_to_band(info.get("wan_active_band"))


def _fmt_pcell(info: dict) -> str:
    band = _digits_to_band(info.get("lte_ca_pcell_band"))
    if band is not None:
        bw = info.get("lte_ca_pcell_bandwidth", "")
        return f"{band_label(band)}  BW {bw} MHz" if bw else band_label(band)
    return info.get("wan_active_band", "") or ""


def _fmt_scells(info: dict) -> list:
    out = []
    for seg in str(info.get("lte_multi_ca_scell_info", "") or "").rstrip(";").split(";"):
        parts = seg.split(",")
        if len(parts) >= 6:
            out.append(f"{band_label(int(parts[3]))}  PCI {parts[1]}, EARFCN {parts[4]}, BW {parts[5]} MHz")
    return out


def _build_state(
    info: dict,
    paused: bool,
    reset_status: str,
    last_reset: str,
    error,
    reset_bands: list = None,
    reset_choice: str = "",
) -> dict:
    mask = info.get("lte_band_ext_1_64", "")
    band_lock = lte_mask_to_bands(mask) if mask and int(mask, 16) != 0 else []
    cell_lock = ""
    if info.get("lte_pci_lock"):
        cell_lock = f"PCI {info['lte_pci_lock']}, EARFCN {info.get('lte_earfcn_lock', '')}"
    return {
        "now": datetime.now().strftime("%H:%M:%S"),
        "active_bands": get_active_lte_bands(info),
        "pcell": _fmt_pcell(info),
        "scells": _fmt_scells(info),
        "rsrp": info.get("lte_rsrp", "?"),
        "rsrq": info.get("lte_rsrq", "?"),
        "snr": info.get("lte_snr", "?"),
        "temp": info.get("pm_sensor_mdm", "?"),
        "mode": NETWORK_MODES_REVERSE.get(info.get("net_select", ""), info.get("net_select", "?")),
        "band_lock": band_lock,
        "cell_lock": cell_lock,
        "paused": paused,
        "reset_status": reset_status,
        "last_reset": last_reset,
        "error": error,
        "reset_bands": reset_bands or [],
        "reset_choice": reset_choice,
    }


class _ResetState:
    """Status shared with the reset worker thread."""

    def __init__(self):
        self.status = "idle"
        self.last = ""


def _reset_worker(shared, ip, pw, base_band, full_bands, settle_s):
    shared.status = "running"
    try:
        cookies = get_auth_cookies(ip, pw)
        ok = reset_lte_bands(ip, cookies, base_band, full_bands, settle_s=settle_s)
        shared.status = "ok" if ok else "failed"
        shared.last = datetime.now().strftime("%H:%M:%S")
    except Exception as exc:  # noqa: BLE001
        shared.status = f"error: {exc}"


def run_monitor(config, base_band, full_bands, settle_s: float = 15.0, keys=None, interval: float = 1.0):
    """Run the interactive monitor loop until the quit key is pressed."""
    keys = keys or DEFAULT_KEYS
    ip, pw = config["router_ip"], config["password"]
    shared = _ResetState()
    paused = False
    error = None
    presets = band_reset_presets(full_bands)
    preset_idx = 0

    cookies = get_auth_cookies(ip, pw)
    last_auth = time.time()
    info = {}
    last_fetch = 0.0  # far enough in the past to force a fetch on the first tick

    fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(fd)
    worker = None
    try:
        tty.setcbreak(fd)
        with Live(auto_refresh=False, screen=True) as live:
            while True:
                if worker is not None and not worker.is_alive():
                    worker = None

                if worker is None and time.monotonic() - last_fetch >= interval:
                    if time.time() - last_auth > AUTH_REFRESH_S:
                        try:
                            cookies = get_auth_cookies(ip, pw)
                            last_auth = time.time()
                        except Exception as exc:  # noqa: BLE001
                            error = f"auth: {exc}"
                    try:
                        info = get_network_info(ip, cookies)
                        if not info.get("wan_active_band"):  # stale session -> re-auth once
                            cookies = get_auth_cookies(ip, pw)
                            last_auth = time.time()
                            info = get_network_info(ip, cookies)
                        error = None
                    except Exception as exc:  # noqa: BLE001
                        info = {}
                        error = f"fetch: {exc}"
                    last_fetch = time.monotonic()

                state = _build_state(
                    info, paused, shared.status, shared.last, error,
                    reset_bands=presets[preset_idx],
                    reset_choice=f"{preset_idx + 1}/{len(presets)}",
                )
                live.update(render(state, keys))
                live.refresh()

                ready, _, _ = select.select([sys.stdin], [], [], RENDER_TICK)
                if not ready:
                    continue
                ch = sys.stdin.read(1)
                if ch == keys["quit"]:
                    break
                if ch == keys["pause"]:
                    paused = not paused
                elif ch == keys["bands"]:
                    preset_idx = (preset_idx + 1) % len(presets)
                elif ch == keys["reset"] and worker is None:
                    shared.status = "running"
                    worker = threading.Thread(
                        target=_reset_worker,
                        args=(shared, ip, pw, base_band, presets[preset_idx], settle_s),
                        daemon=True,
                    )
                    worker.start()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
