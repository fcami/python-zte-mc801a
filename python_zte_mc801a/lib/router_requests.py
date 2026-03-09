import codecs
import hashlib
import logging

import requests
from retry import retry

from python_zte_mc801a.lib.constants import ALL_DATA_FIELDS
from python_zte_mc801a.lib.data_processing import get_ad_value

log = logging.getLogger("rich")


@retry(tries=3, delay=2)
def get_auth_cookies(router_ip: str, user_password: str) -> dict:
    """Retrieve authentication cookies from the router

    Args:
        router_ip (str): IP (or hostname) of the router
        user_password (str): Admin user password

    Raises:
        Exception: Unable to retrieve authentication cookies

    Returns:
        dict: Authentication cookies
    """

    # Request the current LD
    r_ld = requests.get(
        f"http://{router_ip}/goform/goform_get_cmd_process?isTest=false&cmd=LD",
        cookies={"stok": ""},
        headers={"referer": f"http://{router_ip}/"},
    )

    # The password is hashed twice
    m = hashlib.sha256()
    m.update(user_password.encode())

    m2 = hashlib.sha256()
    m2.update(f'{m.hexdigest().upper()}{r_ld.json()["LD"]}'.encode())

    pwd = m2.hexdigest().upper()

    # Login request
    r_login = requests.get(
        f"http://{router_ip}/goform/goform_set_cmd_process?isTest=false&goformId=LOGIN&password={pwd}",
        cookies={"stok": ""},
        headers={"referer": f"http://{router_ip}/"},
    )

    if (not "result" in r_login.json().keys()) or (r_login.json()["result"] != "0"):
        raise Exception("Login unsuccessful")

    return r_login.cookies.get_dict()


def _get_cmd(router_ip: str, auth_cookies: dict, fields: list) -> dict:
    """Query the router for one or more fields. Returns the JSON response."""
    r = requests.get(
        f'http://{router_ip}/goform/goform_get_cmd_process'
        f'?isTest=false&cmd={",".join(fields)}&multi_data=1',
        cookies=auth_cookies,
        headers={"referer": f"http://{router_ip}/"},
    )
    return r.json()


def get_signal_data(router_ip: str, auth_cookies: dict) -> dict:
    """Retrieve router data related to signals."""
    return _get_cmd(router_ip, auth_cookies, ALL_DATA_FIELDS)


def get_latest_sms_messages(router_ip: str, auth_cookies: dict, n: int = 3) -> list:
    """Retrieve latest SMS messages, decoded from hex to text."""
    r = requests.get(
        f"http://{router_ip}/goform/goform_get_cmd_process?isTest=false"
        f"&cmd=sms_data_total&page=0&data_per_page=500"
        f"&mem_store=1&tags=10&order_by=order+by+id+desc",
        cookies=auth_cookies,
        headers={"referer": f"http://{router_ip}/"},
    )
    messages = r.json().get("messages", [])[:n]
    for msg in messages:
        msg["content"] = codecs.decode(
            msg["content"], "hex"
        ).replace(b"\x00", b"").decode("latin-1")
    return messages


def get_lte_band_lock(router_ip: str, auth_cookies: dict) -> dict:
    """Read the current LTE band lock masks from the router."""
    return _get_cmd(router_ip, auth_cookies, [
        "lte_band_ext_1_64", "lte_band_ext_65_128",
        "lte_band_ext_129_192", "lte_band_ext_193_256",
    ])


def set_lte_band(
    router_ip: str, auth_cookies: dict, bands: list, verbose: bool = False
) -> bool:
    """Lock LTE to the given list of band numbers (1-64).

    Uses goformId=BAND_SELECT_EX with lte_band_ext_1_64.
    """
    from python_zte_mc801a.lib.constants import lte_bands_to_mask

    if any(b > 64 for b in bands):
        if verbose:
            log.warning(f"Bands > 64 not supported, ignoring: {[b for b in bands if b > 64]}")
        bands = [b for b in bands if b <= 64]

    hex_str = lte_bands_to_mask(bands)[2:]  # strip "0x"
    padded = "0x" + hex_str.zfill(19)

    result = _post_cmd(router_ip, auth_cookies, {
        "goformId": "BAND_SELECT_EX",
        "lte_band_ext_1_64": padded,
    })
    ok = result.get("result") == "success"
    if verbose:
        if ok:
            log.info(f"Successfully set LTE bands to {bands} (mask {padded})")
        else:
            log.error(f"Error setting LTE bands to {bands}: {result}")
    return ok


def _post_cmd(router_ip: str, auth_cookies: dict, data: dict) -> dict:
    """POST a goform command with fresh AD. Returns the JSON response."""
    raw_data = get_signal_data(router_ip=router_ip, auth_cookies=auth_cookies)
    ad = get_ad_value(raw_data)
    data["isTest"] = "false"
    data["AD"] = ad
    r = requests.post(
        f"http://{router_ip}/goform/goform_set_cmd_process",
        data=data,
        cookies=auth_cookies,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": f"http://{router_ip}/",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    return r.json()


def set_5g_band(
    router_ip: str, auth_cookies: dict, bands: str, verbose: bool = False
) -> bool:
    result = _post_cmd(router_ip, auth_cookies, {
        "goformId": "WAN_PERFORM_NR5G_BAND_LOCK",
        "nr5g_band_mask": bands,
    })
    ok = result.get("result") == "success"
    if verbose:
        if ok:
            log.info(f"Successfully set 5G bands to {bands}")
        else:
            log.error(f"Error setting 5G bands to {bands}: {result}")
    return ok


NETWORK_MODES = {
    "5G+4G+3G": "WL_AND_5G",
    "5G_NSA": "LTE_AND_5G",
    "5G_SA": "Only_5G",
    "4G+5G": "4G_AND_5G",
    "4G+3G": "WCDMA_AND_LTE",
    "4G": "Only_LTE",
    "3G": "Only_WCDMA",
}

NETWORK_MODES_REVERSE = {v: k for k, v in NETWORK_MODES.items()}


def get_network_mode(router_ip: str, auth_cookies: dict) -> str:
    """Return the current network mode (BearerPreference value)."""
    return _get_cmd(router_ip, auth_cookies, ["net_select"]).get("net_select", "")


def set_network_mode(
    router_ip: str, auth_cookies: dict, mode: str, verbose: bool = False
) -> bool:
    """Set the network mode. mode is the BearerPreference value, e.g. 'Only_LTE'."""
    result = _post_cmd(router_ip, auth_cookies, {
        "goformId": "SET_BEARER_PREFERENCE",
        "BearerPreference": mode,
    })
    ok = result.get("result") == "success"
    if verbose:
        label = NETWORK_MODES_REVERSE.get(mode, mode)
        if ok:
            log.info(f"Successfully set network mode to {label} ({mode})")
        else:
            log.error(f"Error setting network mode to {label}: {result}")
    return ok
