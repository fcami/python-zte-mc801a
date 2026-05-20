"""Pure functions to read the radio's currently active bands from a fetched info dict."""

import re


def get_active_lte_bands(info: dict) -> list:
    """Return sorted deduplicated LTE bands in use (PCell + SCells). Empty list if none."""
    bands = set()

    pcell = str(info.get("lte_ca_pcell_band", "") or "").strip()
    if pcell:
        digits = re.sub(r"[^0-9]", "", pcell)
        if digits:
            n = int(digits)
            if n > 0:
                bands.add(n)
    else:
        wan = str(info.get("wan_active_band", "") or "").strip()
        if wan:
            digits = re.sub(r"[^0-9]", "", wan)
            if digits:
                n = int(digits)
                if n > 0:
                    bands.add(n)

    ca = str(info.get("lte_multi_ca_scell_info", "") or "").strip()
    if ca:
        for segment in ca.rstrip(";").split(";"):
            if not segment:
                continue
            parts = segment.split(",")
            if len(parts) >= 6:
                try:
                    n = int(parts[3])
                    if n > 0:
                        bands.add(n)
                except (ValueError, IndexError):
                    pass

    return sorted(bands)


def get_active_5g_bands(info: dict) -> list:
    """Return sorted deduplicated NR bands in use. Empty list if none."""
    raw = str(info.get("nr5g_action_band", "") or "").strip()
    if not raw:
        return []
    bands = set()
    for token in raw.split(","):
        token = token.strip()
        digits = re.sub(r"[^0-9]", "", token)
        if digits:
            try:
                n = int(digits)
                if n > 0:
                    bands.add(n)
            except ValueError:
                pass
    return sorted(bands)
