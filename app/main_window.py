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
    QPropertyAnimation,
    QTimer,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
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
    HeadlessChromeWindowGuard,
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
from app.update_manager import (
    ReleaseInfo,
    ReleaseStatus,
    UpdateManager,
    can_replace_current_executable,
    is_newer_version,
    launch_update_replacement,
)
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
    if token:
        args.extend(["--embed-token", token])
    return program, args


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_path: Path | None = None,
        browser_backend: ChromeBackend | None = None,
        update_manager: UpdateManager | None = None,
        auto_check_updates: bool = True,
    ) -> None:
        super().__init__()
        self.config_path = config_path or find_config_path()
        self._prompt_for_missing_config = (
            config_path is None and not self.config_path.exists()
        )
        self.browser_backend = browser_backend or Win32ChromeBackend()
        self.worker: QProcess | None = None
        self.browser_monitor: ChromeWindowMonitor | None = None
        self.headless_window_guard: HeadlessChromeWindowGuard | None = None
        self.current_site_id = next(iter(SITES))
        self.headless = True
        self.debug_screenshots = False
        self._log_buffer = ""
        self._browser_animation: QVariantAnimation | None = None
        self._site_selector_animation: QPropertyAnimation | None = None
        self._site_selector_expanded_height = 0
        self.update_manager = update_manager or UpdateManager(self)
        self._manual_update_check = False
        self._latest_release: ReleaseInfo | None = None
        self._pending_update: tuple[Path, ReleaseInfo] | None = None
        self._update_installing = False
        self._startup_update_timer: QTimer | None = None

        self.setWindowTitle("Autosubscriber App")
        self.setWindowIcon(
            QIcon(str(resolve_asset("app/assets/branding/autosubscriber-logo.png")))
        )
        self.resize(1440, 900)
        self.setMinimumSize(1100, 720)
        self._build_ui()
        self._connect_update_manager()
        self.select_site(self.current_site_id)
        self._refresh_start_state()
        if self._prompt_for_missing_config:
            QTimer.singleShot(0, self._prompt_create_config)
        if auto_check_updates:
            self._startup_update_timer = QTimer(self)
            self._startup_update_timer.setSingleShot(True)
            self._startup_update_timer.timeout.connect(self._startup_update_check)
            self._startup_update_timer.start(800)

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
        self.site_selector_panel = self._build_site_selector()
        body_layout.addWidget(self.site_selector_panel)
        body_layout.addWidget(self._build_content(), 1)
        root.addWidget(body, 1)

    def _build_header(self) -> GradientHeader:
        header = GradientHeader(self)
        self.header_layout = QGridLayout(header)
        self.header_layout.setContentsMargins(20, 10, 20, 10)
        self.header_layout.setHorizontalSpacing(12)
        self.header_layout.setVerticalSpacing(6)
        self._header_compact: bool | None = None

        self.header_logo = QLabel(header)
        pixmap = QPixmap(
            str(resolve_asset("app/assets/branding/autosubscriber-logo.png"))
        )
        self.header_logo.setPixmap(
            pixmap.scaled(
                52,
                52,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self.header_logo.setFixedSize(54, 54)

        self.header_brand_widget = QWidget(header)
        self.header_brand_widget.setStyleSheet("background: transparent;")
        brand = QVBoxLayout(self.header_brand_widget)
        brand.setContentsMargins(0, 0, 0, 0)
        brand.setSpacing(0)
        title = QLabel("AUTOSUBSCRIBER", self.header_brand_widget)
        title.setStyleSheet(
            f"color: {Colors.WHITE}; font-size: 17pt; font-weight: 700;"
        )
        self.header_subtitle = QLabel(
            "Selenium automation control center",
            self.header_brand_widget,
        )
        self.header_subtitle.setStyleSheet(
            f"color: {Colors.MUTED}; font-size: 9pt;"
        )
        brand.addWidget(title)
        brand.addWidget(self.header_subtitle)

        self.status_display = StatusDisplay(header)

        self.header_version_widget = QWidget(header)
        self.header_version_widget.setStyleSheet("background: transparent;")
        self.header_version_widget.setFixedWidth(116)
        version_layout = QVBoxLayout(self.header_version_widget)
        version_layout.setContentsMargins(2, 0, 2, 0)
        version_layout.setSpacing(0)
        self.installed_version_label = QLabel(
            "App detecting",
            self.header_version_widget,
        )
        self.installed_version_label.setAlignment(Qt.AlignRight)
        self.installed_version_label.setStyleSheet(
            f"color: {Colors.WHITE}; font-size: 8pt; font-weight: 600;"
        )
        self.latest_version_label = QLabel(
            "Latest checking",
            self.header_version_widget,
        )
        self.latest_version_label.setAlignment(Qt.AlignRight)
        self.latest_version_label.setStyleSheet(
            f"color: {Colors.MUTED}; font-size: 8pt;"
        )
        version_layout.addWidget(self.installed_version_label)
        version_layout.addWidget(self.latest_version_label)

        self.update_button = IconButton(
            "refresh",
            "Check for application updates",
            header,
        )
        self.update_button.clicked.connect(self._manual_check_for_updates)

        self.header_action_bar = QWidget(header)
        self.header_action_bar.setStyleSheet("background: transparent;")
        action_layout = QHBoxLayout(self.header_action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)

        controls = QWidget(self.header_action_bar)
        controls.setObjectName("headerControls")
        controls.setStyleSheet("background: transparent;")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(4, 0, 4, 0)
        controls_layout.setHorizontalSpacing(8)
        controls_layout.setVerticalSpacing(1)

        headless_title = QLabel("Headless", controls)
        headless_title.setAlignment(Qt.AlignCenter)
        headless_title.setStyleSheet(
            f"color: {Colors.WHITE}; font-size: 8pt; font-weight: 600;"
        )
        headless_title.setMinimumWidth(headless_title.sizeHint().width() + 6)
        controls_layout.addWidget(headless_title, 0, 0)

        self.headless_switch = AnimatedSwitch(controls)
        self.headless_switch.setToolTip("Show logs only without an embedded browser")
        self.headless_switch.checkedChanged.connect(self._headless_changed)
        controls_layout.addWidget(
            self.headless_switch,
            1,
            0,
            alignment=Qt.AlignCenter,
        )

        self.debug_screenshots_label = QLabel("Debug screenshots", controls)
        self.debug_screenshots_label.setAlignment(Qt.AlignCenter)
        self.debug_screenshots_label.setStyleSheet(
            f"color: {Colors.WHITE}; font-size: 8pt; font-weight: 600;"
        )
        self.debug_screenshots_label.setMinimumWidth(
            self.debug_screenshots_label.sizeHint().width() + 6
        )
        controls_layout.addWidget(self.debug_screenshots_label, 0, 1)

        self.debug_screenshots_switch = AnimatedSwitch(controls)
        self.debug_screenshots_switch.setToolTip(
            "Save diagnostic screenshots during website runs"
        )
        self.debug_screenshots_switch.checkedChanged.connect(
            self._debug_screenshots_changed
        )
        controls_layout.addWidget(
            self.debug_screenshots_switch,
            1,
            1,
            alignment=Qt.AlignCenter,
        )

        self.start_button = IconButton(
            "play",
            "Start selected website",
            controls,
        )
        self.start_button.clicked.connect(self._start_worker)
        controls_layout.addWidget(self.start_button, 0, 2, 2, 1)

        self.stop_button = IconButton(
            "stop",
            "Stop current website",
            controls,
        )
        self.stop_button.clicked.connect(self._stop_worker)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.stop_button, 0, 3, 2, 1)

        action_layout.addWidget(controls)

        self.config_button = IconButton(
            "settings",
            "Configure accounts",
            self.header_action_bar,
        )
        self.config_button.clicked.connect(self._open_config_editor)
        action_layout.addWidget(self.config_button)

        self.screenshots_button = IconButton(
            "folder",
            "Open screenshots folder",
            self.header_action_bar,
        )
        self.screenshots_button.clicked.connect(self._open_screenshots)
        action_layout.addWidget(self.screenshots_button)

        self.clear_logs_button = IconButton(
            "broom",
            "Clear logs",
            self.header_action_bar,
        )
        self.clear_logs_button.clicked.connect(self._clear_logs)
        action_layout.addWidget(self.clear_logs_button)
        self.header_action_bar.setMinimumWidth(
            self.header_action_bar.sizeHint().width()
        )

        self._apply_header_layout(self.width() < 1280)
        return header

    def _apply_header_layout(self, compact: bool) -> None:
        if self._header_compact == compact:
            return
        self._header_compact = compact
        layout = self.header_layout
        while layout.count():
            layout.takeAt(0)
        for column in range(7):
            layout.setColumnStretch(column, 0)

        if compact:
            layout.addWidget(self.header_logo, 0, 0, 2, 1)
            layout.addWidget(self.header_brand_widget, 0, 1)
            layout.setColumnStretch(2, 1)
            layout.addWidget(self.status_display, 0, 3)
            layout.addWidget(self.header_version_widget, 0, 4)
            layout.addWidget(self.update_button, 0, 5)
            layout.addWidget(
                self.header_action_bar,
                1,
                1,
                1,
                5,
                alignment=Qt.AlignRight,
            )
            self.header_subtitle.hide()
        else:
            layout.addWidget(self.header_logo, 0, 0)
            layout.addWidget(self.header_brand_widget, 0, 1)
            layout.setColumnStretch(2, 1)
            layout.addWidget(self.status_display, 0, 3)
            layout.addWidget(self.header_version_widget, 0, 4)
            layout.addWidget(self.update_button, 0, 5)
            layout.addWidget(self.header_action_bar, 0, 6)
            self.header_subtitle.show()
        self.header_action_bar.updateGeometry()

    def _connect_update_manager(self) -> None:
        self.update_manager.checkStarted.connect(self._update_check_started)
        self.update_manager.checkSucceeded.connect(self._update_check_succeeded)
        self.update_manager.checkFailed.connect(self._update_check_failed)
        self.update_manager.downloadStarted.connect(self._update_download_started)
        self.update_manager.downloadProgress.connect(self._update_download_progress)
        self.update_manager.downloadReady.connect(self._update_download_ready)
        self.update_manager.downloadFailed.connect(self._update_download_failed)

    def _startup_update_check(self) -> None:
        self._check_for_updates(manual=False)

    def _manual_check_for_updates(self) -> None:
        self._check_for_updates(manual=True)

    def _check_for_updates(self, *, manual: bool) -> None:
        self._manual_update_check = manual
        if not self.update_manager.check_for_updates() and manual:
            QMessageBox.information(
                self,
                "Update check",
                "An update check is already running.",
            )

    def _update_check_started(self) -> None:
        self.update_button.setEnabled(False)
        self.latest_version_label.setText("Latest checking")
        self.latest_version_label.setStyleSheet(
            f"color: {Colors.MUTED}; font-size: 8pt;"
        )

    def _update_check_succeeded(self, status: ReleaseStatus) -> None:
        release = status.latest
        self._latest_release = release
        self.update_button.setEnabled(True)
        self.latest_version_label.setText(f"Latest {release.version}")
        if status.installed_version is None:
            installed_label = (
                "App local build"
                if can_replace_current_executable()
                else "App development"
            )
            self.installed_version_label.setText(installed_label)
            self.latest_version_label.setStyleSheet(
                f"color: {Colors.WARNING}; font-size: 8pt;"
            )
            self._append_log(
                "The running application has no generated release metadata."
            )
            if self._manual_update_check:
                QMessageBox.information(
                    self,
                    "Application update",
                    f"Latest published version: {release.version}.\n\n"
                    "This local build has no release baseline, so its version "
                    "cannot be compared automatically.",
                )
            self._manual_update_check = False
            return

        local_suffix = "" if status.installed_from_release_asset else " local"
        self.installed_version_label.setText(
            f"App {status.installed_version}{local_suffix}"
        )
        newer = is_newer_version(
            release.version,
            status.installed_version,
        )
        self.latest_version_label.setStyleSheet(
            f"color: {Colors.WARNING if newer else Colors.SUCCESS}; font-size: 8pt;"
        )
        if not newer:
            if self._manual_update_check:
                QMessageBox.information(
                    self,
                    "Application update",
                    f"Autosubscriber App {status.installed_version} is current.",
                )
            self._manual_update_check = False
            return

        self._append_log(
            f"Application update {release.version} is available."
        )
        if not can_replace_current_executable():
            self._append_log(
                "Automatic installation is available in the packaged Windows EXE."
            )
            if self._manual_update_check:
                QMessageBox.information(
                    self,
                    "Application update",
                    f"Version {release.version} is available. Automatic installation "
                    "runs only from AutosubscriberApp.exe.",
                )
            self._manual_update_check = False
            return

        self._manual_update_check = False
        if not self.update_manager.download_update(release):
            self._append_log("The application update is already downloading.")

    def _update_check_failed(self, message: str) -> None:
        self.update_button.setEnabled(True)
        self.latest_version_label.setText("Latest unavailable")
        self.latest_version_label.setStyleSheet(
            f"color: {Colors.ERROR}; font-size: 8pt;"
        )
        self._append_log(f"Update check failed: {message}")
        if self._manual_update_check:
            QMessageBox.warning(self, "Update check failed", message)
        self._manual_update_check = False

    def _update_download_started(self, release: ReleaseInfo) -> None:
        self.update_button.setEnabled(False)
        self.latest_version_label.setText(f"Update {release.version} 0%")

    def _update_download_progress(self, percent: int) -> None:
        if self._latest_release is None:
            return
        self.latest_version_label.setText(
            f"Update {self._latest_release.version} {percent}%"
        )

    def _update_download_ready(self, path: Path, release: ReleaseInfo) -> None:
        self._pending_update = (Path(path), release)
        self.latest_version_label.setText(f"Ready {release.version}")
        self.latest_version_label.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-size: 8pt;"
        )
        self._append_log(
            f"Application update {release.version} downloaded and verified."
        )
        if self.worker is None:
            QTimer.singleShot(0, self._install_pending_update)
        else:
            self._append_log(
                "The update will install after the current website run stops."
            )

    def _update_download_failed(self, message: str) -> None:
        self.update_button.setEnabled(True)
        latest = self._latest_release.version if self._latest_release else "unknown"
        self.latest_version_label.setText(f"Update {latest} failed")
        self.latest_version_label.setStyleSheet(
            f"color: {Colors.ERROR}; font-size: 8pt;"
        )
        self._append_log(f"Update download failed: {message}")

    def _install_pending_update(self) -> None:
        if self._pending_update is None or self.worker is not None:
            return
        if QApplication.activeModalWidget() is not None:
            QTimer.singleShot(1000, self._install_pending_update)
            return
        if not self._launch_pending_update_replacement():
            return
        release = self._pending_update[1]
        self._append_log(
            f"Restarting with Autosubscriber App {release.version}."
        )
        self.close()

    def _launch_pending_update_replacement(self) -> bool:
        if self._pending_update is None or self._update_installing:
            return self._update_installing
        path, release = self._pending_update
        try:
            launch_update_replacement(
                path,
                Path(sys.executable),
                release.sha256,
            )
        except (OSError, RuntimeError, ValueError) as error:
            self.update_button.setEnabled(True)
            self.latest_version_label.setText(f"Update {release.version} failed")
            self._append_log(f"Update installation failed: {error}")
            QMessageBox.warning(self, "Update installation failed", str(error))
            return False
        self._update_installing = True
        return True

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

    def _set_site_selector_visible(
        self,
        visible: bool,
        *,
        animated: bool = True,
    ) -> None:
        panel = self.site_selector_panel
        if not visible and panel.height() > 0:
            self._site_selector_expanded_height = panel.height()
        if self._site_selector_animation is not None:
            self._site_selector_animation.stop()
            self._site_selector_animation.deleteLater()
            self._site_selector_animation = None

        if not animated:
            panel.setMaximumHeight(16_777_215 if visible else 0)
            panel.setVisible(visible)
            return

        if visible and panel.isVisible() and panel.maximumHeight() > 0:
            return
        if not visible and not panel.isVisible():
            return

        expanded_height = max(
            self._site_selector_expanded_height,
            panel.sizeHint().height(),
            122,
        )
        animation = QPropertyAnimation(
            panel,
            b"maximumHeight",
            self,
        )

        if visible:
            panel.setMaximumHeight(0)
            panel.show()
            animation.setStartValue(0)
            animation.setEndValue(expanded_height)
            animation.finished.connect(self._site_selector_shown)
        else:
            animation.setStartValue(panel.height())
            animation.setEndValue(0)
            animation.finished.connect(self._site_selector_hidden)

        animation.setDuration(280)
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._site_selector_animation = animation
        animation.start()

    def _site_selector_hidden(self) -> None:
        self.site_selector_panel.hide()

    def _site_selector_shown(self) -> None:
        panel = self.site_selector_panel
        panel.setMaximumHeight(16_777_215)
        panel.updateGeometry()
        if panel.layout() is not None:
            panel.layout().activate()
        panel.update()
        for button in self.site_buttons.values():
            button.update()

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

        token = str(uuid.uuid4())
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

        if self.headless:
            self.headless_window_guard = HeadlessChromeWindowGuard(
                token,
                self.browser_backend,
                self,
            )
            self.headless_window_guard.start()
        else:
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
        if self.headless_window_guard is not None:
            self.headless_window_guard.stop()
            self.headless_window_guard.deleteLater()
            self.headless_window_guard = None
        self.browser_panel.clear_windows()
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        self._set_running_controls(False)
        self._refresh_start_state()
        if self._pending_update is not None:
            QTimer.singleShot(0, self._install_pending_update)

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
        self._set_site_selector_visible(not running, animated=True)
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

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "header_layout"):
            self._apply_header_layout(event.size().width() < 1280)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._startup_update_timer is not None:
            self._startup_update_timer.stop()
        if self._pending_update is not None and not self._update_installing:
            self._launch_pending_update_replacement()
        if self.worker is not None:
            pid = int(self.worker.processId())
            if pid > 0:
                terminate_process_tree(pid)
        if self.browser_monitor is not None:
            self.browser_monitor.stop()
        if self.headless_window_guard is not None:
            self.headless_window_guard.stop()
        self.browser_panel.clear_windows()
        event.accept()
