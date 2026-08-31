from __future__ import annotations

import ctypes
import logging
import time
from typing import Any, Protocol
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal


class ChromeBackend(Protocol):
    def find_browser_pids(self, token: str) -> set[int]: ...

    def enumerate_windows(self, pids: set[int]) -> list[int]: ...

    def hide_process_windows(self, pids: set[int]) -> None: ...

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
    DWM_TNP_RECTDESTINATION = 0x00000001
    DWM_TNP_OPACITY = 0x00000004
    DWM_TNP_VISIBLE = 0x00000008
    DWM_TNP_SOURCECLIENTAREAONLY = 0x00000010
    GA_ROOT = 2

    class DwmThumbnailProperties(ctypes.Structure):
        _fields_ = [
            ("dwFlags", wintypes.DWORD),
            ("rcDestination", wintypes.RECT),
            ("rcSource", wintypes.RECT),
            ("opacity", wintypes.BYTE),
            ("fVisible", wintypes.BOOL),
            ("fSourceClientAreaOnly", wintypes.BOOL),
        ]

    def __init__(self) -> None:
        self._thumbnails: dict[int, tuple[int, int, int]] = {}

    @staticmethod
    def _dwm_api():
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        dwmapi.DwmRegisterThumbnail.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        dwmapi.DwmRegisterThumbnail.restype = wintypes.LONG
        dwmapi.DwmUnregisterThumbnail.argtypes = [wintypes.HANDLE]
        dwmapi.DwmUnregisterThumbnail.restype = wintypes.LONG
        dwmapi.DwmUpdateThumbnailProperties.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Win32ChromeBackend.DwmThumbnailProperties),
        ]
        dwmapi.DwmUpdateThumbnailProperties.restype = wintypes.LONG
        return dwmapi

    @staticmethod
    def _check_dwm_result(result: int, operation: str) -> None:
        if result != 0:
            unsigned_result = result & 0xFFFFFFFF
            raise OSError(
                f"{operation} failed with HRESULT 0x{unsigned_result:08X}"
            )

    @staticmethod
    def _source_size_for_host(width: int, height: int) -> tuple[int, int]:
        width = max(1, width)
        height = max(1, height)
        if height > 220:
            return width, height

        scale = max(
            (960 + width - 1) // width,
            (540 + height - 1) // height,
        )
        return width * scale, height * scale

    @staticmethod
    def find_browser_pids(token: str) -> set[int]:
        psutil, _, _, _ = _import_windows_modules()
        matched: set[int] = set()

        for process in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                process_name = process.info.get("name")
                process_command = process.info.get("cmdline")
                name = process_name.lower() if process_name is not None else ""
                command = (
                    " ".join(process_command)
                    if process_command is not None
                    else ""
                )
                if "chrome" not in name:
                    continue
                if token not in command:
                    continue
                matched.add(int(process.info["pid"]))
                matched.update(child.pid for child in process.children(recursive=True))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return matched

    @staticmethod
    def enumerate_windows(pids: set[int]) -> list[int]:
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

    @staticmethod
    def hide_process_windows(pids: set[int]) -> None:
        if not pids:
            return

        _, win32con, win32gui, win32process = _import_windows_modules()

        def callback(hwnd: int, _extra: Any) -> bool:
            _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if window_pid not in pids:
                return True
            window_class = win32gui.GetClassName(hwnd)
            if not window_class.startswith("Chrome_WidgetWin_"):
                return True

            extended_style = win32gui.GetWindowLong(
                hwnd,
                win32con.GWL_EXSTYLE,
            )
            desired_style = extended_style & ~win32con.WS_EX_APPWINDOW
            desired_style |= (
                win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
            )
            style_changed = desired_style != extended_style
            is_visible = bool(win32gui.IsWindowVisible(hwnd))
            if not style_changed and not is_visible:
                return True
            if style_changed:
                win32gui.SetWindowLong(
                    hwnd,
                    win32con.GWL_EXSTYLE,
                    desired_style,
                )
            if is_visible:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            win32gui.SetWindowPos(
                hwnd,
                None,
                -32000,
                -32000,
                1,
                1,
                win32con.SWP_NOZORDER
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_FRAMECHANGED,
            )
            return True

        win32gui.EnumWindows(callback, None)
    def attach(self, hwnd: int, parent_hwnd: int) -> None:
        _, win32con, win32gui, _ = _import_windows_modules()
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindow(parent_hwnd):
            raise OSError("Chrome or browser host window is no longer available")

        extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        extended_style &= ~win32con.WS_EX_APPWINDOW
        extended_style |= win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, extended_style)

        root_hwnd = int(win32gui.GetAncestor(parent_hwnd, self.GA_ROOT))
        if not root_hwnd:
            raise OSError("Application preview window is no longer available")

        existing = self._thumbnails.get(hwnd)
        if existing and existing[1] == parent_hwnd and existing[2] == root_hwnd:
            self.resize(hwnd, parent_hwnd)
            return
        if existing:
            self._unregister_thumbnail(hwnd)

        thumbnail = wintypes.HANDLE()
        result = self._dwm_api().DwmRegisterThumbnail(
            root_hwnd,
            hwnd,
            ctypes.byref(thumbnail),
        )
        self._check_dwm_result(result, "DwmRegisterThumbnail")
        if not thumbnail.value:
            raise OSError("DwmRegisterThumbnail returned an empty handle")

        self._thumbnails[hwnd] = (
            int(thumbnail.value),
            int(parent_hwnd),
            root_hwnd,
        )
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
        self._move_source_offscreen(hwnd)
        self.resize(hwnd, parent_hwnd)

    def _unregister_thumbnail(self, hwnd: int) -> None:
        thumbnail_data = self._thumbnails.pop(hwnd, None)
        if not thumbnail_data:
            return
        result = self._dwm_api().DwmUnregisterThumbnail(
            wintypes.HANDLE(thumbnail_data[0])
        )
        if result != 0:
            logging.info(
                "[AppEmbed] DwmUnregisterThumbnail failed for hwnd=%s",
                hwnd,
            )

    @staticmethod
    def _move_source_offscreen(hwnd: int) -> None:
        Win32ChromeBackend._resize_source_offscreen(hwnd, 640, 480)

    @staticmethod
    def _resize_source_offscreen(hwnd: int, width: int, height: int) -> None:
        _, win32con, win32gui, _ = _import_windows_modules()
        if not win32gui.IsWindow(hwnd):
            return
        win32gui.SetWindowPos(
            hwnd,
            None,
            -32000,
            -32000,
            max(1, width),
            max(1, height),
            win32con.SWP_NOZORDER
            | win32con.SWP_NOACTIVATE
            | win32con.SWP_FRAMECHANGED,
        )

    def detach_to_offscreen(self, hwnd: int) -> None:
        self._unregister_thumbnail(hwnd)
        self._move_source_offscreen(hwnd)

    def resize(self, hwnd: int, parent_hwnd: int) -> None:
        _, _, win32gui, _ = _import_windows_modules()
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindow(parent_hwnd):
            return

        thumbnail_data = self._thumbnails.get(hwnd)
        if not thumbnail_data or thumbnail_data[1] != parent_hwnd:
            return
        thumbnail_handle, _, root_hwnd = thumbnail_data
        if not win32gui.IsWindow(root_hwnd):
            return

        left, top, right, bottom = win32gui.GetClientRect(parent_hwnd)
        host_width = right - left
        host_height = bottom - top
        source_width, source_height = self._source_size_for_host(
            host_width,
            host_height,
        )
        self._resize_source_offscreen(
            hwnd,
            source_width,
            source_height,
        )
        screen_left, screen_top = win32gui.ClientToScreen(parent_hwnd, (left, top))
        screen_right, screen_bottom = win32gui.ClientToScreen(
            parent_hwnd,
            (right, bottom),
        )
        destination_left, destination_top = win32gui.ScreenToClient(
            root_hwnd,
            (screen_left, screen_top),
        )
        destination_right, destination_bottom = win32gui.ScreenToClient(
            root_hwnd,
            (screen_right, screen_bottom),
        )

        properties = self.DwmThumbnailProperties(
            self.DWM_TNP_RECTDESTINATION
            | self.DWM_TNP_OPACITY
            | self.DWM_TNP_VISIBLE
            | self.DWM_TNP_SOURCECLIENTAREAONLY,
            wintypes.RECT(
                destination_left,
                destination_top,
                destination_right,
                destination_bottom,
            ),
            wintypes.RECT(),
            255,
            True,
            True,
        )
        result = self._dwm_api().DwmUpdateThumbnailProperties(
            wintypes.HANDLE(thumbnail_handle),
            ctypes.byref(properties),
        )
        self._check_dwm_result(result, "DwmUpdateThumbnailProperties")


