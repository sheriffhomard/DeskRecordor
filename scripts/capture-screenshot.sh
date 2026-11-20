#!/bin/sh
set -eu

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUTPUT=${1:-"$REPO_DIR/assets/screenshots/01-main-window.png"}
WINDOW_TITLE_PREFIX='DeskRecordor — Enregistreur'

for tool in xwininfo xwd ffmpeg; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Required screenshot tool not found: %s\n' "$tool" >&2
        exit 1
    fi
done

if [ -z "${DISPLAY:-}" ]; then
    printf 'No X11 DISPLAY is available. This script captures X11 windows only.\n' >&2
    exit 1
fi

WINDOW_ID=$(
    xwininfo -root -tree |
        awk -v prefix="\"$WINDOW_TITLE_PREFIX" 'index($0, prefix) { print $1; exit }'
)
if [ -z "$WINDOW_ID" ]; then
    printf 'DeskRecordor window not found in the X11 window list.\n' >&2
    printf 'Start the app with GDK_BACKEND=x11, or use an authenticated window-only capture on Wayland.\n' >&2
    exit 1
fi

case "$OUTPUT" in
    /*) ;;
    *) OUTPUT="$REPO_DIR/$OUTPUT" ;;
esac
case "$OUTPUT" in
    *.png) ;;
    *)
        printf 'Output path must end in .png: %s\n' "$OUTPUT" >&2
        exit 1
        ;;
esac

mkdir -p "$(dirname "$OUTPUT")"
TEMP_DIR=$(mktemp -d)
cleanup() {
    rm -f "$TEMP_DIR/window.xwd"
    rmdir "$TEMP_DIR"
}
trap cleanup EXIT HUP INT TERM

xwd -silent -id "$WINDOW_ID" -out "$TEMP_DIR/window.xwd"
ffmpeg -hide_banner -loglevel error -y -i "$TEMP_DIR/window.xwd" -frames:v 1 "$OUTPUT"
printf 'Captured DeskRecordor window to %s\n' "$OUTPUT"
