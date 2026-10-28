"""Integração com a API Bluetooth clássico do Windows via ``ctypes``.

Não depende de ``pywin32`` nem de ``winrt``. A enumeração usa
``BluetoothFindFirstDevice``/``BluetoothFindNextDevice`` e o pareamento usa o
assistente/SSP do Windows por meio de ``BluetoothAuthenticateDeviceEx``.
"""

from __future__ import annotations

import ctypes
import math
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from .errors import BluetoothError, BluetoothRadioUnavailableError
from .models import BluetoothDevice
from .util import is_huawei_device_name, normalize_address, systemtime_to_datetime

ERROR_SUCCESS = 0
ERROR_INVALID_PARAMETER = 87
ERROR_INVALID_HANDLE = 6
ERROR_NO_MORE_ITEMS = 259
ERROR_CANCELLED = 1223
ERROR_REVISION_MISMATCH = 13
MITM_PROTECTION_NOT_REQUIRED = 0
MAX_INQUIRY_SECONDS = 48 * 1.28

if sys.platform == "win32":
    from ctypes import wintypes

    class SYSTEMTIME(ctypes.Structure):
        _fields_ = [
            ("wYear", wintypes.WORD),
            ("wMonth", wintypes.WORD),
            ("wDayOfWeek", wintypes.WORD),
            ("wDay", wintypes.WORD),
            ("wHour", wintypes.WORD),
            ("wMinute", wintypes.WORD),
            ("wSecond", wintypes.WORD),
            ("wMilliseconds", wintypes.WORD),
        ]

    class BLUETOOTH_ADDRESS(ctypes.Union):
        _fields_ = [
            ("ullLong", ctypes.c_ulonglong),
            ("rgBytes", ctypes.c_ubyte * 6),
        ]

    class BLUETOOTH_DEVICE_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("Address", BLUETOOTH_ADDRESS),
            ("ulClassofDevice", wintypes.ULONG),
            ("fConnected", wintypes.BOOL),
            ("fRemembered", wintypes.BOOL),
            ("fAuthenticated", wintypes.BOOL),
            ("stLastSeen", SYSTEMTIME),
            ("stLastUsed", SYSTEMTIME),
            ("szName", wintypes.WCHAR * 248),
        ]

    class BLUETOOTH_DEVICE_SEARCH_PARAMS(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("fReturnAuthenticated", wintypes.BOOL),
            ("fReturnRemembered", wintypes.BOOL),
            ("fReturnUnknown", wintypes.BOOL),
            ("fReturnConnected", wintypes.BOOL),
            ("fIssueInquiry", wintypes.BOOL),
            ("cTimeoutMultiplier", ctypes.c_ubyte),
            ("hRadio", wintypes.HANDLE),
        ]

    class BLUETOOTH_FIND_RADIO_PARAMS(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD)]

    _EXPECTED_SIZES = {
        "BLUETOOTH_DEVICE_INFO": (BLUETOOTH_DEVICE_INFO, 560),
        "BLUETOOTH_DEVICE_SEARCH_PARAMS": (
            BLUETOOTH_DEVICE_SEARCH_PARAMS,
            40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 32,
        ),
        "BLUETOOTH_FIND_RADIO_PARAMS": (BLUETOOTH_FIND_RADIO_PARAMS, 4),
    }
    for _name, (_structure, _size) in _EXPECTED_SIZES.items():
        if ctypes.sizeof(_structure) != _size:
            raise RuntimeError(
                f"{_name} tem {ctypes.sizeof(_structure)} bytes; esperado {_size}. "
                "Estruturas ctypes incompatíveis com esta plataforma."
            )


