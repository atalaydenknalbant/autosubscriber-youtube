from app.browser_panel import BrowserPanel


class FakeBackend:
    def __init__(self) -> None:
        self.attachments: list[tuple[int, int]] = []
        self.detached: list[int] = []

    def attach(self, hwnd: int, parent_hwnd: int) -> None:
        self.attachments.append((hwnd, parent_hwnd))

    def detach_to_offscreen(self, hwnd: int) -> None:
        self.detached.append(hwnd)

    def resize(self, _hwnd: int, _parent_hwnd: int) -> None:
        return None


def test_first_window_is_main_and_later_windows_are_previews(qapp) -> None:
    backend = FakeBackend()
    panel = BrowserPanel(backend)

    panel.set_windows([10, 20, 30])

    assert panel.main_hwnd == 10
    assert panel.preview_hwnds == [20, 30]
    assert {hwnd for hwnd, _parent in backend.attachments} == {10, 20, 30}


def test_oldest_preview_becomes_main_when_main_closes(qapp) -> None:
    backend = FakeBackend()
    panel = BrowserPanel(backend)
    panel.set_windows([10, 20, 30])

    panel.set_windows([20, 30])

    assert panel.main_hwnd == 20
    assert panel.preview_hwnds == [30]


def test_clear_moves_hosted_windows_offscreen(qapp) -> None:
    backend = FakeBackend()
    panel = BrowserPanel(backend)
    panel.set_windows([10, 20])

    panel.clear_windows()

    assert panel.main_hwnd is None
    assert panel.preview_hwnds == []
    assert set(backend.detached) == {10, 20}
