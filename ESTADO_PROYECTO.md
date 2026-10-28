# YoguiCuentas OpenCL — estado para continuar

Actualizado: **28/10/2026**, versión **0.2.4**. Raíz: `/home/javo/Programas/opencl/YoguiCuentas`.

## Pedido y estado

El usuario autorizó equiparar funcionalidad/presentación con Metal. Se incorporaron barra lateral sin superposición, capas independientes, escala automática/manual con mouse, isotermas sobre el rango activo con valores °C, nodos/potencia de fuente, Jacobi directo, CN/Rannacher, selector interactivo CPU/OpenCL, CSV, modelo/guardado/editor de escena v2, materiales y contornos por tramo y fuentes de línea. Ver [PARIDAD_METAL.md](PARIDAD_METAL.md) para alcance y límites.

La interfaz Linux es Tkinter/OpenGL, no SwiftUI. No afirmar equivalencia bit a bit, paridad total de todos los gestos ni certificación multivendor. El estado anterior está íntegro en `resultados/paridad_metal/estado_proyecto_antes_020.md`.

## Contexto que conservar

- Conversación/UI en español. Usar `.venv-portable/bin/python`.
- En esta estación usar **RTX A2000, índice OpenCL 1**; A4000 reservada para otros trabajos. El contexto gráfico de escritorio puede corresponder a otra GPU.
- No sobrescribir `scenarios/mix_base.json` ni resultados del usuario. Los nuevos ejemplos se añadieron sin sustituir escenarios existentes.
- Linux/Debian/iGPU: no exigir CUDA, sudo ni sharing. Se conservan `--transfer auto|shared|host` y recuperación de fallo de adquisición. CPU puede arrancar sin enumerar OpenCL con `--processor cpu`.
- `rg` no está instalado; usar alternativas. No hay un commit Git utilizable del árbol.
- La sesión de escritorio se bloqueó durante la validación. Las pruebas de hit-testing detectan ese estado y se omiten expresamente; no desbloquear/modificar el escritorio. El framebuffer GL sí se verificó.

## Arquitectura actual

| Responsabilidad | Archivos |
|---|---|
| Escenario y formatos | `config/scenarios.py`, `model/scene.py` |
| Geometría v1/v2, materiales y fuentes | `model/domain.py`, `regions.py`, `sources.py`, `scene.py` |
| Operador conservativo | `numerics/operators.py`, `steady.py` |
| Euler/Jacobi/CN CPU | `compute/scheduler.py`, `numerics/crank_nicolson.py` |
| GPU y CN consultable | `compute/opencl_scheduler.py`, `compute/crank_nicolson.py`, `compute/kernels/*.cl` |
| CPU interactivo | `compute/cpu_live.py` (un trabajador, un ticket) |
| Publicación | `render/interop.py`, `render/cpu_transport.py`, `simulation/live.py` |
| Escalas y curvas | `render/statistics.py`, `isotherms.py`, `colorbar.py`, `renderer.py` |
| UI | `ui/main_window.py`, `configuration.py`, `scene_editor.py`; editores v1 se conservan |
| Exportación | `capture/screenshots.py`, `capture/fields.py` |

## Contratos fundamentales

