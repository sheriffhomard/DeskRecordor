from deskrecordor.core.audio import AudioManager, MicrophoneInfo
from types import SimpleNamespace


def test_default_microphone_falls_back_safely():
    manager = AudioManager()
    device = manager.default_microphone()
    assert isinstance(device, MicrophoneInfo)
    assert device.device_id


def test_test_microphone_handles_empty_list():
    manager = AudioManager()
    assert isinstance(manager.test_microphone(), bool)


def test_microphone_list_excludes_playback_monitors_and_uses_default(monkeypatch):
    import deskrecordor.core.audio as audio_module

    monkeypatch.setattr(audio_module.shutil, "which", lambda _: "/usr/bin/pactl")

    def fake_run(command, **_kwargs):
        if command[1:3] == ["list", "short"]:
            return SimpleNamespace(
                stdout=(
                    "55 alsa_output.pci.monitor PipeWire format RUNNING\n"
                    "56 alsa_input.pci Microphone format SUSPENDED\n"
                )
            )
        return SimpleNamespace(stdout="alsa_input.pci\n")

    monkeypatch.setattr(audio_module.subprocess, "run", fake_run)
    manager = AudioManager()

    microphones = manager.list_microphones()
    assert [microphone.device_id for microphone in microphones] == ["alsa_input.pci"]
    assert manager.default_microphone().device_id == "alsa_input.pci"
