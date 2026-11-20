from __future__ import annotations

from enum import Enum


class RecorderState(str, Enum):
    IDLE = "IDLE"
    READY = "READY"
    RECORDING = "RECORDING"
    PAUSED = "PAUSED"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class StateManager:
    """Manage legal transitions for the recorder."""

    ALLOWED_TRANSITIONS = {
        RecorderState.IDLE: {RecorderState.READY, RecorderState.ERROR},
        RecorderState.READY: {RecorderState.RECORDING, RecorderState.ERROR},
        RecorderState.RECORDING: {RecorderState.PAUSED, RecorderState.FINALIZING, RecorderState.ERROR},
        RecorderState.PAUSED: {RecorderState.RECORDING, RecorderState.FINALIZING, RecorderState.ERROR},
        RecorderState.FINALIZING: {RecorderState.COMPLETED, RecorderState.ERROR},
        RecorderState.COMPLETED: {RecorderState.READY, RecorderState.ERROR},
        RecorderState.ERROR: {RecorderState.IDLE, RecorderState.READY},
    }

    def __init__(self, initial_state: RecorderState = RecorderState.IDLE):
        self.state = initial_state
        self.last_error: str | None = None

    def transition_to(self, new_state: RecorderState) -> RecorderState:
        if self.state not in self.ALLOWED_TRANSITIONS:
            raise ValueError(f"Unknown source state: {self.state!r}")
        if new_state not in self.ALLOWED_TRANSITIONS[self.state]:
            current = self.state.value
            raise ValueError(f"Invalid transition: {current} -> {new_state.value}")
        self.state = new_state
        if new_state != RecorderState.ERROR:
            self.last_error = None
        return self.state

    def set_error(self, message: str) -> RecorderState:
        self.last_error = message
        self.state = RecorderState.ERROR
        return self.state

    @property
    def is_active(self) -> bool:
        return self.state in {RecorderState.READY, RecorderState.RECORDING, RecorderState.PAUSED, RecorderState.FINALIZING}

    @property
    def is_recording(self) -> bool:
        return self.state == RecorderState.RECORDING
