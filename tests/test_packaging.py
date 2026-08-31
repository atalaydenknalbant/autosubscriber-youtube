from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_spec_builds_one_file() -> None:
    spec_text = (REPO_ROOT / "autosubscriber_app.spec").read_text(
        encoding="utf-8"
    )

    assert "COLLECT(" not in spec_text
    assert "exclude_binaries=False" in spec_text
    assert "a.binaries" in spec_text
    assert "a.datas" in spec_text


def test_build_script_targets_single_executable() -> None:
    script_text = (REPO_ROOT / "scripts/build_app.ps1").read_text(
        encoding="utf-8"
    )

    assert '"dist"' in script_text
    assert '"AutosubscriberApp.exe"' in script_text
    assert '"dist\\AutosubscriberApp"' not in script_text
    assert "releases/latest" in script_text
    assert "AUTOSUBSCRIBER_BUILD_METADATA_PATH" in script_text

    spec_text = (REPO_ROOT / "autosubscriber_app.spec").read_text(
        encoding="utf-8"
    )
    assert "AUTOSUBSCRIBER_BUILD_METADATA_PATH" in spec_text
    assert '"app"' in spec_text


def test_setup_package_version_does_not_drive_gui_updates() -> None:
    setup_text = (REPO_ROOT / "setup.py").read_text(encoding="utf-8")

    assert "APP_VERSION" not in setup_text
    assert "version='0.0.0'" in setup_text
