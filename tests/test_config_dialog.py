from pathlib import Path

from PySide6.QtWidgets import QLineEdit

from app.config_dialog import ConfigDialog


def test_form_and_text_modes_share_unsaved_values(qapp, config_path: Path) -> None:
    dialog = ConfigDialog(config_path)
    dialog.form_fields["youlikehits_username"].setText("changed")

    assert dialog.set_mode("text") is True

    assert "youlikehits_username = changed" in dialog.raw_editor.toPlainText()


def test_text_changes_populate_form(qapp, config_path: Path) -> None:
    dialog = ConfigDialog(config_path)
    dialog.set_mode("text")
    dialog.raw_editor.setPlainText(
        "[USERINFO]\n"
        "chrome_profile_name=Default\n"
        "youlikehits_username=raw\n"
        "youlikehits_password=secret\n"
    )

    assert dialog.set_mode("form") is True

    assert dialog.form_fields["youlikehits_username"].text() == "raw"


def test_password_fields_are_masked(qapp, config_path: Path) -> None:
    dialog = ConfigDialog(config_path)

    assert (
        dialog.form_fields["youlikehits_password"].echoMode()
        == QLineEdit.Password
    )


def test_invalid_import_does_not_replace_current_document(
    qapp,
    config_path: Path,
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "invalid.ini"
    invalid.write_text("not ini", encoding="utf-8")
    dialog = ConfigDialog(config_path)
    before = dialog.document.to_text()

    assert dialog.import_path(invalid) is False
    assert dialog.document.to_text() == before


def test_save_persists_form_values(qapp, config_path: Path) -> None:
    dialog = ConfigDialog(config_path)
    dialog.form_fields["youlikehits_username"].setText("saved-user")

    assert dialog.save() is True

    assert "youlikehits_username = saved-user" in config_path.read_text(
        encoding="utf-8"
    )
