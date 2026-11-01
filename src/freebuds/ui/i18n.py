"""Gerenciador de internacionalização da interface.

Os textos ficam em ``locales/pt.json`` e ``locales/en.json``. O português é o
idioma de fallback: se uma chave faltar no inglês, o valor em português é usado
sem quebrar a interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LOCALES_DIR = Path(__file__).with_name("locales")
DEFAULT_LANGUAGE = "pt"
SUPPORTED_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("pt", "Português"),
    ("en", "English"),
    ("es", "Español"),
    ("ru", "Русский"),
    ("zh", "简体中文"),
)
_LANGUAGE_CODES = {code for code, _ in SUPPORTED_LANGUAGES}

_current_language = DEFAULT_LANGUAGE
_current_data: dict[str, Any] = {}
_fallback_data: dict[str, Any] = {}
_cache: dict[str, dict[str, Any]] = {}

# Mapeia valores do protocolo para chaves semânticas nos arquivos de tradução.
_OPTION_KEYS: dict[str, dict[object, str]] = {
    "sound_profile": {
        5: "balanced",
        9: "voice",
        2: "bass",
        201: "classic",
        13: "movie",
        15: "podcast",
        14: "games",
        16: "impact",
        17: "adaptive_eq",
        100: "custom",
    },
    "spatial_mode": {0: "off", 1: "head_tracking", 2: "fixed"},
    "spatial_effect": {
        0: "default",
        1: "theater",
        2: "cinema",
        3: "concert_hall",
    },
    "press_hold": {
        0xFF: "none",
        0x0A: "noise_control",
        0x00: "voice_assistant",
    },
    "pinch_hold": {0xFF: "none", 0x06: "noise_control"},
    "double_tap": {0xFF: "none", 0x01: "play_pause"},
    "triple_tap": {0xFF: "none", 0x07: "previous", 0x02: "next"},
    "head_nod": {0: "none", 1: "answer_call"},
    "head_shake": {0: "none", 2: "reject_call"},
    "swipe": {0: "none", 2: "adjust_volume"},
    "quality": {0: "connection", 1: "quality"},
    "anc_mode": {
        "normal": "normal",
        "cancellation": "cancellation",
        "awareness": "awareness",
    },
    "anc_level": {
        "normal": "normal",
        "comfort": "comfort",
        "ultra": "ultra",
        "dynamic": "dynamic",
        "voice_boost": "voice_boost",
        "adaptive": "adaptive",
    },
}


def normalize_language(code: str | None) -> str:
    """Aceita ``pt``, ``en``, ``es``, ``ru``, ``zh`` e variações (ex.: ``pt-BR``, ``zh-CN``)."""

    if not code:
        return DEFAULT_LANGUAGE
    normalized = code.strip().lower().replace("_", "-")
    prefix = normalized.split("-", 1)[0]
    return prefix if prefix in _LANGUAGE_CODES else DEFAULT_LANGUAGE


def _load_file(language: str) -> dict[str, Any]:
    path = LOCALES_DIR / f"{language}.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _load(language: str) -> dict[str, Any]:
    if language not in _cache:
        _cache[language] = _load_file(language)
    return _cache[language]


def set_language(code: str | None) -> str:
    """Define o idioma atual e devolve o código canônico usado."""

    global _current_language, _current_data, _fallback_data
    _fallback_data = _load(DEFAULT_LANGUAGE)
    language = normalize_language(code)
    data = _load(language)
    if language != DEFAULT_LANGUAGE and not data:
        language = DEFAULT_LANGUAGE
    _current_language = language
    _current_data = data if data else _fallback_data
    return _current_language


def get_language() -> str:
    return _current_language


def language_options() -> tuple[tuple[str, str], ...]:
    return SUPPORTED_LANGUAGES


def language_name(code: str | None) -> str:
    normalized = normalize_language(code)
    for language, name in SUPPORTED_LANGUAGES:
        if language == normalized:
            return name
    return normalized


def _lookup(data: dict[str, Any], key: str) -> Any:
    value: Any = data
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def t(key: str, default: str | None = None, **values: object) -> str:
    """Traduz uma chave, com fallback para o português e para ``default``."""

    if not _current_data:
        set_language(_current_language)
    value = _lookup(_current_data, key)
    if value is None and _current_data is not _fallback_data:
        value = _lookup(_fallback_data, key)
    if value is None:
        value = default if default is not None else key
    if not isinstance(value, str):
        value = default if default is not None else key
    if values:
        try:
            value = value.format(**values)
        except (KeyError, ValueError):
            pass
    return value


def option_label(category: str, value: object, fallback: str) -> str:
    """Traduz um valor de opção do protocolo, mantendo o fallback antigo."""

    key = _OPTION_KEYS.get(category, {}).get(value)
    if key is None:
        return fallback
    return t(f"options.{category}.{key}", default=fallback)


def reset_for_tests() -> None:
    """Volta ao português (usado apenas pela suíte de testes)."""

    _cache.clear()
    set_language(DEFAULT_LANGUAGE)
