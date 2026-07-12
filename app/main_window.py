from __future__ import annotations

import os
import sys
import threading
import uuid
from pathlib import Path

from PySide6.QtCore import (
    QProcess,
    QProcessEnvironment,
    QEasingCurve,
    QTimer,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.browser_embed import (
    ChromeBackend,
    ChromeWindowMonitor,
    Win32ChromeBackend,
)
from app.browser_panel import BrowserPanel
from app.config_dialog import ConfigDialog
from app.process_control import terminate_process_tree
from app.site_registry import (
    SITES,
    config_validation_errors,
    ensure_config_file,
    find_config_path,
    find_runtime_root,
    is_config_same_as_default,
    resolve_asset,
)
from app.theme import Colors
from app.widgets import (
    AnimatedSwitch,
    GradientHeader,
    IconButton,
    LogView,
    SiteLogoButton,
    StatusDisplay,
)


def build_worker_invocation(
    site_id: str,
    *,
    headless: bool,
    token: str | None,
    frozen: bool,
    debug_screenshots: bool = False,
) -> tuple[str, list[str]]:
    program = sys.executable
    args = ["--worker"] if frozen else ["-u", "-m", "app.worker"]
    args.extend(
        [
            "--site",
            site_id,
            "--headless",
            str(headless).lower(),
            "--debug-screenshots",
            str(debug_screenshots).lower(),
        ]
    )
    if token and not headless:
        args.extend(["--embed-token", token])
    return program, args


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_path: Path | None = None,
        browser_backend: ChromeBackend | None = None,
    ) -> None:
        super().__init__()
        self.config_path = config_path or find_config_path()
        self._prompt_for_missing_config = (
            config_path is None and not self.config_path.exists()
        )
        self.browser_backend = browser_backend or Win32ChromeBackend()
        self.worker: QProcess | None = None
        self.browser_monitor: ChromeWindowMonitor | None = None
        self.current_site_id = next(iter(SITES))
        self.headless = True
        self.debug_screenshots = False
        self._log_buffer = ""
        self._browser_animation: QVariantAnimation | None = None

        self.setWindowTitle("Autosubscriber App")
        self.setWindowIcon(
            QIcon(str(resolve_asset("app/assets/branding/autosubscriber-logo.png")))
        )
        self.resize(1440, 900)
        self.setMinimumSize(1100, 720)
        self._build_ui()
        self.select_site(self.current_site_id)
        self._refresh_start_state()
        if self._prompt_for_missing_config:
            QTimer.singleShot(0, self._prompt_create_config)

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QWidget(central)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(18, 16, 18, 18)
        body_layout.setSpacing(12)
        body_layout.addWidget(self._build_site_selector())
        body_layout.addWidget(self._build_control_row())
        body_layout.addWidget(self._build_content(), 1)
        root.addWidget(body, 1)

    def _build_header(self) -> GradientHeader:
        header = GradientHeader(self)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(12)

        logo = QLabel(header)
        pixmap = QPixmap(
            str(resolve_asset("app/assets/branding/autosubscriber-logo.png"))
        )
        logo.setPixmap(
            pixmap.scaled(
                52,
                52,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        logo.setFixedSize(54, 54)
        layout.addWidget(logo)

        brand = QVBoxLayout()
        brand.setSpacing(0)
        title = QLabel("AUTOSUBSCRIBER", header)
        title.setStyleSheet(
            f"color: {Colors.WHITE}; font-size: 17pt; font-weight: 700;"
        )
        subtitle = QLabel("Selenium automation control center", header)
        subtitle.setStyleSheet(f"color: {Colors.MUTED}; font-size: 9pt;")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        layout.addLayout(brand)
        layout.addStretch(1)

        self.status_display = StatusDisplay(header)
        layout.addWidget(self.status_display)

        self.config_button = IconButton("settings", "Configure accounts", header)
        self.config_button.clicked.connect(self._open_config_editor)
        layout.addWidget(self.config_button)

        self.screenshots_button = IconButton(
            "folder",
            "Open screenshots folder",
            header,
        )
        self.screenshots_button.clicked.connect(self._open_screenshots)
        layout.addWidget(self.screenshots_button)

        self.clear_logs_button = IconButton("clear", "Clear logs", header)
        self.clear_logs_button.clicked.connect(self._clear_logs)
        layout.addWidget(self.clear_logs_button)
        return header

    def _build_site_selector(self) -> QFrame:
        panel = QFrame(self)
        panel.setObjectName("contentPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 10, 14, 12)
        panel_layout.setSpacing(8)
        title = QLabel("Select website", panel)
        title.setObjectName("sectionTitle")
        panel_layout.addWidget(title)

        scroll = QScrollArea(panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedHeight(102)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        holder = QWidget(scroll)
        holder.setStyleSheet("background: transparent;")
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.site_buttons: dict[str, SiteLogoButton] = {}
        for site_id, site in SITES.items():
            button = SiteLogoButton(
                site_id,
                resolve_asset(site.logo_asset),
                site.display_name,
                holder,
            )
            button.clicked.connect(
                lambda _checked=False, selected=site_id: self.select_site(selected)
            )
            self.site_buttons[site_id] = button
            row.addWidget(button)
        row.addStretch(1)
        scroll.setWidget(holder)
        panel_layout.addWidget(scroll)
        return panel

    def _build_control_row(self) -> QFrame:
        panel = QFrame(self)
        panel.setObjectName("contentPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        mode_text = QVBoxLayout()
        mode_text.setSpacing(0)
        mode_title = QLabel("Headless", panel)
        mode_title.setStyleSheet(f"color: {Colors.WHITE}; font-weight: 600;")
        mode_description = QLabel("Show logs only", panel)
        mode_description.setObjectName("mutedLabel")
        mode_text.addWidget(mode_title)
        mode_text.addWidget(mode_description)
        layout.addLayout(mode_text)

        self.headless_switch = AnimatedSwitch(panel)
        self.headless_switch.checkedChanged.connect(self._headless_changed)
        layout.addWidget(self.headless_switch)
        layout.addSpacing(18)

        screenshot_text = QVBoxLayout()
        screenshot_text.setSpacing(0)
        screenshot_title = QLabel("Debug screenshots", panel)
        screenshot_title.setStyleSheet(
            f"color: {Colors.WHITE}; font-weight: 600;"
        )
        screenshot_description = QLabel("Save diagnostic PNGs", panel)
        screenshot_description.setObjectName("mutedLabel")
        screenshot_text.addWidget(screenshot_title)
        screenshot_text.addWidget(screenshot_description)
        layout.addLayout(screenshot_text)

        self.debug_screenshots_switch = AnimatedSwitch(panel)
        self.debug_screenshots_switch.setToolTip(
            "Save diagnostic screenshots during website runs"
        )
        self.debug_screenshots_switch.checkedChanged.connect(
            self._debug_screenshots_changed
        )
        layout.addWidget(self.debug_screenshots_switch)
        layout.addStretch(1)

        self.start_button = IconButton("play", "Start selected website", panel)
        self.start_button.clicked.connect(self._start_worker)
        layout.addWidget(self.start_button)

        self.stop_button = IconButton("stop", "Stop current website", panel)
        self.stop_button.clicked.connect(self._stop_worker)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)
        return panel

    def _build_content(self) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setCollapsible(1, True)
        splitter.setHandleWidth(6)

        log_panel = QFrame(splitter)
        log_panel.setObjectName("contentPanel")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(8)
        log_title = QLabel("Activity log", log_panel)
        log_title.setObjectName("sectionTitle")
        log_layout.addWidget(log_title)
        self.log_view = LogView(log_panel)
        log_layout.addWidget(self.log_view, 1)

        self.browser_panel = BrowserPanel(self.browser_backend, splitter)
        self.browser_panel.embeddingFailed.connect(self._embedding_failed)
        self.browser_panel.setMinimumWidth(0)
        self.browser_panel.setMaximumWidth(0)
        self.browser_panel.hide()

        splitter.addWidget(log_panel)
        splitter.addWidget(self.browser_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([900, 0])
        self.content_splitter = splitter
        return splitter

    def select_site(self, site_id: str) -> None:
        if site_id not in SITES or self.worker is not None:
            return
        self.current_site_id = site_id
        for button_site_id, button in self.site_buttons.items():
            button.set_selected(button_site_id == site_id)
        self.set_headless(SITES[site_id].default_headless, animated=False)
        self._refresh_start_state()

    def _headless_changed(self, checked: bool) -> None:
        if self.worker is not None:
            self.headless_switch.blockSignals(True)
            self.headless_switch.setChecked(self.headless)
            self.headless_switch.blockSignals(False)
            return
        self.set_headless(checked, animated=True)

    def _debug_screenshots_changed(self, checked: bool) -> None:
        self.debug_screenshots = checked

    def set_headless(self, headless: bool, *, animated: bool = True) -> None:
        self.headless = headless
        if self.headless_switch.isChecked() != headless:
            self.headless_switch.blockSignals(True)
            self.headless_switch.setChecked(headless)
            self.headless_switch.blockSignals(False)

        if self._browser_animation is not None:
            self._browser_animation.stop()

        if not animated:
            if headless:
                self._set_browser_split_width(0)
                self.browser_panel.hide()
            else:
                self.browser_panel.show()
                self._set_browser_split_width(self._browser_target_width())
            return

        current_width = self.content_splitter.sizes()[1]
        if headless:
            animation = QVariantAnimation(self)
            animation.setStartValue(current_width)
            animation.setEndValue(0)
            animation.finished.connect(self.browser_panel.hide)
        else:
            self.browser_panel.show()
            animation = QVariantAnimation(self)
            animation.setStartValue(current_width)
            animation.setEndValue(self._browser_target_width())

        animation.valueChanged.connect(
            lambda value: self._set_browser_split_width(int(value))
        )
        animation.setDuration(240)
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._browser_animation = animation
        animation.start()

    def _browser_target_width(self) -> int:
        total_width = max(
            self.content_splitter.width(),
            sum(self.content_splitter.sizes()),
            self.width() - 36,
        )
        return max(500, min(760, int(total_width * 0.42)))

    def _set_browser_split_width(self, browser_width: int) -> None:
        current_sizes = self.content_splitter.sizes()
        total_width = max(
            self.content_splitter.width(),
            sum(current_sizes),
            self.width() - 36,
        )
        browser_width = max(0, min(browser_width, total_width - 1))
        self.browser_panel.setMinimumWidth(0)
        self.browser_panel.setMaximumWidth(16_777_215)
        self.content_splitter.setSizes(
            [max(1, total_width - browser_width), browser_width]
        )

    def _refresh_start_state(self) -> None:
        config_missing = not self.config_path.exists()
        blocked = config_missing
        if not blocked:
            blocked = is_config_same_as_default(self.config_path)
        self.start_button.setEnabled(not blocked and self.worker is None)
        if self.worker is not None:
            return
        if config_missing:
            self.status_display.set_ready("Create config: click settings")
        elif blocked:
            self.status_display.set_ready("Configuration required")
        else:
            self.status_display.set_ready("Ready")

    def _start_worker(self) -> None:
        if self.worker is not None:
            return
        errors = config_validation_errors(self.current_site_id, self.config_path)
        if errors:
            QMessageBox.warning(
                self,
                "Configuration required",
                "Complete these values before starting:\n\n" + "\n".join(errors),
            )
            self._refresh_start_state()
            return

        token = None if self.headless else str(uuid.uuid4())
        program, args = build_worker_invocation(
            self.current_site_id,
            headless=self.headless,
            token=token,
            frozen=getattr(sys, "frozen", False),
            debug_screenshots=self.debug_screenshots,
        )

        process = QProcess(self)
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.setWorkingDirectory(str(find_runtime_root()))
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        environment.insert("PYTHONIOENCODING", "utf-8:replace")
        environment.insert("PYTHONUTF8", "1")
        process.setProcessEnvironment(environment)
        process.readyReadStandardOutput.connect(self._read_worker_output)
        process.finished.connect(self._worker_finished)
        process.errorOccurred.connect(self._worker_error)
        self.worker = process

        if token:
            self.browser_monitor = ChromeWindowMonitor(
                token,
                self.browser_backend,
                self,
            )
            self.browser_monitor.windowsChanged.connect(self.browser_panel.set_windows)
            self.browser_monitor.fatalError.connect(self._embedding_failed)
            self.browser_monitor.start()

        self._append_log(f"Starting {SITES[self.current_site_id].display_name}")
        self._set_running_controls(True)
        self.status_display.set_running(SITES[self.current_site_id].display_name)
        process.start(program, args)

    def _read_worker_output(self) -> None:
        if self.worker is None:
            return
        chunk = bytes(self.worker.readAllStandardOutput()).decode(
            "utf-8",
            errors="replace",
        )
        self._log_buffer += chunk
        while "\n" in self._log_buffer:
            line, self._log_buffer = self._log_buffer.split("\n", 1)
            self._append_log(line.rstrip("\r"))

    def _stop_worker(self) -> None:
        if self.worker is None:
            return
        self.status_display.set_stopping()
        self.stop_button.setEnabled(False)
        pid = int(self.worker.processId())
        if pid <= 0:
            self.worker.kill()
            return
        threading.Thread(
            target=terminate_process_tree,
            args=(pid,),
            daemon=True,
        ).start()

    def _worker_finished(self, exit_code: int, _exit_status) -> None:
        if self._log_buffer:
            self._append_log(self._log_buffer.rstrip("\r\n"))
            self._log_buffer = ""
        self._append_log(f"Worker exited with code {exit_code}")
        if self.browser_monitor is not None:
            self.browser_monitor.stop()
            self.browser_monitor.deleteLater()
            self.browser_monitor = None
        self.browser_panel.clear_windows()
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        self._set_running_controls(False)
        self._refresh_start_state()

    def _worker_error(self, error) -> None:
        self._append_log(f"Worker process error: {error}")
        if error == QProcess.ProcessError.FailedToStart and self.worker is not None:
            self._worker_finished(-1, None)

    def _embedding_failed(self, message: str) -> None:
        self._append_log(f"Browser embedding error: {message}")
        if self.worker is not None:
            self._stop_worker()
        QMessageBox.critical(self, "Browser embedding failed", message)

    def _set_running_controls(self, running: bool) -> None:
        self.start_button.setEnabled(False if running else self.start_button.isEnabled())
        self.stop_button.setEnabled(running)
        self.headless_switch.setEnabled(not running)
        self.debug_screenshots_switch.setEnabled(not running)
        self.config_button.setEnabled(not running)
        for button in self.site_buttons.values():
            button.setEnabled(not running)

    def _open_config_editor(self) -> None:
        if not self.config_path.exists():
            self.config_path = ensure_config_file(self.config_path)
        dialog = ConfigDialog(
            self.config_path,
            active_site_id=self.current_site_id,
            parent=self,
        )
        dialog.saved.connect(self._refresh_start_state)
        dialog.exec()

    def _prompt_create_config(self) -> None:
        if self.config_path.exists():
            return
        answer = QMessageBox.question(
            self,
            "Create configuration",
            "config.ini was not found beside AutosubscriberApp.exe.\n\n"
            "Create it from the default template and open the configuration editor?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            self._refresh_start_state()
            return
        self.config_path = ensure_config_file(self.config_path)
        self._refresh_start_state()
        self._open_config_editor()

    def _open_screenshots(self) -> None:
        screenshots = find_runtime_root() / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        os.startfile(str(screenshots))

    def _clear_logs(self) -> None:
        self.log_view.clear()

    def _append_log(self, line: str) -> None:
        self.log_view.append_line(line)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker is not None:
            pid = int(self.worker.processId())
            if pid > 0:
                terminate_process_tree(pid)
        if self.browser_monitor is not None:
            self.browser_monitor.stop()
        self.browser_panel.clear_windows()
        event.accept()
