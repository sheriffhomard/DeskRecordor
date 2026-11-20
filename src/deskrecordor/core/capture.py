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
        if self.width <= 0 or self.height <= 0:
            return "sélection via le portail"
        return f"{self.width}x{self.height}"


class ScreenCapture:
    """Describe available displays and select the default monitor."""

    @staticmethod
    def uses_wayland_portal() -> bool:
        return bool(
            os.environ.get("WAYLAND_DISPLAY")
            and os.environ.get("GDK_BACKEND") != "x11"
        )

    @staticmethod
    def list_monitors() -> list[MonitorInfo]:
        if ScreenCapture.uses_wayland_portal():
            return [MonitorInfo("Écran via le portail Wayland", "wayland-portal", 0, 0, primary=True)]

        xrandr = shutil.which("xrandr")
        if xrandr:
            try:
                result = subprocess.run(
                    [xrandr],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=3,
                )
            except subprocess.TimeoutExpired:
                return [MonitorInfo("Display detection timed out", "default", 1920, 1080, primary=True)]
            lines = result.stdout.splitlines()
            monitors: list[MonitorInfo] = []
            for line in lines:
                if " connected" not in line:
                    continue
                tokens = line.split()
                if not tokens:
                    continue
                name = tokens[0]
                width = 1920
                height = 1080
                resolution = tokens[2] if len(tokens) >= 3 else "1920x1080"
                try:
                    width_text, height_text = resolution.split("x", 1)
                    width = int(width_text)
                    height = int(height_text)
                except ValueError:
                    pass
                monitors.append(
                    MonitorInfo(
                        name=name,
                        monitor_id=name,
                        width=width,
                        height=height,
                        primary="primary" in line or name == "eDP-1" or name == "HDMI-1",
                    )
                )
            if monitors:
                return monitors

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

    @staticmethod
    def ffmpeg_screen_input(monitor: MonitorInfo | None = None) -> list[str]:
        if ScreenCapture.uses_wayland_portal():
            raise RuntimeError("La capture Wayland doit être démarrée via le portail ScreenCast.")

        display = os.environ.get("DISPLAY") or ":0"
        selected = monitor or MonitorInfo("Default display", display, 1920, 1080, True)
        if os.environ.get("DISPLAY"):
            return [
                "-f",
                "x11grab",
                "-video_size",
                f"{selected.width}x{selected.height}",
                "-framerate",
                "30",
                "-draw_mouse",
                "0",
                "-i",
                f"{display}+0,0",
            ]
        return [
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={selected.width}x{selected.height}:d=30",
        ]
