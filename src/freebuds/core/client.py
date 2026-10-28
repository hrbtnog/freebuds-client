"""Cliente de alto nível usado pela UI.

Esta camada reúne conexão, handshake e leitura de snapshot sem depender de Qt.
A CLI mantém seu próprio fluxo de diagnóstico; a UI consome este cliente para
evitar duplicar a lógica de canais e comandos.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from datetime import datetime

from . import commands as advanced_commands
from .commands import (
    CMD_ANC,
    CMD_ANC_WRITE,
    CMD_AUDIO_FEATURE,
    CMD_BATTERY,
    CMD_BATTERY_NOTIFY,
    CMD_DEVICE_INFO,
    CMD_DOUBLE_TAP_STATE,
    CMD_LOW_LATENCY,
    CMD_MULTIPOINT_STATE,
    CMD_PINCH_HOLD_STATE,
    CMD_PRESS_HOLD_STATE,
    CMD_SOUND_PROFILE,
    CMD_SOUND_PROFILE_STATE,
    CMD_SOUND_QUALITY_STATE,
    CMD_SOUND_QUALITY_WRITE,
    CMD_SWIPE_STATE,
    CMD_TRIPLE_TAP_STATE,
    CMD_WEAR_STATE,
    CMD_WEAR_WRITE,
    anc_request,
    anc_set_adaptive_level_request,
    anc_set_level_request,
    anc_set_mode_request,
    battery_request,
    decode_anc,
    decode_battery,
    decode_device_info,
    info_request,
)
from .errors import FreeBudsError, RequestTimeout, SessionError
from .models import AdvancedSettings, AncState, BatteryState, DeviceInfo
from .protocol import FrameIssue, HuaweiFrame
from .session import HuaweiSession
from .transport import KNOWN_CHANNELS, RfcommTransport
from .util import normalize_address


@dataclass(slots=True)
class ChannelAttempt:
    """Resultado de uma tentativa de conexão em um canal RFCOMM."""

    channel: int
    ok: bool
    error: str | None = None


@dataclass(slots=True)
class ConnectionInfo:
    """Resultado de uma conexão bem-sucedida."""

    address: str
    channel: int
    info: DeviceInfo
    attempts: list[ChannelAttempt] = field(default_factory=list)


@dataclass(slots=True)
class DeviceSnapshot:
    """Leitura pontual de bateria, ANC e notificações."""

    info: DeviceInfo
    battery: BatteryState | None
    anc: AncState | None
    notifications: list[HuaweiFrame]
    warnings: list[str]
    parser_issues: list[FrameIssue]
    timestamp: datetime
    channel: int
    advanced: AdvancedSettings | None = None


def resolve_channels(
    *,
    requested: Sequence[int] | None = None,
    saved_channel: int | None = None,
    settings_channels: Sequence[int] | None = None,
) -> list[int]:
    """Monta a ordem de canais sem duplicatas e sem valores inválidos.

    Um canal salvo tem prioridade, depois vêm os canais das preferências e, por
    fim, os canais conhecidos por modelo.
    """

    candidates: list[int] = []
    if requested:
        candidates.extend(requested)
    else:
        if saved_channel is not None:
            candidates.append(saved_channel)
        if settings_channels:
            candidates.extend(settings_channels)
        candidates.extend(KNOWN_CHANNELS)

    unique: list[int] = []
    for channel in candidates:
        if (
            isinstance(channel, int)
            and not isinstance(channel, bool)
            and 1 <= channel <= 30
            and channel not in unique
        ):
            unique.append(channel)
    if not unique:
        raise FreeBudsError("nenhum canal RFCOMM válido configurado")
    return unique


class FreeBudsClient:
    """Sessão SPP de alto nível com conexão preguiçosa e leitura de snapshot."""

    def __init__(
        self,
        address: str,
        *,
        channels: Sequence[int] | None = None,
        connect_timeout: float = 5.0,
        response_timeout: float = 2.0,
    ) -> None:
        self.address = normalize_address(address)
        self.channels = resolve_channels(requested=channels)
        if connect_timeout <= 0:
            raise ValueError("connect_timeout deve ser positivo")
        if response_timeout <= 0:
            raise ValueError("response_timeout deve ser positivo")
        self.connect_timeout = connect_timeout
        self.response_timeout = response_timeout
        self.channel: int | None = None
        self.info: DeviceInfo | None = None
        self._session: HuaweiSession | None = None
        self._transport: RfcommTransport | None = None

    @property
    def connected(self) -> bool:
        return self._session is not None and self._session.is_open

    def connect(self, *, should_stop: Callable[[], bool] | None = None) -> ConnectionInfo:
        """Tenta os canais na ordem configurada e mantém a primeira sessão válida."""

        self.close()
        attempts: list[ChannelAttempt] = []
        for channel in self.channels:
            if should_stop is not None and should_stop():
                raise FreeBudsError("conexão cancelada pelo usuário")
            transport = RfcommTransport(
                self.address, channel, connect_timeout=self.connect_timeout
            )
            session = HuaweiSession(transport, response_timeout=self.response_timeout)
            try:
                session.open()
                response = session.request_bytes(
                    info_request(),
                    expected=(CMD_DEVICE_INFO,),
                    timeout=self.response_timeout,
                )
                info = decode_device_info(response.parameters)
            except (FreeBudsError, OSError) as exc:
                attempts.append(ChannelAttempt(channel, False, str(exc)))
                session.close()
                if should_stop is not None and should_stop():
                    raise FreeBudsError("conexão cancelada pelo usuário") from exc
                continue

            self._transport = transport
            self._session = session
            self.info = info
            self.channel = channel
            attempts.append(ChannelAttempt(channel, True))
            return ConnectionInfo(
                address=self.address,
                channel=channel,
                info=info,
                attempts=attempts,
            )

        details = "; ".join(
            f"canal {attempt.channel}: {attempt.error}" for attempt in attempts
        )
        raise FreeBudsError(
            "não foi possível falar SPP com os fones em nenhum canal tentado. "
            "Confirme que estão ligados, fora do estojo, pareados e que o app "
            f"oficial não está usando a conexão. [{details}]"
        )

    def wait_for_notifications(
        self,
        timeout: float,
        *,
        should_stop: Callable[[], bool] | None = None,
    ) -> bool:
        """Acorda quando houver um push espontâneo ou quando o tempo acabar."""

        session = self._session
        if session is None or not session.is_open:
            return False
        return session.wait_for_notifications(
            timeout,
            should_stop=should_stop,
        )

    def read_anc(self) -> AncState:
        """Lê o estado atual de ANC sob demanda, sem montar um snapshot inteiro."""

        session = self._session
        if session is None or not session.is_open:
            raise SessionError("a sessão SPP não está aberta")
        response = session.request_bytes(
            anc_request(),
            expected=(CMD_ANC,),
            timeout=self.response_timeout,
        )
        return decode_anc(response.parameters)

    def set_anc(
        self,
        *,
        mode_code: int,
        level_code: int | None = None,
    ) -> AncState:
        """Troca o modo (ou o nível) de ANC e devolve o estado lido do fone.

        Esta é uma das escritas habilitadas no cliente. O comando é síncrono e
        exige a confirmação do próprio fone; timeout ou falta de confirmação vira
        :class:`FreeBudsError` para a UI informar a falha.
        """

        session = self._session
        if session is None or not session.is_open:
            raise SessionError("a sessão SPP não está aberta")

        if level_code is None:
            payload = anc_set_mode_request(mode_code)
        else:
            payload = anc_set_level_request(mode_code, level_code)

        response = session.request_bytes(
            payload,
            expected=(CMD_ANC_WRITE, CMD_ANC),
            timeout=self.response_timeout,
        )
        candidate = (
            decode_anc(response.parameters)
            if response.command == CMD_ANC
            else None
        )
        return self._confirm_anc_state(
            mode_code=mode_code,
            level_code=level_code,
            initial=candidate,
        )

    def set_anc_adaptive_level(self, level_code: int) -> AncState:
        """Ajusta a intensidade do Reconhecimento adaptável (0..10).

        A escrita usa os parâmetros 1, 3 e 4 de ``0x2B04``, validados no
        FreeBuds Pro 5. Depois do ack, o estado é relido até o fone reportar a
        intensidade aplicada, evitando devolver o valor anterior por um ciclo.
        """

        session = self._session
        if session is None or not session.is_open:
            raise SessionError("a sessão SPP não está aberta")
        session.request_bytes(
            anc_set_adaptive_level_request(level_code),
            expected=(CMD_ANC_WRITE,),
            timeout=self.response_timeout,
        )
        return self._confirm_anc_state(
            mode_code=2,
            level_code=4,
            adaptive_level=level_code,
        )

    def _confirm_anc_state(
        self,
        *,
        mode_code: int,
        level_code: int | None,
        adaptive_level: int | None = None,
        initial: AncState | None = None,
    ) -> AncState:
        """Relê o ANC até o fone reportar o estado solicitado.

        O firmware confirma ``0x2B04`` antes de publicar a notificação
        ``0x2B2A``. Uma leitura imediatamente após o ack pode, portanto, trazer
        o estado antigo; a confirmação evita que a UI mostre um valor atrasado.
        """

        deadline = time.monotonic() + max(1.0, min(self.response_timeout, 2.5))
        state = initial
        while True:
            if state is None:
                state = self.read_anc()
            if self._anc_matches(
                state,
                mode_code=mode_code,
                level_code=level_code,
                adaptive_level=adaptive_level,
            ):
                return state
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise FreeBudsError(
                    "o fone não confirmou a alteração de ANC "
                    f"(modo={mode_code}, nível={level_code}, "
                    f"adaptativo={adaptive_level})"
                )
            time.sleep(min(0.1, remaining))
            state = None

    @staticmethod
    def _anc_matches(
        state: AncState,
        *,
        mode_code: int,
        level_code: int | None,
        adaptive_level: int | None,
    ) -> bool:
        if state.mode_code != mode_code:
            return False
        if level_code is not None and state.level_code != level_code:
            return False
        if (
            adaptive_level is not None
            and state.adaptive_level != adaptive_level
        ):
            return False
        return True

    def read_advanced(self) -> AdvancedSettings:
        """Lê os recursos adicionais confirmados, tolerando comandos ausentes.

        A leitura é usada ao conectar, após uma escrita e no polling da UI. Um
        recurso que não responda não invalida os demais; o campo fica ``None``
        e os parâmetros brutos continuam disponíveis em ``raw``.
        """

        session = self._open_session()
        state = AdvancedSettings()

        def fetch(
            payload: bytes,
            command: bytes,
            decoder: Callable[[Mapping[int, bytes]], AdvancedSettings],
            raw_key: str | None = None,
        ) -> None:
            try:
                response = session.request_bytes(
                    payload,
                    expected=(command,),
                    timeout=self.response_timeout,
                )
            except (RequestTimeout, SessionError):
                return
            key = raw_key or command.hex().upper()
            state.raw[key] = response.parameters
            self._merge_advanced(state, decoder(response.parameters))

        fetch(
            advanced_commands.sound_profile_request(),
            CMD_SOUND_PROFILE_STATE,
            advanced_commands.decode_sound_profile,
        )
        fetch(
            advanced_commands.spatial_request(),
            CMD_AUDIO_FEATURE,
            advanced_commands.decode_spatial,
            "2BB4:18",
        )
        for feature in (
            advanced_commands.AUDIO_FEATURE_ADAPTIVE_VOLUME,
            advanced_commands.AUDIO_FEATURE_CONVERSATION,
            advanced_commands.AUDIO_FEATURE_ONE_EARBUD_ANC,
        ):
            fetch(
                advanced_commands.audio_feature_request(feature),
                CMD_AUDIO_FEATURE,
                lambda parameters, feature=feature: (
                    advanced_commands.decode_audio_feature(parameters, feature)
                ),
                f"2BB4:{feature:02X}",
            )
        fetch(
            advanced_commands.audio_feature_request(
                advanced_commands.AUDIO_FEATURE_HEAD_CONTROL
            ),
            CMD_AUDIO_FEATURE,
            advanced_commands.decode_head_control,
            "2BB4:0B",
        )
        fetch(
            advanced_commands.wear_detection_request(),
            CMD_WEAR_STATE,
            advanced_commands.decode_wear_detection,
        )
        fetch(
            advanced_commands.multipoint_request(),
            CMD_MULTIPOINT_STATE,
            advanced_commands.decode_multipoint,
        )
        fetch(
            advanced_commands.sound_quality_request(),
            CMD_SOUND_QUALITY_STATE,
            advanced_commands.decode_sound_quality,
        )
        fetch(
            advanced_commands.low_latency_request(),
            CMD_LOW_LATENCY,
            advanced_commands.decode_low_latency,
        )
        fetch(
            advanced_commands.press_hold_request(),
            CMD_PRESS_HOLD_STATE,
            advanced_commands.decode_press_hold,
        )
        fetch(
            advanced_commands.pinch_hold_request(),
            CMD_PINCH_HOLD_STATE,
            advanced_commands.decode_pinch_hold,
        )
        fetch(
            advanced_commands.double_tap_request(),
            CMD_DOUBLE_TAP_STATE,
            advanced_commands.decode_double_tap,
        )
        fetch(
            advanced_commands.triple_tap_request(),
            CMD_TRIPLE_TAP_STATE,
            advanced_commands.decode_triple_tap,
        )
        fetch(
            advanced_commands.swipe_request(),
            CMD_SWIPE_STATE,
            advanced_commands.decode_swipe,
        )
        return state

    def set_sound_profile(self, profile_id: int) -> AdvancedSettings:
        custom_eq = None
        custom_name = None
        if profile_id == advanced_commands.SOUND_PROFILE_CUSTOM:
            current = self._read_target(
                advanced_commands.sound_profile_request(),
                CMD_SOUND_PROFILE_STATE,
                advanced_commands.decode_sound_profile,
            )
            custom_eq = current.custom_eq
            custom_name = current.custom_name
        payload = advanced_commands.sound_profile_set_request(
            profile_id,
            custom_eq=custom_eq,
            custom_name=custom_name,
        )
        self._write_request(payload, CMD_SOUND_PROFILE)
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.sound_profile_request(),
                CMD_SOUND_PROFILE_STATE,
                advanced_commands.decode_sound_profile,
            ),
            lambda state: state.sound_profile_id == profile_id,
            f"perfil de som {profile_id}",
        )

    def set_spatial_mode(self, mode_code: int) -> AdvancedSettings:
        self._write_request(
            advanced_commands.spatial_set_mode_request(mode_code),
            CMD_AUDIO_FEATURE,
        )
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.spatial_request(),
                CMD_AUDIO_FEATURE,
                advanced_commands.decode_spatial,
            ),
            lambda state: state.spatial_mode == mode_code,
            f"modo espacial {mode_code}",
        )

    def set_adaptive_volume(self, enabled: bool) -> AdvancedSettings:
        return self._set_boolean_feature(
            advanced_commands.AUDIO_FEATURE_ADAPTIVE_VOLUME,
            enabled,
            "adaptive_volume",
            "volume adaptável",
        )

    def set_conversation_awareness(self, enabled: bool) -> AdvancedSettings:
        return self._set_boolean_feature(
            advanced_commands.AUDIO_FEATURE_CONVERSATION,
            enabled,
            "conversation_awareness",
            "reconhecimento de conversa",
        )

    def set_one_earbud_anc(self, enabled: bool) -> AdvancedSettings:
        return self._set_boolean_feature(
            advanced_commands.AUDIO_FEATURE_ONE_EARBUD_ANC,
            enabled,
            "one_earbud_anc",
            "cancelamento com um fone",
        )

    def set_head_control(
        self,
        *,
        enabled: bool | None = None,
        nod_action: int | None = None,
        shake_action: int | None = None,
    ) -> AdvancedSettings:
        payload = advanced_commands.head_control_set_request(
            enabled=enabled,
            nod_action=nod_action,
            shake_action=shake_action,
        )
        self._write_request(payload, CMD_AUDIO_FEATURE)

        def matches(state: AdvancedSettings) -> bool:
            if enabled is not None and state.head_control != enabled:
                return False
            if nod_action is not None and state.head_nod_action != nod_action:
                return False
            if shake_action is not None and state.head_shake_action != shake_action:
                return False
            return True

        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.audio_feature_request(
                    advanced_commands.AUDIO_FEATURE_HEAD_CONTROL
                ),
                CMD_AUDIO_FEATURE,
                advanced_commands.decode_head_control,
            ),
            matches,
            "controle de cabeça",
        )

    def set_wear_detection(self, enabled: bool) -> AdvancedSettings:
        self._write_request(
            advanced_commands.wear_detection_set_request(enabled),
            CMD_WEAR_WRITE,
        )
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.wear_detection_request(),
                CMD_WEAR_STATE,
                advanced_commands.decode_wear_detection,
            ),
            lambda state: state.wear_detection == enabled,
            "detecção de uso",
        )

    def set_sound_quality(self, value: int) -> AdvancedSettings:
        self._write_request(
            advanced_commands.sound_quality_set_request(value),
            CMD_SOUND_QUALITY_WRITE,
        )
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.sound_quality_request(),
                CMD_SOUND_QUALITY_STATE,
                advanced_commands.decode_sound_quality,
            ),
            lambda state: state.sound_quality == value,
            f"qualidade do som {value}",
        )

    def set_low_latency(self, enabled: bool) -> AdvancedSettings:
        self._write_request(
            advanced_commands.low_latency_set_request(enabled),
            CMD_LOW_LATENCY,
        )
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.low_latency_request(),
                CMD_LOW_LATENCY,
                advanced_commands.decode_low_latency,
            ),
            lambda state: state.low_latency == enabled,
            "latência baixa",
        )

    def set_press_hold(self, side: str, action: int) -> AdvancedSettings:
        self._write_request(
            advanced_commands.press_hold_set_request(side, action),
            advanced_commands.CMD_PRESS_HOLD_WRITE,
        )
        field_name = "press_hold_left" if side == "left" else "press_hold_right"
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.press_hold_request(),
                CMD_PRESS_HOLD_STATE,
                advanced_commands.decode_press_hold,
            ),
            lambda state: getattr(state, field_name) == action,
            f"gesto de pressionar e segurar ({side})",
        )

    def set_pinch_hold(self, side: str, action: int) -> AdvancedSettings:
        self._write_request(
            advanced_commands.pinch_hold_set_request(side, action),
            advanced_commands.CMD_PINCH_HOLD_WRITE,
        )
        field_name = "pinch_hold_left" if side == "left" else "pinch_hold_right"
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.pinch_hold_request(),
                CMD_PINCH_HOLD_STATE,
                advanced_commands.decode_pinch_hold,
            ),
            lambda state: getattr(state, field_name) == action,
            f"gesto de pinçar e segurar ({side})",
        )

    def set_double_tap(self, left: int, right: int) -> AdvancedSettings:
        self._write_request(
            advanced_commands.double_tap_set_request(left, right),
            advanced_commands.CMD_DOUBLE_TAP_WRITE,
        )
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.double_tap_request(),
                CMD_DOUBLE_TAP_STATE,
                advanced_commands.decode_double_tap,
            ),
            lambda state: (
                state.double_tap_left == left
                and state.double_tap_right == right
            ),
            "toque duplo",
        )

    def set_triple_tap(self, side: str, action: int) -> AdvancedSettings:
        self._write_request(
            advanced_commands.triple_tap_set_request(side, action),
            advanced_commands.CMD_TRIPLE_TAP_WRITE,
        )
        field_name = "triple_tap_left" if side == "left" else "triple_tap_right"
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.triple_tap_request(),
                CMD_TRIPLE_TAP_STATE,
                advanced_commands.decode_triple_tap,
            ),
            lambda state: getattr(state, field_name) == action,
            f"toque triplo ({side})",
        )

    def _set_boolean_feature(
        self,
        feature: int,
        enabled: bool,
        attribute: str,
        description: str,
    ) -> AdvancedSettings:
        self._write_request(
            advanced_commands.audio_feature_set_request(
                feature, 1 if enabled else 0
            ),
            CMD_AUDIO_FEATURE,
        )
        return self._confirm_advanced(
            lambda: self._read_target(
                advanced_commands.audio_feature_request(feature),
                CMD_AUDIO_FEATURE,
                lambda parameters: advanced_commands.decode_audio_feature(
                    parameters, feature
                ),
            ),
            lambda state: getattr(state, attribute) == enabled,
            description,
        )

    def _read_target(
        self,
        payload: bytes,
        command: bytes,
        decoder: Callable[[Mapping[int, bytes]], AdvancedSettings],
    ) -> AdvancedSettings:
        session = self._open_session()
        response = session.request_bytes(
            payload,
            expected=(command,),
            timeout=self.response_timeout,
        )
        state = decoder(response.parameters)
        state.raw[command.hex().upper()] = response.parameters
        return state

    def _write_request(self, payload: bytes, command: bytes) -> HuaweiFrame:
        session = self._open_session()
        return session.request_bytes(
            payload,
            expected=(command,),
            timeout=self.response_timeout,
        )

    def _confirm_advanced(
        self,
        read: Callable[[], AdvancedSettings],
        predicate: Callable[[AdvancedSettings], bool],
        description: str,
    ) -> AdvancedSettings:
        deadline = time.monotonic() + max(1.0, min(self.response_timeout, 2.5))
        last: AdvancedSettings | None = None
        while True:
            last = read()
            if predicate(last):
                return last
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise FreeBudsError(
                    f"o fone não confirmou {description} após a escrita"
                )
            time.sleep(min(0.1, remaining))

    def _open_session(self) -> HuaweiSession:
        session = self._session
        if session is None or not session.is_open:
            raise SessionError("a sessão SPP não está aberta")
        return session

    @staticmethod
    def _merge_advanced(
        target: AdvancedSettings, update: AdvancedSettings
    ) -> None:
        for descriptor in fields(update):
            if descriptor.name == "raw":
                continue
            value = getattr(update, descriptor.name)
            if value is not None:
                setattr(target, descriptor.name, value)

    @staticmethod
    def _apply_advanced_notification(
        target: AdvancedSettings, frame: HuaweiFrame
    ) -> None:
        parameters = frame.parameters
        update: AdvancedSettings | None = None
        raw_key = frame.command.hex().upper()
        if frame.command == CMD_SOUND_PROFILE_STATE:
            update = advanced_commands.decode_sound_profile(parameters)
        elif frame.command == CMD_AUDIO_FEATURE:
            feature = advanced_commands._first_byte(parameters, 1)
            if feature == advanced_commands.AUDIO_FEATURE_SPATIAL:
                update = advanced_commands.decode_spatial(parameters)
            elif feature in (
                advanced_commands.AUDIO_FEATURE_ADAPTIVE_VOLUME,
                advanced_commands.AUDIO_FEATURE_CONVERSATION,
                advanced_commands.AUDIO_FEATURE_ONE_EARBUD_ANC,
            ):
                update = advanced_commands.decode_audio_feature(
                    parameters, feature
                )
            elif feature == advanced_commands.AUDIO_FEATURE_HEAD_CONTROL:
                update = advanced_commands.decode_head_control(parameters)
            if feature is not None:
                raw_key = f"2BB4:{feature:02X}"
        elif frame.command == CMD_WEAR_STATE:
            update = advanced_commands.decode_wear_detection(parameters)
        elif frame.command == CMD_MULTIPOINT_STATE:
            update = advanced_commands.decode_multipoint(parameters)
        elif frame.command == CMD_SOUND_QUALITY_STATE:
            update = advanced_commands.decode_sound_quality(parameters)
        elif frame.command == CMD_LOW_LATENCY:
            update = advanced_commands.decode_low_latency(parameters)
        elif frame.command == CMD_PRESS_HOLD_STATE:
            update = advanced_commands.decode_press_hold(parameters)
        elif frame.command == CMD_PINCH_HOLD_STATE:
            update = advanced_commands.decode_pinch_hold(parameters)
        elif frame.command == CMD_DOUBLE_TAP_STATE:
            update = advanced_commands.decode_double_tap(parameters)
        elif frame.command == CMD_TRIPLE_TAP_STATE:
            update = advanced_commands.decode_triple_tap(parameters)
        elif frame.command == CMD_SWIPE_STATE:
            update = advanced_commands.decode_swipe(parameters)
        if update is None:
            return
        target.raw[raw_key] = parameters
        FreeBudsClient._merge_advanced(target, update)

    def read_snapshot(
        self,
        *,
        listen_seconds: float = 0.0,
        include_advanced: bool = False,
    ) -> DeviceSnapshot:
        """Lê bateria/ANC e consome notificações pendentes; pode escutar mais."""

        session = self._session
        if session is None or not session.is_open:
            raise SessionError("a sessão SPP não está aberta")
        if self.info is None:
            raise SessionError("o handshake ainda não foi concluído")

        warnings: list[str] = []
        battery: BatteryState | None = None
        anc: AncState | None = None
        advanced: AdvancedSettings | None = None
        notifications: list[HuaweiFrame] = []

        battery_response = self._request(
            session,
            battery_request(),
            (CMD_BATTERY, CMD_BATTERY_NOTIFY),
            "bateria 0x0108",
            warnings,
        )
        battery_sequence: int | None = None
        if battery_response is not None:
            battery = decode_battery(battery_response.parameters)
            battery_sequence = session.last_response_sequence

        anc_response = self._request(
            session,
            anc_request(),
            (CMD_ANC,),
            "ANC 0x2B2A",
            warnings,
        )
        anc_sequence: int | None = None
        if anc_response is not None:
            anc = decode_anc(anc_response.parameters)
            anc_sequence = session.last_response_sequence

        if include_advanced:
            advanced = self.read_advanced()

        if listen_seconds > 0:
            if session.is_open:
                session.wait_for_frames(listen_seconds)
            else:
                warnings.append("conexão encerrada antes da escuta de notificações")

        # A fila contém apenas quadros que não casaram com nenhuma requisição.
        # Isso inclui mudanças espontâneas recebidas enquanto o worker dormia.
        notification_items = session.take_notification_frames()
        notifications = [frame for _, frame in notification_items]
        for sequence, frame in notification_items:
            # Uma notificação só atualiza o estado se tiver chegado depois da
            # resposta de polling equivalente; caso contrário, o snapshot já
            # contém uma leitura mais nova.
            if frame.command in (CMD_BATTERY, CMD_BATTERY_NOTIFY):
                if battery_sequence is None or sequence > battery_sequence:
                    battery = decode_battery(frame.parameters)
            elif frame.command == CMD_ANC:
                if anc_sequence is None or sequence > anc_sequence:
                    anc = decode_anc(frame.parameters)
            if advanced is not None:
                self._apply_advanced_notification(advanced, frame)

        if session.error is not None:
            warnings.append(f"conexão caiu durante a leitura: {session.error}")

        return DeviceSnapshot(
            info=self.info,
            battery=battery,
            anc=anc,
            notifications=notifications,
            warnings=warnings,
            parser_issues=session.parse_issues,
            timestamp=datetime.now(),
            channel=self.channel or 0,
            advanced=advanced,
        )

    def close(self) -> None:
        """Fecha a sessão e o transporte de forma idempotente."""

        session, self._session = self._session, None
        if session is not None:
            session.close()
        transport, self._transport = self._transport, None
        if transport is not None:
            transport.close()
        self.channel = None

    @staticmethod
    def _request(
        session: HuaweiSession,
        payload: bytes,
        expected: tuple[bytes, ...],
        phase: str,
        warnings: list[str],
    ) -> HuaweiFrame | None:
        try:
            return session.request_bytes(
                payload, expected=expected, timeout=session.response_timeout
            )
        except (RequestTimeout, SessionError) as exc:
            warnings.append(f"{phase}: {exc}")
            return None

    def __enter__(self) -> FreeBudsClient:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
