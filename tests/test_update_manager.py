from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.update_manager import (
    RELEASE_ASSET_NAME,
    bundled_build_version,
    download_release_asset,
    fetch_release_status,
    is_newer_version,
    launch_update_replacement,
    release_from_payload,
)


def release_payload(
    data: bytes = b"portable exe",
    version: str = "2.10",
) -> dict:
    digest = hashlib.sha256(data).hexdigest()
    return {
        "tag_name": version,
        "html_url": (
            "https://github.com/atalaydenknalbant/"
            f"autosubscriber-youtube/releases/tag/{version}"
        ),
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": RELEASE_ASSET_NAME,
                "state": "uploaded",
                "size": len(data),
                "digest": f"sha256:{digest}",
                "browser_download_url": (
                    "https://github.com/atalaydenknalbant/"
                    f"autosubscriber-youtube/releases/download/{version}/"
                    "AutosubscriberApp.exe"
                ),
            }
        ],
    }


class DownloadResponse:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.position = 0

    def __enter__(self) -> "DownloadResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.data) - self.position
        chunk = self.data[self.position : self.position + size]
        self.position += len(chunk)
        return chunk


def json_response(payload) -> DownloadResponse:
    return DownloadResponse(json.dumps(payload).encode("utf-8"))


def test_numeric_versions_are_compared_by_component() -> None:
    assert is_newer_version("2.10", "2.9")
    assert not is_newer_version("2.9", "2.9")
    assert not is_newer_version("2.9.0", "2.9")


def test_release_parser_selects_exact_verified_executable() -> None:
    release = release_from_payload(release_payload())

    assert release.version == "2.10"
    assert release.asset_name == "AutosubscriberApp.exe"
    assert len(release.sha256) == 64


def test_release_parser_rejects_asset_without_digest() -> None:
    payload = release_payload()
    payload["assets"][0]["digest"] = None

    with pytest.raises(ValueError, match="SHA256"):
        release_from_payload(payload)


def test_release_status_identifies_current_executable_with_latest_request(
    tmp_path: Path,
) -> None:
    executable_data = b"published current executable"
    executable = tmp_path / "AutosubscriberApp.exe"
    executable.write_bytes(executable_data)
    requests: list[str] = []

    def opener(request, **_kwargs):
        requests.append(request.full_url)
        return json_response(release_payload(executable_data, "2.9"))

    status = fetch_release_status(executable, opener)

    assert status.installed_version == "2.9"
    assert status.installed_from_release_asset is True
    assert status.latest.version == "2.9"
    assert len(requests) == 1


def test_release_status_finds_older_executable_in_release_history(
    tmp_path: Path,
) -> None:
    latest_data = b"latest executable"
    installed_data = b"older executable"
    executable = tmp_path / "AutosubscriberApp.exe"
    executable.write_bytes(installed_data)
    latest_payload = release_payload(latest_data, "2.10")
    old_payload = release_payload(installed_data, "2.9")

    def opener(request, **_kwargs):
        if request.full_url.endswith("/releases/latest"):
            return json_response(latest_payload)
        return json_response([latest_payload, old_payload])

    status = fetch_release_status(executable, opener)

    assert status.installed_version == "2.9"
    assert status.installed_from_release_asset is True
    assert status.latest.version == "2.10"


def test_release_status_does_not_guess_unpublished_build_version(
    tmp_path: Path,
) -> None:
    latest_payload = release_payload(b"latest executable", "2.10")
    executable = tmp_path / "AutosubscriberApp.exe"
    executable.write_bytes(b"unpublished local build")

    def opener(request, **_kwargs):
        if request.full_url.endswith("/releases/latest"):
            return json_response(latest_payload)
        return json_response([latest_payload])

    status = fetch_release_status(executable, opener)

    assert status.installed_version is None
    assert status.latest.version == "2.10"


def test_release_status_uses_generated_build_baseline_for_local_exe(
    tmp_path: Path,
) -> None:
    latest_payload = release_payload(b"latest executable", "2.10")
    executable = tmp_path / "AutosubscriberApp.exe"
    executable.write_bytes(b"unpublished local build")

    def opener(request, **_kwargs):
        if request.full_url.endswith("/releases/latest"):
            return json_response(latest_payload)
        return json_response([latest_payload])

    status = fetch_release_status(
        executable,
        opener,
        build_version="2.9",
    )

    assert status.installed_version == "2.9"
    assert status.installed_from_release_asset is False
    assert is_newer_version(status.latest.version, status.installed_version)


def test_bundled_build_version_reads_generated_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    metadata = tmp_path / "app/build_metadata.json"
    metadata.parent.mkdir()
    metadata.write_text(
        json.dumps({"base_release_version": "2.9"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.update_manager.sys._MEIPASS", str(tmp_path), raising=False)

    assert bundled_build_version() == "2.9"


def test_download_verifies_size_and_digest(tmp_path: Path) -> None:
    data = b"verified portable executable"
    release = release_from_payload(release_payload(data))
    progress: list[int] = []

    path = download_release_asset(
        release,
        tmp_path,
        progress.append,
        opener=lambda *_args, **_kwargs: DownloadResponse(data),
    )

    assert path.read_bytes() == data
    assert progress[-1] == 100
    assert not list(tmp_path.glob("*.part"))


def test_download_reuses_verified_staged_executable(tmp_path: Path) -> None:
    data = b"already verified executable"
    release = release_from_payload(release_payload(data))
    path = tmp_path / f"AutosubscriberApp-{release.version}.exe"
    path.write_bytes(data)
    progress: list[int] = []

    def fail_opener(*_args, **_kwargs):
        raise AssertionError(
            "A verified staged update must not be downloaded again"
        )

    result = download_release_asset(
        release,
        tmp_path,
        progress.append,
        opener=fail_opener,
    )

    assert result == path
    assert progress == [100]


def test_download_removes_partial_file_after_digest_failure(tmp_path: Path) -> None:
    expected = b"expected executable"
    actual = b"tampered executable"
    payload = release_payload(expected)
    payload["assets"][0]["size"] = len(actual)
    release = release_from_payload(payload)

    with pytest.raises(ValueError, match="SHA256"):
        download_release_asset(
            release,
            tmp_path,
            opener=lambda *_args, **_kwargs: DownloadResponse(actual),
        )

    assert not list(tmp_path.iterdir())


def test_replacement_helper_receives_verified_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "downloaded.exe"
    target = tmp_path / "AutosubscriberApp.exe"
    source.write_bytes(b"new executable")
    calls: list[tuple[list[str], dict]] = []
    monkeypatch.setattr(
        "app.update_manager.update_staging_directory",
        lambda: tmp_path,
    )

    script_path = launch_update_replacement(
        source,
        target,
        "a" * 64,
        wait_pid=1234,
        launcher=lambda command, **kwargs: calls.append((command, kwargs)),
    )

    command, options = calls[0]
    assert script_path.is_file()
    assert command[0] == "powershell.exe"
    assert command[command.index("-WaitPid") + 1] == "1234"
    assert command[command.index("-Source") + 1] == str(source.resolve())
    assert command[command.index("-Target") + 1] == str(target.resolve())
    assert options["close_fds"] is True
    assert "-WindowStyle Hidden" not in script_path.read_text(encoding="utf-8")
