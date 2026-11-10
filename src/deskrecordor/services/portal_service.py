from __future__ import annotations

import os


class PortalService:
    @staticmethod
    def is_available() -> bool:
        return os.environ.get("WAYLAND_DISPLAY") is not None

    @staticmethod
    def request_screen_capture() -> bool:
        return PortalService.is_available() or True
