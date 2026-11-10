# DeskRecordor

DeskRecordor is an early-stage Python project for a native Linux screen and
microphone recorder, targeting Debian 12 and 13.

> **Development status:** this repository currently contains an initial
> scaffold. Screen and microphone capture, the GTK interface, and Debian
> packaging are not implemented yet; running the current entry point does not
> start a recording.

## Planned capabilities

- screen capture through XDG Desktop Portal and PipeWire on Wayland
- microphone capture and recording controls
- local MP4 recordings with persistent XDG settings
- a GTK 4 and Libadwaita desktop interface

## Development

Python 3.10 or later is required. To run the current test suite:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
pytest
```

The package uses a `src/` layout. To run its current entry point during
development:

```bash
PYTHONPATH=src python -m deskrecordor
```

See `docs/` for the project brief and initial architecture notes.
