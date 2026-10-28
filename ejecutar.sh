#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${YOGUI_VENV:-$PROJECT_DIR/.venv-portable}"
[[ "$VENV_DIR" == /* ]] || VENV_DIR="$PROJECT_DIR/$VENV_DIR"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo 'No existe el entorno local. Ejecutar primero ./instalar.sh' >&2
  exit 1
fi
if ! "$VENV_DIR/bin/python" -c 'import sys; assert sys.prefix != sys.base_prefix; import pip' >/dev/null 2>&1; then
  echo 'El venv está incompleto o no tiene pip. Ejecutar: bash instalar.sh --preparar-entorno' >&2
  exit 1
fi
if ! "$VENV_DIR/bin/python" -c 'import numpy,tkinter,OpenGL,pyopengltk,PIL,pyopencl' >/dev/null 2>&1; then
  echo 'Faltan requisitos dentro del venv. Ejecutar: bash instalar.sh' >&2
  exit 1
fi
cd -- "$PROJECT_DIR"
# No heredar un filtro CUDA de otro experimento. AMD/Intel no requieren CUDA.
exec env -u CUDA_VISIBLE_DEVICES "$VENV_DIR/bin/python" -m yoguicuentas.launcher "$@"
