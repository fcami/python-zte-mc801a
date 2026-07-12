"""Tests for the band-monitor pure helpers (no TTY required)."""
from python_zte_mc801a.monitor import _build_state, _fmt_pcell, _fmt_scells, anchor_band


def test_fmt_pcell_normal():
    assert _fmt_pcell({"lte_ca_pcell_band": "28", "lte_ca_pcell_bandwidth": "10.0"}) == "B28 (10.0 MHz)"


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
    assert "B7" in scells[0] and "3350" in scells[0]
    assert "B3" in scells[1]


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
