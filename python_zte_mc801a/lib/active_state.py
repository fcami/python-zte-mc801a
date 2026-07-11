"""Pure functions to read the radio's currently active bands from a fetched info dict."""

import re


def get_active_lte_bands(info: dict) -> list:
    """Return sorted deduplicated LTE bands in use (PCell + SCells). Empty list if none."""
    bands = set()

    # PCell band. The router reports "0" (a literal zero string, not "") when
    # carrier aggregation is inactive, so treat a non-positive PCell as "no
    # reading" and fall back to the plain active band rather than reporting
    # no bands at all while the modem is in fact connected on the primary.
    pcell_digits = re.sub(r"[^0-9]", "", str(info.get("lte_ca_pcell_band", "") or "").strip())
    if pcell_digits and int(pcell_digits) > 0:
        bands.add(int(pcell_digits))
    else:
        wan_digits = re.sub(r"[^0-9]", "", str(info.get("wan_active_band", "") or "").strip())
        if wan_digits and int(wan_digits) > 0:
            bands.add(int(wan_digits))

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
