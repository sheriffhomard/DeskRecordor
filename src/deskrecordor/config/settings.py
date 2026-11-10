from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path.home() / "Videos" / "DeskRecordor"


def _xdg_config_dir() -> Path:
    override = os.environ.get("XDG_CONFIG_HOME")
    if override:
        return Path(override) / "deskrecordor"
    return Path.home() / ".config" / "deskrecordor"


@dataclass
class Settings:
    output_dir: str = str(DEFAULT_OUTPUT_DIR)
    default_microphone: str | None = None
    default_monitor: str | None = None
    final_format: str = "mp4"
    video_quality: str = "balanced"
    countdown: bool = False
    output_prefix: str = "deskrecordor"
    version: int = 1
    last_recording_name: str | None = None

    @classmethod
    def default(cls) -> "Settings":
        settings = cls()
        settings.output_dir = str(DEFAULT_OUTPUT_DIR)
        return settings

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> "Settings":
        config_path = Path(path) if path else _xdg_config_dir() / "settings.json"
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    settings = cls(**{**cls.default().__dict__, **payload})
                    settings.output_dir = str(Path(settings.output_dir).expanduser())
                    return settings
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        settings = cls.default()
        settings.save(config_path)
        return settings

    def save(self, path: str | os.PathLike[str] | None = None) -> Path:
        config_path = Path(path) if path else _xdg_config_dir() / "settings.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        return config_path

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def ensure_output_dir(self) -> Path:
        output = Path(self.output_dir).expanduser()
        output.mkdir(parents=True, exist_ok=True)
        return output
