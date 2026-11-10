from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def default_output_dir() -> Path:
    return Path.home() / "Videos" / "DeskRecordor"


def generate_output_filename(prefix: str = "deskrecordor", extension: str = ".mp4") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}_{prefix}{extension}"
    return filename


def ensure_unique_path(path: str | os.PathLike[str]) -> Path:
    candidate = Path(path)
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        new_path = candidate.with_name(f"{stem}_{counter}{suffix}")
        if not new_path.exists():
            return new_path
        counter += 1


def check_disk_space(path: str | os.PathLike[str]) -> int:
    disk_usage = shutil.disk_usage(str(Path(path).expanduser()))
    return int(disk_usage.free)


def open_directory(path: str | os.PathLike[str]) -> bool:
    target = Path(path).expanduser()
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
    command = ["xdg-open", str(target)]
    if shutil.which("xdg-open") is None:
        return False
    completed = subprocess.run(command, capture_output=True, check=False)
    return completed.returncode == 0


def cleanup_temp_files(paths: list[str | os.PathLike[str]]) -> None:
    for item in paths:
        file_path = Path(item)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
