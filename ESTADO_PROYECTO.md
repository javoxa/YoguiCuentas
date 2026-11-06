# YoguiCuentas — estado del proyecto

Actualizado: **06/11/2026**. Base publicada: **OpenCL 0.2.4 / Metal 0.11.0**,
con numeración independiente. Versiones beta: **OpenCL 0.2.5 / Metal 0.12.0**.
Preparadas en la carpeta ordenada `Yogui_Cuentas`, conservando el historial Git
y el repositorio actual. La distribución sigue mediante `git clone`. El nombre
de la versión estable está por decidir; no se publicaron etiquetas ni se ejecutó
una subida durante esta preparación. Los pendientes conservan su alcance.

## Estado actual y siguiente paso

OpenCL/NumPy incorpora Gauss–Seidel rojo–negro, nueve criterios de parada,
muestreo reproducible, auditoría física independiente e historial de controles.
La campaña Linux está ejecutada en CPU y **RTX A2000, índice OpenCL 1**.
La devolución M1 del 29/10 quedó revisada e integrada: **103 XCTest aprobados,
sin fallos ni omisiones**, en CPU Swift y GPU Metal. Las fuentes de aquella entrega se cotejaron
con la campaña y el benchmark recibidos. Después se cambió la versión de la app
en el empaquetado (0.12.0) y, el 06/11, la capa de presentación para los idiomas.

El [informe de validación CPU/GPU](INFORME_VALIDACION_CPU_GPU_20261029.md)
reúne resultados, integridad y limitaciones. La [preparación de publicación](PREPARACION_PRODUCCION.md)
indica los controles finales. La guía de traspaso y el paquete original se conservan
como antecedentes; no sustituyen las fuentes finales devueltas por el M1.

## Actualización del 6 de noviembre

Se incorporó el selector Español/English en Linux y en las fuentes de Metal,
con español inicial y traducción de presentación que conserva los valores del
modelo. Linux: cuatro pruebas nuevas de idioma, siete de regresión de interfaz
y prueba breve de la aplicación CPU/OpenGL aprobadas. Metal: devolución nueva integrada, con **106 XCTest aprobados sin fallos ni
omisiones** y app release reconstruida en M1. Incluye tres pruebas de idioma y
migración v1. La aceptación visual completa sigue pendiente. El resultado de
octubre mantiene su alcance histórico. [Revisión nueva](INFORME_REVISION_METAL_20261106.md).
[Detalle y protocolo](IDIOMAS.md).

El paper tiene una traducción completa a inglés británico, 16 páginas, cuatro
figuras y siete tablas, con ecuaciones y datos cotejados con la revisión española.
[Archivos y reproducción](technical_report/README.md).

La sincronización está preparada con fuentes, informes y verificación del catálogo;
esta copia conserva el historial y se prepara con un commit de actualización
sobre `main`, sin etiquetas ni publicación remota.
[Guía de sincronización](SINCRONIZACION_GITHUB.md).

## Corrección de selección de bordes — 06/11/2026

Se corrigió la lectura de condiciones de borde ya instanciadas (`Boundary`) al
seleccionar lados del lienzo. La migración de escenas v1 con base rectangular
recupera sus ediciones rectangulares como figuras editables, solamente cuando
reproduce exactamente la máscara original. Esto permite asignar condiciones por
lado a los dos recortes de `prueba_01`, conservando los nodos activos y materiales.
Otras máscaras antiguas conservan su representación anterior.

Verificación: diez pruebas de escena v2 (incluido CPU/OpenCL A2000 y prueba gráfica)
y cuatro del editor aprobadas. La regresión de `prueba_01` comprueba selección
repetida, Dirichlet/Neumann/Robin/adiabático por lado y persistencia JSON. El modelo
de escena cambió después de las campañas de octubre; sus resultados históricos
no se presentan como una ejecución nueva de esta revisión.

## Devolución M1 del 6 de noviembre

