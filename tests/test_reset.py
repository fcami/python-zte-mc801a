"""Tests for the collapse-then-restore band reset primitive."""
from unittest.mock import call, patch

from python_zte_mc801a.lib.reset import reset_lte_bands

IP = "192.0.2.1"  # TEST-NET-1 (RFC 5737) placeholder
COOKIES = {}


def test_reset_collapses_then_restores():
    slept = []
    with patch("python_zte_mc801a.lib.reset.set_lte_band", return_value=True) as m:
        ok = reset_lte_bands(
            IP, COOKIES, base_band=28, full_bands=[3, 7, 28],
            settle_s=5, sleep=slept.append,
        )
    assert ok is True
    assert m.call_args_list[0] == call(IP, COOKIES, [28], verbose=False)
    assert m.call_args_list[1] == call(IP, COOKIES, [3, 7, 28], verbose=False)
    assert slept == [5]  # settled once, between collapse and restore


def test_reset_restores_even_if_collapse_fails():
    with patch("python_zte_mc801a.lib.reset.set_lte_band", side_effect=[False, True]) as m:
        ok = reset_lte_bands(IP, COOKIES, 28, [3, 7, 28], settle_s=0, sleep=lambda _s: None)
    assert ok is False          # overall failure reported
    assert m.call_count == 2    # but the restore was still attempted
    assert m.call_args_list[1] == call(IP, COOKIES, [3, 7, 28], verbose=False)


def test_reset_success_requires_both_calls():
    with patch("python_zte_mc801a.lib.reset.set_lte_band", side_effect=[True, False]):
        ok = reset_lte_bands(IP, COOKIES, 28, [3, 7, 28], settle_s=0, sleep=lambda _s: None)
    assert ok is False
