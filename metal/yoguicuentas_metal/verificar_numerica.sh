#!/bin/bash
# Run from any directory on the Mac; preserve logs and exit status on failure.
set -euo pipefail
cd "$(dirname "$0")"
OUTPUT_DIR="${1:-verification/numerica-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUTPUT_DIR"
if [[ -e "$OUTPUT_DIR/swift-test.log" ]]; then
    echo "La carpeta ya contiene una corrida; elegí otra para conservar la evidencia." >&2; exit 2
fi
export CLANG_MODULE_CACHE_PATH=/private/tmp/yoguicuentas-clang-cache
export YOGUI_EVIDENCE_DIR="$PWD/$OUTPUT_DIR/artifacts"
if [[ "$OUTPUT_DIR" == /* ]]; then export YOGUI_EVIDENCE_DIR="$OUTPUT_DIR/artifacts"; fi
mkdir -p "$YOGUI_EVIDENCE_DIR"
TEST_FILTER=(--scratch-path /private/tmp/yoguicuentas-metal-build -Xswiftc -module-cache-path -Xswiftc /private/tmp/yoguicuentas-swift-cache)
if [[ "${2:-directed}" != full ]]; then
    TEST_FILTER+=(--filter 'NumericalVerificationTests|StationaryTests|CrankNicolsonTests|ConvergenceCriteriaTests|CampaignSupplementTests|ParityContractTests')
fi
find Sources Tests -type f -name '*.swift' -exec shasum -a 256 {} \; > "$OUTPUT_DIR/fuentes.sha256"
shasum -a 256 Package.swift crear_app.sh crear_icono.sh verificar_numerica.sh >> "$OUTPUT_DIR/fuentes.sha256"
{
    date -u
    sw_vers
    uname -m
    sysctl -n machdep.cpu.brand_string
    swift --version
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git rev-parse HEAD
        git status --short
    else
        printf 'Código fuente sin metadatos Git (por ejemplo, archivo ZIP).\n'
    fi
    system_profiler SPDisplaysDataType
    sysctl -n hw.memsize
    sysctl -n hw.logicalcpu
    pmset -g batt
    pmset -g custom
    uptime
    xcode-select -p
    xcodebuild -version
} > "$OUTPUT_DIR/equipo.txt" 2>&1
set +e
swift test "${TEST_FILTER[@]}" 2>&1 | tee "$OUTPUT_DIR/swift-test.log"
TEST_STATUS=${PIPESTATUS[0]}
set -e
printf 'case,backend,nodes,dx,dt,error\n' > "$OUTPUT_DIR/mediciones.csv"
sed -n 's/^NUMERIC,//p' "$OUTPUT_DIR/swift-test.log" >> "$OUTPUT_DIR/mediciones.csv"
if [[ -e "$YOGUI_EVIDENCE_DIR/campaign.jsonl" ]]; then
    cp "$YOGUI_EVIDENCE_DIR/campaign.jsonl" "$OUTPUT_DIR/campaign.jsonl"
else
    sed -n 's/^CAMPAIGN,//p' "$OUTPUT_DIR/swift-test.log" > "$OUTPUT_DIR/campaign.jsonl"
fi
printf '%s\n' "$TEST_STATUS" > "$OUTPUT_DIR/exit-status.txt"
printf '\nResultados: %s/%s\n' "$PWD" "$OUTPUT_DIR"
exit "$TEST_STATUS"
