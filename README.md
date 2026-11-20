<p align="center">
  <img src="assets/branding/logo.svg" alt="DeskRecordor logo" width="360">
</p>

<p align="center">
  <strong>A small, local-first Linux screen and microphone recorder.</strong><br>
  Your screen. Your voice. Nothing complicated.
</p>

<p align="center">
  <a href="https://github.com/sheriffhomard/DeskRecordor/releases"><img src="https://img.shields.io/github/v/release/sheriffhomard/DeskRecordor?label=release" alt="Latest GitHub release"></a>
  <a href="https://github.com/sheriffhomard/DeskRecordor/blob/main/LICENSE"><img src="https://img.shields.io/github/license/sheriffhomard/DeskRecordor" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-%3E%3D3.10-3776AB?logo=python&logoColor=white" alt="Python 3.10 or later">
  <img src="https://img.shields.io/badge/status-experimental-orange" alt="Experimental development status">
  <a href="https://github.com/sheriffhomard/DeskRecordor/issues"><img src="https://img.shields.io/github/issues/sheriffhomard/DeskRecordor" alt="GitHub issues"></a>
</p>

> **Experimental software:** DeskRecordor has a basic GTK window and an
> experimental capture pipeline. Wayland capture now uses the desktop portal
> and PipeWire; real-world portal/backend combinations still need validation.
> The live microphone meter, settings UI, and reliable end-to-end recording
> are not complete.
> Do not use it for important recordings yet.

## Contents