class _BluetoothApi:
    """Carrega e tipa as funções usadas, uma única vez."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise BluetoothError(
                "A descoberta/pareamento nativos deste módulo exigem Windows 10/11"
            )
        # bthprops.cpl (o mesmo painel de Bluetooth do Windows) exporta tanto a
        # enumeração quanto BluetoothAuthenticateDeviceEx. BluetoothAPIs.dll
        # não exporta a função de autenticação em todas as versões.
        try:
            self.lib = ctypes.WinDLL("bthprops.cpl", use_last_error=True)
        except OSError as exc:
            raise BluetoothError(
                f"não foi possível carregar bthprops.cpl: {exc}"
            ) from exc

        self.find_first_radio = self.lib.BluetoothFindFirstRadio
        self.find_first_radio.argtypes = [
            ctypes.POINTER(BLUETOOTH_FIND_RADIO_PARAMS),
            ctypes.POINTER(wintypes.HANDLE),
        ]
        self.find_first_radio.restype = wintypes.HANDLE

        self.find_next_radio = self.lib.BluetoothFindNextRadio
        self.find_next_radio.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        self.find_next_radio.restype = wintypes.BOOL

        self.find_radio_close = self.lib.BluetoothFindRadioClose
        self.find_radio_close.argtypes = [wintypes.HANDLE]
        self.find_radio_close.restype = wintypes.BOOL

        self.find_first_device = self.lib.BluetoothFindFirstDevice
        self.find_first_device.argtypes = [
            ctypes.POINTER(BLUETOOTH_DEVICE_SEARCH_PARAMS),
            ctypes.POINTER(BLUETOOTH_DEVICE_INFO),
        ]
        self.find_first_device.restype = wintypes.HANDLE

        self.find_next_device = self.lib.BluetoothFindNextDevice
        self.find_next_device.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(BLUETOOTH_DEVICE_INFO),
        ]
        self.find_next_device.restype = wintypes.BOOL

        self.find_device_close = self.lib.BluetoothFindDeviceClose
        self.find_device_close.argtypes = [wintypes.HANDLE]
        self.find_device_close.restype = wintypes.BOOL

        self.authenticate_device_ex = self.lib.BluetoothAuthenticateDeviceEx
        self.authenticate_device_ex.argtypes = [
            wintypes.HWND,
            wintypes.HANDLE,
            ctypes.POINTER(BLUETOOTH_DEVICE_INFO),
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        self.authenticate_device_ex.restype = wintypes.DWORD

        self.kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
        self.close_handle = self.kernel32.CloseHandle
        self.close_handle.argtypes = [wintypes.HANDLE]
        self.close_handle.restype = wintypes.BOOL


_api_instance: _BluetoothApi | None = None


def _api() -> _BluetoothApi:
    global _api_instance
    if _api_instance is None:
        _api_instance = _BluetoothApi()
    return _api_instance


def supported() -> bool:
    return sys.platform == "win32"


def _format_winerror(code: int) -> str:
    try:
        text = ctypes.FormatError(code).strip()
    except (OSError, ValueError):
        text = ""
    return f"{text} (WinError {code})" if text else f"WinError {code}"


def address_to_ullong(address: str) -> int:
    return int(normalize_address(address).replace(":", ""), 16)


def address_from_bluetooth_address(address: object) -> str:
    """Converte ``BLUETOOTH_ADDRESS`` para texto legível.

    ``rgBytes`` é armazenado em ordem de rede inversa; o primeiro byte exibido
    é ``rgBytes[5]``.
    """

    raw = bytes(address.rgBytes)
    return ":".join(f"{byte:02X}" for byte in reversed(raw))


@dataclass(slots=True)
class PairResult:
    address: str
    name: str | None
    winerror: int
    already_paired: bool = False
    success: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "address": self.address,
            "name": self.name,
            "winerror": self.winerror,
            "already_paired": self.already_paired,
            "success": self.success,
            "message": self.message,
        }


def _find_radios(api: _BluetoothApi) -> list[int]:
    params = BLUETOOTH_FIND_RADIO_PARAMS()
    params.dwSize = ctypes.sizeof(BLUETOOTH_FIND_RADIO_PARAMS)
    handle = wintypes.HANDLE()
    find_handle = api.find_first_radio(ctypes.byref(params), ctypes.byref(handle))
    if not find_handle:
        code = ctypes.get_last_error()
        if code == ERROR_NO_MORE_ITEMS:
            raise BluetoothRadioUnavailableError(
                "nenhum rádio Bluetooth clássico disponível. Ative o Bluetooth do "
                "Windows e confirme que o adaptador está ligado."
            )
        raise BluetoothError(
            f"BluetoothFindFirstRadio falhou: {_format_winerror(code)}"
        )

    radios: list[int] = []
    try:
        while True:
            if handle.value:
                radios.append(int(handle.value))
            next_handle = wintypes.HANDLE()
            if not api.find_next_radio(find_handle, ctypes.byref(next_handle)):
                break
            handle = next_handle
    finally:
        api.find_radio_close(find_handle)

    if not radios:
        raise BluetoothRadioUnavailableError(
            "o Windows não devolveu nenhum rádio Bluetooth clássico utilizável"
        )
    return radios


@contextmanager
def open_radios() -> Iterator[list[int]]:
    """Abre os rádios clássicos e fecha handles ao final."""

    api = _api()
    radios = _find_radios(api)
    try:
        yield radios
    finally:
        for handle in radios:
            api.close_handle(wintypes.HANDLE(handle))


def _search_params(
    radio: int,
    *,
    include_unknown: bool,
    issue_inquiry: bool,
    inquiry_seconds: float,
) -> BLUETOOTH_DEVICE_SEARCH_PARAMS:
    params = BLUETOOTH_DEVICE_SEARCH_PARAMS()
    params.dwSize = ctypes.sizeof(BLUETOOTH_DEVICE_SEARCH_PARAMS)
    params.fReturnAuthenticated = True
    params.fReturnRemembered = True
    # Dispositivos novos descobertos pelo inquiry são "unknown" até serem
    # lembrados; por isso o inquiry sempre pede unknown.
    params.fReturnUnknown = bool(include_unknown or issue_inquiry)
    params.fReturnConnected = True
    params.fIssueInquiry = bool(issue_inquiry)
    if issue_inquiry:
        multiplier = max(1, min(48, math.ceil(inquiry_seconds / 1.28)))
        params.cTimeoutMultiplier = multiplier
    else:
        params.cTimeoutMultiplier = 1
    params.hRadio = wintypes.HANDLE(radio)
    return params


def _device_from_info(info: BLUETOOTH_DEVICE_INFO) -> BluetoothDevice:
    return BluetoothDevice(
        address=address_from_bluetooth_address(info.Address),
        name=str(info.szName or "").strip(),
        connected=bool(info.fConnected),
        remembered=bool(info.fRemembered),
        authenticated=bool(info.fAuthenticated),
        last_seen=systemtime_to_datetime(info.stLastSeen),
        last_used=systemtime_to_datetime(info.stLastUsed),
        class_of_device=int(info.ulClassofDevice),
    )


def enumerate_devices(
    *,
    include_unknown: bool = False,
    issue_inquiry: bool = False,
    inquiry_seconds: float = 8.0,
) -> list[BluetoothDevice]:
    """Lista dispositivos Bluetooth clássicos conhecidos pelo Windows.

    ``issue_inquiry=True`` executa uma nova varredura (mais lenta). Sem inquiry,
    retorna dispositivos lembrados/pareados/conectados, incluindo os que estão
    desligados no momento.
    """

    if inquiry_seconds <= 0:
        raise ValueError("inquiry_seconds deve ser positivo")
    if inquiry_seconds > MAX_INQUIRY_SECONDS:
        raise ValueError(
            f"inquiry_seconds máximo é {MAX_INQUIRY_SECONDS:.2f}s "
            "(cTimeoutMultiplier = 48)"
        )

    api = _api()
    devices: dict[str, BluetoothDevice] = {}
    with open_radios() as radios:
        for radio in radios:
            params = _search_params(
                radio,
                include_unknown=include_unknown,
                issue_inquiry=issue_inquiry,
                inquiry_seconds=inquiry_seconds,
            )
            info = BLUETOOTH_DEVICE_INFO()
            info.dwSize = ctypes.sizeof(BLUETOOTH_DEVICE_INFO)
            find_handle = api.find_first_device(
                ctypes.byref(params), ctypes.byref(info)
            )
            if not find_handle:
                code = ctypes.get_last_error()
                if code == ERROR_NO_MORE_ITEMS:
                    continue
                raise BluetoothError(
                    f"BluetoothFindFirstDevice falhou: {_format_winerror(code)}"
                )

            try:
                while True:
                    device = _device_from_info(info)
                    devices.setdefault(device.address, device)
                    next_info = BLUETOOTH_DEVICE_INFO()
                    next_info.dwSize = ctypes.sizeof(BLUETOOTH_DEVICE_INFO)
                    if not api.find_next_device(find_handle, ctypes.byref(next_info)):
                        break
                    info = next_info
            finally:
                api.find_device_close(find_handle)

    return _sort_devices(devices.values())


def _sort_devices(devices: Iterable[BluetoothDevice]) -> list[BluetoothDevice]:
    return sorted(
        devices,
        key=lambda device: (
            not device.connected,
            not is_huawei_device_name(device.name),
            (device.name or "").casefold(),
            device.address,
        ),
    )


def find_devices(
    target: str,
    *,
    include_unknown: bool = False,
    issue_inquiry: bool = False,
    inquiry_seconds: float = 8.0,
) -> list[BluetoothDevice]:
    """Localiza por endereço ou nome (sem diferenciar maiúsculas de minúsculas)."""

    normalized: str | None
    try:
        normalized = normalize_address(target)
    except ValueError:
        normalized = None

    devices = enumerate_devices(
        include_unknown=include_unknown,
        issue_inquiry=issue_inquiry,
        inquiry_seconds=inquiry_seconds,
    )
    if normalized is not None:
        return [device for device in devices if device.address == normalized]
    needle = target.strip().casefold()
    return [device for device in devices if needle in device.name.casefold()]


def pair_device(address: str, name: str | None = None) -> PairResult:
    """Abre o assistente/SSP do Windows para autenticar um dispositivo."""

    normalized = normalize_address(address)
    api = _api()

    info = BLUETOOTH_DEVICE_INFO()
    info.dwSize = ctypes.sizeof(BLUETOOTH_DEVICE_INFO)
    info.Address.ullLong = address_to_ullong(normalized)
    if name:
        max_name = len(info.szName) - 1
        info.szName = name[:max_name]

    # hRadio NULL faz o Windows tentar todos os rádios. pbtOobData NULL exibe
    # o fluxo de autenticação/SSP nativo; nunca tentamos capturar ou contornar
    # PIN/passkey.
    code = int(
        api.authenticate_device_ex(
            None,
            None,
            ctypes.byref(info),
            None,
            MITM_PROTECTION_NOT_REQUIRED,
        )
    )
    if code == ERROR_SUCCESS:
        return PairResult(
            normalized,
            name,
            code,
            success=True,
            message="dispositivo autenticado/pareado com sucesso",
        )
    if code == ERROR_NO_MORE_ITEMS:
        return PairResult(
            normalized,
            name,
            code,
            already_paired=True,
            success=True,
            message="o dispositivo já estava autenticado/pareado no Windows",
        )
    if code == ERROR_CANCELLED:
        message = "pareamento cancelado pelo usuário"
    elif code == ERROR_INVALID_PARAMETER:
        message = "estrutura de dispositivo inválida (endereço/nome)"
    else:
        message = f"falha no pareamento: {_format_winerror(code)}"
    return PairResult(normalized, name, code, message=message)
