"""Interface de linha de comando do FreeBuds Client.

A CLI é deliberadamente somente leitura no ``probe``: ela serve para descobrir
dispositivos, testar o handshake, ler bateria/ANC e analisar capturas sem
alterar configurações dos fones.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .. import __version__
from ..config.settings import Settings, SettingsStore
from ..core.client import resolve_channels
from ..core.commands import (
    CMD_ANC,
    CMD_BATTERY,
    CMD_BATTERY_NOTIFY,
    CMD_DEVICE_INFO,
    anc_request,
    battery_request,
    command_name,
    decode_anc,
    decode_battery,
    decode_device_info,
    decode_known_frame,
    info_request,
)
from ..core.errors import (
    BluetoothRadioUnavailableError,
    FreeBudsError,
    RequestTimeout,
    SessionError,
    TransportError,
)
from ..core.models import AncState, BatteryState, BluetoothDevice, DeviceInfo
from ..core.protocol import (
    FrameIssue,
    HuaweiFrame,
    decode_stream,
    parse_frame,
)
from ..core.session import HuaweiSession
from ..core.transport import RfcommTransport
from ..core.util import is_huawei_device_name, normalize_address
from ..core.windows_bt import (
    MAX_INQUIRY_SECONDS,
    enumerate_devices,
    pair_device,
)
from ..core.windows_bt import (
    supported as windows_bluetooth_supported,
)

_MODE_LABELS_PT = {
    "normal": "normal",
    "cancellation": "cancelamento",
    "awareness": "transparência",
}
_LEVEL_LABELS_PT = {
    "normal": "normal",
    "comfort": "conforto",
    "ultra": "ultra",
    "dynamic": "dinâmico",
    "voice_boost": "realce de voz",
    "adaptive": "reconhecimento adaptável",
}


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("informe um número") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("o valor deve ser positivo")
    return number


def _non_negative_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("informe um número") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("o valor não pode ser negativo")
    return number


def _channel(value: str) -> int:
    try:
        channel = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("informe um número inteiro") from exc
    if not 1 <= channel <= 30:
        raise argparse.ArgumentTypeError("o canal RFCOMM deve estar entre 1 e 30")
    return channel


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="freebuds",
        description=(
            "Cliente não oficial para HUAWEI FreeBuds no Windows — descoberta, "
            "pareamento, diagnóstico SPP e decodificação de capturas."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--settings",
        metavar="ARQUIVO",
        help="caminho alternativo para settings.json",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list", help="lista dispositivos Bluetooth clássicos conhecidos pelo Windows"
    )
    list_parser.add_argument("--json", action="store_true", help="saída JSON")
    list_parser.set_defaults(func=cmd_list)

    scan_parser = subparsers.add_parser(
        "scan", help="faz inquiry Bluetooth clássico por novos dispositivos"
    )
    scan_parser.add_argument(
        "--seconds",
        type=_positive_float,
        default=8.0,
        metavar="N",
        help="duração do inquiry em segundos (padrão: 8)",
    )
    scan_parser.add_argument(
        "--all",
        action="store_true",
        help="mostra todos os dispositivos, não apenas nomes Huawei/HONOR/FreeBuds",
    )
    scan_parser.add_argument("--json", action="store_true", help="saída JSON")
    scan_parser.set_defaults(func=cmd_scan)

    pair_parser = subparsers.add_parser(
        "pair", help="pareia via assistente/SSP do Windows"
    )
    pair_parser.add_argument(
        "target", help="endereço MAC (AA:BB:...) ou nome do dispositivo"
    )
    pair_parser.add_argument(
        "--scan-seconds",
        type=_non_negative_float,
        default=6.0,
        metavar="N",
        help="inquiry para localizar um nome ainda não lembrado (0 desativa; padrão: 6)",
    )
    pair_parser.add_argument("--json", action="store_true", help="saída JSON")
    pair_parser.set_defaults(func=cmd_pair)

    probe_parser = subparsers.add_parser(
        "probe",
        help="conecta via RFCOMM e faz handshake/bateria/ANC (somente leitura)",
    )
    target = probe_parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--address", metavar="MAC", help="endereço do dispositivo")
    target.add_argument("--name", metavar="NOME", help="nome (ou parte) já conhecido")
    probe_parser.add_argument(
        "--channel",
        type=_channel,
        action="append",
        metavar="N",
        help="força canal RFCOMM; pode ser repetido (padrão: 1 e 16)",
    )
    probe_parser.add_argument(
        "--timeout",
        type=_positive_float,
        metavar="SEG",
        help="timeout de resposta (padrão: configuração ou 2s)",
    )
    probe_parser.add_argument(
        "--connect-timeout",
        type=_positive_float,
        metavar="SEG",
        help="timeout de conexão RFCOMM (padrão: configuração ou 5s)",
    )
    probe_parser.add_argument(
        "--listen",
        type=_non_negative_float,
        default=0.0,
        metavar="SEG",
        help="escuta notificações por N segundos após o snapshot",
    )
    probe_parser.add_argument(
        "--raw",
        action="store_true",
        help="mostra/inclui os bytes TX/RX e problemas do parser",
    )
    probe_parser.add_argument(
        "--no-save",
        action="store_true",
        help="não salva o canal que funcionou nas preferências",
    )
    probe_parser.add_argument("--json", action="store_true", help="saída JSON")
    probe_parser.set_defaults(func=cmd_probe)

    decode_parser = subparsers.add_parser(
        "decode", help="decodifica quadros Huawei de uma string ou arquivo hex"
    )
    source = decode_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("data", nargs="?", help="bytes hex, ex.: '5A0006...'")
    source.add_argument(
        "--file", metavar="ARQUIVO", help="arquivo-texto com hex (use - para stdin)"
    )
    decode_parser.add_argument("--json", action="store_true", help="saída JSON")
    decode_parser.set_defaults(func=cmd_decode)

    ui_parser = subparsers.add_parser(
        "ui", help="abre a interface gráfica (requer PySide6)"
    )
    ui_parser.add_argument(
        "--address",
        metavar="MAC",
        help="conecta automaticamente a este dispositivo ao abrir",
    )
    ui_parser.set_defaults(func=cmd_ui)

    return parser


# ---------------------------------------------------------------------------
# list / scan / pair
# ---------------------------------------------------------------------------


def _emit_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _print_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    text_rows = [[str(value) for value in row] for row in rows]
    widths = [
        max(len(str(header)), *(len(row[index]) for row in text_rows))
        if text_rows
        else len(str(header))
        for index, header in enumerate(headers)
    ]
    print("  ".join(str(header).ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in text_rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _format_timestamp(value: object) -> str:
    if not value:
        return "—"
    try:
        return value.strftime("%Y-%m-%d %H:%M")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        return "—"


def _print_devices(devices: Sequence[BluetoothDevice]) -> None:
    rows = [
        (
            device.address,
            device.display_name,
            "sim" if device.connected else "—",
            "sim" if device.authenticated else "—",
            _format_timestamp(device.last_seen),
        )
        for device in devices
    ]
    _print_table(("ENDEREÇO", "NOME", "CONECTADO", "PAR", "VISTO POR ÚLTIMO"), rows)


def cmd_list(args: argparse.Namespace) -> int:
    if not windows_bluetooth_supported():
        raise FreeBudsError("a listagem Bluetooth exige Windows 10/11")
    devices = enumerate_devices()
    if args.json:
        _emit_json({"devices": [device.to_dict() for device in devices]})
        return 0
    if not devices:
        print("Nenhum dispositivo Bluetooth clássico conhecido pelo Windows.")
        print("Ative o Bluetooth e use `freebuds scan` para procurar os fones.")
        return 0
    _print_devices(devices)
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    if not windows_bluetooth_supported():
        raise FreeBudsError("o scan Bluetooth exige Windows 10/11")
    if args.seconds > MAX_INQUIRY_SECONDS:
        raise ValueError(
            f"--seconds máximo é {MAX_INQUIRY_SECONDS:.1f}s "
            "(limite do cTimeoutMultiplier do Windows)"
        )
    start = time.monotonic()
    devices = enumerate_devices(
        include_unknown=True,
        issue_inquiry=True,
        inquiry_seconds=args.seconds,
    )
    elapsed = time.monotonic() - start
    selected = (
        devices
        if args.all
        else [device for device in devices if is_huawei_device_name(device.name)]
    )
    if args.json:
        _emit_json(
            {
                "devices": [device.to_dict() for device in selected],
                "total_seen": len(devices),
                "filtered": not args.all,
                "elapsed_seconds": round(elapsed, 2),
            }
        )
        return 0
    if selected:
        _print_devices(selected)
        print(f"\n{len(selected)} dispositivo(s) exibido(s) em {elapsed:.1f}s.")
    else:
        print(f"Nenhum dispositivo correspondente encontrado em {elapsed:.1f}s.")
        print("Use `--all` para mostrar todos os dispositivos vistos no inquiry.")
    if not args.all and len(devices) > len(selected):
        print(
            f"{len(devices) - len(selected)} outro(s) dispositivo(s) não-Huawei "
            "foram omitidos; use --all para vê-los."
        )
    return 0


def _select_named_device(devices: Sequence[BluetoothDevice], name: str) -> BluetoothDevice:
    needle = name.strip().casefold()
    exact = [device for device in devices if device.name.casefold() == needle]
    candidates = exact or [
        device for device in devices if needle and needle in device.name.casefold()
    ]
    if not candidates:
        raise FreeBudsError(
            f"nenhum dispositivo com nome contendo {name!r} foi encontrado. "
            "Use `freebuds scan` ou informe o endereço MAC."
        )
    if len(candidates) > 1:
        listing = "\n".join(
            f"  {device.address}  {device.display_name}" for device in candidates
        )
        raise FreeBudsError(
            f"mais de um dispositivo corresponde a {name!r}:\n{listing}\n"
            "Use --address para escolher um."
        )
    return candidates[0]


def cmd_pair(args: argparse.Namespace) -> int:
    if not windows_bluetooth_supported():
        raise FreeBudsError("o pareamento assistido exige Windows 10/11")
    target = args.target.strip()
    try:
        address = normalize_address(target)
        is_address = True
    except ValueError:
        address = ""
        is_address = False

    devices = enumerate_devices()
    scanned = False
    if is_address:
        device = next((item for item in devices if item.address == address), None)
        name = device.name if device else None
    else:
        try:
            device = _select_named_device(devices, target)
        except FreeBudsError:
            if args.scan_seconds <= 0:
                raise
            if not args.json:
                print(
                    f"Dispositivo não lembrado; fazendo inquiry por "
                    f"{args.scan_seconds:.1f}s...",
                    file=sys.stderr,
                )
            scanned = True
            devices = enumerate_devices(
                include_unknown=True,
                issue_inquiry=True,
                inquiry_seconds=args.scan_seconds,
            )
            device = _select_named_device(devices, target)
        address = device.address
        name = device.display_name

    if not args.json:
        print(f"Pareando {name or '(sem nome)'} [{address}] via Windows...")
        print("O Windows pode exibir um assistente/SSP. Conclua-o na tela.")
    result = pair_device(address, name)
    payload = result.to_dict()
    payload["ok"] = result.success
    payload["scanned"] = scanned
    if args.json:
        _emit_json(payload)
    else:
        print(result.message)
        if result.success:
            print("Agora use `freebuds probe --address ...` quando os fones estiverem ativos.")
    return 0 if result.success else 1


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------


def _load_settings(path: str | None) -> tuple[SettingsStore, Settings]:
    store = SettingsStore(Path(path) if path else None)
    settings = store.load()
    if store.last_load_error:
        print(f"aviso: {store.last_load_error}", file=sys.stderr)
        print("aviso: usando configurações padrão; o arquivo não será sobrescrito.", file=sys.stderr)
    return store, settings


def _resolve_probe_target(args: argparse.Namespace) -> tuple[str, str | None]:
    if args.address:
        try:
            address = normalize_address(args.address)
        except ValueError as exc:
            raise FreeBudsError(str(exc)) from exc
        try:
            devices = enumerate_devices()
        except FreeBudsError:
            return address, None
        known = next((item for item in devices if item.address == address), None)
        return address, (known.name or None) if known else None

    devices = enumerate_devices()
    device = _select_named_device(devices, args.name)
    return device.address, device.display_name


def _channel_order(
    requested: Sequence[int] | None, settings: Settings, address: str
) -> list[int]:
    return resolve_channels(
        requested=requested,
        saved_channel=settings.last_channels.get(address),
        settings_channels=settings.channels,
    )


def _request_with_log(
    session: HuaweiSession,
    *,
    phase: str,
    payload: bytes,
    expected: tuple[bytes, ...],
    timeout: float,
    transactions: list[dict[str, Any]],
    warnings: list[str],
) -> HuaweiFrame | None:
    request = parse_frame(payload, validate_checksum=False)
    transaction: dict[str, Any] = {
        "phase": phase,
        "request": request.raw.hex(" ").upper(),
        "response": None,
        "error": None,
    }
    try:
        response = session.request_bytes(
            payload, expected=expected, timeout=timeout
        )
    except RequestTimeout as exc:
        transaction["error"] = str(exc)
        warnings.append(f"{phase}: {exc}")
        return None
    except SessionError as exc:
        transaction["error"] = str(exc)
        warnings.append(f"{phase}: {exc}")
        return None
    else:
        transaction["response"] = response.raw.hex(" ").upper()
        return response
    finally:
        transactions.append(transaction)


def _frame_issue_to_dict(issue: FrameIssue) -> dict[str, Any]:
    return {
        "offset": issue.offset,
        "message": issue.message,
        "data": issue.data.hex(" ").upper(),
    }


def _notification_to_dict(frame: HuaweiFrame) -> dict[str, Any]:
    return {
        "command": frame.command.hex(" ").upper(),
        "command_name": command_name(frame.command),
        "crc_valid": frame.checksum_valid,
        "raw": frame.raw.hex(" ").upper(),
        "decoded": decode_known_frame(frame),
    }


def _print_info(info: DeviceInfo) -> None:
    print("Informações do dispositivo:")
    print(f"  Modelo............: {info.model or 'não informado'}")
    print(f"  Submodelo.........: {info.submodel or 'não informado'}")
    print(f"  Hardware..........: {info.hardware_version or 'não informado'}")
    print(f"  Software/firmware.: {info.software_version or 'não informado'}")
    print(f"  Serial............: {info.serial_number or 'não informado'}")
    if info.left_serial_number or info.right_serial_number:
        print(f"  Serial esquerdo...: {info.left_serial_number or 'não informado'}")
        print(f"  Serial direito....: {info.right_serial_number or 'não informado'}")
    unknown = {
        key: value
        for key, value in info.fields.items()
        if key not in {3, 7, 9, 10, 15, 24}
    }
    if unknown:
        extras = ", ".join(
            f"0x{key:02X}={value}" for key, value in sorted(unknown.items())
        )
        print(f"  Outros campos.....: {extras}")


def _print_battery(battery: BatteryState) -> None:
    print("Bateria:")
    if battery.global_level is not None:
        print(f"  Global............: {battery.global_level}%")
    for label, value in (
        ("Esquerda", battery.left),
        ("Direita", battery.right),
        ("Estojo", battery.case),
    ):
        if value is not None:
            print(f"  {label:<18}: {value}%")
    if battery.global_level is None and battery.left is None and battery.right is None:
        print("  (o firmware não retornou níveis reconhecíveis)")
    if battery.charging is not None:
        print(f"  Carregando........: {'sim' if battery.charging else 'não'}")
    if battery.charging_flags is not None:
        print(f"  Flags de carga....: {battery.charging_flags.hex(' ').upper()}")
    extras = {
        key: value for key, value in battery.parameters.items() if key not in {1, 2, 3}
    }
    if extras:
        rendered = ", ".join(
            f"{key}={value.hex(' ').upper()}" for key, value in sorted(extras.items())
        )
        print(f"  Extras brutos.....: {rendered}")


def _print_anc(anc: AncState) -> None:
    print("Controle de ruído (somente leitura):")
    mode = _MODE_LABELS_PT.get(anc.mode or "", anc.mode)
    print(f"  Modo..............: {mode or 'não informado'}", end="")
    if anc.mode_code is not None:
        print(f" (código {anc.mode_code})")
    else:
        print()
    if anc.level is not None:
        level = _LEVEL_LABELS_PT.get(anc.level, anc.level)
        print(f"  Nível.............: {level} (código {anc.level_code})")
        if anc.adaptive_level is not None:
            print(
                "  Intensidade.......: "
                f"{anc.adaptive_level + 1} de 11 "
                f"(bruto {anc.adaptive_level})"
            )
    elif anc.mode in {"cancellation", "awareness"}:
        print(f"  Nível.............: código {anc.level_code} (mapeamento desconhecido)")
    extras = {
        key: value for key, value in anc.parameters.items() if key != 1
    }
    if extras:
        rendered = ", ".join(
            f"{key}={value.hex(' ').upper()}" for key, value in sorted(extras.items())
        )
        print(f"  Extras brutos.....: {rendered}")
    print("  Escrita de ANC não é enviada nesta versão.")


def _print_transactions(transactions: Sequence[dict[str, Any]]) -> None:
    if not transactions:
        return
    print("Transações SPP:")
    for transaction in transactions:
        print(f"  [{transaction['phase']}]")
        print(f"    TX {transaction['request']}")
        if transaction.get("response"):
            print(f"    RX {transaction['response']}")
        if transaction.get("error"):
            print(f"    erro: {transaction['error']}")


def _probe_one_channel(
    *,
    address: str,
    channel: int,
    connect_timeout: float,
    response_timeout: float,
    listen_seconds: float,
) -> dict[str, Any]:
    transactions: list[dict[str, Any]] = []
    warnings: list[str] = []
    info: DeviceInfo | None = None
    battery: BatteryState | None = None
    anc: AncState | None = None
    notifications: list[HuaweiFrame] = []
    parser_issues: list[FrameIssue] = []

    transport = RfcommTransport(
        address, channel, connect_timeout=connect_timeout
    )
    session = HuaweiSession(transport, response_timeout=response_timeout)
    try:
        session.open()

        # O handshake é o teste real de que o canal escolhido é o SPP Huawei.
        info_response = _request_with_log(
            session,
            phase="handshake 0x0107",
            payload=info_request(),
            expected=(CMD_DEVICE_INFO,),
            timeout=response_timeout,
            transactions=transactions,
            warnings=warnings,
        )
        if info_response is None:
            raise RequestTimeout(
                f"handshake sem resposta no canal {channel}; canal não parece ser o SPP dos FreeBuds"
            )
        info = decode_device_info(info_response.parameters)

        battery_response = _request_with_log(
            session,
            phase="bateria 0x0108",
            payload=battery_request(),
            expected=(CMD_BATTERY, CMD_BATTERY_NOTIFY),
            timeout=response_timeout,
            transactions=transactions,
            warnings=warnings,
        )
        if battery_response is not None:
            battery = decode_battery(battery_response.parameters)

        anc_response = _request_with_log(
            session,
            phase="ANC 0x2B2A",
            payload=anc_request(),
            expected=(CMD_ANC,),
            timeout=response_timeout,
            transactions=transactions,
            warnings=warnings,
        )
        if anc_response is not None:
            anc = decode_anc(anc_response.parameters)

        if listen_seconds > 0:
            if session.is_open:
                notifications = session.wait_for_frames(listen_seconds)
            else:
                warnings.append(
                    "conexão encerrada antes da escuta de notificações"
                )
            if session.error is not None:
                warnings.append(f"conexão caiu durante a escuta: {session.error}")

        parser_issues = session.parse_issues
        if parser_issues:
            warnings.append(
                f"{len(parser_issues)} problema(s) de parser/CRC durante a sessão"
            )
    except (TransportError, RequestTimeout) as exc:
        return {
            "ok": False,
            "channel": channel,
            "error": str(exc),
            "transactions": transactions,
            "warnings": warnings,
        }
    except (SessionError, OSError) as exc:
        return {
            "ok": False,
            "channel": channel,
            "error": str(exc),
            "transactions": transactions,
            "warnings": warnings,
        }
    finally:
        session.close()

    return {
        "ok": True,
        "channel": channel,
        "error": None,
        "info": info,
        "battery": battery,
        "anc": anc,
        "notifications": notifications,
        "transactions": transactions,
        "warnings": warnings,
        "parser_issues": parser_issues,
    }


def cmd_probe(args: argparse.Namespace) -> int:
    if args.listen < 0:
        raise FreeBudsError("--listen não pode ser negativo")
    address, known_name = _resolve_probe_target(args)
    store, settings = _load_settings(args.settings)
    settings_ok = store.last_load_error is None
    connect_timeout = (
        args.connect_timeout
        if args.connect_timeout is not None
        else settings.connect_timeout
    )
    response_timeout = (
        args.timeout if args.timeout is not None else settings.response_timeout
    )
    channels = _channel_order(args.channel, settings, address)

    attempts: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    for channel in channels:
        if not args.json:
            print(f"Tentando canal RFCOMM {channel}...", file=sys.stderr)
        attempt = _probe_one_channel(
            address=address,
            channel=channel,
            connect_timeout=connect_timeout,
            response_timeout=response_timeout,
            listen_seconds=args.listen,
        )
        attempts.append(
            {
                "channel": channel,
                "ok": bool(attempt.get("ok")),
                "error": attempt.get("error"),
            }
        )
        if attempt.get("ok"):
            result = attempt
            break

    if result is None:
        error = (
            "não foi possível falar SPP com os fones em nenhum canal tentado. "
            "Confirme que estão ligados, fora do estojo, pareados e que o app "
            "oficial não está usando a conexão."
        )
        if args.json:
            _emit_json(
                {
                    "ok": False,
                    "address": address,
                    "name": known_name,
                    "attempts": attempts,
                    "error": error,
                }
            )
        else:
            print(f"Falha: {error}", file=sys.stderr)
            for attempt in attempts:
                print(
                    f"  canal {attempt['channel']}: {attempt['error']}",
                    file=sys.stderr,
                )
        return 1

    channel = int(result["channel"])
    info = result["info"]
    battery = result["battery"]
    anc = result["anc"]
    notifications: list[HuaweiFrame] = result["notifications"]
    warnings: list[str] = list(result["warnings"])
    parser_issues: list[FrameIssue] = result["parser_issues"]
    transactions: list[dict[str, Any]] = result["transactions"]

    if not args.no_save and settings_ok:
        try:
            store.remember_channel(settings, address, channel)
        except OSError as exc:
            warnings.append(f"não foi possível salvar o canal nas preferências: {exc}")

    display_name = known_name or (info.model if info else None)
    if args.json:
        payload = {
            "ok": True,
            "address": address,
            "name": display_name,
            "channel": channel,
            "attempts": attempts,
            "info": info.to_dict() if info else None,
            "battery": battery.to_dict() if battery else None,
            "anc": anc.to_dict() if anc else None,
            "notifications": [
                _notification_to_dict(frame) for frame in notifications
            ],
            "warnings": warnings,
        }
        if args.raw:
            payload["transactions"] = transactions
            payload["parser_issues"] = [
                _frame_issue_to_dict(issue) for issue in parser_issues
            ]
        _emit_json(payload)
        return 0

    print(f"Dispositivo: {display_name or '(nome não resolvido)'}")
    print(f"Endereço...: {address}")
    print(f"Canal SPP..: {channel}")
    print("Handshake..: OK (0x0107)\n")
    if info:
        _print_info(info)
        print()
    if battery:
        _print_battery(battery)
        print()
    else:
        print("Bateria: sem resposta reconhecível.\n")
    if anc:
        _print_anc(anc)
        print()
    else:
        print("ANC: sem resposta reconhecível.\n")

    if args.listen > 0:
        if notifications:
            print(f"Notificações recebidas em {args.listen:.1f}s:")
            for frame in notifications:
                summary = ""
                decoded = decode_known_frame(frame)
                if decoded and frame.command in (CMD_BATTERY, CMD_BATTERY_NOTIFY):
                    levels = decoded
                    summary = (
                        f" — global={levels.get('global')} esquerda={levels.get('left')} "
                        f"direita={levels.get('right')} estojo={levels.get('case')}"
                    )
                elif decoded and frame.command == CMD_ANC:
                    mode_value = decoded.get("mode")
                    mode = (
                        _MODE_LABELS_PT.get(mode_value, mode_value)
                        if mode_value
                        else decoded.get("mode_code")
                    )
                    level = decoded.get("level") or decoded.get("level_code")
                    adaptive_level = decoded.get("adaptive_level")
                    if level == "adaptive" and adaptive_level is not None:
                        level = f"adaptável {adaptive_level + 1}/11"
                    summary = f" — ANC: modo={mode} nível={level}"
                elif frame.parameters:
                    items = list(sorted(frame.parameters.items()))[:12]
                    tlvs = ", ".join(
                        f"{key}={value.hex(' ').upper() or '(vazio)'}"
                        for key, value in items
                    )
                    if len(frame.parameters) > len(items):
                        tlvs += ", …"
                    summary = f" — TLVs: {tlvs}"
                crc = "CRC OK" if frame.checksum_valid else "CRC INVÁLIDO"
                print(
                    f"  {frame.command.hex(' ').upper()} "
                    f"({command_name(frame.command)}, {crc}){summary}"
                )
        else:
            print(f"Nenhuma notificação recebida em {args.listen:.1f}s.")

    if warnings:
        print("\nAvisos:")
        for warning in warnings:
            print(f"  - {warning}")
    if args.raw:
        print()
        _print_transactions(transactions)
        if parser_issues:
            print("Problemas de parser/CRC:")
            for issue in parser_issues:
                print(f"  offset {issue.offset}: {issue.message}")
    return 0


# ---------------------------------------------------------------------------
# decode
# ---------------------------------------------------------------------------


def _parse_hex_argument(text: str) -> bytes:
    cleaned = re.sub(r"0[xX]", "", text)
    cleaned = re.sub(r"[\s:,\-]", "", cleaned)
    if not cleaned:
        raise ValueError("nenhum byte hexadecimal informado")
    if len(cleaned) % 2:
        raise ValueError("a quantidade de dígitos hexadecimais deve ser par")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError("a entrada contém caracteres que não são hexadecimais") from exc


def _parse_hex_text_file(text: str) -> bytes:
    """Extrai bytes de um arquivo-texto com hex, aceitando logs simples.

    Linhas de dump com offset inicial (``0000  ``) e sufixo ASCII após ``|`` são
    aceitas. Linhas de comentário (``#``, ``//``, ``;``) são ignoradas.
    """

    result = bytearray()
    for original_line in text.splitlines():
        line = original_line.strip()
        if not line or line.startswith(("#", "//", ";")):
            continue
        if "|" in line:
            line = line.split("|", 1)[0]
        line = re.sub(r"^\s*(?:0x)?[0-9A-Fa-f]{4,8}\s{2,}", "", line)
        for token in re.split(r"[\s,;]+", line):
            token = token.strip()
            if not token:
                continue
            token = re.sub(r"^0[xX]", "", token)
            if token.startswith(("RX", "TX", "RX:", "TX:", ">", "<")):
                token = re.sub(r"^(?:RX|TX|RECV|SEND)[:>]?", "", token)
            token = token.replace(":", "").replace("-", "")
            if not token or not re.fullmatch(r"[0-9A-Fa-f]+", token):
                continue
            if len(token) % 2:
                continue
            result.extend(bytes.fromhex(token))
    return bytes(result)


def _frame_to_dict(frame: HuaweiFrame) -> dict[str, Any]:
    return {
        "command": frame.command.hex(" ").upper(),
        "command_name": command_name(frame.command),
        "length": len(frame.raw),
        "crc_valid": frame.checksum_valid,
        "raw": frame.raw.hex(" ").upper(),
        "parameters": [
            {
                "type": key,
                "type_hex": f"0x{key:02X}",
                "length": len(value),
                "value_hex": value.hex(" ").upper(),
                "value_ascii": _ascii_preview(value),
            }
            for key, value in sorted(frame.parameters.items())
        ],
        "decoded": decode_known_frame(frame),
    }


def _ascii_preview(value: bytes) -> str | None:
    if not value:
        return ""
    if all(32 <= byte < 127 for byte in value):
        return value.decode("ascii")
    return None


def _print_frame(frame: HuaweiFrame, index: int) -> None:
    crc = "OK" if frame.checksum_valid else "INVÁLIDO"
    print(f"Quadro {index}: {len(frame.raw)} byte(s), CRC {crc}")
    print(f"  Comando: {frame.command.hex(' ').upper()} ({command_name(frame.command)})")
    if frame.parameters:
        print("  Parâmetros:")
        for key, value in sorted(frame.parameters.items()):
            ascii_preview = _ascii_preview(value)
            ascii_text = f"  |{ascii_preview}|" if ascii_preview else ""
            print(
                f"    0x{key:02X} len={len(value)}: "
                f"{value.hex(' ').upper() or '(vazio)'}{ascii_text}"
            )
    else:
        print("  Parâmetros: (nenhum)")
    decoded = decode_known_frame(frame)
    if decoded:
        print("  Decodificado:")
        print(json.dumps(decoded, ensure_ascii=False, indent=4).replace("\n", "\n    "))
    print(f"  Bruto: {frame.raw.hex(' ').upper()}")
    print()


def cmd_decode(args: argparse.Namespace) -> int:
    if args.file:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            try:
                text = Path(args.file).read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise FreeBudsError(f"não foi possível ler {args.file}: {exc}") from exc
        data = _parse_hex_text_file(text)
        if not data:
            raise FreeBudsError(
                f"nenhum byte hexadecimal reconhecido em {args.file!r}"
            )
    else:
        data = _parse_hex_argument(args.data)

    frames, pending, issues = decode_stream(data, validate_checksum=False)
    if args.json:
        _emit_json(
            {
                "bytes": len(data),
                "frames": [_frame_to_dict(frame) for frame in frames],
                "pending_hex": pending.hex(" ").upper(),
                "issues": [_frame_issue_to_dict(issue) for issue in issues],
            }
        )
        return 0

    print(f"{len(data)} byte(s) analisado(s); {len(frames)} quadro(s) completo(s).\n")
    for index, frame in enumerate(frames, start=1):
        _print_frame(frame, index)

    if pending:
        print(f"Restante incompleto ({len(pending)} byte(s)): {pending.hex(' ').upper()}")
    if issues:
        print("Problemas de sincronização/CRC:")
        for issue in issues:
            detail = f"  offset {issue.offset}: {issue.message}"
            if issue.data:
                detail += f" | {issue.data.hex(' ').upper()}"
            print(detail)
    if not frames:
        print(
            "Nenhum quadro completo encontrado. Verifique magic 0x5A, tamanho e CRC.",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    """Abre a interface gráfica; o import é tardio para não exigir Qt na CLI."""

    from ..ui.app import run_ui

    settings_path = Path(args.settings) if args.settings else None
    return run_ui(address=args.address, settings_path=settings_path)


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("interrompido pelo usuário", file=sys.stderr)
        return 130
    except BluetoothRadioUnavailableError as exc:
        print(f"erro Bluetooth: {exc}", file=sys.stderr)
        print(
            "Dica: ative o Bluetooth no Windows, confirme o adaptador e tente "
            "novamente. Em notebooks pode haver uma tecla/função de rádio.",
            file=sys.stderr,
        )
        return 2
    except (FreeBudsError, ValueError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if os.environ.get("FREEBUDS_DEBUG"):
            raise
        print(f"erro inesperado: {exc}", file=sys.stderr)
        print(
            "Defina FREEBUDS_DEBUG=1 para ver o traceback e reporte o problema.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