class _BrowserPidCache:
    def __init__(
        self,
        token: str,
        backend: ChromeBackend,
        refresh_ms: int,
    ) -> None:
        self.token = token
        self.backend = backend
        self.refresh_seconds = max(0.1, refresh_ms / 1000)
        self.pids: set[int] = set()
        self.next_refresh = 0.0

    def get(self) -> set[int]:
        now = time.monotonic()
        if not self.pids or now >= self.next_refresh:
            self.pids = self.backend.find_browser_pids(self.token)
            self.next_refresh = now + self.refresh_seconds
        return set(self.pids)

    def clear(self) -> None:
        self.pids.clear()
        self.next_refresh = 0.0


class ChromeWindowMonitor(QObject):
    windowsChanged = Signal(list)
    fatalError = Signal(str)

    def __init__(
        self,
        token: str,
        backend: ChromeBackend | None = None,
        parent: QObject | None = None,
        interval_ms: int = 500,
        pid_refresh_ms: int = 5_000,
    ) -> None:
        super().__init__(parent)
        self.token = token
        self.backend = backend or Win32ChromeBackend()
        self._pid_cache = _BrowserPidCache(
            token,
            self.backend,
            pid_refresh_ms,
        )
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
        self._pid_cache.clear()

    def scan(self) -> list[int]:
        try:
            pids = self._pid_cache.get()
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


class HeadlessChromeWindowGuard(QObject):
    def __init__(
        self,
        token: str,
        backend: ChromeBackend | None = None,
        parent: QObject | None = None,
        interval_ms: int = 250,
        pid_refresh_ms: int = 5_000,
    ) -> None:
        super().__init__(parent)
        self.token = token
        self.backend = backend or Win32ChromeBackend()
        self._pid_cache = _BrowserPidCache(
            token,
            self.backend,
            pid_refresh_ms,
        )
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.scan)

    def start(self) -> None:
        self.scan()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._pid_cache.clear()

    def scan(self) -> None:
        try:
            pids = self._pid_cache.get()
            self.backend.hide_process_windows(pids)
        except Exception as scan_ex:
            logging.info(
                "[AppHeadless] Chrome window hiding skipped: %s",
                type(scan_ex).__name__,
            )
