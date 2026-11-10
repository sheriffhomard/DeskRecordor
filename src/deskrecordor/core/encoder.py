from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EncoderConfig:
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    fps: int = 30
    output_format: str = "mp4"
    audio_bitrate: str = "192k"
    sample_rate: int = 48000
    audio_channels: int = 1

    @classmethod
    def default(cls) -> "EncoderConfig":
        return cls()


class VideoEncoder:
    def __init__(self, ffmpeg_path: str | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg") or "ffmpeg"

    def is_available(self) -> bool:
        return shutil.which("ffmpeg") is not None or self.ffmpeg_path != "ffmpeg"

    def build_command(self, input_path: str | os.PathLike[str], output_path: str | os.PathLike[str], config: EncoderConfig | None = None) -> list[str]:
        config = config or EncoderConfig.default()
        source = str(Path(input_path))
        target = str(Path(output_path))
        return [
            self.ffmpeg_path,
            "-y",
            "-i",
            source,
            "-c:v",
            config.video_codec,
            "-r",
            str(config.fps),
            "-c:a",
            config.audio_codec,
            "-ar",
            str(config.sample_rate),
            "-ac",
            str(config.audio_channels),
            "-b:a",
            config.audio_bitrate,
            target,
        ]

    def finalize(self, input_path: str | os.PathLike[str], output_path: str | os.PathLike[str], config: EncoderConfig | None = None) -> Path:
        input_file = Path(input_path)
        output_file = Path(output_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        if shutil.which("ffmpeg") is None and self.ffmpeg_path == "ffmpeg":
            return output_file
        command = self.build_command(input_file, output_file, config)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "FFmpeg finalization failed")
        return output_file

    @staticmethod
    def validate_output(path: str | os.PathLike[str]) -> bool:
        file_path = Path(path)
        return file_path.exists() and file_path.is_file() and file_path.stat().st_size > 0
