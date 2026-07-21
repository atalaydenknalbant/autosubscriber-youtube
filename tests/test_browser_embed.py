import inspect

from app.browser_embed import (
    ChromeWindowMonitor,
    HeadlessChromeWindowGuard,
    Win32ChromeBackend,
)
from app.worker import build_parser


class FakeBackend:
    def __init__(self) -> None:
        self.pids = {101}
        self.windows = [1001]

    def find_browser_pids(self, _token: str) -> set[int]:
        return set(self.pids)

    def enumerate_windows(self, _pids: set[int]) -> list[int]:
        return list(self.windows)

    def hide_process_windows(self, pids: set[int]) -> None:
        self.hidden_pids = set(pids)


def test_monitor_tracks_new_and_closed_windows(qapp) -> None:
    backend = FakeBackend()
    monitor = ChromeWindowMonitor("token", backend)

    assert monitor.scan() == [1001]

    backend.windows = [1001, 1002]
    assert monitor.scan() == [1001, 1002]

    backend.windows = [1002]
    assert monitor.scan() == [1002]


def test_monitor_keeps_first_discovery_order(qapp) -> None:
    backend = FakeBackend()
    backend.windows = [1002, 1001]
    monitor = ChromeWindowMonitor("token", backend)

    assert monitor.scan() == [1002, 1001]

    backend.windows = [1001, 1002, 1003]
    assert monitor.scan() == [1002, 1001, 1003]


def test_headless_guard_hides_windows_for_matching_processes(qapp) -> None:
    backend = FakeBackend()
    backend.hidden_pids = set()
    guard = HeadlessChromeWindowGuard("token", backend)

    guard.scan()

    assert backend.hidden_pids == {101}


def test_worker_parser_accepts_main_process_embed_token() -> None:
    args = build_parser().parse_args(
        [
            "--site",
            "youlikehits",
            "--headless",
            "false",
            "--embed-token",
            "run-token",
        ]
    )

    assert args.embed_token == "run-token"


def test_win32_backend_stateless_helpers_are_static() -> None:
    for method_name in (
        "find_browser_pids",
        "enumerate_windows",
        "hide_process_windows",
        "_move_source_offscreen",
        "_resize_source_offscreen",
    ):
        descriptor = inspect.getattr_static(Win32ChromeBackend, method_name)
        assert isinstance(descriptor, staticmethod)


def test_win32_backend_tracks_live_thumbnail_state() -> None:
    backend = Win32ChromeBackend()

    assert backend._thumbnails == {}


def test_main_preview_uses_host_dimensions() -> None:
    assert Win32ChromeBackend._source_size_for_host(600, 720) == (600, 720)


def test_small_preview_uses_large_matching_source_ratio() -> None:
    source_width, source_height = Win32ChromeBackend._source_size_for_host(
        280,
        160,
    )

    assert source_width >= 960
    assert source_height >= 540
    assert source_width / source_height == 280 / 160
