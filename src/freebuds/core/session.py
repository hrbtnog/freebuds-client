"""Sessão SPP com leitura em thread e correlação de respostas.

A thread de leitura mantém o socket sempre drenado, evitando que notificações
atrasem ou se misturem com respostas. Requisições são serializadas e aguardam o
eco do mesmo comando (ou comandos alternativos explicitamente aceitos, como a
notificação de bateria ``0x0127``).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from .errors import (
    RequestTimeout,
    SessionClosedError,
    SessionError,
    TransportError,
)
from .protocol import (
    FrameIssue,
    FrameParser,
    HuaweiFrame,
    encode_frame,
    normalize_parameters,
    parse_frame,
)
from .transport import RfcommTransport


@dataclass(slots=True)
class _Waiter:
    expected: frozenset[bytes]
    start_sequence: int
    frame: HuaweiFrame | None = None
    response_sequence: int | None = None


@dataclass(slots=True)
class _TimedFrame:
    sequence: int
    received_at: float
    frame: HuaweiFrame


class HuaweiSession:
    """Sessão de comandos sobre um ``RfcommTransport``."""

    def __init__(
        self,
        transport: RfcommTransport,
        *,
        response_timeout: float = 2.0,
        reader_timeout: float = 0.4,
        on_frame: object | None = None,
    ) -> None:
        if response_timeout <= 0:
            raise ValueError("response_timeout deve ser positivo")
        if reader_timeout <= 0:
            raise ValueError("reader_timeout deve ser positivo")
        self.transport = transport
        self.response_timeout = response_timeout
        self.reader_timeout = reader_timeout
        self._on_frame = on_frame

        self._condition = threading.Condition()
        self._write_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self._history: deque[_TimedFrame] = deque(maxlen=1024)
        self._notifications: deque[_TimedFrame] = deque(maxlen=256)
        self._waiters: list[_Waiter] = []
        self._sequence = 0
        self._error: BaseException | None = None
        self._closed = True
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._parser: FrameParser | None = None
        self._last_request: HuaweiFrame | None = None
        self._last_response_sequence: int | None = None
        self._callback_errors: deque[BaseException] = deque(maxlen=16)

    @property
    def is_open(self) -> bool:
        with self._condition:
            return not self._closed and self._thread is not None and self._thread.is_alive()

    @property
    def error(self) -> BaseException | None:
        with self._condition:
            return self._error

    @property
    def last_sequence(self) -> int:
        with self._condition:
            return self._sequence

    @property
    def last_request(self) -> HuaweiFrame | None:
        with self._condition:
            return self._last_request

    @property
    def last_response_sequence(self) -> int | None:
        """Sequência do último quadro que satisfez uma requisição."""

        with self._condition:
            return self._last_response_sequence

    @property
    def parse_issues(self) -> list[FrameIssue]:
        with self._condition:
            return list(self._parser.issues) if self._parser else []

    @property
    def callback_errors(self) -> list[BaseException]:
        with self._condition:
            return list(self._callback_errors)

    @property
    def received_frames(self) -> list[HuaweiFrame]:
        with self._condition:
            return [item.frame for item in self._history]

    def open(self) -> HuaweiSession:
        """Conecta o transporte e inicia a thread de leitura."""

        with self._condition:
            if self._thread is not None and self._thread.is_alive():
                return self
            self._closed = True
            self._error = None
            self._stop.clear()
            self._history.clear()
            self._notifications.clear()
            self._waiters.clear()
            self._sequence = 0
            self._last_request = None
            self._last_response_sequence = None
            self._parser = FrameParser(validate_checksum=True)

        self.transport.connect()
        self.transport.settimeout(self.reader_timeout)

        with self._condition:
            self._closed = False
            self._thread = threading.Thread(
                target=self._reader_loop,
                name=f"freebuds-rfcomm-{self.transport.address}",
                daemon=True,
            )
            self._thread.start()
        return self

    # Nomes alternativos para quem preferir a semântica de conexão.
    connect = open

    def close(self) -> None:
        with self._condition:
            self._stop.set()
            self._closed = True
            self._condition.notify_all()

        self.transport.close()

        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

        with self._condition:
            self._thread = None
            self._condition.notify_all()

    def request(
        self,
        command: bytes | int | str,
        parameters: object = None,
        *,
        expected: object = None,
        timeout: float | None = None,
    ) -> HuaweiFrame:
        """Envia um comando e espera pela primeira resposta compatível."""

        params = normalize_parameters(parameters)  # type: ignore[arg-type]
        payload = encode_frame(command, params)
        return self.request_bytes(payload, expected=expected, timeout=timeout)

    def request_bytes(
        self,
        payload: bytes,
        *,
        expected: object = None,
        timeout: float | None = None,
    ) -> HuaweiFrame:
        request_frame = parse_frame(payload, validate_checksum=False)
        return self.request_frame(
            request_frame, expected=expected, timeout=timeout
        )

    def request_frame(
        self,
        request: HuaweiFrame,
        *,
        expected: object = None,
        timeout: float | None = None,
    ) -> HuaweiFrame:
        """Envia um ``HuaweiFrame`` já montado e aguarda a resposta.

        ``expected`` pode ser um comando isolado ou uma lista de comandos
        aceitos como resposta. Por padrão, exige o eco do mesmo comando.
        """

        timeout_value = self.response_timeout if timeout is None else timeout
        if timeout_value <= 0:
            raise ValueError("timeout deve ser positivo")

        expected_commands = self._normalize_expected(expected, request.command)
        with self._request_lock:
            with self._condition:
                self._ensure_usable()
                waiter = _Waiter(
                    expected=frozenset(expected_commands),
                    start_sequence=self._sequence,
                )
                self._waiters.append(waiter)
                self._last_request = request

            try:
                with self._write_lock:
                    self.transport.sendall(request.raw or request.to_bytes())
            except BaseException:
                with self._condition:
                    if waiter in self._waiters:
                        self._waiters.remove(waiter)
                raise

            deadline = time.monotonic() + timeout_value
            try:
                with self._condition:
                    while waiter.frame is None:
                        if self._error is not None:
                            raise SessionClosedError(str(self._error)) from self._error
                        if self._closed:
                            raise SessionClosedError("Sessão RFCOMM encerrada")
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            names = ", ".join(
                                command.hex(" ").upper() for command in expected_commands
                            )
                            raise RequestTimeout(
                                f"sem resposta para {request.command.hex(' ').upper()} "
                                f"(aguardando {names}) em {timeout_value:.1f}s"
                            )
                        self._condition.wait(remaining)
                    self._last_response_sequence = waiter.response_sequence
                    return waiter.frame
            finally:
                with self._condition:
                    if waiter in self._waiters:
                        self._waiters.remove(waiter)

    def send_bytes(self, payload: bytes) -> None:
        """Envia um comando sem aguardar resposta (notificações virão na thread)."""

        with self._condition:
            self._ensure_usable()
        with self._write_lock:
            self.transport.sendall(payload)

    def frames_since(self, sequence: int) -> list[HuaweiFrame]:
        """Quadros recebidos depois de uma sequência, em ordem."""

        with self._condition:
            return [item.frame for item in self._history if item.sequence > sequence]

    def take_notification_frames(self) -> list[tuple[int, HuaweiFrame]]:
        """Devolve notificações com a sequência de recebimento e limpa a fila."""

        with self._condition:
            items = [
                (item.sequence, item.frame) for item in self._notifications
            ]
            self._notifications.clear()
            return items

    def take_notifications(self) -> list[HuaweiFrame]:
        """Devolve e limpa apenas os quadros espontâneos ainda não consumidos.

        Respostas correlacionadas com uma requisição não entram nesta fila; assim
        a UI consegue distinguir notificações reais de ecos de comandos.
        """

        return [frame for _, frame in self.take_notification_frames()]

    def wait_for_notifications(
        self,
        timeout: float,
        *,
        should_stop: Callable[[], bool] | None = None,
    ) -> bool:
        """Espera até chegar uma notificação espontânea ou o tempo acabar.

        A fila não é consumida; o chamador deve usar
        :meth:`take_notification_frames` depois. O retorno é ``True`` quando há
        pelo menos um quadro pendente, o que permite à UI reagir imediatamente a
        mudanças feitas por outro dispositivo (por exemplo, o celular).
        """

        if timeout <= 0:
            return bool(self._notifications)
        deadline = time.monotonic() + timeout
        with self._condition:
            while not self._closed and self._error is None:
                if self._notifications:
                    return True
                if callable(should_stop) and should_stop():
                    return False
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                # Acorda periodicamente para que o encerramento da thread não
                # fique preso em uma espera longa.
                self._condition.wait(min(remaining, 0.25))
            return bool(self._notifications)

    def wait_for_frames(self, seconds: float) -> list[HuaweiFrame]:
        """Espera ``seconds`` e devolve os quadros recebidos nesse intervalo."""

        if seconds <= 0:
            return []
        marker = self.last_sequence
        deadline = time.monotonic() + seconds
        with self._condition:
            while not self._closed and self._error is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
        return self.frames_since(marker)

    def _normalize_expected(
        self, expected: object, default: bytes
    ) -> tuple[bytes, ...]:
        if expected is None:
            return (default,)
        if isinstance(expected, (bytes, bytearray, memoryview, int, str)):
            items = [expected]
        else:
            items = list(expected)  # type: ignore[arg-type]
        if not items:
            raise ValueError("expected não pode ser vazio")
        commands: list[bytes] = []
        for item in items:
            if isinstance(item, int):
                if not 0 <= item <= 0xFFFF:
                    raise ValueError(f"Comando esperado inválido: {item}")
                commands.append(item.to_bytes(2, "big"))
            elif isinstance(item, str):
                raw = bytes.fromhex(item.replace(" ", "").replace("0x", ""))
                if len(raw) != 2:
                    raise ValueError(f"Comando esperado inválido: {item!r}")
                commands.append(raw)
            else:
                raw = bytes(item)  # type: ignore[arg-type]
                if len(raw) != 2:
                    raise ValueError("Cada comando esperado deve ter 2 bytes")
                commands.append(raw)
        return tuple(commands)

    def _ensure_usable(self) -> None:
        if self._closed or self._thread is None:
            raise SessionClosedError("Sessão RFCOMM não iniciada")
        if self._error is not None:
            raise SessionClosedError(str(self._error)) from self._error

    def _reader_loop(self) -> None:
        transport = self.transport
        try:
            while not self._stop.is_set():
                try:
                    chunk = transport.recv()
                except TimeoutError:
                    continue
                except TransportError as exc:
                    if not self._stop.is_set():
                        self._fail(exc)
                    break

                if not chunk:
                    if not self._stop.is_set():
                        self._fail(SessionClosedError("o dispositivo encerrou a conexão SPP"))
                    break

                parser = self._parser
                if parser is None:
                    break
                try:
                    frames = parser.feed(chunk)
                except Exception as exc:  # noqa: BLE001 - proteção da thread
                    self._fail(SessionError(f"falha inesperada no parser: {exc}"))
                    break

                for frame in frames:
                    with self._condition:
                        self._sequence += 1
                        sequence = self._sequence
                        timed_frame = _TimedFrame(sequence, time.monotonic(), frame)
                        self._history.append(timed_frame)
                        matched = False
                        for waiter in self._waiters:
                            if (
                                waiter.frame is None
                                and frame.command in waiter.expected
                                and sequence > waiter.start_sequence
                            ):
                                waiter.frame = frame
                                waiter.response_sequence = sequence
                                matched = True
                                break
                        if not matched:
                            self._notifications.append(timed_frame)
                        self._condition.notify_all()

                    callback = self._on_frame
                    if callback is not None:
                        try:
                            callback(frame)  # type: ignore[operator]
                        except Exception as exc:  # noqa: BLE001 - callback não derruba o leitor
                            with self._condition:
                                self._callback_errors.append(exc)
        except Exception as exc:  # noqa: BLE001 - limite da thread de leitura
            if not self._stop.is_set():
                self._fail(SessionError(f"thread de leitura falhou: {exc}"))
        finally:
            with self._condition:
                if not self._stop.is_set():
                    self._closed = True
                self._condition.notify_all()

    def _fail(self, error: BaseException) -> None:
        with self._condition:
            if self._error is None:
                self._error = error
            self._closed = True
            self._condition.notify_all()
        self.transport.close()

    def __enter__(self) -> Self:
        return self.open()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