Se integraron IDs estables en migración v1 y una regresión de serialización.
Se verificaron los manifiestos de entrega/resultados y 144 conjuntos exportados;
120 mediciones de costo recibidas. La primera construcción falló por caché PCH
con ruta antigua y el reintento limpio aprobó. Se conserva la evidencia de ambos
intentos. El checklist manual no fue completado: la compilación aprobada no
cierra esa aceptación. [Informe y alcance](INFORME_REVISION_METAL_20261106.md).

## Cambios incorporados

| Área | Estado Linux / OpenCL | Estado de la adaptación Metal |
|---|---|---|
| Gauss–Seidel | CPU y GPU, rojo–negro ω=1; dos colores por iteración; ejemplo incluido | CPU Swift/Metal aprobado en la campaña M1 |
| Métodos anteriores | Euler, CN/Rannacher y Jacobi ponderado ω=2/3 conservados | Regresión M1 aprobada en el alcance ensayado |
| Criterios de parada | Residuo físico; ΔT L1, L2/Frobenius, RMS, máximo nodal, normas matriciales 1/∞, traza y media | Cálculo y persistencia verificados; aceptación visual pendiente |
| Nodos de control | Todos los nodos libres o muestra fija sin reemplazo, cantidad y semilla reproducibles | Mismo algoritmo y fixture común verificados en XCTest |
| Auditoría física | Máximo de residuo y suma absoluta ponderada, siempre sobre todo el dominio libre | Contadores independientes verificados en M1 |
| Estados de parada | `converged`, `criterion_met` sin certificar estacionario y `max_steps` | Verificados en M1, incluidas falsas convergencias |
| Historial / datos | JSON final con medidas y escalas, CSV de los últimos 512 controles, CSV de campo con metadatos | Historial de 512 controles y metadatos exportables verificados |
| Formatos | JSON v1 y v2, opciones nuevas con defaults compatibles | Persistencia y contratos de exportación verificados |
| Verificación | Campañas analíticas, convergencia, conservación, flujo, círculo rasterizado y costo | 103 XCTest aprobados; 144 conjuntos de exportación auditados |
| CI | Campaña NumPy y tests CPU de criterios configurados; publicación condicionada a la campaña | Workflow aún no ejecutado con estos cambios; Metal no queda validado por Linux |

Se conservan las mejoras previas de interfaz: barra lateral accesible, escala
manual/automática con mouse, isotermas y rótulos, CPU interactivo en trabajador,
PNG/CSV y editor de escena v2 con dominio, fuentes, materiales y contornos por
tramo. El historial de esas etapas se mantiene al final de este archivo.

## Evidencia vigente

| Fecha | Campaña | Resultado | Registro |
|---|---|---|---|
| 28/10 | Suite completa anterior a los criterios nuevos | 147 aprobadas, sin omisiones | [unittest](verification/2026-10-28/unittest.log) |
| 28/10 | Energía, perfiles, refinamiento y mediciones de costo | 217 comprobaciones aprobadas; 112 registros de experimentos/mediciones | [Resumen y gráficos](verification/2026-10-28/RESUMEN.md) |
| 29/10 | Suite completa con los criterios nuevos | 155 aprobadas y 2 omitidas; 157 descubiertas, sin fallos | [unittest](verification/2026-10-29/unittest.log) |
| 29/10 | Pruebas específicas de criterios | 10 aprobadas, incluidos CPU, OpenCL y configuración Tk | [tests de criterios](verification/2026-10-29/criteria-unittest.log) |
| 29/10 | Revalidación física CPU/A2000 del árbol actualizado | 217 comprobaciones aprobadas | [Informe](verification/2026-10-29/numerical/README.md) |
| 29/10 | M1 CPU Swift / GPU Metal | 103 XCTest aprobados, cero omisiones; 120 mediciones de tiempo | [Informe integrado](INFORME_VALIDACION_CPU_GPU_20261029.md) |
| 29/10 | Comparación pedagógica de criterios, todos/muestra y dt diminuto | 64 comparaciones, con errores al equilibrio y motivos de parada | [Tabla](verification/2026-10-29/criteria/README.md) |

