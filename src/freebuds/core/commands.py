"""Comandos e decodificação semântica do protocolo Huawei.

As escritas abaixo foram capturadas no aplicativo oficial e validadas de forma
reversível no FreeBuds Pro 5 via SPP no Windows. Recursos que não produziram
uma escrita confirmada permanecem somente leitura. Nenhum opcode é inventado:
campos desconhecidos continuam preservados em bruto.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import AdvancedSettings, AncState, BatteryState, DeviceInfo
from .protocol import HuaweiFrame, encode_frame

CMD_DEVICE_INFO = b"\x01\x07"
CMD_BATTERY = b"\x01\x08"
CMD_BATTERY_NOTIFY = b"\x01\x27"
CMD_ANC = b"\x2B\x2A"
CMD_ANC_WRITE = b"\x2B\x04"
CMD_ANC_CHANGED = b"\x2B\x03"
CMD_SOUND_PROFILE = b"\x2B\x49"
CMD_SOUND_PROFILE_STATE = b"\x2B\x4A"
CMD_AUDIO_FEATURE = b"\x2B\xB4"
CMD_WEAR_STATE = b"\x2B\x11"
CMD_WEAR_WRITE = b"\x2B\x10"
CMD_MULTIPOINT_STATE = b"\x2B\x2F"
CMD_SOUND_QUALITY_WRITE = b"\x2B\xA2"
CMD_SOUND_QUALITY_STATE = b"\x2B\xA3"
CMD_LOW_LATENCY = b"\x2B\x6C"
CMD_PRESS_HOLD_STATE = b"\x2B\x17"
CMD_PRESS_HOLD_WRITE = b"\x2B\x16"
CMD_PINCH_HOLD_STATE = b"\x2B\x93"
CMD_PINCH_HOLD_WRITE = b"\x2B\x92"
CMD_DOUBLE_TAP_STATE = b"\x01\x20"
CMD_DOUBLE_TAP_WRITE = b"\x01\x1F"
CMD_TRIPLE_TAP_STATE = b"\x01\x26"
CMD_TRIPLE_TAP_WRITE = b"\x01\x25"
CMD_SWIPE_STATE = b"\x2B\x19"

# Apenas nomes para exibição em capturas. A presença aqui não significa que o
# comando seja emitido ou que a escrita esteja implementada.
COMMAND_NAMES: dict[bytes, str] = {
    CMD_DEVICE_INFO: "GET_DEVICE_INFO",
    CMD_BATTERY: "GET_BATTERY",
    CMD_BATTERY_NOTIFY: "BATTERY_NOTIFY",
    CMD_ANC: "GET_ANC",
    CMD_ANC_WRITE: "SET_ANC",
    CMD_ANC_CHANGED: "ANC_CHANGED",
    CMD_SOUND_PROFILE: "SET_SOUND_PROFILE",
    CMD_SOUND_PROFILE_STATE: "GET_SOUND_PROFILE",
    CMD_AUDIO_FEATURE: "AUDIO_FEATURE",
    CMD_WEAR_STATE: "GET_WEAR_DETECTION",
    CMD_WEAR_WRITE: "SET_WEAR_DETECTION",
    CMD_MULTIPOINT_STATE: "GET_MULTIPOINT",
    CMD_SOUND_QUALITY_WRITE: "SET_SOUND_QUALITY",
    CMD_SOUND_QUALITY_STATE: "GET_SOUND_QUALITY",
    CMD_LOW_LATENCY: "LOW_LATENCY",
    CMD_PRESS_HOLD_STATE: "GET_PRESS_HOLD",
    CMD_PRESS_HOLD_WRITE: "SET_PRESS_HOLD",
    CMD_PINCH_HOLD_STATE: "GET_PINCH_HOLD",
    CMD_PINCH_HOLD_WRITE: "SET_PINCH_HOLD",
    CMD_DOUBLE_TAP_STATE: "GET_DOUBLE_TAP",
    CMD_DOUBLE_TAP_WRITE: "SET_DOUBLE_TAP",
    CMD_TRIPLE_TAP_STATE: "GET_TRIPLE_TAP",
    CMD_TRIPLE_TAP_WRITE: "SET_TRIPLE_TAP",
    CMD_SWIPE_STATE: "GET_SWIPE",
}

SOUND_PROFILES: dict[int, str] = {
    5: "Equilibrado",
    9: "Voz",
    2: "Graves",
    201: "Clássico",
    13: "Filme",
    15: "Podcast",
    14: "Jogos",
    16: "Impacto",
    17: "EQ adaptável",
    100: "Personalizado",
}

SOUND_PROFILE_CUSTOM = 100
SOUND_PROFILE_CLASSIC = 201
SOUND_PROFILE_CLASSIC_EQ = bytes.fromhex("fb141e0a0000e7f60a00")
SOUND_PROFILE_CLASSIC_NAME = b"201"

SPATIAL_MODES: dict[int, str] = {
    0: "Desativado",
    1: "Acompanhamento da cabeça",
    2: "Fixo",
}

SPATIAL_EFFECTS: dict[int, str] = {
    0: "Padrão",
    1: "Teatro",
    2: "Cinema",
    3: "Sala de espetáculos",
}

AUDIO_FEATURE_ADAPTIVE_VOLUME = 0x02
AUDIO_FEATURE_CONVERSATION = 0x1B
AUDIO_FEATURE_ONE_EARBUD_ANC = 0x05
AUDIO_FEATURE_HEAD_CONTROL = 0x0B
AUDIO_FEATURE_SPATIAL = 0x18

HEAD_NOD_ACTIONS: dict[int, str] = {
    0: "Nenhum",
    1: "Atender chamada",
}
HEAD_SHAKE_ACTIONS: dict[int, str] = {
    0: "Nenhum",
    2: "Rejeitar chamada",
}

PRESS_HOLD_ACTIONS: dict[int, str] = {
    0xFF: "Nenhum",
    0x0A: "Controle de ruído",
    0x00: "Despertar assistente de voz",
}
PINCH_HOLD_ACTIONS: dict[int, str] = {
    0xFF: "Nenhum",
    0x06: "Controle de ruído",
}
DOUBLE_TAP_ACTIONS: dict[int, str] = {
    0xFF: "Nenhum",
    0x01: "Reproduzir/pausar",
}
TRIPLE_TAP_ACTIONS: dict[int, str] = {
    0xFF: "Nenhum",
    0x07: "Faixa anterior",
    0x02: "Próxima faixa",
}
SWIPE_ACTIONS: dict[int, str] = {
    0x00: "Nenhum",
    0x02: "Ajustar volume",
}
SOUND_QUALITY_LABELS: dict[int, str] = {
    0: "Priorizar conexão",
    1: "Priorizar qualidade",
}

# Campos documentados publicamente. Campos não listados são preservados como
# field_N; não presumimos o significado de dados desconhecidos.
INFO_FIELD_NAMES: dict[int, str] = {
    3: "hardware_version",
    7: "software_version",
    9: "serial_number",
    10: "submodel",
    15: "model",
}

# Somente estes campos são tratados como texto. Qualquer outro campo é exibido
# como hex, pois bytes binários podem decodificar como GBK por coincidência.
INFO_TEXT_FIELDS: frozenset[int] = frozenset({3, 7, 9, 10, 15, 24})

INFO_REQUEST_FIELDS: tuple[int, ...] = tuple(range(32))

ANC_MODES: dict[int, str] = {
    0: "normal",
    1: "cancellation",
    2: "awareness",
}

ANC_CANCELLATION_LEVELS: dict[int, str] = {
    0: "normal",
    1: "comfort",
    2: "ultra",
    3: "dynamic",
}

ANC_AWARENESS_ADAPTIVE = 4
ANC_AWARENESS_LEVELS: dict[int, str] = {
    1: "voice_boost",
    2: "normal",
    ANC_AWARENESS_ADAPTIVE: "adaptive",
}

# O Reconhecimento adaptável usa o nível 4 no parâmetro 1 e a intensidade no
# parâmetro 4 da escrita. O fone reporta a intensidade de 0 a 10 no parâmetro 2
# da leitura; a interface mostra esses valores como 1 a 11.
ANC_ADAPTIVE_LEVEL_MIN = 0
ANC_ADAPTIVE_LEVEL_MAX = 10

DECODE_COMMANDS = (CMD_DEVICE_INFO, CMD_BATTERY, CMD_BATTERY_NOTIFY, CMD_ANC)


def info_request(fields: tuple[int, ...] | None = None) -> bytes:
    """Monta o handshake ``0x0107`` pedindo os campos de identificação.

    O pedido usa TLVs vazios, como no cliente OpenFreebuds. Sem campos
    explícitos, solicita os índices 0..31 para maximizar a resposta.
    """

    selected = INFO_REQUEST_FIELDS if fields is None else fields
    return encode_frame(CMD_DEVICE_INFO, {field: b"" for field in selected})


def battery_request() -> bytes:
    """Monta a leitura de bateria ``0x0108`` com parâmetros 1, 2 e 3."""

    return encode_frame(CMD_BATTERY, {1: b"", 2: b"", 3: b""})


def anc_request() -> bytes:
    """Monta a leitura de ANC ``0x2B2A`` com parâmetros 1 e 2."""

    return encode_frame(CMD_ANC, {1: b"", 2: b""})


def anc_set_mode_request(mode_code: int) -> bytes:
    """Monta ``0x2B04`` para trocar o modo global de ANC.

    O formato público é ``[modo, 0x00]`` para normal e ``[modo, 0xFF]`` para
    cancelamento/transparência. O fone responde com o eco de ``0x2B04`` e
    normalmente também envia uma notificação ``0x2B2A``.
    """

    if mode_code not in ANC_MODES:
        raise ValueError(f"modo de ANC inválido: {mode_code!r}")
    marker = b"\x00" if mode_code == 0 else b"\xFF"
    return encode_frame(CMD_ANC_WRITE, {1: bytes([mode_code]) + marker})


def anc_set_level_request(mode_code: int, level_code: int) -> bytes:
    """Monta ``0x2B04`` para trocar apenas o nível do modo ativo.

    O formato público é ``[modo_ativo, nível]``. No modo transparência, o
    nível ``4`` ativa o Reconhecimento adaptável; a intensidade dele é enviada
    por :func:`anc_set_adaptive_level_request`. Só aceitamos níveis cujo
    significado já foi mapeado.
    """

    if mode_code == 1:
        allowed = ANC_CANCELLATION_LEVELS
    elif mode_code == 2:
        allowed = ANC_AWARENESS_LEVELS
    else:
        raise ValueError("só é possível trocar o nível nos modos 1 e 2")
    if level_code not in allowed:
        raise ValueError(
            f"nível {level_code!r} inválido para o modo {mode_code!r}"
        )
    return encode_frame(
        CMD_ANC_WRITE,
        {1: bytes([mode_code, level_code])},
    )


def anc_set_adaptive_level_request(level_code: int) -> bytes:
    """Monta a escrita da intensidade do Reconhecimento adaptável.

    Validado no FreeBuds Pro 5: ``0x2B04`` com o parâmetro 1 ``[2, 4]`` ativa
    o modo, o parâmetro 3 vale ``1`` e o parâmetro 4 leva a intensidade de
    ``0`` a ``10``. A interface apresenta esses valores como ``1`` a ``11``.
    """

    if not ANC_ADAPTIVE_LEVEL_MIN <= level_code <= ANC_ADAPTIVE_LEVEL_MAX:
        raise ValueError(
            "intensidade adaptativa inválida: "
            f"{level_code!r}; use {ANC_ADAPTIVE_LEVEL_MIN}..{ANC_ADAPTIVE_LEVEL_MAX}"
        )
    return encode_frame(
        CMD_ANC_WRITE,
        {
            1: bytes([2, ANC_AWARENESS_ADAPTIVE]),
            3: b"\x01",
            4: bytes([level_code]),
        },
    )


def sound_profile_request() -> bytes:
    """Lê o perfil de equalização ativo e os dados do perfil personalizado."""

    return encode_frame(CMD_SOUND_PROFILE_STATE, {2: b""})


def sound_profile_set_request(
    profile_id: int,
    *,
    custom_eq: bytes | None = None,
    custom_name: str | bytes | None = None,
) -> bytes:
    """Monta a escrita de um perfil HUAWEI Sound validado.

    Os perfis comuns usam apenas o parâmetro 1 com o ID. O perfil Clássico foi
    observado com curva e nome próprios; o Personalizado reutiliza a curva e o
    nome atualmente gravados no fone, que devem vir de
    :func:`decode_sound_profile`.
    """

    if profile_id not in SOUND_PROFILES:
        raise ValueError(f"perfil de som inválido: {profile_id!r}")
    if profile_id == SOUND_PROFILE_CUSTOM:
        if not custom_eq or not custom_name:
            raise ValueError(
                "o perfil Personalizado exige a curva e o nome atuais do fone"
            )
        name = (
            custom_name.encode("utf-8")
            if isinstance(custom_name, str)
            else bytes(custom_name)
        )
        if len(name) > 31:
            raise ValueError("nome do perfil personalizado longo demais")
        return encode_frame(
            CMD_SOUND_PROFILE,
            {
                1: bytes([SOUND_PROFILE_CUSTOM]),
                2: b"\x0A",
                5: b"\x01",
                3: bytes(custom_eq),
                4: name,
            },
        )
    if profile_id == SOUND_PROFILE_CLASSIC:
        return encode_frame(
            CMD_SOUND_PROFILE,
            {
                1: bytes([SOUND_PROFILE_CLASSIC]),
                2: b"\x0A",
                5: b"\x01",
                3: SOUND_PROFILE_CLASSIC_EQ,
                4: SOUND_PROFILE_CLASSIC_NAME,
            },
        )
    return encode_frame(CMD_SOUND_PROFILE, {1: bytes([profile_id])})


def spatial_request() -> bytes:
    return encode_frame(
        CMD_AUDIO_FEATURE,
        {1: bytes([AUDIO_FEATURE_SPATIAL]), 2: b"", 3: b""},
    )


def spatial_set_mode_request(mode_code: int) -> bytes:
    if mode_code not in SPATIAL_MODES:
        raise ValueError(f"modo espacial inválido: {mode_code!r}")
    return encode_frame(
        CMD_AUDIO_FEATURE,
        {1: bytes([AUDIO_FEATURE_SPATIAL]), 2: bytes([mode_code])},
    )


def audio_feature_request(feature: int) -> bytes:
    if feature not in (
        AUDIO_FEATURE_ADAPTIVE_VOLUME,
        AUDIO_FEATURE_CONVERSATION,
        AUDIO_FEATURE_ONE_EARBUD_ANC,
        AUDIO_FEATURE_HEAD_CONTROL,
    ):
        raise ValueError(f"recurso de áudio inválido: {feature!r}")
    if feature == AUDIO_FEATURE_HEAD_CONTROL:
        return encode_frame(CMD_AUDIO_FEATURE, {1: bytes([feature])})
    return encode_frame(CMD_AUDIO_FEATURE, {1: bytes([feature]), 2: b""})


def audio_feature_set_request(feature: int, value: int) -> bytes:
    if feature not in (
        AUDIO_FEATURE_ADAPTIVE_VOLUME,
        AUDIO_FEATURE_CONVERSATION,
        AUDIO_FEATURE_ONE_EARBUD_ANC,
        AUDIO_FEATURE_HEAD_CONTROL,
    ):
        raise ValueError(f"recurso de áudio inválido: {feature!r}")
    if not 0 <= value <= 0xFF:
        raise ValueError("valor de recurso fora de 0..255")
    return encode_frame(
        CMD_AUDIO_FEATURE,
        {1: bytes([feature]), 2: bytes([value])},
    )


def head_control_set_request(
    *,
    enabled: bool | None = None,
    nod_action: int | None = None,
    shake_action: int | None = None,
) -> bytes:
    if enabled is None and nod_action is None and shake_action is None:
        raise ValueError("nenhuma alteração de controle de cabeça informada")
    params: dict[int, bytes] = {1: bytes([AUDIO_FEATURE_HEAD_CONTROL])}
    if enabled is not None:
        params[2] = b"\x01" if enabled else b"\x00"
    if nod_action is not None:
        if nod_action not in HEAD_NOD_ACTIONS:
            raise ValueError(f"ação de aceno inválida: {nod_action!r}")
        params[3] = bytes([nod_action])
    if shake_action is not None:
        if shake_action not in HEAD_SHAKE_ACTIONS:
            raise ValueError(
                f"ação de balançar a cabeça inválida: {shake_action!r}"
            )
        params[4] = bytes([shake_action])
    return encode_frame(CMD_AUDIO_FEATURE, params)


def wear_detection_request() -> bytes:
    return encode_frame(CMD_WEAR_STATE, {1: b""})


def wear_detection_set_request(enabled: bool) -> bytes:
    return encode_frame(CMD_WEAR_WRITE, {1: b"\x01" if enabled else b"\x00"})


def multipoint_request() -> bytes:
    return encode_frame(CMD_MULTIPOINT_STATE, {1: b""})


def sound_quality_request() -> bytes:
    return encode_frame(CMD_SOUND_QUALITY_STATE, {})


def sound_quality_set_request(value: int) -> bytes:
    if value not in SOUND_QUALITY_LABELS:
        raise ValueError(f"qualidade de som inválida: {value!r}")
    return encode_frame(CMD_SOUND_QUALITY_WRITE, {1: bytes([value])})


def low_latency_request() -> bytes:
    return encode_frame(CMD_LOW_LATENCY, {2: b""})


def low_latency_set_request(enabled: bool) -> bytes:
    return encode_frame(CMD_LOW_LATENCY, {1: b"\x01" if enabled else b"\x00"})


def press_hold_request() -> bytes:
    return encode_frame(CMD_PRESS_HOLD_STATE, {1: b"", 2: b""})


def press_hold_set_request(side: str, action: int) -> bytes:
    if side not in ("left", "right"):
        raise ValueError("lado deve ser 'left' ou 'right'")
    if action not in PRESS_HOLD_ACTIONS:
        raise ValueError(f"ação de pressionar e segurar inválida: {action!r}")
    return encode_frame(
        CMD_PRESS_HOLD_WRITE,
        {1 if side == "left" else 2: bytes([action])},
    )


def pinch_hold_request() -> bytes:
    return encode_frame(CMD_PINCH_HOLD_STATE, {1: b"\x03", 2: b"\x00"})


def pinch_hold_set_request(side: str, action: int) -> bytes:
    if side not in ("left", "right"):
        raise ValueError("lado deve ser 'left' ou 'right'")
    if action not in PINCH_HOLD_ACTIONS:
        raise ValueError(f"ação de pinçar e segurar inválida: {action!r}")
    return encode_frame(
        CMD_PINCH_HOLD_WRITE,
        {
            1: b"\x03",
            2: b"\x00",
            3 if side == "left" else 4: bytes([action]),
        },
    )


def double_tap_request() -> bytes:
    return encode_frame(CMD_DOUBLE_TAP_STATE, {1: b"", 2: b""})


def double_tap_set_request(left: int, right: int) -> bytes:
    if left not in DOUBLE_TAP_ACTIONS or right not in DOUBLE_TAP_ACTIONS:
        raise ValueError("ação de toque duplo inválida")
    return encode_frame(
        CMD_DOUBLE_TAP_WRITE,
        {1: bytes([left]), 2: bytes([right])},
    )


def triple_tap_request() -> bytes:
    return encode_frame(CMD_TRIPLE_TAP_STATE, {1: b"", 2: b""})


def triple_tap_set_request(side: str, action: int) -> bytes:
    if side not in ("left", "right"):
        raise ValueError("lado deve ser 'left' ou 'right'")
    if action not in TRIPLE_TAP_ACTIONS:
        raise ValueError(f"ação de toque triplo inválida: {action!r}")
    return encode_frame(
        CMD_TRIPLE_TAP_WRITE,
        {1 if side == "left" else 2: bytes([action])},
    )


def swipe_request() -> bytes:
    return encode_frame(CMD_SWIPE_STATE, {1: b"", 2: b""})


def _first_byte(parameters: Mapping[int, bytes], key: int) -> int | None:
    value = parameters.get(key)
    if value is None or not value:
        return None
    return bytes(value)[0]


def _bool_value(parameters: Mapping[int, bytes], key: int) -> bool | None:
    value = _first_byte(parameters, key)
    return None if value is None else value != 0


def _utf8_value(parameters: Mapping[int, bytes], key: int) -> str | None:
    raw = parameters.get(key)
    if raw is None:
        return None
    text = bytes(raw).rstrip(b"\x00").decode("utf-8", "replace")
    return text or None


def decode_sound_profile(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.sound_profile_id = _first_byte(parameters, 2)
    state.custom_eq = (
        bytes(parameters[6]) if parameters.get(6) else None
    )
    state.custom_name = _utf8_value(parameters, 7)
    return state


def decode_spatial(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.spatial_mode = _first_byte(parameters, 2)
    state.spatial_effect = _first_byte(parameters, 3)
    return state


def decode_audio_feature(
    parameters: Mapping[int, bytes], feature: int
) -> AdvancedSettings:
    state = AdvancedSettings()
    value = _bool_value(parameters, 2)
    if feature == AUDIO_FEATURE_ADAPTIVE_VOLUME:
        state.adaptive_volume = value
    elif feature == AUDIO_FEATURE_CONVERSATION:
        state.conversation_awareness = value
    elif feature == AUDIO_FEATURE_ONE_EARBUD_ANC:
        state.one_earbud_anc = value
    return state


def decode_head_control(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.head_control = _bool_value(parameters, 2)
    state.head_nod_action = _first_byte(parameters, 3)
    state.head_shake_action = _first_byte(parameters, 4)
    return state


def decode_wear_detection(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.wear_detection = _bool_value(parameters, 1)
    return state


def decode_multipoint(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.multipoint = _bool_value(parameters, 1)
    return state


def decode_sound_quality(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.sound_quality = _first_byte(parameters, 2)
    return state


def decode_low_latency(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.low_latency = _bool_value(parameters, 2)
    return state


def decode_press_hold(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.press_hold_left = _first_byte(parameters, 1)
    state.press_hold_right = _first_byte(parameters, 2)
    return state


def decode_pinch_hold(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.pinch_hold_left = _first_byte(parameters, 3)
    state.pinch_hold_right = _first_byte(parameters, 4)
    return state


def decode_double_tap(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.double_tap_left = _first_byte(parameters, 1)
    state.double_tap_right = _first_byte(parameters, 2)
    return state


def decode_triple_tap(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.triple_tap_left = _first_byte(parameters, 1)
    state.triple_tap_right = _first_byte(parameters, 2)
    return state


def decode_swipe(parameters: Mapping[int, bytes]) -> AdvancedSettings:
    state = AdvancedSettings()
    state.swipe_up = _first_byte(parameters, 1)
    state.swipe_down = _first_byte(parameters, 2)
    return state


def command_name(command: bytes) -> str:
    return COMMAND_NAMES.get(command, "DESCONHECIDO")


def _text_value(raw: bytes) -> str:
    stripped = raw.rstrip(b"\x00")
    for encoding in ("utf-8", "gbk"):
        try:
            text = stripped.decode(encoding)
        except UnicodeDecodeError:
            continue
        if text and all(character.isprintable() or character == "\t" for character in text):
            return text
    return raw.hex(" ") if raw else ""


def decode_device_info(parameters: Mapping[int, bytes]) -> DeviceInfo:
    """Interpreta a resposta de ``0x0107`` mantendo todos os campos brutos."""

    info = DeviceInfo()
    raw_fields = {key: bytes(value) for key, value in parameters.items()}
    fields = {
        key: _text_value(value)
        if key in INFO_TEXT_FIELDS
        else (value.hex(" ") if value else "")
        for key, value in raw_fields.items()
    }

    info.hardware_version = fields.get(3)
    info.software_version = fields.get(7)
    info.serial_number = fields.get(9)
    info.submodel = fields.get(10)
    info.model = fields.get(15)
    info.fields = fields
    info.raw_fields = raw_fields

    serial = raw_fields.get(24)
    if serial:
        try:
            text = serial.decode("ascii").strip("\x00")
        except UnicodeDecodeError:
            text = ""
        if "," in text:
            left, right = text.split(",", 1)
            if left[:1].upper() == "L" and left[1:2] == "-":
                info.left_serial_number = left[2:]
            if right[:1].upper() == "R" and right[1:2] == "-":
                info.right_serial_number = right[2:]

    return info


def decode_battery(parameters: Mapping[int, bytes]) -> BatteryState:
    """Interpreta ``0x0108`` ou notificações ``0x0127``.

    O layout conhecido é: parâmetro 1 = nível global (1 byte), parâmetro 2 =
    esquerda/direita/estojo (3 bytes), parâmetro 3 = flags de carga. Variações
    de firmware deixam campos como ``None`` em vez de inventar valores.
    """

    raw = {key: bytes(value) for key, value in parameters.items()}
    state = BatteryState(parameters=raw)

    global_value = raw.get(1)
    if global_value is not None and len(global_value) == 1:
        state.global_level = global_value[0]

    tws = raw.get(2)
    if tws is not None and len(tws) == 3:
        state.left, state.right, state.case = tws[0], tws[1], tws[2]

    flags = raw.get(3)
    if flags:
        state.charging_flags = flags
        state.charging = 1 in flags

    return state


def decode_anc(parameters: Mapping[int, bytes]) -> AncState:
    """Interpreta ``0x2B2A`` (modo no byte 1; nível no byte 0 do parâmetro 1).

    No Reconhecimento adaptável (modo transparência, nível ``4``), o parâmetro
    ``2`` traz a intensidade de ``0`` a ``10``. Valores fora dessa faixa são
    preservados apenas no bruto, sem inventar semântica.
    """

    raw = {key: bytes(value) for key, value in parameters.items()}
    state = AncState(parameters=raw)

    mode_data = raw.get(1)
    if mode_data is not None and len(mode_data) >= 2:
        level_code = mode_data[0]
        mode_code = mode_data[1]
        state.level_code = level_code
        state.mode_code = mode_code
        state.mode = ANC_MODES.get(mode_code)
        if mode_code == 1:
            state.level = ANC_CANCELLATION_LEVELS.get(level_code)
        elif mode_code == 2:
            state.level = ANC_AWARENESS_LEVELS.get(level_code)
            if level_code == ANC_AWARENESS_ADAPTIVE:
                slider = raw.get(2)
                if slider is not None and len(slider) == 1:
                    if ANC_ADAPTIVE_LEVEL_MIN <= slider[0] <= ANC_ADAPTIVE_LEVEL_MAX:
                        state.adaptive_level = slider[0]

    return state


def decode_parameter_text(parameters: Mapping[int, bytes]) -> dict[int, str]:
    """Representação textual de TLVs para a saída ``decode`` da CLI."""

    return {
        key: bytes(value).decode("utf-8", "backslashreplace")
        if bytes(value) and all(32 <= byte < 127 for byte in value)
        else bytes(value).hex(" ")
        for key, value in sorted(parameters.items())
    }


def decode_known_frame(frame: HuaweiFrame) -> dict[str, Any] | None:
    """Decodifica semanticamente um quadro conhecido, se possível."""

    if frame.command == CMD_DEVICE_INFO:
        return decode_device_info(frame.parameters).to_dict()
    if frame.command in (CMD_BATTERY, CMD_BATTERY_NOTIFY):
        return decode_battery(frame.parameters).to_dict()
    if frame.command == CMD_ANC:
        return decode_anc(frame.parameters).to_dict()
    return None
