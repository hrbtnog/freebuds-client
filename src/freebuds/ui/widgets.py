"""Widgets da interface do FreeBuds Client, no visual do HarmonyOS.

O desenho segue o app HUAWEI Audio Connect: cartões grandes, poucos níveis de
tipografia, ícones circulares coloridos e controles agrupados em linhas com
separadores finos.
"""

from __future__ import annotations

import html
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QRegion,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStyle,
    QStyledItemDelegate,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.commands import (
    DOUBLE_TAP_ACTIONS,
    HEAD_NOD_ACTIONS,
    HEAD_SHAKE_ACTIONS,
    PINCH_HOLD_ACTIONS,
    PRESS_HOLD_ACTIONS,
    SOUND_PROFILES,
    SPATIAL_EFFECTS,
    SPATIAL_MODES,
    SWIPE_ACTIONS,
    TRIPLE_TAP_ACTIONS,
)
from ..core.models import AdvancedSettings, AncState, BatteryState, DeviceInfo
from .icons import (
    make_card_avatar,
    make_chevron_icon,
    make_noise_icon,
)
from .i18n import option_label, t
from .svg_icons import feature_pixmap, make_spatial_icon
from .theme import (
    ACCENT,
    ACCENT_TEXT,
    GREEN,
    RED,
    TEXT,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    YELLOW,
)

_LEVEL_COLORS = {
    "good": GREEN,
    "medium": YELLOW,
    "low": RED,
    "unknown": "#5C5C64",
}

_ANC_MODE_LABELS = {
    "normal": "Normal",
    "cancellation": "Cancelamento",
    "awareness": "Transparência",
}

_ANC_LEVEL_LABELS = {
    "normal": "Padrão",
    "comfort": "Conforto",
    "ultra": "Ultra",
    "dynamic": "Dinâmico",
    "voice_boost": "Realce de voz",
    "adaptive": "Reconhecimento adaptável",
}

_ADAPTIVE_DEFAULT = 6
_ADAPTIVE_LEVELS = 11


def _level_color(level: int | None) -> str:
    if level is None:
        return _LEVEL_COLORS["unknown"]
    if level >= 60:
        return _LEVEL_COLORS["good"]
    if level >= 30:
        return _LEVEL_COLORS["medium"]
    return _LEVEL_COLORS["low"]


def _value_text(value: str | None, fallback: str = "—") -> str:
    return value if value else fallback


def make_section_label(text: str) -> QLabel:
    """Rótulo de seção em caixa alta, com leve espaçamento de letras."""

    label = QLabel(text.upper())
    label.setObjectName("sectionLabel")
    font = QFont(label.font())
    font.setWeight(QFont.Weight.DemiBold)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
    label.setFont(font)
    return label


def _separator() -> QFrame:
    line = QFrame()
    line.setObjectName("separator")
    line.setFixedHeight(1)
    return line


def _vertical_separator() -> QFrame:
    line = QFrame()
    line.setObjectName("vseparator")
    line.setFixedWidth(1)
    line.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    return line


def _elide(text: str, metrics: QFontMetrics, width: float) -> str:
    return metrics.elidedText(text, Qt.TextElideMode.ElideRight, int(width))


