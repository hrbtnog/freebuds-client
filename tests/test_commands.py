from __future__ import annotations

import pytest

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
    CMD_BATTERY_NOTIFY,
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
    SOUND_PROFILE_CLASSIC,
    SOUND_PROFILE_CLASSIC_EQ,
    SOUND_PROFILE_CLASSIC_NAME,
    SOUND_PROFILE_CUSTOM,
    anc_request,
    anc_set_adaptive_level_request,
    anc_set_level_request,
    anc_set_mode_request,
    audio_feature_request,
    audio_feature_set_request,
    battery_request,
    decode_anc,
    decode_audio_feature,
    decode_battery,
    decode_device_info,
    decode_double_tap,
    decode_head_control,
    decode_known_frame,
    decode_low_latency,
    decode_multipoint,
    decode_pinch_hold,
    decode_press_hold,
    decode_sound_profile,
    decode_sound_quality,
    decode_spatial,
    decode_swipe,
    decode_triple_tap,
    decode_wear_detection,
    double_tap_request,
    double_tap_set_request,
    head_control_set_request,
    info_request,
    low_latency_request,
    low_latency_set_request,
    multipoint_request,
    pinch_hold_request,
    pinch_hold_set_request,
    press_hold_request,
    press_hold_set_request,
    sound_profile_request,
    sound_profile_set_request,
    sound_quality_request,
    sound_quality_set_request,
    spatial_request,
    spatial_set_mode_request,
    swipe_request,
    triple_tap_request,
    triple_tap_set_request,
    wear_detection_request,
    wear_detection_set_request,
)
from freebuds.core.protocol import HuaweiFrame, encode_frame, parse_frame


def test_request_frames() -> None:
    info = parse_frame(info_request())
    assert info.command == CMD_DEVICE_INFO
    assert len(info.parameters) == 32
    assert set(info.parameters) == set(range(32))
    assert all(value == b"" for value in info.parameters.values())

    battery = parse_frame(battery_request())
    assert battery.command == CMD_BATTERY
    assert battery.parameters == {1: b"", 2: b"", 3: b""}

    anc = parse_frame(anc_request())
    assert anc.command == CMD_ANC
    assert anc.parameters == {1: b"", 2: b""}

    normal = parse_frame(anc_set_mode_request(0))
    assert normal.command == CMD_ANC_WRITE
    assert normal.parameters == {1: b"\x00\x00"}

    cancellation = parse_frame(anc_set_mode_request(1))
    assert cancellation.parameters == {1: b"\x01\xFF"}

    awareness = parse_frame(anc_set_mode_request(2))
    assert awareness.parameters == {1: b"\x02\xFF"}

    level = parse_frame(anc_set_level_request(1, 3))
    assert level.command == CMD_ANC_WRITE
    assert level.parameters == {1: b"\x01\x03"}

    adaptive_mode = parse_frame(anc_set_level_request(2, 4))
    assert adaptive_mode.parameters == {1: b"\x02\x04"}

    adaptive_level = parse_frame(anc_set_adaptive_level_request(5))
    assert adaptive_level.command == CMD_ANC_WRITE
    assert adaptive_level.parameters == {
        1: b"\x02\x04",
        3: b"\x01",
        4: b"\x05",
    }

    with pytest.raises(ValueError):
        anc_set_mode_request(9)
    with pytest.raises(ValueError):
        anc_set_level_request(0, 1)
    with pytest.raises(ValueError):
        anc_set_level_request(1, 8)
    with pytest.raises(ValueError):
        anc_set_level_request(2, 3)
    with pytest.raises(ValueError):
        anc_set_adaptive_level_request(-1)
    with pytest.raises(ValueError):
        anc_set_adaptive_level_request(11)


def test_decode_device_info_known_and_unknown_fields() -> None:
    params = {
        3: b"HW1.0",
        7: b"FW2.0",
        9: b"SN123",
        10: b"Pro",
        15: b"FreeBuds Pro 5",
        24: b"L-LEFT,R-RIGHT",
        20: b"\xFF\x01",
    }
    info = decode_device_info(params)
    assert info.hardware_version == "HW1.0"
    assert info.software_version == "FW2.0"
    assert info.serial_number == "SN123"
    assert info.submodel == "Pro"
    assert info.model == "FreeBuds Pro 5"
    assert info.left_serial_number == "LEFT"
    assert info.right_serial_number == "RIGHT"
    assert info.fields[20] == "ff 01"
    assert info.raw_fields[20] == b"\xFF\x01"
    assert info.to_dict()["raw_fields"]["20"] == "ff 01"


