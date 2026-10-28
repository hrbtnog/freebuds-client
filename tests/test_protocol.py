from __future__ import annotations

import pytest

from freebuds.core.errors import ChecksumError, ProtocolError
from freebuds.core.protocol import (
    FrameParser,
    HuaweiFrame,
    crc16_xmodem,
    decode_stream,
    encode_frame,
    parse_frame,
)

KNOWN_FRAME = bytes.fromhex("5A0006002B03080100A79D")


def test_crc16_xmodem_known_frame() -> None:
    assert crc16_xmodem(KNOWN_FRAME[:-2]) == 0xA79D


def test_encode_known_frame() -> None:
    assert encode_frame(b"\x2B\x03", {8: b"\x00"}) == KNOWN_FRAME


def test_encode_accepts_int_and_string_commands() -> None:
    assert encode_frame(0x2B03, {8: b"\x00"}) == KNOWN_FRAME
    assert encode_frame("2B 03", {8: b"\x00"}) == KNOWN_FRAME


def test_frame_roundtrip_with_empty_and_nonempty_parameters() -> None:
    raw = encode_frame(b"\x01\x07", {0: b"", 3: b"HW", 15: b"FreeBuds"})
    frame = parse_frame(raw)
    assert isinstance(frame, HuaweiFrame)
    assert frame.command == b"\x01\x07"
    assert frame.command_hex == "01 07"
    assert frame.parameters == {0: b"", 3: b"HW", 15: b"FreeBuds"}
    assert frame.checksum_valid
    assert frame.raw == raw
    assert frame.to_bytes() == raw


def test_encode_rejects_bad_parameters() -> None:
    with pytest.raises(ValueError):
        encode_frame(b"\x01\x07", {256: b""})
    with pytest.raises(ValueError):
        encode_frame(b"\x01\x07", {1: b"x" * 256})
    with pytest.raises(ValueError):
        encode_frame(b"\x01\x07", [(1, b"a"), (1, b"b")])
    with pytest.raises(ValueError):
        encode_frame(b"\x01")


def test_parse_rejects_wrong_magic_and_length() -> None:
    with pytest.raises(ProtocolError):
        parse_frame(b"\x5B" + KNOWN_FRAME[1:])
    with pytest.raises(ProtocolError):
        parse_frame(KNOWN_FRAME[:-1])
    with pytest.raises(ProtocolError):
        parse_frame(KNOWN_FRAME + b"\x00")
    with pytest.raises(ProtocolError):
        parse_frame(b"\x5A\x00\x00\x00\x00\x00\x00\x00")


def test_parse_checksum_optional() -> None:
    bad = bytearray(KNOWN_FRAME)
    bad[-1] ^= 0xFF
    with pytest.raises(ChecksumError):
        parse_frame(bytes(bad))
    frame = parse_frame(bytes(bad), validate_checksum=False)
    assert frame.checksum_valid is False
    assert frame.raw == bytes(bad)


def test_parse_duplicate_tlv() -> None:
    # Corpo: comando 01 07 + parâmetro 01/00 repetido.
    body = b"\x01\x07\x01\x00\x01\x00"
    length = len(body) + 1
    raw = b"\x5A" + length.to_bytes(2, "big") + b"\x00" + body
    raw += crc16_xmodem(raw).to_bytes(2, "big")
    with pytest.raises(ProtocolError, match="duplicado"):
        parse_frame(raw)


def test_parser_fragmented_and_concatenated() -> None:
    first = encode_frame(b"\x01\x08", {1: b"\x64"})
    second = encode_frame(b"\x2B\x2A", {1: b"\x01\x01"})
    parser = FrameParser()
    frames = []
    for byte in first + second:
        frames.extend(parser.feed(bytes([byte])))
    assert [frame.command for frame in frames] == [b"\x01\x08", b"\x2B\x2A"]
    assert frames[0].parameters == {1: b"\x64"}
    assert parser.pending == b""


def test_parser_skips_garbage_and_bad_crc() -> None:
    bad = bytearray(encode_frame(b"\x01\x08", {1: b"\x32"}))
    bad[-1] ^= 0x01
    good = encode_frame(b"\x2B\x2A", {1: b"\x02\x02"})
    parser = FrameParser()
    frames = parser.feed(b"lixo" + bytes(bad) + good)
    assert len(frames) == 1
    assert frames[0].command == b"\x2B\x2A"
    assert any("CRC" in issue.message for issue in parser.issues)
    assert any("descartado" in issue.message for issue in parser.issues)


def test_decode_stream_keeps_bad_crc_frames() -> None:
    bad = bytearray(KNOWN_FRAME)
    bad[-1] ^= 0x01
    frames, pending, issues = decode_stream(bytes(bad), validate_checksum=False)
    assert len(frames) == 1
    assert frames[0].checksum_valid is False
    assert pending == b""
    assert issues == []


def test_parser_keeps_incomplete_frame_pending() -> None:
    raw = KNOWN_FRAME
    parser = FrameParser()
    assert parser.feed(raw[:4]) == []
    assert parser.pending == raw[:4]
    assert parser.feed(raw[4:]) == [parse_frame(raw)]
    assert parser.pending == b""


def test_parser_tolerates_invalid_declared_length() -> None:
    # Magic seguido de um tamanho absurdo e depois um quadro válido.
    parser = FrameParser(max_frame_size=100)
    frames = parser.feed(b"\x5A\xFF\xFF\x00" + KNOWN_FRAME)
    assert len(frames) == 1
    assert frames[0].command == b"\x2B\x03"
    assert parser.issues
