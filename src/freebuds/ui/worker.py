"""Threads de conexão, polling e varredura Bluetooth da UI."""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Sequence

from PySide6.QtCore import QThread, Signal

from ..core.client import FreeBudsClient
from ..core.errors import FreeBudsError
from ..core.models import BluetoothDevice
from ..core.windows_bt import enumerate_devices
from .i18n import t


class DeviceWorker(QThread):
    """Mantém uma sessão SPP e emite snapshots periodicamente."""

    connected = Signal(object)
    snapshot_ready = Signal(object)
    failed = Signal(str)
    action_failed = Signal(str)
    action_done = Signal(str)

    def __init__(
        self,
        address: str,
        channels: Sequence[int],
        *,
        poll_interval: float = 30.0,
        connect_timeout: float = 5.0,
        response_timeout: float = 2.0,
        retry_interval: float = 12.0,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self.address = address
        self.channels = list(channels)
        self._poll_interval = max(5.0, float(poll_interval))
        self._connect_timeout = connect_timeout
        self._response_timeout = response_timeout
        self._retry_interval = max(1.0, float(retry_interval))
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._actions: queue.Queue[tuple[str, object, str]] = queue.Queue()

    def stop(self) -> None:
        """Pede o encerramento e acorda a thread se ela estiver dormindo."""

        self._stop_event.set()
        self._wake_event.set()

    def request_refresh(self) -> None:
        """Antecipa o próximo ciclo de leitura."""

        self._wake_event.set()

    def set_anc_mode(self, mode_code: int) -> None:
        """Enfileira uma troca de modo; a escrita acontece na thread do worker."""

        self._actions.put(
            ("anc_mode", mode_code, t("worker.done_anc_mode"))
        )
        self._wake_event.set()

    def set_anc_level(self, mode_code: int, level_code: int) -> None:
        """Enfileira uma troca de nível do modo ativo de ANC."""

        self._actions.put(
            ("anc_level", (mode_code, level_code), t("worker.done_anc_level"))
        )
        self._wake_event.set()

    def set_anc_adaptive_level(self, level_code: int) -> None:
        """Enfileira o ajuste da intensidade do Reconhecimento adaptável."""

        self._actions.put(
            ("adaptive_level", level_code, t("worker.done_adaptive_level"))
        )
        self._wake_event.set()

    def set_sound_profile(self, profile_id: int) -> None:
        self._enqueue(
            "sound_profile", profile_id, t("worker.done_sound_profile")
        )

    def set_spatial_mode(self, mode_code: int) -> None:
        self._enqueue(
            "spatial_mode", mode_code, t("worker.done_spatial_mode")
        )

    def set_adaptive_volume(self, enabled: bool) -> None:
        self._enqueue(
            "adaptive_volume", enabled, t("worker.done_adaptive_volume")
        )

    def set_conversation_awareness(self, enabled: bool) -> None:
        self._enqueue(
            "conversation_awareness",
            enabled,
            t("worker.done_conversation_awareness"),
        )

    def set_one_earbud_anc(self, enabled: bool) -> None:
        self._enqueue(
            "one_earbud_anc", enabled, t("worker.done_one_earbud_anc")
        )

    def set_head_control(self, enabled: bool | None = None) -> None:
        self._enqueue(
            "head_control", enabled, t("worker.done_head_control")
        )

    def set_head_action(self, field: int, action: int) -> None:
        label = (
            t("worker.done_head_nod")
            if field == 3
            else t("worker.done_head_shake")
        )
        self._enqueue("head_action", (field, action), label)

    def set_wear_detection(self, enabled: bool) -> None:
        self._enqueue(
            "wear_detection", enabled, t("worker.done_wear_detection")
        )

    def set_sound_quality(self, value: int) -> None:
        self._enqueue(
            "sound_quality", value, t("worker.done_sound_quality")
        )

    def set_low_latency(self, enabled: bool) -> None:
        self._enqueue(
            "low_latency", enabled, t("worker.done_low_latency")
        )

    def set_press_hold(self, side: str, action: int) -> None:
        self._enqueue(
            "press_hold", (side, action), t("worker.done_press_hold")
        )

    def set_pinch_hold(self, side: str, action: int) -> None:
        self._enqueue(
            "pinch_hold", (side, action), t("worker.done_pinch_hold")
        )

    def set_double_tap(self, left: int, right: int) -> None:
        self._enqueue(
            "double_tap", (left, right), t("worker.done_double_tap")
        )

    def set_triple_tap(self, side: str, action: int) -> None:
        self._enqueue(
            "triple_tap", (side, action), t("worker.done_triple_tap")
        )

    def _enqueue(self, kind: str, payload: object, label: str) -> None:
        self._actions.put((kind, payload, label))
        self._wake_event.set()

    def set_poll_interval(self, seconds: float) -> None:
        self._poll_interval = max(5.0, float(seconds))
        self._wake_event.set()

    def run(self) -> None:  # noqa: D401 - assinatura do QThread
        client: FreeBudsClient | None = None
        try:
            while not self._stop_event.is_set():
                if client is None:
                    try:
                        client = FreeBudsClient(
                            self.address,
                            channels=self.channels,
                            connect_timeout=self._connect_timeout,
                            response_timeout=self._response_timeout,
                        )
                        connection = client.connect(
                            should_stop=self._stop_event.is_set
                        )
                    except (FreeBudsError, ValueError) as exc:
                        client = None
                        if self._stop_event.is_set():
                            break
                        self.failed.emit(str(exc))
                        if self._wait(self._retry_interval):
                            break
                        continue

                    if self._stop_event.is_set():
                        break
                    self.connected.emit(connection)

                self._apply_actions(client)

                try:
                    snapshot = client.read_snapshot(include_advanced=True)
                except (FreeBudsError, ValueError) as exc:
                    client.close()
                    client = None
                    if self._stop_event.is_set():
                        break
                    self.failed.emit(
                        t("worker.error_connection_lost", error=exc)
                    )
                    if self._wait(self._retry_interval):
                        break
                    continue

                self.snapshot_ready.emit(snapshot)

                if not client.connected:
                    client.close()
                    client = None
                    if not self._stop_event.is_set():
                        self.failed.emit(
                            t("worker.error_connection_lost_reading")
                        )
                    if self._wait(self._retry_interval):
                        break
                    continue

                if self._wait_for_update(client, self._poll_interval):
                    break
        except Exception as exc:  # noqa: BLE001 - limite da thread
            if not self._stop_event.is_set():
                self.failed.emit(
                    t("worker.error_unexpected_connection", error=exc)
                )
        finally:
            if client is not None:
                client.close()

    def _apply_actions(self, client: FreeBudsClient) -> None:
        while not self._stop_event.is_set():
            try:
                kind, payload, label = self._actions.get_nowait()
            except queue.Empty:
                return
            try:
                self._dispatch_action(client, kind, payload)
                self.action_done.emit(label)
            except (FreeBudsError, ValueError) as exc:
                self.action_failed.emit(str(exc))

    @staticmethod
    def _dispatch_action(
        client: FreeBudsClient, kind: str, payload: object
    ) -> None:
        if kind == "anc_mode":
            client.set_anc(mode_code=int(payload))
        elif kind == "anc_level":
            mode_code, level_code = payload  # type: ignore[misc]
            client.set_anc(mode_code=int(mode_code), level_code=int(level_code))
        elif kind == "adaptive_level":
            client.set_anc_adaptive_level(int(payload))
        elif kind == "sound_profile":
            client.set_sound_profile(int(payload))
        elif kind == "spatial_mode":
            client.set_spatial_mode(int(payload))
        elif kind == "adaptive_volume":
            client.set_adaptive_volume(bool(payload))
        elif kind == "conversation_awareness":
            client.set_conversation_awareness(bool(payload))
        elif kind == "one_earbud_anc":
            client.set_one_earbud_anc(bool(payload))
        elif kind == "head_control":
            client.set_head_control(enabled=bool(payload))
        elif kind == "head_action":
            field, action = payload  # type: ignore[misc]
            if int(field) == 3:
                client.set_head_control(nod_action=int(action))
            else:
                client.set_head_control(shake_action=int(action))
        elif kind == "wear_detection":
            client.set_wear_detection(bool(payload))
        elif kind == "sound_quality":
            client.set_sound_quality(int(payload))
        elif kind == "low_latency":
            client.set_low_latency(bool(payload))
        elif kind == "press_hold":
            side, action = payload  # type: ignore[misc]
            client.set_press_hold(str(side), int(action))
        elif kind == "pinch_hold":
            side, action = payload  # type: ignore[misc]
            client.set_pinch_hold(str(side), int(action))
        elif kind == "double_tap":
            left, right = payload  # type: ignore[misc]
            client.set_double_tap(int(left), int(right))
        elif kind == "triple_tap":
            side, action = payload  # type: ignore[misc]
            client.set_triple_tap(str(side), int(action))
        else:
            raise ValueError(f"ação de UI desconhecida: {kind}")

    def _wait_for_update(self, client: FreeBudsClient, seconds: float) -> bool:
        """Aguarda um push espontâneo, um refresh manual ou o próximo polling.

        O retorno ``True`` significa que a thread deve encerrar. O fone envia
        ``0x2B2A`` quando o ANC muda no celular; ao acordar, o worker lê um
        snapshot imediatamente, sem depender do intervalo de polling.
        """

        end = time.monotonic() + max(0.0, seconds)
        while not self._stop_event.is_set():
            if self._wake_event.is_set():
                self._wake_event.clear()
                return False
            remaining = end - time.monotonic()
            if remaining <= 0:
                return False
            if client.wait_for_notifications(
                min(remaining, 0.5),
                should_stop=self._stop_event.is_set,
            ):
                return False
        return True

    def _wait(self, seconds: float) -> bool:
        """Dorme até o intervalo, um refresh ou um pedido de parada."""

        self._wake_event.wait(seconds)
        if self._stop_event.is_set():
            return True
        self._wake_event.clear()
        return False


class ScanWorker(QThread):
    """Executa uma varredura Bluetooth sem bloquear a janela."""

    devices_found = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        *,
        seconds: float = 8.0,
        include_unknown: bool = True,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self.seconds = seconds
        self.include_unknown = include_unknown

    def run(self) -> None:  # noqa: D401 - assinatura do QThread
        try:
            devices: list[BluetoothDevice] = enumerate_devices(
                include_unknown=self.include_unknown,
                issue_inquiry=True,
                inquiry_seconds=self.seconds,
            )
        except (FreeBudsError, ValueError) as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - limite da thread
            self.failed.emit(
                t("worker.error_scan_unexpected", error=exc)
            )
            return
        self.devices_found.emit(devices)
