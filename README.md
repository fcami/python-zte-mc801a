# python-zte-mc801a

Python CLI and library for the ZTE MC801a / MC888 5G CPE router.

![Python ZTE MC801a Live View](docs/images/live-view.png?raw=true "Live View")

## What is this?

A command-line tool and Python library to manage the ZTE MC801A router.
It can query signal data, lock LTE and 5G bands, lock to a specific cell,
change network mode, configure DNS, and run a watchdog daemon to keep
settings stable.

Original idea and inspiration from the JavaScript code by
[Miononno](https://miononno.it/).

## Status

**Alpha / Beta.** The features listed below seem to work but the API and CLI
interface may change between releases. Bug reports and contributions are welcome.

## Warning

**This is not an official client. The authors have no affiliation with ZTE.**
READ operations are safe. WRITE operations (band locking, cell locking, DNS,
network mode, reboot) modify router state and could — in extreme cases — require
a factory reset. Use at your own risk.

## Features

| Feature                    | Type  | CLI command        |
| -------------------------- | ----- | ------------------ |
| Comprehensive status       | READ  | `status`           |
| Device version info        | READ  | `info`             |
| Signal data (raw/processed)| READ  | `data`             |
| LTE band lock state        | READ  | `lte-band-info`    |
| Live dashboard             | READ  | `live`             |
| Network mode switching     | WRITE | `set-mode`         |
| LTE band locking           | WRITE | `lock-lte-bands`   |
| 5G NR band locking         | WRITE | `lock-5g-bands`    |
| Cell locking (PCI+EARFCN)  | WRITE | `lock-cell`        |
| Cell lock removal          | WRITE | `unlock-cell`      |
| DNS configuration          | WRITE | `set-dns`          |
| Reboot                     | WRITE | `reboot`           |
| 5G PCI forcing             | WRITE | `force-5g-pci`     |
| Watchdog daemon             | WRITE | `watchdog`         |

## Compatibility

| Firmware                          | Operator  | Status               |
| --------------------------------- | --------- | -------------------- |
| BD_UKH3GMC801AV1.0.0B15          | Three UK  | All features working |
| BD_XCBZHKMC801A ProV1.0.0B03     | Free (FR) | All features working |

## Installation

```bash
pip install python-zte-mc801a
```

Or install directly from the repository:

```bash
pip install git+https://github.com/nicjac/python-zte-mc801a
```

## Quick start

### 1. Save credentials (optional)

```bash
python-zte-mc801a setup
```

This creates a `settings.yml` file so you don't have to pass `--router-ip`
and `--password` to every command. You can always override them on the command
line.

### 2. Check router status

```bash
python-zte-mc801a status
```

Shows network mode, 4G cell info (PCI, EARFCN, band, RSRP/RSRQ/RSSI/SNR),
carrier aggregation details, 5G cell info, band locks, cell lock, DNS, and
modem temperatures — all in one view.

### 3. Show device info

```bash
python-zte-mc801a info
```

### 4. Show signal data

```bash
python-zte-mc801a data            # processed
python-zte-mc801a data --raw      # raw JSON from the router
```

## Band locking

### LTE bands

```bash
# Lock to B3 + B7 + B28
python-zte-mc801a lock-lte-bands 3,7,28

# Check current lock state
python-zte-mc801a lte-band-info
```

### 5G NR bands

```bash
# Lock to n78
python-zte-mc801a lock-5g-bands 78

# Lock to n28 + n78
python-zte-mc801a lock-5g-bands 28,78
```

## Cell locking

Lock to a specific cell identified by its PCI and EARFCN. Use `status` to
find the values of the cell you're connected to.

```bash
# Set cell lock (requires reboot to take effect)
python-zte-mc801a lock-cell 116 3350

# Set cell lock and reboot immediately
python-zte-mc801a lock-cell 116 3350 --reboot

# Remove cell lock
python-zte-mc801a unlock-cell --reboot
```

## Network mode

```bash
python-zte-mc801a set-mode 4G         # LTE only
python-zte-mc801a set-mode 5G_NSA     # 5G Non-Standalone (4G anchor + 5G)
python-zte-mc801a set-mode 5G_SA      # 5G Standalone only
python-zte-mc801a set-mode 5G+4G+3G   # All networks
```

Valid modes: `5G+4G+3G`, `5G_NSA`, `5G_SA`, `4G+5G`, `4G+3G`, `4G`, `3G`.

## DNS configuration

```bash
python-zte-mc801a set-dns 1.1.1.1,1.0.0.1     # Cloudflare
python-zte-mc801a set-dns 8.8.8.8,8.8.4.4     # Google
python-zte-mc801a set-dns auto                 # Revert to provider DNS
```

## Reboot

```bash
python-zte-mc801a reboot
```

## Live dashboard

```bash
python-zte-mc801a live                    # default: SMS view
python-zte-mc801a live --viz power-4g     # 4G signal power graph
python-zte-mc801a live --viz power-5g     # 5G signal power graph
```

## Watchdog daemon

The watchdog monitors router state at a regular interval and re-applies
desired settings if the router drifts (e.g. after a reconnection).

```bash
python-zte-mc801a watchdog                        # default: watchdog.yml, 30s
python-zte-mc801a watchdog my-config.yml --interval 60
```

Configuration file format (see `watchdog.yml.example`):

```yaml
router_ip: "192.0.2.1"
password: "YOUR_PASSWORD"

# All settings below are optional — only include what you want to enforce.

network_mode: "4G"        # 5G+4G+3G, 5G_NSA, 5G_SA, 4G+5G, 4G+3G, 4G, 3G
lte_bands: [3, 7, 28]     # LTE band numbers to lock to
nr5g_bands: [28, 78]      # NR band numbers to lock to

cell_lock:
  pci: 123
  earfcn: 3350

dns:
  primary: "1.1.1.1"
  secondary: "1.0.0.1"
```

## Using as a library

```python
from python_zte_mc801a.lib.router_requests import (
    get_auth_cookies,
    get_network_info,
    set_lte_band,
    set_5g_band,
    set_network_mode,
    lock_cell,
    set_dns,
    reboot_device,
    NETWORK_MODES,
)

cookies = get_auth_cookies("192.0.2.1", "password")
info = get_network_info("192.0.2.1", cookies)
print(info)

# Lock LTE to B3+B7+B28
set_lte_band("192.0.2.1", cookies, [3, 7, 28], verbose=True)

# Lock 5G to n78
set_5g_band("192.0.2.1", cookies, "78", verbose=True)

# Switch to LTE only
set_network_mode("192.0.2.1", cookies, NETWORK_MODES["4G"], verbose=True)
```

## Development

```bash
git clone https://github.com/nicjac/python-zte-mc801a
cd python-zte-mc801a
pip install -e ".[dev]"   # or: poetry install

# Lint
pylint python_zte_mc801a/
flake8 python_zte_mc801a/
```

## License

[MIT](LICENSE)
