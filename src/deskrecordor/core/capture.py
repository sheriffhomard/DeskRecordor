from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
import subprocess


@dataclass
class MonitorInfo:
    name: str
    monitor_id: str
    width: int
    height: int
    primary: bool = False

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"


class ScreenCapture:
    """Describe available screens and pick a default monitor."""

    @staticmethod
    def list_monitors() -> list[MonitorInfo]:
        xrandr = shutil.which("xrandr")
        if xrandr:
            result = subprocess.run([xrandr], capture_output=True, text=True, check=False)
            lines = result.stdout.splitlines()
            monitors: list[MonitorInfo] = []
            for line in lines:
                if " connected" not in line:
                    continue
                pieces = line.split()
                name = pieces[0]
                width = 1920
                height = 1080
                if len(pieces) >= 3 and pieces[1] == "connected":
                    try:
                        resolution = pieces[2]
                        if "x" in resolution:
                            width_text, height_text = resolution.split("x", 1)
                            width = int(width_text)
                            height = int(height_text)
                    except ValueError:
                        pass
                monitors.append(MonitorInfo(name=name, monitor_id=name, width=width, height=height, primary=name == "eDP-1" or "primary" in line))
            if monitors:
                return monitors
        if os.environ.get("WAYLAND_DISPLAY"):
            return [MonitorInfo("Wayland primary", "wayland-default", 1920, 1080, primary=True)]
        return [MonitorInfo("Default display", "default", 1920, 1080, primary=True)]

    @staticmethod
    def primary_monitor(monitors: list[MonitorInfo]) -> MonitorInfo | None:
        for item in monitors:
            if item.primary:
                return item
        return monitors[0] if monitors else None

    @staticmethod
    def validate_monitor(monitor: MonitorInfo) -> bool:
        return monitor.width > 0 and monitor.height > 0 and bool(monitor.monitor_id)
