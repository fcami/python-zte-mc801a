import logging

import typer
import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.padding import Padding
from rich.pretty import pprint
from rich.prompt import Prompt
from rich.table import Table

from python_zte_mc801a.client.data_io import check_config
from python_zte_mc801a.client.live import show_live, LIVE_VISUALIZATIONS
from python_zte_mc801a.lib.constants import ALL_5G_BANDS, lte_mask_to_bands
from python_zte_mc801a.lib.data_processing import process_data
from python_zte_mc801a.lib.helpers import force_5g_pci_selection
from python_zte_mc801a.lib.router_requests import (
    get_auth_cookies, get_signal_data, get_network_info, get_device_info,
    set_lte_band, get_lte_band_lock,
    set_5g_band, set_network_mode,
    set_dns, set_dns_auto, lock_cell, unlock_cell, reboot_device,
    NETWORK_MODES, NETWORK_MODES_REVERSE,
)

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")

app = typer.Typer()

console = Console()


@app.callback()
def callback():
    """
    ZTE MC801a Management Tool
    """


@app.command()
def setup():
    print(Padding("Setup and persist router IP and password", (1, 1)))

    print(
        Padding(
            "🚨 Your password will be stored as plain-text in `settings.yml`. You can alternatively pass your password directly to the various commands.",
            (1, 1),
        )
    )

    router_ip = Prompt.ask(
        "Enter your router IP",
    )

    password = Prompt.ask(
        "Enter your router password",
        password=True,
    )

    with open("settings.yml", "w") as f:
        yaml.dump({"router_ip": router_ip, "password": password}, f)


