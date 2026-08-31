from __future__ import annotations

from pathlib import Path
from typing import Literal

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QWidget,
)

from app.theme import Colors


IconName = Literal["play", "stop", "settings", "folder", "broom", "refresh"]


class GradientHeader(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(76)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0.0, QColor("#1C2029"))
        gradient.setColorAt(0.58, QColor("#101218"))
        gradient.setColorAt(1.0, QColor("#2B0A0D"))
        painter.fillRect(self.rect(), gradient)
        painter.fillRect(0, self.height() - 2, self.width(), 2, QColor(Colors.RED))


class SiteLogoButton(QToolButton):
    def __init__(
        self,
        site_id: str,
        logo_path: Path,
        label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(label)
        self.site_id = site_id
        self.setObjectName("siteLogoButton")
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(126, 88)
        self.setIcon(QIcon(str(logo_path)))
        self.setIconSize(QSize(92, 42))
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(12)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(self._shadow)

    def set_selected(self, selected: bool) -> None:
        self.setChecked(selected)
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self._shadow.setBlurRadius(24 if selected else 12)
        self._shadow.setColor(
            QColor(255, 32, 38, 130) if selected else QColor(0, 0, 0, 150)
        )


class AnimatedSwitch(QAbstractButton):
    checkedChanged = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(64, 34)
        self._offset = 4.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self._animate_to_state)

    def sizeHint(self) -> QSize:
        return QSize(64, 34)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        if self.signalsBlocked() or not self.isVisible():
            self._animation.stop()
            self.set_offset(34.0 if checked else 4.0)

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def _animate_to_state(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(34.0 if checked else 4.0)
        self._animation.start()
        self.checkedChanged.emit(checked)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = QRectF(1, 1, 62, 32)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(Colors.RED_DARK if self.isChecked() else "#343A46"))
        painter.drawRoundedRect(track, 16, 16)
        painter.setBrush(QColor(Colors.WHITE))
        painter.drawEllipse(QRectF(self._offset, 4, 26, 26))


class ActivityRing(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(34, 34)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(32)
        self._timer.timeout.connect(self._advance)

    @property
    def is_active(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self._angle = 0
        self.update()

    def _advance(self) -> None:
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.rect().center())
        painter.rotate(self._angle)
        gradient = QConicalGradient(QPointF(0, 0), 0)
        gradient.setColorAt(0.0, QColor(Colors.RED))
        gradient.setColorAt(0.72, QColor(Colors.RED_DARK))
        gradient.setColorAt(1.0, QColor(Colors.RED_MUTED))
        pen = QPen(gradient, 4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(QRectF(-12, -12, 24, 24), 20 * 16, 292 * 16)


class IconButton(QPushButton):
    def __init__(
        self,
        icon_name: IconName,
        tooltip: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.icon_name = icon_name
        self.setToolTip(tooltip)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(44, 44)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(Colors.RED if self.isEnabled() else "#626977")
        painter.setPen(QPen(color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(color)
        center = self.rect().center()

        if self.icon_name == "play":
            path = QPainterPath()
            path.moveTo(center.x() - 6, center.y() - 9)
            path.lineTo(center.x() + 9, center.y())
            path.lineTo(center.x() - 6, center.y() + 9)
            path.closeSubpath()
            painter.drawPath(path)
        elif self.icon_name == "stop":
            painter.drawRoundedRect(QRectF(center.x() - 8, center.y() - 8, 16, 16), 2, 2)
        elif self.icon_name == "settings":
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(center.x() - 9, center.y() - 9, 18, 18))
            painter.drawEllipse(QRectF(center.x() - 3, center.y() - 3, 6, 6))
        elif self.icon_name == "folder":
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(center.x() - 10, center.y() - 7, 20, 15), 2, 2)
            painter.drawLine(center.x() - 8, center.y() - 7, center.x() - 2, center.y() - 11)
            painter.drawLine(center.x() - 2, center.y() - 11, center.x() + 3, center.y() - 7)
        elif self.icon_name == "broom":
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(
                center.x() + 8,
                center.y() - 10,
                center.x() - 2,
                center.y() + 1,
            )
            painter.setBrush(color)
            brush = QPainterPath()
            brush.moveTo(center.x() - 3, center.y())
            brush.lineTo(center.x() - 10, center.y() + 6)
            brush.lineTo(center.x() - 4, center.y() + 11)
            brush.lineTo(center.x() + 3, center.y() + 4)
            brush.closeSubpath()
            painter.drawPath(brush)
            painter.drawLine(
                center.x() - 8,
                center.y() + 5,
                center.x() - 2,
                center.y() + 10,
            )
        elif self.icon_name == "refresh":
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(
                QRectF(center.x() - 9, center.y() - 9, 18, 18),
                35 * 16,
                285 * 16,
            )
            painter.setBrush(color)
            arrow = QPainterPath()
            arrow.moveTo(center.x() + 9, center.y() - 7)
            arrow.lineTo(center.x() + 10, center.y() + 1)
            arrow.lineTo(center.x() + 3, center.y() - 2)
            arrow.closeSubpath()
            painter.drawPath(arrow)


class StatusDisplay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.ring = ActivityRing(self)
        self.ring.hide()
        self.label = QLabel("Ready", self)
        self.label.setStyleSheet(f"color: {Colors.MUTED}; font-weight: 600;")
        layout.addWidget(self.ring)
        layout.addWidget(self.label)

    def set_running(self, site_name: str) -> None:
        self.label.setText(f"Running {site_name}")
        self.label.setStyleSheet(f"color: {Colors.WHITE}; font-weight: 600;")
        self.ring.start()

    def set_stopping(self) -> None:
        self.label.setText("Stopping")

    def set_ready(self, message: str = "Ready") -> None:
        self.ring.stop()
        self.ring.hide()
        self.label.setText(message)
        self.label.setStyleSheet(f"color: {Colors.MUTED}; font-weight: 600;")


class LogView(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setFont(QFont("Cascadia Mono", 9))
        self.document().setMaximumBlockCount(10_000)
        self.setStyleSheet(
            f"background-color: {Colors.DEEP}; color: {Colors.TEXT};"
            f"border: 1px solid {Colors.BORDER_SOFT}; border-radius: 8px; padding: 10px;"
        )

    @staticmethod
    def _line_color(line: str) -> QColor:
        upper = line.upper()
        if " ERROR " in upper or "[FAILURE]" in upper:
            return QColor(Colors.ERROR)
        if " WARNING " in upper:
            return QColor(Colors.WARNING)
        if " INFO " in upper:
            return QColor(Colors.TEXT)
        return QColor(Colors.MUTED)

    def append_line(self, line: str) -> None:
        scroll_bar = self.verticalScrollBar()
        at_bottom = scroll_bar.value() >= scroll_bar.maximum() - 2
        original_cursor = self.textCursor()
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.End)
        if not self.document().isEmpty():
            cursor.insertBlock()
        text_format = QTextCharFormat()
        text_format.setForeground(self._line_color(line))
        cursor.insertText(line.rstrip("\r\n"), text_format)

        if at_bottom:
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
        else:
            self.setTextCursor(original_cursor)
