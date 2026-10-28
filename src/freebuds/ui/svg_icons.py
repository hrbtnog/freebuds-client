"""Ícones SVG fornecidos para a interface.

Os arquivos ficam em ``assets/icons`` e são renderizados em alta resolução com
``QSvgRenderer``. Ícones de estado (ruído e áudio espacial) recebem uma máscara
de cor para ficarem cinza quando inativos e azuis quando selecionados.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

SVG_DIR = Path(__file__).with_name("assets") / "icons"

FEATURE_ICONS: dict[str, str] = {
    "huawei_sound": "Huawei Sound.svg",
    "sound": "Huawei Sound.svg",
    "adaptive_audio": "AudioAdaptavel.svg",
    "spatial": "Modo Espacial com rastreamento de cabeça.svg",
    "spatial_audio": "Modo Espacial com rastreamento de cabeça.svg",
    "gestures": "ControleDeGestos.svg",
    "head_control": "Controle de Cabeça.svg",
    "wear_detection": "Deteccao de uso.svg",
    "earbuds": "Fones_1.svg",
    "case": "Case.svg",
}

NOISE_ICONS: dict[str, str] = {
    "off": "Modos de Som Desativado_1.svg",
    "cancellation": "Modo cancelamento de ruído.svg",
    "awareness": "Modo transparencia.svg",
}

SPATIAL_ICONS: dict[int, str] = {
    0: "Modo Espacial Desativado.svg",
    1: "Modo Espacial com rastreamento de cabeça.svg",
    2: "Modo Espacial Fixo.svg",
}


def _renderer(name: str) -> QSvgRenderer | None:
    path = SVG_DIR / name
    if not path.is_file():
        return None
    renderer = QSvgRenderer(str(path))
    return renderer if renderer.isValid() else None


def render_svg(name: str, size: int, *, tint: str | None = None) -> QPixmap:
    """Renderiza um SVG quadrado de ``size`` px, preservando a proporção."""

    if size <= 0:
        return QPixmap()
    renderer = _renderer(name)
    if renderer is None:
        return QPixmap()

    scale = 3
    pixel_size = size * scale
    pixmap = QPixmap(pixel_size, pixel_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    box = renderer.viewBoxF()
    if box.isEmpty():
        default = renderer.defaultSize()
        box = QRectF(0, 0, default.width(), default.height())
    if box.width() > 0 and box.height() > 0:
        factor = min(pixel_size / box.width(), pixel_size / box.height())
        width = box.width() * factor
        height = box.height() * factor
        target = QRectF(
            (pixel_size - width) / 2.0,
            (pixel_size - height) / 2.0,
            width,
            height,
        )
        renderer.render(painter, target)

    if tint is not None:
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(tint))

    painter.end()
    result = pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    result.setDevicePixelRatio(1)
    return result


def feature_pixmap(
    kind: str, size: int, *, tint: str | None = None
) -> QPixmap | None:
    """Ícone colorido de um cartão/atalho, ou ``None`` se não houver SVG."""

    name = FEATURE_ICONS.get(kind)
    if name is None:
        return None
    pixmap = render_svg(name, size, tint=tint)
    return None if pixmap.isNull() else pixmap


def make_state_icon(
    name: str,
    size: int,
    *,
    off_color: str,
    on_color: str,
    disabled_color: str,
) -> QIcon:
    icon = QIcon()
    icon.addPixmap(
        render_svg(name, size, tint=off_color),
        QIcon.Mode.Normal,
        QIcon.State.Off,
    )
    icon.addPixmap(
        render_svg(name, size, tint=on_color),
        QIcon.Mode.Normal,
        QIcon.State.On,
    )
    icon.addPixmap(
        render_svg(name, size, tint=disabled_color),
        QIcon.Mode.Disabled,
        QIcon.State.Off,
    )
    return icon


def make_noise_icon(kind: str, size: int = 28) -> QIcon:
    name = NOISE_ICONS.get(kind)
    if name is None:
        return QIcon()
    return make_state_icon(
        name,
        size,
        off_color="#8E8E96",
        on_color="#79ACFF",
        disabled_color="#4E4E56",
    )


def make_spatial_icon(mode: int, size: int = 28) -> QIcon:
    name = SPATIAL_ICONS.get(mode)
    if name is None:
        return QIcon()
    return make_state_icon(
        name,
        size,
        off_color="#8E8E96",
        on_color="#79ACFF",
        disabled_color="#4E4E56",
    )


def icon_size(name: str) -> QSize:
    renderer = _renderer(name)
    if renderer is None:
        return QSize()
    size = renderer.defaultSize()
    if size.isEmpty():
        box = renderer.viewBoxF()
        size = QSize(int(box.width()), int(box.height()))
    return size
