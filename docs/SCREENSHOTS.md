# Screenshots and visual assets

This inventory records real application images only. No UI mockups or
generated images are substituted for application screenshots.

## Current inventory

| Asset | Purpose | Status | Resolution | README / landing-page use |
|---|---|---|---|---|
| `assets/screenshots/01-main-window.png` | Main window / future hero | Pending | — | Not currently embedded |
| `assets/screenshots/02-microphone-level.png` | Microphone input and level | Pending; the meter is not connected to captured audio | — | Not available |
| `assets/screenshots/03-recording-active.png` | Active capture controls | Pending; successful recording is not validated | — | Not available |
| `assets/screenshots/04-recording-paused.png` | Paused capture | Pending; pause and recording integrity are not validated | — | Not available |
| `assets/screenshots/05-settings.png` | Settings window | Not available; settings UI is not implemented | — | Not available |
| `assets/screenshots/06-recording-completed.png` | Saved output | Pending; finalization and output validity are not verified | — | Not available |
| `assets/landing-page/` | Web-optimized feature images | Pending authentic source captures | — | Future landing page only |

The GTK window was launched for a visual check, but no screenshot was retained:
the available desktop session did not provide a trustworthy idle-state capture
for publication. No resolution, capture state, or successful output file is
claimed here.

## Identity assets

- `assets/branding/logo.svg` is an original vector wordmark for DeskRecordor.
- Palette: slate `#202936`, indigo `#5267D8`, record accent `#E35B62`, and
  muted gray `#667085`.
- Typography: use the platform system sans-serif; Inter is an optional web
  equivalent, not an application dependency.
- The identity asset is a logo, not an application screenshot.

## Capture procedure

The helper `scripts/capture-screenshot.sh` captures only the DeskRecordor
window visible to the X11 server. It requires `xwininfo`, `xwd`, and `ffmpeg`.
It does not click controls, change application state, capture the whole
desktop, or redact image contents.

1. Run DeskRecordor in a clean Debian desktop session with non-personal demo
   data. For an X11 screenshot, launch with `GDK_BACKEND=x11`.
2. Bring the real app to the state to be documented using its normal UI.
   Capture a dynamic state only after that workflow has been tested and a
   valid output has been checked.
3. Capture the main window:

   ```bash
   ./scripts/capture-screenshot.sh
   ```

   Or specify a path:

   ```bash
   ./scripts/capture-screenshot.sh assets/screenshots/01-main-window.png
   ```

4. Inspect the resulting PNG manually. Confirm it shows only the intended
   application window and contains no personal paths, account names, or
   notifications before committing or sharing it.
5. Record the actual resolution and state in this inventory, then link it from
   the README only if the feature shown works as represented.

The helper intentionally fails when it cannot find the X11 application window.
It does not fall back to a full-screen capture. On Wayland, use the compositor's
authenticated, window-only screenshot flow and verify the resulting image;
portal screen recording and screenshot capture are distinct operations.

## Web derivatives

Keep the original PNG as the source. When there is a verified screenshot,
create a WebP derivative only for the landing page; do not retouch or alter the
displayed application state. Preserve the PNG and note the derivative's
dimensions and encoding command here.
