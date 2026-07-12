import os
from pathlib import Path

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
