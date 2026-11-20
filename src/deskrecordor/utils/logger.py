from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(name: str = "deskrecordor", log_dir: str | None = None) -> logging.Logger:
    root_logger = logging.getLogger("deskrecordor")
    root_logger.setLevel(logging.DEBUG)
    if not root_logger.handlers:
        state_dir = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
        log_directory = Path(log_dir) if log_dir else state_dir / "deskrecordor"
        log_directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_directory / "deskrecordor.log",
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger


def get_log_file_path() -> Path:
    logger = get_logger()
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            return Path(handler.baseFilename)
    raise RuntimeError("DeskRecordor file logger is not configured")
