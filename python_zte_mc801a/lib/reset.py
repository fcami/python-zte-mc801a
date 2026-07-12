"""Band-reset maneuver: collapse to the base band, then restore the full lock.

Re-applying an identical lock often does not dislodge a modem stuck on fewer
carriers; narrowing to a single base band and widening back forces the radio
to re-select carrier aggregation. Shared by the interactive monitor's manual
reset (C5) and, later, the watchdog escalation ladder (D5) and the bandwidth
guard (J4/J5).
"""
import logging
import time

from python_zte_mc801a.lib.router_requests import set_lte_band

log = logging.getLogger("rich")


def reset_lte_bands(
    router_ip,
    auth_cookies,
    base_band,
    full_bands,
    settle_s: float = 15.0,
    sleep=time.sleep,
    verbose: bool = False,
) -> bool:
    """Collapse the LTE lock to ``[base_band]``, wait ``settle_s``, then restore.

    Returns True only if both the collapse and the restore succeeded. The
    restore is always attempted -- even if the collapse call reported failure --
    so a partial failure never leaves the lock narrowed to the base band.

    ``sleep`` is injectable so the maneuver can be unit-tested without delay.
    """
    if verbose:
        log.info(
            f"Band reset: collapse to B{base_band}, settle {settle_s}s, "
            f"restore {sorted(full_bands)}"
        )
    collapsed = set_lte_band(router_ip, auth_cookies, [base_band], verbose=verbose)
    sleep(settle_s)
    restored = set_lte_band(router_ip, auth_cookies, list(full_bands), verbose=verbose)
    return bool(collapsed and restored)
