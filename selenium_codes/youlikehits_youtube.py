from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By


CURRENT_CARD_SELECTOR = "#listall .earn-card"
CURRENT_TITLE_SELECTOR = ".Title"
CURRENT_BUTTON_SELECTOR = "a.earn-btn[onclick*='imageWin']"
CURRENT_SKIP_SELECTOR = ".earn-links a[onclick*='skipvid']"
CURRENT_THUMBNAIL_SELECTOR = "img.ytthumb"
NO_VIDEO_MARKERS = (
    "there are no videos available",
    "no videos available",
    "there are no more videos",
    "no more videos",
)


@dataclass(frozen=True)
class YouTubeWatchTask:
    label: str
    identity: str
    wait_seconds: int | None
    button: Any
    skip_button: Any | None


def _first_element(parent: Any, by: str, selector: str) -> Any | None:
    elements = parent.find_elements(by, selector)
    return elements[0] if elements else None


def _element_text(parent: Any, selector: str) -> str:
    element = _first_element(parent, By.CSS_SELECTOR, selector)
    return element.text.strip() if element is not None else ""


def _wait_seconds_from_onclick(onclick: str) -> int | None:
    match = re.search(
        r"imageWin\(\s*[^,]+,\s*[^,]+,\s*['\"]?(\d+)",
        onclick,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def _task_from_snapshot(snapshot: Any) -> YouTubeWatchTask | None:
    if not isinstance(snapshot, dict):
        return None
    label = str(snapshot.get("label") or "").strip()
    button = snapshot.get("button")
    onclick = str(snapshot.get("onclick") or "").strip()
    thumbnail_url = str(snapshot.get("thumbnailUrl") or "").strip()
    identity = onclick or thumbnail_url or label.casefold()
    if not label or button is None or not identity:
        return None
    return YouTubeWatchTask(
        label=label,
        identity=identity,
        wait_seconds=_wait_seconds_from_onclick(onclick),
        button=button,
        skip_button=snapshot.get("skipButton"),
    )


def _task_from_single_script(driver: Any) -> tuple[bool, YouTubeWatchTask | None]:
    try:
        snapshot = driver.execute_script(
            """
            const card = document.querySelector(arguments[0]);
            if (card) {
                const title = card.querySelector(arguments[1]);
                const button = card.querySelector(arguments[2]);
                if (title && button) {
                    const thumbnail = card.querySelector(arguments[4]);
                    return {
                        label: (title.textContent || '').trim(),
                        onclick: (button.getAttribute('onclick') || '').trim(),
                        thumbnailUrl: thumbnail ? (thumbnail.src || '') : '',
                        button: button,
                        skipButton: card.querySelector(arguments[3]),
                    };
                }
            }
            return null;
            """,
            CURRENT_CARD_SELECTOR,
            CURRENT_TITLE_SELECTOR,
            CURRENT_BUTTON_SELECTOR,
            CURRENT_SKIP_SELECTOR,
            CURRENT_THUMBNAIL_SELECTOR,
        )
    except (AttributeError, WebDriverException):
        return False, None
    return True, _task_from_snapshot(snapshot)


def find_youtube_watch_task(driver: Any) -> YouTubeWatchTask | None:
    """Return the current YouLikeHits YouTube task."""
    script_supported, task = _task_from_single_script(driver)
    if script_supported:
        return task

    try:
        for card in driver.find_elements(By.CSS_SELECTOR, CURRENT_CARD_SELECTOR):
            button = _first_element(card, By.CSS_SELECTOR, CURRENT_BUTTON_SELECTOR)
            if button is None:
                continue
            label = _element_text(card, CURRENT_TITLE_SELECTOR)
            onclick = (button.get_attribute("onclick") or "").strip()
            thumbnail = _first_element(
                card,
                By.CSS_SELECTOR,
                CURRENT_THUMBNAIL_SELECTOR,
            )
            thumbnail_url = (
                (thumbnail.get_attribute("src") or "").strip()
                if thumbnail is not None
                else ""
            )
            identity = onclick or thumbnail_url or label.casefold()
            if not label or not identity:
                continue
            return YouTubeWatchTask(
                label=label,
                identity=identity,
                wait_seconds=_wait_seconds_from_onclick(onclick),
                button=button,
                skip_button=_first_element(
                    card,
                    By.CSS_SELECTOR,
                    CURRENT_SKIP_SELECTOR,
                ),
            )

        return None
    except WebDriverException:
        return None


def youtube_watch_tasks_finished(list_text: str) -> bool:
    normalized = " ".join(list_text.casefold().split())
    return any(marker in normalized for marker in NO_VIDEO_MARKERS)
