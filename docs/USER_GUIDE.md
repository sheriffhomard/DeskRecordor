# User guide

## Current prototype

DeskRecordor is experimental. The application opens a basic GTK window with
monitor and microphone entries, a timer, and recording controls. This guide
does not imply a reliable recording workflow; inspect any generated file
before relying on it.

## Launch

From a source checkout:

```bash
PYTHONPATH=src python -m deskrecordor
```

After building and installing the Debian package, launch `deskrecordor` from
the application menu or a terminal in a graphical desktop session.

## Controls and files

- The monitor and microphone dropdowns show the current prototype's detected
  entries. Selection behavior is not verified end to end.
- **ENREGISTRER**, **PAUSE**, **REPRENDRE**, and **ARRÊTER** exercise the
  prototype recording controls.
- The default output directory is `~/Videos/DeskRecordor/`.
- The settings backend stores JSON under the user's XDG configuration path,
  but a settings window is not yet available.

The live audio meter is not connected to microphone samples. Wayland portal
capture and video finalization are incomplete. Do not use this prototype for
important recordings.