class _RoundedItemDelegate(QStyledItemDelegate):
    """Desenha a seleção do combo como uma pílula, e não como um retângulo."""

    def paint(self, painter: QPainter, option: object, index: object) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect.adjusted(4, 2, -4, -2)  # type: ignore[attr-defined]
        selected = bool(
            option.state & QStyle.StateFlag.State_Selected  # type: ignore[attr-defined]
        )
        hovered = bool(
            option.state & QStyle.StateFlag.State_MouseOver  # type: ignore[attr-defined]
        )
        if selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#17243B"))
            painter.drawRoundedRect(QRectF(rect), 8, 8)
        elif hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#242429"))
            painter.drawRoundedRect(QRectF(rect), 8, 8)

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""  # type: ignore[attr-defined]
        font = QFont(option.font)  # type: ignore[attr-defined]
        font.setPixelSize(13)
        painter.setFont(font)
        painter.setPen(QColor(ACCENT_TEXT if selected else TEXT))
        painter.drawText(
            rect.adjusted(10, 0, -10, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            str(text),
        )
        painter.restore()

    def sizeHint(self, option: object, index: object) -> QSize:
        _ = option, index
        return QSize(0, 32)


class _RoundedPopupCombo(QComboBox):
    """Combo com popup de cantos arredondados e largura para o maior item."""

    def _popup_font(self) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(13)
        return font

    def _prepare_popup(self) -> None:
        view = self.view()
        if view is None:
            return
        view.setMouseTracking(True)
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setViewportMargins(0, 0, 0, 0)
        view.setStyleSheet(
            "QAbstractItemView {"
            " background-color: #1F1F23; border: none; outline: none;"
            " selection-background-color: transparent;"
            "}"
        )
        if not isinstance(view.itemDelegate(), _RoundedItemDelegate):
            view.setItemDelegate(_RoundedItemDelegate(view))

        metrics = QFontMetrics(self._popup_font())
        width = self.width()
        for index in range(self.count()):
            width = max(width, metrics.horizontalAdvance(self.itemText(index)) + 48)
        view.setMinimumWidth(width)

    def showPopup(self) -> None:
        self._prepare_popup()
        super().showPopup()
        self._finish_popup()
        QTimer.singleShot(0, self._finish_popup)

    def _finish_popup(self) -> None:
        view = self.view()
        if view is None:
            return
        popup = view.window()
        if popup is self:
            return
        popup.setObjectName("comboPopup")
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        popup.setStyleSheet(
            "QFrame#comboPopup { background-color: #1F1F23; border: none; }"
        )
        view.viewport().setAutoFillBackground(False)
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(popup.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12
        )
        popup.setMask(QRegion(path.toFillPolygon().toPolygon()))


class FieldComboBox(_RoundedPopupCombo):
    """Combo com desenho próprio: campo escuro, texto à esquerda e chevron."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def enterEvent(self, event: object) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)  # type: ignore[arg-type]

    def leaveEvent(self, event: object) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def focusInEvent(self, event: object) -> None:
        super().focusInEvent(event)  # type: ignore[arg-type]
        self.update()

    def focusOutEvent(self, event: object) -> None:
        super().focusOutEvent(event)  # type: ignore[arg-type]
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        enabled = self.isEnabled()

        background = QColor("#141417" if not enabled else "#1A1A1E")
        border = QColor("#2A2A31" if not self._hover or not enabled else "#3C3C45")
        if self.hasFocus() and enabled:
            border = QColor("#2B5FB8")
        painter.setPen(QPen(border, 1))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 11, 11)

        text_color = QColor("#5C5C64" if not enabled else TEXT)
        painter.setPen(text_color)
        font = QFont(self.font())
        font.setPixelSize(13)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        text = _elide(self.currentText(), metrics, rect.width() - 42)
        painter.drawText(
            rect.adjusted(12, 0, -30, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            text,
        )
        chevron = QColor("#4E4E56" if not enabled else TEXT_SECONDARY)
        painter.setPen(
            QPen(
                chevron,
                1.6,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        cx = rect.right() - 17
        cy = rect.center().y()
        painter.drawLine(QPointF(cx - 4, cy - 2.5), QPointF(cx, cy + 1.5))
        painter.drawLine(QPointF(cx, cy + 1.5), QPointF(cx + 4, cy - 2.5))
        painter.end()


class InlineComboBox(_RoundedPopupCombo):
    """Combo sem moldura, alinhado à direita, usado nas linhas de ajuste."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def enterEvent(self, event: object) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)  # type: ignore[arg-type]

    def leaveEvent(self, event: object) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(max(180, hint.width()), 28)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled = self.isEnabled()
        color = QColor(
            "#4E4E56"
            if not enabled
            else ("#A9C9FF" if self._hover else ACCENT_TEXT)
        )
        painter.setPen(color)
        font = QFont(self.font())
        font.setPixelSize(13)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        text = _elide(self.currentText(), metrics, self.width() - 26)
        painter.drawText(
            QRectF(0, 0, self.width() - 20, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
            text,
        )

        painter.setPen(
            QPen(
                color,
                1.5,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        cx = self.width() - 8
        cy = self.height() / 2
        painter.drawLine(QPointF(cx - 3.5, cy - 2.5), QPointF(cx, cy + 1))
        painter.drawLine(QPointF(cx, cy + 1), QPointF(cx + 3.5, cy - 2.5))
        painter.end()


class ProductHero(QWidget):
    """Foto do produto com brilho suave e as pastilhas de bateria flutuantes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 230)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        asset = Path(__file__).with_name("assets") / "freebuds_pro_5.png"
        self._image = QPixmap(str(asset))
        self._buds_icon = (
            feature_pixmap("earbuds", 40, tint="#E8E8ED") or QPixmap()
        )
        self._case_icon = feature_pixmap("case", 40, tint="#E8E8ED") or QPixmap()
        self._buds: int | None = None
        self._case: int | None = None
        self._charging = False

    def set_battery(
        self,
        buds: int | None,
        case: int | None,
        charging: bool = False,
    ) -> None:
        self._buds = buds
        self._case = case
        self._charging = charging
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()

        # Luz de estúdio, bem discreta, atrás do produto.
        glow = QRadialGradient(
            rect.width() * 0.62,
            rect.height() * 0.46,
            max(rect.width(), rect.height()) * 0.56,
        )
        glow.setColorAt(0.0, QColor(255, 255, 255, 20))
        glow.setColorAt(0.55, QColor(180, 200, 255, 7))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, glow)

        if not self._image.isNull():
            available_w = max(1, rect.width() - 118)
            available_h = max(1, rect.height() - 26)
            scaled = self._image.scaled(
                available_w,
                available_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            target = QRectF(
                rect.width() - scaled.width() - 14,
                (rect.height() - scaled.height()) / 2.0 + 4,
                scaled.width(),
                scaled.height(),
            )
            shadow = QRadialGradient(
                target.center().x(),
                target.bottom() - 4,
                target.width() * 0.42,
            )
            shadow.setColorAt(0.0, QColor(0, 0, 0, 130))
            shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shadow)
            painter.drawEllipse(
                QRectF(
                    target.center().x() - target.width() * 0.42,
                    target.bottom() - 16,
                    target.width() * 0.84,
                    30,
                )
            )
            painter.drawPixmap(target, scaled, QRectF(scaled.rect()))

        # Pastilhas verticais de bateria, como na tela inicial do app oficial.
        if self._buds is not None or self._case is not None:
            pill_w, pill_h, gap = 64, 88, 10
            x = 6
            y = rect.height() - pill_h - 6
            self._draw_battery_pill(
                painter, x, y, pill_w, pill_h, self._buds, "buds"
            )
            self._draw_battery_pill(
                painter, x + pill_w + gap, y, pill_w, pill_h, self._case, "case"
            )
        painter.end()

    def _draw_battery_pill(
        self,
        painter: QPainter,
        x: float,
        y: float,
        width: float,
        height: float,
        level: int | None,
        kind: str,
    ) -> None:
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(QColor("#0B0B0D"))
        painter.drawRoundedRect(QRectF(x, y, width, height), 20, 20)

        ring = 32
        gap = 5
        text_height = 16
        content_height = ring + gap + text_height
        top = y + (height - content_height) / 2.0
        rx = x + (width - ring) / 2
        ry = top
        ring_rect = QRectF(rx, ry, ring, ring)
        painter.setPen(
            QPen(
                QColor("#2A2A30"),
                3.2,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        painter.drawEllipse(ring_rect)
        if level is not None:
            fraction = max(0.02, min(1.0, level / 100.0))
            painter.setPen(
                QPen(
                    QColor(_level_color(level)),
                    3.2,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )
            painter.drawArc(ring_rect, 90 * 16, int(-fraction * 360 * 16))

        cx = ring_rect.center().x()
        cy = ring_rect.center().y()
        icon = self._case_icon if kind == "case" else self._buds_icon
        if not icon.isNull():
            glyph = 20
            painter.drawPixmap(
                QRectF(cx - glyph / 2.0, cy - glyph / 2.0, glyph, glyph),
                icon,
                QRectF(icon.rect()),
            )
        else:
            painter.setPen(
                QPen(
                    QColor(TEXT_SECONDARY),
                    1.3,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )
            if kind == "case":
                painter.drawRoundedRect(
                    QRectF(cx - 7, cy - 5, 14, 10), 2.5, 2.5
                )
                painter.drawLine(QPointF(cx - 4, cy), QPointF(cx + 4, cy))
            else:
                painter.drawEllipse(QRectF(cx - 2.5, cy - 7, 5, 5))
                painter.drawLine(
                    QPointF(cx - 2.5, cy - 2), QPointF(cx - 2.5, cy + 5)
                )
                painter.drawEllipse(QRectF(cx + 4, cy - 5, 5, 5))
                painter.drawLine(
                    QPointF(cx + 6.5, cy), QPointF(cx + 6.5, cy + 5)
                )

        font = QFont("Segoe UI", 8)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(TEXT) if level is not None else QColor(TEXT_TERTIARY))
        painter.drawText(
            QRectF(x, ring_rect.bottom() + gap, width, text_height),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            f"{level}%" if level is not None else "—",
        )


class BatteryCard(QWidget):
    """Bloco compacto de bateria; mantém a API usada pelos testes."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("small")
        self.value_label = QLabel(t("common.none"))
        self.value_label.setObjectName("strongValue")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)
        self.status_label = QLabel(t("battery.no_data"))
        self.status_label.setObjectName("tiny")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.bar)
        layout.addWidget(self.status_label)

    def set_level(self, level: int | None, *, charging: bool | None = None) -> None:
        if level is None:
            self.value_label.setText(t("common.none"))
            self.value_label.setStyleSheet(f"color: {TEXT_TERTIARY};")
            self.bar.setValue(0)
            self.bar.setStyleSheet(
                "QProgressBar::chunk { background-color: #3A3A42; border-radius: 2px; }"
            )
            self.status_label.setText(t("battery.no_data"))
            self.status_label.setStyleSheet(f"color: {TEXT_TERTIARY};")
            return

        normalized = max(0, min(100, int(level)))
        color = _level_color(normalized)
        self.value_label.setText(f"{normalized}%")
        self.value_label.setStyleSheet(f"color: {TEXT};")
        self.bar.setValue(normalized)
        self.bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }}"
        )
        if charging is True:
            self.status_label.setText(t("battery.status_charging"))
            self.status_label.setStyleSheet(f"color: {YELLOW};")
        elif normalized <= 20:
            self.status_label.setText(t("battery.status_low"))
            self.status_label.setStyleSheet(f"color: {RED};")
        else:
            self.status_label.setText(t("battery.status_ok"))
            self.status_label.setStyleSheet(f"color: {TEXT_TERTIARY};")


