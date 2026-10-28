from __future__ import annotations

import pytest

import freebuds.core.client as client_module
from freebuds.core.client import FreeBudsClient, resolve_channels
from freebuds.core.commands import (
    AUDIO_FEATURE_ADAPTIVE_VOLUME,
    AUDIO_FEATURE_CONVERSATION,
    AUDIO_FEATURE_HEAD_CONTROL,
    AUDIO_FEATURE_ONE_EARBUD_ANC,
    AUDIO_FEATURE_SPATIAL,
    CMD_ANC,
    CMD_ANC_WRITE,
    CMD_AUDIO_FEATURE,
    CMD_BATTERY,
    CMD_DEVICE_INFO,
    CMD_DOUBLE_TAP_STATE,
    CMD_DOUBLE_TAP_WRITE,
    CMD_LOW_LATENCY,
    CMD_MULTIPOINT_STATE,
    CMD_PINCH_HOLD_STATE,
    CMD_PINCH_HOLD_WRITE,
    CMD_PRESS_HOLD_STATE,
    CMD_PRESS_HOLD_WRITE,
    CMD_SOUND_PROFILE,
    CMD_SOUND_PROFILE_STATE,
    CMD_SOUND_QUALITY_STATE,
    CMD_SOUND_QUALITY_WRITE,
    CMD_SWIPE_STATE,
    CMD_TRIPLE_TAP_STATE,
    CMD_TRIPLE_TAP_WRITE,
    CMD_WEAR_STATE,
    CMD_WEAR_WRITE,
    SOUND_PROFILE_CUSTOM,
    anc_request,
    anc_set_adaptive_level_request,
    anc_set_level_request,
    anc_set_mode_request,
    battery_request,
    info_request,
)
from freebuds.core.errors import FreeBudsError
from freebuds.core.models import AdvancedSettings, AncState
from freebuds.core.protocol import encode_frame, parse_frame


def test_resolve_channels_prioritizes_saved_then_settings() -> None:
    channels = resolve_channels(
        saved_channel=16,
        settings_channels=[16, 1, 4],
    )
    assert channels == [16, 1, 4]


def test_resolve_channels_requested_wins_and_deduplicates() -> None:
    channels = resolve_channels(
        requested=[4, 4, 1, 0, 31],
        saved_channel=16,
        settings_channels=[16],
    )
    assert channels == [4, 1]


def test_resolve_channels_rejects_empty_result() -> None:
    with pytest.raises(FreeBudsError):
        resolve_channels(requested=[0, 31])


