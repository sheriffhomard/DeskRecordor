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

- Drag the header bar to move the window. Its buttons minimize, maximize, or
  restore the previous size. **?** opens the built-in documentation and legal
  notice; **Guide** opens the onboarding steps.
- On Wayland, choose the monitor in the system portal dialog that appears
  after the countdown. On X11, the monitor dropdown shows the detected entry.
  The microphone dropdown shows detected input sources.
- Choose the destination with **Choisir…**. The selected folder and next
  proposed filename are shown in the window. The default is
  `~/Videos/DeskRecordor/`.
- **ENREGISTRER** shows a three-second startup countdown. On Wayland, approve
  screen sharing in the portal dialog; the timer starts after the capture
  pipeline launches. The health check reports if capture stops early.
- **PAUSE**, **REPRENDRE**, and **ARRÊTER** control the experimental capture
  process. Finalization status and errors are shown in the window.
- **JOURNAL** opens the local diagnostic log. The log file is
  `~/.local/state/deskrecordor/deskrecordor.log` (or under `$XDG_STATE_HOME`
  when configured).
- **QUITTER / INTERROMPRE** forcibly terminates the active capture processes
  before closing. An interrupted recording may be incomplete or unplayable.
- The settings backend stores JSON under the user's XDG configuration path,
  but a settings window is not yet available.

The live audio meter is not connected to microphone samples. Portal availability
depends on the desktop environment, and end-to-end capture has not yet been
validated on all supported desktops. Do not use this prototype for important
recordings.

The **?** documentation window displays the application version and this
notice: DeskRecordor is provided “as is”; the user is responsible for its use,
required permissions, consent, and legal compliance. The developer disclaims
responsibility for uses, losses, or damages to the extent permitted by law.
