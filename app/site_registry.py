from __future__ import annotations

import sys
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SiteSpec:
    site_id: str
    display_name: str
    function_name: str
    required_config_keys: tuple[str, ...]
    field_map: dict[str, str]
    default_headless: bool
    supports_embedded_chrome: bool
    logo_asset: str


COMMON_FIELD_MAP = {
    "yt_email": "youtube_email",
    "chrome_userdata_directory": "chrome_userdata_directory",
    "chrome_profile_name": "chrome_profile_name",
    "yt_channel_id": "youtube_channel_id",
    "yt_useragent": "youtube_useragent",
    "github_token": "github_token",
}

DEFAULT_VALUE_ALLOWED_KEYS = {"chrome_profile_name"}


SITES: dict[str, SiteSpec] = {
    "youlikehits": SiteSpec(
        site_id="youlikehits",
        display_name="YouLikeHits",
        function_name="youlikehits_functions",
        required_config_keys=(
            "chrome_userdata_directory",
            "chrome_profile_name",
            "youtube_email",
            "youtube_channel_id",
            "youtube_useragent",
            "youlikehits_username",
            "youlikehits_password",
        ),
        field_map={
            **COMMON_FIELD_MAP,
            "username_youlikehits": "youlikehits_username",
            "pw_youlikehits": "youlikehits_password",
        },
        default_headless=True,
        supports_embedded_chrome=True,
        logo_asset="app/assets/sites/youlikehits.png",
    ),
    "ytmonsterru": SiteSpec(
        site_id="ytmonsterru",
        display_name="YTMonster RU",
        function_name="ytmonsterru_functions",
        required_config_keys=(
            "chrome_userdata_directory",
            "chrome_profile_name",
            "youtube_email",
            "youtube_channel_id",
            "youtube_useragent",
            "ytmonsterru_email",
            "ytmonsterru_password",
        ),
        field_map={
            **COMMON_FIELD_MAP,
            "email_ytmonsterru": "ytmonsterru_email",
            "pw_ytmonsterru": "ytmonsterru_password",
        },
        default_headless=True,
        supports_embedded_chrome=True,
        logo_asset="app/assets/sites/ytmonsterru.png",
    ),
    "traffup": SiteSpec(
        site_id="traffup",
        display_name="Traffup",
        function_name="traffup_functions",
        required_config_keys=(
            "chrome_userdata_directory",
            "chrome_profile_name",
            "youtube_email",
            "youtube_channel_id",
            "youtube_useragent",
            "traffup_email",
            "traffup_password",
        ),
        field_map={
            **COMMON_FIELD_MAP,
            "email_traffup": "traffup_email",
            "pw_traffup": "traffup_password",
        },
        default_headless=True,
        supports_embedded_chrome=True,
        logo_asset="app/assets/sites/traffup.png",
    ),
    "ytmonster": SiteSpec(
        site_id="ytmonster",
        display_name="YTMonster",
        function_name="ytmonster_functions",
        required_config_keys=(
            "chrome_userdata_directory",
            "chrome_profile_name",
            "youtube_email",
            "youtube_channel_id",
            "youtube_useragent",
            "ytmonster_com_username",
            "ytmonster_com_password",
        ),
        field_map={
            **COMMON_FIELD_MAP,
            "username_ytmonster": "ytmonster_com_username",
            "pw_ytmonster": "ytmonster_com_password",
        },
        default_headless=True,
        supports_embedded_chrome=True,
        logo_asset="app/assets/sites/ytmonster.png",
    ),
    "ytbpals": SiteSpec(
        site_id="ytbpals",
        display_name="YTBPals",
        function_name="ytbpals_functions",
        required_config_keys=(
            "chrome_userdata_directory",
            "chrome_profile_name",
            "youtube_email",
            "youtube_channel_id",
            "youtube_useragent",
            "ytbpals_com_email",
            "ytbpals_com_password",
        ),
        field_map={
            **COMMON_FIELD_MAP,
            "email_ytbpals": "ytbpals_com_email",
            "pw_ytbpals": "ytbpals_com_password",
        },
        default_headless=False,
        supports_embedded_chrome=True,
        logo_asset="app/assets/sites/ytbpals.png",
    ),
    "like4like": SiteSpec(
        site_id="like4like",
        display_name="Like4Like",
        function_name="like4like_functions",
        required_config_keys=(
            "chrome_userdata_directory",
            "chrome_profile_name",
            "youtube_email",
            "youtube_channel_id",
            "youtube_useragent",
            "like4like_username",
            "like4like_password",
        ),
        field_map={
            **COMMON_FIELD_MAP,
            "username_like4like": "like4like_username",
            "pw_like4like": "like4like_password",
        },
        default_headless=False,
        supports_embedded_chrome=True,
        logo_asset="app/assets/sites/like4like.png",
    ),
}


