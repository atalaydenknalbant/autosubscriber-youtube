from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, Signal


GITHUB_REPOSITORY = "atalaydenknalbant/autosubscriber-youtube"
LATEST_RELEASE_API = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
RELEASES_API = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases?per_page=100"
)
RELEASE_ASSET_NAME = "AutosubscriberApp.exe"
REQUEST_TIMEOUT_SECONDS = 30
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    page_url: str
    asset_url: str
    asset_name: str
    asset_size: int
    sha256: str


@dataclass(frozen=True)
class ReleaseStatus:
    latest: ReleaseInfo
    installed_version: str | None
    installed_from_release_asset: bool = False


def version_key(value: str) -> tuple[int, ...]:
    normalized = value.strip().removeprefix("v").removeprefix("V")
    if not re.fullmatch(r"\d+(?:\.\d+)*", normalized):
        raise ValueError(f"Unsupported release version: {value!r}")
    parts = [int(part) for part in normalized.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def is_newer_version(candidate: str, current: str) -> bool:
    candidate_parts = version_key(candidate)
    current_parts = version_key(current)
    width = max(len(candidate_parts), len(current_parts))
    return candidate_parts + (0,) * (width - len(candidate_parts)) > (
        current_parts + (0,) * (width - len(current_parts))
    )


def release_from_payload(payload: dict[str, Any]) -> ReleaseInfo:
    if payload.get("draft") or payload.get("prerelease"):
        raise ValueError("The latest GitHub release is not a stable published release.")

    tag = str(payload.get("tag_name") or "").strip()
    version_key(tag)
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ValueError("The GitHub release does not contain an asset list.")

    asset = next(
        (
            item
            for item in assets
            if isinstance(item, dict)
            and item.get("name") == RELEASE_ASSET_NAME
            and item.get("state") == "uploaded"
        ),
        None,
    )
    if asset is None:
        raise ValueError(
            f"The release does not contain {RELEASE_ASSET_NAME}."
        )

    asset_url = str(asset.get("browser_download_url") or "").strip()
    parsed_url = urlparse(asset_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "github.com":
        raise ValueError("The release asset URL is not a trusted GitHub HTTPS URL.")

    digest = str(asset.get("digest") or "").strip().lower()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("The release asset does not provide a valid SHA256 digest.")

    asset_size = int(asset.get("size") or 0)
    if asset_size <= 0:
        raise ValueError("The release asset size is invalid.")

    return ReleaseInfo(
        version=tag.removeprefix("v").removeprefix("V"),
        page_url=str(payload.get("html_url") or "").strip(),
        asset_url=asset_url,
        asset_name=RELEASE_ASSET_NAME,
        asset_size=asset_size,
        sha256=digest.removeprefix("sha256:"),
    )


def _fetch_github_json(url: str, opener: Callable[..., Any]) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AutosubscriberApp",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def fetch_latest_release(
    opener: Callable[..., Any] = urlopen,
) -> ReleaseInfo:
    payload = _fetch_github_json(LATEST_RELEASE_API, opener)
    if not isinstance(payload, dict):
        raise ValueError("GitHub returned an invalid release response.")
    return release_from_payload(payload)


def fetch_release_history(
    opener: Callable[..., Any] = urlopen,
) -> list[ReleaseInfo]:
    payload = _fetch_github_json(RELEASES_API, opener)
    if not isinstance(payload, list):
        raise ValueError("GitHub returned an invalid release history response.")
    releases: list[ReleaseInfo] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            releases.append(release_from_payload(item))
        except ValueError:
            continue
    return releases


def update_staging_directory() -> Path:
    path = Path(tempfile.gettempdir()) / "AutosubscriberApp" / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(DOWNLOAD_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def bundled_build_version() -> str | None:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is None:
        return None
    metadata_path = Path(bundle_root) / "app" / "build_metadata.json"
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        version = str(payload.get("base_release_version") or "").strip()
        version_key(version)
    except (AttributeError, OSError, ValueError):
        return None
    return version.removeprefix("v").removeprefix("V")


def fetch_release_status(
    executable_path: Path | None,
    opener: Callable[..., Any] = urlopen,
    *,
    build_version: str | None = None,
) -> ReleaseStatus:
    latest = fetch_latest_release(opener)
    if executable_path is None or not executable_path.is_file():
        return ReleaseStatus(latest=latest, installed_version=build_version)

    executable_digest = _file_sha256(executable_path).lower()
    if executable_digest == latest.sha256.lower():
        return ReleaseStatus(
            latest=latest,
            installed_version=latest.version,
            installed_from_release_asset=True,
        )

    installed_release = next(
        (
            release
            for release in fetch_release_history(opener)
            if release.sha256.lower() == executable_digest
        ),
        None,
    )
    return ReleaseStatus(
        latest=latest,
        installed_version=(
            installed_release.version
            if installed_release is not None
            else build_version
        ),
        installed_from_release_asset=installed_release is not None,
    )


def download_release_asset(
    release: ReleaseInfo,
    destination_directory: Path | None = None,
    progress: Callable[[int], None] | None = None,
    opener: Callable[..., Any] = urlopen,
) -> Path:
    destination = destination_directory or update_staging_directory()
    destination.mkdir(parents=True, exist_ok=True)
    final_path = destination / f"AutosubscriberApp-{release.version}.exe"
    partial_path = final_path.with_suffix(".exe.part")
    partial_path.unlink(missing_ok=True)
    if (
        final_path.is_file()
        and final_path.stat().st_size == release.asset_size
        and _file_sha256(final_path).lower() == release.sha256.lower()
    ):
        if progress is not None:
            progress(100)
        return final_path
    final_path.unlink(missing_ok=True)

    request = Request(
        release.asset_url,
        headers={"User-Agent": "AutosubscriberApp"},
    )
    digest = hashlib.sha256()
    downloaded = 0
    try:
        with opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            with partial_path.open("wb") as output:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if progress is not None:
                        progress(min(100, int(downloaded * 100 / release.asset_size)))

        if downloaded != release.asset_size:
            raise ValueError(
                "The downloaded update size does not match the GitHub release asset."
            )
        if digest.hexdigest().lower() != release.sha256.lower():
            raise ValueError("The downloaded update failed SHA256 verification.")
        os.replace(partial_path, final_path)
        if progress is not None:
            progress(100)
        return final_path
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise


def can_replace_current_executable() -> bool:
    return (
        sys.platform == "win32"
        and bool(getattr(sys, "frozen", False))
        and Path(sys.executable).suffix.casefold() == ".exe"
    )


def _update_script_text() -> str:
    return r"""
param(
    [Parameter(Mandatory=$true)][int]$WaitPid,
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Target,
    [Parameter(Mandatory=$true)][string]$ExpectedSha256,
    [Parameter(Mandatory=$true)][string]$LogPath
)
$ErrorActionPreference = 'Stop'
$backup = "$Target.update-backup"
try {
    Wait-Process -Id $WaitPid -ErrorAction SilentlyContinue
    $actual = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $ExpectedSha256.ToLowerInvariant()) {
        throw 'Downloaded update digest changed before installation.'
    }
    $installed = $false
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        try {
            Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
            if (Test-Path -LiteralPath $Target) {
                Move-Item -LiteralPath $Target -Destination $backup -Force
            }
            try {
                Move-Item -LiteralPath $Source -Destination $Target -Force
            }
            catch {
                if (Test-Path -LiteralPath $backup) {
                    Move-Item -LiteralPath $backup -Destination $Target -Force
                }
                throw
            }
            $installed = $true
            break
        }
        catch {
            if ($attempt -eq 20) {
                throw
            }
            Start-Sleep -Seconds 1
        }
    }
    if (-not $installed) {
        throw 'The update could not replace the application executable.'
    }
    Start-Process -FilePath $Target -WorkingDirectory (Split-Path -Parent $Target)
    Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
}
catch {
    Add-Content -LiteralPath $LogPath -Value "$(Get-Date -Format o) $($_.Exception.Message)"
    exit 1
}
finally {
    Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
}
""".strip()


def launch_update_replacement(
    source: Path,
    target: Path,
    expected_sha256: str,
    wait_pid: int | None = None,
    launcher: Callable[..., Any] = subprocess.Popen,
) -> Path:
    if sys.platform != "win32":
        raise RuntimeError("Automatic executable replacement is supported on Windows only.")
    source = source.resolve()
    target = target.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Downloaded update was not found: {source}")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("The update SHA256 value is invalid.")

    staging = update_staging_directory()
    script_path = staging / f"apply-update-{os.getpid()}.ps1"
    log_path = target.parent / "update-error.log"
    script_path.write_text(_update_script_text(), encoding="utf-8")
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(script_path),
        "-WaitPid",
        str(wait_pid or os.getpid()),
        "-Source",
        str(source),
        "-Target",
        str(target),
        "-ExpectedSha256",
        expected_sha256.lower(),
        "-LogPath",
        str(log_path),
    ]
    creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    launcher(
        command,
        close_fds=True,
        creationflags=creation_flags,
    )
    return script_path


class UpdateManager(QObject):
    checkStarted = Signal()
    checkSucceeded = Signal(object)
    checkFailed = Signal(str)
    downloadStarted = Signal(object)
    downloadProgress = Signal(int)
    downloadReady = Signal(object, object)
    downloadFailed = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        executable_path: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.executable_path = (
            executable_path
            if executable_path is not None
            else Path(sys.executable) if can_replace_current_executable() else None
        )
        self.build_version = bundled_build_version()
        self._check_lock = threading.Lock()
        self._download_lock = threading.Lock()

    def check_for_updates(self) -> bool:
        if not self._check_lock.acquire(blocking=False):
            return False
        self.checkStarted.emit()
        threading.Thread(target=self._check_worker, daemon=True).start()
        return True

    def _check_worker(self) -> None:
        try:
            self.checkSucceeded.emit(
                fetch_release_status(
                    self.executable_path,
                    build_version=self.build_version,
                )
            )
        except Exception as error:
            self.checkFailed.emit(str(error))
        finally:
            self._check_lock.release()

    def download_update(self, release: ReleaseInfo) -> bool:
        if not self._download_lock.acquire(blocking=False):
            return False
        self.downloadStarted.emit(release)
        threading.Thread(
            target=self._download_worker,
            args=(release,),
            daemon=True,
        ).start()
        return True

    def _download_worker(self, release: ReleaseInfo) -> None:
        try:
            path = download_release_asset(
                release,
                progress=self.downloadProgress.emit,
            )
            self.downloadReady.emit(path, release)
        except Exception as error:
            self.downloadFailed.emit(str(error))
        finally:
            self._download_lock.release()
