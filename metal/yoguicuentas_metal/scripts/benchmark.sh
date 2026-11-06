#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUTPUT="${1:-verification/benchmark-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUTPUT"
if [[ -e "$OUTPUT/timings.csv" ]]; then echo "La corrida ya existe" >&2;exit 2;fi
find Sources -type f -name '*.swift' -exec shasum -a 256 {} \; > "$OUTPUT/fuentes.sha256"
shasum -a 256 scripts/campaign_benchmark.swift scripts/benchmark.sh >> "$OUTPUT/fuentes.sha256"
SOURCE=Sources/YoguiCuentasMetal
swiftc -O -module-cache-path /private/tmp/yoguicuentas-swift-cache \
 "$SOURCE/Scenario.swift" "$SOURCE/Scene.swift" "$SOURCE/ScenePartition.swift" \
 "$SOURCE/SceneBoundarySegments.swift" "$SOURCE/VisualFields.swift" \
 "$SOURCE/ThermalSolver.swift" "$SOURCE/CrankNicolson.swift" "$SOURCE/Convergence.swift" \
 scripts/campaign_benchmark.swift -o "$OUTPUT/benchmark"
"$OUTPUT/benchmark" "$OUTPUT"
