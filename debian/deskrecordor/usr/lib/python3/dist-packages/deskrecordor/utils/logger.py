from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(name: str = "deskrecordor", log_dir: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    log_directory = Path(log_dir or Path.home() / ".local" / "state" / "deskrecordor")
    log_directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_directory / "deskrecordor.log", maxBytes=2_000_000, backupCount=3)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
