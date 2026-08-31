from selenium.webdriver.common.by import By

from selenium_codes.youlikehits_youtube import (
    find_youtube_watch_task,
    youtube_watch_tasks_finished,
)


class FakeElement:
    def __init__(self, text: str = "", attributes: dict | None = None) -> None:
        self.text = text
        self.attributes = attributes or {}
        self.elements: dict[tuple[str, str], list[FakeElement]] = {}

    def add(self, by: str, selector: str, *elements: "FakeElement") -> None:
        self.elements[(by, selector)] = list(elements)

    def find_elements(self, by: str, selector: str) -> list["FakeElement"]:
        return self.elements.get((by, selector), [])

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)


class ScriptDriver:
    def __init__(self, snapshot: dict | None) -> None:
        self.snapshot = snapshot
        self.execute_calls = 0

    def execute_script(self, _script: str, *_args: str) -> dict | None:
        self.execute_calls += 1
        return self.snapshot

    def find_elements(self, _by: str, _selector: str) -> list[FakeElement]:
        raise AssertionError("Element fallback should not run after a script read")


def test_current_task_uses_one_browser_round_trip() -> None:
    view_button = FakeElement()
    skip_button = FakeElement()
    onclick = "imageWin(4026250,'yuRA0X0YlYs','180','hash',event);"
    driver = ScriptDriver(
        {
            "label": "Current video",
            "onclick": onclick,
            "thumbnailUrl": "https://i.ytimg.com/vi/yuRA0X0YlYs/hqdefault.jpg",
            "button": view_button,
            "skipButton": skip_button,
        }
    )

    task = find_youtube_watch_task(driver)

    assert driver.execute_calls == 1
    assert task is not None
    assert task.identity == onclick
    assert task.wait_seconds == 180
    assert task.button is view_button
    assert task.skip_button is skip_button


def test_current_youtube_card_reads_title_timer_and_actions() -> None:
    driver = FakeElement()
    card = FakeElement()
    onclick = "imageWin(4026250,'yuRA0X0YlYs','180','hash',event);"
    view_button = FakeElement(attributes={"onclick": onclick})
    skip_button = FakeElement(attributes={"onclick": "skipvid(4026250);"})
    card.add(By.CSS_SELECTOR, ".Title", FakeElement("Current video"))
    card.add(
        By.CSS_SELECTOR,
        "a.earn-btn[onclick*='imageWin']",
        view_button,
    )
    card.add(
        By.CSS_SELECTOR,
        ".earn-links a[onclick*='skipvid']",
        skip_button,
    )
    card.add(
        By.CSS_SELECTOR,
        "img.ytthumb",
        FakeElement(attributes={"src": "https://i.ytimg.com/vi/yuRA0X0YlYs/hqdefault.jpg"}),
    )
    driver.add(By.CSS_SELECTOR, "#listall .earn-card", card)

    task = find_youtube_watch_task(driver)

    assert task is not None
    assert task.label == "Current video"
    assert task.identity == onclick
    assert task.wait_seconds == 180
    assert task.button is view_button
    assert task.skip_button is skip_button


def test_missing_current_youtube_markup_returns_no_task() -> None:
    driver = FakeElement()

    task = find_youtube_watch_task(driver)

    assert task is None


def test_no_video_message_is_detected_case_insensitively() -> None:
    assert youtube_watch_tasks_finished(
        "There are no videos available to view at this time."
    )
