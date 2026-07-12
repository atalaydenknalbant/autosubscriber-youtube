from __future__ import annotations

from itertools import groupby
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config_model import ConfigDocument, config_fields
from app.theme import Colors


class ConfigDialog(QDialog):
    saved = Signal()

    def __init__(
        self,
        config_path: Path,
        active_site_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config_path = config_path
        self.active_site_id = active_site_id
        self.document = ConfigDocument.load(config_path)
        self.form_fields: dict[str, QLineEdit] = {}
        self._mode = "form"

        self.setWindowTitle("Configuration")
        self.resize(900, 720)
        self.setMinimumSize(720, 580)
        self.setModal(True)
        self._build_ui()
        self._populate_form()
        self.raw_editor.setPlainText(self.document.to_text())

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 18)
        root.setSpacing(14)

        title = QLabel("Application configuration", self)
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        description = QLabel(
            "Import an existing config or edit the same values in Form and Text views.",
            self,
        )
        description.setObjectName("mutedLabel")
        root.addWidget(description)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        self.form_mode_button = QPushButton("Form", self)
        self.text_mode_button = QPushButton("Text", self)
        for button in (self.form_mode_button, self.text_mode_button):
            button.setCheckable(True)
            button.setMinimumWidth(110)
        self.form_mode_button.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.form_mode_button)
        mode_group.addButton(self.text_mode_button)
        self.form_mode_button.clicked.connect(lambda: self.set_mode("form"))
        self.text_mode_button.clicked.connect(lambda: self.set_mode("text"))
        mode_row.addWidget(self.form_mode_button)
        mode_row.addWidget(self.text_mode_button)
        mode_row.addStretch(1)
        root.addLayout(mode_row)

        self.pages = QStackedWidget(self)
        self.pages.addWidget(self._build_form_page())
        self.raw_editor = QPlainTextEdit(self)
        self.raw_editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.raw_editor.setStyleSheet("font-family: 'Cascadia Mono'; font-size: 9pt;")
        self.pages.addWidget(self.raw_editor)
        root.addWidget(self.pages, 1)

        self.error_label = QLabel("", self)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(f"color: {Colors.ERROR};")
        self.error_label.hide()
        root.addWidget(self.error_label)

        actions = QHBoxLayout()
        self.import_button = QPushButton("Import config", self)
        self.import_button.clicked.connect(self._choose_import)
        actions.addWidget(self.import_button)
        actions.addStretch(1)

        cancel_button = QPushButton("Cancel", self)
        cancel_button.clicked.connect(self.reject)
        actions.addWidget(cancel_button)

        save_button = QPushButton("Save", self)
        save_button.setStyleSheet(
            f"background-color: {Colors.RED_DARK}; border-color: {Colors.RED};"
            f"color: {Colors.WHITE}; font-weight: 600;"
        )
        save_button.clicked.connect(self._save_and_accept)
        actions.addWidget(save_button)
        root.addLayout(actions)

    def _build_form_page(self) -> QScrollArea:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget(scroll)
        groups_layout = QVBoxLayout(container)
        groups_layout.setContentsMargins(0, 4, 8, 4)
        groups_layout.setSpacing(12)

        fields = config_fields()
        for group_name, group_fields in groupby(fields, key=lambda item: item.group):
            box = QGroupBox(group_name, container)
            form = QFormLayout(box)
            form.setContentsMargins(14, 18, 14, 14)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(10)
            form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

            for field in group_fields:
                editor = QLineEdit(box)
                editor.setObjectName(f"config_{field.key}")
                if field.secret:
                    editor.setEchoMode(QLineEdit.Password)
                    row = QWidget(box)
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(6)
                    row_layout.addWidget(editor, 1)
                    reveal = QPushButton("Show", row)
                    reveal.setCheckable(True)
                    reveal.setFixedWidth(64)
                    reveal.toggled.connect(
                        lambda checked, line_edit=editor, button=reveal: self._toggle_secret(
                            line_edit,
                            button,
                            checked,
                        )
                    )
                    row_layout.addWidget(reveal)
                    form.addRow(field.label, row)
                else:
                    form.addRow(field.label, editor)
                self.form_fields[field.key] = editor

            groups_layout.addWidget(box)

        groups_layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    @staticmethod
    def _toggle_secret(
        editor: QLineEdit,
        button: QPushButton,
        checked: bool,
    ) -> None:
        editor.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        button.setText("Hide" if checked else "Show")

    def _populate_form(self) -> None:
        for key, editor in self.form_fields.items():
            editor.setText(self.document.get(key))
            editor.setStyleSheet("")

    def _sync_form_to_document(self) -> None:
        for key, editor in self.form_fields.items():
            self.document.set(key, editor.text())

    def _sync_text_to_document(self) -> bool:
        try:
            document = ConfigDocument.from_text(self.raw_editor.toPlainText())
        except ValueError as parse_ex:
            self._show_error(str(parse_ex))
            return False
        self.document = document
        self._clear_error()
        return True

    def set_mode(self, mode: str) -> bool:
        if mode not in {"form", "text"}:
            raise ValueError(f"Unknown configuration mode: {mode}")

        if mode == self._mode:
            return True

        if mode == "text":
            self._sync_form_to_document()
            self.raw_editor.setPlainText(self.document.to_text())
            self.pages.setCurrentIndex(1)
            self.text_mode_button.setChecked(True)
        else:
            if not self._sync_text_to_document():
                self.text_mode_button.setChecked(True)
                return False
            self._populate_form()
            self.pages.setCurrentIndex(0)
            self.form_mode_button.setChecked(True)

        self._mode = mode
        self._clear_error()
        return True

    def import_path(self, path: Path) -> bool:
        try:
            imported = ConfigDocument.load(path)
        except (OSError, ValueError) as import_ex:
            self._show_error(f"Could not import config: {import_ex}")
            return False

        self.document = imported
        self._populate_form()
        self.raw_editor.setPlainText(self.document.to_text())
        self._clear_error()
        return True

    def _choose_import(self) -> None:
        selected, _filter = QFileDialog.getOpenFileName(
            self,
            "Import configuration",
            str(self.config_path.parent),
            "INI files (*.ini);;All files (*)",
        )
        if selected:
            self.import_path(Path(selected))

    def save(self) -> bool:
        if self._mode == "text":
            if not self._sync_text_to_document():
                return False
        else:
            self._sync_form_to_document()

        errors = self.document.validate(self.active_site_id)
        if errors:
            self._mark_field_errors(errors)
            self._show_error("Complete the highlighted values before saving.")
            return False

        try:
            self.document.save_atomic(self.config_path)
        except OSError as save_ex:
            self._show_error(f"Could not save config: {save_ex}")
            return False

        self._clear_error()
        self.saved.emit()
        return True

    def _save_and_accept(self) -> None:
        if self.save():
            self.accept()

    def _mark_field_errors(self, errors: dict[str, str]) -> None:
        for key, editor in self.form_fields.items():
            if key in errors:
                editor.setStyleSheet(
                    f"border: 1px solid {Colors.ERROR}; background-color: #190E12;"
                )
                editor.setToolTip(errors[key])
            else:
                editor.setStyleSheet("")
                editor.setToolTip("")

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _clear_error(self) -> None:
        self.error_label.clear()
        self.error_label.hide()
