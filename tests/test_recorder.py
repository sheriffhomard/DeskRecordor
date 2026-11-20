import io
import os
import signal

import pytest

from deskrecordor.config.settings import Settings
from deskrecordor.core.audio import MicrophoneInfo
from deskrecordor.core.capture import MonitorInfo
from deskrecordor.core.recorder import Recorder
from deskrecordor.services.portal_service import PortalCapture, PortalService


class FakeCaptureProcess:
    def __init__(self, command):
        self.pid = 12345
        self.returncode = None
        self.stderr = io.StringIO()
        self.output_path = command[-1]

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = 0
        if self.output_path.endswith(".mp4"):
            with open(self.output_path, "wb") as recording:
                recording.write(b"test-recording")
        return self.returncode


def _recording_recorder(tmp_path, monkeypatch):
    settings = Settings(output_dir=str(tmp_path), output_prefix="demo")
    recorder = Recorder(settings=settings)
    recorder.prepare()
    monkeypatch.setattr(recorder, "_ffmpeg_available", lambda: True)
    monkeypatch.setattr(
        recorder,
        "selected_microphone",
        lambda: MicrophoneInfo("Test mic", "test-mic"),
    )
    monkeypatch.setattr(
        recorder,
        "selected_monitor",
        lambda: MonitorInfo("Test display", "test-display", 1920, 1080, True),
    )
    monkeypatch.setenv("DISPLAY", ":test")
    monkeypatch.setenv("GDK_BACKEND", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    return recorder


def test_recorder_starts_in_ready_state(tmp_path, monkeypatch):
    recorder = _recording_recorder(tmp_path, monkeypatch)
    assert recorder.state.name == "READY"


def test_recorder_starts_and_finalizes_recording(tmp_path, monkeypatch):
    recorder = _recording_recorder(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "deskrecordor.core.recorder.subprocess.Popen",
        lambda command, **_kwargs: FakeCaptureProcess(command),
    )
    monkeypatch.setattr("deskrecordor.core.recorder.os.killpg", lambda *_args: None)

    file_path = recorder.start_recording()
    assert file_path.parent == tmp_path
    assert file_path.name.endswith(".mp4")
    assert recorder.state.name == "RECORDING"

    finalization = recorder.stop_recording()
    assert finalization.result(timeout=3) == file_path
    assert recorder.state.name == "COMPLETED"
    recorder._executor.shutdown(wait=True)


def test_recorder_does_not_create_empty_file_when_ffmpeg_is_missing(tmp_path, monkeypatch):
    recorder = _recording_recorder(tmp_path, monkeypatch)
    monkeypatch.setattr(recorder, "_ffmpeg_available", lambda: False)

    with pytest.raises(RuntimeError, match="FFmpeg"):
        recorder.start_recording()

    assert list(tmp_path.iterdir()) == []


def test_wayland_capture_uses_portal_gstreamer_and_ffmpeg(tmp_path, monkeypatch):
    recorder = _recording_recorder(tmp_path, monkeypatch)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("GDK_BACKEND", "wayland")
    portal_fd = os.open(os.devnull, os.O_RDONLY)
    capture = PortalCapture(
        connection=None,
        session_handle="/org/freedesktop/portal/desktop/session/test",
        node_id=42,
        width=1280,
        height=720,
        pipewire_fd=portal_fd,
    )
    monkeypatch.setattr(
        PortalService,
        "start_capture",
        lambda _cancel_event: capture,
    )
    monkeypatch.setattr(
        PortalService,
        "close_capture",
        lambda session: os.close(session.pipewire_fd),
    )
    monkeypatch.setattr(
        "deskrecordor.core.recorder.shutil.which",
        lambda _program: "/usr/bin/gst-launch-1.0",
    )
    monkeypatch.setattr(recorder, "_wait_for_pipewire_video", lambda _fd: None)
    commands = []

    def fake_popen(command, **_kwargs):
        commands.append(command)
        return FakeCaptureProcess(command)

    monkeypatch.setattr("deskrecordor.core.recorder.subprocess.Popen", fake_popen)
    monkeypatch.setattr("deskrecordor.core.recorder.os.killpg", lambda *_args: None)
    output_path = recorder.start_recording()

    assert output_path.parent == tmp_path
    assert commands[0][0] == "gst-launch-1.0"
    assert "path=42" in commands[0]
    assert commands[0].index("videorate") < commands[0].index(
        "video/x-raw,format=I420,width=1280,height=720,framerate=30/1"
    )
    assert commands[1][0] == "ffmpeg"
    assert commands[1][commands[1].index("-video_size") + 1] == "1280x720"
    assert commands[1][commands[1].index("-i") + 1] == "pipe:0"
    assert recorder.stop_recording().result(timeout=3) == output_path
    recorder._executor.shutdown(wait=True)


def test_wayland_startup_reports_gstreamer_failure_before_first_frame(tmp_path):
    recorder = Recorder(settings=Settings(output_dir=str(tmp_path)))
    process = FakeCaptureProcess(["gst-launch-1.0"])
    process.returncode = 1
    recorder._video_process = process

    with pytest.raises(RuntimeError, match="GStreamer"):
        recorder._wait_for_pipewire_video(12)

    recorder._executor.shutdown(wait=True)


def test_capture_health_reports_ffmpeg_exit(tmp_path, monkeypatch):
    recorder = _recording_recorder(tmp_path, monkeypatch)
    process_holder = []

    def fake_popen(command, **_kwargs):
        process = FakeCaptureProcess(command)
        process_holder.append(process)
        return process

    monkeypatch.setattr("deskrecordor.core.recorder.subprocess.Popen", fake_popen)
    recorder.start_recording()
    process_holder[0].returncode = 1

    assert recorder.check_capture_health() is False
    assert recorder.state.name == "ERROR"
    assert "FFmpeg" in recorder.state_manager.last_error


def test_abort_uses_sigkill_to_stop_capture(tmp_path, monkeypatch):
    recorder = _recording_recorder(tmp_path, monkeypatch)
    process_holder = []

    def fake_popen(command, **_kwargs):
        process = FakeCaptureProcess(command)
        process_holder.append(process)
        return process

    monkeypatch.setattr("deskrecordor.core.recorder.subprocess.Popen", fake_popen)
    killed = []
    monkeypatch.setattr(
        "deskrecordor.core.recorder.os.killpg",
        lambda pid, sig: killed.append((pid, sig)),
    )
    monkeypatch.setattr("deskrecordor.core.recorder.os.kill", lambda *_args: None)

    recorder.start_recording()
    process = process_holder[0]
    recorder.pause_recording()
    assert recorder.check_capture_health() is True
    recorder.abort()

    assert killed == [(process.pid, signal.SIGKILL)]
    assert recorder._capture_process is None
