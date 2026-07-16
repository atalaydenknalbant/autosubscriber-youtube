from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.browser_embed import ChromeBackend
from app.theme import Colors


class InputShield(QWidget):
    INPUT_EVENTS = {
        QEvent.MouseButtonPress,
        QEvent.MouseButtonRelease,
        QEvent.MouseButtonDblClick,
        QEvent.MouseMove,
        QEvent.Wheel,
        QEvent.KeyPress,
        QEvent.KeyRelease,
        QEvent.ContextMenu,
        QEvent.DragEnter,
        QEvent.DragMove,
        QEvent.Drop,
    }

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.ArrowCursor)
        self.setToolTip("Live Selenium preview. User input is disabled.")
        self.show()

    def event(self, event) -> bool:
        if event.type() in self.INPUT_EVENTS:
            event.accept()
            return True
        return super().event(event)


class ChromeHost(QFrame):
    def __init__(
        self,
        resize_callback: Callable[[int, int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.hwnd: int | None = None
        self._resize_callback = resize_callback
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setObjectName("chromeHost")
        self.setMinimumSize(180, 120)
        self.setStyleSheet(
            f"QFrame#chromeHost {{ background: {Colors.DEEP};"
            f"border: 1px solid {Colors.BORDER}; border-radius: 6px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.placeholder = QLabel("Waiting for Chrome", self)
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"color: {Colors.MUTED};")
        layout.addWidget(self.placeholder)

        self.shield = InputShield(self)
        self.shield.raise_()

    @property
    def parent_hwnd(self) -> int:
        return int(self.winId())

    def assign(self, hwnd: int) -> None:
        self.hwnd = hwnd
        self.placeholder.hide()
        self.shield.setGeometry(self.rect())
        self.shield.raise_()

    def release(self) -> None:
        self.hwnd = None
        self.placeholder.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.shield.setGeometry(self.rect())
        self.shield.raise_()
        if self.hwnd is not None:
            self._resize_callback(self.hwnd, self.parent_hwnd)


class PreviewTile(QFrame):
    def __init__(
        self,
        index: int,
        host: ChromeHost,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.host = host
        self.setObjectName("previewTile")
        self.setStyleSheet(
            f"QFrame#previewTile {{ background: {Colors.PANEL_RAISED};"
            f"border: 1px solid {Colors.BORDER}; border-radius: 7px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)
        label = QLabel(f"Window {index}", self)
        label.setStyleSheet(f"color: {Colors.MUTED}; font-size: 8pt;")
        layout.addWidget(label)
        layout.addWidget(host, 1)
        self.setMaximumHeight(176)


class BrowserPanel(QFrame):
    embeddingFailed = Signal(str)

    def __init__(
        self,
        backend: ChromeBackend,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.backend = backend
        self.main_hwnd: int | None = None
        self.preview_hwnds: list[int] = []
        self._preview_tiles: dict[int, PreviewTile] = {}
        self._attach_deadlines: dict[int, float] = {}
        self._animations: list[QAbstractAnimation] = []
        self._containment_timer = QTimer(self)
        self._containment_timer.setInterval(1000)
        self._containment_timer.timeout.connect(self.refresh_containment)
        self._containment_timer.start()

        self.setObjectName("contentPanel")
        self.setMinimumWidth(420)
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.preview_scroll = QScrollArea(self)
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setFrameShape(QFrame.NoFrame)
        self.preview_scroll.setFixedWidth(210)
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_container = QWidget(self.preview_scroll)
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(8)
        self.preview_layout.addStretch(1)
        self.preview_scroll.setWidget(self.preview_container)
        self.preview_scroll.hide()
        root.addWidget(self.preview_scroll)

        self.main_host = ChromeHost(self.backend.resize, self)
        root.addWidget(self.main_host, 1)

    def set_windows(self, hwnds: list[int]) -> None:
        ordered = list(dict.fromkeys(hwnds))
        desired_main = ordered[0] if ordered else None
        desired_previews = ordered[1:]
        desired_set = set(ordered)
        previous_set = {
            hwnd
            for hwnd in [self.main_hwnd, *self.preview_hwnds]
            if hwnd is not None
        }

        for stale_hwnd in previous_set - desired_set:
            self.backend.detach_to_offscreen(stale_hwnd)
            self._attach_deadlines.pop(stale_hwnd, None)

        if self.main_hwnd != desired_main:
            if desired_main in self._preview_tiles:
                self._remove_preview(desired_main, detach=False)
            self.main_host.release()
            self.main_hwnd = desired_main
            if desired_main is not None:
                self.main_host.assign(desired_main)
                self._attach(self.main_host, desired_main)

        for hwnd in tuple(self._preview_tiles):
            if hwnd not in desired_previews:
                self._remove_preview(hwnd, detach=hwnd not in desired_set)

        for index, hwnd in enumerate(desired_previews, start=2):
            if hwnd in self._preview_tiles:
                continue
            self._add_preview(hwnd, index)

        self.preview_hwnds = desired_previews
        self.preview_scroll.setVisible(bool(self.preview_hwnds))

    def refresh_containment(self) -> None:
        """Keep every real Chrome source offscreen while its preview is active."""
        hosted = [
            hwnd
            for hwnd in [self.main_hwnd, *self.preview_hwnds]
            if hwnd is not None
        ]
        for hwnd in hosted:
            host = self._host_for(hwnd)
            if host is None:
                continue
            try:
                self.backend.resize(hwnd, host.parent_hwnd)
            except OSError:
                continue

    def clear_windows(self) -> None:
        hosted = [
            hwnd
            for hwnd in [self.main_hwnd, *self.preview_hwnds]
            if hwnd is not None
        ]
        for hwnd in hosted:
            self.backend.detach_to_offscreen(hwnd)
        self._attach_deadlines.clear()
        self.main_hwnd = None
        self.main_host.release()
        for hwnd in tuple(self._preview_tiles):
            self._remove_preview(hwnd, detach=False, animate=False)
        self.preview_hwnds = []
        self.preview_scroll.hide()

    def _add_preview(self, hwnd: int, index: int) -> None:
        host = ChromeHost(self.backend.resize, self.preview_container)
        host.assign(hwnd)
        tile = PreviewTile(index, host, self.preview_container)
        self._preview_tiles[hwnd] = tile
        self.preview_layout.insertWidget(self.preview_layout.count() - 1, tile)
        self._attach(host, hwnd)
        self._animate_tile_in(tile)

    def _remove_preview(
        self,
        hwnd: int,
        *,
        detach: bool,
        animate: bool = True,
    ) -> None:
        tile = self._preview_tiles.pop(hwnd, None)
        if tile is None:
            return
        if detach:
            self.backend.detach_to_offscreen(hwnd)
        tile.host.release()
        if animate:
            self._animate_tile_out(tile)
        else:
            tile.deleteLater()

    def _host_for(self, hwnd: int) -> ChromeHost | None:
        if self.main_hwnd == hwnd:
            return self.main_host
        tile = self._preview_tiles.get(hwnd)
        return tile.host if tile else None

    def _attach(self, host: ChromeHost, hwnd: int) -> None:
        deadline = self._attach_deadlines.setdefault(hwnd, time.monotonic() + 3.0)
        try:
            self.backend.attach(hwnd, host.parent_hwnd)
        except Exception as attach_ex:
            self.backend.detach_to_offscreen(hwnd)
            if time.monotonic() >= deadline:
                self._attach_deadlines.pop(hwnd, None)
                self.embeddingFailed.emit(
                    f"Could not contain Chrome window {hwnd}: {type(attach_ex).__name__}"
                )
                return
            QTimer.singleShot(100, lambda: self._retry_attach(hwnd, host))
            return
        self._attach_deadlines.pop(hwnd, None)
        host.shield.raise_()

    def _retry_attach(self, hwnd: int, expected_host: ChromeHost) -> None:
        if self._host_for(hwnd) is expected_host:
            self._attach(expected_host, hwnd)

    def _keep_animation(self, animation: QAbstractAnimation) -> None:
        self._animations.append(animation)
        animation.finished.connect(lambda: self._animations.remove(animation))
        animation.start()

    def _animate_tile_in(self, tile: PreviewTile) -> None:
        target_height = tile.maximumHeight()
        tile.setMaximumHeight(0)
        effect = QGraphicsOpacityEffect(tile)
        effect.setOpacity(0.0)
        tile.setGraphicsEffect(effect)
        group = QParallelAnimationGroup(tile)
        height = QPropertyAnimation(tile, b"maximumHeight", group)
        height.setDuration(220)
        height.setStartValue(0)
        height.setEndValue(target_height)
        height.setEasingCurve(QEasingCurve.OutCubic)
        opacity = QPropertyAnimation(effect, b"opacity", group)
        opacity.setDuration(180)
        opacity.setStartValue(0.0)
        opacity.setEndValue(1.0)
        group.addAnimation(height)
        group.addAnimation(opacity)
        self._keep_animation(group)

    def _animate_tile_out(self, tile: PreviewTile) -> None:
        effect = tile.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(tile)
            tile.setGraphicsEffect(effect)
        group = QParallelAnimationGroup(tile)
        height = QPropertyAnimation(tile, b"maximumHeight", group)
        height.setDuration(180)
        height.setStartValue(tile.height())
        height.setEndValue(0)
        opacity = QPropertyAnimation(effect, b"opacity", group)
        opacity.setDuration(150)
        opacity.setStartValue(effect.opacity())
        opacity.setEndValue(0.0)
        group.addAnimation(height)
        group.addAnimation(opacity)
        group.finished.connect(tile.deleteLater)
        self._keep_animation(group)
