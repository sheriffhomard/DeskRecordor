# Installation

## Debian package

Download a release package and install it with APT, which resolves the
application's Debian dependencies:

```bash
sudo apt install ./deskrecordor_VERSION_all.deb
```

The package declares Python 3, PyGObject, GTK 4, Libadwaita, FFmpeg, GStreamer
with its PipeWire plugin, and xdg-desktop-portal as dependencies. For Wayland
capture, the desktop session must also provide an appropriate portal backend
and a working PipeWire/PulseAudio service.

## Build from source

Install the build tools on Debian 12 or 13:

```bash
sudo apt install build-essential debhelper dh-python pybuild-plugin-pyproject \
  python3-all python3-setuptools python3-build python3-installer
```

Then run `./build-deb.sh`. The resulting `.deb` and its SHA-256 checksum are
written to `dist/`. Install the local package with:

```bash
sudo apt install ./dist/deskrecordor_0.2.1-1_all.deb
```

APT installs dependencies from the configured Debian repositories. Installing
a local `.deb` with `dpkg -i` alone does not resolve dependencies.

## Development

Python 3.10+ is required. Create a virtual environment, install
`requirements.txt`, and run the test suite with `pytest`.
