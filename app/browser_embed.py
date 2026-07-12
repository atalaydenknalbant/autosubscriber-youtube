from __future__ import annotations

import logging
import threading
import time
from typing import Any, Protocol

from PySide6.QtCore import QObject, QTimer, Signal


class ChromeBackend(Protocol):
    def find_browser_pids(self, token: str) -> set[int]: ...

    def enumerate_windows(self, pids: set[int]) -> list[int]: ...

    def attach(self, hwnd: int, parent_hwnd: int) -> None: ...

    def detach_to_offscreen(self, hwnd: int) -> None: ...

    def resize(self, hwnd: int, parent_hwnd: int) -> None: ...


def _import_windows_modules():
    import psutil
    import win32con
    import win32gui
    import win32process

    return psutil, win32con, win32gui, win32process


class Win32ChromeBackend:
    def find_browser_pids(self, token: str) -> set[int]:
        psutil, _, _, _ = _import_windows_modules()
        matched: set[int] = set()

        for process in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (process.info.get("name") or "").lower()
                command = " ".join(process.info.get("cmdline") or [])
                if "chrome" not in name or token not in command:
                    continue
                matched.add(int(process.info["pid"]))
                matched.update(child.pid for child in process.children(recursive=True))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return matched

    def enumerate_windows(self, pids: set[int]) -> list[int]:
        if not pids:
            return []

        _, _, win32gui, win32process = _import_windows_modules()
        matches: list[int] = []

        def callback(hwnd: int, _extra: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if window_pid not in pids:
                return True
            if not win32gui.GetWindowText(hwnd).strip():
                return True
            window_class = win32gui.GetClassName(hwnd)
            if not window_class.startswith("Chrome_WidgetWin_"):
                return True
            matches.append(int(hwnd))
            return True

        win32gui.EnumWindows(callback, None)
        return matches

    def attach(self, hwnd: int, parent_hwnd: int) -> None:
        _, win32con, win32gui, _ = _import_windows_modules()
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindow(parent_hwnd):
            raise OSError("Chrome or browser host window is no longer available")

        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style &= ~(
            win32con.WS_POPUP
            | win32con.WS_CAPTION
            | win32con.WS_THICKFRAME
            | win32con.WS_MINIMIZEBOX
            | win32con.WS_MAXIMIZEBOX
            | win32con.WS_SYSMENU
        )
        style |= win32con.WS_CHILD | win32con.WS_CLIPSIBLINGS | win32con.WS_CLIPCHILDREN
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

        extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        extended_style &= ~win32con.WS_EX_APPWINDOW
        extended_style |= win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, extended_style)

        win32gui.SetParent(hwnd, int(parent_hwnd))
        win32gui.EnableWindow(hwnd, False)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
        self.resize(hwnd, parent_hwnd)

    def detach_to_offscreen(self, hwnd: int) -> None:
        _, win32con, win32gui, _ = _import_windows_modules()
        if not win32gui.IsWindow(hwnd):
            return
        win32gui.SetWindowPos(
            hwnd,
            None,
            -32000,
            -32000,
            640,
            480,
            win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
        )

    def resize(self, hwnd: int, parent_hwnd: int) -> None:
        _, win32con, win32gui, _ = _import_windows_modules()
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindow(parent_hwnd):
            return
        left, top, right, bottom = win32gui.GetClientRect(parent_hwnd)
        width = max(1, right - left)
        height = max(1, bottom - top)
        win32gui.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            width,
            height,
            win32con.SWP_NOZORDER
            | win32con.SWP_NOACTIVATE
            | win32con.SWP_FRAMECHANGED,
        )


class ChromeWindowMonitor(QObject):
    windowsChanged = Signal(list)
    fatalError = Signal(str)

    def __init__(
        self,
        token: str,
        backend: ChromeBackend | None = None,
        parent: QObject | None = None,
        interval_ms: int = 250,
    ) -> None:
        super().__init__(parent)
        self.token = token
        self.backend = backend or Win32ChromeBackend()
        self._order: dict[int, int] = {}
        self._next_order = 0
        self._windows: list[int] = []
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.scan)

    @property
    def windows(self) -> list[int]:
        return list(self._windows)

    def start(self) -> None:
        self.scan()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._windows = []
        self._order.clear()

    def scan(self) -> list[int]:
        try:
            pids = self.backend.find_browser_pids(self.token)
            discovered = list(dict.fromkeys(self.backend.enumerate_windows(pids)))
        except Exception as scan_ex:
            message = f"Chrome window discovery failed: {type(scan_ex).__name__}"
            logging.info("[AppEmbed] %s", message)
            self.fatalError.emit(message)
            return self.windows

        active = set(discovered)
        for hwnd in tuple(self._order):
            if hwnd not in active:
                del self._order[hwnd]

        for hwnd in discovered:
            if hwnd not in self._order:
                self._order[hwnd] = self._next_order
                self._next_order += 1

        ordered = sorted(discovered, key=self._order.__getitem__)
        if ordered != self._windows:
            self._windows = ordered
            self.windowsChanged.emit(self.windows)
        return self.windows


def _compatibility_resize_loop(
    backend: Win32ChromeBackend,
    parent_hwnd: int,
    child_hwnd: int,
) -> None:
    _, _, win32gui, _ = _import_windows_modules()
    while win32gui.IsWindow(parent_hwnd) and win32gui.IsWindow(child_hwnd):
        backend.resize(child_hwnd, parent_hwnd)
        time.sleep(0.5)


def embed_driver_chrome(
    _driver: Any,
    parent_hwnd: int,
    token: str,
) -> int | None:
    """Compatibility path for the old Tkinter shell during the Qt migration."""
    backend = Win32ChromeBackend()
    chrome_hwnd = None
    chrome_pid = None

    for _attempt in range(30):
        pids = backend.find_browser_pids(token)
        windows = backend.enumerate_windows(pids)
        if windows:
            chrome_hwnd = windows[0]
            chrome_pid = next(iter(pids), None)
            break
        time.sleep(0.5)

    if chrome_hwnd is None:
        logging.info("[AppEmbed] Could not find Chrome window for embedding")
        return None

    backend.attach(chrome_hwnd, int(parent_hwnd))
    thread = threading.Thread(
        target=_compatibility_resize_loop,
        args=(backend, int(parent_hwnd), chrome_hwnd),
        daemon=True,
    )
    thread.start()
    logging.info("[AppEmbed] Embedded Chrome hwnd=%s pid=%s", chrome_hwnd, chrome_pid)
    return chrome_hwnd
