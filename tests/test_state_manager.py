from deskrecordor.core.state_manager import RecorderState, StateManager


def test_valid_transition_sequence():
    manager = StateManager()
    assert manager.state == RecorderState.IDLE
    manager.transition_to(RecorderState.READY)
    manager.transition_to(RecorderState.RECORDING)
    manager.transition_to(RecorderState.PAUSED)
    manager.transition_to(RecorderState.RECORDING)
    manager.transition_to(RecorderState.FINALIZING)
    manager.transition_to(RecorderState.COMPLETED)


def test_invalid_transition_raises():
    manager = StateManager()
    try:
        manager.transition_to(RecorderState.RECORDING)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for invalid transition")


def test_error_transition():
    manager = StateManager(RecorderState.IDLE)
    manager.set_error("boom")
    assert manager.state == RecorderState.ERROR
