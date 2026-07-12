import sys
from pathlib import Path

from app import site_registry


def test_every_site_has_a_packaged_logo() -> None:
    assert set(site_registry.SITES) == {
        "youlikehits",
        "ytmonsterru",
        "traffup",
        "ytmonster",
        "ytbpals",
        "like4like",
    }

    for site in site_registry.SITES.values():
        assert hasattr(site, "logo_asset")
        logo = site_registry.resolve_asset(site.logo_asset)
        assert logo.is_file(), f"Missing logo for {site.site_id}: {logo}"


def test_frozen_app_separates_bundle_and_executable_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bundle_root = tmp_path / "bundle"
    executable = tmp_path / "publish/AutosubscriberApp.exe"
    bundle_root.mkdir()
    (bundle_root / "config.default.ini").write_text(
        "[USERINFO]\nchrome_profile_name=Default\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root), raising=False)
    monkeypatch.setattr(
        sys,
        "executable",
        str(executable),
    )

    assert site_registry.find_bundle_root() == bundle_root
    assert site_registry.find_runtime_root() == executable.parent
    assert site_registry.resolve_asset("app/assets/logo.png") == (
        bundle_root / "app/assets/logo.png"
    )
    assert site_registry.find_default_config_path() == (
        bundle_root / "config.default.ini"
    )


def test_frozen_app_creates_config_beside_executable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bundle_root = tmp_path / "bundle"
    executable = tmp_path / "publish/AutosubscriberApp.exe"
    bundle_root.mkdir()
    default_text = "[USERINFO]\nchrome_profile_name=Default\n"
    (bundle_root / "config.default.ini").write_text(
        default_text,
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root), raising=False)
    monkeypatch.setattr(
        sys,
        "executable",
        str(executable),
    )

    config_path = site_registry.ensure_config_file()

    assert config_path == executable.parent / "config.ini"
    assert config_path.read_text(encoding="utf-8") == default_text
