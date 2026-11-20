from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass
class MicrophoneInfo:
    name: str
    device_id: str
    available: bool = True
    sample_rate: int = 48000

    @property
    def label(self) -> str:
        return f"{self.name} ({self.device_id})" if self.device_id and self.device_id != self.name else self.name


class AudioVUMeter:
    def __init__(self) -> None:
        self.level = 0.0

    def update(self, value: float) -> float:
        self.level = max(0.0, min(float(value), 1.0))
        return self.level


class AudioManager:
    """List and validate microphone sources."""

    def __init__(self, source: str | None = None) -> None:
        self.source = source

    @staticmethod
    def _list_pulse_sources() -> list[MicrophoneInfo]:
        pactl = shutil.which("pactl")
        if not pactl:
            return [MicrophoneInfo("System default", "default", True, 48000)]

        result = subprocess.run(
            [pactl, "list", "short", "sources"],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = result.stdout.splitlines()
        devices: list[MicrophoneInfo] = []
        for line in lines:
            if not line.strip():
                continue
            pieces = line.split()
            if len(pieces) < 2:
                continue
            device_id = pieces[1]
            name = pieces[1]
            if len(pieces) >= 3:
                name = " ".join(pieces[1:])
            devices.append(MicrophoneInfo(name=name, device_id=device_id, sample_rate=48000))

        if not devices:
            return [MicrophoneInfo("System default", "default", True, 48000)]
        return devices

    def list_microphones(self) -> list[MicrophoneInfo]:
        return self._list_pulse_sources()

    def default_microphone(self) -> MicrophoneInfo:
        microphones = self.list_microphones()
        if not microphones:
            return MicrophoneInfo("System default", "default", False, 48000)
        if self.source:
            for item in microphones:
                if item.device_id == self.source or item.name == self.source:
                    return item
        return microphones[0]

    def test_microphone(self, device_id: str | None = None) -> bool:
        mics = self.list_microphones()
        if not mics:
            return False
        if device_id is None:
            return any(item.available for item in mics)
        return any(item.device_id == device_id and item.available for item in mics)

    def signal_level(self, value: float) -> float:
        return AudioVUMeter().update(value)
