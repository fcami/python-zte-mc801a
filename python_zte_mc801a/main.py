import typer
import yaml

from python_zte_mc801a.lib.data_processing import process_data
from python_zte_mc801a.lib.router_requests import (
    get_auth_cookies, get_signal_data, set_lte_band, get_lte_band_lock,
    set_5g_band, set_network_mode, get_network_mode,
    NETWORK_MODES, NETWORK_MODES_REVERSE,
)
from python_zte_mc801a.lib.constants import lte_mask_to_bands

from python_zte_mc801a.lib.helpers import force_5g_pci_selection

from python_zte_mc801a.client.live import show_live, LIVE_VISUALIZATIONS

from python_zte_mc801a.client.data_io import check_config

from rich.pretty import pprint
from rich.console import Console
from rich.prompt import Prompt
from rich.padding import Padding

from python_zte_mc801a.lib.constants import ALL_5G_BANDS

import logging
from rich.logging import RichHandler

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


@app.command()
def status(
    router_ip: str = typer.Option(None),
    password: str = typer.Option(None),
):
    """Show current network mode, active bands, and band lock state"""
    config = check_config(router_ip, password)
    if not config:
        return
    cookies = get_auth_cookies(config["router_ip"], config["password"])

    import requests
    r = requests.get(
        f'http://{config["router_ip"]}/goform/goform_get_cmd_process?isTest=false'
        '&cmd=network_type,net_select,wan_active_band,lte_band,lte_ca_pcell_band,'
        'lte_ca_pcell_bandwidth,lte_multi_ca_scell_info,'
        'nr5g_action_band,nr5g_action_channel,'
        'lte_band_ext_1_64,nr5g_sa_band_lock,nr5g_nsa_band_lock'
        '&multi_data=1',
        cookies=cookies, headers={"referer": f'http://{config["router_ip"]}/'}
    )
    d = r.json()

    mode_raw = d.get("net_select", "")
    mode_label = NETWORK_MODES_REVERSE.get(mode_raw, mode_raw)
    console.print(f"[bold]Network mode[/bold]       : {mode_label} ({mode_raw})")
    console.print(f"[bold]Connection type[/bold]    : {d.get('network_type', '')}")
    console.print()

    console.print(f"[bold]Active 4G band[/bold]     : {d.get('wan_active_band', '')} (band {d.get('lte_band', '')})")
    bw = d.get("lte_ca_pcell_bandwidth", "")
    if bw:
        console.print(f"[bold]4G PCell[/bold]           : B{d.get('lte_ca_pcell_band', '')} ({round(float(bw))} MHz)")
    ca = d.get("lte_multi_ca_scell_info", "")
    if ca:
        console.print(f"[bold]4G CA SCells[/bold]       : {ca}")
    nr_band = d.get("nr5g_action_band", "")
    if nr_band:
        console.print(f"[bold]Active 5G band[/bold]     : {nr_band} (ch {d.get('nr5g_action_channel', '')})")
    console.print()

    lte_mask = d.get("lte_band_ext_1_64", "")
    if lte_mask and int(lte_mask, 16) != 0:
        console.print(f"[bold]LTE band lock[/bold]      : {lte_mask_to_bands(lte_mask)}")
    else:
        console.print("[bold]LTE band lock[/bold]      : (all bands)")
    sa = d.get("nr5g_sa_band_lock", "")
    nsa = d.get("nr5g_nsa_band_lock", "")
    if sa:
        console.print(f"[bold]5G SA band lock[/bold]    : {sa}")
    if nsa:
        console.print(f"[bold]5G NSA band lock[/bold]   : {nsa}")


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


if __name__ == "__main__":
    typer.run(live)
