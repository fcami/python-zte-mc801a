"""Tests for save_monitor_bands (C6 persistence)."""
import yaml

from python_zte_mc801a.client.data_io import save_monitor_bands


def test_save_monitor_bands_writes_and_preserves_creds(tmp_path):
    settings = tmp_path / "settings.yml"
    settings.write_text(yaml.safe_dump({"router_ip": "192.0.2.1", "password": "secret"}))

    save_monitor_bands([3, "7", 28], path=str(settings))

    config = yaml.safe_load(settings.read_text())
    assert config["monitor_bands"] == [3, 7, 28]
    assert config["router_ip"] == "192.0.2.1"
    assert config["password"] == "secret"


def test_save_monitor_bands_noop_when_file_missing(tmp_path):
    settings = tmp_path / "settings.yml"

    save_monitor_bands([3, 7, 28], path=str(settings))

    assert not settings.exists()
