import math
import hashlib


def process_data(raw_data: dict) -> dict:
    """Process raw data to produce usable data

    Args:
        data (dict): Raw data

    Returns:
        dict: Processed signal data
    """
    processed_data = {}

    processed_data["4G"] = process_data_4g(raw_data)
    processed_data["4G_CA"] = process_ca_4g_data(raw_data)
    processed_data["CELL AND NETWORK"] = process_data_cell(raw_data)
    processed_data["5G"] = process_5g_data(raw_data)
    processed_data["MISC"] = process_misc_data(raw_data)

    return processed_data


def process_misc_data(data: dict) -> dict:
    """Process misc. data such as temperature and firmware version

    Args:
        data (dict): Raw data

    Returns:
        dict: Processed data
    """
    processed_data = {}

    processed_data["TEMPERATURE_4G"] = {
        "desc": "Temperature 4G",
        "str_value": f"{data['pm_sensor_mdm']}",
    }

    processed_data["TEMPERATURE_5G"] = {
        "desc": "Temperature 4G",
        "str_value": f"{data['pm_modem_5g']}",
    }

    processed_data["FIRMWARE_VERSION"] = {
        "desc": "Firmware Version",
        "str_value": f"{data['wa_inner_version']}",
    }

    return processed_data


def process_ca_4g_data(data: dict) -> list:
    """Process carrier aggregation data

    Args:
        data (dict): Raw data

    Returns:
        dict: Processed data
    """
    ca_4g_processed_data = []

    if len(data["lte_multi_ca_scell_info"]):
        ca_4g = data["lte_multi_ca_scell_info"].split(";")

        for chan in ca_4g:
            chan_details = chan.split(",")
            ca_4g_processed_data.append(
                [
                    chan_details[1],
                    chan_details[4],
                    f"{chan_details[3]} ({round(float(chan_details[5]))}Mhz)",
                ]
            )

    return ca_4g_processed_data


def process_5g_data(data: dict) -> dict:
    """Process 5G-related data

    Args:
        data (dict): Raw data

    Returns:
        dict: Processed data
    """
    processed_data = {}

    processed_data["PCI"] = {
        "desc": "PCI",
        "str_value": f"{int(data['nr5g_pci'],base=16)}",
    }

    processed_data["EARFCN"] = {
        "desc": "EARFCN",
        "str_value": data["nr5g_action_channel"],
    }

    processed_data["Bands"] = {
        "desc": "Bands",
        "str_value": f"{data['nr5g_action_band']}",
    }

    processed_data["RSRP"] = {
        "desc": "RSRP [Power]",
        "str_value": f"{data['Z5g_rsrp']}dB",
    }

    processed_data["SNR"] = {
        "desc": "SNR [Noise]",
        "str_value": f"{data['Z5g_SINR']}dB",
    }

    return processed_data


def process_data_cell(data: dict) -> dict:
    """Process general cell data

    Args:
        data (dict): Raw data

    Returns:
        dict: Processed data
    """

    processed_data = {}

    processed_data["CELL_ID"] = {
        "desc": "Cell ID",
        "str_value": f'{int(data["cell_id"], base=16)}',
    }

    processed_data["ENBID"] = {
        "desc": "ENBID",
        "str_value": math.trunc(int(data["cell_id"], base=16) / 256),
    }

    processed_data["NETWORK_TYPE"] = {
        "desc": "Network Type",
        "str_value": data["network_type"],
    }

    processed_data["NETWORK_PROVIDER"] = {
        "desc": "Provider",
        "str_value": data["network_provider"],
    }

    if len(data["wan_lte_ca"]):
        processed_data["CA_STATUS"] = {"desc": "CA Status", "str_value": "🟢 Active"}
    else:
        processed_data["CA_STATUS"] = {"desc": "CA Status", "str_value": "🔴 Inactive"}

    processed_data["WAN_WIP"] = {
        "desc": "WAN IP",
        "str_value": data["wan_ipaddr"],
    }

    processed_data["APN"] = {
        "desc": "APN",
        "str_value": data["wan_apn"],
    }

    return processed_data


def process_data_4g(data: dict) -> dict:
    """Process 4G-related data

    Args:
        data (dict): Raw data

    Returns:
        dict: Processed data
    """
    processed_data = {}

    if len(data["lte_pci"]):
        lock_str = ""

        if str(int(data["lte_pci"], base=16)) == data["lte_pci_lock"]:
            lock_str = "🔒"

        processed_data["4G_PCI"] = {
            "desc": "PCI",
            "str_value": f"{lock_str}{int(data['lte_pci'],base=16)}",
        }
    else:
        processed_data["4G_PCI"] = {"desc": "PCI", "str_value": ""}

    lock_str = ""

    if data["wan_active_channel"] == data["lte_earfcn_lock"]:
        lock_str = "🔒"

    processed_data["4G_EARFCN"] = {
        "desc": "EARFCN",
        "str_value": f'{lock_str}{data["wan_active_channel"]}',
    }

    if len(data["lte_ca_pcell_bandwidth"]):
        processed_data["4G_BANDS"] = {
            "desc": "Bands",
            "str_value": (
                f"{data['lte_ca_pcell_band']}"
                f" ({round(float(data['lte_ca_pcell_bandwidth']))}Mhz)"
            ),
        }
    else:
        processed_data["4G_BANDS"] = {
            "desc": "Bands",
            "str_value": f"{data['wan_active_band']}",
        }

    processed_data["4G_RSRP"] = {
        "desc": "RSRP [Power]",
        "str_value": f"{data['lte_rsrp']}dB",
    }

    processed_data["4G_RSRQ"] = {
        "desc": "RSRQ [Quality]",
        "str_value": f"{data['lte_rsrq']}dB",
    }

    processed_data["4G_RSSI"] = {"desc": "RSSI", "str_value": f"{data['lte_rssi']}dB"}

    processed_data["4G_SNR"] = {
        "desc": "SNR [Noise]",
        "str_value": f"{data['lte_snr']}dB",
    }

    return processed_data


def get_ad_value(raw_data: dict) -> str:
    """Retrieve AD value for write operations.

    The router JS computes: AD = SHA256(SHA256(wa_inner_version + cr_version) + RD)
    (cookWithRequest is SHA256, confirmed from util.js on the router).

    Args:
        raw_data (dict): Raw data containing wa_inner_version, cr_version, RD

    Returns:
        str: AD value (hex digest)
    """
    # The router's JS SHA256 outputs UPPERCASE hex (p=1 in util.js).
    h1 = hashlib.sha256(
        (raw_data["wa_inner_version"] + raw_data["cr_version"]).encode()
    ).hexdigest().upper()

    return hashlib.sha256((h1 + raw_data["RD"]).encode()).hexdigest().upper()