class _FakeTransport:
    def __init__(
        self, address: str, channel: int, *, connect_timeout: float = 5.0
    ) -> None:
        self.address = address
        self.channel = channel
        self.connect_timeout = connect_timeout
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeSession:
    instances: list[_FakeSession] = []

    def __init__(
        self, transport: _FakeTransport, *, response_timeout: float = 2.0
    ) -> None:
        self.transport = transport
        self.response_timeout = response_timeout
        self._open = False
        self.error = None
        self.parse_issues: list[object] = []
        self.notifications: list[tuple[int, object]] = []
        self.sent_payloads: list[bytes] = []
        self.wait_calls: list[float] = []
        self.anc_parameters: dict[int, bytes] = {
            1: bytes([3, 1]),
            2: b"\x01\x00",
        }
        self.sound_profile_id = 5
        self.custom_eq = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A"
        self.custom_name = "My EQ"
        self.spatial_mode = 0
        self.spatial_effect = 0
        self.adaptive_volume = False
        self.conversation_awareness = True
        self.one_earbud_anc = False
        self.head_control = True
        self.head_nod = 1
        self.head_shake = 2
        self.wear_detection = True
        self.multipoint = True
        self.sound_quality = 0
        self.low_latency = False
        self.press_hold_left = 0xFF
        self.press_hold_right = 0x0A
        self.pinch_hold_left = 0x06
        self.pinch_hold_right = 0x06
        self.double_tap_left = 0xFF
        self.double_tap_right = 0xFF
        self.triple_tap_left = 0x07
        self.triple_tap_right = 0x02
        self.swipe_up = 2
        self.swipe_down = 2
        self.last_response_sequence: int | None = None
        self._sequence = 0
        self.instances.append(self)

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> _FakeSession:
        self._open = True
        return self

    def close(self) -> None:
        self._open = False

    def _respond(self, frame: object) -> object:
        self._sequence += 1
        self.last_response_sequence = self._sequence
        return frame

    def request_bytes(
        self,
        payload: bytes,
        *,
        expected: object = None,
        timeout: float | None = None,
    ) -> object:
        self.sent_payloads.append(payload)
        if payload == info_request():
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_DEVICE_INFO,
                        {
                            3: b"HL1SAKM2_Ver.A",
                            7: b"HarmonyOS 7.0.0.350",
                            10: b"BTFT0023-00016D",
                            15: b"BTFT0023",
                        },
                    )
                )
            )
        if payload == battery_request():
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_BATTERY,
                        {1: bytes([83]), 2: bytes([83, 83, 69]), 3: b"\x01\x01\x01"},
                    )
                )
            )
        if payload == anc_request():
            return self._respond(
                parse_frame(encode_frame(CMD_ANC, self.anc_parameters))
            )
        if payload == anc_set_mode_request(1):
            return self._respond(
                parse_frame(encode_frame(CMD_ANC, {1: bytes([3, 1]), 2: b"\x09"}))
            )
        if payload == anc_set_level_request(1, 3):
            return self._respond(
                parse_frame(encode_frame(CMD_ANC, {1: bytes([3, 1]), 2: b"\x09"}))
            )
        if payload == anc_set_level_request(2, 4):
            self.anc_parameters = {1: b"\x04\x02", 2: b"\x05"}
            return self._respond(
                parse_frame(encode_frame(CMD_ANC, self.anc_parameters))
            )
        parsed = parse_frame(payload)
        if (
            parsed.command == CMD_ANC_WRITE
            and parsed.parameters.get(1) == b"\x02\x04"
            and parsed.parameters.get(3) == b"\x01"
            and 4 in parsed.parameters
        ):
            level = parsed.parameters[4][0]
            self.anc_parameters = {1: b"\x04\x02", 2: bytes([level])}
            return self._respond(
                parse_frame(encode_frame(CMD_ANC_WRITE, {2: b"\x00"}))
            )
        if parsed.command == CMD_SOUND_PROFILE_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_SOUND_PROFILE_STATE,
                        {
                            2: bytes([self.sound_profile_id]),
                            6: self.custom_eq,
                            7: self.custom_name.encode("utf-8") + b"\x00",
                        },
                    )
                )
            )
        if parsed.command == CMD_SOUND_PROFILE:
            self.sound_profile_id = parsed.parameters[1][0]
            return self._respond(
                parse_frame(encode_frame(CMD_SOUND_PROFILE, {2: b"\x00"}))
            )
        if parsed.command == CMD_AUDIO_FEATURE:
            feature = parsed.parameters[1][0]
            if feature == AUDIO_FEATURE_SPATIAL:
                if 2 in parsed.parameters and parsed.parameters[2]:
                    self.spatial_mode = parsed.parameters[2][0]
                    return self._respond(
                        parse_frame(encode_frame(CMD_AUDIO_FEATURE, {2: b"\x00"}))
                    )
                return self._respond(
                    parse_frame(
                        encode_frame(
                            CMD_AUDIO_FEATURE,
                            {
                                1: bytes([AUDIO_FEATURE_SPATIAL]),
                                2: bytes([self.spatial_mode]),
                                3: bytes([self.spatial_effect]),
                            },
                        )
                    )
                )
            if feature == AUDIO_FEATURE_ADAPTIVE_VOLUME:
                if 2 in parsed.parameters and parsed.parameters[2]:
                    self.adaptive_volume = parsed.parameters[2][0] != 0
                    return self._respond(
                        parse_frame(encode_frame(CMD_AUDIO_FEATURE, {2: b"\x00"}))
                    )
                return self._respond(
                    parse_frame(
                        encode_frame(
                            CMD_AUDIO_FEATURE,
                            {
                                1: bytes([AUDIO_FEATURE_ADAPTIVE_VOLUME]),
                                2: b"\x01" if self.adaptive_volume else b"\x00",
                            },
                        )
                    )
                )
            if feature == AUDIO_FEATURE_CONVERSATION:
                if 2 in parsed.parameters and parsed.parameters[2]:
                    self.conversation_awareness = parsed.parameters[2][0] != 0
                    return self._respond(
                        parse_frame(encode_frame(CMD_AUDIO_FEATURE, {2: b"\x00"}))
                    )
                return self._respond(
                    parse_frame(
                        encode_frame(
                            CMD_AUDIO_FEATURE,
                            {
                                1: bytes([AUDIO_FEATURE_CONVERSATION]),
                                2: b"\x01" if self.conversation_awareness else b"\x00",
                            },
                        )
                    )
                )
            if feature == AUDIO_FEATURE_ONE_EARBUD_ANC:
                if 2 in parsed.parameters and parsed.parameters[2]:
                    self.one_earbud_anc = parsed.parameters[2][0] != 0
                    return self._respond(
                        parse_frame(encode_frame(CMD_AUDIO_FEATURE, {2: b"\x00"}))
                    )
                return self._respond(
                    parse_frame(
                        encode_frame(
                            CMD_AUDIO_FEATURE,
                            {
                                1: bytes([AUDIO_FEATURE_ONE_EARBUD_ANC]),
                                2: b"\x01" if self.one_earbud_anc else b"\x00",
                            },
                        )
                    )
                )
            if feature == AUDIO_FEATURE_HEAD_CONTROL:
                if (
                    2 in parsed.parameters
                    or 3 in parsed.parameters
                    or 4 in parsed.parameters
                ):
                    if 2 in parsed.parameters:
                        self.head_control = parsed.parameters[2][0] != 0
                    if 3 in parsed.parameters:
                        self.head_nod = parsed.parameters[3][0]
                    if 4 in parsed.parameters:
                        self.head_shake = parsed.parameters[4][0]
                    return self._respond(
                        parse_frame(encode_frame(CMD_AUDIO_FEATURE, {2: b"\x00"}))
                    )
                return self._respond(
                    parse_frame(
                        encode_frame(
                            CMD_AUDIO_FEATURE,
                            {
                                1: bytes([AUDIO_FEATURE_HEAD_CONTROL]),
                                2: b"\x01" if self.head_control else b"\x00",
                                3: bytes([self.head_nod]),
                                4: bytes([self.head_shake]),
                            },
                        )
                    )
                )
        if parsed.command == CMD_WEAR_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_WEAR_STATE,
                        {1: b"\x01" if self.wear_detection else b"\x00"},
                    )
                )
            )
        if parsed.command == CMD_WEAR_WRITE:
            self.wear_detection = parsed.parameters[1][0] != 0
            return self._respond(
                parse_frame(encode_frame(CMD_WEAR_WRITE, {1: b"\x00"}))
            )
        if parsed.command == CMD_MULTIPOINT_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_MULTIPOINT_STATE,
                        {1: b"\x01" if self.multipoint else b"\x00"},
                    )
                )
            )
        if parsed.command == CMD_SOUND_QUALITY_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_SOUND_QUALITY_STATE,
                        {2: bytes([self.sound_quality])},
                    )
                )
            )
        if parsed.command == CMD_SOUND_QUALITY_WRITE:
            self.sound_quality = parsed.parameters[1][0]
            return self._respond(
                parse_frame(encode_frame(CMD_SOUND_QUALITY_WRITE, {2: b"\x00"}))
            )
        if parsed.command == CMD_LOW_LATENCY:
            if 1 in parsed.parameters and parsed.parameters[1]:
                self.low_latency = parsed.parameters[1][0] != 0
                return self._respond(
                    parse_frame(encode_frame(CMD_LOW_LATENCY, {2: b"\x00"}))
                )
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_LOW_LATENCY,
                        {2: b"\x01" if self.low_latency else b"\x00"},
                    )
                )
            )
        if parsed.command == CMD_PRESS_HOLD_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_PRESS_HOLD_STATE,
                        {
                            1: bytes([self.press_hold_left]),
                            2: bytes([self.press_hold_right]),
                        },
                    )
                )
            )
        if parsed.command == CMD_PRESS_HOLD_WRITE:
            if 1 in parsed.parameters:
                self.press_hold_left = parsed.parameters[1][0]
            if 2 in parsed.parameters:
                self.press_hold_right = parsed.parameters[2][0]
            return self._respond(
                parse_frame(encode_frame(CMD_PRESS_HOLD_WRITE, {1: b"\x00"}))
            )
        if parsed.command == CMD_PINCH_HOLD_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_PINCH_HOLD_STATE,
                        {
                            1: b"\x03",
                            2: b"\x00",
                            3: bytes([self.pinch_hold_left]),
                            4: bytes([self.pinch_hold_right]),
                        },
                    )
                )
            )
        if parsed.command == CMD_PINCH_HOLD_WRITE:
            if 3 in parsed.parameters:
                self.pinch_hold_left = parsed.parameters[3][0]
            if 4 in parsed.parameters:
                self.pinch_hold_right = parsed.parameters[4][0]
            return self._respond(
                parse_frame(encode_frame(CMD_PINCH_HOLD_WRITE, {1: b"\x00"}))
            )
        if parsed.command == CMD_DOUBLE_TAP_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_DOUBLE_TAP_STATE,
                        {
                            1: bytes([self.double_tap_left]),
                            2: bytes([self.double_tap_right]),
                        },
                    )
                )
            )
        if parsed.command == CMD_DOUBLE_TAP_WRITE:
            self.double_tap_left = parsed.parameters[1][0]
            self.double_tap_right = parsed.parameters[2][0]
            return self._respond(
                parse_frame(encode_frame(CMD_DOUBLE_TAP_WRITE, {1: b"\x00"}))
            )
        if parsed.command == CMD_TRIPLE_TAP_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_TRIPLE_TAP_STATE,
                        {
                            1: bytes([self.triple_tap_left]),
                            2: bytes([self.triple_tap_right]),
                        },
                    )
                )
            )
        if parsed.command == CMD_TRIPLE_TAP_WRITE:
            if 1 in parsed.parameters:
                self.triple_tap_left = parsed.parameters[1][0]
            if 2 in parsed.parameters:
                self.triple_tap_right = parsed.parameters[2][0]
            return self._respond(
                parse_frame(encode_frame(CMD_TRIPLE_TAP_WRITE, {1: b"\x00"}))
            )
        if parsed.command == CMD_SWIPE_STATE:
            return self._respond(
                parse_frame(
                    encode_frame(
                        CMD_SWIPE_STATE,
                        {
                            1: bytes([self.swipe_up]),
                            2: bytes([self.swipe_down]),
                        },
                    )
                )
            )
        raise AssertionError(f"payload inesperado: {payload.hex()}")

    def wait_for_notifications(
        self,
        timeout: float,
        *,
        should_stop: object = None,
    ) -> bool:
        self.wait_calls.append(timeout)
        return True

    def take_notification_frames(self) -> list[tuple[int, object]]:
        items = list(self.notifications)
        self.notifications.clear()
        return items

    def take_notifications(self) -> list[object]:
        return [frame for _, frame in self.take_notification_frames()]

    def wait_for_frames(self, seconds: float) -> list[object]:
        return []