- [What is DeskRecordor?](#what-is-deskrecordor)
- [Screenshots](#screenshots)
- [Features and implementation status](#features-and-implementation-status)
- [Compatibility](#compatibility)
- [Installation](#installation)
- [How to use DeskRecordor](#how-to-use-deskrecordor)
- [Technology stack](#technology-stack)
- [Privacy](#privacy)
- [Roadmap](#roadmap)
- [Documentation](#documentation)
- [Contributing and support](#contributing-and-support)
- [License](#license)

## What is DeskRecordor?

DeskRecordor is an early-stage Linux desktop recorder project. Its goal is to
make recording a screen and a microphone less complicated than using a
streaming or video-editing suite.

The project targets Debian desktops and is built in Python with GTK 4 and
Libadwaita. It is not a streaming, editing, webcam, or production-video tool.
The current application is a prototype, not yet a dependable recorder.

## Screenshots

No application screenshots are published yet. A window was opened for a visual
check, but the available session did not provide a trustworthy idle-state
capture suitable for documenting the product. No mockup or generated image is
presented as a real screenshot.

See [Screenshot inventory and capture procedure](docs/SCREENSHOTS.md) for what
is pending and how to capture the real application window.

## Features and implementation status

| Capability | Current status |
|---|---|
| GTK 4 / Libadwaita window | Basic window, source selectors, timer and recording controls are present. |
| Monitor selection | Basic monitor label detection; applying a selection to capture is not verified. |
| Microphone selection | PulseAudio-compatible sources can be listed; source selection and capture are not verified end to end. |
| Live microphone level | Not implemented; the current meter is not connected to captured audio. |
| Start, pause, resume and stop | Prototype controls are present; recording integrity and synchronization are not verified. |
| Startup countdown and elapsed timer | A 3-second countdown and capture-process health checks are present. They do not prove video validity. |
| Local output and automatic filename | Destination folder can be selected; unique timestamped names are implemented. Successful video output is not guaranteed. |
| Diagnostic logs and emergency quit | Rotating local logs and a forced FFmpeg termination control are available. |
| Settings window | Not implemented. JSON settings storage exists, but not all settings are exposed in the UI. |
| Wayland screen capture | Uses the ScreenCast portal for user consent and GStreamer/PipeWire for video. Desktop-specific validation is still required. |
| Debian package | Standard Debian packaging is present in this repository; a local build and APT dependency simulation have been verified on Debian 13. |

These are implementation notes, not a claim that every control works reliably.
See the [test plan](docs/TEST_PLAN.md) for the scope of automated tests.

## Compatibility

Debian 12 and 13 are **targets**, not fully validated support claims.

| Environment | Validation performed | Status |
|---|---|---|
| Debian 13, GNOME/X11 | GTK window opened; package built and APT install simulated. Recording was not validated. | Partial smoke test |
| Debian 13, GNOME/Wayland | Portal and PipeWire code paths are implemented; no real desktop end-to-end test yet. | Not tested |
| Debian 13, KDE/Wayland | Portal and PipeWire code paths are implemented; no real desktop end-to-end test yet. | Not tested |
| Debian 12 | No distribution test performed. | Not tested |

## Installation

### Build and install a Debian package

On Debian 12 or 13, install the packaging tools:

```bash
sudo apt install build-essential debhelper dh-python pybuild-plugin-pyproject \
  python3-all python3-setuptools python3-build python3-installer
```

Build the package and checksum from the repository root:

```bash
./build-deb.sh
```

Install the resulting package with APT so it can resolve runtime dependencies:

```bash
sudo apt install ./dist/deskrecordor_0.2.1-1_all.deb
```

Remove it with:

```bash
sudo apt remove deskrecordor
```

The GitHub Releases page contains tagged source and Debian package builds.

### Run from source

```bash
git clone https://github.com/sheriffhomard/DeskRecordor.git
cd DeskRecordor
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m deskrecordor
```

For a graphical session, the application also needs the system GTK 4,
Libadwaita and PyGObject libraries. The Debian package declares these runtime
dependencies.

## How to use DeskRecordor

The current prototype opens a window with monitor and microphone selectors and
recording controls. Its recording pipeline is experimental; these steps do
not imply that a valid video will be produced:

1. Launch `deskrecordor` from a graphical session.
2. Review the displayed monitor and microphone entries.
3. Choose a destination with **Choisir…** or keep `~/Videos/DeskRecordor/`.
4. Use **ENREGISTRER** to start the three-second countdown and attempt a capture.
5. Use **PAUSE** / **REPRENDRE** or **ARRÊTER** to exercise the prototype controls.
6. Open **JOURNAL** for local diagnostics, or **QUITTER / INTERROMPRE** to force-stop the capture pipeline.

The UI does not yet expose all settings or reliably report finalization
results. Check output files before relying on them.

## Technology stack

- Python 3.10+
- GTK 4, Libadwaita and PyGObject for the desktop window
- FFmpeg for the experimental capture pipeline
- PulseAudio-compatible input for the current audio path
- Wayland capture requests explicit user consent through XDG Desktop Portal;
  recordings remain local and use GStreamer/PipeWire for screen video
- Debian `debhelper` and `pybuild` for packaging

See [Architecture](docs/ARCHITECTURE.md) for component boundaries and current
limitations.

## Privacy

The application source contains no account, cloud upload, or telemetry
implementation. Recordings are intended to be saved locally under the
configured output directory (by default `~/Videos/DeskRecordor/`), and settings
are stored under the user's XDG configuration directory.

This is a repository-level code review, not a network or dependency audit.
DeskRecordor interacts with local desktop, audio, and capture services; their
behavior and the behavior of system dependencies are outside that statement.
Wayland capture requires a supported desktop portal and user-granted
permissions.

## Roadmap

| Milestone | Focus | Status |
|---|---|---|
| 0.1 | Initial Python scaffold and state model | Released |
| 0.2 | GTK prototype, capture adapters and early Debian package | Released; experimental |
| 0.3 | Validate the portal lifecycle, add genuine audio metering, reliable finalization and recovery | In progress |
| 1.0 | Tested Debian desktop support and dependable recording workflow | Planned |

See the [detailed roadmap](docs/ROADMAP.md).

## Documentation

- [Project brief](docs/CAHIER_DES_CHARGES.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [User guide](docs/USER_GUIDE.md)
- [Test plan](docs/TEST_PLAN.md)
- [Roadmap](docs/ROADMAP.md)
- [Screenshots and visual assets](docs/SCREENSHOTS.md)
- [Landing-page copy](docs/LANDING_PAGE_CONTENT.md)
- [Changelog](CHANGELOG.md)
- [Security policy](SECURITY.md)

## Contributing and support

Bug reports and feature requests belong in [GitHub Issues](https://github.com/sheriffhomard/DeskRecordor/issues).
Please include your Debian version, desktop environment, session type
(Wayland/X11), and relevant logs, while removing personal information.
See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a change.

## License

DeskRecordor is distributed under the [MIT License](LICENSE).
