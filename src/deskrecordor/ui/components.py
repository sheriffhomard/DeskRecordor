from __future__ import annotations

class VUMeter:
    """Simple text-based vumeter used when GTK is unavailable."""

    def __init__(self, level: float = 0.0) -> None:
        self.level = level

    def set_level(self, level: float) -> float:
        self.level = max(0.0, min(float(level), 1.0))
        return self.level

    def render(self) -> str:
        filled = int(round(self.level * 20))
        return "|" * filled + "-" * (20 - filled)


class TimerLabel:
    def __init__(self, seconds: int = 0) -> None:
        self.seconds = seconds

    def tick(self, seconds: int = 1) -> int:
        self.seconds += seconds
        return self.seconds

    def format(self) -> str:
        hours, remainder = divmod(self.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
