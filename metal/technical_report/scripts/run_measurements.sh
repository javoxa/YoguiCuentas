#!/usr/bin/env bash
set -euo pipefail
REPORT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$REPORT_DIR/source_snapshot"
mkdir -p "$REPORT_DIR/build" "$REPORT_DIR/data"
swiftc -O -module-cache-path /private/tmp/yoguicuentas-swift-cache \
  "$SOURCE_DIR/Scenario.swift" "$SOURCE_DIR/Scene.swift" \
  "$SOURCE_DIR/ScenePartition.swift" "$SOURCE_DIR/SceneBoundarySegments.swift" \
  "$SOURCE_DIR/VisualFields.swift" "$SOURCE_DIR/ThermalSolver.swift" \
  "$SOURCE_DIR/CrankNicolson.swift" "$REPORT_DIR/scripts/measure.swift" \
  -o "$REPORT_DIR/build/measure"
"$REPORT_DIR/build/measure" "$REPORT_DIR/data" "$REPORT_DIR/data/scenarios"
