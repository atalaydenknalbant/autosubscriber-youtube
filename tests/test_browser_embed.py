from app.browser_embed import ChromeWindowMonitor
from app.worker import build_parser


class FakeBackend:
    def __init__(self) -> None:
        self.pids = {101}
        self.windows = [1001]

    def find_browser_pids(self, _token: str) -> set[int]:
        return set(self.pids)

    def enumerate_windows(self, _pids: set[int]) -> list[int]:
        return list(self.windows)


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
