"""Pure rendering for the interactive band monitor (C5).

``render(state, keys)`` turns a plain state dict into a rich renderable. It
does no I/O and no terminal control, so the display is unit-testable headless
and ports cleanly to the planned Rust TUI. The live loop that populates
``state`` and handles keypresses lives in ``monitor.py``.

Expected ``state`` keys (all optional): now, active_bands (list[int]),
pcell (str), scells (list[str]), rsrp, rsrq, snr, temp, mode,
band_lock (list[int]), cell_lock (str), paused (bool),
reset_status ("idle"|"running"|"ok"|"failed"|"error: ..."), last_reset (str),
error (str), reset_bands (list[int]), reset_choice (str, e.g. "2/4").
"""
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from python_zte_mc801a.lib.constants import band_label, sort_bands_by_freq


def _fmt_bands(bands) -> str:
    if not bands:
        return "(none)"
    return " / ".join(band_label(b) for b in sort_bands_by_freq(bands))


def _band_style(active, band_lock) -> str:
    if band_lock and set(active) >= set(band_lock):
        return "bold green"
    if active:
        return "bold yellow"
    return "bold red"


def render(state: dict, keys: dict) -> Panel:
    active = state.get("active_bands") or []
    band_lock = state.get("band_lock") or []

    body = Table.grid(padding=(0, 2))
    body.add_column(justify="right", style="bold")
    body.add_column()

    body.add_row("Time", state.get("now", ""))
    body.add_row("", "")
    body.add_row("Active LTE", Text(_fmt_bands(active), style=_band_style(active, band_lock)))
    if state.get("pcell"):
        body.add_row("PCell", state["pcell"])
    for scell in state.get("scells") or []:
        body.add_row("SCell", scell)

    body.add_row("", "")
    body.add_row("RSRP", f"{state.get('rsrp', '?')} dBm")
    body.add_row("RSRQ", f"{state.get('rsrq', '?')} dB")
    body.add_row("SNR", f"{state.get('snr', '?')} dB")
    body.add_row("Temp", f"{state.get('temp', '?')} C")

    body.add_row("", "")
    body.add_row("Mode", state.get("mode", "?"))
    body.add_row("Band lock", _fmt_bands(band_lock))
    if state.get("cell_lock"):
        body.add_row("Cell lock", state["cell_lock"])

    body.add_row("", "")
    paused = bool(state.get("paused"))
    body.add_row("Probing", Text("PAUSED", style="bold red") if paused else Text("active", style="green"))
    reset_status = state.get("reset_status", "idle")
    reset_style = {"running": "bold yellow", "ok": "green", "idle": "dim"}.get(reset_status, "red")
    reset_line = f"ok ({state.get('last_reset', '')})" if reset_status == "ok" else reset_status
    body.add_row("Reset", Text(reset_line, style=reset_style))
    reset_bands = state.get("reset_bands") or []
    reset_choice = state.get("reset_choice", "")
    target_line = _fmt_bands(reset_bands) + (f"   ({reset_choice})" if reset_choice else "")
    body.add_row("Reset target", target_line)
    if state.get("error"):
        body.add_row("Error", Text(state["error"], style="red"))

    legend = Text.assemble(
        ("[", "dim"), (keys.get("reset", "r"), "bold cyan"), ("] reset    ", "dim"),
        ("[", "dim"), (keys.get("bands", "b"), "bold cyan"), ("] bands    ", "dim"),
        ("[", "dim"), (keys.get("pause", "p"), "bold cyan"), ("] pause    ", "dim"),
        ("[", "dim"), (keys.get("quit", "q"), "bold cyan"), ("] quit", "dim"),
    )

    grid = Table.grid()
    grid.add_row(body)
    grid.add_row(Text(""))
    grid.add_row(legend)

    return Panel(grid, title="ZTE MC801a monitor", border_style="cyan")
