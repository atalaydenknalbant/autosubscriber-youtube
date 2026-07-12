from __future__ import annotations

import contextlib
import io
import logging
import threading
from pathlib import Path
from typing import Any


_lock = threading.RLock()
_active_driver: Any = None
_active_website = ""
_active_req_dict: dict[str, Any] = {}


def set_active_driver(driver: Any, website: str, req_dict: dict[str, Any]) -> None:
    global _active_driver, _active_website, _active_req_dict
    with _lock:
        _active_driver = driver
        _active_website = website
        _active_req_dict = dict(req_dict)


def clear_active_driver(driver: Any | None = None) -> None:
    global _active_driver, _active_website, _active_req_dict
    with _lock:
        if driver is not None and _active_driver is not driver:
            return
        _active_driver = None
        _active_website = ""
        _active_req_dict = {}


def execute_debug_code(code: str, sws_module: Any) -> None:
    with _lock:
        driver = _active_driver
        website = _active_website
        req_dict = dict(_active_req_dict)

    if driver is None:
        logging.info("[AppDebug] No active Selenium driver yet")
        return

    stdout_buffer = io.StringIO()
    namespace = {
        "driver": driver,
        "website": website,
        "req_dict": req_dict,
        "logging": logging,
        "Path": Path,
        "sws": sws_module,
    }
    try:
        with contextlib.redirect_stdout(stdout_buffer):
            exec(code, namespace, namespace)
    except Exception:
        logging.exception("[AppDebug] Debug code failed")
    output = stdout_buffer.getvalue().strip()
    if output:
        for line in output.splitlines():
            logging.info("[AppDebug] %s", line)