def test_client_connects_reads_snapshot_and_closes(monkeypatch) -> None:
    _FakeSession.instances.clear()
    monkeypatch.setattr(client_module, "RfcommTransport", _FakeTransport)
    monkeypatch.setattr(client_module, "HuaweiSession", _FakeSession)

    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    connection = client.connect()
    assert connection.channel == 1
    assert connection.info.model == "BTFT0023"
    assert connection.info.submodel == "BTFT0023-00016D"
    assert client.connected is True

    notification = parse_frame(
        encode_frame(CMD_ANC, {1: bytes([0, 2]), 2: b"\x01\x00"})
    )
    _FakeSession.instances[0].notifications.append((100, notification))

    snapshot = client.read_snapshot()
    assert snapshot.battery is not None
    assert snapshot.battery.global_level == 83
    assert snapshot.battery.left == 83
    assert snapshot.battery.right == 83
    assert snapshot.battery.case == 69
    assert snapshot.battery.charging is True
    assert snapshot.anc is not None
    assert snapshot.anc.mode == "awareness"
    assert snapshot.anc.level is None
    assert snapshot.notifications == [notification]
    assert snapshot.warnings == []

    client.close()
    assert client.connected is False
    assert _FakeSession.instances[0].transport.closed is True


def test_client_waits_for_notifications_through_session(monkeypatch) -> None:
    _FakeSession.instances.clear()
    monkeypatch.setattr(client_module, "RfcommTransport", _FakeTransport)
    monkeypatch.setattr(client_module, "HuaweiSession", _FakeSession)

    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    client.connect()
    assert client.wait_for_notifications(0.05) is True
    assert _FakeSession.instances[0].wait_calls == [0.05]
    client.close()


