"""Tema visual do FreeBuds Client inspirado no HarmonyOS.

A referência é o app HUAWEI Audio Connect: fundo preto, cartões grandes de
cantos generosos, tipografia clara em poucos níveis, separadores finos e o azul
HUAWEI usado apenas para estado ativo, links e controles primários.
"""

from __future__ import annotations

# Paleta compartilhada com os widgets desenhados em QPainter.
BACKGROUND = "#000000"
SIDEBAR = "#08080A"
SURFACE = "#161618"
SURFACE_RAISED = "#1F1F23"
SURFACE_HOVER = "#232328"
TRACK = "#101012"
HAIRLINE = "rgba(255, 255, 255, 0.07)"
HAIRLINE_STRONG = "rgba(255, 255, 255, 0.12)"
TEXT = "#F3F3F6"
TEXT_SECONDARY = "#9A9AA2"
TEXT_TERTIARY = "#6C6C74"
ACCENT = "#0A59F7"
ACCENT_TEXT = "#79ACFF"
ACCENT_SOFT = "#17243B"
GREEN = "#30D158"
YELLOW = "#FFD60A"
RED = "#FF453A"

APP_STYLESHEET = f"""
/* ------------------------------------------------------------------ */
/* Base                                                                */
/* ------------------------------------------------------------------ */
* {{
    font-family: "Segoe UI Variable Text", "Segoe UI", Arial, sans-serif;
    font-size: 14px;
    color: {TEXT};
}}

QMainWindow, QWidget#root {{
    background-color: {BACKGROUND};
}}

QWidget#mainArea {{
    background-color: {BACKGROUND};
}}

QWidget#page {{
    background-color: transparent;
}}

QToolTip {{
    background-color: {SURFACE_RAISED};
    color: {TEXT};
    border: 1px solid {HAIRLINE};
    border-radius: 8px;
    padding: 6px 9px;
    font-size: 12px;
}}

/* ------------------------------------------------------------------ */
/* Barra lateral                                                       */
/* ------------------------------------------------------------------ */
QFrame#sidebar {{
    background-color: {SIDEBAR};
    border-right: 1px solid {HAIRLINE};
}}

QLabel#brandName {{
    font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
    font-size: 17px;
    font-weight: 600;
    color: #FFFFFF;
}}

QLabel#brandCaption {{
    font-size: 10px;
    color: {TEXT_TERTIARY};
}}

QPushButton#navItem {{
    background-color: transparent;
    border: none;
    border-radius: 12px;
    padding: 0 12px;
    min-height: 42px;
    text-align: left;
    color: {TEXT_SECONDARY};
    font-size: 14px;
    font-weight: 500;
}}

QPushButton#navItem:hover {{
    background-color: rgba(255, 255, 255, 0.04);
    color: {TEXT};
}}

QPushButton#navItem:checked {{
    background-color: rgba(10, 89, 247, 0.11);
    color: {ACCENT_TEXT};
    font-weight: 600;
}}

QFrame#devicePanel {{
    background-color: #101013;
    border: 1px solid {HAIRLINE};
    border-radius: 18px;
}}

QLabel#devicePanelLabel {{
    color: {TEXT_TERTIARY};
    font-size: 10px;
    font-weight: 600;
}}

QLabel#devicePanelStatus {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

/* ------------------------------------------------------------------ */
/* Cabeçalho da página                                                 */
/* ------------------------------------------------------------------ */
QWidget#topBar {{
    background-color: transparent;
}}

QLabel#pageTitle {{
    font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
    font-size: 28px;
    font-weight: 600;
    color: #FFFFFF;
}}

QLabel#pageSubtitle {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

QFrame#statusDot {{
    background-color: {TEXT_TERTIARY};
    border-radius: 4px;
    min-width: 8px;
    max-width: 8px;
    min-height: 8px;
    max-height: 8px;
}}

QFrame#statusDot[state="off"] {{ background-color: {TEXT_TERTIARY}; }}
QFrame#statusDot[state="connecting"] {{ background-color: {ACCENT_TEXT}; }}
QFrame#statusDot[state="connected"] {{ background-color: {GREEN}; }}
QFrame#statusDot[state="warning"] {{ background-color: {YELLOW}; }}
QFrame#statusDot[state="error"] {{ background-color: {RED}; }}

QLabel#statusPill {{
    background-color: transparent;
    border: none;
    padding: 0;
    font-size: 13px;
    font-weight: 500;
    color: {TEXT_SECONDARY};
}}

QLabel#statusPill[state="connecting"] {{ color: {ACCENT_TEXT}; }}
QLabel#statusPill[state="connected"] {{ color: {GREEN}; }}
QLabel#statusPill[state="warning"] {{ color: {YELLOW}; }}
QLabel#statusPill[state="error"] {{ color: {RED}; }}

/* ------------------------------------------------------------------ */
/* Cartões                                                             */
/* ------------------------------------------------------------------ */
QFrame#hero {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #1B1B1F, stop: 1 #111113
    );
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 28px;
}}

QFrame#card {{
    background-color: {SURFACE};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 24px;
}}

QFrame#quickTile {{
    background-color: {SURFACE};
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 20px;
}}

QFrame#quickTile:hover {{
    background-color: {SURFACE_RAISED};
    border-color: {HAIRLINE};
}}

QFrame#adaptiveBox {{
    background-color: {TRACK};
    border: none;
    border-radius: 16px;
}}

QFrame#segmentTrack {{
    background-color: {TRACK};
    border: none;
    border-radius: 20px;
}}

QFrame#separator {{
    background-color: {HAIRLINE};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}

QFrame#vseparator {{
    background-color: {HAIRLINE};
    border: none;
    min-width: 1px;
    max-width: 1px;
}}

/* ------------------------------------------------------------------ */
/* Tipografia de conteúdo                                              */
/* ------------------------------------------------------------------ */
QLabel#sectionLabel {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
}}

QLabel#cardTitle {{
    font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
    font-size: 18px;
    font-weight: 600;
    color: #FFFFFF;
}}

QLabel#cardSubtitle {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}

QLabel#cardBadge {{
    color: {TEXT_TERTIARY};
    font-size: 10px;
    font-weight: 600;
}}

QLabel#heroEyebrow {{
    color: {TEXT_TERTIARY};
    font-size: 10px;
    font-weight: 600;
}}

QLabel#heroTitle {{
    font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
    font-size: 30px;
    font-weight: 600;
    color: #FFFFFF;
}}

QLabel#heroSubtitle {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QLabel#heroBattery {{
    font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
    font-size: 38px;
    font-weight: 600;
    color: #FFFFFF;
}}

QLabel#heroBatteryDetail {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel#rowTitle {{
    color: {TEXT};
    font-size: 14px;
}}

QLabel#rowSubtitle {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel#rowValue {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QLabel#strongValue {{
    font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
    font-size: 26px;
    font-weight: 600;
    color: #FFFFFF;
}}

QLabel#muted {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QLabel#small {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel#tiny {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
}}

QLabel#link {{
    color: {ACCENT_TEXT};
    font-size: 12px;
    font-weight: 500;
}}

QLabel#chargingBadge {{
    color: {YELLOW};
    background-color: rgba(255, 214, 10, 0.10);
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 600;
}}

QLabel#warnBadge {{
    color: {YELLOW};
    background-color: rgba(255, 214, 10, 0.08);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 12px;
}}

QLabel#featureValue {{
    color: {ACCENT_TEXT};
    font-size: 13px;
    font-weight: 500;
}}

QLabel#featureHint {{
    color: {TEXT_TERTIARY};
    font-size: 12px;
}}

QLabel#adaptiveValue {{
    color: {ACCENT_TEXT};
    font-size: 13px;
    font-weight: 500;
}}

/* ------------------------------------------------------------------ */
/* Botões                                                              */
/* ------------------------------------------------------------------ */
QPushButton {{
    background-color: {SURFACE_RAISED};
    border: 1px solid transparent;
    border-radius: 12px;
    padding: 8px 14px;
    color: {TEXT};
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {SURFACE_HOVER};
}}

QPushButton:pressed {{
    background-color: #17171A;
}}

QPushButton:disabled {{
    color: #4E4E56;
    background-color: #121214;
}}

QPushButton#primary {{
    background-color: {ACCENT};
    border: none;
    color: #FFFFFF;
    font-weight: 600;
    border-radius: 12px;
    padding: 9px 16px;
}}

QPushButton#primary:hover {{ background-color: #2B6FF8; }}
QPushButton#primary:pressed {{ background-color: #0847C5; }}
QPushButton#primary:disabled {{
    background-color: #14213A;
    color: #5A6B87;
}}

QPushButton#danger {{
    background-color: transparent;
    border: 1px solid rgba(255, 69, 58, 0.34);
    color: #FF7A72;
    font-weight: 600;
}}

QPushButton#danger:hover {{
    background-color: rgba(255, 69, 58, 0.09);
    border-color: rgba(255, 69, 58, 0.55);
}}

QPushButton#ghost {{
    background-color: transparent;
    border: none;
    color: {TEXT_SECONDARY};
    padding: 7px 10px;
}}

QPushButton#ghost:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    color: {TEXT};
}}

QPushButton#iconButton {{
    background-color: transparent;
    border: 1px solid {HAIRLINE};
    border-radius: 11px;
    padding: 0;
}}

QPushButton#iconButton:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    border-color: {HAIRLINE_STRONG};
}}

QPushButton#linkButton {{
    background-color: transparent;
    border: none;
    color: {ACCENT_TEXT};
    font-size: 12px;
    font-weight: 500;
    padding: 4px 2px;
    text-align: right;
}}

QPushButton#linkButton:hover {{ color: #A9C9FF; }}

QPushButton#linkButton:checked {{ color: {ACCENT_TEXT}; }}

QPushButton#linkButton:disabled {{ color: #4E4E56; }}

/* Segment control de três estados (controle de ruído) */
QToolButton#segment {{
    background-color: transparent;
    border: none;
    border-radius: 16px;
    padding: 9px 4px 8px 4px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
}}

QToolButton#segment:hover {{
    background-color: rgba(255, 255, 255, 0.04);
    color: {TEXT};
}}

QToolButton#segment:checked {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT_TEXT};
    font-weight: 600;
}}

QToolButton#segment:disabled {{
    color: #4E4E56;
}}

/* Chips de subnível */
QPushButton#levelChip {{
    background-color: {SURFACE_RAISED};
    border: none;
    border-radius: 11px;
    padding: 6px 13px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
}}

QPushButton#levelChip:hover {{
    background-color: {SURFACE_HOVER};
    color: {TEXT};
}}

QPushButton#levelChip:checked {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT_TEXT};
    font-weight: 600;
}}

QPushButton#levelChip:disabled {{
    background-color: #121214;
    color: #4E4E56;
}}

/* Chips de perfil / modo */
QPushButton#chip {{
    background-color: {SURFACE_RAISED};
    border: none;
    border-radius: 14px;
    padding: 12px 10px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#chip:hover {{
    background-color: {SURFACE_HOVER};
    color: {TEXT};
}}

QPushButton#chip:checked {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT_TEXT};
    font-weight: 600;
}}

QPushButton#chip:disabled {{
    background-color: #111113;
    color: #4E4E56;
}}

/* Chips com ícone (modos espaciais) */
QToolButton#chip {{
    background-color: {SURFACE_RAISED};
    border: none;
    border-radius: 14px;
    padding: 9px 8px 7px 8px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 500;
}}

QToolButton#chip:hover {{
    background-color: {SURFACE_HOVER};
    color: {TEXT};
}}

QToolButton#chip:checked {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT_TEXT};
    font-weight: 600;
}}

QToolButton#chip:disabled {{
    background-color: #111113;
    color: #4E4E56;
}}

/* ------------------------------------------------------------------ */
/* Combos                                                              */
/* ------------------------------------------------------------------ */
QComboBox QAbstractItemView {{
    background-color: {SURFACE_RAISED};
    border: 1px solid {HAIRLINE};
    border-radius: 12px;
    padding: 5px;
    outline: none;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT_TEXT};
}}

QComboBox QAbstractItemView::item {{
    min-height: 30px;
    padding: 2px 8px;
    border-radius: 8px;
    color: {TEXT};
}}

/* ------------------------------------------------------------------ */
/* Slider                                                              */
/* ------------------------------------------------------------------ */
QSlider {{
    min-height: 22px;
    max-height: 22px;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background-color: #2A2A30;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background-color: {ACCENT};
    border-radius: 3px;
}}

QSlider::add-page:horizontal {{
    background-color: #2A2A30;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 20px;
    height: 20px;
    margin: -7px 0;
    border-radius: 10px;
    background-color: #FFFFFF;
    border: none;
}}

QSlider::handle:horizontal:hover {{
    background-color: #F2F2F7;
}}

QSlider::handle:horizontal:disabled {{
    background-color: #4E4E56;
}}

QSlider::sub-page:horizontal:disabled {{
    background-color: #233C66;
}}

QSlider::add-page:horizontal:disabled {{
    background-color: #1A1A1E;
}}

/* ------------------------------------------------------------------ */
/* Barra de bateria                                                    */
/* ------------------------------------------------------------------ */
QProgressBar {{
    background-color: #2A2A30;
    border: none;
    border-radius: 3px;
    min-height: 4px;
    max-height: 4px;
}}

QProgressBar::chunk {{
    background-color: #30D158;
    border-radius: 3px;
}}

/* ------------------------------------------------------------------ */
/* Log de atividade                                                    */
/* ------------------------------------------------------------------ */
QTextEdit#activityLog {{
    background-color: #0C0C0E;
    border: 1px solid #1C1C20;
    border-radius: 16px;
    padding: 12px 14px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    color: {TEXT_SECONDARY};
    selection-background-color: {ACCENT_SOFT};
}}

/* ------------------------------------------------------------------ */
/* Abas de ajustes (a barra de abas é escondida no código)             */
/* ------------------------------------------------------------------ */
QTabWidget#featureTabs::pane {{
    background-color: transparent;
    border: none;
    top: 0;
}}

QTabWidget#featureTabs QTabBar {{
    background-color: transparent;
}}

/* ------------------------------------------------------------------ */
/* Rolagem                                                             */
/* ------------------------------------------------------------------ */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 0;
}}

QScrollBar::handle:vertical {{
    background: #2C2C33;
    min-height: 30px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #3A3A42;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background: #2C2C33;
    min-width: 30px;
    border-radius: 4px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ------------------------------------------------------------------ */
/* Menus, diálogos e barra de status                                   */
/* ------------------------------------------------------------------ */
QMenuBar {{
    background-color: {BACKGROUND};
    color: {TEXT_SECONDARY};
}}

QMenu {{
    background-color: {SURFACE_RAISED};
    border: 1px solid {HAIRLINE};
    border-radius: 12px;
    padding: 6px;
}}

QMenu::item {{
    padding: 7px 22px 7px 12px;
    border-radius: 8px;
    color: {TEXT};
    font-size: 13px;
}}

QMenu::item:selected {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT_TEXT};
}}

QMenu::separator {{
    height: 1px;
    background-color: {HAIRLINE};
    margin: 5px 8px;
}}

QFrame#statusBar {{
    background-color: transparent;
    border-top: 1px solid {HAIRLINE};
}}

QLabel#statusText {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
}}

QMessageBox {{
    background-color: {SURFACE};
}}

QMessageBox QLabel {{
    color: {TEXT};
}}
"""
