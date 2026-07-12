import json
import logging
from datetime import datetime
from pathlib import Path

import yaml

log = logging.getLogger("rich")


def check_config(router_ip: str, password: str) -> dict:
    if router_ip and password:
        log.info("Configuration from CLI options")
        return {"router_ip": router_ip, "password": password}
    if router_ip or password:
        log.info("Both router-ip and password CLI options must be provided")
        return None
    if Path("settings.yml").exists():
        with open("settings.yml", "r") as f:
            config = yaml.load(f, Loader=yaml.SafeLoader)
        if (
            config is not None
            and "password" in config
            and "router_ip" in config
        ):
            log.info("Configuration from file: settings.yml")
            return config
    else:
        log.error("Could not locate settings file or CLI settings parameters.")
    return None


def save_monitor_bands(bands, path="settings.yml"):
    """Persist the monitor's full reference band set to settings.yml.

    No-op if the settings file doesn't exist yet -- there is nothing to
    preserve router_ip/password into.
    """
    p = Path(path)
    if not p.exists():
        return
    with open(p, "r") as f:
        config = yaml.safe_load(f) or {}
    config["monitor_bands"] = [int(b) for b in bands]
    with open(p, "w") as f:
        yaml.safe_dump(config, f)


def check_create_data_file():
    if not Path("data.json").exists():
        Path("data.json").touch()
        Path("data.json").write_text('{"signal_data":[]}')


def persist_data(data):
    if data:
        check_create_data_file()

        with open("data.json", "r") as f:
            existing_json_data = json.load(f)

        with open("data.json", "w") as f:
            data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            existing_json_data["signal_data"].append(data)

            json.dump(existing_json_data, f)


def load_data():
    check_create_data_file()

    with open("data.json", "r") as f:
        json_data = json.load(f)

        if "signal_data" in json_data.keys():
            y = [int(x["lte_rsrp"]) for x in json_data["signal_data"][-10:]]
            x = [*range(0, len(y))]

            return x, y

        else:
            return [], []