def test_client_set_anc_mode_and_level(monkeypatch) -> None:
    _FakeSession.instances.clear()
    monkeypatch.setattr(client_module, "RfcommTransport", _FakeTransport)
    monkeypatch.setattr(client_module, "HuaweiSession", _FakeSession)

    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    client.connect()
    state = client.set_anc(mode_code=1)
    assert state.mode == "cancellation"
    assert state.level == "dynamic"
    assert _FakeSession.instances[0].sent_payloads[-1] == anc_set_mode_request(1)

    state = client.set_anc(mode_code=1, level_code=3)
    assert state.level_code == 3
    assert _FakeSession.instances[0].sent_payloads[-1] == anc_set_level_request(1, 3)

    with pytest.raises(ValueError):
        client.set_anc(mode_code=9)
    client.close()


def test_client_set_anc_adaptive_mode_and_level(monkeypatch) -> None:
    _FakeSession.instances.clear()
    monkeypatch.setattr(client_module, "RfcommTransport", _FakeTransport)
    monkeypatch.setattr(client_module, "HuaweiSession", _FakeSession)

    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    client.connect()
    state = client.set_anc(mode_code=2, level_code=4)
    assert state.mode == "awareness"
    assert state.level == "adaptive"
    assert state.adaptive_level == 5
    assert _FakeSession.instances[0].sent_payloads[-1] == anc_set_level_request(
        2, 4
    )

    state = client.set_anc_adaptive_level(9)
    assert state.mode == "awareness"
    assert state.level == "adaptive"
    assert state.adaptive_level == 9
    assert (
        anc_set_adaptive_level_request(9)
        in _FakeSession.instances[0].sent_payloads
    )

    with pytest.raises(ValueError):
        client.set_anc_adaptive_level(11)
    client.close()