def test_decode_device_info_gbk_and_missing_values() -> None:
    info = decode_device_info({15: "测试".encode("gbk")})
    assert info.model == "测试"
    assert info.hardware_version is None
    assert info.left_serial_number is None


def test_decode_device_info_binary_field_is_hex_not_gbk() -> None:
    raw = bytes.fromhex("DE AD BE EF")
    info = decode_device_info({32: raw})
    assert info.fields[32] == "de ad be ef"
    assert info.raw_fields[32] == raw


def test_decode_battery_complete_and_partial() -> None:
    battery = decode_battery({1: b"\x64", 2: b"\x5A\x50\x46", 3: b"\x00\x01"})
    assert battery.global_level == 100
    assert battery.left == 90
    assert battery.right == 80
    assert battery.case == 70
    assert battery.charging is True
    assert battery.charging_flags == b"\x00\x01"

    partial = decode_battery({2: b"\x01\x02", 3: b""})
    assert partial.global_level is None
    assert partial.left is None
    assert partial.right is None
    assert partial.case is None
    assert partial.charging is None


def test_decode_anc_modes_and_levels() -> None:
    cancel = decode_anc({1: b"\x01\x01"})
    assert cancel.mode == "cancellation"
    assert cancel.level == "comfort"
    assert cancel.mode_code == 1
    assert cancel.level_code == 1

    aware = decode_anc({1: b"\x02\x02"})
    assert aware.mode == "awareness"
    assert aware.level == "normal"
    assert aware.adaptive_level is None

    adaptive = decode_anc({1: b"\x04\x02", 2: b"\x05"})
    assert adaptive.mode == "awareness"
    assert adaptive.level == "adaptive"
    assert adaptive.adaptive_level == 5

    out_of_range = decode_anc({1: b"\x04\x02", 2: b"\x0B"})
    assert out_of_range.level == "adaptive"
    assert out_of_range.adaptive_level is None

    normal = decode_anc({1: b"\x00\x00", 2: b"\x05"})
    assert normal.mode == "normal"
    assert normal.level is None
    assert normal.adaptive_level is None

    unknown = decode_anc({1: b"\x00\x09"})
    assert unknown.mode is None
    assert unknown.mode_code == 9
    assert unknown.level is None

    missing = decode_anc({})
    assert missing.mode is None
    assert missing.mode_code is None


def test_decode_known_frame() -> None:
    frame = HuaweiFrame(CMD_BATTERY_NOTIFY, {2: b"\x32\x33\x34"}, checksum_valid=True)
    decoded = decode_known_frame(frame)
    assert decoded is not None
    assert decoded["left"] == 50
    assert decoded["right"] == 51
    assert decoded["case"] == 52
    assert decode_known_frame(HuaweiFrame(b"\x99\x99", {})) is None


def test_decode_real_pro_battery_and_anc_frames() -> None:
    battery_frame = parse_frame(
        bytes.fromhex("5A001B0001080101530203535345030301010104020A140502010106010A9F73")
    )
    assert battery_frame.checksum_valid
    battery = decode_battery(battery_frame.parameters)
    assert (battery.global_level, battery.left, battery.right, battery.case) == (
        83,
        83,
        83,
        69,
    )
    assert battery.charging is True
    assert battery.charging_flags == b"\x01\x01\x01"
    assert battery.parameters[4] == b"\x0A\x14"
    assert battery.parameters[5] == b"\x01\x01"
    assert battery.parameters[6] == b"\x0A"

    anc_frame = parse_frame(
        bytes.fromhex("5A000A002B2A01020000020100E8E6")
    )
    assert anc_frame.checksum_valid
    anc = decode_anc(anc_frame.parameters)
    assert anc.mode_code == 0
    assert anc.mode == "normal"
    assert anc.level_code == 0
    assert anc.level is None
    assert anc.parameters == {1: b"\x00\x00", 2: b"\x00"}

    cancel_frame = parse_frame(
        bytes.fromhex("5A000A002B2A010203010201007080")
    )
    assert cancel_frame.checksum_valid
    cancel = decode_anc(cancel_frame.parameters)
    assert cancel.mode_code == 1
    assert cancel.mode == "cancellation"
    assert cancel.level_code == 3
    assert cancel.level == "dynamic"

    aware_frame = parse_frame(
        bytes.fromhex("5A000A002B2A010204020201008C88")
    )
    assert aware_frame.checksum_valid
    aware = decode_anc(aware_frame.parameters)
    assert aware.mode_code == 2
    assert aware.mode == "awareness"
    assert aware.level_code == 4
    assert aware.level == "adaptive"
    assert aware.adaptive_level == 0

    adaptive_frame = parse_frame(
        encode_frame(CMD_ANC, {1: b"\x04\x02", 2: b"\x05"})
    )
    adaptive = decode_anc(adaptive_frame.parameters)
    assert adaptive.level == "adaptive"
    assert adaptive.adaptive_level == 5
    assert adaptive.to_dict()["adaptive_level"] == 5


