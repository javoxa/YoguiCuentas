#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$PROJECT_DIR/pyproject.toml")"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT
ROOT="$BUILD_DIR/yoguicuentas_${VERSION}_all"
install -d "$ROOT/DEBIAN" "$ROOT/opt/yoguicuentas" "$ROOT/usr/share/applications" "$ROOT/usr/share/doc/yoguicuentas"
cp "$PROJECT_DIR/packaging/debian/control" "$ROOT/DEBIAN/control"
sed -i "s/^Version:.*/Version: $VERSION/" "$ROOT/DEBIAN/control"
install -m 0755 "$PROJECT_DIR/packaging/debian/postinst" "$ROOT/DEBIAN/postinst"
install -m 0755 "$PROJECT_DIR/packaging/debian/prerm" "$ROOT/DEBIAN/prerm"
install -m 0755 "$PROJECT_DIR/packaging/debian/postrm" "$ROOT/DEBIAN/postrm"
install -d "$ROOT/opt/yoguicuentas/packaging/debian"
install -m 0755 "$PROJECT_DIR/packaging/debian/yoguicuentas-launcher" "$ROOT/opt/yoguicuentas/packaging/debian/yoguicuentas-launcher"
cp -a "$PROJECT_DIR/yoguicuentas" "$ROOT/opt/yoguicuentas/"
cp -a "$PROJECT_DIR/scenarios" "$ROOT/opt/yoguicuentas/"
cp "$PROJECT_DIR/instalar.sh" "$PROJECT_DIR/ejecutar.sh" "$PROJECT_DIR/requisitos.txt" "$PROJECT_DIR/pyproject.toml" "$PROJECT_DIR/build-constraints.txt" "$ROOT/opt/yoguicuentas/"
cp "$PROJECT_DIR/README.md" "$PROJECT_DIR/PORTABILIDAD.md" "$PROJECT_DIR/LICENSE" "$PROJECT_DIR/NOTICE" "$ROOT/usr/share/doc/yoguicuentas/"
install -m 0644 "$PROJECT_DIR/packaging/debian/yoguicuentas.desktop" "$ROOT/usr/share/applications/yoguicuentas.desktop"
find "$ROOT/opt/yoguicuentas" -type d -name __pycache__ -prune -exec rm -rf {} +
install -d "$PROJECT_DIR/dist"
dpkg-deb --root-owner-group --build "$ROOT" "$PROJECT_DIR/dist/yoguicuentas_${VERSION}_all.deb"
echo "Paquete creado: dist/yoguicuentas_${VERSION}_all.deb"
