from __future__ import annotations

import ctypes
import json
import sys

import pytest

from freebuds.cli import app
from freebuds.config.settings import SettingsStore
from freebuds.core.models import AncState, BatteryState, BluetoothDevice, DeviceInfo


def test_cli_decode_json(capsys) -> None:
    code = app.main(["decode", "--json", "5A0006002B03080100A79D"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frames"][0]["command"] == "2B 03"
    assert payload["frames"][0]["crc_valid"] is True
    assert payload["frames"][0]["parameters"][0]["type"] == 8


def test_cli_ui_command_is_registered() -> None:
    parser = app._build_parser()
    args = parser.parse_args(["ui", "--address", "AA:BB:CC:DD:EE:FF"])
    assert args.command == "ui"
    assert args.func is app.cmd_ui
    assert args.address == "AA:BB:CC:DD:EE:FF"


def test_cli_decode_invalid_crc_still_analyses(capsys) -> None:
    bad = "5A0006002B03080100A79E"
    code = app.main(["decode", "--json", bad])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frames"][0]["crc_valid"] is False


def test_cli_decode_file_with_offset_and_ascii_gutter(tmp_path, capsys) -> None:
    capture = tmp_path / "spp.txt"
    capture.write_text(
        "# captura\n"
        "0000  5A 00 06 00 2B 03 08 01 00 A7 9D  |Z.....+....|\n",
        encoding="utf-8",
    )
    code = app.main(["decode", "--json", "--file", str(capture)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frames"][0]["raw"] == "5A 00 06 00 2B 03 08 01 00 A7 9D"


def test_cli_decode_bad_hex_returns_error(capsys) -> None:
    code = app.main(["decode", "ZZ"])
    assert code == 1
    assert "erro:" in capsys.readouterr().err


def test_cli_probe_orchestration_and_channel_persistence(tmp_path, monkeypatch, capsys) -> None:
    device = BluetoothDevice(
        address="AA:BB:CC:DD:EE:FF",
        name="HUAWEI FreeBuds Pro 5",
        connected=True,
        authenticated=True,
    )
    monkeypatch.setattr(app, "enumerate_devices", lambda *args, **kwargs: [device])

    calls: list[int] = []

    def fake_probe_channel(**kwargs):
        calls.append(kwargs["channel"])
        if kwargs["channel"] == 1:
            return {
                "ok": False,
                "channel": 1,
                "error": "canal errado",
                "transactions": [],
                "warnings": [],
            }
        return {
            "ok": True,
            "channel": 16,
            "error": None,
            "info": DeviceInfo(model="FreeBuds Pro 5", software_version="1.2.3"),
            "battery": BatteryState(global_level=90, left=91, right=92, case=80),
            "anc": AncState(mode_code=1, mode="cancellation", level_code=1, level="comfort"),
            "notifications": [],
            "transactions": [],
            "warnings": [],
            "parser_issues": [],
        }

    monkeypatch.setattr(app, "_probe_one_channel", fake_probe_channel)
    settings_path = tmp_path / "settings.json"
    code = app.main(
        [
            "--settings",
            str(settings_path),
            "probe",
            "--name",
            "FreeBuds",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["channel"] == 16
    assert payload["info"]["model"] == "FreeBuds Pro 5"
    assert payload["battery"]["global"] == 90
    assert calls == [1, 16]
    loaded = SettingsStore(settings_path).load()
    assert loaded.last_channels["AA:BB:CC:DD:EE:FF"] == 16


def test_cli_probe_listen_prints_anc_notification(
    tmp_path, monkeypatch, capsys
) -> None:
    from freebuds.core.protocol import parse_frame

    device = BluetoothDevice(
        address="AA:BB:CC:DD:EE:FF", name="HUAWEI FreeBuds Pro 5"
    )
    monkeypatch.setattr(app, "enumerate_devices", lambda *args, **kwargs: [device])
    notification = parse_frame(
        bytes.fromhex("5A000A002B2A010203010201007080")
    )
    monkeypatch.setattr(
        app,
        "_probe_one_channel",
        lambda **kwargs: {
            "ok": True,
            "channel": 1,
            "error": None,
            "info": DeviceInfo(model="BTFT0023"),
            "battery": BatteryState(global_level=90),
            "anc": AncState(mode_code=1, mode="cancellation", level_code=3, level="dynamic"),
            "notifications": [notification],
            "transactions": [],
            "warnings": [],
            "parser_issues": [],
        },
    )
    code = app.main(
        [
            "--settings",
            str(tmp_path / "settings.json"),
            "probe",
            "--name",
            "FreeBuds",
            "--listen",
            "1",
        ]
    )
    assert code == 0
    output = capsys.readouterr().out
    assert "ANC: modo=cancelamento nível=dynamic" in output


def test_cli_probe_all_channels_fail(tmp_path, monkeypatch, capsys) -> None:
    device = BluetoothDevice(
        address="AA:BB:CC:DD:EE:FF", name="HUAWEI FreeBuds Pro 5"
    )
    monkeypatch.setattr(app, "enumerate_devices", lambda *args, **kwargs: [device])
    monkeypatch.setattr(
        app,
        "_probe_one_channel",
        lambda **kwargs: {
            "ok": False,
            "channel": kwargs["channel"],
            "error": "offline",
            "transactions": [],
            "warnings": [],
        },
    )
    code = app.main(
        [
            "--settings",
            str(tmp_path / "settings.json"),
            "probe",
            "--name",
            "FreeBuds",
            "--json",
            "--channel",
            "1",
        ]
    )
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["attempts"][0]["channel"] == 1


@pytest.mark.skipif(sys.platform != "win32", reason="estruturas Bluetooth do Windows")
def test_windows_address_conversion() -> None:
    from types import SimpleNamespace

    from freebuds.core.windows_bt import (
        address_from_bluetooth_address,
        address_to_ullong,
    )

    assert address_to_ullong("aabbccddeeff") == 0xAABBCCDDEEFF
    raw = SimpleNamespace(rgBytes=[0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA])
    assert address_from_bluetooth_address(raw) == "AA:BB:CC:DD:EE:FF"


@pytest.mark.skipif(sys.platform != "win32", reason="estruturas Bluetooth do Windows")
def test_windows_struct_sizes() -> None:
    from freebuds.core import windows_bt

    assert ctypes.sizeof(windows_bt.BLUETOOTH_DEVICE_INFO) == 560
    assert ctypes.sizeof(windows_bt.BLUETOOTH_DEVICE_SEARCH_PARAMS) in (32, 40)
