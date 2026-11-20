from __future__ import annotations

import os
import select
import shutil
import signal
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from deskrecordor.config.settings import Settings
from deskrecordor.core.audio import AudioManager
from deskrecordor.core.capture import ScreenCapture
from deskrecordor.core.encoder import VideoEncoder
from deskrecordor.core.state_manager import RecorderState, StateManager
from deskrecordor.services.portal_service import PortalCapture, PortalService
from deskrecordor.utils.file_manager import check_disk_space, ensure_unique_path, generate_output_filename
from deskrecordor.utils.logger import get_logger


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
        self._video_process: subprocess.Popen[str] | None = None
        self._stderr_thread: threading.Thread | None = None
        self._video_stderr_thread: threading.Thread | None = None
        self._stderr_tail: list[str] = []
        self._video_stderr_tail: list[str] = []
        self._wayland_capture: PortalCapture | None = None
        self._start_cancel_event = threading.Event()
        self._aborted = False
        self._lifecycle_lock = threading.RLock()
        self._logger = get_logger(__name__)

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

    def _build_ffmpeg_command(
        self,
        output_path: Path,
        portal_capture: PortalCapture | None = None,
    ) -> list[str]:
        monitor = self.selected_monitor()
        microphone = self.selected_microphone()
        if ScreenCapture.uses_wayland_portal():
            if portal_capture is None:
                raise RuntimeError("La session du portail Wayland n’a pas été créée.")
            screen_args = [
                "-f",
                "rawvideo",
                "-pixel_format",
                "yuv420p",
                "-video_size",
                f"{portal_capture.width}x{portal_capture.height}",
                "-framerate",
                "30",
                "-i",
                "pipe:0",
            ]
        else:
            screen_args = ScreenCapture.ffmpeg_screen_input(monitor)
        audio_source = microphone.device_id if microphone else "default"
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
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

    def _start_pipewire_video(self, capture: PortalCapture) -> int:
        command = [
            "gst-launch-1.0",
            "-q",
            "pipewiresrc",
            f"fd={capture.pipewire_fd}",
            f"path={capture.node_id}",
            "do-timestamp=true",
            "!",
            "videoconvert",
            "!",
            "videoscale",
            "!",
            "videorate",
            "!",
            f"video/x-raw,format=I420,width={capture.width},height={capture.height},framerate=30/1",
            "!",
            "fdsink",
            "fd=1",
        ]
        self._logger.debug("GStreamer command: %r", command)
        read_fd, write_fd = os.pipe()
        try:
            self._video_process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=write_fd,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                start_new_session=True,
                pass_fds=(capture.pipewire_fd, write_fd),
            )
        except OSError as exc:
            os.close(read_fd)
            os.close(write_fd)
            raise RuntimeError(f"Impossible de démarrer GStreamer : {exc}") from exc
        os.close(write_fd)
        self._video_stderr_tail = []
        self._video_stderr_thread = threading.Thread(
            target=self._read_process_errors,
            args=(self._video_process, "GStreamer", self._video_stderr_tail),
            name="deskrecordor-gstreamer-log",
            daemon=True,
        )
        self._video_stderr_thread.start()
        return read_fd

    def _wait_for_pipewire_video(self, video_input_fd: int, timeout: float = 10) -> None:
        deadline = time.monotonic() + timeout
        while True:
            if self._start_cancel_event.is_set():
                raise RuntimeError("Le démarrage de la capture a été interrompu.")

            process = self._video_process
            if process is None:
                raise RuntimeError("Le processus GStreamer est introuvable.")
            if process.poll() is not None:
                if self._video_stderr_thread is not None:
                    self._video_stderr_thread.join(timeout=0.2)
                detail = "\n".join(self._video_stderr_tail[-5:])
                raise RuntimeError(
                    detail or f"GStreamer s'est arrêté (code {process.returncode})."
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    "GStreamer n’a fourni aucune image vidéo dans le délai imparti."
                )
            readable, _, _ = select.select([video_input_fd], [], [], min(0.1, remaining))
            if readable and process.poll() is None:
                return
            if readable:
                if self._video_stderr_thread is not None:
                    self._video_stderr_thread.join(timeout=0.2)
                detail = "\n".join(self._video_stderr_tail[-5:])
                raise RuntimeError(
                    detail or f"GStreamer s'est arrêté (code {process.returncode})."
                )

    def start_recording_async(
        self,
        output_dir: str | os.PathLike[str] | None = None,
    ) -> Future[Path]:
        return self._executor.submit(self.start_recording, output_dir)

    def prepare(self) -> dict[str, Any]:
        monitors = ScreenCapture.list_monitors()
        if not monitors:
            raise RuntimeError("No monitors available for recording")
        default = ScreenCapture.primary_monitor(monitors) or monitors[0]
        self.settings.default_monitor = default.monitor_id
        self.state_manager.transition_to(RecorderState.READY)
        return {"monitors": monitors, "default": default}

    def start_recording(self, output_dir: str | os.PathLike[str] | None = None) -> Path:
        with self._lifecycle_lock:
            if self._aborted:
                raise RuntimeError("L’enregistreur a été arrêté.")
            self._start_cancel_event.clear()
            return self._start_recording(output_dir)

    def _start_recording(self, output_dir: str | os.PathLike[str] | None = None) -> Path:
        if self.state_manager.state not in {RecorderState.READY, RecorderState.IDLE}:
            raise ValueError(f"Cannot start recording while in {self.state_manager.state.value}")

        target_dir = Path(output_dir).expanduser() if output_dir else Path(self.settings.output_dir).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        if not self.selected_microphone().available:
            raise RuntimeError("Aucun microphone d’entrée disponible.")
        free_space = check_disk_space(target_dir)
        if free_space < 50 * 1024 * 1024:
            raise OSError("Not enough disk space available for recording")

        filename = generate_output_filename(prefix=self.settings.output_prefix, extension=f".{self.settings.final_format}")
        candidate = ensure_unique_path(target_dir / filename)
        self.current_file = candidate
        self.settings.last_recording_name = candidate.name
        self.settings.save()

        if not self._ffmpeg_available():
            raise RuntimeError("FFmpeg est introuvable. Installez le paquet ffmpeg puis réessayez.")
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            raise RuntimeError("Aucune session graphique détectée.")

        portal_capture = None
        video_input_fd = None
        self._logger.info("Starting capture to %s", candidate)
        try:
            if ScreenCapture.uses_wayland_portal():
                if shutil.which("gst-launch-1.0") is None:
                    raise RuntimeError(
                        "GStreamer est introuvable. Installez gstreamer1.0-tools "
                        "et gstreamer1.0-pipewire."
                    )
                self._logger.info("Requesting Wayland screen capture from the desktop portal")
                portal_capture = PortalService.start_capture(self._start_cancel_event)
                self._wayland_capture = portal_capture
                video_input_fd = self._start_pipewire_video(portal_capture)
                self._wait_for_pipewire_video(video_input_fd)

            command = self._build_ffmpeg_command(candidate, portal_capture)
            self._logger.debug("FFmpeg command: %r", command)
            self._capture_process = subprocess.Popen(
                command,
                stdin=video_input_fd if video_input_fd is not None else subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
            if video_input_fd is not None:
                os.close(video_input_fd)
                video_input_fd = None
        except Exception as exc:
            if video_input_fd is not None:
                os.close(video_input_fd)
            self._stop_video_process()
            self._release_portal_capture()
            self._capture_process = None
            self._logger.exception("Could not start capture pipeline")
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(f"Impossible de démarrer la capture : {exc}") from exc

        self._stderr_tail = []
        self._stderr_thread = threading.Thread(
            target=self._read_process_errors,
            args=(self._capture_process, "FFmpeg", self._stderr_tail),
            name="deskrecordor-ffmpeg-log",
            daemon=True,
        )
        self._stderr_thread.start()
        if (
            self._capture_process.poll() is not None
            or (self._video_process is not None and self._video_process.poll() is not None)
        ):
            process = self._capture_process
            self._stderr_thread.join(timeout=1)
            self._close_process_stderr(process)
            self._stop_video_process()
            self._release_portal_capture()
            self._capture_process = None
            detail = "\n".join((self._video_stderr_tail + self._stderr_tail)[-5:])
            message = detail or "Un processus de capture s'est arrêté immédiatement."
            self._logger.error("Capture process exited during startup: %s", message)
            raise RuntimeError(f"Le démarrage de la capture a échoué.\n{message}")

        self.state_manager.transition_to(RecorderState.RECORDING)
        return candidate

    def _read_process_errors(
        self,
        process: subprocess.Popen[str],
        source: str = "FFmpeg",
        tail: list[str] | None = None,
    ) -> None:
        if process.stderr is None:
            return
        tail = self._stderr_tail if tail is None else tail
        try:
            for line in process.stderr:
                message = line.rstrip()
                if message:
                    self._logger.warning("%s: %s", source, message)
                    tail.append(message)
                    del tail[:-20]
        except OSError:
            self._logger.exception("Failed while reading %s output", source)

    @staticmethod
    def _close_process_stderr(process: subprocess.Popen[str]) -> None:
        if process.stderr is not None:
            process.stderr.close()

    def _stop_video_process(self) -> None:
        process = self._video_process
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._logger.warning("GStreamer did not stop in time; sending SIGKILL")
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._logger.error("GStreamer ignored SIGKILL")
            except ProcessLookupError:
                pass
        if self._video_stderr_thread is not None:
            self._video_stderr_thread.join(timeout=1)
            self._video_stderr_thread = None
        if process is not None:
            self._close_process_stderr(process)
        self._video_process = None

    def _release_portal_capture(self) -> None:
        capture = self._wayland_capture
        self._wayland_capture = None
        if capture is None:
            return
        try:
            PortalService.close_capture(capture)
        except Exception:
            self._logger.exception("Could not close the Wayland portal session")

    def check_capture_health(self) -> bool:
        """Return whether FFmpeg is still capturing; record early exits as errors."""
        process = self._capture_process
        if process is None:
            if self.state in {RecorderState.RECORDING, RecorderState.PAUSED}:
                message = "Le processus FFmpeg de capture est introuvable."
                self.state_manager.set_error(message)
                self._logger.error(message)
            return False
        video_process = self._video_process
        if video_process is not None and video_process.poll() is not None:
            if self._video_stderr_thread is not None:
                self._video_stderr_thread.join(timeout=0.2)
                self._video_stderr_thread = None
            detail = "\n".join(self._video_stderr_tail[-5:])
            message = detail or f"GStreamer s'est arrêté (code {video_process.returncode})."
            self.state_manager.set_error(message)
            self._logger.error("Wayland video source exited unexpectedly: %s", message)
            self._stop_capture_process(graceful=False)
            return False
        if process.poll() is None:
            return self.state in {RecorderState.RECORDING, RecorderState.PAUSED}
        if self.state in {RecorderState.RECORDING, RecorderState.PAUSED}:
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=0.2)
                self._stderr_thread = None
            detail = "\n".join(self._stderr_tail[-5:])
            message = detail or f"FFmpeg s'est arrêté (code {process.returncode})."
            self.state_manager.set_error(message)
            self._logger.error("Capture process exited unexpectedly: %s", message)
            self._capture_process = None
            self._stop_video_process()
            self._release_portal_capture()
            return False
        return False

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
            with self._lifecycle_lock:
                self._stop_capture_process(graceful=True)

            file_path = self.current_file
            if self.encoder.validate_output(file_path):
                self.state_manager.transition_to(RecorderState.COMPLETED)
                self.settings.last_recording_name = file_path.name
                self.settings.save()
                self._logger.info("Capture finalized: %s (%d bytes)", file_path, file_path.stat().st_size)
                return file_path

            detail = "\n".join(self._stderr_tail[-5:])
            message = f"Le fichier vidéo est absent ou vide : {file_path}"
            if detail:
                message = f"{message}\n{detail}"
            self.state_manager.set_error(message)
            self._logger.error(message)
            return None
        except Exception as exc:  # pragma: no cover - defensive branch
            self.state_manager.set_error(str(exc))
            self._logger.exception("Recording finalization failed")
            return None

    def _stop_capture_process(self, graceful: bool) -> None:
        self._stop_video_process()
        process = self._capture_process
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGCONT)
                os.killpg(process.pid, signal.SIGINT if graceful else signal.SIGTERM)
                process.wait(timeout=5 if graceful else 1)
            except subprocess.TimeoutExpired:
                self._logger.warning("FFmpeg did not stop in time; sending SIGTERM")
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._logger.error("FFmpeg ignored SIGTERM; sending SIGKILL")
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=2)
            except ProcessLookupError:
                pass

        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=1)
            self._stderr_thread = None
        if process is not None:
            self._close_process_stderr(process)
        self._capture_process = None
        self._release_portal_capture()

    def abort(self) -> None:
        """Immediately terminate an active capture, without finalization."""
        self._logger.warning("User requested immediate recorder shutdown")
        self._aborted = True
        self._start_cancel_event.set()
        with self._lifecycle_lock:
            self._stop_video_process()
            process = self._capture_process
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._logger.error("FFmpeg process did not exit after SIGKILL")
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=0.5)
                self._stderr_thread = None
            if process is not None:
                self._close_process_stderr(process)
            self._capture_process = None
            self._release_portal_capture()
            self._executor.shutdown(wait=False, cancel_futures=True)

    def open_output_directory(self) -> bool:
        return self.state_manager.state in {RecorderState.IDLE, RecorderState.READY, RecorderState.COMPLETED, RecorderState.ERROR}

    def output_directory(self) -> Path:
        return Path(self.settings.output_dir).expanduser()
