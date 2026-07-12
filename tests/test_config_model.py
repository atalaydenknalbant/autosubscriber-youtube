from pathlib import Path

import pytest

from app.config_model import ConfigDocument, config_fields


def test_form_changes_are_reflected_in_raw_text() -> None:
    document = ConfigDocument.from_text(
        "[USERINFO]\n"
        "youlikehits_username=old\n"
    )

    document.set("youlikehits_username", "new")

    assert "youlikehits_username = new" in document.to_text()


def test_atomic_save_replaces_target(tmp_path: Path) -> None:
    target = tmp_path / "config.ini"
    target.write_text("[USERINFO]\nvalue=old\n", encoding="utf-8")
    document = ConfigDocument.from_text("[USERINFO]\nvalue=new\n")

    document.save_atomic(target)

    assert "value = new" in target.read_text(encoding="utf-8")
    assert not (tmp_path / "config.ini.tmp").exists()


def test_missing_userinfo_section_is_rejected() -> None:
    with pytest.raises(ValueError, match="USERINFO"):
        ConfigDocument.from_text("[OTHER]\nvalue=1\n")


def test_passwords_and_tokens_are_secret_fields() -> None:
    fields = {field.key: field for field in config_fields()}

    assert fields["youlikehits_password"].secret is True
    assert fields["github_token"].secret is True
    assert fields["chrome_profile_name"].secret is False


def test_site_validation_names_missing_fields_without_values() -> None:
    document = ConfigDocument.from_text(
        "[USERINFO]\n"
        "youlikehits_password=private-value\n"
    )

    errors = document.validate("youlikehits")

    assert errors["youlikehits_username"] == "Required value"
    assert "private-value" not in repr(errors)
