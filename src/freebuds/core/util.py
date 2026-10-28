"""Utilitários sem dependência de Windows ou Qt."""

from __future__ import annotations

import re
from datetime import datetime

_ADDRESS_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]?){5}[0-9A-Fa-f]{2}$")
_HUAWEI_HINTS = ("huawei", "honor", "freebuds", "freearc", "freelace", "freeclip")


def normalize_address(value: str) -> str:
    """Normaliza um endereço Bluetooth para ``AA:BB:CC:DD:EE:FF``.

    Aceita dois-pontos, hífens ou os 12 dígitos hexadecimais sem separador.
    Levanta ``ValueError`` para entradas inválidas.
    """

    text = value.strip()
    if not _ADDRESS_RE.fullmatch(text):
        raise ValueError(f"Endereço Bluetooth inválido: {value!r}")
    digits = re.sub(r"[^0-9A-Fa-f]", "", text)
    if len(digits) != 12:
        raise ValueError(f"Endereço Bluetooth inválido: {value!r}")
    return ":".join(digits.upper()[i : i + 2] for i in range(0, 12, 2))


def is_huawei_device_name(name: str | None) -> bool:
    """Heurística apenas para filtro de descoberta, não para protocolo."""

    if not name:
        return False
    lowered = name.casefold()
    return any(hint in lowered for hint in _HUAWEI_HINTS)


def systemtime_to_datetime(value: object) -> datetime | None:
    """Converte um ``SYSTEMTIME`` do ctypes em ``datetime``, se preenchido."""

    year = int(getattr(value, "wYear", 0))
    month = int(getattr(value, "wMonth", 0))
    day = int(getattr(value, "wDay", 0))
    if year < 1601 or not (1 <= month <= 12) or not (1 <= day <= 31):
        return None
    try:
        return datetime(
            year,
            month,
            day,
            int(getattr(value, "wHour", 0)),
            int(getattr(value, "wMinute", 0)),
            int(getattr(value, "wSecond", 0)),
        )
    except ValueError:
        return None
