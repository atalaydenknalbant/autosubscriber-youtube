from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid

from app.site_registry import (
    SITES,
    build_required_dict,
    config_validation_errors,
    find_default_config_path,
    find_config_path,
    find_runtime_root,
    resolve_asset,
)


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def configure_logging() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    class Utf8StdoutHandler(logging.StreamHandler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                message = self.format(record) + self.terminator
                if hasattr(self.stream, "buffer"):
                    self.stream.buffer.write(message.encode("utf-8", errors="replace"))
                    self.stream.flush()
                else:
                    self.stream.write(message)
                    self.stream.flush()
            except Exception:
                self.handleError(record)

    handler = Utf8StdoutHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def verify_packaged_runtime() -> None:
    import cv2
    import google.protobuf
    import sentencepiece
    import sentencepiece._sentencepiece
    import selenium
    import timm
    import torch
    import transformers
    from PySide6 import QtCore
    from transformers.models.xlm_roberta.tokenization_xlm_roberta import (
        XLMRobertaTokenizer,
    )

    required_files = (
        find_default_config_path(),
        resolve_asset("app/assets/branding/autosubscriber-logo.png"),
        resolve_asset("extensions/AutoTubeYouTube-nonstop.crx"),
        resolve_asset("ytmonsterru_assets/canvas1.png"),
        resolve_asset("ytmonsterru_assets/canvas2.png"),
    )
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise RuntimeError("Missing packaged files: " + ", ".join(missing))

    loaded_modules = (
        cv2,
        google.protobuf,
        sentencepiece,
        sentencepiece._sentencepiece,
        selenium,
        timm,
        torch,
        transformers,
        QtCore,
        XLMRobertaTokenizer,
    )
    if not all(loaded_modules):
        raise RuntimeError("A packaged runtime dependency did not load")


def prepare_runtime_directory(debug_screenshots: bool) -> None:
    runtime_root = find_runtime_root()
    runtime_root.mkdir(parents=True, exist_ok=True)
    os.chdir(runtime_root)
    if debug_screenshots:
        (runtime_root / "screenshots/debug").mkdir(parents=True, exist_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=sorted(SITES))
    parser.add_argument("--headless", default="true")
    parser.add_argument("--debug-screenshots", default="false")
    parser.add_argument("--embed-parent-hwnd", type=int, default=None)
    parser.add_argument("--embed-token", default=None)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--check-runtime", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    debug_screenshots = parse_bool(args.debug_screenshots)
    prepare_runtime_directory(debug_screenshots)

    if args.check_runtime:
        try:
            verify_packaged_runtime()
        except Exception:
            logging.exception("[AppWorker] Packaged runtime check failed")
            return 1
        print("Packaged runtime OK", flush=True)
        return 0

    if not args.site:
        logging.error("[AppWorker] --site is required")
        return 2

    errors = config_validation_errors(args.site)
    if args.check_config:
        if errors:
            for error in errors:
                print(error, flush=True)
            return 1
        print(f"Config OK: {find_config_path()}", flush=True)
        return 0

    if errors:
        for error in errors:
            logging.error("[AppWorker] Config error: %s", error)
        return 2

    headless = parse_bool(args.headless)
    embed_token = args.embed_token
    if not embed_token and args.embed_parent_hwnd and not headless:
        embed_token = str(uuid.uuid4())
    req_dict = build_required_dict(
        args.site,
        headless=headless,
        debug_screenshots=debug_screenshots,
        embed_parent_hwnd=args.embed_parent_hwnd,
        embed_window_token=embed_token,
    )

    from selenium_codes import sub4sub_websites_selenium as sws

    spec = SITES[args.site]
    logging.info("[AppWorker] Starting %s", spec.display_name)
    try:
        getattr(sws, spec.function_name)(req_dict)
    except KeyboardInterrupt:
        logging.info("[AppWorker] Stopped by interrupt")
        return 130
    except Exception:
        logging.exception("[AppWorker] Site run failed")
        return 1
    logging.info("[AppWorker] Finished %s", spec.display_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
