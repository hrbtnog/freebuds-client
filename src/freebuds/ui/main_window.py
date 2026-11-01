"""Janela principal do FreeBuds Client."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThread, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..config.settings import SettingsStore
from ..core.client import ConnectionInfo, DeviceSnapshot, resolve_channels
from ..core.commands import (
    CMD_ANC,
    CMD_BATTERY_NOTIFY,
    SOUND_PROFILES,
    SPATIAL_MODES,
    decode_anc,
    decode_battery,
)
from ..core.errors import FreeBudsError
from ..core.models import AncState, BatteryState, BluetoothDevice
from ..core.protocol import HuaweiFrame
from ..core.util import is_huawei_device_name
from ..core.windows_bt import enumerate_devices
from .icons import (
    make_app_icon,
    make_brand_mark,
    make_nav_icon,
    make_refresh_icon,
    make_search_icon,
)
from .i18n import language_options, option_label, set_language, t
from .theme import APP_STYLESHEET
from .tray import TrayController
from .widgets import (
    ActivityLog,
    AncPanel,
    BatteryOverview,
    DeviceDetailsPanel,
    FeatureCard,
    FeatureRow,
    FeaturesPanel,
    FieldComboBox,
    ProductHero,
    QuickTile,
    ToggleSwitch,
    make_section_label,
)
from .worker import DeviceWorker, ScanWorker

_ANC_MODE_LABELS = {
    "normal": "Normal",
    "cancellation": "Cancelamento",
    "awareness": "Transparência",
}
_ANC_LEVEL_LABELS = {
    "normal": "Normal",
    "comfort": "Conforto",
    "ultra": "Ultra",
    "dynamic": "Dinâmico",
    "voice_boost": "Realce de voz",
    "adaptive": "Reconhecimento adaptável",
}

_NAV_ITEMS = (
    ("overview", "Visão geral", "overview"),
    ("audio", "Áudio", "audio"),
    ("gestures", "Gestos", "gestures"),
    ("connection", "Conexão", "connection"),
    ("diagnostics", "Diagnóstico", "diagnostics"),
)

_PAGE_TITLES = {
    "overview": "Visão geral",
    "audio": "Áudio",
    "gestures": "Gestos",
    "connection": "Conexão",
    "diagnostics": "Diagnóstico",
}

_FEATURE_SECTIONS = {"audio": 0, "gestures": 1, "connection": 2}


def _page_title(key: str) -> str:
    return t(f"nav.{key}", default=_PAGE_TITLES.get(key, key))


def _battery_summary(battery: BatteryState | None) -> str:
    if battery is None:
        return t("battery.summary_none")
    parts: list[str] = []
    if battery.global_level is not None:
        parts.append(t("battery.global_short", value=battery.global_level))
    if battery.left is not None:
        parts.append(t("battery.left_short", value=battery.left))
    if battery.right is not None:
        parts.append(t("battery.right_short", value=battery.right))
    if battery.case is not None:
        parts.append(t("battery.case_short", value=battery.case))
    if battery.charging:
        parts.append(t("battery.charging_short"))
    return ", ".join(parts) if parts else t("battery.summary_none")


def _anc_summary(anc: AncState | None) -> str:
    if anc is None:
        return t("anc.summary_none")
    raw_mode = anc.mode or ""
    mode = option_label("anc_mode", raw_mode, raw_mode.capitalize() or t("common.unknown"))
    if anc.mode_code is not None and not anc.mode:
        mode = t("anc.summary_unknown_mode", code=anc.mode_code)
    if anc.mode == "normal":
        return mode
    if anc.mode == "awareness" and anc.level_code == 4:
        if anc.adaptive_level is not None:
            return t(
                "anc.summary_adaptive_level",
                mode=mode,
                level=anc.adaptive_level + 1,
            )
        return t("anc.summary_adaptive", mode=mode)
    if anc.level:
        level_label = option_label("anc_level", anc.level, anc.level.capitalize())
        return t("anc.summary_level", mode=mode, level=level_label)
    if anc.level_code is not None:
        return t("anc.summary_level_code", mode=mode, code=anc.level_code)
    return mode


def _battery_key(battery: BatteryState | None) -> tuple[object, ...]:
    if battery is None:
        return (None, None, None, None, None)
    return (
        battery.global_level,
        battery.left,
        battery.right,
        battery.case,
        battery.charging,
    )


def _anc_key(anc: AncState | None) -> tuple[object, ...]:
    if anc is None:
        return (None, None, None)
    return (anc.mode_code, anc.level_code, anc.adaptive_level)


def _on_off(value: bool | None, on_text: str, off_text: str) -> str:
    if value is True:
        return on_text
    if value is False:
        return off_text
    return "—"


def _count_text(value: int, singular: str, plural: str) -> str:
    return f"{value} {singular if value == 1 else plural}."


class MainWindow(QMainWindow):
    """Janela principal com navegação lateral, som, bateria e ajustes."""

    def __init__(
        self,
        *,
        settings_path: Path | None = None,
        address: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_store = SettingsStore(settings_path)
        self._settings = self._settings_store.load()
        set_language(self._settings.language)
        self._devices: list[BluetoothDevice] = []
        self._worker: DeviceWorker | None = None
        self._scan_worker: ScanWorker | None = None
        self._last_snapshot: DeviceSnapshot | None = None
        self._last_connection: ConnectionInfo | None = None
        self._last_device_name: str | None = None
        self._last_battery_key: tuple[object, ...] | None = None
        self._last_anc_key: tuple[object, ...] | None = None
        self._last_error: str | None = None
        self._last_warnings: set[str] = set()
        self._seen_raw_notifications: set[
            tuple[int, tuple[tuple[int, bytes], ...]]
        ] = set()
        self._session_connected = False
        self._force_quit = False
        self._manual_stop = False
        self._closing = False
        self._tray_notice_shown = False
        self._tray: TrayController | None = None
        self._anc_busy = False
        self._current_page = "overview"

        self.setWindowTitle("FreeBuds Client")
        self.setWindowIcon(make_app_icon())
        self.setMinimumSize(1100, 680)
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            width = max(1100, min(1320, available.width() - 80))
            height = max(680, min(880, available.height() - 80))
            self.resize(width, height)
        else:
            self.resize(1320, 880)
        self.setStyleSheet(APP_STYLESHEET)

        self._build_ui()
        self._setup_tray()
        self._apply_settings()
        self._refresh_devices(auto_select=address or self._settings.last_device)
        if self._settings_store.last_load_error:
            self._log(self._settings_store.last_load_error, "warn")
        self._log(t("log.ready"), "muted")
        QTimer.singleShot(250, lambda: self._maybe_auto_connect(address))

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_sidebar())

        main = QWidget()
        main.setObjectName("mainArea")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._build_header())

        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        self.overview_page = self._build_overview_page()
        self.features_page = self._build_features_page()
        self.diagnostics_page = self._build_diagnostics_page()
        self.pages.addWidget(self.overview_page)
        self.pages.addWidget(self.features_page)
        self.pages.addWidget(self.diagnostics_page)
        main_layout.addWidget(self.pages, 1)
        main_layout.addWidget(self._build_status_bar())
        outer.addWidget(main, 1)

        self._build_menu()
        self.menuBar().hide()

        self.anc_panel.mode_requested.connect(self._on_anc_mode_requested)
        self.anc_panel.level_requested.connect(self._on_anc_level_requested)
        self.anc_panel.adaptive_requested.connect(
            self._on_anc_adaptive_requested
        )
        self.anc_panel.adaptive_level_requested.connect(
            self._on_anc_adaptive_level_requested
        )
        self.features_panel.action_requested.connect(self._on_feature_action)

        self._select_page("overview")

    # ------------------------------------------------------------------
    # Barra lateral
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 16)
        layout.setSpacing(16)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = QLabel()
        mark.setPixmap(make_brand_mark(30))
        mark.setFixedSize(30, 30)
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel("FreeBuds")
        name.setObjectName("brandName")
        caption = QLabel("CLIENT")
        caption.setObjectName("brandCaption")
        caption_font = QFont(caption.font())
        caption_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        caption.setFont(caption_font)
        brand_text.addWidget(name)
        brand_text.addWidget(caption)
        brand.addLayout(brand_text)
        brand.addStretch(1)
        layout.addLayout(brand)

        nav = QVBoxLayout()
        nav.setSpacing(3)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        for key, _, icon_kind in _NAV_ITEMS:
            button = QPushButton(_page_title(key))
            button.setObjectName("navItem")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(make_nav_icon(icon_kind))
            button.setIconSize(QSize(19, 19))
            button.setFixedHeight(42)
            button.clicked.connect(
                lambda _checked=False, key=key: self._select_page(key)
            )
            self.nav_group.addButton(button)
            self.nav_buttons[key] = button
            nav.addWidget(button)
        layout.addLayout(nav)
        layout.addStretch(1)

        layout.addWidget(self._build_device_panel())

        footer = QHBoxLayout()
        footer.setSpacing(8)
        version = QLabel(f"v{__version__}")
        version.setObjectName("tiny")
        about = QPushButton(t("menu.about"))
        about.setObjectName("linkButton")
        about.setCursor(Qt.CursorShape.PointingHandCursor)
        about.clicked.connect(self._show_about)
        footer.addWidget(version)
        footer.addStretch(1)
        footer.addWidget(about)
        layout.addLayout(footer)
        return sidebar

    def _build_device_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("devicePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(13, 13, 13, 13)
        layout.setSpacing(9)

        label = QLabel(t("device.section"))
        label.setObjectName("devicePanelLabel")
        label_font = QFont(label.font())
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        label.setFont(label_font)
        layout.addWidget(label)

        self.device_combo = FieldComboBox()
        self.device_combo.setToolTip(
            t("device.tooltip")
        )
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        layout.addWidget(self.device_combo)

        row = QHBoxLayout()
        row.setSpacing(7)
        self.scan_button = QPushButton()
        self.scan_button.setObjectName("iconButton")
        self.scan_button.setIcon(make_search_icon())
        self.scan_button.setIconSize(QSize(17, 17))
        self.scan_button.setFixedSize(38, 38)
        self.scan_button.setToolTip(
            t("device.scan_tooltip")
        )
        self.scan_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_button.clicked.connect(self._scan_devices)

        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("iconButton")
        self.refresh_button.setIcon(make_refresh_icon())
        self.refresh_button.setIconSize(QSize(17, 17))
        self.refresh_button.setFixedSize(38, 38)
        self.refresh_button.setToolTip(
            t("device.refresh_tooltip")
        )
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.clicked.connect(lambda: self._refresh_devices())

        row.addWidget(self.scan_button)
        row.addWidget(self.refresh_button)
        row.addStretch(1)
        layout.addLayout(row)

        self.connect_button = QPushButton(t("device.connect"))
        self.connect_button.setObjectName("primary")
        self.connect_button.setMinimumHeight(38)
        self.connect_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_button.clicked.connect(self._toggle_connection)
        layout.addWidget(self.connect_button)

        self.device_hint = QLabel(
            t("device.hint")
        )
        self.device_hint.setObjectName("tiny")
        self.device_hint.setWordWrap(True)
        self.device_hint.hide()
        layout.addWidget(self.device_hint)
        return panel

    # ------------------------------------------------------------------
    # Cabeçalho e páginas
    # ------------------------------------------------------------------
    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("topBar")
        outer = QHBoxLayout(header)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch(1)
        column = QWidget()
        column.setMaximumWidth(1040)
        column.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        outer.addWidget(column, 40)
        outer.addStretch(1)

        layout = QHBoxLayout(column)
        layout.setContentsMargins(32, 20, 32, 8)
        layout.setSpacing(16)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        self.page_title = QLabel(_page_title("overview"))
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel(t("page.overview.subtitle_disconnected"))
        self.page_subtitle.setObjectName("pageSubtitle")
        heading.addWidget(self.page_title)
        heading.addWidget(self.page_subtitle)
        layout.addLayout(heading)
        layout.addStretch(1)

        status = QHBoxLayout()
        status.setSpacing(8)
        self.status_dot = QFrame()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setProperty("state", "off")
        self.connection_pill = QLabel(t("status.disconnected"))
        self.connection_pill.setObjectName("statusPill")
        self.connection_pill.setProperty("state", "off")
        status.addWidget(self.status_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        status.addWidget(self.connection_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(status)
        return header

    def _build_status_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("statusBar")
        bar.setFixedHeight(34)
        outer = QHBoxLayout(bar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch(1)
        column = QWidget()
        column.setMaximumWidth(1040)
        column.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        outer.addWidget(column, 40)
        outer.addStretch(1)

        layout = QHBoxLayout(column)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(12)
        self.footer_status = QLabel(t("status.ready"))
        self.footer_status.setObjectName("statusText")
        meta = QLabel(t("status.spp"))
        meta.setObjectName("statusText")
        layout.addWidget(self.footer_status, 1)
        layout.addWidget(meta)
        return bar

    def _make_page(self) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("page")
        outer = QHBoxLayout(content)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch(1)
        column = QWidget()
        column.setMaximumWidth(1040)
        column.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        outer.addWidget(column, 40)
        outer.addStretch(1)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(32, 10, 32, 36)
        layout.setSpacing(24)
        scroll.setWidget(content)
        return scroll, layout

    def _build_overview_page(self) -> QScrollArea:
        scroll, column = self._make_page()
        column.addWidget(self._build_hero())

        column.addWidget(make_section_label(t("sections.sound")))
        self.anc_panel = AncPanel()
        column.addWidget(self.anc_panel)

        column.addWidget(make_section_label(t("sections.shortcuts")))
        shortcuts = QGridLayout()
        shortcuts.setHorizontalSpacing(20)
        shortcuts.setVerticalSpacing(16)
        shortcuts.setColumnStretch(0, 1)
        shortcuts.setColumnStretch(1, 1)
        self.quick_tiles: dict[str, QuickTile] = {}
        specs = (
            ("sound", t("audio.sound_title"), "sound", "audio"),
            ("spatial", t("audio.spatial_title"), "spatial", "audio"),
            ("head", t("gestures.head_title"), "head_control", "gestures"),
            ("wear", t("connection.wear_title"), "wear_detection", "connection"),
        )
        for index, (key, title, kind, page_key) in enumerate(specs):
            tile = QuickTile(title, "—", kind)
            tile.clicked.connect(
                lambda key=page_key: self._select_page(key)
            )
            self.quick_tiles[key] = tile
            shortcuts.addWidget(tile, index // 2, index % 2)
        column.addLayout(shortcuts)

        column.addWidget(make_section_label(t("sections.battery")))
        self.battery_panel = BatteryOverview()
        column.addWidget(self.battery_panel)
        column.addStretch(1)
        return scroll

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumHeight(282)
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(34, 30, 18, 26)
        layout.setSpacing(10)

        info = QVBoxLayout()
        info.setSpacing(5)
        self.hero_eyebrow = QLabel(t("hero.eyebrow"))
        self.hero_eyebrow.setObjectName("heroEyebrow")
        eyebrow_font = QFont(self.hero_eyebrow.font())
        eyebrow_font.setWeight(QFont.Weight.DemiBold)
        eyebrow_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        self.hero_eyebrow.setFont(eyebrow_font)
        self.hero_title = QLabel(t("hero.title_default"))
        self.hero_title.setObjectName("heroTitle")
        self.hero_subtitle = QLabel(t("hero.subtitle_disconnected"))
        self.hero_subtitle.setObjectName("heroSubtitle")
        info.addWidget(self.hero_eyebrow)
        info.addWidget(self.hero_title)
        info.addWidget(self.hero_subtitle)
        info.addStretch(1)

        battery_row = QHBoxLayout()
        battery_row.setSpacing(14)
        self.hero_battery_box = QWidget()
        self.hero_battery_box.setLayout(battery_row)
        self.hero_battery = QLabel("—")
        self.hero_battery.setObjectName("heroBattery")
        battery_row.addWidget(self.hero_battery, 0, Qt.AlignmentFlag.AlignBottom)
        battery_text = QVBoxLayout()
        battery_text.setSpacing(2)
        self.hero_battery_detail = QLabel(t("hero.battery"))
        self.hero_battery_detail.setObjectName("heroBatteryDetail")
        self.hero_meta = QLabel(t("hero.no_session"))
        self.hero_meta.setObjectName("tiny")
        self.hero_charging = QLabel(t("hero.charging"))
        self.hero_charging.setObjectName("chargingBadge")
        self.hero_charging.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.hero_charging.hide()
        battery_text.addStretch(1)
        battery_text.addWidget(self.hero_battery_detail)
        battery_text.addWidget(self.hero_meta)
        battery_text.addWidget(
            self.hero_charging, 0, Qt.AlignmentFlag.AlignLeft
        )
        battery_row.addLayout(battery_text, 1)
        self.hero_battery_box.hide()
        info.addWidget(self.hero_battery_box)

        layout.addLayout(info, 5)
        self.product_hero = ProductHero(
            initial_color=self._settings.earbud_color
        )
        self.product_hero.color_changed.connect(self._on_earbud_color_changed)
        layout.addWidget(self.product_hero, 6)
        return hero

    def _build_features_page(self) -> QScrollArea:
        scroll, column = self._make_page()
        self.features_panel = FeaturesPanel()
        column.addWidget(self.features_panel)
        column.addStretch(1)
        return scroll

    def _build_diagnostics_page(self) -> QScrollArea:
        scroll, column = self._make_page()

        column.addWidget(make_section_label(t("sections.activity")))
        activity = QFrame()
        activity.setObjectName("card")
        activity_layout = QVBoxLayout(activity)
        activity_layout.setContentsMargins(22, 18, 22, 18)
        activity_layout.setSpacing(12)
        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel(t("activity.title"))
        title.setObjectName("cardTitle")
        self.toggle_log_button = QPushButton(t("activity.collapse"))
        self.toggle_log_button.setObjectName("ghost")
        self.toggle_log_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_log_button.clicked.connect(self._toggle_log_view)
        clear_button = QPushButton(t("activity.clear"))
        clear_button.setObjectName("ghost")
        clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_button.clicked.connect(self._clear_log)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.toggle_log_button)
        header.addWidget(clear_button)
        activity_layout.addLayout(header)
        self.log_view = ActivityLog()
        activity_layout.addWidget(self.log_view)
        column.addWidget(activity)

        column.addWidget(make_section_label(t("sections.device")))
        self.details_panel = DeviceDetailsPanel()
        column.addWidget(self.details_panel)

        column.addWidget(make_section_label(t("sections.preferences")))
        column.addWidget(self._build_preferences_card())
        column.addStretch(1)
        return scroll

    def _build_preferences_card(self) -> FeatureCard:
        card = FeatureCard(t("preferences.title"), t("preferences.badge"))
        self.interval_combo = FieldComboBox()
        for seconds, label in (
            (15, "15 s"),
            (30, "30 s"),
            (60, "60 s"),
            (120, "120 s"),
        ):
            self.interval_combo.addItem(label, seconds)
        self.interval_combo.setToolTip(
            t("preferences.poll_subtitle")
        )
        self.interval_combo.setFixedWidth(132)
        card.body.addWidget(
            FeatureRow(
                t("preferences.poll_title"),
                t("preferences.poll_subtitle"),
                self.interval_combo,
            )
        )

        self.close_tray_check = ToggleSwitch()
        self.close_tray_check.setToolTip(
            t("preferences.tray_subtitle")
        )
        self.close_tray_row = FeatureRow(
            t("preferences.tray_title"),
            t("preferences.tray_subtitle"),
            self.close_tray_check,
        )
        card.body.addWidget(self.close_tray_row)

        self.language_combo = FieldComboBox()
        for code, name in language_options():
            self.language_combo.addItem(name, code)
        self.language_combo.setToolTip(t("preferences.language_subtitle"))
        self.language_combo.setFixedWidth(145)
        card.body.addWidget(
            FeatureRow(
                t("preferences.language_title"),
                t("preferences.language_subtitle"),
                self.language_combo,
            )
        )

        self.refresh_now_button = QPushButton(t("preferences.refresh_title"))
        self.refresh_now_button.setObjectName("ghost")
        self.refresh_now_button.setIcon(make_refresh_icon(16))
        self.refresh_now_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_now_button.clicked.connect(self._refresh_now)
        card.body.addWidget(
            FeatureRow(
                t("preferences.refresh_title"),
                t("preferences.refresh_subtitle"),
                self.refresh_now_button,
            )
        )
        return card

    def _build_menu(self) -> None:
        self.menuBar().setNativeMenuBar(False)
        file_menu = self.menuBar().addMenu(t("menu.file"))

        self.refresh_action = QAction(t("menu.refresh"), self)
        self.refresh_action.setShortcut("Ctrl+R")
        self.refresh_action.triggered.connect(self._refresh_now)
        file_menu.addAction(self.refresh_action)

        self.scan_action = QAction(t("menu.scan"), self)
        self.scan_action.triggered.connect(self._scan_devices)
        file_menu.addAction(self.scan_action)
        file_menu.addSeparator()

        self.quit_action = QAction(t("menu.quit"), self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.quit_application)
        file_menu.addAction(self.quit_action)

        help_menu = self.menuBar().addMenu(t("menu.help"))
        about_action = QAction(t("menu.about"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------
    def _select_page(self, key: str) -> None:
        if key not in _PAGE_TITLES:
            return
        self._current_page = key
        if key in _FEATURE_SECTIONS:
            self.pages.setCurrentWidget(self.features_page)
            self.features_panel.select_section(_FEATURE_SECTIONS[key])
        elif key == "diagnostics":
            self.pages.setCurrentWidget(self.diagnostics_page)
        else:
            self.pages.setCurrentWidget(self.overview_page)
        button = self.nav_buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)
        self.page_title.setText(_page_title(key))
        self._update_page_subtitle()

    def _update_page_subtitle(self) -> None:
        name = (self._last_device_name or "FreeBuds").removeprefix("HUAWEI ").strip()
        connected = self._session_connected
        if self._current_page == "overview":
            if connected:
                self.page_subtitle.setText(
                    t("page.overview.subtitle_connected", device=name)
                )
            elif self._worker is not None:
                self.page_subtitle.setText(t("page.overview.subtitle_connecting"))
            else:
                self.page_subtitle.setText(t("page.overview.subtitle_disconnected"))
        elif self._current_page == "diagnostics":
            self.page_subtitle.setText(
                t("page.diagnostics.subtitle")
            )
        elif connected:
            self.page_subtitle.setText(t("page.features.subtitle_connected", device=name))
        else:
            self.page_subtitle.setText(t("page.features.subtitle_disconnected"))

    # ------------------------------------------------------------------
    # Estado, listas e conexão
    # ------------------------------------------------------------------
    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.close_tray_check.setChecked(False)
            self.close_tray_check.setEnabled(False)
            self.close_tray_check.hide()
            self.close_tray_row.hide()
            return
        self._tray = TrayController(
            self,
            on_refresh=self._refresh_now,
            on_quit=self.quit_application,
            parent=self,
        )
        self._tray.show()
        self._tray.update(None, None, connected=False)
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(False)

    def _apply_settings(self) -> None:
        self._select_interval(self._settings.poll_interval)
        self.close_tray_check.setChecked(self._settings.close_to_tray)
        self._select_language(self._settings.language)
        self.interval_combo.currentIndexChanged.connect(
            self._on_interval_changed
        )
        self.close_tray_check.toggled.connect(
            self._on_close_to_tray_changed
        )
        self.language_combo.currentIndexChanged.connect(
            self._on_language_changed
        )

    def _select_language(self, language: str) -> None:
        for index in range(self.language_combo.count()):
            if self.language_combo.itemData(index) == language:
                self.language_combo.setCurrentIndex(index)
                return

    def _select_interval(self, seconds: float) -> None:
        for index in range(self.interval_combo.count()):
            value = self.interval_combo.itemData(index)
            if isinstance(value, int) and abs(value - seconds) < 0.5:
                self.interval_combo.setCurrentIndex(index)
                return
        self.interval_combo.addItem(f"{seconds:g} s", int(seconds))
        self.interval_combo.setCurrentIndex(self.interval_combo.count() - 1)

    # ------------------------------------------------------------------
    # Lista de dispositivos
    # ------------------------------------------------------------------
    def _refresh_devices(self, auto_select: str | None = None) -> None:
        if self._worker is not None or self._scan_worker is not None:
            return
        try:
            devices = enumerate_devices()
        except FreeBudsError as exc:
            self._devices = []
            self._populate_devices([], auto_select)
            self._log(t("log.bluetooth_unavailable", error=exc), "error")
            self.footer_status.setText(t("device.footer_unavailable"))
            self._update_controls()
            return
        except Exception as exc:  # noqa: BLE001 - limite da UI
            self._devices = []
            self._populate_devices([], auto_select)
            self._log(t("log.list_error", error=exc), "error")
            self._update_controls()
            return

        self._devices = devices
        self._populate_devices(devices, auto_select)
        huawei = sum(
            1 for device in devices if is_huawei_device_name(device.name)
        )
        if devices:
            self._log(
                t("log.devices_found", count=len(devices), huawei=huawei),
                "muted",
            )
            self.footer_status.setText(
                t("device.available", count=len(devices))
            )
        else:
            self._log(
                t("log.no_paired"),
                "warn",
            )
            self.footer_status.setText(t("device.footer_none"))
        self._update_controls()

    def _populate_devices(
        self, devices: list[BluetoothDevice], selected: str | None = None
    ) -> None:
        current = selected or self._selected_address()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        if not devices:
            self.device_combo.addItem(
                t("device.none"), None
            )
            self.device_combo.setEnabled(False)
            self.device_combo.blockSignals(False)
            self._update_controls()
            return

        ordered = sorted(
            devices,
            key=lambda device: (
                not device.connected,
                not is_huawei_device_name(device.name),
                not device.authenticated,
                (device.name or "").casefold(),
                device.address,
            ),
        )
        for device in ordered:
            label = device.display_name
            if is_huawei_device_name(device.name):
                label = label.removeprefix("HUAWEI ").strip()
            self.device_combo.addItem(label, device.address)

        target = current or self._settings.last_device
        index = self._find_device_index(target)
        if index < 0:
            index = 0
            for candidate, device in enumerate(ordered):
                if is_huawei_device_name(device.name):
                    index = candidate
                    break
        self.device_combo.setCurrentIndex(index)
        self.device_combo.setEnabled(True)
        self.device_combo.blockSignals(False)
        self._update_controls()

    def _find_device_index(self, address: str | None) -> int:
        if not address:
            return -1
        for index in range(self.device_combo.count()):
            if self.device_combo.itemData(index) == address:
                return index
        return -1

    def _selected_address(self) -> str | None:
        value = self.device_combo.currentData()
        return value if isinstance(value, str) else None

    def _selected_device(self) -> BluetoothDevice | None:
        address = self._selected_address()
        if address is None:
            return None
        for device in self._devices:
            if device.address == address:
                return device
        return None

    def _maybe_auto_connect(self, explicit_address: str | None = None) -> None:
        if self._worker is not None:
            return
        target = explicit_address or self._settings.last_device
        if not target:
            return
        index = self._find_device_index(target)
        if index < 0:
            return
        self.device_combo.setCurrentIndex(index)
        device = self._selected_device()
        if explicit_address is not None or (device is not None and device.connected):
            QTimer.singleShot(150, self._connect_selected)

    # ------------------------------------------------------------------
    # Conexão e polling
    # ------------------------------------------------------------------
    def _toggle_connection(self) -> None:
        if self._worker is not None:
            self._stop_worker()
        else:
            self._connect_selected()

    def _connect_selected(self) -> None:
        if self._worker is not None:
            return
        address = self._selected_address()
        if address is None:
            self._log("Nenhum dispositivo selecionado.", "warn")
            return
        device = self._selected_device()
        name = device.display_name if device is not None else address
        saved_channel = self._settings.last_channels.get(address)
        try:
            channels = resolve_channels(
                saved_channel=saved_channel,
                settings_channels=self._settings.channels,
            )
            worker = DeviceWorker(
                address,
                channels,
                poll_interval=self._settings.poll_interval,
                connect_timeout=self._settings.connect_timeout,
                response_timeout=self._settings.response_timeout,
                parent=self,
            )
        except (FreeBudsError, ValueError) as exc:
            self._log(t("log.connection_failed", error=exc), "error")
            return

        self._last_connection = None
        self._last_snapshot = None
        self._last_battery_key = None
        self._last_anc_key = None
        self._last_error = None
        self._last_warnings.clear()
        self._manual_stop = False
        self._session_connected = False
        self._last_device_name = name
        self._worker = worker
        worker.connected.connect(self._on_connected)
        worker.snapshot_ready.connect(self._on_snapshot)
        worker.failed.connect(self._on_failed)
        worker.action_failed.connect(self._on_action_failed)
        worker.action_done.connect(self._on_action_done)
        worker.finished.connect(self._on_worker_finished)

        self._set_status(t("status.connecting"), "connecting")
        self.footer_status.setText(t("device.footer_connecting", name=name))
        self._log(
            t(
                "log.connection_started",
                name=name,
                channels=", ".join(map(str, channels)),
            ),
            "info",
        )
        self._update_hero()
        self._update_controls()
        worker.start()

    def _stop_worker(self) -> None:
        worker = self._worker
        if worker is None:
            return
        self._manual_stop = True
        self._set_status(t("status.disconnecting"), "warning")
        self.footer_status.setText(t("device.footer_stopping"))
        self._log(t("log.disconnecting"), "muted")
        self.connect_button.setEnabled(False)
        self.connect_button.setText(t("status.disconnecting"))
        worker.stop()

    def _on_connected(self, connection: ConnectionInfo) -> None:
        if self.sender() is not self._worker:
            return
        self._last_connection = connection
        self._session_connected = True
        self._last_error = None
        device = self._selected_device()
        if device is not None:
            self._last_device_name = device.display_name
        elif connection.info.model:
            self._last_device_name = connection.info.model

        try:
            self._settings_store.remember_channel(
                self._settings, connection.address, connection.channel
            )
        except OSError as exc:
            self._log(t("log.settings_save_error", error=exc), "warn")

        self.details_panel.update_info(connection.info, connection.channel)
        self.features_panel.update_advanced(None)
        self._update_quick_tiles(None)
        self._set_status(t("status.connected"), "connected")
        self.footer_status.setText(
            t(
                "device.footer_connected",
                channel=connection.channel,
                seconds=f"{self._settings.poll_interval:g}",
            )
        )
        self._log(
            t(
                "log.connected",
                name=self._last_device_name or connection.address,
                channel=connection.channel,
            ),
            "ok",
        )
        self._update_hero()
        self._update_controls()
        self._update_tray()

    def _on_snapshot(self, snapshot: DeviceSnapshot) -> None:
        if self.sender() is not self._worker:
            return
        self._last_snapshot = snapshot
        self._session_connected = True
        self._last_error = None
        self._anc_busy = False
        for frame in snapshot.notifications:
            self._handle_notification(frame)
        self.battery_panel.update_battery(snapshot.battery)
        self.anc_panel.update_anc(snapshot.anc)
        self.features_panel.update_advanced(snapshot.advanced)
        self._update_quick_tiles(snapshot.advanced)
        self.details_panel.update_info(
            snapshot.info, snapshot.channel, snapshot.timestamp
        )
        self._update_hero()
        self._update_page_subtitle()
        self.footer_status.setText(
            t(
                "device.footer_snapshot",
                channel=snapshot.channel,
                time=snapshot.timestamp.strftime("%H:%M:%S"),
            )
        )

        battery_key = _battery_key(snapshot.battery)
        if battery_key != self._last_battery_key:
            self._last_battery_key = battery_key
            self._log(
                t("log.battery", summary=_battery_summary(snapshot.battery)),
                "info",
            )

        anc_key = _anc_key(snapshot.anc)
        if anc_key != self._last_anc_key:
            self._last_anc_key = anc_key
            self._log(t("log.anc", summary=_anc_summary(snapshot.anc)), "ok")

        for warning in snapshot.warnings:
            if warning not in self._last_warnings:
                self._last_warnings.add(warning)
                self._log(warning, "warn")
        if snapshot.parser_issues:
            issue_text = t(
                "log.parser_ignored",
                count=len(snapshot.parser_issues),
            )
            if issue_text not in self._last_warnings:
                self._last_warnings.add(issue_text)
                self._log(issue_text, "warn")

        self._update_tray()
        self._update_controls()

    def _handle_notification(self, frame: HuaweiFrame) -> None:
        """Registra um push espontâneo; o snapshot já traz o estado mais novo."""

        if frame.command == CMD_ANC:
            anc = decode_anc(frame.parameters)
            if anc.mode_code is None and anc.level_code is None:
                self._log_notification_raw(frame)
                return
            self._last_anc_key = _anc_key(anc)
            self._log(t("log.anc_notify", summary=_anc_summary(anc)), "ok")
            return

        if frame.command == CMD_BATTERY_NOTIFY:
            battery = decode_battery(frame.parameters)
            if (
                battery.global_level is None
                and battery.left is None
                and battery.right is None
                and battery.case is None
                and battery.charging_flags is None
            ):
                self._log_notification_raw(frame)
                return
            self._last_battery_key = _battery_key(battery)
            self._log(
                t("log.battery_notify", summary=_battery_summary(battery)),
                "info",
            )
            return

        self._log_notification_raw(frame)

    def _log_notification_raw(self, frame: HuaweiFrame) -> None:
        signature = (
            frame.command,
            tuple((key, bytes(value)) for key, value in sorted(frame.parameters.items())),
        )
        if signature in self._seen_raw_notifications:
            return
        if len(self._seen_raw_notifications) < 256:
            self._seen_raw_notifications.add(signature)
        parts = [
            f"{key}={value.hex(' ').upper()}"
            for key, value in sorted(frame.parameters.items())
        ]
        raw = ", ".join(parts)
        if len(raw) > 160:
            raw = raw[:157] + "..."
        self._log(
            t(
                "log.raw_notification",
                command=frame.command.hex(" ").upper(),
                raw=raw or t("log.raw_empty"),
            ),
            "muted",
        )

    def _on_failed(self, message: str) -> None:
        if self.sender() is not self._worker:
            return
        self._session_connected = False
        self._anc_busy = False
        if message != self._last_error:
            self._last_error = message
            self._log(message, "error")
        self._set_status(t("status.reconnecting"), "warning")
        self.footer_status.setText(t("device.footer_connection_failed"))
        self._update_hero()
        self._update_quick_tiles(None)
        self._update_tray()
        self._update_controls()

    def _on_action_failed(self, message: str) -> None:
        if self.sender() is not self._worker:
            return
        self._anc_busy = False
        self._log(t("log.action_failed", error=message), "error")
        if self._last_snapshot is not None:
            self.anc_panel.update_anc(self._last_snapshot.anc)
            self.features_panel.update_advanced(self._last_snapshot.advanced)
            self._update_quick_tiles(self._last_snapshot.advanced)
        self._update_controls()

    def _on_action_done(self, label: str) -> None:
        if self.sender() is not self._worker:
            return
        self._log(t("log.action_done", label=label), "ok")

    def _on_worker_finished(self) -> None:
        worker = self.sender()
        if worker is not self._worker:
            return
        self._worker = None
        self._session_connected = False
        self._anc_busy = False
        self._set_status(t("status.disconnected"), "off")
        self.footer_status.setText(
            t("device.footer_session_ended")
            if self._manual_stop
            else t("device.footer_disconnected")
        )
        self._log(
            t("log.session_ended")
            if self._manual_stop
            else t("log.connection_ended"),
            "muted",
        )
        self._last_snapshot = None
        self._last_connection = None
        self._last_battery_key = None
        self._last_anc_key = None
        self._last_warnings.clear()
        self.battery_panel.update_battery(None)
        self.anc_panel.update_anc(None)
        self.features_panel.update_advanced(None)
        self._update_quick_tiles(None)
        self.details_panel.update_info(None, None)
        self._update_hero()
        self._update_tray()
        self._update_controls()
        if isinstance(worker, QThread):
            worker.deleteLater()

    def _refresh_now(self) -> None:
        if self._worker is None:
            self._refresh_devices()
            return
        self._worker.request_refresh()
        self._log(t("log.refresh_requested"), "muted")

    # ------------------------------------------------------------------
    # Ações de ANC e recursos
    # ------------------------------------------------------------------
    def _on_anc_mode_requested(self, mode_code: int) -> None:
        if self._worker is None or self._anc_busy:
            return
        anc = self._last_snapshot.anc if self._last_snapshot else None
        if anc is None:
            return
        if mode_code == 2:
            if anc.mode_code == 2 and anc.level_code == 2:
                return
        elif anc.mode_code == mode_code:
            return
        self._anc_busy = True
        self._update_controls()
        mode_name = {0: "normal", 1: "cancellation", 2: "awareness"}.get(mode_code, "")
        label = option_label("anc_mode", mode_name, mode_name or f"modo {mode_code}")
        self._log(t("log.anc_mode_changing", label=label), "info")
        if mode_code == 2:
            self._worker.set_anc_level(2, 2)
        else:
            self._worker.set_anc_mode(mode_code)

    def _on_anc_level_requested(self, level_code: int) -> None:
        if self._worker is None or self._anc_busy:
            return
        anc = self._last_snapshot.anc if self._last_snapshot else None
        if anc is None or anc.mode_code not in (1, 2):
            return
        if anc.level_code == level_code:
            return
        self._anc_busy = True
        self._update_controls()
        self._log(t("log.anc_level_changing", code=level_code), "info")
        self._worker.set_anc_level(anc.mode_code, level_code)

    def _on_anc_adaptive_requested(self) -> None:
        if self._worker is None or self._anc_busy:
            return
        anc = self._last_snapshot.anc if self._last_snapshot else None
        if anc is None:
            return
        if anc.mode_code == 2 and anc.level_code == 4:
            return
        self._anc_busy = True
        self._update_controls()
        self._log(t("log.anc_adaptive_activating"), "info")
        self._worker.set_anc_level(2, 4)

    def _on_anc_adaptive_level_requested(self, level_code: int) -> None:
        if self._worker is None or self._anc_busy:
            return
        anc = self._last_snapshot.anc if self._last_snapshot else None
        if anc is None or anc.mode_code != 2 or anc.level_code != 4:
            return
        if anc.adaptive_level == level_code:
            return
        self._anc_busy = True
        self._update_controls()
        self._log(
            t("log.anc_adaptive_level_changing", level=level_code + 1, total=11),
            "info",
        )
        self._worker.set_anc_adaptive_level(level_code)

    def _on_feature_action(self, action: str, value: object) -> None:
        worker = self._worker
        if worker is None or self._anc_busy or not self._session_connected:
            return
        self._anc_busy = True
        self._update_controls()
        self._log(t("log.action_applied", action=_feature_action_label(action)), "info")
        if action == "sound_profile":
            worker.set_sound_profile(int(value))
        elif action == "spatial_mode":
            worker.set_spatial_mode(int(value))
        elif action == "adaptive_volume":
            worker.set_adaptive_volume(bool(value))
        elif action == "conversation_awareness":
            worker.set_conversation_awareness(bool(value))
        elif action == "one_earbud_anc":
            worker.set_one_earbud_anc(bool(value))
        elif action == "head_control":
            worker.set_head_control(bool(value))
        elif action == "head_action":
            field, action_value = value
            worker.set_head_action(int(field), int(action_value))
        elif action == "wear_detection":
            worker.set_wear_detection(bool(value))
        elif action == "sound_quality":
            worker.set_sound_quality(int(value))
        elif action == "low_latency":
            worker.set_low_latency(bool(value))
        elif action == "press_hold":
            side, action_value = value
            worker.set_press_hold(str(side), int(action_value))
        elif action == "pinch_hold":
            side, action_value = value
            worker.set_pinch_hold(str(side), int(action_value))
        elif action == "double_tap":
            left, right = value
            worker.set_double_tap(int(left), int(right))
        elif action == "triple_tap":
            side, action_value = value
            worker.set_triple_tap(str(side), int(action_value))
        else:
            self._anc_busy = False
            self._update_controls()
            self._log(t("log.action_unsupported", action=action), "warn")

    # ------------------------------------------------------------------
    # Atualização visual
    # ------------------------------------------------------------------
    def _update_hero(self) -> None:
        snapshot = self._last_snapshot
        if not self._session_connected and snapshot is None:
            self.hero_title.setText(t("hero.title_default"))
            self.hero_subtitle.setText(t("hero.subtitle_disconnected"))
            self.hero_battery.setText("—")
            self.hero_battery.setStyleSheet("")
            self.hero_battery_detail.setText(t("hero.battery"))
            self.hero_meta.setText(t("hero.no_session"))
            self.hero_charging.hide()
            self.hero_battery_box.hide()
            self.product_hero.set_battery(None, None, False)
            return

        name = self._last_device_name or (snapshot.info.model if snapshot else None)
        display = (name or t("hero.title_default")).removeprefix("HUAWEI ").strip()
        self.hero_title.setText(display)
        if snapshot is not None:
            self.hero_subtitle.setText(
                t("hero.subtitle_connected", channel=snapshot.channel)
            )
            self.hero_meta.setText(
                t("hero.updated", time=snapshot.timestamp.strftime("%H:%M:%S"))
            )
        else:
            self.hero_subtitle.setText(t("hero.subtitle_awaiting"))
            self.hero_meta.setText(t("hero.awaiting"))

        battery = snapshot.battery if snapshot else None
        if battery is None:
            self.hero_battery.setText("—")
            self.hero_battery.setStyleSheet("")
            self.hero_battery_detail.setText(t("hero.battery"))
            self.hero_charging.hide()
            self.hero_battery_box.hide()
            self.product_hero.set_battery(None, None, False)
            return

        self.hero_battery_box.show()
        level = battery.global_level
        if level is None:
            values = [
                value
                for value in (battery.left, battery.right, battery.case)
                if value is not None
            ]
            level = min(values) if values else None
        self.hero_battery.setText(f"{level}%" if level is not None else "—")
        self.hero_battery.setStyleSheet("")

        details: list[str] = []
        if battery.left is not None:
            details.append(t("battery.left_short", value=battery.left))
        if battery.right is not None:
            details.append(t("battery.right_short", value=battery.right))
        if battery.case is not None:
            details.append(t("battery.case_short", value=battery.case))
        self.hero_battery_detail.setText(
            "  ·  ".join(details) if details else t("hero.battery")
        )
        self.hero_charging.setVisible(battery.charging is True)

        buds_level = battery.global_level
        if buds_level is None and (battery.left is not None or battery.right is not None):
            valid = [val for val in (battery.left, battery.right) if val is not None]
            buds_level = int(sum(valid) / len(valid))
        self.product_hero.set_battery(
            buds_level, battery.case, battery.charging is True
        )

    def _update_quick_tiles(self, advanced: object | None) -> None:
        data = advanced
        if data is None and self._last_snapshot is not None:
            data = self._last_snapshot.advanced
        if data is None:
            for tile in self.quick_tiles.values():
                tile.set_value("—")
            return
        profile_id = getattr(data, "sound_profile_id", None)
        profile_fallback = SOUND_PROFILES.get(
            profile_id if profile_id is not None else -1, t("common.none")
        )
        profile = option_label("sound_profile", profile_id, profile_fallback)
        custom = getattr(data, "custom_name", None)
        if profile == t("options.sound_profile.custom") and custom:
            profile = t("audio.custom_profile", name=custom)
        spatial_id = getattr(data, "spatial_mode", None)
        spatial_fallback = SPATIAL_MODES.get(
            spatial_id if spatial_id is not None else -1, t("common.none")
        )
        spatial = option_label("spatial_mode", spatial_id, spatial_fallback)
        self.quick_tiles["sound"].set_value(profile or "—")
        self.quick_tiles["spatial"].set_value(spatial)
        self.quick_tiles["head"].set_value(
            _on_off(
                getattr(data, "head_control", None),
                t("common.on"),
                t("common.off"),
            )
        )
        self.quick_tiles["wear"].set_value(
            _on_off(
                getattr(data, "wear_detection", None),
                t("common.active"),
                t("common.inactive"),
            )
        )

    # ------------------------------------------------------------------
    # Varredura
    # ------------------------------------------------------------------
    def _scan_devices(self) -> None:
        if self._worker is not None or self._scan_worker is not None:
            return
        worker = ScanWorker(seconds=8.0, parent=self)
        self._scan_worker = worker
        worker.devices_found.connect(self._on_scan_found)
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(self._on_scan_finished)
        self._log(t("log.scan_started"), "info")
        self.footer_status.setText(t("device.footer_scanning"))
        self._update_controls()
        worker.start()

    def _on_scan_found(self, devices: list[BluetoothDevice]) -> None:
        self._devices = list(devices)
        self._populate_devices(self._devices)
        huawei = sum(
            1 for device in self._devices if is_huawei_device_name(device.name)
        )
        self._log(
            t("log.scan_done", count=len(self._devices), huawei=huawei),
            "ok" if self._devices else "warn",
        )
        self.footer_status.setText(
            t("device.footer_scan_done", count=len(self._devices))
        )
        self._update_controls()

    def _on_scan_failed(self, message: str) -> None:
        self._log(t("log.scan_failed", error=message), "error")
        self.footer_status.setText(t("device.footer_scan_failed"))

    def _on_scan_finished(self) -> None:
        worker = self._scan_worker
        self._scan_worker = None
        if worker is not None:
            worker.deleteLater()
        self._update_controls()

    # ------------------------------------------------------------------
    # Estado e configurações
    # ------------------------------------------------------------------
    def _update_controls(self) -> None:
        connected = self._worker is not None
        scanning = self._scan_worker is not None
        has_devices = bool(self._devices)
        self.device_combo.setEnabled(has_devices and not connected)
        self.scan_button.setEnabled(not connected and not scanning)
        self.refresh_button.setEnabled(not connected and not scanning)
        self.scan_action.setEnabled(not connected and not scanning)
        self.connect_button.setEnabled(
            (connected and not self._manual_stop)
            or (
                not connected
                and has_devices
                and self._selected_address() is not None
            )
        )
        if connected and self._manual_stop:
            self.connect_button.setText(t("status.disconnecting"))
        else:
            self.connect_button.setText(
                t("device.disconnect") if connected else t("device.connect")
            )
        self.connect_button.setObjectName("danger" if connected else "primary")
        self._restyle(self.connect_button)
        self.refresh_now_button.setEnabled(connected and not self._manual_stop)
        self.interval_combo.setEnabled(True)
        anc_ready = (
            connected
            and self._session_connected
            and not self._anc_busy
            and self._last_snapshot is not None
        )
        self.anc_panel.set_enabled(anc_ready)
        self.features_panel.set_enabled(
            anc_ready and self._last_snapshot.advanced is not None
        )
        self._update_page_subtitle()

    def _set_status(self, text: str, state: str) -> None:
        self.connection_pill.setText(text)
        self.connection_pill.setProperty("state", state)
        self.status_dot.setProperty("state", state)
        self._restyle(self.connection_pill)
        self._restyle(self.status_dot)
        self._update_page_subtitle()

    @staticmethod
    def _restyle(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _on_device_changed(self, _index: int) -> None:
        self._update_controls()

    def _on_interval_changed(self, _index: int) -> None:
        value = self.interval_combo.currentData()
        if not isinstance(value, int):
            return
        self._settings.poll_interval = float(value)
        if self._worker is not None:
            self._worker.set_poll_interval(float(value))
        self._save_settings()
        self._log(t("log.interval", seconds=value), "muted")

    def _on_close_to_tray_changed(self, checked: bool) -> None:
        self._settings.close_to_tray = checked
        self._save_settings()

    def _on_earbud_color_changed(self, color: str) -> None:
        if self._settings.earbud_color != color:
            self._settings.earbud_color = color
            self._save_settings()

    def _on_language_changed(self, index: int) -> None:
        code = self.language_combo.itemData(index)
        if isinstance(code, str) and code != self._settings.language:
            self._settings.language = code
            self._save_settings()
            set_language(code)
            QMessageBox.information(
                self,
                t("preferences.restart_title"),
                t("preferences.restart_body"),
            )

    def _save_settings(self) -> None:
        try:
            self._settings_store.save(self._settings)
        except OSError as exc:
            self._log(t("log.settings_save_error", error=exc), "warn")

    def _clear_log(self) -> None:
        self.log_view.clear()

    def _toggle_log_view(self) -> None:
        visible = not self.log_view.isVisible()
        self.log_view.setVisible(visible)
        self.toggle_log_button.setText(
            t("activity.collapse") if visible else t("activity.expand")
        )

    def _log(self, message: str, level: str = "info") -> None:
        self.log_view.log(message, level)

    def _update_tray(self) -> None:
        if self._tray is not None:
            self._tray.update(
                self._last_snapshot,
                self._last_device_name,
                connected=self._session_connected,
            )

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            t("about.title"),
            t("about.body", version=__version__),
        )

    # ------------------------------------------------------------------
    # Encerramento
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._save_settings()
        worker = self._worker
        if worker is not None:
            worker.stop()
            worker.wait(12000)
            self._worker = None
        scan_worker = self._scan_worker
        if scan_worker is not None:
            scan_worker.wait(12000)
            self._scan_worker = None
        if self._tray is not None:
            self._tray.hide()
        self._closing = False

    def quit_application(self) -> None:
        self._force_quit = True
        self.shutdown()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        if (
            not self._force_quit
            and self._tray is not None
            and self.close_tray_check.isChecked()
        ):
            event.ignore()
            self.hide()
            if not self._tray_notice_shown:
                self._tray.notify(
                    t("app.name"),
                    t("tray.notify_body"),
                )
                self._tray_notice_shown = True
            return
        self._force_quit = True
        self.shutdown()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            app.quit()


_FEATURE_ACTION_LABELS = {
    "sound_profile": "perfil HUAWEI Sound",
    "spatial_mode": "áudio espacial",
    "adaptive_volume": "volume adaptável",
    "conversation_awareness": "reconhecimento de conversa",
    "one_earbud_anc": "ANC com um fone",
    "head_control": "controle de cabeça",
    "head_action": "movimento de cabeça",
    "wear_detection": "detecção de uso",
    "sound_quality": "qualidade do som",
    "low_latency": "latência baixa",
    "press_hold": "gesto de pressionar e segurar",
    "pinch_hold": "gesto de pinçar e segurar",
    "double_tap": "toque duplo",
    "triple_tap": "toque triplo",
}


def _feature_action_label(action: str) -> str:
    return t(f"actions.{action}", default=_FEATURE_ACTION_LABELS.get(action, action))