def test_sound_profile_builders_and_decoders() -> None:
    req = parse_frame(sound_profile_request())
    assert req.command == CMD_SOUND_PROFILE_STATE
    assert req.parameters == {2: b""}

    standard = parse_frame(sound_profile_set_request(5))
    assert standard.command == CMD_SOUND_PROFILE
    assert standard.parameters == {1: b"\x05"}

    classic = parse_frame(sound_profile_set_request(SOUND_PROFILE_CLASSIC))
    assert classic.command == CMD_SOUND_PROFILE
    assert classic.parameters == {
        1: bytes([SOUND_PROFILE_CLASSIC]),
        2: b"\x0A",
        5: b"\x01",
        3: SOUND_PROFILE_CLASSIC_EQ,
        4: SOUND_PROFILE_CLASSIC_NAME,
    }

    custom = parse_frame(
        sound_profile_set_request(
            SOUND_PROFILE_CUSTOM,
            custom_eq=b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A",
            custom_name="My EQ",
        )
    )
    assert custom.command == CMD_SOUND_PROFILE
    assert custom.parameters[1] == bytes([SOUND_PROFILE_CUSTOM])
    assert custom.parameters[2] == b"\x0A"
    assert custom.parameters[5] == b"\x01"
    assert custom.parameters[3] == b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A"
    assert custom.parameters[4] == b"My EQ"

    decoded = decode_sound_profile(
        {2: b"\x05", 6: b"\x10\x20", 7: b"Custom Preset\x00"}
    )
    assert decoded.sound_profile_id == 5
    assert decoded.custom_eq == b"\x10\x20"
    assert decoded.custom_name == "Custom Preset"


def test_spatial_builders_and_decoders() -> None:
    req = parse_frame(spatial_request())
    assert req.command == CMD_AUDIO_FEATURE
    assert req.parameters == {1: bytes([AUDIO_FEATURE_SPATIAL]), 2: b"", 3: b""}

    set_req = parse_frame(spatial_set_mode_request(1))
    assert set_req.command == CMD_AUDIO_FEATURE
    assert set_req.parameters == {1: bytes([AUDIO_FEATURE_SPATIAL]), 2: b"\x01"}

    decoded = decode_spatial({1: bytes([AUDIO_FEATURE_SPATIAL]), 2: b"\x02", 3: b"\x01"})
    assert decoded.spatial_mode == 2
    assert decoded.spatial_effect == 1


def test_audio_features_builders_and_decoders() -> None:
    vol_req = parse_frame(audio_feature_request(AUDIO_FEATURE_ADAPTIVE_VOLUME))
    assert vol_req.command == CMD_AUDIO_FEATURE
    assert vol_req.parameters == {1: bytes([AUDIO_FEATURE_ADAPTIVE_VOLUME]), 2: b""}

    vol_set = parse_frame(audio_feature_set_request(AUDIO_FEATURE_ADAPTIVE_VOLUME, 1))
    assert vol_set.parameters == {1: bytes([AUDIO_FEATURE_ADAPTIVE_VOLUME]), 2: b"\x01"}

    decoded_vol = decode_audio_feature({2: b"\x01"}, AUDIO_FEATURE_ADAPTIVE_VOLUME)
    assert decoded_vol.adaptive_volume is True

    conv_req = parse_frame(audio_feature_request(AUDIO_FEATURE_CONVERSATION))
    assert conv_req.parameters == {1: bytes([AUDIO_FEATURE_CONVERSATION]), 2: b""}
    decoded_conv = decode_audio_feature({2: b"\x00"}, AUDIO_FEATURE_CONVERSATION)
    assert decoded_conv.conversation_awareness is False

    anc1_req = parse_frame(audio_feature_request(AUDIO_FEATURE_ONE_EARBUD_ANC))
    assert anc1_req.parameters == {1: bytes([AUDIO_FEATURE_ONE_EARBUD_ANC]), 2: b""}
    decoded_anc1 = decode_audio_feature({2: b"\x01"}, AUDIO_FEATURE_ONE_EARBUD_ANC)
    assert decoded_anc1.one_earbud_anc is True


