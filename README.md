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
> unverified FFmpeg capture prototype. The Wayland portal flow, live microphone
> meter, settings UI, and reliable end-to-end recording are not complete.
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
| Local output and automatic filename | Default folder and unique timestamped names are implemented; successful video output is not guaranteed. |
| Settings window | Not implemented. JSON settings storage exists, but not all settings are exposed in the UI. |
| Wayland screen capture | Not implemented end to end. The current portal code does not complete the portal selection/start/stream lifecycle. |
| Debian package | Standard Debian packaging is present in this repository; a local build and APT dependency simulation have been verified on Debian 13. |

These are implementation notes, not a claim that every control works reliably.
See the [test plan](docs/TEST_PLAN.md) for the scope of automated tests.

## Compatibility

Debian 12 and 13 are **targets**, not fully validated support claims.

| Environment | Validation performed | Status |
|---|---|---|
| Debian 13, GNOME/X11 | GTK window opened; package built and APT install simulated. Recording was not validated. | Partial smoke test |
| Debian 13, GNOME/Wayland | No end-to-end portal capture test. | Not tested |
| Debian 13, KDE/Wayland | No end-to-end portal capture test. | Not tested |
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
sudo apt install ./dist/deskrecordor_0.2.0-2_all.deb
```

Remove it with:

```bash
sudo apt remove deskrecordor
```

The repository's GitHub Releases page contains an earlier `v0.2.0` package
that predates the standard Debian dependency metadata. Prefer building the
current package from source until a newer package is published.

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
3. Use **ENREGISTRER** to attempt a capture.
4. Use **PAUSE** / **REPRENDRE** or **ARRÊTER** to exercise the prototype controls.
5. The configured default output folder is `~/Videos/DeskRecordor/`.

The UI does not yet expose all settings or reliably report finalization
results. Check output files before relying on them.

## Technology stack

- Python 3.10+
- GTK 4, Libadwaita and PyGObject for the desktop window
- FFmpeg for the experimental capture pipeline
- PulseAudio-compatible input for the current audio path
- XDG Desktop Portal / PipeWire integration is incomplete; the project does not
  yet complete a Wayland screen-capture session
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
Wayland capture must use a supported desktop portal and user-granted
permissions; a complete portal recording flow is still pending.

## Roadmap

| Milestone | Focus | Status |
|---|---|---|
| 0.1 | Initial Python scaffold and state model | Released |
| 0.2 | GTK prototype, capture adapters and early Debian package | Released; experimental |
| 0.3 | Complete portal lifecycle, genuine audio metering, reliable finalization and recovery | Planned |
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
