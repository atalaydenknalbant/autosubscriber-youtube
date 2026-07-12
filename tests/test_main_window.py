from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from app.main_window import MainWindow, build_worker_invocation


class FakeBackend:
    def find_browser_pids(self, _token: str) -> set[int]:
        return set()

    def enumerate_windows(self, _pids: set[int]) -> list[int]:
        return []

    def attach(self, _hwnd: int, _parent_hwnd: int) -> None:
        return None

    def detach_to_offscreen(self, _hwnd: int) -> None:
        return None

    def resize(self, _hwnd: int, _parent_hwnd: int) -> None:
        return None


def test_visible_worker_receives_token() -> None:
    _program, args = build_worker_invocation(
        "youlikehits",
        headless=False,
        debug_screenshots=True,
        token="run-token",
        frozen=False,
    )

    assert args[args.index("--headless") + 1] == "false"
    assert args[args.index("--debug-screenshots") + 1] == "true"
    assert args[args.index("--embed-token") + 1] == "run-token"


def test_headless_worker_has_no_embed_token() -> None:
    _program, args = build_worker_invocation(
        "youlikehits",
        headless=True,
        token=None,
        frozen=True,
    )

    assert "--embed-token" not in args
    assert args[0] == "--worker"


def test_main_window_uses_logo_selection_and_screenshot_control(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())

    assert len(window.site_buttons) == 6
    assert not hasattr(window, "debug_text")
    assert hasattr(window, "debug_screenshots_switch")


def test_headless_state_controls_browser_panel_visibility(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())

    window.set_headless(False, animated=False)
    assert window.browser_panel.isHidden() is False

    window.set_headless(True, animated=False)
    assert window.browser_panel.isHidden() is True


def test_visible_mode_allocates_a_usable_browser_width(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())
    window.resize(1200, 760)
    window.show()
    qapp.processEvents()

    window.set_headless(False, animated=False)
    qapp.processEvents()

    assert window.content_splitter.sizes()[1] >= 420
    window.close()


def test_missing_config_prompt_creates_default_and_opens_editor(
    qapp,
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "portable/config.ini"
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())
    opened: list[Path] = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(
        window,
        "_open_config_editor",
        lambda: opened.append(window.config_path),
    )

    window._prompt_create_config()

    assert config_path.is_file()
    assert opened == [config_path]
    window.close()
