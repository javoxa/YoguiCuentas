#!/usr/bin/env bash
# Entorno por estación: no copiar un venv entre máquinas.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${YOGUI_VENV:-$PROJECT_DIR/.venv-portable}"
[[ "$VENV_DIR" == /* ]] || VENV_DIR="$PROJECT_DIR/$VENV_DIR"
PYTHON_BIN="${YOGUI_PYTHON:-python3}"
usage() {
  cat <<'HELP'
Uso: ./instalar.sh [--comprobar | --preparar-entorno | --recompilar-opencl | --ayuda]
Crea .venv-portable e instala requisitos. --recompilar-opencl habilita GL opcional.
No modifica instalaciones Python globales ni instala/cambia drivers.
YOGUI_PYTHON=/ruta/python3 elige Python (>=3.10).
YOGUI_VENV=/ruta/entorno cambia la ubicación del entorno.

Dependencias del sistema (ejemplo Debian/Ubuntu, instalar una vez):
 Como root (su -): apt install python3-venv python3-tk
 Para compilar GL opcional: python3-dev build-essential cmake ninja-build pkg-config ocl-icd-opencl-dev opencl-headers libgl1-mesa-dev libx11-dev
Además hace falta el runtime/ICD OpenCL del fabricante de la GPU y su driver GL.
Ver PORTABILIDAD.md para diagnóstico y estaciones con varias GPUs.
HELP
}
MODE="${1:-}"
case "$MODE" in
  --ayuda|--help|-h) usage; exit 0 ;;
  --comprobar)
    [[ -x "$VENV_DIR/bin/python" ]] || { echo 'No existe el entorno. Ejecutar ./instalar.sh'; exit 1; }
    cd -- "$PROJECT_DIR"
    exec env -u CUDA_VISIBLE_DEVICES "$VENV_DIR/bin/python" -m yoguicuentas.portability
    ;;
  ''|--preparar-entorno|--recompilar-opencl) ;;
  *) usage; exit 2 ;;
esac
[[ "$(uname -s)" == Linux ]] || { echo 'Este instalador está preparado para estaciones Linux.'; exit 1; }
command -v "$PYTHON_BIN" >/dev/null || { echo 'No se encontró Python. Ver --ayuda.'; exit 1; }
"$PYTHON_BIN" -c 'import sys,tkinter; assert sys.version_info >= (3,10), "Se requiere Python >=3.10"' || {
  echo 'Falta Python compatible o Tkinter. Ver ./instalar.sh --ayuda.'; exit 1;
}
if [[ ! -d "$VENV_DIR" ]]; then
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
    echo 'No se pudo crear el entorno. En Debian instalar python3-venv (o pythonX.Y-venv del Python elegido) y reintentar.' >&2
    exit 1
  fi
fi
[[ -x "$VENV_DIR/bin/python" ]] || { echo "La carpeta $VENV_DIR no es un entorno Python válido."; exit 1; }
cd -- "$PROJECT_DIR"
PY="$VENV_DIR/bin/python"
# No ejecutar bootstrap ni instalaciones sobre Python global por accidente.
"$PY" -c 'import sys; assert sys.prefix != sys.base_prefix, "La ruta elegida no es un entorno virtual"'
if ! "$PY" -m pip --version >/dev/null 2>&1; then
  echo 'El entorno existe, pero no tiene pip. Intentando recuperarlo con ensurepip…'
  if ! "$PY" -m ensurepip --upgrade; then
    echo 'No se pudo recuperar pip. En Debian, instalar python3-venv o pythonX.Y-venv para la versión elegida.' >&2
    echo "Después repetir: $0 --preparar-entorno" >&2
    echo 'No es necesario borrar el entorno ni instalar paquetes Python globales.' >&2
    exit 1
  fi
fi
"$PY" -m pip --version
if [[ "$MODE" == --preparar-entorno ]]; then
  echo 'Entorno y pip preparados. Ejecutar ./instalar.sh para instalar requisitos.'
  exit 0
fi
"$PY" -m pip install --upgrade 'pip>=25.3'
"$PY" -m pip install -r "$PROJECT_DIR/requisitos.txt"
if [[ "$MODE" == --recompilar-opencl ]]; then
  command -v c++ >/dev/null || { echo 'Falta compilador C++. Ver --ayuda.'; exit 1; }
  printf '#include <CL/cl.h>\n#include <GL/gl.h>\n' | c++ -x c++ -E - >/dev/null 2>&1 || {
    echo 'Faltan headers OpenCL/OpenGL para GL opcional. Ver --ayuda.'; exit 1;
  }
  export PYOPENCL_ENABLE_GL=ON
  export PIP_BUILD_CONSTRAINT="$PROJECT_DIR/build-constraints.txt"
  export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
  "$PY" -m pip install --no-cache-dir --force-reinstall --no-deps --no-binary=pyopencl pyopencl==2026.1.2
fi
"$PY" -m pip install --no-deps -e "$PROJECT_DIR"
"$PY" -m pip check
"$PY" -m pip freeze > "$VENV_DIR/requisitos-instalados.txt"
# La compilación debe funcionar aun sin un monitor conectado; GL real se prueba al abrir.
"$PY" -c 'import tkinter,OpenGL,pyopengltk,pyopencl'
echo 'Entorno listo. Inventario de dispositivos (no crea todavía contexto GL):'
if ! env -u CUDA_VISIBLE_DEVICES "$PY" -m yoguicuentas.portability; then
  echo 'Dependencias instaladas; resolver los avisos de driver/ICD antes de abrir la vista.'
fi
echo 'Ejecutar: ./ejecutar.sh'
