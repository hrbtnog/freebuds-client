from __future__ import annotations

from datetime import datetime

import pytest

from freebuds.core.models import AncState, BatteryState, BluetoothDevice, DeviceInfo
from freebuds.core.util import (
    is_huawei_device_name,
    normalize_address,
    systemtime_to_datetime,
)


def test_normalize_address() -> None:
    expected = "AA:BB:CC:DD:EE:FF"
    assert normalize_address("aabbccddeeff") == expected
    assert normalize_address("AA-BB-CC-DD-EE-FF") == expected
    assert normalize_address(" aa:bb:cc:dd:ee:ff ") == expected
    with pytest.raises(ValueError):
        normalize_address("AA:BB:CC:DD:EE")
    with pytest.raises(ValueError):
        normalize_address("AA:BB:CC:DD:EE:FG")


def test_huawei_name_filter() -> None:
    assert is_huawei_device_name("HUAWEI FreeBuds Pro 5")
    assert is_huawei_device_name("FreeBuds 5i")
    assert is_huawei_device_name("HONOR Earbuds")
    assert not is_huawei_device_name("JBL Flip 7")
    assert not is_huawei_device_name("")


def test_systemtime_to_datetime() -> None:
    class Time:
        wYear = 2026
        wMonth = 10
        wDay = 21
        wHour = 15
        wMinute = 4
        wSecond = 5

    assert systemtime_to_datetime(Time()) == datetime(2026, 10, 21, 15, 4, 5)

    class Empty:
        wYear = 0
        wMonth = 0
        wDay = 0

    assert systemtime_to_datetime(Empty()) is None


def test_model_json_keeps_raw_bytes_as_hex() -> None:
    device = BluetoothDevice(
        address="AA:BB:CC:DD:EE:FF",
        name="FreeBuds",
        connected=True,
        authenticated=True,
        last_seen=datetime(2026, 10, 21, 15, 4, 5),
    )
    data = device.to_dict()
    assert data["address"] == "AA:BB:CC:DD:EE:FF"
    assert data["last_seen"] == "2026-10-21T15:04:05"

    info = DeviceInfo(
        model="FreeBuds",
        fields={3: "HW"},
        raw_fields={3: b"HW"},
    )
    info_json = info.to_dict()
    assert info_json["raw_fields"] == {"3": "48 57"}

    battery = BatteryState(left=10, right=20, case=30, charging=False)
    assert battery.to_dict()["charging"] is False

    anc = AncState(mode_code=1, mode="cancellation", level_code=1, level="comfort")
    assert anc.to_dict()["mode"] == "cancellation"