def test_head_control_builders_and_decoders() -> None:
    req = parse_frame(audio_feature_request(AUDIO_FEATURE_HEAD_CONTROL))
    assert req.parameters == {1: bytes([AUDIO_FEATURE_HEAD_CONTROL])}

    set_all = parse_frame(
        head_control_set_request(enabled=True, nod_action=1, shake_action=2)
    )
    assert set_all.parameters == {
        1: bytes([AUDIO_FEATURE_HEAD_CONTROL]),
        2: b"\x01",
        3: b"\x01",
        4: b"\x02",
    }

    set_partial = parse_frame(head_control_set_request(enabled=False))
    assert set_partial.parameters == {
        1: bytes([AUDIO_FEATURE_HEAD_CONTROL]),
        2: b"\x00",
    }

    decoded = decode_head_control({2: b"\x01", 3: b"\x01", 4: b"\x02"})
    assert decoded.head_control is True
    assert decoded.head_nod_action == 1
    assert decoded.head_shake_action == 2


def test_wear_detection_and_multipoint() -> None:
    wear_req = parse_frame(wear_detection_request())
    assert wear_req.command == CMD_WEAR_STATE
    assert wear_req.parameters == {1: b""}

    wear_on = parse_frame(wear_detection_set_request(True))
    assert wear_on.command == CMD_WEAR_WRITE
    assert wear_on.parameters == {1: b"\x01"}

    wear_off = parse_frame(wear_detection_set_request(False))
    assert wear_off.parameters == {1: b"\x00"}

    decoded_wear = decode_wear_detection({1: b"\x01"})
    assert decoded_wear.wear_detection is True

    mp_req = parse_frame(multipoint_request())
    assert mp_req.command == CMD_MULTIPOINT_STATE
    assert mp_req.parameters == {1: b""}

    decoded_mp = decode_multipoint({1: b"\x01"})
    assert decoded_mp.multipoint is True


def test_sound_quality_and_low_latency() -> None:
    sq_req = parse_frame(sound_quality_request())
    assert sq_req.command == CMD_SOUND_QUALITY_STATE
    assert sq_req.parameters == {}

    sq_set = parse_frame(sound_quality_set_request(1))
    assert sq_set.command == CMD_SOUND_QUALITY_WRITE
    assert sq_set.parameters == {1: b"\x01"}

    decoded_sq = decode_sound_quality({2: b"\x01"})
    assert decoded_sq.sound_quality == 1

    ll_req = parse_frame(low_latency_request())
    assert ll_req.command == CMD_LOW_LATENCY
    assert ll_req.parameters == {2: b""}

    ll_set = parse_frame(low_latency_set_request(True))
    assert ll_set.command == CMD_LOW_LATENCY
    assert ll_set.parameters == {1: b"\x01"}

    decoded_ll = decode_low_latency({2: b"\x01"})
    assert decoded_ll.low_latency is True


