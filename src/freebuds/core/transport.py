"""Transporte RFCOMM/SPP sobre a API de sockets do Windows.

Os FreeBuds usam Bluetooth clássico com o UUID SPP padrão
``00001101-0000-1000-8000-00805F9B34FB``. O Windows não expõe o UUID na API de
socket: conectamos diretamente ao canal RFCOMM descoberto para cada modelo.
"""

from __future__ import annotations

import socket
import sys
from typing import Self

from .errors import TransportError
from .util import normalize_address

SPP_SERVICE_UUID = "00001101-0000-1000-8000-00805F9B34FB"
KNOWN_CHANNELS: tuple[int, ...] = (1, 16)
_WINDOWS_ERROR_HINTS = {
    10013: (
        "acesso negado pelo Windows; verifique permissões Bluetooth, outro app "
        "usando o canal SPP ou uma política do sistema"
    ),
    10048: "endereço/canal já está em uso",
    10049: "endereço Bluetooth indisponível",
    10050: (
        "sem conexão Bluetooth; confirme que os fones estão ligados, fora do "
        "estojo, no alcance e que o Bluetooth do PC está ativado"
    ),
    10051: "rede Bluetooth inacessível",
    10060: "tempo esgotado ao conectar; os fones podem estar desligados ou fora de alcance",
    10061: (
        "conexão recusada; o canal RFCOMM provavelmente não é o SPP correto ou os "
        "fones não aceitam conexão neste momento"
    ),
}


def supported() -> bool:
    return hasattr(socket, "AF_BLUETOOTH") and hasattr(socket, "BTPROTO_RFCOMM")


def _windows_error(exc: OSError) -> int | None:
    winerror = getattr(exc, "winerror", None)
    if isinstance(winerror, int):
        return winerror
    if exc.errno in _WINDOWS_ERROR_HINTS:
        return exc.errno
    return None


def describe_socket_error(exc: OSError, *, address: str, channel: int) -> str:
    code = _windows_error(exc)
    detail = _WINDOWS_ERROR_HINTS.get(code) if code is not None else None
    if detail is None:
        detail = exc.strerror or str(exc)
    code_text = f" (WinError {code})" if code is not None and sys.platform == "win32" else ""
    return f"falha ao conectar em {address}, canal RFCOMM {channel}: {detail}{code_text}"


class RfcommTransport:
    """Socket RFCOMM com abertura tardia e fechamento idempotente."""

    def __init__(
        self,
        address: str,
        channel: int,
        *,
        connect_timeout: float = 5.0,
        recv_size: int = 4096,
    ) -> None:
        self.address = normalize_address(address)
        if not 1 <= channel <= 30:
            raise ValueError("O canal RFCOMM deve estar entre 1 e 30")
        if connect_timeout <= 0:
            raise ValueError("connect_timeout deve ser positivo")
        self.channel = channel
        self.connect_timeout = connect_timeout
        self.recv_size = recv_size
        self._socket: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        if self._socket is not None:
            return
        if not supported():
            raise TransportError(
                "Esta versão do Python/sistema não expõe sockets Bluetooth RFCOMM. "
                "Use Windows com Python 3.11+ e um adaptador Bluetooth clássico."
            )

        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        # No Linux/BlueZ, um bind local é necessário antes do connect. No
        # Windows a função connect cuida disso; mantemos o caminho somente para
        # não transformar o módulo em algo exclusivo de uma plataforma.
        if sys.platform.startswith("linux") and hasattr(socket, "BDADDR_ANY"):
            try:
                sock.bind((socket.BDADDR_ANY, 0))
            except OSError:
                pass

        sock.settimeout(self.connect_timeout)
        try:
            sock.connect((self.address, self.channel))
        except OSError as exc:
            try:
                sock.close()
            finally:
                raise TransportError(
                    describe_socket_error(exc, address=self.address, channel=self.channel)
                ) from exc

        self._socket = sock

    def settimeout(self, timeout: float | None) -> None:
        sock = self._require_socket()
        sock.settimeout(timeout)

    def sendall(self, data: bytes) -> None:
        sock = self._require_socket()
        try:
            sock.sendall(data)
        except OSError as exc:
            raise TransportError(
                f"falha ao enviar dados para {self.address}: {exc}"
            ) from exc

    def recv(self, size: int | None = None) -> bytes:
        sock = self._require_socket()
        try:
            return sock.recv(size or self.recv_size)
        except TimeoutError:
            raise
        except OSError as exc:
            raise TransportError(
                f"conexão com {self.address} caiu durante a leitura: {exc}"
            ) from exc

    def close(self) -> None:
        sock, self._socket = self._socket, None
        if sock is None:
            return
        try:
            sock.close()
        except OSError:
            pass

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise TransportError("Socket RFCOMM não conectado")
        return self._socket

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