Las dos omisiones del 29/10 son pruebas de clic nativo por escritorio bloqueado;
no se omitieron los controles numéricos nuevos ni los de GPU. No desbloquear ni
cambiar la configuración del escritorio para forzar esos tests.

Las campañas guardan fecha, equipo, commit base, estado `dirty` y hash de las
fuentes Python/OpenCL. Son evidencia de un árbol local identificado, no del
binario original de la etiqueta 0.2.4. Los tiempos incluyen carga no aislada;
no se prometen aceleraciones universales. La evidencia M1 se registra por separado y usa sus propios hashes y tolerancias.

## Alcance numérico y criterios

El problema se discretiza sobre una **grilla cartesiana estructurada**, uniforme
por eje, con operador conservativo de cinco puntos y volúmenes duales. Dibujar
curvas no genera una malla polar ni ajustada a la frontera: se rasterizan nodos
y caras. El refinamiento reduce errores pero aumenta memoria y costo; en Euler
reduce también el dt admisible.

El criterio predeterminado sigue siendo el residuo físico máximo y su suma
absoluta ponderada por capacidad y volumen. Las medidas ΔT comparan controles
consecutivos, no imágenes ni medios barridos. Tienen tolerancias en K separadas
de la auditoría en K/s. La auditoría y el criterio elegido tienen confirmaciones
independientes. Una muestra, traza o media que se estabilice no certifica el campo
completo. La norma infinito nodal equivale al máximo absoluto; la matricial
infinito suma por filas. La traza/media admiten cancelación.

Método, límites y comandos: [VERIFICACION_NUMERICA.md](VERIFICACION_NUMERICA.md)
y [CRITERIOS_ESTACIONARIO.md](CRITERIOS_ESTACIONARIO.md).

Las grillas polares para círculos y las mallas no estructuradas son etapas
futuras diferentes: una grilla polar puede seguir siendo estructurada. No están
implementadas. No hay funciones temporales arbitrarias ni propiedades térmicas
dependientes de temperatura en el alcance validado.

## Arquitectura que hay que conservar

| Responsabilidad | Archivos Python / OpenCL |
|---|---|
| Escenarios y formatos | `config/scenarios.py`, `model/scene.py` |
| Geometría, materiales y fuentes | `model/domain.py`, `regions.py`, `sources.py`, `scene.py` |
| Operador y métodos | `numerics/operators.py`, `steady.py`, `crank_nicolson.py` |
| Normas y muestreo | `numerics/convergence.py` |
| CPU y trabajador interactivo | `compute/scheduler.py`, `compute/cpu_live.py` |
| GPU y CN consultable | `compute/opencl_scheduler.py`, `compute/crank_nicolson.py`, `compute/kernels/*.cl` |
| Publicación gráfica | `render/interop.py`, `render/cpu_transport.py`, `simulation/live.py` |
| Escalas / curvas | `render/statistics.py`, `isotherms.py`, `colorbar.py`, `renderer.py` |
| UI / edición | `ui/main_window.py`, `configuration.py`, `scene_editor.py` |
| Exportación y campañas | `capture/fields.py`, `verification.py`, `compare_criteria.py` |

- Mantener fence → acquire → copia → release completo → dibujo. Un lote y una
  publicación pendientes; no introducir `finish` por cuadro.
- El campo privado calculado y el publicado son distintos. PNG, isotermas y
  CSV corresponden al campo confirmado visible y sus metadatos.
- NumPy calcula en float64; OpenCL y visualización usan float32. CPU interactivo
  calcula en un trabajador. CPU Swift y Metal usan float32, sin equivalencia bit a bit.
- CN resuelve incrementos; rechazar el lote completo si falla. Rannacher solo al
  primer paso físico; reiniciar lo repite. No recortar oscilaciones.
