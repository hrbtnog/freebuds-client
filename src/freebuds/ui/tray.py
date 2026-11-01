"""Ícone e menu da bandeja do sistema."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from ..core.client import DeviceSnapshot
from .i18n import option_label, t
from .icons import make_tray_icon


def _battery_text(snapshot: DeviceSnapshot | None) -> str:
    if snapshot is None or snapshot.battery is None:
        return t("tray.battery_empty")
    battery = snapshot.battery
    parts: list[str] = []
    if battery.left is not None:
        parts.append(t("battery.left_short", value=battery.left))
    if battery.right is not None:
        parts.append(t("battery.right_short", value=battery.right))
    if battery.case is not None:
        parts.append(t("battery.case_short", value=battery.case))
    if not parts and battery.global_level is not None:
        parts.append(f"{battery.global_level}%")
    content = " · ".join(parts) if parts else t("common.none")
    return t("tray.battery", value=content)


def _anc_text(snapshot: DeviceSnapshot | None) -> str:
    if snapshot is None or snapshot.anc is None:
        return t("tray.anc_empty")
    anc = snapshot.anc
    raw_mode = anc.mode or ""
    label = option_label("anc_mode", raw_mode, raw_mode.capitalize() or t("common.unknown"))
    if anc.mode_code is not None and not anc.mode:
        label = t("anc.summary_unknown_mode", code=anc.mode_code)
    if anc.mode == "normal":
        return t("tray.anc", value=label)
    if anc.mode_code == 2 and anc.level_code == 4:
        if anc.adaptive_level is not None:
            return t(
                "tray.anc",
                value=t("anc.summary_adaptive_level", mode=label, level=anc.adaptive_level + 1),
            )
        return t("tray.anc", value=t("anc.summary_adaptive", mode=label))
    if anc.level:
        level_label = option_label("anc_level", anc.level, anc.level.capitalize())
        return t("tray.anc", value=t("anc.summary_level", mode=label, level=level_label))
    if anc.level_code is not None:
        return t("tray.anc", value=t("anc.summary_level_code", mode=label, code=anc.level_code))
    return t("tray.anc", value=label)


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
        self.tray.setToolTip(
            t("tray.tooltip_disconnected", name=t("app.name"))
        )

        self.menu = QMenu()
        self.open_action = QAction(t("tray.open"), self.menu)
        self.status_action = QAction(t("tray.status_disconnected"), self.menu)
        self.status_action.setEnabled(False)
        self.battery_action = QAction(t("tray.battery_empty"), self.menu)
        self.battery_action.setEnabled(False)
        self.anc_action = QAction(t("tray.anc_empty"), self.menu)
        self.anc_action.setEnabled(False)
        self.refresh_action = QAction(t("tray.refresh"), self.menu)
        self.quit_action = QAction(t("tray.quit"), self.menu)

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
        ) or t("hero.title_default")

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
            self.tray.setToolTip(
                t(
                    "tray.tooltip_connected",
                    name=name,
                    battery=battery_text,
                    anc=anc_text,
                )
            )
            self.status_action.setText(name)
            self.battery_action.setText(battery_text)
            self.anc_action.setText(anc_text)
        else:
            self.tray.setIcon(make_tray_icon(None, None, connected=False))
            self.tray.setToolTip(t("tray.tooltip_disconnected", name=name))
            self.status_action.setText(t("tray.status_disconnected"))
            self.battery_action.setText(t("tray.battery_empty"))
            self.anc_action.setText(t("tray.anc_empty"))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window()
