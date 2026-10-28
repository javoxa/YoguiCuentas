# YoguiCuentas en otra estación Linux, incluida iGPU

## Instalar la versión publicada en Debian/Devuan

Descargá `yoguicuentas_0.2.4_all.deb` desde [Releases](https://github.com/javoxa/YoguiCuentas/releases/latest). El archivo `.deb` se instala directamente; no hace falta descomprimirlo ni copiar el código fuente.

Si todavía no hay una Release, revisá [Actions](https://github.com/javoxa/YoguiCuentas/actions) y esperá a que termine correctamente **Build release packages** para `v0.2.4`.

En una terminal, entrá a la carpeta de descarga e instalalo:

```bash
cd ~/Descargas
sudo apt update
sudo apt install ./yoguicuentas_0.2.4_all.deb
```

Si tu sistema no tiene `sudo`, usá `su -` para entrar como administrador y ejecutá `apt install /home/USUARIO/Descargas/yoguicuentas_0.2.4_all.deb`, reemplazando `USUARIO` por tu nombre de usuario. APT instalará dependencias del sistema. La primera instalación también necesita conexión a Internet para preparar las dependencias Python desde PyPI.

Al terminar, abrí **YoguiCuentas** desde el menú o escribí `yoguicuentas` en una terminal. El lanzador selecciona OpenCL si encuentra una GPU compatible; si solo encuentra PoCL en CPU o no enumera una GPU, inicia el procesador CPU NumPy.

Para instalar el proyecto desde el código fuente en vez del `.deb`, seguí las instrucciones de esta página desde «Copiar el proyecto…».

Copiar el proyecto con código, escenarios, requisitos y scripts. No copiar los
entornos `.venv*`: se crean de nuevo en cada estación. Desde esa carpeta:

```bash
bash instalar.sh
bash ejecutar.sh
```

## Debian: dependencias del sistema

Entrar como administrador con `su -` y ejecutar, sin depender de sudo:

```bash
apt update
apt install python3-venv python3-tk
exit
```

Luego ejecutar los scripts con el usuario normal. También se requiere el driver
OpenGL y un runtime OpenCL/ICD del fabricante compatible con la placa y Debian.
Los paquetes exactos del runtime dependen del modelo Intel/AMD/NVIDIA; los
headers genéricos no proporcionan por sí solos acceso OpenCL a la GPU.
La aplicación no requiere CUDA. Requiere Python >=3.10, sesión X11/XWayland
con DISPLAY y OpenGL 3.2+ para shaders, buffers de textura y fences.
El soporte actual es Linux; otros sistemas necesitan adaptar el canvas.

## Transferencia automática y modo compatible

Ya no es obligatoria `cl_khr_gl_sharing`, ni `pyopencl.have_gl()==True`.

```bash
./ejecutar.sh --list-devices
./ejecutar.sh                         # GPU única: automática; varias: selector
./ejecutar.sh --device 0               # Índice de esta estación, no de la A2000
./ejecutar.sh --device 0 --transfer host
```

Los modos disponibles son:

- `--transfer auto` (predeterminado): con GL activo prueba contexto y VBO CL/GL
  compartidos. Si falla la compatibilidad o falta la extensión/soporte GL de
  PyOpenCL, conserva el dispositivo CL elegido y usa transferencia mediante RAM.
- `--transfer host`: fuerza OpenCL → memoria CPU → VBO OpenGL. No usa GLBuffer de
  OpenCL, acquire/release ni contexto compartido. Es la ruta para iGPU sin sharing.
- `--transfer shared`: exige la ruta compartida y reporta un error si no funciona.

El panel indica la ruta activa. El reporte de smoke indica además el motivo de
la ruta alternativa en modo auto. El selector ya no descarta GPUs por no tener
sharing. Las GPUs de cálculo y de render pueden ser diferentes en modo host.

La referencia de osciladores usa clEnqueueReadBuffer a host antes de visualizar.
Aquí se sigue ese principio en host, con lectura CL asíncrona, evento consultado
y subida al VBO tras comprobar un fence GL. El campo sigue calculándose con los
mismos kernels OpenCL. No se reemplaza por NumPy ni se cambian dt/materiales.
Hay una sola lectura pendiente y una publicación máxima de 30 Hz en esa ruta.
Se pueden omitir imágenes intermedias, no pasos físicos; al pausar/reiniciar o
alcanzar tf se publica el último campo aunque deba esperar al siguiente turno.
El repintado, cámara y Tkinter siguen activos. Una transferencia grande y su
subida GL aún consumen CPU/ancho de banda y pueden reducir rendimiento.

## Entorno virtual y pip

El instalador crea `.venv-portable` aislado y comprueba que su Python sea un venv.
Si falta pip intenta recuperarlo con ensurepip, sin borrar el entorno ni usar
get-pip.py. `ejecutar.sh` verifica venv, pip y los imports requeridos antes de abrir.

```bash
bash instalar.sh --preparar-entorno   # Sólo crear/reparar venv y pip
bash instalar.sh --comprobar         # Imports e inventario de dispositivos
```

Si ensurepip no está disponible, instalar python3-venv como root. Para un Python
no predeterminado, instalar su paquete versionado (por ejemplo python3.11-venv).
Instalar pip global no repara pip dentro del entorno. Si se copió un venv desde
otra máquina, usar una ruta nueva con YOGUI_VENV en vez de reutilizarlo.

```bash
YOGUI_PYTHON=/usr/bin/python3.11 ./instalar.sh
YOGUI_VENV=/ruta/entorno_nuevo ./instalar.sh
YOGUI_VENV=/ruta/entorno_nuevo ./ejecutar.sh --transfer host
```

YOGUI_VENV relativo se interpreta desde la carpeta del proyecto. El lanzador
elimina CUDA_VISIBLE_DEVICES sólo para ese proceso, evitando filtros heredados;
no altera permanentemente el sistema ni los filtros de otros runtimes.

## Instalación Python y GL compartido opcional

La instalación normal usa requisitos.txt y admite el wheel de PyOpenCL sin GL.
No necesita compilar PyOpenCL si hay wheel compatible. Guarda versiones resueltas
en `.venv-portable/requisitos-instalados.txt`; necesita conexión para descargar.
No instala ni cambia drivers o paquetes de sistema automáticamente.

Para habilitar GL compartido opcionalmente, instalar como root las dependencias
de compilación y ejecutar después el script como usuario normal:

```bash
# Como root, sólo si se va a compilar:
apt install python3-dev build-essential cmake ninja-build pkg-config ocl-icd-opencl-dev opencl-headers libgl1-mesa-dev libx11-dev
# Como usuario normal:
./instalar.sh --recompilar-opencl
```

Eso compila con PYOPENCL_ENABLE_GL=ON y build-constraints.txt (nanobind<3).
Habilitar GL en PyOpenCL no puede añadir una extensión que falte en el driver.
En tal caso usar host. Fuente de las opciones de build:
https://documen.tician.de/pyopencl/misc.html
https://pip.pypa.io/en/stable/user_guide/#build-constraints

## Diagnóstico y pruebas

```bash
./instalar.sh --comprobar
./ejecutar.sh --device 0 --transfer host --smoke-seconds 3 --output resultados/prueba_igpu
```

El inventario no abre GL ni garantiza interoperabilidad. La prueba con ventana
valida imagen, shaders, comparación del VBO con NumPy, pausa, reinicio y reemplazo
de escenario. Las pruebas completas se ejecutan con:

```bash
env -u CUDA_VISIBLE_DEVICES YOGUI_TEST_DEVICE=0 YOGUI_TEST_GL=1 .venv-portable/bin/python -m unittest discover -s tests -v
```

Las pruebas compartidas se omiten si falta esa capacidad; las pruebas host se
ejecutan sin exigirla. Incluyen auto con have_gl=False simulado.
En esta estación se probaron ambas rutas en la RTX A2000; no se dispone aquí de
la iGPU de la otra estación. Si falla también host, revisar OpenCL/ICD, acceso al
dispositivo, DISPLAY y versión de OpenGL, no sólo cl_khr_gl_sharing.

Consola sin ventana:

```bash
./ejecutar.sh --console --steps 1000
./ejecutar.sh --console --backend opencl --device 0 --steps 1000
```

Verificación adicional: se creó un venv limpio con el wheel PyOpenCL 2026.1.2
real (`have_gl=False`), sin compilación de GL. Se validaron en él las ventanas,
las cuatro vistas, capturas, cambio de grilla, fuentes/materiales, reinicio,
reproducción temporal y comparación numérica del VBO a través de host. La prueba
que exige intercambio compartido se omite cuando esa capacidad no está presente.

Si el driver permite crear contexto/GLBuffer pero luego devuelve INVALID_OPERATION
al adquirirlo, auto prueba ahora acquire/release al abrir y elige host si falla.
Si acquire falla más tarde, cambia a host conservando solución y último campo
visible. --transfer shared sigue siendo estricto; --transfer host evita la ruta
compartida por completo.

## Versión 0.2.0: CPU interactivo y escenas v2

`bash ejecutar.sh --device 1 --processor cpu` inicia cálculo NumPy en trabajador y render OpenGL, sin enumerar dispositivos OpenCL para iniciar CPU. La GPU sigue eligiéndose con el índice/selector habitual; cambiar procesador desde Cálculo reinicia y deja detenido. No se cambia silenciosamente a CPU ante un fallo de OpenCL. Las dependencias Python instaladas son las mismas; no se incorporó una biblioteca geométrica externa.

Las escenas JSON v2 y kernels CN se incluyen en el árbol; copiar también los nuevos módulos y `compute/kernels/crank_nicolson.cl`. Recrear el venv en otra estación. El núcleo sigue compilando con OpenCL C 1.1. Las funciones de texto/isotermas requieren el OpenGL de escritorio 3.2+ documentado. Las nuevas comprobaciones se ejecutaron en A2000, no certifican otra iGPU ni Wayland nativo. Ver PARIDAD_METAL.md para alcance, memoria y coste.


## Paquete instalable Debian/Devuan para laboratorios

En la estación de desarrollo, construir el paquete (requiere `dpkg-deb`):

```bash
bash construir_deb.sh
```

Se genera `dist/yoguicuentas_0.2.4_all.deb` (paquete de código independiente de arquitectura; los wheels se resuelven en la PC al instalar). Instalar en una PC Debian/Devuan con acceso a los repositorios APT y a PyPI:

```bash
su -
apt install ./yoguicuentas_0.2.4_all.deb
```

APT instala Python/Tk, PoCL, clinfo y los componentes Mesa/OpenGL usados en las PCs probadas. El postinst crea un entorno Python aislado en `/var/lib/yoguicuentas` e instala las dependencias una vez para todos los usuarios. La aplicación queda en el menú y también se puede abrir con `yoguicuentas`. No se copian venvs entre máquinas. El primer postinst necesita red para descargar wheels Python; APT se ocupa de las dependencias del sistema.

El lanzador `--processor auto` busca dispositivos OpenCL de tipo GPU. Si solo ve el dispositivo CPU de PoCL o no enumera ninguna GPU, abre la interfaz con `--processor cpu`. Se puede forzar `yoguicuentas --processor cpu` o `yoguicuentas --processor opencl`. Si la estación tiene una GPU NVIDIA/AMD que no aparece como OpenCL, instalar además el runtime/ICD provisto por el fabricante. Mesa/PoCL no sustituyen esos drivers de cálculo.

Cada usuario escribe exportaciones en `~/.local/share/yoguicuentas/resultados`; los escenarios de ejemplo del paquete son compartidos y de solo lectura. Desinstalar con `apt remove yoguicuentas`; `apt purge yoguicuentas` también retira el venv común.

### Descarga centralizada desde GitHub

Al publicar el código en un repositorio GitHub y subir una etiqueta `v` que
coincida con `pyproject.toml` (por ejemplo `v0.2.4`), GitHub Actions compila el
`.deb` Linux, la app Metal para macOS Apple Silicon y adjunta el informe técnico
PDF, y publica los tres archivos con `SHA256SUMS`. Las ediciones mantienen sus
versiones propias (OpenCL 0.2.4 y Metal 0.11.0 en esta instantánea). Así se puede distribuir un enlace a esa Release
en vez de llevar el paquete en un pendrive. La primera instalación Linux sigue
necesitando acceso a APT y PyPI. La app macOS todavía usa firma ad hoc y puede
requerir autorización manual en Gatekeeper; para una distribución sin ese aviso
hace falta firma Developer ID y notarización de Apple.