- Jacobi y GS estacionarios cuentan iteraciones, no tiempo. GS usa ambos colores;
  el campo del control anterior no puede ser un medio barrido.
- El control OpenCL conserva el campo anterior en GPU y lee 15 escalares por
  comprobación. No atribuir esa ruta de transferencia al modelo Swift/Metal actual.
- La escena inmutable y sus IDs/roles/contornos son la fuente de verdad; los
  campos derivados se cachean. No sustituir escenas ni resultados del usuario.
- Fuentes de área: W/m³ y muestreo 8×8 en v2; fuentes de línea: W/m. La migración
  v1→v2 puede cambiar discretización del área; no afirmar igualdad exacta universal.
- Las condiciones por tramo actúan en caras expuestas; dos regiones activas
  conservan conducción. Fronteras internas a media celda, Robin con resistencia.
- Isotermas equiespaciadas en temperatura, no en distancia; N es cantidad de
  niveles, no de curvas conexas. No inventar curvas para completar el contador.
- Mantener columna de 320 px, `grid_propagate(False)` y host GL separado;
  no reintroducir la superposición que ocultaba el menú.

## Comandos de esta workstation

Usar **A2000, índice 1**. La A4000 está reservada para otros trabajos. No usar
la variable heredada `CUDA_VISIBLE_DEVICES` para limitar el inventario OpenCL.

```bash
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas --gui --device 1 --batch-size 8
env -u CUDA_VISIBLE_DEVICES YOGUI_TEST_DEVICE=1 YOGUI_TEST_GL=1 \
  .venv/bin/python -m unittest discover -s tests -v
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas.verification \
  --backend all --device 1 --skip-benchmark --output verification/local/numerical
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas.compare_criteria \
  --backend all --device 1 --output verification/local/criteria
```

Conversación/UI en español. `rg` no está instalado; usar alternativas. No
sobrescribir `scenarios/mix_base.json` ni resultados del usuario. CPU puede
iniciar sin GPU con `--processor cpu`; la distribución Linux no requiere CUDA.

## Pendientes para completar y publicar

1. Aceptación visual/manual en M1: editor, selección de rectas y regiones,
   contornos, isotermas, escala, 2D/3D y exportaciones.
2. Instalar/desinstalar el `.deb` en Debian/Devuan de destino; verificar selección
   CPU automática y el arranque sin GPU dedicada.
3. Probar primera apertura de la app en otra Mac, recursos y Gatekeeper. La firma
   ad hoc recibida fue verificada en macOS; no hay Developer ID ni notarización.
4. Repetir las dos pruebas Linux de clic nativo cuando el escritorio esté disponible.
5. Ejecutar CI sobre la candidata 0.2.5 / Metal 0.12.0 antes de
   publicar. No hubo commits, pushes, cambios de etiquetas ni publicación automática.

**Limitación geométrica comprobada:** Robin sobre un círculo rasterizado presenta
un exceso de conductancia de aproximadamente 31,3 % → 28,3 % al refinar 41² → 161².
Aumentar nodos no elimina el sesgo del perímetro escalonado; requiere otro tratamiento
geométrico. La convergencia del solver no certifica la frontera circular ideal.

## Historial de etapas anteriores

Los siguientes apartados se conservan como registro histórico. Sus conteos,
versiones y comandos no sustituyen el estado ni las evidencias vigentes de arriba.

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

## Carpeta ordenada y continuidad de la beta

Se reunieron las fuentes vigentes Linux y Metal, tests, papers y evidencia
pública en `Yogui_Cuentas`. La copia anterior se conserva como respaldo local.
La portada prioriza instalación y actualización desde fuentes. Se preparó una
guía futura de APT firmado; ese canal todavía no está desplegado. El repositorio
Git conserva el historial anterior. La copia publicable excluye entornos
virtuales, cachés, apps antiguas y devoluciones originales. YoguiCuentas sigue
en beta; el nombre de la futura edición estable aún no fue decidido.