- Propiedad GL/CL: fence → acquire → copia → release completo → dibujo. Mantener un lote y una publicación pendientes. No añadir finish por cuadro.
- Campo privado calculado distinto del campo publicado. CSV, curvas, escalas y PNG usan el publicado y sus metadatos.
- Referencia NumPy float64; OpenCL y visualización float32. CPU interactivo convierte solo snapshots confirmados y no calcula lotes en el callback Tk.
- Cambiar procesador o aplicar escena reinicia y deja detenido. CPU/OpenCL no se sustituyen silenciosamente ante fallos numéricos.
- CN resuelve incrementos; no publicar ni avanzar contador hasta aceptar el lote completo. Sus tolerancias son del sistema lineal, en K. Arranque Rannacher solo en el primer paso físico; el reinicio lo repite.
- Jacobi directo cuenta iteraciones y carece de tiempo/dt físico. Requiere referencia en cada componente. No confundirlo con integración implícita temporal.
- Convergencia exige residuo máximo y suma absoluta ponderada, con confirmaciones. Límite no significa converger. No relajar tolerancias ni recortar temperaturas para ocultar oscilaciones.
- La escena inmutable guarda JSON canónico; campos derivados se cachean por escena/grilla/parámetros y no son fuente de verdad. IDs/orden/roles y ausencias de contornos heredados se conservan al guardar v2.
- Fuente de área: W/m³, muestreo 8×8 en v2. Línea: W/m, recorte semiabierto, profundidad de referencia 1 m. V1 conserva integración analítica hasta migrar al editor v2; no afirmar equivalencia exacta de esa migración para fuentes.
- Fronteras internas a media celda: Dirichlet y Robin con resistencia conductiva. Una curva sigue escalonada y tiene sesgo de perímetro.
- Las caras v2 tienen propietario/subsegmento; con ambos vecinos activos hay conducción material. Borrar un separador elimina regiones dependientes; borrar una fuente no separadora limpia referencias sin borrar el dominio.
- Escalas automáticas leen cuatro escalares GL por campo; rótulos leen anclajes por nivel, nunca temperatura completa por cuadro. Hay sincronización/coste, y curvas cuestan niveles × triángulos.
- N isotermas significa niveles, no componentes conexas. Uniformidad, discontinuidades entre piezas, cámara y resolución pueden impedir N trazos distinguibles. No inventar curvas para completar un contador.
- `ScrollablePage` usa grid: mantener `grid_propagate(False)` y columna de 320 px en la ventana principal. Un host separado recorta el drawable GL. No reintroducir la regresión de barra de 47 px.

## Verificación y arranque

```bash
bash ejecutar.sh --device 1
bash ejecutar.sh --device 1 --processor cpu
bash ejecutar.sh --console --backend opencl --device 1 --steady-method jacobi --output resultados/jacobi_nuevo
bash ejecutar.sh --console --backend opencl --device 1 --scenario scenarios/cn_animacion.json --steps 20 --output resultados/cn_nuevo
env -u CUDA_VISIBLE_DEVICES YOGUI_TEST_DEVICE=1 YOGUI_TEST_GL=1 .venv-portable/bin/python -m unittest discover -s tests -v
```

Registro nuevo: `resultados/paridad_metal/pruebas_release_020_final.log`. Capturas en `resultados/paridad_metal/visuales/`. Los fallos encontrados durante integración se conservan en registros anteriores; consultar el registro final para el resultado efectivo.

La comparación cuantitativa con Metal incluye el trapecio fuente (potencia/nodos y máximo final), no una campaña exhaustiva. Pendiente validación manual del editor con escritorio desbloqueado, campañas de rendimiento/portabilidad y revisión de combinaciones geométricas extremas. No hay video, malla no estructurada, funciones temporales arbitrarias, propiedades dependientes de T ni VLM; no pertenecen al alcance disponible en Metal de referencia.

Resultado final 0.2.0: **138 pruebas ejecutadas, 136 aprobadas, 2 omitidas**, 68,263 s, RTX A2000 (índice OpenCL 1, kernels CL 1.1). Las dos omisiones son de hit-testing nativo porque `LockedHint=yes`; no se omitieron las pruebas numéricas GPU ni las de framebuffer. Registro `resultados/paridad_metal/pruebas_release_020_final.log`.


## Correcciones 0.2.1 — selección, contornos y elección del método

- Seleccionar no ajusta el punto a la grilla. Las fuentes tienen prioridad frente a figuras envolventes; la lista las identifica con [fuente]. Los tiradores solo actúan sobre su figura propietaria.
- Elegir región reutiliza una región existente. El inspector muestra los controles de contorno arriba y enumera lados del lienzo y tramos generadores; edita el propietario real y conserva simultáneamente los cambios de roles/geometría de la región. Dos regiones activas siguen conectadas por conducción.
- Elegir Jacobi activa Hasta estacionario; elegir un integrador temporal desactiva Jacobi directo. Se conserva la validación de referencias térmicas y de convergencia.
- Pruebas ampliadas en test_scene_editor.py y test_configuration_ui.py. Los motores numéricos no requirieron cambios.

