from __future__ import annotations

from deskrecordor.core.encoder import EncoderConfig, VideoEncoder


class FFmpegService:
    def __init__(self, ffmpeg_path: str | None = None) -> None:
        self.encoder = VideoEncoder(ffmpeg_path=ffmpeg_path)

    def is_available(self) -> bool:
        return self.encoder.is_available()

    def finalize(self, input_path, output_path, config: EncoderConfig | None = None):
        return self.encoder.finalize(input_path, output_path, config=config)
