from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By


CURRENT_CARD_SELECTOR = "#listall .earn-card"
CURRENT_BUTTON_SELECTOR = ".earn-btn"
CURRENT_NAME_SELECTOR = ".who"
CURRENT_TARGET_SELECTOR = ".scmeta"
LEGACY_NAME_SELECTOR = "#listall > center > b:nth-child(1) > font"
LEGACY_BUTTON_CLASS = "followbutton"
NO_SONG_MARKERS = (
    "there are no more songs to play for points",
    "no more songs",
)


@dataclass(frozen=True)
class SoundCloudTask:
    label: str
    identity: str
    wait_seconds: int | None
    button: Any


def _element_text(parent: Any, selector: str) -> str:
    elements = parent.find_elements(By.CSS_SELECTOR, selector)
    if not elements:
        return ""
    return elements[0].text.strip()


def _wait_seconds_from_onclick(onclick: str) -> int | None:
    match = re.search(
        r"imageWin\(\s*[^,]+,\s*[^,]+,\s*['\"]?(\d+)",
        onclick,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def find_soundcloud_task(driver: Any) -> SoundCloudTask | None:
    """Return the current task from either the current or legacy page markup."""
    try:
        for card in driver.find_elements(By.CSS_SELECTOR, CURRENT_CARD_SELECTOR):
            buttons = card.find_elements(By.CSS_SELECTOR, CURRENT_BUTTON_SELECTOR)
            if not buttons:
                continue
            button = buttons[0]
            account_name = _element_text(card, CURRENT_NAME_SELECTOR)
            target_name = _element_text(card, CURRENT_TARGET_SELECTOR)
            label = " | ".join(
                part for part in (account_name, target_name) if part
            )
            onclick = (button.get_attribute("onclick") or "").strip()
            identity = onclick or label.casefold()
            if not identity:
                continue
            return SoundCloudTask(
                label=label or "SoundCloud task",
                identity=identity,
                wait_seconds=_wait_seconds_from_onclick(onclick),
                button=button,
            )

        names = driver.find_elements(By.CSS_SELECTOR, LEGACY_NAME_SELECTOR)
        buttons = driver.find_elements(By.CLASS_NAME, LEGACY_BUTTON_CLASS)
        if not names or not buttons:
            return None
        label = names[0].text.strip()
        if not label:
            return None
        return SoundCloudTask(
            label=label,
            identity=label.casefold(),
            wait_seconds=None,
            button=buttons[0],
        )
    except WebDriverException:
        return None


def soundcloud_tasks_finished(list_text: str) -> bool:
    normalized = " ".join(list_text.casefold().split())
    return any(marker in normalized for marker in NO_SONG_MARKERS)
