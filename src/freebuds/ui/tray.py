"""Ícone e menu da bandeja do sistema."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from ..core.client import DeviceSnapshot
from .icons import make_tray_icon

_ANC_LABELS = {
    "normal": "Normal",
    "cancellation": "Cancelamento",
    "awareness": "Transparência",
}


def _battery_text(snapshot: DeviceSnapshot | None) -> str:
    if snapshot is None or snapshot.battery is None:
        return "Bateria: —"
    battery = snapshot.battery
    parts: list[str] = []
    if battery.left is not None:
        parts.append(f"E {battery.left}%")
    if battery.right is not None:
        parts.append(f"D {battery.right}%")
    if battery.case is not None:
        parts.append(f"Estojo {battery.case}%")
    if not parts and battery.global_level is not None:
        parts.append(f"{battery.global_level}%")
    return "Bateria: " + (" · ".join(parts) if parts else "—")


def _anc_text(snapshot: DeviceSnapshot | None) -> str:
    if snapshot is None or snapshot.anc is None:
        return "ANC: —"
    anc = snapshot.anc
    label = _ANC_LABELS.get(anc.mode or "")
    if label is None:
        label = f"Modo {anc.mode_code}" if anc.mode_code is not None else "Desconhecido"
    if anc.mode == "normal":
        return f"ANC: {label}"
    if anc.mode_code == 2 and anc.level_code == 4:
        if anc.adaptive_level is not None:
            return f"ANC: {label} (adaptável {anc.adaptive_level + 1}/11)"
        return f"ANC: {label} (adaptável)"
    if anc.level:
        level = {
            "normal": "Normal",
            "comfort": "Conforto",
            "ultra": "Ultra",
            "dynamic": "Dinâmico",
            "voice_boost": "Realce de voz",
            "adaptive": "Reconhecimento adaptável",
        }.get(anc.level, anc.level)
        return f"ANC: {label} ({level})"
    if anc.level_code is not None:
        return f"ANC: {label} (código {anc.level_code})"
    return f"ANC: {label}"


class TrayController(QObject):
    """Controla o ícone, o tooltip e o menu da bandeja."""

    def __init__(
        self,
        window: QWidget,
        *,
        on_refresh: Callable[[], None],
        on_quit: Callable[[], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._window = window
        self._on_refresh = on_refresh
        self._on_quit = on_quit

        self.tray = QSystemTrayIcon(
            make_tray_icon(None, None, connected=False), self
        )
        self.tray.setToolTip("FreeBuds Client — desconectado")

        self.menu = QMenu()
        self.open_action = QAction("Abrir FreeBuds Client", self.menu)
        self.status_action = QAction("Desconectado", self.menu)
        self.status_action.setEnabled(False)
        self.battery_action = QAction("Bateria: —", self.menu)
        self.battery_action.setEnabled(False)
        self.anc_action = QAction("ANC: —", self.menu)
        self.anc_action.setEnabled(False)
        self.refresh_action = QAction("Atualizar agora", self.menu)
        self.quit_action = QAction("Sair", self.menu)

        self.menu.addAction(self.open_action)
        self.menu.addSeparator()
        self.menu.addAction(self.status_action)
        self.menu.addAction(self.battery_action)
        self.menu.addAction(self.anc_action)
        self.menu.addSeparator()
        self.menu.addAction(self.refresh_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        self.tray.setContextMenu(self.menu)

        self.open_action.triggered.connect(self.show_window)
        self.refresh_action.triggered.connect(lambda: self._on_refresh())
        self.quit_action.triggered.connect(lambda: self._on_quit())
        self.tray.activated.connect(self._on_activated)

    def show(self) -> None:
        self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show_window(self) -> None:
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    def notify(self, title: str, message: str) -> None:
        if self.tray.isVisible():
            self.tray.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )

    def update(
        self,
        snapshot: DeviceSnapshot | None,
        device_name: str | None,
        *,
        connected: bool,
    ) -> None:
        battery_text = _battery_text(snapshot)
        anc_text = _anc_text(snapshot)
        name = device_name or (
            snapshot.info.model if snapshot is not None else None
        ) or "FreeBuds"

        if connected and snapshot is not None:
            battery = snapshot.battery
            level = None
            if battery is not None:
                if battery.global_level is not None:
                    level = battery.global_level
                else:
                    available = [
                        value
                        for value in (battery.left, battery.right, battery.case)
                        if value is not None
                    ]
                    level = min(available) if available else None
            anc_mode = snapshot.anc.mode if snapshot.anc is not None else None
            self.tray.setIcon(make_tray_icon(level, anc_mode, connected=True))
            self.tray.setToolTip(f"{name}\n{battery_text}\n{anc_text}")
            self.status_action.setText(name)
            self.battery_action.setText(battery_text)
            self.anc_action.setText(anc_text)
        else:
            self.tray.setIcon(make_tray_icon(None, None, connected=False))
            self.tray.setToolTip(f"{name}\nDesconectado")
            self.status_action.setText("Desconectado")
            self.battery_action.setText("Bateria: —")
            self.anc_action.setText("ANC: —")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window()
