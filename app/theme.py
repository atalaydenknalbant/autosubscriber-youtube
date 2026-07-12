from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


class Colors:
    BLACK = "#07080B"
    DEEP = "#0D0F14"
    PANEL = "#13161D"
    PANEL_RAISED = "#1B1F29"
    BORDER = "#2B303C"
    BORDER_SOFT = "#212631"
    RED = "#FF2026"
    RED_DARK = "#B8060B"
    RED_MUTED = "#4A171A"
    WHITE = "#F7F8FB"
    TEXT = "#E8EAF0"
    MUTED = "#969EAD"
    SUCCESS = "#43D17C"
    WARNING = "#FFB84A"
    ERROR = "#FF5B61"


APP_STYLESHEET = f"""
QWidget {{
    background-color: {Colors.BLACK};
    color: {Colors.TEXT};
    font-family: "Segoe UI";
    font-size: 10pt;
}}
QLabel {{
    background-color: transparent;
}}
QToolTip {{
    background-color: {Colors.PANEL_RAISED};
    color: {Colors.WHITE};
    border: 1px solid {Colors.BORDER};
    padding: 6px;
}}
QPushButton {{
    background-color: {Colors.PANEL_RAISED};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    color: {Colors.TEXT};
    padding: 8px 12px;
}}
QPushButton:hover {{
    background-color: #252A35;
    border-color: #3A414F;
}}
QPushButton:pressed {{
    background-color: {Colors.RED_MUTED};
    border-color: {Colors.RED};
}}
QPushButton:disabled {{
    color: #626977;
    background-color: #111319;
    border-color: #1D212A;
}}
QLineEdit, QPlainTextEdit {{
    background-color: #0B0D12;
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    color: {Colors.WHITE};
    selection-background-color: {Colors.RED_DARK};
    padding: 8px;
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border-color: {Colors.RED};
}}
QScrollBar:vertical {{
    background: {Colors.DEEP};
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3A404D;
    border-radius: 5px;
    min-height: 28px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QLabel#sectionTitle {{
    color: {Colors.WHITE};
    font-size: 12pt;
    font-weight: 600;
}}
QLabel#mutedLabel {{
    color: {Colors.MUTED};
}}
QFrame#contentPanel {{
    background-color: {Colors.PANEL};
    border: 1px solid {Colors.BORDER_SOFT};
    border-radius: 8px;
}}
QToolButton#siteLogoButton {{
    background-color: {Colors.PANEL};
    border: 1px solid {Colors.BORDER_SOFT};
    border-radius: 8px;
    color: {Colors.MUTED};
    font-weight: 600;
    padding: 6px;
}}
QToolButton#siteLogoButton:hover {{
    background-color: {Colors.PANEL_RAISED};
    border-color: #4A5262;
    color: {Colors.WHITE};
}}
QToolButton#siteLogoButton[selected="true"] {{
    background-color: #211316;
    border: 2px solid {Colors.RED};
    color: {Colors.WHITE};
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(Colors.BLACK))
    palette.setColor(QPalette.WindowText, QColor(Colors.TEXT))
    palette.setColor(QPalette.Base, QColor(Colors.DEEP))
    palette.setColor(QPalette.AlternateBase, QColor(Colors.PANEL))
    palette.setColor(QPalette.Text, QColor(Colors.TEXT))
    palette.setColor(QPalette.Button, QColor(Colors.PANEL_RAISED))
    palette.setColor(QPalette.ButtonText, QColor(Colors.TEXT))
    palette.setColor(QPalette.Highlight, QColor(Colors.RED_DARK))
    palette.setColor(QPalette.HighlightedText, QColor(Colors.WHITE))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLESHEET)
