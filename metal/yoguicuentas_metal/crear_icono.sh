#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$PROJECT_DIR/Assets/AppIcon.png"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/yogui-icon.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT
ICONSET="$WORK_DIR/AppIcon.iconset"
mkdir -p "$ICONSET"

for SIZE in 16 32 128 256 512; do
  /usr/bin/sips -z "$SIZE" "$SIZE" "$SOURCE" --out "$ICONSET/icon_${SIZE}x${SIZE}.png" >/dev/null
  DOUBLE=$((SIZE * 2))
  /usr/bin/sips -z "$DOUBLE" "$DOUBLE" "$SOURCE" --out "$ICONSET/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done

/usr/bin/iconutil --convert icns "$ICONSET" --output "$PROJECT_DIR/Assets/AppIcon.icns"
echo "Icono generado: $PROJECT_DIR/Assets/AppIcon.icns"
