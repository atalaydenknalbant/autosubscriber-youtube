from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from app.main_window import MainWindow, build_worker_invocation


class FakeBackend:
    def find_browser_pids(self, _token: str) -> set[int]:
        return set()

    def enumerate_windows(self, _pids: set[int]) -> list[int]:
        return []

    def hide_process_windows(self, _pids: set[int]) -> None:
        return None

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


def test_headless_worker_receives_window_hiding_token() -> None:
    _program, args = build_worker_invocation(
        "youlikehits",
        headless=True,
        token="headless-token",
        frozen=True,
    )

    assert args[args.index("--embed-token") + 1] == "headless-token"
    assert args[0] == "--worker"


def test_main_window_uses_logo_selection_and_screenshot_control(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())

    assert len(window.site_buttons) == 6
    assert not hasattr(window, "debug_text")
    assert hasattr(window, "debug_screenshots_switch")
    window.close()


def test_run_controls_are_hosted_in_header(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())

    header_controls = window.findChild(QWidget, "headerControls")

    assert header_controls is not None
    assert window.headless_switch.parent() is header_controls
    assert window.debug_screenshots_switch.parent() is header_controls
    assert window.start_button.parent() is header_controls
    assert window.stop_button.parent() is header_controls
    assert window.clear_logs_button.icon_name == "broom"
    window.close()


def test_headless_state_controls_browser_panel_visibility(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())

    window.set_headless(False, animated=False)
    assert window.browser_panel.isHidden() is False

    window.set_headless(True, animated=False)
    assert window.browser_panel.isHidden() is True
    window.close()


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


def test_site_selector_can_collapse_and_restore(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())

    window._set_site_selector_visible(False, animated=False)
    assert window.site_selector_panel.isHidden() is True
    assert window.site_selector_panel.maximumHeight() == 0

    window._set_site_selector_visible(True, animated=False)
    assert window.site_selector_panel.isHidden() is False
    assert window.site_selector_panel.maximumHeight() == 16_777_215
    window.close()


def test_site_selector_animation_restores_logo_buttons(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(config_path=config_path, browser_backend=FakeBackend())
    window.show()
    qapp.processEvents()

    window._set_site_selector_visible(False, animated=True)
    assert window._site_selector_animation is not None
    window._site_selector_animation.setCurrentTime(
        window._site_selector_animation.duration()
    )
    assert window.site_selector_panel.isHidden() is True

    window._set_site_selector_visible(True, animated=True)
    assert window._site_selector_animation is not None
    window._site_selector_animation.setCurrentTime(
        window._site_selector_animation.duration()
    )

    assert window.site_selector_panel.isVisible() is True
    assert all(button.isVisible() for button in window.site_buttons.values())
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
