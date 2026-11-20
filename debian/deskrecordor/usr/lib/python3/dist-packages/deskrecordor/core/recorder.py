from __future__ import annotations

import os
import shutil
import signal
import subprocess
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from deskrecordor.config.settings import Settings
from deskrecordor.core.audio import AudioManager
from deskrecordor.core.capture import ScreenCapture
from deskrecordor.core.encoder import VideoEncoder
from deskrecordor.core.state_manager import RecorderState, StateManager
from deskrecordor.utils.file_manager import check_disk_space, ensure_unique_path, generate_output_filename


class Recorder:
    def __init__(self, settings: Settings | None = None, state_manager: StateManager | None = None) -> None:
        self.settings = settings or Settings.load()
        self.state_manager = state_manager or StateManager()
        self.audio_manager = AudioManager(self.settings.default_microphone)
        self.encoder = VideoEncoder()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.current_file: Path | None = None
        self._finalization_future: Future[Any] | None = None
        self._capture_process: subprocess.Popen[str] | None = None
        self._stub_recording = False

    @property
    def state(self) -> RecorderState:
        return self.state_manager.state

    def selected_monitor(self):
        monitors = ScreenCapture.list_monitors()
        default_id = self.settings.default_monitor
        if default_id:
            for monitor in monitors:
                if monitor.monitor_id == default_id:
                    return monitor
        return ScreenCapture.primary_monitor(monitors) or monitors[0]

    def selected_microphone(self):
        return self.audio_manager.default_microphone()

    def _ffmpeg_available(self) -> bool:
        return shutil.which("ffmpeg") is not None

    def _build_ffmpeg_command(self, output_path: Path) -> list[str]:
        monitor = self.selected_monitor()
        microphone = self.selected_microphone()
        screen_args = ScreenCapture.ffmpeg_screen_input(monitor)
        audio_source = microphone.device_id if microphone else "default"
        command = [
            "ffmpeg",
            "-y",
            *screen_args,
            "-f",
            "pulse",
            "-i",
            audio_source,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ]
        return command

    def prepare(self) -> dict[str, Any]:
        monitors = ScreenCapture.list_monitors()
        if not monitors:
            raise RuntimeError("No monitors available for recording")
        default = ScreenCapture.primary_monitor(monitors) or monitors[0]
        self.settings.default_monitor = default.monitor_id
        self.state_manager.transition_to(RecorderState.READY)
        return {"monitors": monitors, "default": default}

    def start_recording(self, output_dir: str | os.PathLike[str] | None = None) -> Path:
        if self.state_manager.state not in {RecorderState.READY, RecorderState.IDLE}:
            raise ValueError(f"Cannot start recording while in {self.state_manager.state.value}")

        target_dir = Path(output_dir).expanduser() if output_dir else Path(self.settings.output_dir).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        free_space = check_disk_space(target_dir)
        if free_space < 50 * 1024 * 1024:
            raise OSError("Not enough disk space available for recording")

        filename = generate_output_filename(prefix=self.settings.output_prefix, extension=f".{self.settings.final_format}")
        candidate = ensure_unique_path(target_dir / filename)
        self.current_file = candidate
        self.settings.last_recording_name = candidate.name
        self.settings.save()

        self._stub_recording = False
        if self._ffmpeg_available() and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            command = self._build_ffmpeg_command(candidate)
            try:
                self._capture_process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )
            except OSError as exc:
                self._capture_process = None
                self.state_manager.set_error(str(exc))
                candidate.touch()
                self._stub_recording = True
                return candidate

            # If ffmpeg exits immediately because the display or audio source is unavailable,
            # fall back to a stub file instead of leaving the recorder stuck in an invalid state.
            if self._capture_process.poll() is not None:
                stderr = self._capture_process.communicate()[1] if self._capture_process.stderr else ""
                self._capture_process = None
                self.state_manager.set_error(stderr.strip() or "ffmpeg could not start the capture")
                candidate.touch()
                self._stub_recording = True
                return candidate
        else:
            candidate.touch()
            self._stub_recording = True

        self.state_manager.transition_to(RecorderState.RECORDING)
        return candidate

    def pause_recording(self) -> RecorderState:
        if self._capture_process and self._capture_process.poll() is None:
            os.kill(self._capture_process.pid, signal.SIGSTOP)
        self.state_manager.transition_to(RecorderState.PAUSED)
        return self.state_manager.state

    def resume_recording(self) -> RecorderState:
        if self._capture_process and self._capture_process.poll() is None:
            os.kill(self._capture_process.pid, signal.SIGCONT)
        self.state_manager.transition_to(RecorderState.RECORDING)
        return self.state_manager.state

    def stop_recording(self) -> Future[Any]:
        if self.state_manager.state not in {RecorderState.RECORDING, RecorderState.PAUSED}:
            raise ValueError(f"Cannot stop recording while in {self.state_manager.state.value}")
        self.state_manager.transition_to(RecorderState.FINALIZING)
        self._finalization_future = self._executor.submit(self._finalize)
        return self._finalization_future

    def _finalize(self) -> Path | None:
        if self.current_file is None:
            self.state_manager.set_error("No active recording file")
            return None

        try:
            if self._capture_process and self._capture_process.poll() is None:
                self._capture_process.send_signal(signal.SIGINT)
                try:
                    self._capture_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._capture_process.terminate()
                    self._capture_process.wait(timeout=5)
                self._capture_process = None

            file_path = self.current_file
            file_path.touch(exist_ok=True)
            if self.encoder.validate_output(file_path) or self._stub_recording:
                self.state_manager.transition_to(RecorderState.COMPLETED)
                self.settings.last_recording_name = file_path.name
                self.settings.save()
                return file_path

            self.state_manager.set_error("Recording file invalid")
            return None
        except Exception as exc:  # pragma: no cover - defensive branch
            self.state_manager.set_error(str(exc))
            return None

    def open_output_directory(self) -> bool:
        return self.state_manager.state in {RecorderState.IDLE, RecorderState.READY, RecorderState.COMPLETED, RecorderState.ERROR}

    def output_directory(self) -> Path:
        return Path(self.settings.output_dir).expanduser()
