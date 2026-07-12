from app.site_registry import SITES, resolve_asset
from app.widgets import ActivityRing, AnimatedSwitch, IconButton, SiteLogoButton


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
