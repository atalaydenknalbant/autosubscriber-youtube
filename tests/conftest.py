import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    path = tmp_path / "config.ini"
    path.write_text(
        "[USERINFO]\n"
        "chrome_profile_name=Default\n"
        "youlikehits_username=old\n"
        "youlikehits_password=secret\n",
        encoding="utf-8",
    )
    return path
