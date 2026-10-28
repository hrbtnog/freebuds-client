"""Modelos de domínio compartilhados pelo core, pela CLI e pela UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _parameters_to_json(parameters: dict[int, bytes]) -> dict[str, str]:
    return {str(key): value.hex(" ") for key, value in sorted(parameters.items())}


@dataclass(slots=True)
class BluetoothDevice:
    """Dispositivo Bluetooth clássico visto pelo Windows."""

    address: str
    name: str = ""
    connected: bool = False
    remembered: bool = False
    authenticated: bool = False
    last_seen: datetime | None = None
    last_used: datetime | None = None
    class_of_device: int | None = None

    @property
    def paired(self) -> bool:
        """Alias semântico para ``fAuthenticated``."""

        return self.authenticated

    @property
    def display_name(self) -> str:
        return self.name or "(sem nome)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "name": self.name,
            "connected": self.connected,
            "remembered": self.remembered,
            "authenticated": self.authenticated,
            "last_seen": self.last_seen.isoformat(timespec="seconds")
            if self.last_seen
            else None,
            "last_used": self.last_used.isoformat(timespec="seconds")
            if self.last_used
            else None,
            "class_of_device": self.class_of_device,
        }


@dataclass(slots=True)
class DeviceInfo:
    """Resposta de ``0x0107`` decodificada sem descartar campos desconhecidos."""

    hardware_version: str | None = None
    software_version: str | None = None
    serial_number: str | None = None
    submodel: str | None = None
    model: str | None = None
    left_serial_number: str | None = None
    right_serial_number: str | None = None
    fields: dict[int, str] = field(default_factory=dict)
    raw_fields: dict[int, bytes] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hardware_version": self.hardware_version,
            "software_version": self.software_version,
            "serial_number": self.serial_number,
            "submodel": self.submodel,
            "model": self.model,
            "left_serial_number": self.left_serial_number,
            "right_serial_number": self.right_serial_number,
            "fields": {str(key): value for key, value in sorted(self.fields.items())},
            "raw_fields": _parameters_to_json(self.raw_fields),
        }


@dataclass(slots=True)
class BatteryState:
    """Leitura de ``0x0108``/notificação ``0x0127``.

    O protocolo varia por modelo. Campos ausentes permanecem ``None``; o valor
    bruto sempre é mantido para inspeção.
    """

    global_level: int | None = None
    left: int | None = None
    right: int | None = None
    case: int | None = None
    charging: bool | None = None
    charging_flags: bytes | None = None
    parameters: dict[int, bytes] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "global": self.global_level,
            "left": self.left,
            "right": self.right,
            "case": self.case,
            "charging": self.charging,
            "charging_flags": self.charging_flags.hex(" ")
            if self.charging_flags is not None
            else None,
            "raw_parameters": _parameters_to_json(self.parameters),
        }


@dataclass(slots=True)
class AncState:
    """Leitura de ``0x2B2A``, incluindo a intensidade do modo adaptável."""

    mode_code: int | None = None
    mode: str | None = None
    level_code: int | None = None
    level: str | None = None
    adaptive_level: int | None = None
    parameters: dict[int, bytes] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_code": self.mode_code,
            "mode": self.mode,
            "level_code": self.level_code,
            "level": self.level,
            "adaptive_level": self.adaptive_level,
            "raw_parameters": _parameters_to_json(self.parameters),
        }


@dataclass(slots=True)
class AdvancedSettings:
    """Preferências do fone confirmadas no FreeBuds Pro 5.

    Cada campo corresponde a uma escrita observada no aplicativo oficial e
    reverificada por leitura no Windows. Recursos sem escrita confirmada
    (multiponto, efeitos espaciais, tons do estojo e deslizar) aparecem apenas
    como leitura. Campos desconhecidos continuam disponíveis em ``raw``.
    """

    sound_profile_id: int | None = None
    custom_eq: bytes | None = None
    custom_name: str | None = None
    spatial_mode: int | None = None
    spatial_effect: int | None = None
    adaptive_volume: bool | None = None
    conversation_awareness: bool | None = None
    head_control: bool | None = None
    head_nod_action: int | None = None
    head_shake_action: int | None = None
    wear_detection: bool | None = None
    multipoint: bool | None = None
    sound_quality: int | None = None
    low_latency: bool | None = None
    one_earbud_anc: bool | None = None
    press_hold_left: int | None = None
    press_hold_right: int | None = None
    pinch_hold_left: int | None = None
    pinch_hold_right: int | None = None
    double_tap_left: int | None = None
    double_tap_right: int | None = None
    triple_tap_left: int | None = None
    triple_tap_right: int | None = None
    swipe_up: int | None = None
    swipe_down: int | None = None
    raw: dict[str, dict[int, bytes]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sound_profile_id": self.sound_profile_id,
            "custom_eq": self.custom_eq.hex(" ") if self.custom_eq else None,
            "custom_name": self.custom_name,
            "spatial_mode": self.spatial_mode,
            "spatial_effect": self.spatial_effect,
            "adaptive_volume": self.adaptive_volume,
            "conversation_awareness": self.conversation_awareness,
            "head_control": self.head_control,
            "head_nod_action": self.head_nod_action,
            "head_shake_action": self.head_shake_action,
            "wear_detection": self.wear_detection,
            "multipoint": self.multipoint,
            "sound_quality": self.sound_quality,
            "low_latency": self.low_latency,
            "one_earbud_anc": self.one_earbud_anc,
            "press_hold_left": self.press_hold_left,
            "press_hold_right": self.press_hold_right,
            "pinch_hold_left": self.pinch_hold_left,
            "pinch_hold_right": self.pinch_hold_right,
            "double_tap_left": self.double_tap_left,
            "double_tap_right": self.double_tap_right,
            "triple_tap_left": self.triple_tap_left,
            "triple_tap_right": self.triple_tap_right,
            "swipe_up": self.swipe_up,
            "swipe_down": self.swipe_down,
            "raw": {
                command: _parameters_to_json(parameters)
                for command, parameters in sorted(self.raw.items())
            },
        }
