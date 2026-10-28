"""Ícones desenhados em tempo de execução, sem arquivos externos.

O traço é fino, monocromático e geométrico. As cores cheias aparecem apenas
nos avatares circulares dos cartões de recurso, como no app oficial.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from .svg_icons import feature_pixmap
from .svg_icons import make_noise_icon as make_svg_noise_icon

_AVATAR_COLORS = {
    "huawei_sound": "#E4577B",
    "sound": "#E4577B",
    "adaptive_audio": "#E8A23A",
    "spatial": "#8B6CEF",
    "spatial_audio": "#8B6CEF",
    "gestures": "#17B3A3",
    "head_control": "#17B3A3",
    "wear_detection": "#2FBF71",
    "earbuds": "#0A84FF",
    "device_phone": "#0A84FF",
    "device_pc": "#0A84FF",
    "bluetooth": "#0A84FF",
    "anc": "#0A59F7",
    "default": "#3A3A42",
}

_LEVEL_COLORS = {
    "good": "#30D158",
    "medium": "#FFD60A",
    "low": "#FF453A",
    "unknown": "#5C5C64",
}

_ANC_COLORS = {
    "normal": "#8E8E96",
    "cancellation": "#30D158",
    "awareness": "#FFD60A",
}


def _level_color(level: int | None) -> str:
    if level is None:
        return _LEVEL_COLORS["unknown"]
    if level >= 60:
        return _LEVEL_COLORS["good"]
    if level >= 30:
        return _LEVEL_COLORS["medium"]
    return _LEVEL_COLORS["low"]


def _canvas(size: int, dpr: int = 2) -> tuple[QPixmap, QPainter, int]:
    """Cria um canvas em alta resolução sem DPR no QPainter.

    O painter é aplicado em pixels físicos; os chamadores reduzem o resultado
    para o tamanho lógico. Definir devicePixelRatio aqui faria o Qt escalar o
    desenho duas vezes e cortar o ícone no canto superior esquerdo.
    """

    pixmap = QPixmap(size * dpr, size * dpr)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    return pixmap, painter, size * dpr


def _rounded_pen(color: QColor, width: float) -> QPen:
    return QPen(
        color,
        width,
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )


def _finish(pixmap: QPixmap, painter: QPainter, size: int) -> QPixmap:
    """Reduz o desenho em 2x para o tamanho lógico e remove o DPR.

    QLabel não aplica o device pixel ratio ao dimensionar todos os pixmaps;
    devolver um pixmap 1x evita que o ícone apareça cortado no canto.
    """

    painter.end()
    scaled = pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(1)
    return scaled


def make_brand_mark(size: int = 30) -> QPixmap:
    """Marca do app: quadrado azul com um fone estilizado em branco."""

    pixmap, painter, s = _canvas(size)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#0A59F7"))
    painter.drawRoundedRect(QRectF(0, 0, s, s), s * 0.30, s * 0.30)

    pen = _rounded_pen(QColor("#FFFFFF"), s * 0.075)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    # Arco da tiara e as duas cápsulas.
    painter.drawArc(
        QRectF(s * 0.24, s * 0.26, s * 0.52, s * 0.46),
        20 * 16,
        140 * 16,
    )
    painter.setBrush(QColor("#FFFFFF"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(
        QRectF(s * 0.20, s * 0.47, s * 0.14, s * 0.27), s * 0.07, s * 0.07
    )
    painter.drawRoundedRect(
        QRectF(s * 0.66, s * 0.47, s * 0.14, s * 0.27), s * 0.07, s * 0.07
    )
    return _finish(pixmap, painter, size)


def make_app_icon(size: int = 256) -> QIcon:
    """Ícone do aplicativo: marca azul HUAWEI sobre fundo escuro."""

    pixmap, painter, s = _canvas(size, dpr=1)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#0B0B0D"))
    painter.drawRoundedRect(QRectF(0, 0, s, s), s * 0.22, s * 0.22)
    painter.setBrush(QColor("#0A59F7"))
    painter.drawRoundedRect(QRectF(s * 0.08, s * 0.08, s * 0.84, s * 0.84), s * 0.20, s * 0.20)

    painter.setPen(_rounded_pen(QColor("#FFFFFF"), s * 0.055))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(
        QRectF(s * 0.25, s * 0.27, s * 0.50, s * 0.44),
        20 * 16,
        140 * 16,
    )
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(
        QRectF(s * 0.21, s * 0.47, s * 0.13, s * 0.24), s * 0.06, s * 0.06
    )
    painter.drawRoundedRect(
        QRectF(s * 0.66, s * 0.47, s * 0.13, s * 0.24), s * 0.06, s * 0.06
    )
    painter.end()
    return QIcon(pixmap)


def make_tray_icon(
    level: int | None,
    anc_mode: str | None,
    *,
    connected: bool,
) -> QIcon:
    """Ícone da bandeja: bateria horizontal e um ponto de ANC."""

    size = 64
    pixmap, painter, s = _canvas(size, dpr=1)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#151517"))
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 15, 15)

    body = QRectF(10, 22, 38, 21)
    terminal = QRectF(49, 28, 5, 9)
    border = QColor("#E8E8EC") if connected else QColor("#7A7A82")
    painter.setPen(QPen(border, 2.6))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(body, 4, 4)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(border)
    painter.drawRoundedRect(terminal, 2, 2)

    fill = _level_color(level) if connected else _LEVEL_COLORS["unknown"]
    if connected and level is not None:
        fraction = max(0.0, min(1.0, level / 100.0))
        inner = QRectF(14, 26, max(1.0, 30 * fraction), 13)
        painter.setBrush(QColor(fill))
        painter.drawRoundedRect(inner, 2, 2)
    elif connected:
        painter.setPen(QPen(QColor(fill), 2))
        painter.drawLine(15, 32, 43, 32)
        painter.setPen(Qt.PenStyle.NoPen)

    if not connected:
        painter.setPen(QPen(QColor("#FF453A"), 2.8))
        painter.drawLine(14, 46, 46, 18)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(_ANC_COLORS.get(anc_mode or "", "#8E8E96")))
    painter.drawEllipse(QRectF(49, 8, 9, 9))

    painter.end()
    return QIcon(pixmap)


def make_card_avatar(kind: str, size: int = 36) -> QPixmap:
    """Círculo colorido com o SVG fornecido centralizado dentro da moldura."""

    pixmap, painter, s = _canvas(size)
    color = QColor(_AVATAR_COLORS.get(kind, _AVATAR_COLORS["default"]))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QRectF(0, 0, s, s))

    icon_size = max(1, int(s * 0.68))
    svg = feature_pixmap(kind, icon_size)
    if svg is not None:
        painter.drawPixmap(
            QRectF(
                (s - icon_size) / 2.0,
                (s - icon_size) / 2.0,
                icon_size,
                icon_size,
            ),
            svg,
            QRectF(svg.rect()),
        )
        return _finish(pixmap, painter, size)

    pen = _rounded_pen(QColor("#FFFFFF"), s * 0.065)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    c = s * 0.5

    if kind in ("huawei_sound", "sound"):
        for offset, height in ((-0.20, 0.12), (-0.07, 0.28), (0.07, 0.20), (0.20, 0.10)):
            painter.drawLine(
                QPointF(c + s * offset, c - s * height),
                QPointF(c + s * offset, c + s * height),
            )
    elif kind in ("adaptive_audio",):
        painter.drawArc(
            QRectF(c - s * 0.27, c - s * 0.20, s * 0.18, s * 0.40),
            90 * 16,
            180 * 16,
        )
        painter.drawArc(
            QRectF(c + s * 0.09, c - s * 0.20, s * 0.18, s * 0.40),
            -90 * 16,
            180 * 16,
        )
        painter.drawLine(QPointF(c, c - s * 0.16), QPointF(c, c + s * 0.16))
    elif kind in ("spatial", "spatial_audio"):
        painter.drawEllipse(QRectF(c - s * 0.12, c - s * 0.22, s * 0.24, s * 0.24))
        painter.drawArc(
            QRectF(c - s * 0.24, c - s * 0.02, s * 0.48, s * 0.36),
            20 * 16,
            140 * 16,
        )
        painter.drawArc(
            QRectF(c - s * 0.38, c - s * 0.14, s * 0.20, s * 0.28),
            90 * 16,
            180 * 16,
        )
        painter.drawArc(
            QRectF(c + s * 0.18, c - s * 0.14, s * 0.20, s * 0.28),
            -90 * 16,
            180 * 16,
        )
    elif kind in ("gestures",):
        painter.drawEllipse(QRectF(c - s * 0.09, c - s * 0.28, s * 0.18, s * 0.18))
        painter.drawRoundedRect(
            QRectF(c - s * 0.08, c - s * 0.12, s * 0.16, s * 0.34),
            s * 0.08,
            s * 0.08,
        )
        painter.drawLine(
            QPointF(c - s * 0.22, c + s * 0.04),
            QPointF(c - s * 0.08, c + s * 0.18),
        )
    elif kind in ("head_control",):
        painter.drawEllipse(QRectF(c - s * 0.26, c - s * 0.26, s * 0.52, s * 0.52))
        painter.drawPoint(QPointF(c - s * 0.10, c - s * 0.06))
        painter.drawPoint(QPointF(c + s * 0.10, c - s * 0.06))
        painter.drawArc(
            QRectF(c - s * 0.12, c, s * 0.24, s * 0.14),
            -30 * 16,
            -120 * 16,
        )
    elif kind in ("wear_detection",):
        painter.drawArc(
            QRectF(c - s * 0.16, c - s * 0.26, s * 0.30, s * 0.52),
            40 * 16,
            250 * 16,
        )
        painter.drawArc(
            QRectF(c + s * 0.04, c - s * 0.12, s * 0.16, s * 0.24),
            -60 * 16,
            120 * 16,
        )
    elif kind in ("device_phone",):
        painter.drawRoundedRect(
            QRectF(c - s * 0.14, c - s * 0.24, s * 0.28, s * 0.48),
            s * 0.06,
            s * 0.06,
        )
        painter.drawLine(
            QPointF(c - s * 0.04, c + s * 0.16),
            QPointF(c + s * 0.04, c + s * 0.16),
        )
    elif kind in ("device_pc",):
        painter.drawRoundedRect(
            QRectF(c - s * 0.24, c - s * 0.18, s * 0.48, s * 0.30),
            s * 0.04,
            s * 0.04,
        )
        painter.drawLine(
            QPointF(c - s * 0.28, c + s * 0.18),
            QPointF(c + s * 0.28, c + s * 0.18),
        )
        painter.drawLine(
            QPointF(c, c + s * 0.12),
            QPointF(c, c + s * 0.18),
        )
    elif kind in ("bluetooth",):
        _draw_bluetooth(painter, c, s)
    elif kind in ("anc",):
        painter.drawArc(
            QRectF(c - s * 0.28, c - s * 0.28, s * 0.56, s * 0.56),
            0,
            360 * 16,
        )
        painter.drawArc(
            QRectF(c - s * 0.12, c - s * 0.14, s * 0.24, s * 0.28),
            40 * 16,
            280 * 16,
        )
    return _finish(pixmap, painter, size)


def _draw_bluetooth(painter: QPainter, c: float, s: float) -> None:
    points = [
        QPointF(c, c - s * 0.24),
        QPointF(c + s * 0.15, c - s * 0.10),
        QPointF(c - s * 0.13, c + s * 0.12),
        QPointF(c, c + s * 0.24),
        QPointF(c, c - s * 0.24),
        QPointF(c - s * 0.13, c - s * 0.10),
        QPointF(c + s * 0.15, c + s * 0.12),
    ]
    for start, end in zip(points, points[1:]):
        painter.drawLine(start, end)


def make_noise_icon(kind: str, size: int = 28, active: bool = False) -> QIcon:
    """Ícone do segmented control de ruído, baseado nos SVGs fornecidos."""

    _ = active
    return make_svg_noise_icon(kind, size)


def _nav_pixmap(kind: str, size: int, color: QColor) -> QPixmap:
    pixmap, painter, s = _canvas(size)
    c = s * 0.5
    painter.setPen(_rounded_pen(color, s * 0.085))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == "overview":
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            painter.drawRoundedRect(
                QRectF(c + dx * s * 0.20 - s * 0.14, c + dy * s * 0.20 - s * 0.14, s * 0.28, s * 0.28),
                s * 0.06,
                s * 0.06,
            )
    elif kind == "audio":
        for offset, height in ((-0.24, 0.10), (-0.08, 0.26), (0.08, 0.18), (0.24, 0.30)):
            painter.drawLine(
                QPointF(c + s * offset, c - s * height),
                QPointF(c + s * offset, c + s * height),
            )
    elif kind == "gestures":
        painter.drawEllipse(QRectF(c - s * 0.08, c - s * 0.30, s * 0.16, s * 0.16))
        painter.drawRoundedRect(
            QRectF(c - s * 0.07, c - s * 0.14, s * 0.14, s * 0.32),
            s * 0.07,
            s * 0.07,
        )
        painter.drawLine(
            QPointF(c - s * 0.22, c + s * 0.02),
            QPointF(c - s * 0.07, c + s * 0.16),
        )
    elif kind == "connection":
        painter.drawEllipse(QRectF(c - s * 0.28, c - s * 0.10, s * 0.24, s * 0.24))
        painter.drawEllipse(QRectF(c + s * 0.04, c - s * 0.12, s * 0.24, s * 0.24))
        painter.drawLine(
            QPointF(c - s * 0.06, c + s * 0.06),
            QPointF(c + s * 0.06, c + s * 0.02),
        )
    elif kind == "diagnostics":
        painter.drawRoundedRect(
            QRectF(c - s * 0.32, c - s * 0.26, s * 0.64, s * 0.52),
            s * 0.10,
            s * 0.10,
        )
        path = QPainterPath()
        path.moveTo(c - s * 0.22, c + s * 0.02)
        path.lineTo(c - s * 0.08, c + s * 0.02)
        path.lineTo(c - s * 0.01, c - s * 0.12)
        path.lineTo(c + s * 0.07, c + s * 0.12)
        path.lineTo(c + s * 0.14, c + s * 0.02)
        path.lineTo(c + s * 0.24, c + s * 0.02)
        painter.drawPath(path)
    painter.end()
    return pixmap


def make_nav_icon(kind: str, size: int = 19) -> QIcon:
    """Ícone da navegação lateral, branco quando o item está ativo."""

    icon = QIcon()
    icon.addPixmap(
        _nav_pixmap(kind, size, QColor("#8E8E96")),
        QIcon.Mode.Normal,
        QIcon.State.Off,
    )
    icon.addPixmap(
        _nav_pixmap(kind, size, QColor("#79ACFF")),
        QIcon.Mode.Normal,
        QIcon.State.On,
    )
    icon.addPixmap(
        _nav_pixmap(kind, size, QColor("#4E4E56")),
        QIcon.Mode.Disabled,
        QIcon.State.Off,
    )
    return icon


def make_search_icon(size: int = 18, color: str = "#9A9AA2") -> QIcon:
    return _simple_icon(size, color, "search")


def make_refresh_icon(size: int = 18, color: str = "#9A9AA2") -> QIcon:
    return _simple_icon(size, color, "refresh")


def make_chevron_icon(
    size: int = 14, color: str = "#6C6C74", direction: str = "right"
) -> QIcon:
    return _simple_icon(size, color, f"chevron_{direction}")


def _simple_icon(size: int, color: str, kind: str) -> QIcon:
    pixmap, painter, s = _canvas(size)
    c = s * 0.5
    pen = _rounded_pen(QColor(color), s * 0.09)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == "search":
        painter.drawEllipse(QRectF(c - s * 0.24, c - s * 0.24, s * 0.34, s * 0.34))
        painter.drawLine(
            QPointF(c + s * 0.04, c + s * 0.04),
            QPointF(c + s * 0.24, c + s * 0.24),
        )
    elif kind == "refresh":
        painter.drawArc(
            QRectF(c - s * 0.26, c - s * 0.26, s * 0.52, s * 0.52),
            35 * 16,
            290 * 16,
        )
        painter.drawLine(
            QPointF(c + s * 0.16, c - s * 0.30),
            QPointF(c + s * 0.28, c - s * 0.18),
        )
        painter.drawLine(
            QPointF(c + s * 0.28, c - s * 0.18),
            QPointF(c + s * 0.13, c - s * 0.14),
        )
    elif kind == "chevron_right":
        painter.drawLine(
            QPointF(c - s * 0.16, c - s * 0.24),
            QPointF(c + s * 0.10, c),
        )
        painter.drawLine(
            QPointF(c + s * 0.10, c),
            QPointF(c - s * 0.16, c + s * 0.24),
        )
    elif kind == "chevron_down":
        painter.drawLine(
            QPointF(c - s * 0.24, c - s * 0.10),
            QPointF(c, c + s * 0.14),
        )
        painter.drawLine(
            QPointF(c, c + s * 0.14),
            QPointF(c + s * 0.24, c - s * 0.10),
        )
    painter.end()
    return QIcon(pixmap)
