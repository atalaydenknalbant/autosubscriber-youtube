from selenium.webdriver.common.by import By

from selenium_codes.youlikehits_soundcloud import (
    find_soundcloud_task,
    soundcloud_tasks_finished,
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


def test_current_soundcloud_card_is_read_with_timer() -> None:
    driver = FakeElement()
    card = FakeElement()
    button = FakeElement(
        attributes={
            "onclick": "imageWin(211506,'2212646840','50','hash',event);"
        }
    )
    card.add(By.CSS_SELECTOR, ".who", FakeElement("velvet-sky"))
    card.add(
        By.CSS_SELECTOR,
        ".scmeta",
        FakeElement("soundcloud.com/djkinkilu"),
    )
    card.add(By.CSS_SELECTOR, ".earn-btn", button)
    driver.add(By.CSS_SELECTOR, "#listall .earn-card", card)

    task = find_soundcloud_task(driver)

    assert task is not None
    assert task.label == "velvet-sky | soundcloud.com/djkinkilu"
    assert task.wait_seconds == 50
    assert task.button is button


def test_missing_current_soundcloud_markup_returns_no_task() -> None:
    driver = FakeElement()

    task = find_soundcloud_task(driver)

    assert task is None


def test_no_song_message_is_detected_case_insensitively() -> None:
    assert soundcloud_tasks_finished(
        "There are no more songs to play for points. Check back later!"
    )
