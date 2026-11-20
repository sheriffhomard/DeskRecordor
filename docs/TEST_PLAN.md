# Test plan and known validation

## Automated tests

Run `pytest` from the repository root. The current suite covers state
transitions, settings serialization, path generation, and basic audio and
portal helpers. At the documentation audit, all 13 tests passed on Python
3.13.

Automated tests do **not** validate GTK interaction, microphone samples,
X11/Wayland recording, audio/video synchronization, output validity, or
long-duration stability.

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
