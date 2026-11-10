from __future__ import annotations

from deskrecordor.config.settings import Settings
from deskrecordor.core.recorder import Recorder
from deskrecordor.core.state_manager import RecorderState
from deskrecordor.ui.components import TimerLabel, VUMeter


class MainWindow:
    """Main application window. This keeps GTK-specific code optional."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.load()
        self.recorder = Recorder(self.settings)
        self.vumeter = VUMeter()
        self.timer = TimerLabel()

    def run(self) -> int:
        return 0

    def start_recording(self):
        return self.recorder.start_recording(self.settings.output_dir)

    def pause_recording(self):
        if self.recorder.state == RecorderState.RECORDING:
            return self.recorder.pause_recording()
        return self.recorder.state

    def resume_recording(self):
        if self.recorder.state == RecorderState.PAUSED:
            return self.recorder.resume_recording()
        return self.recorder.state

    def stop_recording(self):
        if self.recorder.state in {RecorderState.RECORDING, RecorderState.PAUSED}:
            return self.recorder.stop_recording()
        return None
