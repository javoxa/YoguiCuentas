# YoguiCuentas

Simulador educativo de conducción térmica bidimensional para explorar temperatura,
flujo de calor, materiales, fuentes y condiciones de borde con recursos de hardware
moderados. El cálculo usa una **grilla cartesiana estructurada** y la visualización
interpola sus valores para presentar mapas y superficies animadas.

Versiones beta desde fuentes: **Linux/OpenCL 0.2.5** y
**macOS/Metal 0.12.0**, con numeración independiente. Español por defecto y menú
**Idioma → Español / English**. Licencia [Apache 2.0](LICENSE).

## Instalar en Debian / Devuan mediante git clone

Se requiere Python 3.10 o posterior, conexión a Internet durante la instalación
y un controlador OpenGL compatible. El cálculo puede ejecutarse en CPU sin una
GPU dedicada; la interfaz gráfica sigue necesitando OpenGL.

Instalar las dependencias del sistema una vez, como administrador:

```bash
sudo apt update
sudo apt install git python3-venv python3-tk pocl-opencl-icd clinfo mesa-utils libgl1-mesa-dri libglx-mesa0
```

Si tu sistema no tiene `sudo`, usar `su -` para ejecutar esas dos órdenes sin
`sudo` y luego volver a la cuenta normal. Como usuario normal:

```bash
git clone https://github.com/javoxa/YoguiCuentas.git Yogui_Cuentas
cd Yogui_Cuentas
bash instalar.sh
bash ejecutar.sh
```

El instalador crea `.venv-portable` dentro de esta carpeta. Cada computadora debe
crear su propio entorno. El lanzador selecciona una GPU OpenCL disponible y, si
no la encuentra, utiliza CPU. Para forzar CPU, como en los equipos del laboratorio:

```bash
bash ejecutar.sh --processor cpu
```

Los escenarios y exportaciones propios conviene guardarlos fuera del código del
proyecto. [Guía completa de uso y diagnóstico](GUIA_COMPLETA.md) y
[portabilidad](PORTABILIDAD.md).

## Actualizar una instalación hecha con git clone

Cerrar la aplicación y, desde la carpeta del proyecto:

```bash
git pull --ff-only
bash instalar.sh
bash ejecutar.sh
```

Esto actualiza código y dependencias. Si hay modificaciones locales o ramas
divergentes, Git detiene la actualización para que puedas resolverlas conservando
tus cambios. El futuro canal APT se documenta en
[REPOSITORIO_APT_DEBIAN_DEVUAN.txt](REPOSITORIO_APT_DEBIAN_DEVUAN.txt);
actualmente no hay un repositorio APT configurado por este proyecto.

## Compilar en macOS Apple Silicon

Con las herramientas Swift/Xcode configuradas en la Mac:

```bash
git clone https://github.com/javoxa/YoguiCuentas.git Yogui_Cuentas
cd Yogui_Cuentas
YOGUI_SKIP_OPEN=1 bash metal/yoguicuentas_metal/crear_app.sh
open "metal/yoguicuentas_metal/dist/YoguiCuentas Metal.app"
```

La app se construye localmente con firma ad hoc, sin Developer ID ni notarización.
[Instalación y primera apertura](metal/yoguicuentas_metal/INSTALACION_APPLE_M1.md).

## Funciones y evidencia

Euler explícito, Crank–Nicolson/Rannacher, Jacobi ponderado y Gauss–Seidel
rojo–negro; nueve criterios de parada, muestreo reproducible y auditoría física;
edición de regiones, fuentes, materiales y contornos; isotermas con temperatura,
escala automática/manual, PNG, CSV e historial.

La verificación Linux incluye referencias analíticas y balances en CPU/OpenCL.
La devolución M1 actual acredita **106 XCTest aprobados sin fallos ni omisiones**,
120 mediciones y 144 conjuntos exportados auditados.
[Informe M1](INFORME_REVISION_METAL_20261106.md),
[verificación Linux](INFORME_VALIDACION_CPU_GPU_20261029.md) y
[pruebas para aceptar instalaciones](PREPARACION_PRODUCCION.md).

La aceptación manual completa de la nueva interfaz M1 y de instalaciones de destino
sigue pendiente de registro. El nombre de la futura edición estable está por decidir. Los contornos curvos son escalonados; el sesgo Robin
circular no desaparece solamente aumentando nodos. La imagen suave no añade
resolución física. [Límites y estado](ESTADO_PROYECTO.md).

## Artículo técnico

[Español](output/pdf/yoguicuentas_paper_20261030.pdf),
[inglés técnico británico](output/pdf/yoguicuentas_paper_en.pdf) y
[fuentes, datos y reproducción](technical_report/README.md).

Javier Armando Gutierrez — Departamento de Física, FCE, Universidad Nacional de
Salta, Salta, Argentina. Correspondencia: g.javier.ar@gmail.com.

## Publicación y mantenimiento

[Actualizar el repositorio existente](SUBIR_A_GITHUB.txt).
La documentación histórica y sus hashes se conservan como evidencia de las
campañas. Esta carpeta conserva el historial Git del proyecto; los entornos,
cachés y devoluciones originales permanecen fuera de los archivos publicables.
