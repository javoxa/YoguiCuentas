#!/usr/bin/env bash
set -euo pipefail
REPORT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPORT_DIR"
mkdir -p build
for PASS in 1 2 3; do
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build informe_tecnico_yoguicuentas_metal.tex > "build/pdflatex-$PASS.stdout.log"
done
cp build/informe_tecnico_yoguicuentas_metal.pdf informe_tecnico_yoguicuentas_metal.pdf
