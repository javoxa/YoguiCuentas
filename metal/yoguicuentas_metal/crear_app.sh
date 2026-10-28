#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$PROJECT_DIR/.build"
APP_PATH="${1:-$PROJECT_DIR/dist/YoguiCuentas Metal.app}"
BUILD_ID="$(date -u +%Y%m%d%H%M%S)"

swift build \
  --package-path "$PROJECT_DIR" \
  --scratch-path "$BUILD_DIR" \
  --configuration release \
  --product yoguicuentas_metal

EXECUTABLE="$BUILD_DIR/release/yoguicuentas_metal"
RESOURCE_BUNDLE="$BUILD_DIR/release/YoguiCuentasMetal_YoguiCuentasMetal.bundle"
if [[ ! -x "$EXECUTABLE" ]]; then
  echo "No se encontró el ejecutable compilado: $EXECUTABLE" >&2
  exit 1
fi
if [[ ! -d "$RESOURCE_BUNDLE" ]]; then
  echo "No se encontró el paquete de recursos: $RESOURCE_BUNDLE" >&2
  exit 1
fi

CONTENTS="$APP_PATH/Contents"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources"
bash "$PROJECT_DIR/crear_icono.sh"
cp "$PROJECT_DIR/Assets/AppIcon.icns" "$CONTENTS/Resources/AppIcon.icns"
cp "$PROJECT_DIR/Assets/AppIcon.png" "$CONTENTS/Resources/AppIcon.png"
cp "$PROJECT_DIR/../../LICENSE" "$CONTENTS/Resources/LICENSE"
cp "$PROJECT_DIR/../../NOTICE" "$CONTENTS/Resources/NOTICE"
cp "$EXECUTABLE" "$CONTENTS/MacOS/yoguicuentas_metal"
rm -rf "$CONTENTS/Resources/YoguiCuentasMetal_YoguiCuentasMetal.bundle"
ditto "$RESOURCE_BUNDLE" "$CONTENTS/Resources/YoguiCuentasMetal_YoguiCuentasMetal.bundle"

cat > "$CONTENTS/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>es</string>
  <key>CFBundleExecutable</key>
  <string>yoguicuentas_metal</string>
  <key>CFBundleIdentifier</key>
  <string>com.yoguicuentas.metal</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>YoguiCuentas Metal</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon.icns</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>${YOGUI_APP_VERSION:-0.11.0}</string>
  <key>CFBundleVersion</key>
  <string>$BUILD_ID</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
PLIST

/usr/bin/codesign --force --deep --sign - "$APP_PATH"
/usr/bin/codesign --verify --deep --strict "$APP_PATH"
/usr/bin/touch "$APP_PATH"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
if [[ -x "$LSREGISTER" ]]; then
  "$LSREGISTER" -f "$APP_PATH"
fi
echo "App compilada: $APP_PATH (build $BUILD_ID)"
if [[ "${YOGUI_SKIP_OPEN:-0}" != 1 ]]; then
  /usr/bin/open -n "$APP_PATH"
  echo "Abriendo la app recién compilada. Cerrá cualquier instancia anterior para evitar confundirla."
fi
