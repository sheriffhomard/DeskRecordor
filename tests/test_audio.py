from deskrecordor.core.audio import AudioManager, MicrophoneInfo


def test_default_microphone_falls_back_safely():
    manager = AudioManager()
    device = manager.default_microphone()
    assert isinstance(device, MicrophoneInfo)
    assert device.device_id


def test_test_microphone_handles_empty_list():
    manager = AudioManager()
    assert isinstance(manager.test_microphone(), bool)
