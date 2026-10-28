from __future__ import annotations

import queue
import time

import pytest

from freebuds.core.commands import CMD_BATTERY_NOTIFY, CMD_DEVICE_INFO
from freebuds.core.errors import RequestTimeout, SessionClosedError
from freebuds.core.protocol import encode_frame, parse_frame
from freebuds.core.session import HuaweiSession


class FakeTransport:
    address = "AA:BB:CC:DD:EE:FF"
    channel = 1

    def __init__(self, handler=None) -> None:
        self.handler = handler
        self.incoming: queue.Queue[bytes] = queue.Queue()
        self.sent: list[bytes] = []
        self.closed = False
        self.timeout: float | None = None

    def connect(self) -> None:
        self.closed = False

    def settimeout(self, timeout: float | None) -> None:
        self.timeout = timeout

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)
        if self.handler is not None:
            responses = self.handler(parse_frame(data))
            for response in responses:
                self.incoming.put(response)

    def recv(self, size: int | None = None) -> bytes:
        try:
            return self.incoming.get(timeout=0.05)
        except queue.Empty as exc:
            raise TimeoutError() from exc

    def close(self) -> None:
        self.closed = True

    def push(self, data: bytes) -> None:
        self.incoming.put(data)


def echo_handler(request):
    payload = {2: b"\x5A\x50\x46"} if request.command == CMD_DEVICE_INFO else {}
    return [encode_frame(request.command, payload)]


def test_session_request_response() -> None:
    transport = FakeTransport(echo_handler)
    session = HuaweiSession(transport, response_timeout=1.0)
    try:
        session.open()
        response = session.request(CMD_DEVICE_INFO, {0: b""}, timeout=1.0)
        assert response.command == CMD_DEVICE_INFO
        assert response.parameters == {2: b"\x5A\x50\x46"}
        assert session.last_request is not None
        assert session.last_request.command == CMD_DEVICE_INFO
        assert transport.sent
    finally:
        session.close()
    assert transport.closed


def test_session_accepts_battery_notification_as_response() -> None:
    def handler(request):
        return [encode_frame(CMD_BATTERY_NOTIFY, {2: b"\x32\x33\x34"})]

    transport = FakeTransport(handler)
    session = HuaweiSession(transport, response_timeout=1.0)
    try:
        session.open()
        response = session.request(
            b"\x01\x08",
            {1: b"", 2: b"", 3: b""},
            expected=(b"\x01\x08", CMD_BATTERY_NOTIFY),
            timeout=1.0,
        )
        assert response.command == CMD_BATTERY_NOTIFY
    finally:
        session.close()


def test_session_timeout() -> None:
    transport = FakeTransport(lambda request: [])
    session = HuaweiSession(transport, response_timeout=0.2)
    try:
        session.open()
        with pytest.raises(RequestTimeout):
            session.request(CMD_DEVICE_INFO, {}, timeout=0.1)
    finally:
        session.close()


def test_session_records_unsolicited_notifications() -> None:
    transport = FakeTransport(lambda request: [])
    session = HuaweiSession(transport, response_timeout=1.0)
    try:
        session.open()
        transport.push(encode_frame(CMD_BATTERY_NOTIFY, {1: b"\x64"}))
        deadline = time.monotonic() + 1.0
        while session.last_sequence == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        frames = session.frames_since(0)
        assert len(frames) == 1
        assert frames[0].command == CMD_BATTERY_NOTIFY
    finally:
        session.close()


def test_session_takes_only_unsolicited_notifications() -> None:
    transport = FakeTransport(echo_handler)
    session = HuaweiSession(transport, response_timeout=1.0)
    try:
        session.open()
        response = session.request(CMD_DEVICE_INFO, {}, timeout=1.0)
        assert response.command == CMD_DEVICE_INFO
        assert session.take_notifications() == []

        transport.push(encode_frame(CMD_BATTERY_NOTIFY, {1: b"\x64"}))
        deadline = time.monotonic() + 1.0
        while session.last_sequence < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        pending = session.take_notifications()
        assert len(pending) == 1
        assert pending[0].command == CMD_BATTERY_NOTIFY
        assert session.take_notifications() == []
    finally:
        session.close()


def test_session_waits_for_notification_without_consuming_it() -> None:
    transport = FakeTransport(lambda request: [])
    session = HuaweiSession(transport, response_timeout=1.0)
    try:
        session.open()
        transport.push(encode_frame(CMD_BATTERY_NOTIFY, {1: b"\x64"}))
        assert session.wait_for_notifications(1.0) is True
        pending = session.take_notifications()
        assert len(pending) == 1
        assert pending[0].command == CMD_BATTERY_NOTIFY
        assert session.wait_for_notifications(0.02) is False
    finally:
        session.close()


def test_session_wait_for_notification_honors_stop_predicate() -> None:
    transport = FakeTransport(lambda request: [])
    session = HuaweiSession(transport, response_timeout=1.0)
    try:
        session.open()
        started = time.monotonic()
        assert session.wait_for_notifications(
            1.0, should_stop=lambda: True
        ) is False
        assert time.monotonic() - started < 0.5
    finally:
        session.close()


def test_session_on_frame_callback_and_callback_error() -> None:
    received = []

    def callback(frame):
        received.append(frame)
        raise RuntimeError("callback falhou")

    transport = FakeTransport(lambda request: [])
    session = HuaweiSession(transport, on_frame=callback, response_timeout=1.0)
    try:
        session.open()
        transport.push(encode_frame(CMD_BATTERY_NOTIFY, {1: b"\x32"}))
        deadline = time.monotonic() + 1.0
        while not received and time.monotonic() < deadline:
            time.sleep(0.01)
        assert received
        assert session.callback_errors
    finally:
        session.close()


def test_session_discards_bad_crc_and_records_issue() -> None:
    def handler(request):
        raw = bytearray(encode_frame(request.command, {1: b"\x64"}))
        raw[-1] ^= 0xFF
        return [bytes(raw)]

    transport = FakeTransport(handler)
    session = HuaweiSession(transport, response_timeout=0.2)
    try:
        session.open()
        with pytest.raises(RequestTimeout):
            session.request(CMD_DEVICE_INFO, {}, timeout=0.1)
        assert session.parse_issues
        assert any("CRC" in issue.message for issue in session.parse_issues)
    finally:
        session.close()


def test_session_rejects_request_before_open() -> None:
    session = HuaweiSession(FakeTransport(lambda request: []))
    with pytest.raises(SessionClosedError):
        session.request(CMD_DEVICE_INFO, {})
