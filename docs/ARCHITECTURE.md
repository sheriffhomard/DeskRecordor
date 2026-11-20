# Architecture

DeskRecordor is an experimental Python application with a `src/` package.
The current separation is:

| Area | Modules | Current responsibility |
|---|---|---|
| UI | `ui/main_window.py`, `ui/components.py` | Basic GTK 4 / Libadwaita window, selectors, timer and controls. The settings dialog is a placeholder. |
| Recording state | `core/state_manager.py`, `core/recorder.py` | State transitions and an early FFmpeg process wrapper. Recording lifecycle and output validation need work. |
| Screen / audio | `core/capture.py`, `core/audio.py` | X11 monitor discovery and PulseAudio-compatible source listing. Wayland screen capture is not complete. |
| Portal adapters | `services/portal_service.py`, `services/pipewire_service.py` | Early portal and PipeWire helpers; they do not yet create a full ScreenCast session and consume its streams. |
| Settings / utilities | `config/settings.py`, `utils/` | XDG JSON settings, file naming, and local logging helpers. |

## Current capture paths

- **X11:** FFmpeg is invoked with `x11grab` and a PulseAudio-compatible audio
  input. End-to-end capture, synchronization, monitor selection, and long-run
  stability are not verified.
- **Wayland:** `portal_service.py` currently starts an incomplete portal call.
  It does not complete the required create-session, source-selection, start,
  PipeWire-node connection, and teardown lifecycle. The current build must not
  be described as providing working Wayland recording.

The automated tests focus on state transitions, settings, and small helper
functions. They do not prove that the UI, microphone, portal, or recording
pipeline works on a desktop.
