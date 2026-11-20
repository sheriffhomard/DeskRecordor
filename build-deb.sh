#!/bin/sh
set -eu

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$REPO_DIR"

for tool in dpkg-buildpackage dpkg-parsechangelog sha256sum; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Required Debian packaging tool not found: %s\n' "$tool" >&2
        exit 1
    fi
done

VERSION=$(dpkg-parsechangelog --show-field Version)
PACKAGE="deskrecordor_${VERSION}_all.deb"
PARENT_DIR=$(dirname "$REPO_DIR")
BUILD_PACKAGE="$PARENT_DIR/$PACKAGE"
OUTPUT_DIR="$REPO_DIR/dist"

dpkg-buildpackage --build=binary --no-sign

if [ ! -f "$BUILD_PACKAGE" ]; then
    printf 'Expected package was not produced: %s\n' "$BUILD_PACKAGE" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
cp "$BUILD_PACKAGE" "$OUTPUT_DIR/$PACKAGE"
(
    cd "$OUTPUT_DIR"
    sha256sum "$PACKAGE" > "$PACKAGE.sha256"
)

printf 'Package: %s\n' "$OUTPUT_DIR/$PACKAGE"
printf 'Checksum: %s\n' "$OUTPUT_DIR/$PACKAGE.sha256"
printf 'Install with: sudo apt install ./%s\n' "${OUTPUT_DIR#"$REPO_DIR"/}/$PACKAGE"
