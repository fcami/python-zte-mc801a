"""Tests for LTE band constants and frequency-based sorting."""
from python_zte_mc801a.lib.constants import sort_bands_by_freq


def test_sort_bands_by_freq_orders_by_dl_frequency():
    assert sort_bands_by_freq([3, 7, 28]) == [28, 3, 7]


def test_sort_bands_by_freq_unknown_band_sorts_last():
    assert sort_bands_by_freq([3, 999, 28]) == [28, 3, 999]


def test_sort_bands_by_freq_unknown_bands_ordered_by_number():
    assert sort_bands_by_freq([999, 3, 500]) == [3, 500, 999]