@app.command(
    help="Try to connect to a target 5G PCI by alternatively setting 5G bands to one of two sets. Useful when a certain PCI is preferred over another (e.g. for performance reason)"
)
def force_5g_pci(
    target_pci: str = typer.Argument(..., help="PCI to target", metavar="TEXT"),
    band_set_1: str = typer.Argument(
        ...,
        help="First set of bands to alternative between (comma separated, e.g. 1,3,78)",
    ),
    band_set_2: str = typer.Argument(
        ALL_5G_BANDS,
        help="Second set of bands to alternative between (comma separated, e.g. 1,3,78)",
        metavar="TEXT",
    ),
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    config = check_config(router_ip, password)

    if config:
        cookies = get_auth_cookies(config["router_ip"], config["password"])
        data = get_signal_data(config["router_ip"], cookies)
        processed_data = process_data(raw_data=data)

        force_5g_pci_selection(
            target_pci=target_pci,
            processed_data=processed_data,
            router_ip=config["router_ip"],
            auth_cookies=cookies,
            bands_5g=[band_set_1, band_set_2],
        )


def _format_cell_table(d: dict) -> Table:
    """Build a Rich table showing detailed cell connection info."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="bold")
    table.add_column("value")

    # Network mode
    mode_raw = d.get("net_select", "")
    mode_label = NETWORK_MODES_REVERSE.get(mode_raw, mode_raw)
    table.add_row("Network mode", f"{mode_label} ({mode_raw})")
    table.add_row("Connection type", d.get("network_type", ""))
    table.add_row("Provider", d.get("network_provider", ""))
    table.add_row("WAN IP", d.get("wan_ipaddr", ""))
    table.add_row("APN", d.get("wan_apn", ""))
    table.add_row("", "")

    # 4G main cell
    lte_pci = d.get("lte_pci", "")
    pci_dec = str(int(lte_pci, 16)) if lte_pci else ""
    earfcn = d.get("wan_active_channel", "")
    lock_pci = d.get("lte_pci_lock", "")
    lock_earfcn = d.get("lte_earfcn_lock", "")
    lock_tag = ""
    if lock_pci and pci_dec == lock_pci:
        lock_tag = " [red](locked)[/red]"
    table.add_row("4G PCI", f"{pci_dec}{lock_tag}")
    table.add_row("4G EARFCN", earfcn)
    table.add_row("4G band", d.get("wan_active_band", ""))
    bw = d.get("lte_ca_pcell_bandwidth", "")
    if bw:
        table.add_row(
            "4G PCell",
            f"B{d.get('lte_ca_pcell_band', '')} ({round(float(bw))} MHz)",
        )
    table.add_row("4G RSRP", f"{d.get('lte_rsrp', '')} dBm")
    table.add_row("4G RSRQ", f"{d.get('lte_rsrq', '')} dB")
    table.add_row("4G RSSI", f"{d.get('lte_rssi', '')} dBm")
    table.add_row("4G SNR", f"{d.get('lte_snr', '')} dB")

    # Carrier aggregation
    ca = d.get("lte_multi_ca_scell_info", "")
    if ca:
        table.add_row("", "")
        for scell in ca.rstrip(";").split(";"):
            parts = scell.split(",")
            if len(parts) >= 6:
                table.add_row(
                    f"CA SCell B{parts[3]}",
                    f"PCI {parts[1]}, EARFCN {parts[4]}, {round(float(parts[5]))} MHz",
                )

    # 5G
    nr_band = d.get("nr5g_action_band", "")
    if nr_band:
        nr_pci = d.get("nr5g_pci", "")
        nr_pci_dec = str(int(nr_pci, 16)) if nr_pci else ""
        table.add_row("", "")
        table.add_row("5G band", nr_band)
        table.add_row("5G PCI", nr_pci_dec)
        table.add_row("5G EARFCN", d.get("nr5g_action_channel", ""))
        table.add_row("5G RSRP", f"{d.get('Z5g_rsrp', '')} dBm")
        table.add_row("5G SINR", f"{d.get('Z5g_SINR', '')} dB")

    # Band locks
    table.add_row("", "")
    lte_mask = d.get("lte_band_ext_1_64", "")
    if lte_mask and int(lte_mask, 16) != 0:
        table.add_row("LTE band lock", str(lte_mask_to_bands(lte_mask)))
    else:
        table.add_row("LTE band lock", "(all bands)")
    sa = d.get("nr5g_sa_band_lock", "")
    nsa = d.get("nr5g_nsa_band_lock", "")
    if sa:
        table.add_row("5G SA band lock", sa)
    if nsa:
        table.add_row("5G NSA band lock", nsa)
    if lock_pci:
        table.add_row("Cell lock", f"PCI {lock_pci}, EARFCN {lock_earfcn}")

    # DNS
    dns_mode = d.get("dns_mode", "")
    if dns_mode == "manual":
        dns = f"{d.get('prefer_dns_manual', '')}, {d.get('standby_dns_manual', '')}"
        table.add_row("DNS", f"manual ({dns})")
    elif dns_mode:
        table.add_row("DNS", dns_mode)

    # Temperature
    t4g = d.get("pm_sensor_mdm", "")
    t5g = d.get("pm_modem_5g", "")
    if t4g or t5g:
        table.add_row("", "")
        if t4g:
            table.add_row("Temp 4G", f"{t4g} C")
        if t5g:
            table.add_row("Temp 5G", f"{t5g} C")

    return table


@app.command()
def status(
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Show current network mode, active bands, signal, and band lock state"""
    config = check_config(router_ip, password)
    if not config:
        return
    cookies = get_auth_cookies(config["router_ip"], config["password"])
    d = get_network_info(config["router_ip"], cookies)
    console.print(_format_cell_table(d))


@app.command()
def set_mode(
    mode: str = typer.Argument(
        ...,
        help="Network mode: 5G+4G+3G, 5G_NSA, 5G_SA, 4G+5G, 4G+3G, 4G, 3G",
        metavar="MODE",
    ),
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Set network mode (e.g. 4G, 5G_NSA, 5G_SA, 5G+4G+3G)"""
    config = check_config(router_ip, password)
    if not config:
        return
    mode_value = NETWORK_MODES.get(mode)
    if not mode_value:
        log.error(f"Unknown mode '{mode}'. Valid modes: {', '.join(NETWORK_MODES.keys())}")
        raise typer.Exit(1)
    cookies = get_auth_cookies(config["router_ip"], config["password"])
    success = set_network_mode(config["router_ip"], cookies, mode_value, verbose=True)
    if not success:
        raise typer.Exit(1)


@app.command()
def lock_5g_bands(
    bands: str = typer.Argument(
        ...,
        help="Comma-separated NR band numbers to lock to, e.g. '28' or '28,78'",
        metavar="BANDS",
    ),
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Lock 5G NR to specific bands (comma-separated band numbers, e.g. 28 or 28,78)"""
    config = check_config(router_ip, password)
    if config:
        cookies = get_auth_cookies(config["router_ip"], config["password"])
        success = set_5g_band(
            router_ip=config["router_ip"],
            auth_cookies=cookies,
            bands=bands,
            verbose=True,
        )
        if not success:
            raise typer.Exit(1)


@app.command()
def lte_band_info(
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Show current LTE band lock state (locked bands and their bitmask)"""
    config = check_config(router_ip, password)
    if config:
        cookies = get_auth_cookies(config["router_ip"], config["password"])
        result = get_lte_band_lock(config["router_ip"], cookies)
        lte_mask = result.get("lte_band_ext_1_64", "")
        if lte_mask and int(lte_mask, 16) != 0:
            bands = lte_mask_to_bands(lte_mask)
            console.print(f"LTE band lock mask (bands 1-64) : {lte_mask}")
            console.print(f"Locked LTE bands                : {bands}")
        else:
            console.print("LTE band lock mask : (not set / all bands)")


@app.command()
def lock_lte_bands(
    bands: str = typer.Argument(
        ...,
        help="Comma-separated LTE band numbers to lock to, e.g. '3,7,28'",
        metavar="BANDS",
    ),
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Lock LTE to specific bands (comma-separated band numbers, e.g. 3,7,28)"""
    config = check_config(router_ip, password)
    if config:
        try:
            band_list = [int(b.strip()) for b in bands.split(",")]
        except ValueError:
            log.error("Invalid band list — expected comma-separated integers, e.g. '3,7,28'")
            raise typer.Exit(1)
        cookies = get_auth_cookies(config["router_ip"], config["password"])
        success = set_lte_band(
            router_ip=config["router_ip"],
            auth_cookies=cookies,
            bands=band_list,
            verbose=True,
        )
        if not success:
            raise typer.Exit(1)


@app.command()
def info(
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Show device hardware, web, and firmware version"""
    config = check_config(router_ip, password)
    if not config:
        return
    cookies = get_auth_cookies(config["router_ip"], config["password"])
    d = get_device_info(config["router_ip"], cookies)
    console.print(f"[bold]Hardware version[/bold]  : {d.get('hardware_version', '')}")
    console.print(f"[bold]Web version[/bold]       : {d.get('web_version', '')}")
    console.print(f"[bold]Firmware version[/bold]  : {d.get('wa_inner_version', '')}")
    console.print(f"[bold]CR version[/bold]        : {d.get('cr_version', '')}")


@app.command()
def set_dns_cmd(
    servers: str = typer.Argument(
        ...,
        help="Two DNS servers comma-separated (e.g. '1.1.1.1,1.0.0.1') or 'auto'",
        metavar="SERVERS",
    ),
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Set DNS servers (e.g. '1.1.1.1,1.0.0.1') or 'auto' for provider defaults"""
    config = check_config(router_ip, password)
    if not config:
        return
    cookies = get_auth_cookies(config["router_ip"], config["password"])
    if servers.lower() == "auto":
        ok = set_dns_auto(config["router_ip"], cookies, verbose=True)
    else:
        parts = [s.strip() for s in servers.split(",")]
        if len(parts) != 2:
            log.error("Expected two DNS servers separated by comma")
            raise typer.Exit(1)
        ok = set_dns(config["router_ip"], cookies, parts[0], parts[1], verbose=True)
    if not ok:
        raise typer.Exit(1)


@app.command()
def lock_cell_cmd(
    pci: int = typer.Argument(..., help="PCI of the cell to lock to"),
    earfcn: int = typer.Argument(..., help="EARFCN of the cell to lock to"),
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
    do_reboot: bool = typer.Option(
        False, "--reboot", help="Reboot the router after locking"
    ),
):
    """Lock LTE to a specific cell (PCI + EARFCN). Requires reboot to take effect."""
    config = check_config(router_ip, password)
    if not config:
        return
    cookies = get_auth_cookies(config["router_ip"], config["password"])
    ok = lock_cell(config["router_ip"], cookies, pci, earfcn, verbose=True)
    if not ok:
        raise typer.Exit(1)
    if do_reboot:
        reboot_device(config["router_ip"], cookies, verbose=True)


@app.command()
def unlock_cell_cmd(
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
    do_reboot: bool = typer.Option(
        False, "--reboot", help="Reboot the router after unlocking"
    ),
):
    """Remove cell lock. Requires reboot to take effect."""
    config = check_config(router_ip, password)
    if not config:
        return
    cookies = get_auth_cookies(config["router_ip"], config["password"])
    ok = unlock_cell(config["router_ip"], cookies, verbose=True)
    if not ok:
        raise typer.Exit(1)
    if do_reboot:
        reboot_device(config["router_ip"], cookies, verbose=True)


@app.command()
def reboot(
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Reboot the router"""
    config = check_config(router_ip, password)
    if not config:
        return
    cookies = get_auth_cookies(config["router_ip"], config["password"])
    ok = reboot_device(config["router_ip"], cookies, verbose=True)
    if not ok:
        raise typer.Exit(1)


@app.command()
def data(
    raw: bool = typer.Option(False),
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Show signal data"""
    config = check_config(router_ip, password)

    if config:
        cookies = get_auth_cookies(config["router_ip"], config["password"])
        data = get_signal_data(config["router_ip"], cookies)

        if not raw:
            processed_data = process_data(raw_data=data)
            pprint(processed_data)
        else:
            pprint(data)


@app.command()
def live(
    viz: LIVE_VISUALIZATIONS = typer.Option(
        LIVE_VISUALIZATIONS.SMS, case_sensitive=False
    ),
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Show a live dashboard"""

    config = check_config(router_ip, password)

    if config:
        show_live(config, viz=viz)


@app.command()
def watchdog(
    config_file: str = typer.Argument(
        "watchdog.yml",
        help="Path to watchdog YAML config file",
    ),
    interval: int = typer.Option(30, help="Check interval in seconds"),
):
    """Run a watchdog daemon that monitors router state and re-applies settings.

    The config file (default: watchdog.yml) should contain:

    \b
        router_ip: 192.0.2.1
        password: SECRET
        network_mode: "4G"           # optional
        lte_bands: [3, 7, 28]        # optional
        nr5g_bands: [28, 78]         # optional
        cell_lock:                    # optional
          pci: 123
          earfcn: 3350
        dns:                          # optional
          primary: "1.1.1.1"
          secondary: "1.0.0.1"
    """
    from python_zte_mc801a.daemon import load_watchdog_config, run_daemon

    cfg = load_watchdog_config(config_file)
    run_daemon(cfg, interval=interval)


if __name__ == "__main__":
    typer.run(live)