def test_client_confirmation_retries_after_stale_anc_state(monkeypatch) -> None:
    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    stale = AncState(
        mode_code=2,
        mode="awareness",
        level_code=4,
        level="adaptive",
        adaptive_level=4,
    )
    fresh = AncState(
        mode_code=2,
        mode="awareness",
        level_code=4,
        level="adaptive",
        adaptive_level=5,
    )
    states = iter([stale, fresh])
    monkeypatch.setattr(client, "read_anc", lambda: next(states))

    state = client._confirm_anc_state(
        mode_code=2,
        level_code=4,
        adaptive_level=5,
    )
    assert state.adaptive_level == 5


def test_client_ignores_notification_older_than_poll_response(monkeypatch) -> None:
    _FakeSession.instances.clear()
    monkeypatch.setattr(client_module, "RfcommTransport", _FakeTransport)
    monkeypatch.setattr(client_module, "HuaweiSession", _FakeSession)

    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    client.connect()
    notification = parse_frame(
        encode_frame(CMD_ANC, {1: bytes([0, 2]), 2: b"\x01\x00"})
    )
    # Sequência anterior às respostas de bateria/ANC do polling.
    _FakeSession.instances[0].notifications.append((0, notification))

    snapshot = client.read_snapshot()
    assert snapshot.anc is not None
    assert snapshot.anc.mode == "cancellation"
    assert snapshot.anc.level == "dynamic"
    assert snapshot.notifications == [notification]

    client.close()


def test_client_rejects_invalid_timeout() -> None:
    with pytest.raises(ValueError):
        FreeBudsClient("AA:BB:CC:DD:EE:FF", connect_timeout=0)
    with pytest.raises(ValueError):
        FreeBudsClient("AA:BB:CC:DD:EE:FF", response_timeout=-1)


def test_connect_can_be_cancelled_before_opening_socket() -> None:
    client = FreeBudsClient("AA:BB:CC:DD:EE:FF", channels=[1, 16])
    with pytest.raises(FreeBudsError, match="cancelada"):
        client.connect(should_stop=lambda: True)
    assert client.connected is False