class BatteryOverview(QFrame):
    """Cartão de bateria com quatro métricas e o rodapé técnico."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(10)
        title = QLabel(t("battery.title"))
        title.setObjectName("cardTitle")
        self.charging_label = QLabel(t("battery.charging"))
        self.charging_label.setObjectName("chargingBadge")
        self.charging_label.hide()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.charging_label)
        layout.addLayout(header)

        metrics = QHBoxLayout()
        metrics.setSpacing(18)
        self.global_card = BatteryCard(t("battery.global"))
        self.left_card = BatteryCard(t("battery.left"))
        self.right_card = BatteryCard(t("battery.right"))
        self.case_card = BatteryCard(t("battery.case"))
        for index, card in enumerate(
            (self.global_card, self.left_card, self.right_card, self.case_card)
        ):
            if index:
                metrics.addWidget(_vertical_separator())
            metrics.addWidget(card, 1)
        layout.addLayout(metrics)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.flags_label = QLabel(t("battery.flags_none"))
        self.flags_label.setObjectName("tiny")
        self.raw_label = QLabel(t("battery.read"))
        self.raw_label.setObjectName("tiny")
        footer.addWidget(self.flags_label)
        footer.addStretch(1)
        footer.addWidget(self.raw_label)
        layout.addLayout(footer)

    def update_battery(self, battery: BatteryState | None) -> None:
        if battery is None:
            self.global_card.set_level(None)
            self.left_card.set_level(None)
            self.right_card.set_level(None)
            self.case_card.set_level(None)
            self.flags_label.setText(t("battery.flags_none"))
            self.charging_label.hide()
            return

        is_charging = battery.charging is True
        self.global_card.set_level(battery.global_level, charging=battery.charging)
        self.left_card.set_level(battery.left)
        self.right_card.set_level(battery.right)
        self.case_card.set_level(battery.case)

        if battery.charging_flags is not None:
            flags = battery.charging_flags.hex(" ").upper()
            self.flags_label.setText(t("battery.flags", flags=flags))
        else:
            self.flags_label.setText(t("battery.flags_none"))
        self.charging_label.setVisible(is_charging)


class AncPanel(QFrame):
    """Estado e controle do cancelamento de ruído."""

    mode_requested = Signal(int)
    level_requested = Signal(int)
    adaptive_requested = Signal()
    adaptive_level_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(18)
        self._writable = False
        self._adaptive_raw: int | None = None

        header = QHBoxLayout()
        header.setSpacing(10)
        heading = QVBoxLayout()
        heading.setSpacing(3)
        title = QLabel(t("anc.title"))
        title.setObjectName("cardTitle")
        heading.addWidget(title)
        header.addLayout(heading)
        header.addStretch(1)

        # Apenas informa o modo em uso; não é um atalho para o adaptável.
        self.current_link = QLabel(t("anc.no_connection"))
        self.current_link.setObjectName("cardSubtitle")
        self.current_link.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        header.addWidget(self.current_link, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)

        # Rótulos internos preservados para a suíte de testes e diagnóstico.
        self.mode_label = QLabel(t("anc.no_data"))
        self.mode_label.setObjectName("cardTitle")
        self.level_label = QLabel(t("anc.level_label", level=t("common.none")))
        self.level_label.setObjectName("muted")
        self.raw_label = QLabel(t("anc.raw", value=t("common.none")))
        self.raw_label.setObjectName("tiny")
        self.mode_label.hide()
        self.level_label.hide()
        self.raw_label.hide()
        layout.addWidget(self.mode_label)
        layout.addWidget(self.level_label)

        track = QFrame()
        track.setObjectName("segmentTrack")
        segments = QHBoxLayout(track)
        segments.setContentsMargins(5, 5, 5, 5)
        segments.setSpacing(5)

        self.mode_buttons: dict[int, QToolButton] = {}
        mode_specs = (
            (0, t("anc.segment_off"), t("anc.tooltip_off"), "off"),
            (
                1,
                t("anc.segment_cancellation"),
                t("anc.tooltip_cancellation"),
                "cancellation",
            ),
            (
                2,
                t("anc.segment_awareness"),
                t("anc.tooltip_awareness"),
                "awareness",
            ),
        )
        for code, text, tooltip, icon_kind in mode_specs:
            button = QToolButton()
            button.setObjectName("segment")
            button.setText(text)
            button.setIcon(make_noise_icon(icon_kind))
            button.setIconSize(QSize(26, 26))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            button.setMinimumHeight(80)
            button.setToolTip(tooltip)
            button.clicked.connect(
                lambda _checked=False, code=code: self._on_mode_clicked(code)
            )
            self.mode_buttons[code] = button
            segments.addWidget(button, 1)
        layout.addWidget(track)

        (
            self.cancellation_levels,
            cancellation_buttons,
        ) = self._make_level_row(
            t("anc.level"),
            (
                (1, t("anc.level_comfort")),
                (0, t("anc.level_standard")),
                (2, t("anc.level_ultra")),
                (3, t("anc.level_dynamic")),
            ),
            mode_code=1,
        )
        self.level_buttons: dict[tuple[int, int], QPushButton] = {}
        self.level_buttons.update(cancellation_buttons)

        (
            self.awareness_levels,
            awareness_buttons,
        ) = self._make_level_row(
            t("anc.level"),
            (
                (1, t("anc.level_voice_boost")),
                (2, t("anc.level_normal")),
            ),
            mode_code=2,
        )
        self.level_buttons.update(awareness_buttons)

        self.adaptive_chip_shortcut = QPushButton(t("anc.adaptive_chip"))
        self.adaptive_chip_shortcut.setObjectName("levelChip")
        self.adaptive_chip_shortcut.setCheckable(True)
        self.adaptive_chip_shortcut.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adaptive_chip_shortcut.clicked.connect(self._on_adaptive_clicked)
        awareness_layout = self.awareness_levels.layout()
        if awareness_layout is not None:
            awareness_layout.addWidget(self.adaptive_chip_shortcut)

        layout.addWidget(self.cancellation_levels)
        layout.addWidget(self.awareness_levels)

        self.adaptive_controls = QFrame()
        self.adaptive_controls.setObjectName("adaptiveBox")
        self.adaptive_controls.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.adaptive_controls.setMinimumHeight(106)
        adaptive_layout = QVBoxLayout(self.adaptive_controls)
        adaptive_layout.setContentsMargins(16, 14, 16, 16)
        adaptive_layout.setSpacing(11)

        adaptive_header = QHBoxLayout()
        adaptive_header.setSpacing(8)
        adaptive_title = QLabel(t("anc.adaptive_title"))
        adaptive_title.setObjectName("small")
        adaptive_header.addWidget(adaptive_title)
        adaptive_header.addStretch(1)
        self.adaptive_value_label = QLabel(t("common.none"))
        self.adaptive_value_label.setObjectName("adaptiveValue")
        adaptive_header.addWidget(self.adaptive_value_label)
        adaptive_layout.addLayout(adaptive_header)

        self.adaptive_slider = QSlider(Qt.Orientation.Horizontal)
        self.adaptive_slider.setObjectName("adaptiveSlider")
        self.adaptive_slider.setRange(1, _ADAPTIVE_LEVELS)
        self.adaptive_slider.setSingleStep(1)
        self.adaptive_slider.setPageStep(1)
        self.adaptive_slider.setTracking(True)
        self.adaptive_slider.setToolTip(t("anc.slider_tooltip_short"))
        self.adaptive_slider.valueChanged.connect(
            self._on_adaptive_slider_changed
        )
        self.adaptive_slider.sliderReleased.connect(
            self._on_adaptive_slider_released
        )
        adaptive_layout.addWidget(self.adaptive_slider)

        adaptive_hints = QHBoxLayout()
        adaptive_hints.setSpacing(8)
        noisy = QLabel(t("anc.more_noise"))
        noisy.setObjectName("tiny")
        default = QLabel(t("anc.adaptive_default"))
        default.setObjectName("tiny")
        quiet = QLabel(t("anc.less_noise"))
        quiet.setObjectName("tiny")
        quiet.setAlignment(Qt.AlignmentFlag.AlignRight)
        adaptive_hints.addWidget(noisy)
        adaptive_hints.addStretch(1)
        adaptive_hints.addWidget(default)
        adaptive_hints.addStretch(1)
        adaptive_hints.addWidget(quiet)
        adaptive_layout.addLayout(adaptive_hints)

        self.adaptive_controls.hide()
        layout.addWidget(self.adaptive_controls)

        self.unknown_level_label = QLabel("")
        self.unknown_level_label.setObjectName("warnBadge")
        self.unknown_level_label.setWordWrap(True)
        self.unknown_level_label.hide()
        layout.addWidget(self.unknown_level_label)
        layout.addWidget(self.raw_label)

        self.set_enabled(False)
        self.update_anc(None)

    def _make_level_row(
        self,
        title: str,
        items: tuple[tuple[int, str], ...],
        *,
        mode_code: int,
    ) -> tuple[QWidget, dict[tuple[int, int], QPushButton]]:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(8)
        label = QLabel(title)
        label.setObjectName("small")
        label.setFixedWidth(44)
        label.setMinimumHeight(22)
        row.addWidget(label)
        buttons: dict[tuple[int, int], QPushButton] = {}
        for level_code, text in items:
            button = QPushButton(text)
            button.setObjectName("levelChip")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, mode=mode_code, level=level_code: (
                    self._on_level_clicked(mode, level)
                )
            )
            buttons[(mode_code, level_code)] = button
            row.addWidget(button)
        row.addStretch(1)
        widget.hide()
        return widget, buttons

    def set_enabled(self, enabled: bool) -> None:
        """Habilita as trocas somente quando há sessão e nenhuma ação pendente."""

        self._writable = enabled
        for button in self.mode_buttons.values():
            button.setEnabled(enabled)
        self.adaptive_chip_shortcut.setEnabled(enabled)
        self.adaptive_slider.setEnabled(
            enabled
            and not self.adaptive_controls.isHidden()
            and self._adaptive_raw is not None
        )
        for button in self.level_buttons.values():
            button.setEnabled(enabled)

    def _on_mode_clicked(self, mode_code: int) -> None:
        if self._writable:
            self.mode_requested.emit(mode_code)

    @staticmethod
    def _clear_checks(buttons: Iterable[QAbstractButton]) -> None:
        """Desmarca inclusive botões autoexclusivos, preservando o grupo."""

        for button in buttons:
            button.setAutoExclusive(False)
            button.setChecked(False)
            button.setAutoExclusive(True)

    def _on_level_clicked(self, mode_code: int, level_code: int) -> None:
        if self._writable:
            self.level_requested.emit(level_code)

    def _on_adaptive_clicked(self) -> None:
        if self._writable:
            self.adaptive_chip_shortcut.setChecked(True)
            self.adaptive_requested.emit()

    def _on_adaptive_slider_changed(self, value: int) -> None:
        self._update_adaptive_value(value)
        if not self.adaptive_slider.isSliderDown():
            self._emit_adaptive_level()

    def _on_adaptive_slider_released(self) -> None:
        self._emit_adaptive_level()

    def _update_adaptive_value(self, value: int) -> None:
        if value == _ADAPTIVE_DEFAULT:
            text = t(
                "anc.adaptive_value_default",
                value=value,
                total=_ADAPTIVE_LEVELS,
            )
        else:
            text = t("anc.adaptive_value", value=value, total=_ADAPTIVE_LEVELS)
        self.adaptive_value_label.setText(text)
        self.adaptive_slider.setToolTip(
            t(
                "anc.slider_tooltip",
                value=value,
                total=_ADAPTIVE_LEVELS,
            )
        )

    def _emit_adaptive_level(self) -> None:
        if not self._writable:
            return
        raw = self.adaptive_slider.value() - 1
        if self._adaptive_raw == raw:
            return
        self._adaptive_raw = raw
        self.adaptive_level_requested.emit(raw)

    def update_anc(self, anc: AncState | None) -> None:
        self._clear_checks(self.mode_buttons.values())
        self.adaptive_chip_shortcut.setChecked(False)
        self._clear_checks(self.level_buttons.values())
        self.cancellation_levels.hide()
        self.awareness_levels.hide()
        self.adaptive_controls.hide()
        self.unknown_level_label.hide()
        self._adaptive_raw = None

        if anc is None:
            self.mode_label.setText(t("anc.no_data"))
            self.level_label.setText(
                t("anc.level_label", level=t("common.none"))
            )
            self.adaptive_value_label.setText(t("common.none"))
            self.raw_label.setText(t("anc.raw", value=t("common.none")))
            self.current_link.setText(t("anc.no_connection"))
            return

        adaptive = anc.mode_code == 2 and anc.level_code == 4
        mode = anc.mode
        if adaptive:
            mode_text = t("anc.mode_adaptive")
        elif mode in _ANC_MODE_LABELS:
            mode_text = option_label("anc_mode", mode, _ANC_MODE_LABELS[mode])
        elif anc.mode_code is not None:
            mode_text = t("anc.mode_unknown_prefix", code=anc.mode_code)
        else:
            mode_text = t("anc.mode_unknown")
        self.mode_label.setText(mode_text)

        if adaptive:
            if anc.adaptive_level is None:
                level_text = t("common.none")
            else:
                value = anc.adaptive_level + 1
                key = (
                    "anc.adaptive_value_default"
                    if value == _ADAPTIVE_DEFAULT
                    else "anc.adaptive_value"
                )
                level_text = t(key, value=value, total=_ADAPTIVE_LEVELS)
            subtitle = t("anc.subtitle_adaptive", level=level_text)
        elif anc.level in _ANC_LEVEL_LABELS:
            level_text = option_label(
                "anc_level", anc.level, _ANC_LEVEL_LABELS[anc.level]
            )
            subtitle = t(
                "anc.subtitle_mode_level", mode=mode_text, level=level_text
            )
        elif anc.mode == "normal":
            level_text = t("common.none")
            subtitle = t("anc.subtitle_off")
        elif anc.level_code is not None:
            level_text = t("anc.level_code_unmapped", code=anc.level_code)
            subtitle = t("anc.subtitle_unmapped", mode=mode_text)
        else:
            level_text = t("common.none")
            subtitle = mode_text
        self.level_label.setText(t("anc.level_label", level=level_text))
        self.current_link.setText(subtitle)

        if adaptive:
            self.adaptive_chip_shortcut.setChecked(True)
            self.adaptive_controls.show()
            if anc.adaptive_level is None:
                self.adaptive_value_label.setText(t("common.none"))
                self.adaptive_slider.setEnabled(False)
            else:
                self._adaptive_raw = anc.adaptive_level
                value = anc.adaptive_level + 1
                self.adaptive_slider.blockSignals(True)
                self.adaptive_slider.setValue(value)
                self.adaptive_slider.blockSignals(False)
                self._update_adaptive_value(value)
                self.adaptive_slider.setEnabled(self._writable)
        elif anc.mode_code in self.mode_buttons:
            self.mode_buttons[anc.mode_code].setChecked(True)

        if anc.mode_code == 1:
            self.cancellation_levels.show()
        elif anc.mode_code == 2 and not adaptive:
            self.awareness_levels.show()

        matched = False
        for (button_mode, level_code), button in self.level_buttons.items():
            if button_mode == anc.mode_code and level_code == anc.level_code:
                button.setChecked(True)
                matched = True

        if (
            anc.mode_code in (1, 2)
            and anc.level_code is not None
            and not matched
            and not adaptive
        ):
            self.unknown_level_label.setText(
                t("anc.unknown_level", code=anc.level_code)
            )
            self.unknown_level_label.show()

        raw = anc.parameters.get(1)
        self.raw_label.setText(
            t("anc.raw", value=raw.hex(" ").upper())
            if raw
            else t("anc.raw", value=t("common.none"))
        )
        self._sync_height()

    def showEvent(self, event: object) -> None:
        super().showEvent(event)  # type: ignore[arg-type]
        QTimer.singleShot(0, self._sync_height)

    def _sync_height(self) -> None:
        """Recalcula a altura do cartão quando o painel adaptativo aparece."""

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        layout = self.layout()
        if layout is not None:
            layout.invalidate()
            layout.activate()
        hint = self.sizeHint().height() + 4
        self.setFixedHeight(hint)
        self.updateGeometry()
        widget: QWidget | None = self.parentWidget()
        for _ in range(4):
            if widget is None or widget.layout() is None:
                break
            widget.layout().invalidate()
            widget.layout().activate()
            widget = widget.parentWidget()


class ToggleSwitch(QAbstractButton):
    """Switch com o formato e as cores do HarmonyOS."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(46, 26)
        self._hover = False

    def sizeHint(self) -> QSize:
        return QSize(46, 26)

    def enterEvent(self, event: object) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)  # type: ignore[arg-type]

    def leaveEvent(self, event: object) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled = self.isEnabled()
        checked = self.isChecked()

        if checked:
            track = QColor(ACCENT) if enabled else QColor("#1B2B46")
            knob = QColor("#FFFFFF") if enabled else QColor("#8E8E96")
        else:
            track = QColor("#333339") if enabled else QColor("#1E1E22")
            if self._hover and enabled:
                track = QColor("#3D3D44")
            knob = QColor("#FFFFFF") if enabled else QColor("#6C6C74")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(1, 1, 44, 24), 12, 12)
        painter.setBrush(knob)
        x = 23 if checked else 3
        painter.drawEllipse(QRectF(x, 3, 20, 20))
        painter.end()


