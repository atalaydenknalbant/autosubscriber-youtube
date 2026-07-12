from __future__ import annotations

import os
from configparser import ConfigParser, Error as ConfigError
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from app.site_registry import (
    DEFAULT_VALUE_ALLOWED_KEYS,
    SITES,
    default_userinfo,
)


@dataclass(frozen=True)
class ConfigField:
    key: str
    label: str
    group: str
    secret: bool = False


COMMON_FIELDS = (
    ConfigField(
        "chrome_userdata_directory",
        "Chrome user data directory",
        "Chrome",
    ),
    ConfigField("chrome_profile_name", "Chrome profile name", "Chrome"),
    ConfigField("youtube_email", "YouTube email", "YouTube"),
    ConfigField("youtube_channel_id", "YouTube channel ID", "YouTube"),
    ConfigField("youtube_useragent", "YouTube user agent", "YouTube"),
    ConfigField("github_token", "GitHub token", "YouTube", secret=True),
)

FIELD_LABELS = {
    "youlikehits_username": "Username",
    "youlikehits_password": "Password",
    "ytmonsterru_email": "Email",
    "ytmonsterru_password": "Password",
    "traffup_email": "Email",
    "traffup_password": "Password",
    "ytmonster_com_username": "Username",
    "ytmonster_com_password": "Password",
    "ytbpals_com_email": "Email",
    "ytbpals_com_password": "Password",
    "like4like_username": "Username",
    "like4like_password": "Password",
}


def config_fields() -> tuple[ConfigField, ...]:
    fields = list(COMMON_FIELDS)
    common_keys = {field.key for field in fields}
    added = set(common_keys)

    for site in SITES.values():
        for key in site.required_config_keys:
            if key in added:
                continue
            fields.append(
                ConfigField(
                    key=key,
                    label=FIELD_LABELS.get(key, key.replace("_", " ").title()),
                    group=site.display_name,
                    secret="password" in key or "token" in key,
                )
            )
            added.add(key)

    return tuple(fields)


class ConfigDocument:
    def __init__(self, parser: ConfigParser) -> None:
        self.parser = parser

    @staticmethod
    def _new_parser() -> ConfigParser:
        return ConfigParser(interpolation=None)

    @classmethod
    def from_text(cls, text: str) -> "ConfigDocument":
        parser = cls._new_parser()
        try:
            parser.read_string(text)
        except ConfigError as parse_ex:
            raise ValueError("Invalid INI configuration") from parse_ex
        if not parser.has_section("USERINFO"):
            raise ValueError("Configuration must contain a USERINFO section")
        return cls(parser)

    @classmethod
    def load(cls, path: Path) -> "ConfigDocument":
        return cls.from_text(path.read_text(encoding="utf-8"))

    def get(self, key: str) -> str:
        return self.parser.get("USERINFO", key, fallback="")

    def set(self, key: str, value: str) -> None:
        self.parser.set("USERINFO", key, value)

    def to_text(self) -> str:
        output = StringIO()
        self.parser.write(output)
        return output.getvalue()

    def validate(self, site_id: str | None = None) -> dict[str, str]:
        required_keys = SITES[site_id].required_config_keys if site_id else ()
        defaults = default_userinfo()
        errors: dict[str, str] = {}

        for key in required_keys:
            value = self.get(key).strip()
            if not value:
                errors[key] = "Required value"
            elif (
                value == defaults.get(key, "")
                and key not in DEFAULT_VALUE_ALLOWED_KEYS
            ):
                errors[key] = "Replace the default value"

        return errors

    def save_atomic(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            temporary.write_text(self.to_text(), encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
