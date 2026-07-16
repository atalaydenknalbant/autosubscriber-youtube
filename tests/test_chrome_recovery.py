from pathlib import Path

from selenium.common.exceptions import (
    InvalidSessionIdException,
    SessionNotCreatedException,
    TimeoutException,
)

from selenium_codes import sub4sub_websites_selenium as sws


def test_chrome_startup_exception_classification() -> None:
    assert sws.is_chrome_startup_recovery_exception(
        SessionNotCreatedException("Chrome instance exited")
    )
    assert sws.is_chrome_startup_recovery_exception(
        InvalidSessionIdException("not connected to DevTools")
    )
    assert not sws.is_chrome_startup_recovery_exception(TimeoutException())


def test_remove_stale_devtools_port_from_profile_root_and_child(
    tmp_path: Path,
) -> None:
    profile_root = tmp_path / "ChromeProfile"
    profile_child = profile_root / "Default"
    profile_child.mkdir(parents=True)
    root_port = profile_root / "DevToolsActivePort"
    child_port = profile_child / "DevToolsActivePort"
    root_port.write_text("root", encoding="utf-8")
    child_port.write_text("child", encoding="utf-8")

    removed = sws._remove_stale_devtools_port(
        {"chrome_userdata_directory": str(profile_root)}
    )

    assert removed == 2
    assert not root_port.exists()
    assert not child_port.exists()


def test_recovery_waits_for_chrome_then_cleans_once(monkeypatch) -> None:
    calls: list[str] = []
    process_states = iter((True, True, False))

    monkeypatch.setattr(
        sws,
        "_windows_process_is_running",
        lambda _name: next(process_states),
    )
    monkeypatch.setattr(
        sws,
        "close_existing_chrome_processes",
        lambda: calls.append("close"),
    )
    monkeypatch.setattr(
        sws,
        "_remove_stale_devtools_port",
        lambda _req_dict: calls.append("port") or 1,
    )
    monkeypatch.setattr(
        sws,
        "refresh_selenium_driver_cache",
        lambda: calls.append("refresh"),
    )
    monkeypatch.setattr(sws.EVENT, "wait", lambda _seconds: calls.append("wait"))

    sws.recover_chrome_after_update({}, wait_timeout_seconds=10, poll_seconds=1)

    assert calls == ["wait", "close", "port", "refresh", "wait"]
