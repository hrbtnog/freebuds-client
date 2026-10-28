from __future__ import annotations

import json

from freebuds.config.settings import SETTINGS_VERSION, Settings, SettingsStore


def test_settings_roundtrip(tmp_path) -> None:
    path = tmp_path / "config" / "settings.json"
    store = SettingsStore(path)
    settings = Settings(
        channels=[16, 1],
        connect_timeout=3.5,
        response_timeout=1.5,
        poll_interval=60.0,
        close_to_tray=False,
        last_device="AA:BB:CC:DD:EE:FF",
        last_channels={"AA:BB:CC:DD:EE:FF": 16},
    )
    store.save(settings)

    loaded = store.load()
    assert store.last_load_error is None
    assert loaded.version == SETTINGS_VERSION
    assert loaded.channels == [16, 1]
    assert loaded.connect_timeout == 3.5
    assert loaded.response_timeout == 1.5
    assert loaded.poll_interval == 60.0
    assert loaded.close_to_tray is False
    assert loaded.last_channels == {"AA:BB:CC:DD:EE:FF": 16}
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == SETTINGS_VERSION


def test_settings_missing_returns_defaults(tmp_path) -> None:
    store = SettingsStore(tmp_path / "missing.json")
    settings = store.load()
    assert store.last_load_error is None
    assert settings.channels == [1, 16]


def test_settings_corrupt_file_is_preserved(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{não é json", encoding="utf-8")
    store = SettingsStore(path)
    settings = store.load()
    assert store.last_load_error is not None
    assert settings.channels == [1, 16]
    assert path.read_text(encoding="utf-8") == "{não é json"


def test_settings_sanitizes_invalid_values(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "channels": [0, 31, True, 1, 1, 16, "2"],
                "connect_timeout": -1,
                "response_timeout": "2",
                "poll_interval": 3,
                "close_to_tray": "sim",
                "last_channels": {
                    "aa:bb:cc:dd:ee:ff": 16,
                    "inválido": 1,
                    "AA:BB:CC:DD:EE:FE": 99,
                },
            }
        ),
        encoding="utf-8",
    )
    settings = SettingsStore(path).load()
    assert settings.channels == [1, 16]
    assert settings.connect_timeout == 5.0
    assert settings.response_timeout == 2.0
    assert settings.poll_interval == 30.0
    assert settings.close_to_tray is True
    assert settings.last_channels == {"AA:BB:CC:DD:EE:FF": 16}


def test_remember_channel_persists(tmp_path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    settings = Settings()
    store.remember_channel(settings, "aabbccddeeff", 16)
    loaded = store.load()
    assert loaded.last_device == "AA:BB:CC:DD:EE:FF"
    assert loaded.last_channels["AA:BB:CC:DD:EE:FF"] == 16
