"""Erros públicos do núcleo do FreeBuds Client."""

from __future__ import annotations


class FreeBudsError(Exception):
    """Erro base do projeto."""


class ProtocolError(FreeBudsError):
    """Quadro, TLV ou CRC inválido."""


class ChecksumError(ProtocolError):
    """CRC16/XMODEM do quadro não confere."""


class TransportError(FreeBudsError):
    """Falha de baixo nível no socket RFCOMM/SPP."""


class BluetoothError(FreeBudsError):
    """Falha nas APIs Bluetooth do Windows."""


class BluetoothRadioUnavailableError(BluetoothError):
    """Nenhum rádio Bluetooth clássico utilizável foi encontrado."""


class SessionError(FreeBudsError):
    """Falha na sessão de comandos."""


class SessionClosedError(SessionError):
    """A sessão ou o transporte foi encerrado."""


class RequestTimeout(SessionError):
    """O dispositivo não respondeu dentro do prazo."""
