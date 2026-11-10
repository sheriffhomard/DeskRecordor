from deskrecordor.config.settings import Settings
from deskrecordor.core.recorder import Recorder


def test_recorder_starts_in_ready_state(tmp_path):
    settings = Settings(output_dir=str(tmp_path), output_prefix="demo")
    recorder = Recorder(settings=settings)
    recorder.prepare()
    assert recorder.state.name == "READY"


def test_recorder_starts_recording(tmp_path):
    settings = Settings(output_dir=str(tmp_path), output_prefix="demo")
    recorder = Recorder(settings=settings)
    recorder.prepare()
    file_path = recorder.start_recording()
    assert file_path.parent == tmp_path
    assert file_path.name.endswith(".mp4")
    assert recorder.state.name == "RECORDING"
