import os
import sys
from types import SimpleNamespace
from pathlib import Path

import selenium_codes
from selenium.common.exceptions import (
    InvalidSessionIdException,
    SessionNotCreatedException,
)

from app import worker


def test_runtime_check_does_not_require_site(monkeypatch) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(
        worker,
        "verify_packaged_runtime",
        lambda: calls.append(True),
    )

    assert worker.main(["--check-runtime"]) == 0
    assert calls == [True]


def test_chrome_recovery_reason_distinguishes_profile_lock() -> None:
    profile_error = SessionNotCreatedException(
        "Could not remove old devtools port file for user-data-dir"
    )
    disconnected_error = InvalidSessionIdException("not connected to DevTools")

    assert worker.chrome_recovery_reason(profile_error) == (
        "Chrome profile startup lock detected"
    )
    assert worker.chrome_recovery_reason(disconnected_error) == (
        "Chrome restarted or disconnected during startup"
    )


def test_debug_runtime_directory_is_created_beside_executable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    original_directory = Path.cwd()
    runtime_root = tmp_path / "portable"
    monkeypatch.setattr(worker, "find_runtime_root", lambda: runtime_root)

    try:
        worker.prepare_runtime_directory(debug_screenshots=True)

        assert Path.cwd() == runtime_root
        assert (runtime_root / "screenshots/debug").is_dir()
    finally:
        os.chdir(original_directory)


def test_session_creation_failure_refreshes_driver_and_retries_once(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def site_function(_req_dict: dict) -> None:
        calls.append("run")
        if calls.count("run") == 1:
            raise SessionNotCreatedException("Chrome instance exited")

    selenium_module = SimpleNamespace(
        youlikehits_functions=site_function,
        recover_chrome_after_update=lambda _req_dict: calls.append("recover"),
    )
    monkeypatch.setitem(
        sys.modules,
        "selenium_codes.sub4sub_websites_selenium",
        selenium_module,
    )
    monkeypatch.setattr(
        selenium_codes,
        "sub4sub_websites_selenium",
        selenium_module,
        raising=False,
    )
    monkeypatch.setattr(worker, "find_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(worker, "config_validation_errors", lambda _site: [])
    monkeypatch.setattr(worker, "build_required_dict", lambda *args, **kwargs: {})

    original_directory = Path.cwd()
    try:
        result = worker.main(["--site", "youlikehits"])
    finally:
        os.chdir(original_directory)

    assert result == 0
    assert calls == ["run", "recover", "run"]


def test_early_invalid_session_recovers_and_retries_once(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def site_function(_req_dict: dict) -> None:
        calls.append("run")
        if calls.count("run") == 1:
            raise InvalidSessionIdException("not connected to DevTools")

    selenium_module = SimpleNamespace(
        youlikehits_functions=site_function,
        recover_chrome_after_update=lambda _req_dict: calls.append("recover"),
    )
    monkeypatch.setitem(
        sys.modules,
        "selenium_codes.sub4sub_websites_selenium",
        selenium_module,
    )
    monkeypatch.setattr(
        selenium_codes,
        "sub4sub_websites_selenium",
        selenium_module,
        raising=False,
    )
    monkeypatch.setattr(worker, "find_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(worker, "config_validation_errors", lambda _site: [])
    monkeypatch.setattr(worker, "build_required_dict", lambda *args, **kwargs: {})

    original_directory = Path.cwd()
    try:
        result = worker.main(["--site", "youlikehits"])
    finally:
        os.chdir(original_directory)

    assert result == 0
    assert calls == ["run", "recover", "run"]
