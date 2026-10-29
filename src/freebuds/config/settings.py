"""Preferências persistentes em ``%APPDATA%``.

A localização é intencionalmente simples e legível. O arquivo é escrito de
forma atômica para não corromper as preferências se o processo for encerrado.
"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from ..core.transport import KNOWN_CHANNELS
from ..core.util import normalize_address

APP_DIR_NAME = "FreeBudsClient"
SETTINGS_FILE_NAME = "settings.json"
SETTINGS_VERSION = 1


def default_settings_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_DIR_NAME / SETTINGS_FILE_NAME
    # Fallback útil em testes e execução fora do Windows.
    return Path.home() / ".config" / "freebuds-client" / SETTINGS_FILE_NAME


@dataclass(slots=True)
class Settings:
    version: int = SETTINGS_VERSION
    channels: list[int] = field(default_factory=lambda: list(KNOWN_CHANNELS))
    connect_timeout: float = 5.0
    response_timeout: float = 2.0
    poll_interval: float = 30.0
    close_to_tray: bool = True
    language: str = "pt"
    earbud_color: str = "sand"
    last_device: str | None = None
    # Endereço -> canal que funcionou na última sessão.
    last_channels: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        settings = cls()
        raw_channels = data.get("channels")
        if isinstance(raw_channels, list):
            channels: list[int] = []
            for value in raw_channels:
                if (
                    isinstance(value, int)
                    and not isinstance(value, bool)
                    and 1 <= value <= 30
                    and value not in channels
                ):
                    channels.append(value)
            if channels:
                settings.channels = channels

        for name in ("connect_timeout", "response_timeout"):
            value = data.get(name)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                setattr(settings, name, float(value))

        poll_interval = data.get("poll_interval")
        if (
            isinstance(poll_interval, (int, float))
            and not isinstance(poll_interval, bool)
            and 5 <= poll_interval <= 3600
        ):
            settings.poll_interval = float(poll_interval)

        close_to_tray = data.get("close_to_tray")
        if isinstance(close_to_tray, bool):
            settings.close_to_tray = close_to_tray

        language = data.get("language")
        if isinstance(language, str):
            normalized = language.strip().lower().replace("_", "-")
            if normalized.startswith("en"):
                settings.language = "en"
            elif normalized.startswith("pt"):
                settings.language = "pt"

        color = data.get("earbud_color")
        if isinstance(color, str) and color in ("sand", "white", "grey", "blue"):
            settings.earbud_color = color

        last_device = data.get("last_device")
        if isinstance(last_device, str):
            settings.last_device = last_device.strip() or None

        raw_last_channels = data.get("last_channels")
        if isinstance(raw_last_channels, dict):
            for address, channel in raw_last_channels.items():
                if (
                    isinstance(address, str)
                    and isinstance(channel, int)
                    and not isinstance(channel, bool)
                    and 1 <= channel <= 30
                ):
                    try:
                        normalized = normalize_address(address)
                    except ValueError:
                        continue
                    settings.last_channels[normalized] = channel
        return settings


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_settings_path()
        self.last_load_error: str | None = None

    def load(self) -> Settings:
        self.last_load_error = None
        if not self.path.exists():
            return Settings()
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.last_load_error = f"não foi possível ler {self.path}: {exc}"
            return Settings()
        if not isinstance(data, dict):
            self.last_load_error = f"{self.path} não contém um objeto JSON"
            return Settings()
        known = {item.name for item in fields(Settings)}
        filtered = {key: value for key, value in data.items() if key in known}
        try:
            return Settings.from_dict(filtered)
        except (TypeError, ValueError) as exc:
            self.last_load_error = f"configuração inválida em {self.path}: {exc}"
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = settings.to_dict()
        payload["version"] = SETTINGS_VERSION
        temp_path: Path | None = None
        replaced = False
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=self.path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_path, self.path)
            replaced = True
        finally:
            if not replaced and temp_path is not None:
                with suppress(OSError):
                    temp_path.unlink(missing_ok=True)

    def remember_channel(self, settings: Settings, address: str, channel: int) -> None:
        normalized = normalize_address(address)
        settings.last_channels[normalized] = channel
        settings.last_device = normalized
        self.save(settings)
