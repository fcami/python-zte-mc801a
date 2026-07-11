"""Tests for active_state band parsing helpers."""

from python_zte_mc801a.lib.active_state import get_active_lte_bands, get_active_5g_bands


# --- LTE ---

def test_pcell_only():
    info = {"lte_ca_pcell_band": "3"}
    assert get_active_lte_bands(info) == [3]


def test_pcell_and_scells():
    info = {
        "lte_ca_pcell_band": "3",
        "lte_multi_ca_scell_info": "1,85,1,7,3350,20;2,85,1,28,1675,15;",
    }
    assert get_active_lte_bands(info) == [3, 7, 28]


def test_wan_active_band_fallback_b_prefix():
    info = {"lte_ca_pcell_band": "", "wan_active_band": "B3"}
    assert get_active_lte_bands(info) == [3]


def test_wan_active_band_fallback_plain():
    info = {"lte_ca_pcell_band": "", "wan_active_band": "3"}
    assert get_active_lte_bands(info) == [3]


def test_wan_active_band_fallback_verbose():
    info = {"lte_ca_pcell_band": "", "wan_active_band": "LTE BAND 3"}
    assert get_active_lte_bands(info) == [3]


def test_trailing_semicolon_ignored():
    info = {
        "lte_ca_pcell_band": "3",
        "lte_multi_ca_scell_info": "1,85,1,7,3350,20;",
    }
    assert get_active_lte_bands(info) == [3, 7]


def test_malformed_scell_skipped():
    # Too few comma fields — must be silently ignored
    info = {
        "lte_ca_pcell_band": "3",
        "lte_multi_ca_scell_info": "bad;1,85,1,7,3350,20;",
    }
    assert get_active_lte_bands(info) == [3, 7]


def test_empty_info_returns_empty():
    assert get_active_lte_bands({}) == []


def test_all_empty_strings():
    info = {"lte_ca_pcell_band": "", "wan_active_band": "", "lte_multi_ca_scell_info": ""}
    assert get_active_lte_bands(info) == []


def test_deduplication():
    # PCell B3, SCell also reports B3 — should appear once
    info = {
        "lte_ca_pcell_band": "3",
        "lte_multi_ca_scell_info": "1,85,1,3,3350,20;",
    }
    assert get_active_lte_bands(info) == [3]


def test_pcell_zero_falls_back_to_wan_active_band():
    # CA inactive: router reports pcell "0" (not ""); must fall back to wan_active_band
    info = {"lte_ca_pcell_band": "0", "wan_active_band": "LTE BAND 28"}
    assert get_active_lte_bands(info) == [28]


def test_pcell_zero_with_scells_reports_scells():
    # pcell "0" but SCells present: base band from wan fallback plus the SCell bands
    info = {
        "lte_ca_pcell_band": "0",
        "wan_active_band": "LTE BAND 28",
        "lte_multi_ca_scell_info": "1,85,1,7,3350,20;",
    }
    assert get_active_lte_bands(info) == [7, 28]


def test_pcell_zero_without_wan_returns_empty():
    # pcell "0" and no usable wan_active_band: genuinely nothing active
    info = {"lte_ca_pcell_band": "0", "wan_active_band": ""}
    assert get_active_lte_bands(info) == []


# --- 5G ---

def test_5g_n_prefix():
    assert get_active_5g_bands({"nr5g_action_band": "n78"}) == [78]


def test_5g_nr_ca():
    assert get_active_5g_bands({"nr5g_action_band": "n28,n78"}) == [28, 78]


def test_5g_plain_number():
    assert get_active_5g_bands({"nr5g_action_band": "78"}) == [78]


def test_5g_empty():
    assert get_active_5g_bands({"nr5g_action_band": ""}) == []


def test_5g_missing_key():
    assert get_active_5g_bands({}) == []
