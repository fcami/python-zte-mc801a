import logging
import time

from python_zte_mc801a.lib.constants import ALL_5G_BANDS
from python_zte_mc801a.lib.data_processing import process_data
from python_zte_mc801a.lib.router_requests import (
    get_auth_cookies,
    get_latest_sms_messages,
    get_signal_data,
    set_5g_band,
)

log = logging.getLogger("rich")


def get_sms_data(router_ip: str, password: str) -> list:
    """Return SMS data in a single auth + fetch operation."""
    auth_cookies = get_auth_cookies(router_ip=router_ip, user_password=password)
    return get_latest_sms_messages(router_ip=router_ip, auth_cookies=auth_cookies)


def get_processed_data(router_ip: str, password: str) -> tuple:
    """Return (processed_data, raw_data) in a single auth + fetch operation."""
    auth_cookies = get_auth_cookies(router_ip=router_ip, user_password=password)
    data = get_signal_data(router_ip=router_ip, auth_cookies=auth_cookies)
    processed_data = process_data(raw_data=data)
    return processed_data, data


def force_5g_pci_selection(
    target_pci: str,
    processed_data: dict,
    router_ip: str,
    auth_cookies: dict,
    bands_5g: list = None,
    verbose: bool = True,
) -> bool:
    """Force selection of a 5G PCI by alternating between two band sets."""
    if bands_5g is None:
        bands_5g = ["78", ALL_5G_BANDS]
    next_set = 0

    for attempt in range(30):
        if verbose:
            log.info(f"Attempt {attempt + 1}/30 to obtain target PCI")
        if processed_data["5G"]["PCI"]["str_value"] == target_pci:
            if verbose:
                log.info(f"PCI already set to target {target_pci}")
            return True

        next_set = 1 - next_set
        set_5g_band(
            router_ip=router_ip,
            auth_cookies=auth_cookies,
            bands=bands_5g[next_set],
            verbose=False,
        )

        if verbose:
            log.info("Waiting 20 seconds before checking current PCI")
        time.sleep(20)

        raw_data = get_signal_data(
            router_ip=router_ip, auth_cookies=auth_cookies,
        )
        new_data = process_data(raw_data)
        current_pci = new_data["5G"]["PCI"]["str_value"]

        if current_pci == target_pci:
            if verbose:
                log.info(f"Achieved target PCI {current_pci}")
            return True
        if verbose:
            log.info(f"Not achieved target PCI — current is {current_pci}")

    return False
