from app.site_registry import SITES, resolve_asset
from app.widgets import (
    ActivityRing,
    AnimatedSwitch,
    IconButton,
    LogView,
    SiteLogoButton,
)


def test_site_button_selection_updates_property(qapp) -> None:
    logo = resolve_asset(SITES["youlikehits"].logo_asset)
    button = SiteLogoButton("youlikehits", logo, "YouLikeHits")

    button.set_selected(True)

    assert button.property("selected") is True
    assert button.isChecked() is True


def test_switch_emits_new_state(qapp) -> None:
    values: list[bool] = []
    switch = AnimatedSwitch()
    switch.checkedChanged.connect(values.append)

    switch.setChecked(True)

    assert values == [True]


def test_switch_position_matches_checked_state_when_signals_are_blocked(qapp) -> None:
    switch = AnimatedSwitch()
    switch.blockSignals(True)

    switch.setChecked(True)
    switch.blockSignals(False)

    assert switch.isChecked() is True
    assert switch.get_offset() == 34.0

    switch.blockSignals(True)
    switch.setChecked(False)
    switch.blockSignals(False)

    assert switch.isChecked() is False
    assert switch.get_offset() == 4.0


def test_activity_ring_tracks_running_state(qapp) -> None:
    ring = ActivityRing()

    ring.start()
    assert ring.is_active is True

    ring.stop()
    assert ring.is_active is False


def test_icon_button_keeps_stable_dimensions(qapp) -> None:
    button = IconButton("play", "Start")

    assert button.width() == button.height()
    assert button.toolTip() == "Start"


def test_log_view_caps_long_running_history(qapp) -> None:
    log_view = LogView()
    assert log_view.document().maximumBlockCount() == LogView.MAX_BLOCKS
    log_view.document().setMaximumBlockCount(100)

    for index in range(200):
        log_view.append_line(f"line {index}")

    assert log_view.document().blockCount() == 100
    assert "line 0" not in log_view.toPlainText()
    assert "line 199" in log_view.toPlainText()


def test_log_view_truncates_pathological_lines(qapp) -> None:
    log_view = LogView()

    log_view.append_line("x" * (LogView.MAX_LINE_CHARS + 100))

    assert log_view.toPlainText().endswith("[log line truncated]")
