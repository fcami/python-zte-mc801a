"""Tests for _check_active_bands and load_watchdog_config clamp logic."""

import textwrap
from unittest.mock import patch

from python_zte_mc801a.daemon import _check_active_bands, load_watchdog_config

IP = "192.0.2.1"
COOKIES = {}

# info that yields LTE active [3, 7] via PCell B3 + SCell B7
INFO_LTE_3_7 = {
    "lte_ca_pcell_band": "3",
    "lte_multi_ca_scell_info": "1,85,1,7,3350,20;",
}

# info that yields LTE active [3, 7, 28]
INFO_LTE_3_7_28 = {
    "lte_ca_pcell_band": "3",
    "lte_multi_ca_scell_info": "1,85,1,7,3350,20;2,85,1,28,1675,15;",
}

# info that yields LTE active [3] only
INFO_LTE_3 = {"lte_ca_pcell_band": "3"}

# info with no bands
INFO_EMPTY = {}


def test_no_op_when_no_bands_configured():
    with patch("python_zte_mc801a.daemon.set_lte_band") as mock_lte, \
         patch("python_zte_mc801a.daemon.set_5g_band") as mock_5g:
        result = _check_active_bands({}, INFO_EMPTY, IP, COOKIES)
    assert result is True
    mock_lte.assert_not_called()
    mock_5g.assert_not_called()


def test_default_min_from_lte_bands_length_triggers_remediation():
    cfg = {"lte_bands": [3, 7, 28]}
    with patch("python_zte_mc801a.daemon.set_lte_band", return_value=True) as mock_lte:
        result = _check_active_bands(cfg, INFO_LTE_3_7, IP, COOKIES)
    assert result is True
    mock_lte.assert_called_once()
    call_args = mock_lte.call_args
    assert call_args[0][0] == IP
    assert call_args[0][1] == COOKIES
    assert sorted(call_args[0][2]) == [3, 7, 28]
    assert call_args[1].get("verbose") is True


def test_pass_through_when_active_meets_min():
    cfg = {"lte_bands": [3, 7, 28]}
    with patch("python_zte_mc801a.daemon.set_lte_band") as mock_lte:
        result = _check_active_bands(cfg, INFO_LTE_3_7_28, IP, COOKIES)
    assert result is True
    mock_lte.assert_not_called()


def test_explicit_min_below_lock_count_no_remediation():
    cfg = {"lte_bands": [3, 7, 28], "min_active_lte_bands": 2}
    with patch("python_zte_mc801a.daemon.set_lte_band") as mock_lte:
        result = _check_active_bands(cfg, INFO_LTE_3_7, IP, COOKIES)
    assert result is True
    mock_lte.assert_not_called()


def test_explicit_min_triggers_with_desired_lock():
    cfg = {"lte_bands": [3, 7, 28], "min_active_lte_bands": 2}
    with patch("python_zte_mc801a.daemon.set_lte_band", return_value=True) as mock_lte:
        result = _check_active_bands(cfg, INFO_LTE_3, IP, COOKIES)
    assert result is True
    call_args = mock_lte.call_args
    assert sorted(call_args[0][2]) == [3, 7, 28]


def test_5g_branch_fires_lte_not_called():
    cfg = {"nr5g_bands": [78]}
    with patch("python_zte_mc801a.daemon.set_lte_band") as mock_lte, \
         patch("python_zte_mc801a.daemon.set_5g_band", return_value=True) as mock_5g:
        result = _check_active_bands(cfg, INFO_EMPTY, IP, COOKIES)
    assert result is True
    mock_lte.assert_not_called()
    mock_5g.assert_called_once_with(IP, COOKIES, "78", verbose=True)


def test_setter_failure_propagates():
    cfg = {"lte_bands": [3, 7, 28]}
    with patch("python_zte_mc801a.daemon.set_lte_band", return_value=False):
        result = _check_active_bands(cfg, INFO_LTE_3_7, IP, COOKIES)
    assert result is False


def test_load_config_clamps_lte_min(tmp_path):
    cfg_file = tmp_path / "watchdog.yml"
    cfg_file.write_text(textwrap.dedent("""\
        router_ip: "192.0.2.1"
        password: "secret"
        lte_bands: [3, 7]
        min_active_lte_bands: 5
    """))
    cfg = load_watchdog_config(str(cfg_file))
    assert cfg["min_active_lte_bands"] == 2


def test_load_config_clamps_5g_min(tmp_path):
    cfg_file = tmp_path / "watchdog.yml"
    cfg_file.write_text(textwrap.dedent("""\
        router_ip: "192.0.2.1"
        password: "secret"
        nr5g_bands: [78]
        min_active_nr5g_bands: 3
    """))
    cfg = load_watchdog_config(str(cfg_file))
    assert cfg["min_active_nr5g_bands"] == 1
