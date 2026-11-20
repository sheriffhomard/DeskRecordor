from __future__ import annotations

import shutil


class PipeWireService:
    @staticmethod
    def is_available() -> bool:
        return shutil.which("pw-cli") is not None or shutil.which("pactl") is not None

    @staticmethod
    def default_source() -> str:
        return "default"