class FeatureCard(QFrame):
    """Cartão de ajuste com avatar, título e corpo em linhas."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        kind: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(11)
        if kind:
            avatar = QLabel()
            avatar.setPixmap(make_card_avatar(kind, size=34))
            avatar.setFixedSize(34, 34)
            header.addWidget(avatar)

        heading = QVBoxLayout()
        heading.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        heading.addWidget(title_label)
        if subtitle:
            badge = QLabel(subtitle.upper())
            badge.setObjectName("cardBadge")
            badge_font = QFont(badge.font())
            badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
            badge.setFont(badge_font)
            heading.addWidget(badge)
        header.addLayout(heading)
        header.addStretch(1)
        layout.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setSpacing(0)
        layout.addLayout(self.body)
        layout.addStretch(1)


class FeatureRow(QFrame):
    """Linha título/descrição com um controle à direita e separador fino."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        control: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("featureRow")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(0, 10, 0, 10)
        row.setSpacing(12)
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("rowTitle")
        text_box.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("rowSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        text_box.addWidget(self.subtitle_label)
        row.addLayout(text_box, 1)
        if control is not None:
            row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(content)
        outer.addWidget(_separator())


class ChipGroup(QWidget):
    """Grupo de chips mutuamente exclusivos."""

    value_changed = Signal(object)

    def __init__(
        self,
        options: tuple[tuple[object, str], ...],
        *,
        columns: int = 3,
        span_last: bool = False,
        icon_provider: Callable[[object], QIcon] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._buttons: dict[object, QAbstractButton] = {}
        self._enabled = True
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 4, 0, 3)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        total = len(options)
        for index, (value, label) in enumerate(options):
            if icon_provider is None:
                button: QAbstractButton = QPushButton(label)
                button.setMinimumHeight(42)
            else:
                tool_button = QToolButton()
                tool_button.setText(label)
                tool_button.setIcon(icon_provider(value))
                tool_button.setIconSize(QSize(30, 30))
                tool_button.setToolButtonStyle(
                    Qt.ToolButtonStyle.ToolButtonTextUnderIcon
                )
                tool_button.setMinimumHeight(78)
                button = tool_button
            button.setObjectName("chip")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            button.clicked.connect(
                lambda _checked=False, value=value: self._select(value)
            )
            self._buttons[value] = button
            if span_last and index == total - 1:
                grid.addWidget(button, index // columns, 0, 1, columns)
            else:
                grid.addWidget(button, index // columns, index % columns)
        for column in range(columns):
            grid.setColumnStretch(column, 1)

    def _select(self, value: object) -> None:
        if self._enabled:
            self.value_changed.emit(value)

    def set_value(self, value: object | None) -> None:
        for option, button in self._buttons.items():
            button.setChecked(option == value)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        for button in self._buttons.values():
            button.setEnabled(enabled)

    def set_option_enabled(self, value: object, enabled: bool) -> None:
        button = self._buttons.get(value)
        if button is not None:
            button.setEnabled(enabled and self._enabled)


class FeaturesPanel(QFrame):
    """Páginas de ajustes confirmados no hardware."""

    action_requested = Signal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("featuresPanel")
        self._advanced = AdvancedSettings()
        self._updating = False
        self._enabled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("featureTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().hide()
        self.tabs.addTab(self._build_audio_tab(), t("nav.audio"))
        self.tabs.addTab(self._build_gestures_tab(), t("nav.gestures"))
        self.tabs.addTab(self._build_connection_tab(), t("nav.connection"))
        layout.addWidget(self.tabs)
        self.set_enabled(False)

    def select_section(self, index: int) -> None:
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Construção das páginas
    # ------------------------------------------------------------------
    def _build_audio_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        sound = FeatureCard(
            t("audio.sound_title"),
            t("audio.sound_badge"),
            kind="sound",
        )
        self.sound_profile_label = QLabel(t("common.none"))
        self.sound_profile_label.setObjectName("cardTitle")
        sound.body.addWidget(self.sound_profile_label)
        self.sound_chips = ChipGroup(
            tuple(
                (
                    profile,
                    option_label("sound_profile", profile, label),
                )
                for profile, label in SOUND_PROFILES.items()
            ),
            columns=3,
            span_last=True,
        )
        self.sound_chips.value_changed.connect(
            lambda value: self._emit("sound_profile", value)
        )
        sound.body.addWidget(self.sound_chips)
        sound_hint = QLabel(t("audio.sound_hint"))
        sound_hint.setObjectName("featureHint")
        sound_hint.setWordWrap(True)
        sound.body.addWidget(sound_hint)
        layout.addWidget(sound)

        spatial = FeatureCard(
            t("audio.spatial_title"),
            t("audio.spatial_badge"),
            kind="spatial",
        )
        self.spatial_chips = ChipGroup(
            tuple(
                (mode, option_label("spatial_mode", mode, label))
                for mode, label in SPATIAL_MODES.items()
            ),
            columns=3,
            icon_provider=lambda mode: make_spatial_icon(int(mode), 30),
        )
        self.spatial_chips.value_changed.connect(
            lambda value: self._emit("spatial_mode", value)
        )
        spatial.body.addWidget(self.spatial_chips)
        self.spatial_effect_label = QLabel(
            t("audio.spatial_effect", effect=t("common.none"))
        )
        self.spatial_effect_label.setObjectName("rowSubtitle")
        spatial.body.addWidget(self.spatial_effect_label)
        effect_hint = QLabel(t("audio.spatial_hint"))
        effect_hint.setObjectName("featureHint")
        effect_hint.setWordWrap(True)
        spatial.body.addWidget(effect_hint)
        layout.addWidget(spatial)

        adaptive = FeatureCard(
            t("audio.adaptive_title"),
            t("audio.adaptive_badge"),
            kind="adaptive_audio",
        )
        self.adaptive_volume_switch = ToggleSwitch()
        self.adaptive_volume_switch.toggled.connect(
            lambda checked: self._emit("adaptive_volume", checked)
        )
        adaptive.body.addWidget(
            FeatureRow(
                t("audio.volume_title"),
                t("audio.volume_subtitle"),
                self.adaptive_volume_switch,
            )
        )
        self.conversation_switch = ToggleSwitch()
        self.conversation_switch.toggled.connect(
            lambda checked: self._emit("conversation_awareness", checked)
        )
        adaptive.body.addWidget(
            FeatureRow(
                t("audio.conversation_title"),
                t("audio.conversation_subtitle"),
                self.conversation_switch,
            )
        )
        layout.addWidget(adaptive)
        layout.addStretch(1)
        return page

    def _build_gestures_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        press = FeatureCard(
            t("gestures.press_title"), t("gestures.press_badge"), kind="gestures"
        )
        self.press_left = self._combo(PRESS_HOLD_ACTIONS, "press_hold")
        self.press_right = self._combo(PRESS_HOLD_ACTIONS, "press_hold")
        self.press_left.currentIndexChanged.connect(
            lambda _index: self._emit(
                "press_hold", ("left", self.press_left.currentData())
            )
        )
        self.press_right.currentIndexChanged.connect(
            lambda _index: self._emit(
                "press_hold", ("right", self.press_right.currentData())
            )
        )
        press.body.addWidget(FeatureRow(t("gestures.side_left"), "", self.press_left))
        press.body.addWidget(
            FeatureRow(t("gestures.side_right"), "", self.press_right)
        )
        grid.addWidget(press, 0, 0)

        pinch = FeatureCard(
            t("gestures.pinch_title"), t("gestures.pinch_badge"), kind="gestures"
        )
        self.pinch_left = self._combo(PINCH_HOLD_ACTIONS, "pinch_hold")
        self.pinch_right = self._combo(PINCH_HOLD_ACTIONS, "pinch_hold")
        self.pinch_left.currentIndexChanged.connect(
            lambda _index: self._emit(
                "pinch_hold", ("left", self.pinch_left.currentData())
            )
        )
        self.pinch_right.currentIndexChanged.connect(
            lambda _index: self._emit(
                "pinch_hold", ("right", self.pinch_right.currentData())
            )
        )
        pinch.body.addWidget(FeatureRow(t("gestures.side_left"), "", self.pinch_left))
        pinch.body.addWidget(
            FeatureRow(t("gestures.side_right"), "", self.pinch_right)
        )
        grid.addWidget(pinch, 0, 1)

        taps = FeatureCard(
            t("gestures.taps_title"), t("gestures.taps_badge"), kind="gestures"
        )
        self.double_left = self._combo(DOUBLE_TAP_ACTIONS, "double_tap")
        self.double_right = self._combo(DOUBLE_TAP_ACTIONS, "double_tap")
        self.triple_left = self._combo(TRIPLE_TAP_ACTIONS, "triple_tap")
        self.triple_right = self._combo(TRIPLE_TAP_ACTIONS, "triple_tap")
        for combo in (self.double_left, self.double_right):
            combo.currentIndexChanged.connect(lambda _index: self._emit_double())
        self.triple_left.currentIndexChanged.connect(
            lambda _index: self._emit(
                "triple_tap", ("left", self.triple_left.currentData())
            )
        )
        self.triple_right.currentIndexChanged.connect(
            lambda _index: self._emit(
                "triple_tap", ("right", self.triple_right.currentData())
            )
        )
        taps.body.addWidget(
            FeatureRow(t("gestures.double_left"), "", self.double_left)
        )
        taps.body.addWidget(
            FeatureRow(t("gestures.double_right"), "", self.double_right)
        )
        taps.body.addWidget(
            FeatureRow(t("gestures.triple_left"), "", self.triple_left)
        )
        taps.body.addWidget(
            FeatureRow(t("gestures.triple_right"), "", self.triple_right)
        )
        grid.addWidget(taps, 1, 0)

        head = FeatureCard(
            t("gestures.head_title"), t("gestures.head_badge"), kind="head_control"
        )
        self.head_switch = ToggleSwitch()
        self.head_switch.toggled.connect(
            lambda checked: self._emit("head_control", checked)
        )
        head.body.addWidget(
            FeatureRow(
                t("gestures.head_enable"),
                t("gestures.head_enable_subtitle"),
                self.head_switch,
            )
        )
        self.head_nod = self._combo(HEAD_NOD_ACTIONS, "head_nod")
        self.head_shake = self._combo(HEAD_SHAKE_ACTIONS, "head_shake")
        self.head_nod.currentIndexChanged.connect(
            lambda _index: self._emit("head_action", (3, self.head_nod.currentData()))
        )
        self.head_shake.currentIndexChanged.connect(
            lambda _index: self._emit(
                "head_action", (4, self.head_shake.currentData())
            )
        )
        head.body.addWidget(
            FeatureRow(t("gestures.head_nod"), "", self.head_nod)
        )
        head.body.addWidget(
            FeatureRow(t("gestures.head_shake"), "", self.head_shake)
        )
        grid.addWidget(head, 1, 1)

        layout.addLayout(grid)

        swipe = FeatureCard(
            t("gestures.swipe_title"), t("gestures.swipe_badge"), kind="gestures"
        )
        self.swipe_label = QLabel(t("common.none"))
        self.swipe_label.setObjectName("featureValue")
        swipe.body.addWidget(self.swipe_label)
        swipe_hint = QLabel(t("gestures.swipe_hint"))
        swipe_hint.setObjectName("featureHint")
        swipe_hint.setWordWrap(True)
        swipe.body.addWidget(swipe_hint)
        layout.addWidget(swipe)
        layout.addStretch(1)
        return page

    def _build_connection_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        quality = FeatureCard(
            t("connection.quality_title"),
            t("connection.quality_badge"),
            kind="device_phone",
        )
        self.quality_chips = ChipGroup(
            (
                (0, t("options.quality.connection")),
                (1, t("options.quality.quality")),
            ),
            columns=2,
        )
        self.quality_chips.value_changed.connect(
            lambda value: self._emit("sound_quality", value)
        )
        quality.body.addWidget(self.quality_chips)
        self.codec_label = QLabel(
            t("connection.quality_current", value=t("common.none"))
        )
        self.codec_label.setObjectName("rowSubtitle")
        quality.body.addWidget(self.codec_label)
        quality_hint = QLabel(t("connection.quality_hint"))
        quality_hint.setObjectName("featureHint")
        quality_hint.setWordWrap(True)
        quality.body.addWidget(quality_hint)
        layout.addWidget(quality)

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        latency = FeatureCard(
            t("connection.latency_title"),
            t("connection.latency_badge"),
            kind="device_pc",
        )
        self.latency_switch = ToggleSwitch()
        self.latency_switch.toggled.connect(
            lambda checked: self._emit("low_latency", checked)
        )
        latency.body.addWidget(
            FeatureRow(
                t("connection.latency_row"),
                t("connection.latency_subtitle"),
                self.latency_switch,
            )
        )
        grid.addWidget(latency, 0, 0)

        wear = FeatureCard(
            t("connection.wear_title"),
            t("connection.wear_badge"),
            kind="wear_detection",
        )
        self.wear_switch = ToggleSwitch()
        self.wear_switch.toggled.connect(
            lambda checked: self._emit("wear_detection", checked)
        )
        wear.body.addWidget(
            FeatureRow(
                t("connection.wear_row"),
                t("connection.wear_subtitle"),
                self.wear_switch,
            )
        )
        grid.addWidget(wear, 0, 1)

        one_earbud = FeatureCard(
            t("connection.one_title"),
            t("connection.one_badge"),
            kind="wear_detection",
        )
        self.one_earbud_switch = ToggleSwitch()
        self.one_earbud_switch.toggled.connect(
            lambda checked: self._emit("one_earbud_anc", checked)
        )
        one_earbud.body.addWidget(
            FeatureRow(
                t("connection.one_row"),
                t("connection.one_subtitle"),
                self.one_earbud_switch,
            )
        )
        grid.addWidget(one_earbud, 1, 0)

        multipoint = FeatureCard(
            t("connection.multipoint_title"),
            t("connection.multipoint_badge"),
            kind="device_phone",
        )
        self.multipoint_label = QLabel(t("common.none"))
        self.multipoint_label.setObjectName("featureValue")
        multipoint.body.addWidget(self.multipoint_label)
        multipoint_hint = QLabel(t("connection.multipoint_hint"))
        multipoint_hint.setObjectName("featureHint")
        multipoint_hint.setWordWrap(True)
        multipoint.body.addWidget(multipoint_hint)
        grid.addWidget(multipoint, 1, 1)

        layout.addLayout(grid)
        layout.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _combo(options: dict[int, str], category: str) -> InlineComboBox:
        combo = InlineComboBox()
        for value, label in options.items():
            combo.addItem(option_label(category, value, label), value)
        combo.setMinimumWidth(196)
        return combo

    def _emit(self, action: str, value: object) -> None:
        if self._enabled and not self._updating:
            self.action_requested.emit(action, value)

    def _emit_double(self) -> None:
        left = self.double_left.currentData()
        right = self.double_right.currentData()
        if left is not None and right is not None:
            self._emit("double_tap", (left, right))

    @staticmethod
    def _set_switch(switch: ToggleSwitch, value: bool | None) -> None:
        switch.blockSignals(True)
        switch.setChecked(bool(value))
        switch.blockSignals(False)

    @staticmethod
    def _set_combo(combo: QComboBox, value: int | None) -> None:
        combo.blockSignals(True)
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else -1)
        combo.blockSignals(False)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.sound_chips.set_enabled(enabled)
        self.spatial_chips.set_enabled(enabled)
        self.quality_chips.set_enabled(enabled)
        for switch in (
            self.adaptive_volume_switch,
            self.conversation_switch,
            self.head_switch,
            self.latency_switch,
            self.wear_switch,
            self.one_earbud_switch,
        ):
            switch.setEnabled(enabled)
        for combo in (
            self.press_left,
            self.press_right,
            self.pinch_left,
            self.pinch_right,
            self.double_left,
            self.double_right,
            self.triple_left,
            self.triple_right,
            self.head_nod,
            self.head_shake,
        ):
            combo.setEnabled(enabled)
        custom_available = bool(
            self._advanced.custom_eq and self._advanced.custom_name
        )
        self.sound_chips.set_option_enabled(100, enabled and custom_available)

    def update_advanced(self, settings: AdvancedSettings | None) -> None:
        self._updating = True
        try:
            self._advanced = settings or AdvancedSettings()
            data = self._advanced
            profile = SOUND_PROFILES.get(
                data.sound_profile_id
                if data.sound_profile_id is not None
                else -1
            )
            profile_name = option_label(
                "sound_profile", data.sound_profile_id, profile or t("common.none")
            )
            if profile_name == t("options.sound_profile.custom") and data.custom_name:
                profile_name = t("audio.custom_profile", name=data.custom_name)
            self.sound_profile_label.setText(profile_name or t("common.none"))
            self.sound_chips.set_value(data.sound_profile_id)
            self.sound_chips.set_option_enabled(
                100, bool(data.custom_eq and data.custom_name)
            )

            self.spatial_chips.set_value(data.spatial_mode)
            effect_id = data.spatial_effect
            effect_fallback = SPATIAL_EFFECTS.get(
                effect_id if effect_id is not None else -1,
                f"ID {effect_id}" if effect_id is not None else t("common.none"),
            )
            effect = option_label(
                "spatial_effect", effect_id, effect_fallback
            )
            self.spatial_effect_label.setText(
                t("audio.spatial_effect", effect=effect)
            )

            self._set_switch(self.adaptive_volume_switch, data.adaptive_volume)
            self._set_switch(
                self.conversation_switch, data.conversation_awareness
            )
            self._set_switch(self.head_switch, data.head_control)
            self._set_combo(self.head_nod, data.head_nod_action)
            self._set_combo(self.head_shake, data.head_shake_action)

            self.quality_chips.set_value(data.sound_quality)
            self._set_switch(self.latency_switch, data.low_latency)
            self._set_switch(self.wear_switch, data.wear_detection)
            self._set_switch(self.one_earbud_switch, data.one_earbud_anc)
            if data.multipoint is True:
                multipoint = t("connection.multipoint_active")
            elif data.multipoint is False:
                multipoint = t("connection.multipoint_inactive")
            else:
                multipoint = t("common.none")
            self.multipoint_label.setText(
                t("connection.multipoint_value", status=multipoint)
            )
            quality = option_label(
                "quality",
                data.sound_quality,
                t("common.none"),
            )
            self.codec_label.setText(
                t("connection.quality_current", value=quality)
            )

            self._set_combo(self.press_left, data.press_hold_left)
            self._set_combo(self.press_right, data.press_hold_right)
            self._set_combo(self.pinch_left, data.pinch_hold_left)
            self._set_combo(self.pinch_right, data.pinch_hold_right)
            self._set_combo(self.double_left, data.double_tap_left)
            self._set_combo(self.double_right, data.double_tap_right)
            self._set_combo(self.triple_left, data.triple_tap_left)
            self._set_combo(self.triple_right, data.triple_tap_right)

            swipe_labels = []
            if data.swipe_up is not None:
                action = option_label(
                    "swipe",
                    data.swipe_up,
                    SWIPE_ACTIONS.get(data.swipe_up, f"ID {data.swipe_up}"),
                )
                swipe_labels.append(t("gestures.swipe_up", action=action))
            if data.swipe_down is not None:
                action = option_label(
                    "swipe",
                    data.swipe_down,
                    SWIPE_ACTIONS.get(data.swipe_down, f"ID {data.swipe_down}"),
                )
                swipe_labels.append(t("gestures.swipe_down", action=action))
            self.swipe_label.setText(
                " · ".join(swipe_labels) or t("common.none")
            )
            self.set_enabled(self._enabled)
        finally:
            self._updating = False


class DeviceDetailsPanel(QFrame):
    """Detalhes técnicos não sensíveis do dispositivo, em linhas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(4)

        title = QLabel(t("details.title"))
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        caption = QLabel(t("details.subtitle"))
        caption.setObjectName("cardSubtitle")
        layout.addWidget(caption)
        layout.addSpacing(10)

        self._values: dict[str, QLabel] = {}
        fields = (
            ("model", t("details.model")),
            ("submodel", t("details.submodel")),
            ("firmware", t("details.firmware")),
            ("hardware", t("details.hardware")),
            ("channel", t("details.channel")),
            ("updated", t("details.updated")),
        )
        for index, (key, label) in enumerate(fields):
            row = QHBoxLayout()
            row.setContentsMargins(0, 9, 0, 9)
            row.setSpacing(16)
            name = QLabel(label)
            name.setObjectName("rowSubtitle")
            value = QLabel(t("common.none"))
            value.setObjectName("rowValue")
            value.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            value.setWordWrap(False)
            value.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
            )
            self._values[key] = value
            row.addWidget(name)
            row.addStretch(1)
            row.addWidget(value, 0, Qt.AlignmentFlag.AlignRight)
            layout.addLayout(row)
            if index < len(fields) - 1:
                layout.addWidget(_separator())

    def update_info(
        self,
        info: DeviceInfo | None,
        channel: int | None,
        updated_at: datetime | None = None,
    ) -> None:
        if info is None:
            self._values["model"].setText(t("common.none"))
            self._values["submodel"].setText(t("common.none"))
            self._values["firmware"].setText(t("common.none"))
            self._values["hardware"].setText(t("common.none"))
        else:
            self._values["model"].setText(_value_text(info.model, t("common.none")))
            self._values["submodel"].setText(
                _value_text(info.submodel, t("common.none"))
            )
            self._values["firmware"].setText(
                _value_text(info.software_version, t("common.none"))
            )
            self._values["hardware"].setText(
                _value_text(info.hardware_version, t("common.none"))
            )
        self._values["channel"].setText(
            str(channel) if channel else t("common.none")
        )
        self._values["updated"].setText(
            updated_at.strftime("%H:%M:%S") if updated_at else t("common.none")
        )


class QuickTile(QFrame):
    """Atalho de ajuste da visão geral, no estilo dos cartões do app oficial."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        value: str,
        kind: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("quickTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(76)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 16, 14)
        layout.setSpacing(13)

        avatar = QLabel()
        avatar.setPixmap(make_card_avatar(kind, size=34))
        avatar.setFixedSize(34, 34)
        layout.addWidget(avatar)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("rowTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("rowSubtitle")
        text_box.addWidget(self.title_label)
        text_box.addWidget(self.value_label)
        layout.addLayout(text_box, 1)

        chevron = QLabel()
        chevron.setPixmap(make_chevron_icon(14, TEXT_TERTIARY).pixmap(14, 14))
        chevron.setFixedSize(14, 14)
        layout.addWidget(chevron, 0, Qt.AlignmentFlag.AlignVCenter)

        for child in (avatar, self.title_label, self.value_label, chevron):
            child.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def mouseReleaseEvent(self, event: object) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton  # type: ignore[attr-defined]
            and self.rect().contains(
                event.position().toPoint()  # type: ignore[attr-defined]
            )
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)  # type: ignore[arg-type]


class ActivityLog(QTextEdit):
    """Log discreto para diagnóstico, com limite de linhas."""

    _COLORS = {
        "info": "#A7A7AF",
        "ok": GREEN,
        "warn": YELLOW,
        "error": RED,
        "muted": TEXT_TERTIARY,
    }
    _PREFIXES = {
        "info": "·",
        "ok": "✓",
        "warn": "!",
        "error": "×",
        "muted": "·",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activityLog")
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.document().setMaximumBlockCount(300)
        self.setMinimumHeight(220)

    def log(self, message: str, level: str = "info") -> None:
        color = self._COLORS.get(level, self._COLORS["info"])
        prefix = self._PREFIXES.get(level, self._PREFIXES["info"])
        timestamp = datetime.now().strftime("%H:%M:%S")
        safe = html.escape(message)
        self.append(
            f'<span style="color:{color}">{timestamp}&nbsp;&nbsp;'
            f"{prefix} {safe}</span>"
        )
        self.moveCursor(QTextCursor.MoveOperation.End)
