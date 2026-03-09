"""Watchdog daemon that monitors router state and re-applies settings."""

import logging
import time
from pathlib import Path

import yaml

from python_zte_mc801a.lib.constants import lte_mask_to_bands
from python_zte_mc801a.lib.router_requests import (
    NETWORK_MODES,
    NETWORK_MODES_REVERSE,
    get_auth_cookies,
    get_network_info,
    lock_cell,
    set_5g_band,
    set_dns,
    set_lte_band,
    set_network_mode,
)

log = logging.getLogger("rich")

DEFAULT_INTERVAL = 30
DEFAULT_CONFIG_PATH = "watchdog.yml"


def load_watchdog_config(path: str) -> dict:
    """Load and validate the watchdog YAML config file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(p) as f:
        cfg = yaml.safe_load(f)
    if not cfg or "router_ip" not in cfg or "password" not in cfg:
        raise ValueError("Config must contain at least 'router_ip' and 'password'")
    return cfg


def _check_network_mode(cfg: dict, info: dict, ip: str, cookies: dict) -> bool:
    """Check and fix network mode if it drifted."""
    desired = cfg.get("network_mode")
    if not desired:
        return True
    mode_value = NETWORK_MODES.get(desired)
    if not mode_value:
        log.error(f"Unknown network_mode '{desired}' in config")
        return False
    current = info.get("net_select", "")
    if current == mode_value:
        return True
    current_label = NETWORK_MODES_REVERSE.get(current, current)
    log.warning(f"Network mode drifted: {current_label} -> re-applying {desired}")
    return set_network_mode(ip, cookies, mode_value, verbose=True)


def _check_lte_bands(cfg: dict, info: dict, ip: str, cookies: dict) -> bool:
    """Check and fix LTE band lock if it drifted."""
    desired = cfg.get("lte_bands")
    if not desired:
        return True
    desired_set = set(desired)
    lte_mask = info.get("lte_band_ext_1_64", "")
    current_set = set(lte_mask_to_bands(lte_mask)) if lte_mask else set()
    if current_set == desired_set:
        return True
    log.warning(f"LTE bands drifted: {sorted(current_set)} -> re-applying {sorted(desired_set)}")
    return set_lte_band(ip, cookies, list(desired_set), verbose=True)


def _check_5g_bands(cfg: dict, info: dict, ip: str, cookies: dict) -> bool:
    """Check and fix 5G NR band lock if it drifted."""
    desired = cfg.get("nr5g_bands")
    if not desired:
        return True
    desired_str = ",".join(str(b) for b in sorted(desired))
    current = info.get("nr5g_sa_band_lock", "") or info.get("nr5g_nsa_band_lock", "")
    if current:
        current_set = set(int(b) for b in current.split(",") if b.strip())
        if current_set == set(desired):
            return True
    log.warning(f"5G bands drifted -> re-applying {desired_str}")
    return set_5g_band(ip, cookies, desired_str, verbose=True)


def _check_cell_lock(cfg: dict, info: dict, ip: str, cookies: dict) -> bool:
    """Check and fix cell lock if it drifted."""
    cell_cfg = cfg.get("cell_lock")
    if not cell_cfg:
        return True
    desired_pci = str(cell_cfg["pci"])
    desired_earfcn = str(cell_cfg["earfcn"])
    current_pci = info.get("lte_pci_lock", "")
    current_earfcn = info.get("lte_earfcn_lock", "")
    if current_pci == desired_pci and current_earfcn == desired_earfcn:
        return True
    log.warning(
        f"Cell lock drifted: PCI {current_pci}/{current_earfcn}"
        f" -> re-applying PCI {desired_pci}/{desired_earfcn}"
    )
    return lock_cell(ip, cookies, int(desired_pci), int(desired_earfcn), verbose=True)


def _check_dns(cfg: dict, info: dict, ip: str, cookies: dict) -> bool:
    """Check and fix DNS settings if they drifted."""
    dns_cfg = cfg.get("dns")
    if not dns_cfg:
        return True
    desired_primary = dns_cfg.get("primary", "")
    desired_secondary = dns_cfg.get("secondary", "")
    current_mode = info.get("dns_mode", "")
    current_primary = info.get("prefer_dns_manual", "")
    current_secondary = info.get("standby_dns_manual", "")
    if (
        current_mode == "manual"
        and current_primary == desired_primary
        and current_secondary == desired_secondary
    ):
        return True
    log.warning(f"DNS drifted -> re-applying {desired_primary}, {desired_secondary}")
    return set_dns(ip, cookies, desired_primary, desired_secondary, verbose=True)


CHECKS = [
    _check_network_mode,
    _check_lte_bands,
    _check_5g_bands,
    _check_cell_lock,
    _check_dns,
]


def run_once(cfg: dict) -> bool:
    """Run a single check-and-fix cycle. Returns True if all checks pass."""
    ip = cfg["router_ip"]
    pw = cfg["password"]
    cookies = get_auth_cookies(ip, pw)
    info = get_network_info(ip, cookies)
    all_ok = True
    for check in CHECKS:
        if not check(cfg, info, ip, cookies):
            all_ok = False
    return all_ok


def run_daemon(cfg: dict, interval: int = DEFAULT_INTERVAL):
    """Run the watchdog loop forever at the given interval."""
    log.info(f"Watchdog started (interval={interval}s)")
    while True:
        try:
            ok = run_once(cfg)
            if ok:
                log.info("All settings OK")
        except Exception as e:
            log.error(f"Watchdog error: {e}")
        time.sleep(interval)
