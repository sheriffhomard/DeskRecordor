# Architecture

DeskRecordor is an experimental Python application with a `src/` package.
The current separation is:

| Area | Modules | Current responsibility |
|---|---|---|
| UI | `ui/main_window.py`, `ui/components.py` | Basic GTK 4 / Libadwaita window, selectors, timer and controls. The settings dialog is a placeholder. |
| Recording state | `core/state_manager.py`, `core/recorder.py` | State transitions and an early FFmpeg process wrapper. Recording lifecycle and output validation need work. |
| Screen / audio | `core/capture.py`, `core/audio.py` | X11 monitor discovery, PulseAudio-compatible source listing, and Wayland portal selection. |
| Portal adapters | `services/portal_service.py` | ScreenCast session, user consent, PipeWire remote FD, selected node, and session teardown. |
| Settings / utilities | `config/settings.py`, `utils/` | XDG JSON settings, file naming, and local logging helpers. |

## Current capture paths

- **X11:** FFmpeg is invoked with `x11grab` and a PulseAudio-compatible audio
  input. End-to-end capture, synchronization, monitor selection, and long-run
  stability are not verified.
- **Wayland:** the portal selects one monitor and returns a PipeWire stream.
  GStreamer converts that stream to raw video for FFmpeg encoding; the portal
  session is closed when capture stops. This path requires the portal backend,
  GStreamer PipeWire plugin, and a working PipeWire session.

The automated tests focus on state transitions, settings, and small helper
functions. They do not prove that the UI, microphone, portal, or recording
pipeline works on a desktop.
