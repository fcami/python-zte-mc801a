ALL_5G_BANDS = (
    "1,2,3,5,7,8,20,28,38,41,50,51,"
    "66,70,71,74,75,76,77,78,79,80,81,82,83,84"
)


# LTE band bitmask: bit (N-1) represents band N.
# Verified from router JS (goformId=SET_NETWORK_BAND_LOCK).
def lte_bands_to_mask(bands: list) -> str:
    """Convert a list of LTE band numbers to a hex bitmask string."""
    mask = sum(1 << (b - 1) for b in bands)
    return hex(mask)


def lte_mask_to_bands(mask_str: str) -> list:
    """Convert a hex bitmask string to a list of LTE band numbers."""
    mask = int(mask_str, 16)
    return [i + 1 for i in range(64) if mask & (1 << i)]


ALL_DATA_FIELDS = [
    "lte_pci",
    "lte_pci_lock",
    "lte_earfcn_lock",
    "lte_freq_lock",
    "lte_band_lock",
    "nr5g_band_lock",
    "wan_ipaddr",
    "wan_apn",
    "pm_sensor_mdm",
    "pm_modem_5g",
    "nr5g_pci",
    "nr5g_action_band",
    "nr5g_action_channel",
    "Z5g_SINR",
    "Z5g_rsrp",
    "wan_active_channel",
    "wan_active_band",
    "lte_multi_ca_scell_info",
    "cell_id",
    "dns_mode",
    "prefer_dns_manual",
    "standby_dns_manual",
    "rmcc",
    "rmnc",
    "network_type",
    "wan_lte_ca",
    "lte_rssi",
    "lte_rsrp",
    "lte_snr",
    "lte_rsrq",
    "lte_ca_pcell_bandwidth",
    "lte_ca_pcell_band",
    "lte_ca_scell_bandwidth",
    "lte_ca_scell_band",
    "wa_inner_version",
    "cr_version",
    "RD",
    "network_provider",
    "signalbar",
]
