from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from app.main_window import MainWindow, build_worker_invocation
from app.update_manager import ReleaseInfo, ReleaseStatus, UpdateManager


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


def test_header_shows_versions_and_manual_update_control(
    qapp,
    config_path: Path,
) -> None:
    manager = UpdateManager()
    checks: list[bool] = []
    manager.check_for_updates = lambda: checks.append(True) or True
    window = MainWindow(
        config_path=config_path,
        browser_backend=FakeBackend(),
        update_manager=manager,
        auto_check_updates=False,
    )

    assert window.installed_version_label.text() == "App detecting"
    assert window.latest_version_label.text() == "Latest checking"
    assert window.update_button.icon_name == "refresh"

    window.update_button.click()

    assert checks == [True]
    window.close()


def test_startup_automatically_checks_for_updates(
    qapp,
    config_path: Path,
) -> None:
    manager = UpdateManager()
    checks: list[bool] = []
    manager.check_for_updates = lambda: checks.append(True) or True
    window = MainWindow(
        config_path=config_path,
        browser_backend=FakeBackend(),
        update_manager=manager,
    )

    assert window._startup_update_timer is not None
    assert window._startup_update_timer.isActive()
    assert window._startup_update_timer.isSingleShot()
    assert window._startup_update_timer.interval() == 800
    window._startup_update_check()
    assert checks == [True]
    window.close()


def test_detected_gui_version_downloads_newer_online_release(
    qapp,
    config_path: Path,
    monkeypatch,
) -> None:
    manager = UpdateManager()
    downloads: list[ReleaseInfo] = []
    manager.download_update = lambda release: downloads.append(release) or True
    window = MainWindow(
        config_path=config_path,
        browser_backend=FakeBackend(),
        update_manager=manager,
        auto_check_updates=False,
    )
    release = ReleaseInfo(
        version="2.10",
        page_url="https://github.com/example/release",
        asset_url="https://github.com/example/AutosubscriberApp.exe",
        asset_name="AutosubscriberApp.exe",
        asset_size=100,
        sha256="a" * 64,
    )
    monkeypatch.setattr(
        "app.main_window.can_replace_current_executable",
        lambda: True,
    )

    window._update_check_succeeded(
        ReleaseStatus(latest=release, installed_version="2.9")
    )

    assert window.installed_version_label.text() == "App 2.9 local"
    assert window.latest_version_label.text() == "Latest 2.10"
    assert downloads == [release]
    window.close()


def test_update_download_locks_run_controls(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(
        config_path=config_path,
        browser_backend=FakeBackend(),
        auto_check_updates=False,
    )
    release = ReleaseInfo(
        version="3.1",
        page_url="https://github.com/example/release",
        asset_url="https://github.com/example/AutosubscriberApp.exe",
        asset_name="AutosubscriberApp.exe",
        asset_size=100,
        sha256="a" * 64,
    )

    window._update_download_started(release)

    assert window._update_in_progress is True
    assert window.start_button.isEnabled() is False
    assert window.headless_switch.isEnabled() is False
    assert all(not button.isEnabled() for button in window.site_buttons.values())

    window._update_download_failed("network unavailable")

    assert window._update_in_progress is False
    assert window.start_button.isEnabled() is True
    window.close()


def test_update_stops_active_website_before_installing(
    qapp,
    config_path: Path,
    monkeypatch,
) -> None:
    window = MainWindow(
        config_path=config_path,
        browser_backend=FakeBackend(),
        auto_check_updates=False,
    )
    release = ReleaseInfo(
        version="3.1",
        page_url="https://github.com/example/release",
        asset_url="https://github.com/example/AutosubscriberApp.exe",
        asset_name="AutosubscriberApp.exe",
        asset_size=100,
        sha256="a" * 64,
    )
    stopped: list[bool] = []
    window.worker = object()
    monkeypatch.setattr(window, "_stop_worker", lambda: stopped.append(True))

    window._update_download_started(release)

    assert stopped == [True]
    window.worker = None
    window.close()


def test_normal_close_does_not_install_a_pending_update(
    qapp,
    config_path: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    window = MainWindow(
        config_path=config_path,
        browser_backend=FakeBackend(),
        auto_check_updates=False,
    )
    release = ReleaseInfo(
        version="3.1",
        page_url="https://github.com/example/release",
        asset_url="https://github.com/example/AutosubscriberApp.exe",
        asset_name="AutosubscriberApp.exe",
        asset_size=100,
        sha256="a" * 64,
    )
    window._pending_update = (tmp_path / "update.exe", release)
    launches: list[bool] = []
    monkeypatch.setattr(
        window,
        "_launch_pending_update_replacement",
        lambda: launches.append(True) or True,
    )

    window.close()

    assert launches == []


def test_narrow_header_keeps_debug_screenshots_label_visible(
    qapp,
    config_path: Path,
) -> None:
    window = MainWindow(
        config_path=config_path,
        browser_backend=FakeBackend(),
        auto_check_updates=False,
    )
    window.resize(1100, 720)
    window.show()
    qapp.processEvents()

    assert window._header_compact is True
    assert window.debug_screenshots_label.text() == "Debug screenshots"
    assert window.debug_screenshots_label.width() == 112
    ordered_widgets = [
        window.status_display,
        window.header_version_widget,
        window.update_button,
        window.header_action_bar,
    ]
    positions = [
        window.header_layout.getItemPosition(
            window.header_layout.indexOf(widget)
        )
        for widget in ordered_widgets
    ]
    assert [position[0] for position in positions] == [0, 0, 0, 0]
    assert [position[1] for position in positions] == [3, 4, 5, 6]
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
