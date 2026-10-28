"""Codec do protocolo Huawei SPP.

Formato de um quadro::

    5A LL LL 00 CC CC [TT LL VV...] CRC CRC

* ``LL`` = quantidade de bytes do corpo (comando + TLVs) + 1.
* ``CC CC`` = comando de dois bytes.
* ``TT`` = tipo do parâmetro, ``LL`` = tamanho do valor, ``VV`` = valor.
* O tamanho total é ``LL + 5``.
* CRC16/XMODEM (polinômio 0x1021, valor inicial 0), big-endian.

O parser é incremental e tolera dados fragmentados, quadros concatenados e
lixo antes/sincronização perdida. Nenhum código deste módulo depende de
Windows, Qt ou de um dispositivo conectado.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from .errors import ChecksumError, ProtocolError

MAGIC = 0x5A
HEADER_SIZE = 4
CRC_SIZE = 2
MIN_FRAME_SIZE = 8
MAX_FRAME_SIZE = 8192

ParameterInput = Mapping[int, bytes | bytearray | memoryview | int] | Iterable[
    tuple[int, bytes | bytearray | memoryview | int]
]


def crc16_xmodem(data: bytes | bytearray | memoryview) -> int:
    """Calcula CRC16/XMODEM: polinômio 0x1021, inicial 0, sem reflexão."""

    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def crc16_bytes(data: bytes | bytearray | memoryview) -> bytes:
    return crc16_xmodem(data).to_bytes(2, "big")


def command_bytes(command: bytes | bytearray | memoryview | int | str) -> bytes:
    """Normaliza um comando para exatamente dois bytes."""

    if isinstance(command, int):
        if not 0 <= command <= 0xFFFF:
            raise ValueError("O comando deve caber em 16 bits")
        return command.to_bytes(2, "big")
    if isinstance(command, str):
        text = command.replace(" ", "").replace("0x", "").replace("0X", "")
        try:
            raw = bytes.fromhex(text)
        except ValueError as exc:
            raise ValueError(f"Comando hexadecimal inválido: {command!r}") from exc
        if len(raw) != 2:
            raise ValueError("O comando deve ter exatamente dois bytes")
        return raw
    raw = bytes(command)
    if len(raw) != 2:
        raise ValueError("O comando deve ter exatamente dois bytes")
    return raw


def _coerce_parameter_value(key: int, value: object) -> bytes:
    if isinstance(value, int) and not isinstance(value, bool):
        if not 0 <= value <= 0xFF:
            raise ValueError(f"Parâmetro {key}: inteiro fora do intervalo de 1 byte")
        return value.to_bytes(1, "big")
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
    else:
        raise TypeError(
            f"Parâmetro {key}: esperado bytes, bytearray, memoryview ou int de 0..255"
        )
    if len(raw) > 0xFF:
        raise ValueError(f"Parâmetro {key}: valor maior que 255 bytes")
    return raw


def normalize_parameters(parameters: ParameterInput | None) -> dict[int, bytes]:
    """Valida e normaliza parâmetros TLV, preservando a ordem de inserção."""

    if parameters is None:
        return {}
    items = parameters.items() if isinstance(parameters, Mapping) else parameters
    result: dict[int, bytes] = {}
    for key, value in items:
        if not isinstance(key, int) or isinstance(key, bool) or not 0 <= key <= 0xFF:
            raise ValueError(f"Tipo de parâmetro inválido: {key!r}")
        if key in result:
            raise ValueError(f"Parâmetro TLV duplicado: {key}")
        result[key] = _coerce_parameter_value(key, value)
    return result


def encode_frame(
    command: bytes | bytearray | memoryview | int | str,
    parameters: ParameterInput | None = None,
) -> bytes:
    """Monta um quadro completo, com CRC, pronto para ``sendall``."""

    cmd = command_bytes(command)
    params = normalize_parameters(parameters)

    body = bytearray(cmd)
    for key, value in params.items():
        body.append(key)
        body.append(len(value))
        body.extend(value)

    length = len(body) + 1
    if length > 0xFFFF:
        raise ValueError("Quadro grande demais para o campo de tamanho")

    result = bytearray((MAGIC,))
    result.extend(length.to_bytes(2, "big"))
    result.append(0)
    result.extend(body)
    result.extend(crc16_xmodem(result).to_bytes(2, "big"))
    return bytes(result)


def decode_parameters(payload: bytes) -> dict[int, bytes]:
    """Decodifica a região TLV (sem comando e sem CRC)."""

    parameters: dict[int, bytes] = {}
    position = 0
    while position < len(payload):
        if position + 2 > len(payload):
            raise ProtocolError(
                f"TLV truncado no offset {position}: faltam tipo/tamanho"
            )
        key = payload[position]
        length = payload[position + 1]
        end = position + 2 + length
        if end > len(payload):
            raise ProtocolError(
                f"TLV {key:#04x} truncado: declara {length} byte(s), "
                f"restam {len(payload) - position - 2}"
            )
        if key in parameters:
            raise ProtocolError(f"Parâmetro TLV duplicado: {key:#04x}")
        parameters[key] = payload[position + 2 : end]
        position = end
    return parameters


@dataclass(slots=True)
class HuaweiFrame:
    """Um quadro Huawei já decodificado."""

    command: bytes
    parameters: dict[int, bytes] = field(default_factory=dict)
    raw: bytes = b""
    checksum_valid: bool = True

    @property
    def command_int(self) -> int:
        return int.from_bytes(self.command, "big")

    @property
    def command_hex(self) -> str:
        return self.command.hex(" ").upper()

    def parameter(self, key: int, default: bytes = b"") -> bytes:
        return self.parameters.get(key, default)

    def to_bytes(self) -> bytes:
        return encode_frame(self.command, self.parameters)

    def __str__(self) -> str:
        params = ", ".join(
            f"{key:#04x}={value.hex(' ')}"
            for key, value in sorted(self.parameters.items())
        )
        suffix = "" if self.checksum_valid else " [CRC INVÁLIDO]"
        return f"{self.command.hex(' ').upper()}{suffix}" + (
            f" | {params}" if params else ""
        )


def parse_frame(
    data: bytes | bytearray | memoryview,
    *,
    validate_checksum: bool = True,
    max_frame_size: int = MAX_FRAME_SIZE,
) -> HuaweiFrame:
    """Decodifica exatamente um quadro.

    Com ``validate_checksum=False`` quadros com CRC errado são retornados com
    ``checksum_valid=False``; isso é útil para analisar capturas.
    """

    raw = bytes(data)
    if len(raw) < MIN_FRAME_SIZE:
        raise ProtocolError(f"Quadro curto demais: {len(raw)} byte(s)")
    if raw[0] != MAGIC:
        raise ProtocolError(f"Magic inválido: {raw[0]:#04x} (esperado 0x5A)")
    if raw[3] != 0:
        raise ProtocolError(f"Byte reservado inválido no offset 3: {raw[3]:#04x}")

    declared_length = int.from_bytes(raw[1:3], "big")
    if declared_length < 3:
        raise ProtocolError(f"Tamanho declarado inválido: {declared_length}")
    total = declared_length + 5
    if total > max_frame_size:
        raise ProtocolError(
            f"Quadro de {total} byte(s) excede o limite de {max_frame_size}"
        )
    if len(raw) != total:
        raise ProtocolError(
            f"Tamanho inconsistente: campo declara {total} byte(s), "
            f"recebidos {len(raw)}"
        )

    command = raw[4:6]
    body_end = declared_length + 3  # início do CRC
    payload = raw[6:body_end]
    parameters = decode_parameters(payload)

    expected_crc = int.from_bytes(raw[body_end : body_end + 2], "big")
    actual_crc = crc16_xmodem(raw[:body_end])
    checksum_valid = expected_crc == actual_crc
    if validate_checksum and not checksum_valid:
        raise ChecksumError(
            f"CRC inválido: recebido {expected_crc:04X}, calculado {actual_crc:04X}"
        )

    return HuaweiFrame(
        command=command,
        parameters=parameters,
        raw=raw,
        checksum_valid=checksum_valid,
    )


@dataclass(slots=True)
class FrameIssue:
    """Problema encontrado durante a ressincronização/parse de um fluxo."""

    offset: int
    message: str
    data: bytes = b""


class FrameParser:
    """Parser incremental de um fluxo SPP.

    Alimente ``feed()`` com qualquer quantidade de bytes. Ele mantém o restante
    em ``pending`` até completar um quadro.
    """

    def __init__(
        self,
        *,
        validate_checksum: bool = True,
        max_frame_size: int = MAX_FRAME_SIZE,
        max_issues: int = 100,
    ) -> None:
        self.validate_checksum = validate_checksum
        self.max_frame_size = max_frame_size
        self._buffer = bytearray()
        self._consumed = 0
        self._issues: deque[FrameIssue] = deque(maxlen=max_issues)

    @property
    def pending(self) -> bytes:
        return bytes(self._buffer)

    @property
    def issues(self) -> list[FrameIssue]:
        return list(self._issues)

    @property
    def bytes_consumed(self) -> int:
        return self._consumed

    def _issue(self, message: str, data: bytes = b"") -> None:
        self._issues.append(FrameIssue(self._consumed, message, data))

    def feed(self, data: bytes | bytearray | memoryview) -> list[HuaweiFrame]:
        self._buffer.extend(data)
        frames: list[HuaweiFrame] = []

        while self._buffer:
            if self._buffer[0] != MAGIC:
                magic_at = self._buffer.find(MAGIC, 1)
                if magic_at < 0:
                    garbage = bytes(self._buffer)
                    self._issue(
                        f"{len(garbage)} byte(s) descartado(s) sem magic 0x5A",
                        garbage,
                    )
                    self._consumed += len(garbage)
                    self._buffer.clear()
                    break
                garbage = bytes(self._buffer[:magic_at])
                self._issue(f"{magic_at} byte(s) descartado(s) antes do magic", garbage)
                del self._buffer[:magic_at]
                self._consumed += magic_at
                continue

            if len(self._buffer) < HEADER_SIZE:
                break

            declared_length = int.from_bytes(self._buffer[1:3], "big")
            total = declared_length + 5
            if declared_length < 3 or total > self.max_frame_size:
                self._issue(
                    f"tamanho declarado inválido ({declared_length}); "
                    "descartando um byte para ressincronizar",
                    bytes(self._buffer[:1]),
                )
                del self._buffer[0]
                self._consumed += 1
                continue

            if len(self._buffer) < total:
                break

            raw = bytes(self._buffer[:total])
            try:
                frame = parse_frame(
                    raw,
                    validate_checksum=self.validate_checksum,
                    max_frame_size=self.max_frame_size,
                )
            except ChecksumError as exc:
                self._issue(str(exc), raw)
                del self._buffer[:total]
                self._consumed += total
                continue
            except ProtocolError as exc:
                self._issue(str(exc), raw)
                del self._buffer[0]
                self._consumed += 1
                continue

            frames.append(frame)
            del self._buffer[:total]
            self._consumed += total

        return frames

    def reset(self) -> None:
        self._buffer.clear()
        self._issues.clear()
        self._consumed = 0


def decode_stream(
    data: bytes | bytearray | memoryview,
    *,
    validate_checksum: bool = False,
    max_frame_size: int = MAX_FRAME_SIZE,
) -> tuple[list[HuaweiFrame], bytes, list[FrameIssue]]:
    """Atalho para decodificar um bloco inteiro e devolver sobras/problemas."""

    parser = FrameParser(
        validate_checksum=validate_checksum, max_frame_size=max_frame_size
    )
    frames = parser.feed(data)
    return frames, parser.pending, parser.issues