Validación final 0.2.1: **138 pruebas aprobadas, sin omisiones**, 65,145 s. Incluye pruebas gráficas interactivas, selección superpuesta, contornos desde región y activación Jacobi/CN, además de las verificaciones numéricas CPU/OpenCL en A2000. Registro: resultados/paridad_metal/pruebas_correcciones_editor.log.


## Corrección 0.2.2 — elegir rectas y subtramos

«Elegir borde» buscaba únicamente caras expuestas ya rasterizadas y no podía seleccionar un separador antes de excluir regiones. Ahora prueba la distancia a los trazos originales (rectas, lados de figuras y subsegmentos de polilínea), sin snap, conserva owner/clave, carga la condición guardada y resalta el tramo naranja. El lienzo se selecciona por sus lados continuos, incluso con grilla gruesa; se conserva el fallback para máscaras importadas. La selección normal prioriza trazos abiertos cercanos sobre rellenos superpuestos.

Una recta con ambos vecinos activos conserva conducción; su condición queda guardada y actúa al convertirse en frontera por exclusión de región. No se alteró el operador ni se introdujo una barrera interna artificial.

Validación dirigida: 10 pruebas de escena/editor aprobadas, incluidas selección previa a exclusión, condición efectiva posterior, subsegmento Neumann y relectura, superposición con fuente, contorno exterior y CPU/OpenCL. Registro resultados/paridad_metal/pruebas_seleccion_segmentos.log.


## Editor 0.2.3 — acciones sobre la selección

- Barra visible de dibujo/selección. Acciones Incluir, Excluir, Fuente, Material, Contorno y Geometría fijas junto al lienzo; no se desplazan al recorrer propiedades.
- Propiedades separadas en pestañas Fuente/Material/Contorno/Geometría/Objetos. Agregar fuente/material conserva los demás roles. Las acciones abren su pestaña y activan el rol correspondiente.
- Un clic vacío en Seleccionar crea/reutiliza la región delimitada; si una figura de dominio está subdividida por rectas, el clic interior selecciona la región resultante. Bordes y fuentes/materiales mantienen selección directa, y arrastrar vacío conserva selección por marco. Región por clic sigue disponible explícitamente.
- Isotermas verificadas: niveles equiespaciados en temperatura, no en distancia espacial. Se informa ΔT en la barra lateral y se explica la relación entre concentración de curvas y gradiente. No se cambian niveles para simular separaciones espaciales uniformes.
- Regresión de UI prueba clic en región formada por recta, excluir/incluir, reelección sin duplicar, recta como fuente/material/contorno y acciones visibles. Captura de revisión /tmp/yogui_editor_context.png.

Validación 0.2.3: **140 pruebas aprobadas sin omisiones**, 66,469 s, incluidas CPU/OpenCL, curvas y editor. Repetición de 3 pruebas del editor con espera del compositor y verificación de visibilidad. Captura inspeccionada: resultados/paridad_metal/visuales/editor_contextual_023.png. Registro completo: resultados/paridad_metal/pruebas_correcciones_editor.log.


## Paquete Debian/Devuan y selección de procesador — 0.2.4

`bash construir_deb.sh` produce `dist/yoguicuentas_VERSION_all.deb`. El paquete instala en `/opt/yoguicuentas`, declara las dependencias probadas (Python/Tk, PoCL, clinfo, Mesa/OpenGL) y en postinst crea un venv común en `/var/lib/yoguicuentas` e instala requisitos pip una sola vez. La primera instalación necesita acceso a los repositorios APT y al índice de paquetes Python. Cada usuario guarda resultados en `~/.local/share/yoguicuentas/resultados`. El lanzador de menú y terminal usa `--processor auto`: elige GPU OpenCL cuando encuentra una; si PoCL expone solo CPU, inicia NumPy. `--processor cpu|opencl` permite fijarlo. Los drivers OpenCL propietarios se instalan aparte si se despliega hardware que los necesite.


Paquete 0.2.4 generado: `dist/yoguicuentas_0.2.4_all.deb` (1,368,732 bytes). Se verificaron sintaxis de scripts, metadatos Debian, dependencias declaradas y contenido del archivo. No se instaló en una máquina destino: postinst requiere APT y PyPI accesibles.