def test_gestures_builders_and_decoders() -> None:
    ph_req = parse_frame(press_hold_request())
    assert ph_req.command == CMD_PRESS_HOLD_STATE
    assert ph_req.parameters == {1: b"", 2: b""}

    ph_set_l = parse_frame(press_hold_set_request("left", 0x0A))
    assert ph_set_l.command == CMD_PRESS_HOLD_WRITE
    assert ph_set_l.parameters == {1: b"\x0A"}

    ph_set_r = parse_frame(press_hold_set_request("right", 0xFF))
    assert ph_set_r.command == CMD_PRESS_HOLD_WRITE
    assert ph_set_r.parameters == {2: b"\xFF"}

    decoded_ph = decode_press_hold({1: b"\xFF", 2: b"\x0A"})
    assert decoded_ph.press_hold_left == 0xFF
    assert decoded_ph.press_hold_right == 0x0A

    pi_req = parse_frame(pinch_hold_request())
    assert pi_req.command == CMD_PINCH_HOLD_STATE
    assert pi_req.parameters == {1: b"\x03", 2: b"\x00"}

    pi_set = parse_frame(pinch_hold_set_request("left", 0x06))
    assert pi_set.command == CMD_PINCH_HOLD_WRITE
    assert pi_set.parameters == {1: b"\x03", 2: b"\x00", 3: b"\x06"}

    decoded_pi = decode_pinch_hold({3: b"\x06", 4: b"\x06"})
    assert decoded_pi.pinch_hold_left == 0x06
    assert decoded_pi.pinch_hold_right == 0x06

    dt_req = parse_frame(double_tap_request())
    assert dt_req.command == CMD_DOUBLE_TAP_STATE
    assert dt_req.parameters == {1: b"", 2: b""}

    dt_set = parse_frame(double_tap_set_request(0x01, 0xFF))
    assert dt_set.command == CMD_DOUBLE_TAP_WRITE
    assert dt_set.parameters == {1: b"\x01", 2: b"\xFF"}

    decoded_dt = decode_double_tap({1: b"\x01", 2: b"\xFF"})
    assert decoded_dt.double_tap_left == 0x01
    assert decoded_dt.double_tap_right == 0xFF

    tt_req = parse_frame(triple_tap_request())
    assert tt_req.command == CMD_TRIPLE_TAP_STATE
    assert tt_req.parameters == {1: b"", 2: b""}

    tt_set = parse_frame(triple_tap_set_request("right", 0x02))
    assert tt_set.command == CMD_TRIPLE_TAP_WRITE
    assert tt_set.parameters == {2: b"\x02"}

    decoded_tt = decode_triple_tap({1: b"\x07", 2: b"\x02"})
    assert decoded_tt.triple_tap_left == 0x07
    assert decoded_tt.triple_tap_right == 0x02

    sw_req = parse_frame(swipe_request())
    assert sw_req.command == CMD_SWIPE_STATE
    assert sw_req.parameters == {1: b"", 2: b""}

    decoded_sw = decode_swipe({1: b"\x02", 2: b"\x00"})
    assert decoded_sw.swipe_up == 0x02
    assert decoded_sw.swipe_down == 0x00


def test_advanced_validation_errors() -> None:
    with pytest.raises(ValueError, match="perfil de som inválido"):
        sound_profile_set_request(999)

    with pytest.raises(ValueError, match="Personalizado"):
        sound_profile_set_request(SOUND_PROFILE_CUSTOM)

    with pytest.raises(ValueError, match="longo demais"):
        sound_profile_set_request(
            SOUND_PROFILE_CUSTOM,
            custom_eq=b"\x01" * 10,
            custom_name="A" * 32,
        )

    with pytest.raises(ValueError, match="modo espacial inválido"):
        spatial_set_mode_request(99)

    with pytest.raises(ValueError, match="recurso de áudio inválido"):
        audio_feature_request(0xFF)

    with pytest.raises(ValueError, match="recurso de áudio inválido"):
        audio_feature_set_request(0xFF, 1)

    with pytest.raises(ValueError, match="fora de 0..255"):
        audio_feature_set_request(AUDIO_FEATURE_ADAPTIVE_VOLUME, 300)

    with pytest.raises(ValueError, match="nenhuma alteração"):
        head_control_set_request()

    with pytest.raises(ValueError, match="ação de aceno inválida"):
        head_control_set_request(nod_action=9)

    with pytest.raises(ValueError, match="ação de balançar a cabeça inválida"):
        head_control_set_request(shake_action=9)

    with pytest.raises(ValueError, match="qualidade de som inválida"):
        sound_quality_set_request(5)

    with pytest.raises(ValueError, match="lado deve ser 'left' ou 'right'"):
        press_hold_set_request("both", 0x0A)

    with pytest.raises(ValueError, match="ação de pressionar e segurar inválida"):
        press_hold_set_request("left", 0x55)

    with pytest.raises(ValueError, match="lado deve ser 'left' ou 'right'"):
        pinch_hold_set_request("center", 0x06)

    with pytest.raises(ValueError, match="ação de pinçar e segurar inválida"):
        pinch_hold_set_request("left", 0x99)

    with pytest.raises(ValueError, match="ação de toque duplo inválida"):
        double_tap_set_request(0x99, 0x01)

    with pytest.raises(ValueError, match="lado deve ser 'left' ou 'right'"):
        triple_tap_set_request("top", 0x02)

    with pytest.raises(ValueError, match="ação de toque triplo inválida"):
        triple_tap_set_request("left", 0x99)

