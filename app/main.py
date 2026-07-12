from __future__ import annotations

import ctypes
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--worker":
        from app.worker import main as worker_main

        return worker_main(args[1:])

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Autosubscriber.App"
        )

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from app.main_window import MainWindow
    from app.site_registry import resolve_asset
    from app.theme import apply_theme

    app = QApplication([sys.argv[0], *args])
    app.setApplicationName("Autosubscriber App")
    app.setOrganizationName("Autosubscriber")
    icon = QIcon(str(resolve_asset("app/assets/branding/autosubscriber-logo.png")))
    app.setWindowIcon(icon)
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
