"""Tests for the band-monitor pure helpers (no TTY required)."""
import pytest

from python_zte_mc801a.monitor import (
    _build_state,
    _fmt_pcell,
    _fmt_scells,
    anchor_band,
    band_reset_presets,
    resolve_monitor_bands,
)


def test_fmt_pcell_normal():
    assert _fmt_pcell({"lte_ca_pcell_band": "28", "lte_ca_pcell_bandwidth": "10.0"}) == "B28 700[780]  BW 10.0 MHz"


def test_fmt_pcell_zero_falls_back_to_wan():
    assert _fmt_pcell({"lte_ca_pcell_band": "0", "wan_active_band": "LTE BAND 28"}) == "LTE BAND 28"


def test_anchor_band_from_pcell():
    assert anchor_band({"lte_ca_pcell_band": "28"}) == 28


def test_anchor_band_from_wan_when_pcell_zero():
    assert anchor_band({"lte_ca_pcell_band": "0", "wan_active_band": "LTE BAND 28"}) == 28


def test_anchor_band_none_when_absent():
    assert anchor_band({}) is None


def test_fmt_scells_parses_segments():
    scells = _fmt_scells({"lte_multi_ca_scell_info": "1,85,1,7,3350,20;2,85,1,3,1675,15;"})
    assert len(scells) == 2
    assert scells[0] == "B7 2600[2655]  PCI 85, EARFCN 3350, BW 20 MHz"
    assert scells[1] == "B3 1800[1842]  PCI 85, EARFCN 1675, BW 15 MHz"


def test_build_state_maps_fields_and_lock():
    info = {
        "lte_ca_pcell_band": "28", "lte_ca_pcell_bandwidth": "10.0",
        "lte_multi_ca_scell_info": "1,85,1,7,3350,20;",
        "lte_rsrp": "-97", "lte_snr": "4.0", "pm_sensor_mdm": "80",
        "net_select": "Only_LTE",
        "lte_band_ext_1_64": "0x008000044",  # bands 3, 7, 28
        "lte_pci_lock": "455", "lte_earfcn_lock": "9460",
        "wan_active_band": "LTE BAND 28",
    }
    state = _build_state(info, paused=True, reset_status="idle", last_reset="", error=None)
    assert state["active_bands"] == [7, 28]
    assert state["band_lock"] == [3, 7, 28]
    assert state["mode"] == "4G"
    assert state["cell_lock"].startswith("PCI 455")
    assert state["paused"] is True
    assert state["rsrp"] == "-97"


def test_band_reset_presets_three_bands():
    assert band_reset_presets([3, 7, 28]) == [[3, 7, 28], [3, 28], [7, 28], [28]]


def test_band_reset_presets_two_bands_dedupes():
    assert band_reset_presets([3, 28]) == [[3, 28], [28]]


def test_band_reset_presets_single_band():
    assert band_reset_presets([28]) == [[28]]


def test_resolve_monitor_bands_prefers_bands_opt():
    assert resolve_monitor_bands("3, 7,28", [1], [1, 2]) == [3, 7, 28]


def test_resolve_monitor_bands_falls_back_to_persisted():
    assert resolve_monitor_bands(None, [3, 7, 28], [1, 2]) == [3, 7, 28]


def test_resolve_monitor_bands_bootstraps_from_current_lock():
    assert resolve_monitor_bands(None, None, [28, 3]) == [3, 28]


def test_resolve_monitor_bands_raises_when_nothing_available():
    with pytest.raises(ValueError, match="Pass --bands"):
        resolve_monitor_bands(None, None, [28])