def test_client_read_advanced_and_merge_in_snapshot(monkeypatch) -> None:
    _FakeSession.instances.clear()
    monkeypatch.setattr(client_module, "RfcommTransport", _FakeTransport)
    monkeypatch.setattr(client_module, "HuaweiSession", _FakeSession)

    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    client.connect()

    advanced = client.read_advanced()
    assert advanced.sound_profile_id == 5
    assert advanced.custom_name == "My EQ"
    assert advanced.spatial_mode == 0
    assert advanced.adaptive_volume is False
    assert advanced.conversation_awareness is True
    assert advanced.one_earbud_anc is False
    assert advanced.head_control is True
    assert advanced.head_nod_action == 1
    assert advanced.head_shake_action == 2
    assert advanced.wear_detection is True
    assert advanced.multipoint is True
    assert advanced.sound_quality == 0
    assert advanced.low_latency is False
    assert advanced.press_hold_left == 0xFF
    assert advanced.press_hold_right == 0x0A
    assert advanced.pinch_hold_left == 0x06
    assert advanced.pinch_hold_right == 0x06
    assert advanced.double_tap_left == 0xFF
    assert advanced.double_tap_right == 0xFF
    assert advanced.triple_tap_left == 0x07
    assert advanced.triple_tap_right == 0x02
    assert advanced.swipe_up == 2
    assert advanced.swipe_down == 2
    assert "2B4A" in advanced.raw
    assert "2BB4:18" in advanced.raw
    assert "2BB4:02" in advanced.raw

    snapshot = client.read_snapshot(include_advanced=True)
    assert snapshot.advanced is not None
    assert snapshot.advanced.sound_profile_id == 5

    client.close()


def test_client_set_advanced_settings(monkeypatch) -> None:
    _FakeSession.instances.clear()
    monkeypatch.setattr(client_module, "RfcommTransport", _FakeTransport)
    monkeypatch.setattr(client_module, "HuaweiSession", _FakeSession)

    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    client.connect()

    # Perfil comum e personalizado
    p = client.set_sound_profile(2)
    assert p.sound_profile_id == 2
    p_custom = client.set_sound_profile(SOUND_PROFILE_CUSTOM)
    assert p_custom.sound_profile_id == SOUND_PROFILE_CUSTOM

    # Áudio espacial
    s = client.set_spatial_mode(1)
    assert s.spatial_mode == 1

    # Features booleanas de áudio
    v = client.set_adaptive_volume(True)
    assert v.adaptive_volume is True
    c = client.set_conversation_awareness(False)
    assert c.conversation_awareness is False
    o = client.set_one_earbud_anc(True)
    assert o.one_earbud_anc is True

    # Controle de cabeça
    h = client.set_head_control(enabled=False, nod_action=0, shake_action=0)
    assert h.head_control is False
    assert h.head_nod_action == 0
    assert h.head_shake_action == 0

    # Detecção de uso, qualidade, latência
    w = client.set_wear_detection(False)
    assert w.wear_detection is False
    q = client.set_sound_quality(1)
    assert q.sound_quality == 1
    ll = client.set_low_latency(True)
    assert ll.low_latency is True

    # Gestos
    ph = client.set_press_hold("left", 0x0A)
    assert ph.press_hold_left == 0x0A
    ph_r = client.set_press_hold("right", 0xFF)
    assert ph_r.press_hold_right == 0xFF

    pi = client.set_pinch_hold("left", 0xFF)
    assert pi.pinch_hold_left == 0xFF

    dt = client.set_double_tap(0x01, 0x01)
    assert dt.double_tap_left == 0x01
    assert dt.double_tap_right == 0x01

    tt = client.set_triple_tap("right", 0x07)
    assert tt.triple_tap_right == 0x07

    client.close()


def test_client_advanced_confirmation_timeout(monkeypatch) -> None:
    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1], response_timeout=0.1)

    with pytest.raises(FreeBudsError, match="não confirmou teste"):
        client._confirm_advanced(
            read=lambda: AdvancedSettings(sound_profile_id=1),
            predicate=lambda state: state.sound_profile_id == 2,
            description="teste",
        )


def test_client_advanced_notification_updates_snapshot(monkeypatch) -> None:
    _FakeSession.instances.clear()
    monkeypatch.setattr(client_module, "RfcommTransport", _FakeTransport)
    monkeypatch.setattr(client_module, "HuaweiSession", _FakeSession)

    client = FreeBudsClient("aa:bb:cc:dd:ee:ff", channels=[1])
    client.connect()

    # Notificação espontânea de troca de perfil de som
    notify_frame = parse_frame(
        encode_frame(CMD_SOUND_PROFILE_STATE, {2: bytes([9])})
    )
    _FakeSession.instances[0].notifications.append((500, notify_frame))

    snapshot = client.read_snapshot(include_advanced=True)
    assert snapshot.advanced is not None
    assert snapshot.advanced.sound_profile_id == 9

    client.close()