def find_runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return REPO_ROOT


def find_bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return REPO_ROOT


def resolve_asset(relative_path: str) -> Path:
    return find_bundle_root() / relative_path


def find_default_config_path() -> Path:
    bundled_default = find_bundle_root() / "config.default.ini"
    if bundled_default.exists():
        return bundled_default
    return REPO_ROOT / "config.default.ini"


def find_config_path() -> Path:
    return find_runtime_root() / "config.ini"


def load_config(path: Path | None = None) -> ConfigParser:
    config = ConfigParser()
    config.read(path or find_config_path(), encoding="utf-8")
    return config


def load_default_config() -> ConfigParser:
    config = ConfigParser()
    config.read(find_default_config_path(), encoding="utf-8")
    return config


def ensure_config_file(path: Path | None = None) -> Path:
    config_path = path or find_config_path()
    if config_path.exists():
        return config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)
    default_text = find_default_config_path().read_text(encoding="utf-8")
    config_path.write_text(default_text, encoding="utf-8")
    return config_path


def get_userinfo(config: ConfigParser) -> dict[str, str]:
    if not config.has_section("USERINFO"):
        return {}
    return {key: value for key, value in config["USERINFO"].items()}


def default_userinfo() -> dict[str, str]:
    return get_userinfo(load_default_config())


def is_config_same_as_default(config_path: Path | None = None) -> bool:
    config = load_config(config_path)
    current = get_userinfo(config)
    defaults = default_userinfo()
    if not current:
        return True
    default_keys = set(defaults)
    current_keys = set(current)
    if not default_keys.issubset(current_keys):
        return False
    return all(current.get(key, "") == defaults.get(key, "") for key in default_keys)


def config_validation_errors(site_id: str, config_path: Path | None = None) -> list[str]:
    if site_id not in SITES:
        return [f"Unknown site: {site_id}"]

    path = config_path or find_config_path()
    if not path.exists():
        return [f"Missing config.ini at {path}"]

    config = load_config(path)
    values = get_userinfo(config)
    defaults = default_userinfo()
    errors: list[str] = []

    if not values:
        errors.append("config.ini is missing the USERINFO section")
        return errors

    if is_config_same_as_default(path):
        errors.append("config.ini still matches config.default.ini")

    for key in SITES[site_id].required_config_keys:
        value = values.get(key, "").strip()
        if not value:
            errors.append(f"Missing value: {key}")
        elif value == defaults.get(key, "") and key not in DEFAULT_VALUE_ALLOWED_KEYS:
            errors.append(f"Default value unchanged: {key}")

    return errors


def build_required_dict(
    site_id: str,
    *,
    headless: bool,
    debug_screenshots: bool,
    embed_parent_hwnd: int | None = None,
    embed_window_token: str | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    spec = SITES[site_id]
    config = load_config(config_path)
    userinfo = config["USERINFO"]
    req_dict: dict[str, Any] = {
        out_key: userinfo.get(config_key, "")
        for out_key, config_key in spec.field_map.items()
    }
    req_dict["headless"] = headless
    req_dict["debug_screenshots"] = debug_screenshots
    req_dict["app_asset_root"] = str(find_bundle_root())
    if embed_parent_hwnd is not None:
        req_dict["app_embed_parent_hwnd"] = embed_parent_hwnd
    if embed_window_token:
        req_dict["app_embed_window_token"] = embed_window_token
    return req_dict


def site_choices() -> list[str]:
    return [spec.display_name for spec in SITES.values()]


def site_id_from_display(display_name: str) -> str:
    for site_id, spec in SITES.items():
        if spec.display_name == display_name:
            return site_id
    raise KeyError(display_name)
