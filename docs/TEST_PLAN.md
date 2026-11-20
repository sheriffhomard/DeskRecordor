# Test plan and known validation

## Automated tests

Run `pytest` from the repository root. The current suite covers state
transitions, settings serialization, path generation, audio helpers, and
Wayland pipeline command construction with a mocked portal session. The
20 automated tests pass on Python 3.13 when PyGObject is available; the
ScreenCast D-Bus signature test is skipped otherwise.

Automated tests do **not** validate GTK interaction, a real D-Bus portal
session, PipeWire frames, microphone samples, X11/Wayland recording,
audio/video synchronization, output validity, or long-duration stability.

## Manual desktop checks still required

- Debian 12 and 13 separately.
- GNOME/X11 and XFCE/X11 screen and microphone capture.
- GNOME/Wayland and KDE/Wayland portal permission, stream setup, pause/resume,
  stop, and teardown.
- Real audio-level metering, output format validity, synchronization and
  playback.
- Recovery from microphone/display disconnection, portal denial, low disk
  space, and FFmpeg errors.
- Repeated start/stop and a documented long-duration run.

Do not mark an environment supported until those relevant checks have passed
and their environment and results are recorded.
