from __future__ import annotations

from typing import Any


class SettingsDialog:
    """Minimal settings dialog for the GTK application."""

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings

    def show(self) -> None:
        return None
