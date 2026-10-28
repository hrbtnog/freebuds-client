"""Ponto de entrada da interface gráfica."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run_ui(
    *, address: str | None = None, settings_path: Path | None = None
) -> int:
    """Inicia a UI. Retorna o código de saída ou 2 se PySide6 faltar."""

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "A interface gráfica exige PySide6. Instale com:\n"
            '  pip install -e ".[ui]"',
            file=sys.stderr,
        )
        return 2

    from .icons import make_app_icon
    from .main_window import MainWindow
    from .theme import APP_STYLESHEET

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName("FreeBuds Client")
    app.setApplicationDisplayName("FreeBuds Client")
    app.setOrganizationName("FreeBudsClient")
    app.setStyle("Fusion")
    app.setWindowIcon(make_app_icon())
    app.setStyleSheet(APP_STYLESHEET)

    # Barra de título nativa escura quando o Qt/Windows suporta o pedido.
    try:
        from PySide6.QtCore import Qt

        hints = app.styleHints()
        if hasattr(hints, "setColorScheme"):
            hints.setColorScheme(Qt.ColorScheme.Dark)
    except (ImportError, AttributeError):
        pass

    window = MainWindow(settings_path=settings_path, address=address)
    window.show()
    app.aboutToQuit.connect(window.shutdown)
    if not owns_app:
        return 0
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="freebuds-ui",
        description="Interface desktop não oficial para HUAWEI FreeBuds.",
    )
    parser.add_argument(
        "--address",
        help="MAC do fone para conectar automaticamente (ex.: AA:BB:CC:DD:EE:FF).",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        help="Arquivo de configurações alternativo (padrão: %%APPDATA%%).",
    )
    args = parser.parse_args(argv)
    return run_ui(address=args.address, settings_path=args.settings)


if __name__ == "__main__":
    raise SystemExit(main())
