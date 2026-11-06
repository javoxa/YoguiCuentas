# Traspaso a macOS M1: cambios, pruebas y devolución de resultados

> Documento histórico de entrada. La devolución M1 ya fue integrada y auditada.
> Estado vigente: [informe CPU/GPU](INFORME_VALIDACION_CPU_GPU_20261029.md).
> Las tareas pendientes descritas abajo corresponden al momento del traspaso.

Fecha: **29/10/2026**. Documento de trabajo para completar la versión Metal
antes del anuncio oficial. Puede entregarse a otra sesión de desarrollo junto
con las fuentes. Los pasos de este documento se ejecutan en la **Mac M1** salvo
el apartado de transferencia desde Linux.

## 1. Punto de partida y objetivo

La etiqueta Linux publicada es **0.2.4**; Metal usa su numeración independiente,
**0.11.0**. Hay cambios locales posteriores a esas versiones, sin publicar.
Las fuentes Swift incluidas ya contienen una primera implementación de
Gauss–Seidel y de los criterios de parada. **No están compiladas ni verificadas
en macOS**. No repetir su implementación desde cero sin revisar primero el código.

Objetivo en el M1: integrar/corregir esas fuentes en la copia de trabajo Metal,
cerrar las diferencias pendientes, ejecutar pruebas CPU Swift y GPU Metal y
devolver resultados reproducibles. Una prueba que compila, una prueba numérica
y una instalación satisfactoria son evidencias distintas.

No publicar, crear etiquetas ni modificar el informe técnico histórico por el
solo hecho de recibir este paquete. Primero obtener y revisar los resultados.
Conservar las correcciones y los fallos encontrados, no solamente el último log.

## 2. Llevar las fuentes correctas a la Mac

En Linux se prepararon:

- `TRASPASO_METAL_M1.md`: este documento.
- `dist/YoguiCuentas_Metal_M1_desarrollo_20261029.tar.gz`: paquete de trabajo con
  fuentes actuales, tests, escenarios, licencias y evidencias Linux.
- El archivo del mismo nombre terminado en `.tar.gz.sha256`: checksum del paquete.

El paquete **no es una app compilada ni un instalador**. No contiene `.build`,
entornos Python ni el historial Git. Sí incluye archivos nuevos todavía no
publicados. Descargar solamente `main` de GitHub puede dejar esos archivos fuera.

Copiar el archivo comprimido y su checksum a **Descargas** de la Mac. Desde Terminal:

```bash
cd "$HOME/Downloads"
shasum -a 256 -c YoguiCuentas_Metal_M1_desarrollo_20261029.tar.gz.sha256
mkdir -p "$HOME/Documents/YoguiCuentas-M1-20261029"
tar -xzf YoguiCuentas_Metal_M1_desarrollo_20261029.tar.gz \
  -C "$HOME/Documents/YoguiCuentas-M1-20261029"
cd "$HOME/Documents/YoguiCuentas-M1-20261029/YoguiCuentas"
shasum -a 256 -c MANIFIESTO_TRASPASO.sha256
```

`Downloads` es la ruta habitual de Finder «Descargas»; adaptar la ruta si el
archivo se guardó en otro lugar. Extraer en una carpeta nueva: no reemplazar la
copia Metal que ya funcionaba ni perder cambios propios de la Mac. No copiar
una `.build` de otro equipo. Si se trabaja sobre una copia macOS más reciente,
comparar y fusionar los archivos, conservando sus avances.

Conservar `IDENTIFICACION_TRASPASO.json` y el manifiesto inicial: identifican
exactamente las fuentes recibidas, aun sin `.git`. Mantener esta estructura:

```text
YoguiCuentas/
  LICENSE
  NOTICE
  TRASPASO_METAL_M1.md
  MANIFIESTO_TRASPASO.sha256
  IDENTIFICACION_TRASPASO.json
  verification/                 # evidencias de Linux
  scenarios/                   # ejemplos comunes de comparación
  metal/yoguicuentas_metal/
    Package.swift
    Sources/
    Tests/
    Assets/
    examples/
    crear_app.sh
    crear_icono.sh
    verificar_numerica.sh
```

`crear_app.sh` necesita `LICENSE` y `NOTICE` dos niveles por encima de la carpeta
Metal. Por eso conviene trasladar esta estructura completa.

## 3. Contratos que debe conservar la implementación

- **Grilla cartesiana estructurada**, uniforme por eje, con `dx` y `dy` distintos
  si corresponde; operador conservativo de cinco puntos y volúmenes duales.
- Las curvas se rasterizan: no hay malla polar ni malla no estructurada en esta
  etapa. No atribuir orden espacial dos a cualquier frontera escalonada.
- CPU Swift y GPU Metal usan **float32**. NumPy Linux usa **float64** como
  referencia. No exigir igualdad bit a bit entre esas precisiones.
- Euler avanza tiempo físico y respeta su cota estable. CN mantiene el rechazo
  del lote completo si falla el sistema interno; no recortar oscilaciones ni
  rebajar tolerancias automáticamente. Rannacher se aplica solo al inicio físico.
- Jacobi y Gauss–Seidel son **iterativos estacionarios**, sin tiempo físico.
  «Directo» en la interfaz significa resolver el sistema estacionario sin
  evolución temporal, no una factorización directa. Cada componente necesita
  Dirichlet o Robin con `h>0` para esos modos.
- Reiniciar, cambiar procesador o aplicar parámetros restaura el campo, los
  controles anteriores, las confirmaciones y el muestreo; queda detenido.
- Una medición D compara **campos confirmados en controles consecutivos**, no
  cuadros de pantalla ni el medio barrido rojo de Gauss–Seidel.

## 4. Cambios Swift preparados: revisar e integrar

Las rutas de esta tabla son relativas a `metal/yoguicuentas_metal`.

| Archivo | Cambio preparado | Verificación necesaria |
|---|---|---|
| `Sources/YoguiCuentasMetal/Scenario.swift` | `.gaussSeidel`, opciones de convergencia y lectura v1 con valores predeterminados | Validación, migración y compatibilidad con escenarios anteriores |
| `Sources/YoguiCuentasMetal/Scene.swift` | Persistencia de `canvas.time.convergence` en v2 | Ida y vuelta, ausencia de parámetros nuevos y conservación de roles/materiales/contornos |
| `Sources/YoguiCuentasMetal/ThermalSolver.swift` | Gauss–Seidel rojo–negro CPU y dos despachos Metal ordenados | Un barrido completo = rojo + negro; sin carreras, mismos contornos y nodos inactivos |
| `Sources/YoguiCuentasMetal/Convergence.swift` — nuevo | Nueve criterios, escalas, selección reproducible y medidas | Fórmulas, semillas, máscaras, cancelación y casos sin nodos elegibles |
| `Sources/YoguiCuentasMetal/SimulationModel.swift` | Campo del control anterior, auditoría física y confirmaciones separadas | Reinicio, cancelación y distinción `converged` / `criterion_met` / `max_steps` |
| `Sources/YoguiCuentasMetal/ContentView.swift` | Selectores de método, criterio, muestreo y tolerancias | Controles accesibles, etiquetas/unidades y activación efectiva del método |
| `Sources/YoguiCuentasMetal/Resources/Scenarios/estacionario_gauss_seidel.json` — nuevo | Ejemplo de Gauss–Seidel | Carga, corrida CPU/Metal, parada y reinicio |
| `Tests/SceneTests/NumericalVerificationTests.swift` — nuevo | Campaña analítica y registros `NUMERIC` | Ejecutar CPU y Metal; revisar métricas, no solo el total de tests |
| `Tests/SceneTests/ConvergenceCriteriaTests.swift` — nuevo | Normas, cancelación, semilla y falsa convergencia por dt pequeño | Compilar y ejecutar; comprobar ambos procesadores donde interviene el modelo |
| `verificar_numerica.sh` — nuevo | Ejecución y recolección de datos del M1 | Que conserve logs, CSV y código de salida también cuando falla |

### Gauss–Seidel

Usar ordenación **rojo–negro**, `ω=1`, con los dos colores por iteración.
Jacobi conserva `ω=2/3`. En Metal los despachos deben estar ordenados y leer/escribir
buffers distintos. No convertirlo en una actualización simultánea de todos los
nodos ni confundir sus iterados con Gauss–Seidel lexicográfico.

El JSON usa `gaussSeidel`. La CPU y la GPU deben resolver el mismo operador con
fuentes, materiales y Dirichlet/Neumann/Robin. El agregado estacionario no cambia
el Jacobi interno de CN.

### Criterios de parada y muestreo

| Identificador | Medida |
|---|---|
| `residual` | Máximo residuo físico y suma absoluta ponderada por capacidad/volumen |
| `delta_l1` | Suma de cambios absolutos de nodos |
| `delta_l2` | Euclídea del vector de nodos / Frobenius de la matriz |
| `delta_rms` | Raíz del promedio de cambios cuadrados |
| `delta_linf` | Máximo cambio absoluto; es la norma infinito nodal |
| `delta_matrix_1` | Máxima suma absoluta por columna |
| `delta_matrix_inf` | Máxima suma absoluta por fila |
| `delta_trace` | Valor absoluto de la suma de cambios diagonales |
| `delta_mean` | Valor absoluto del cambio medio con signo |

Traza y media pueden cancelarse; no son normas. En una grilla rectangular la
«traza» ofrecida es una suma diagonal, no la traza de una matriz cuadrada.
La norma matricial 2 no es Frobenius y no se ofrece con ese nombre.

Para D: `valor ≤ delta_atol + delta_rtol × escala`, con unidades K. La escala
usa el campo actual relativo a la temperatura inicial base; traza/media usan
sumas/medias absolutas para su escala. Para el residuo físico se conservan sus
tolerancias en K/s y su balance en W/m. No mezclar esas tolerancias.

La muestra es fija, sin reemplazo y solo de nodos activos libres. Cantidad y
semilla se guardan; si se piden demasiados nodos se usan todos. CPU/Python y
Swift comparten la selección: en grilla 9×7, bordes Dirichlet y tres nodos con
semilla 123, los índices lineales son **[31, 32, 46]**. La traza siempre usa su
diagonal libre y el residuo siempre todos los nodos; allí no se aplica la muestra.
Una diagonal sin nodos elegibles no confirma una medida cero.

El residuo físico se calcula siempre y tiene **su propio contador consecutivo**.
Una parada por D sin confirmación física debe anunciar «Criterio ΔT cumplido;
residuo físico sin confirmar», nunca «Estacionario alcanzado». El dt diminuto,
una media constante o una muestra que omita cambios son ensayos educativos,
no errores que haya que ocultar relajando límites.

## 5. Diferencias pendientes que hay que cerrar en la Mac

Estas tareas no deben darse por hechas al copiar los archivos:

1. **Compilar y corregir Swift/Metal.** En Linux no se pudo ejecutar el compilador
   ni XCTest de Apple. Registrar cada fallo y su corrección.
2. **Validación de tolerancias físicas.** La validación Metal todavía exige
   `steady_atol>0` y `steady_rtol>0` por separado. Linux acepta cero en una si
   la otra es positiva. Alinear ese contrato: ambas finitas/no negativas y
   al menos una positiva. Agregar tests, especialmente `rtol=0`.
3. **Historial de convergencia.** Linux guarda los últimos 512 controles en CSV,
   con pasos, intervalo, valor/límite y auditoría física. La primera adaptación
   Metal aún no exporta ese historial: incorporarlo, indicar truncamiento y
   limpiarlo al reiniciar. No acumular memoria indefinidamente.
4. **Exportación de campo y metadatos.** `SimulationModel.exportCSV()` todavía
   guarda coordenadas, temperatura y máscara, pero no identifica método,
   pasos/iteraciones, tiempo ni criterio. Ampliar el CSV o agregar un JSON
   acompañante. Para un estacionario no presentar las iteraciones como segundos;
   registrar también la condición de parada, tolerancias y procesador efectivo.
5. **Completar la campaña equivalente.** Los XCTest nuevos cubren una parte
   amplia, pero no todos los 217 controles Linux tienen ya su equivalente Swift:
   agregar balance transitorio independiente Neumann/Robin; refinamiento del
   círculo 17²/33²/65²; oscilación de alta frecuencia de CN y amortiguación Rannacher
   en GPU; y comparación sistemática de todos los criterios con todos/muestra.
6. **Identificar las fuentes finales.** El script actual registra equipo y
   versión, pero una copia sin Git necesita además un manifiesto/hash del código.
   Conservar el manifiesto de entrada y devolver las fuentes finales completas.
7. **Costo y rendimiento.** Los XCTest existentes no son un benchmark aislado.
   Para el informe de costo, agregar tiempos CPU/Metal con calentamiento,
   número de pasos/barridos, iteraciones internas de CN y tamaños declarados.

En OpenCL los controles reducen datos en GPU y leen 15 escalares. El modelo
Metal actual ya devuelve un campo al host por lote y evalúa estas medidas allí.
No afirmar que Metal tiene la misma ruta de transferencia ni los mismos costos;
registrar esa diferencia y optimizarla solo como una tarea explícita posterior.

## 6. Preparar el entorno y crear una carpeta para la campaña

Requisitos del proyecto: Apple Silicon arm64, macOS 13 o posterior, herramientas
Apple compatibles con Swift 5.9 o posterior. No hace falta instalar Python,
OpenCL ni Homebrew para estos XCTest. Usar las herramientas de Xcode/CLT que
correspondan al sistema; las instrucciones ampliadas están en la guía de instalación.

```bash
cd "$HOME/Documents/YoguiCuentas-M1-20261029/YoguiCuentas/metal/yoguicuentas_metal"
uname -m
sw_vers
xcode-select -p
swift --version
RUN_DIR="verification/m1-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN_DIR"
{
  date -u
  xcrun --find swift
  xcodebuild -version 2>&1 || true
  sysctl -n hw.memsize
  sysctl -n hw.logicalcpu
  pmset -g batt
  pmset -g custom
} > "$RUN_DIR/entorno-adicional.txt" 2>&1
```

Esperado: `arm64`. Si aparece `x86_64`, verificar Terminal/Rosetta antes de
interpretar costos. Si faltan las herramientas Apple, instalarlas siguiendo
`INSTALACION_APPLE_M1.md`. No usar `sudo` para compilar en la carpeta de usuario.
`hw.memsize` devuelve bytes de RAM. Un error de `xcodebuild -version` con solo
Command Line Tools se conserva como dato del entorno, no como fallo numérico;
registrar qué herramientas se utilizaron realmente.

## 7. Pruebas automáticas: orden de ejecución

### A. Campaña numérica dirigida

```bash
bash verificar_numerica.sh "$RUN_DIR/numerica"
```

Ejecuta `NumericalVerificationTests`, `StationaryTests`, `CrankNicolsonTests`
y `ConvergenceCriteriaTests`. Guarda equipo, log completo, mediciones CSV y
código de salida. **Exit 0 no basta** si hubo tests omitidos: revisar que se
ejecutaron las pruebas con GPU Metal y que no hay un fallback inadvertido a CPU.

Conservar el primer resultado si falla. Para una repetición luego de corregir:

```bash
bash verificar_numerica.sh "$RUN_DIR/numerica-repeticion-01"
```

No sobrescribir los primeros logs ni cambiar tolerancias para conseguir un
resultado verde sin justificarlo. Si cambia una tolerancia, registrar el valor
anterior, el nuevo, el motivo y el error independiente obtenido.

### B. Suite completa de regresión

```bash
bash -o pipefail -c 'swift test 2>&1 | tee "$1"' _ "$RUN_DIR/swift-test-completo.log"
printf '%s\n' "$?" > "$RUN_DIR/exit-status-completo.txt"
```

La invocación en Bash conserva el error real aunque la salida pase por `tee`.
Registrar aprobados, fallidos y omitidos, con motivos. Incluir los tests nuevos
que se agreguen para cerrar el apartado 5.

### C. Compilación de la app de distribución

```bash
YOGUI_SKIP_OPEN=1 bash crear_app.sh "$PWD/$RUN_DIR/YoguiCuentas Metal.app" \
  > "$RUN_DIR/build-app.log" 2>&1
printf '%s\n' "$?" > "$RUN_DIR/exit-status-app.txt"
```

Solo si la compilación terminó correctamente:

```bash
codesign --verify --deep --strict --verbose=2 "$RUN_DIR/YoguiCuentas Metal.app" \
  > "$RUN_DIR/codesign.log" 2>&1
shasum -a 256 "$RUN_DIR/YoguiCuentas Metal.app/Contents/MacOS/yoguicuentas_metal" \
  > "$RUN_DIR/binario.sha256"
open "$RUN_DIR/YoguiCuentas Metal.app"
```

La firma local no equivale a notarización. Probar apertura de esa app fuera
del entorno de compilación y anotar qué ocurrió; no desactivar Gatekeeper.

## 8. Matriz de verificación numérica y datos a registrar

| Ensayo | CPU Swift y GPU Metal | Datos necesarios |
|---|---|---|
| Dominio aislado, sin fuentes | Campo no uniforme; caja y elipse; materiales distintos | Energía inicial/final, deriva absoluta/relativa, dt y tiempo final |
| Fuente uniforme aislada | Comparar energía añadida con `Σ Q V × tiempo` | Aporte esperado/medido y error; no solo temperatura máxima |
| Neumann/Robin transitorio | Balance energético con flujo impuesto/disipado | Flujo integral por paso y energía; para CN usar promedio temporal consistente |
| Placa 1D con fuente | Perfil parabólico analítico | L∞/RMS del error y residuo final; Euler/Jacobi/GS |
| Dos materiales | Interfaz a mitad entre nodos, media armónica | Perfil, flujo a ambos lados, continuidad y balance |
| Neumann/Robin estacionario | Perfil lineal conocido | Error de temperatura, signo y valor del flujo |
| Refinamiento temporal | Grilla fija; dt, dt/2, dt/4 | Error frente al modo semidiscreto y orden observado: Euler≈1, CN≈2 |
| Refinamiento espacial | 17×9, 33×17, 65×33; dt controlado | Error frente a solución continua y orden≈2 en el caso suave |
| Círculo rasterizado | 17², 33², 65²; R=0.31 m, Q=4, k=1, T_borde=0 | Error a `T=Q(R²−r²)/(4k)`, área discreta y error de área; no exigir orden dos |
| CN con frecuencia alta | Paso grande; CN puro y Rannacher | Factor de amplificación; en el caso `dt·λ=4`, −1/3 y +1/9 respectivamente |
| Solver CN no convergente | Máximo de iteraciones deliberadamente insuficiente | Campo/contador anteriores conservados y mensaje de lote rechazado |
| Criterios de parada | Cada norma, todos/muestra y semilla fija | Medida, escala, límite, controles consecutivos, residuo físico y motivo de parada |
| Falsa convergencia | dt diminuto, media/traza con cancelación, cambio fuera de la muestra | El criterio puede cumplirse; no afirmar estacionario si la auditoría falla |
| Reinicio/cancelación | Euler/CN/Jacobi/GS y ambos procesadores | Campo inicial restaurado, control anterior y contadores limpios; Rannacher solo al reiniciar |

Los XCTest nuevos ya generan registros `NUMERIC` para varios de estos ensayos.
Agregar las columnas/métricas que falten para las pruebas complementarias.
La campaña Linux de referencia está en `verification/2026-10-28` y `2026-10-29`
en la raíz del paquete; no en el subdirectorio histórico de verificación Metal.

Tolerancias de la campaña Swift preparada: CN `atol=1e−8 K`, `rtol=1e−6`;
en los perfiles estacionarios, residuo `2e−5 K/s` y error máximo `2e−4 K`;
flujo de interfaz `1e−3 W/m²`. El círculo 33² usa residuo `5e−5 K/s` y error
`1.5e−2 K`. Son límites de esos tests, no una promesa universal. Compararlos con
los valores efectivos de cada archivo antes de interpretar los resultados.

Si CPU y Metal usan tolerancias de parada diferentes, conservarlas y explicar
el efecto en el número de iteraciones. Para comparar campos entre equipos usar
el mismo JSON, máscara, materiales, tiempo final y número de pasos/barridos,
o identificar expresamente la diferencia. No comparar capturas como sustituto
de una comparación de datos.

### Costo educativo: ensayo adicional

Medir, por ejemplo, 17², 33², 65², 129² y 257² nodos; 64 pasos/barridos completos
por método tras un calentamiento. Una iteración GS incluye ambos colores. En
CN registrar también sus iteraciones internas. Separar inicialización/compilación
del cálculo y declarar si se incluye lectura del campo. Hacer al menos tres
repeticiones y conservar cada tiempo, junto con modo de energía, alimentación,
memoria y carga de fondo. No mezclar costo por iteración con costo para llegar
al mismo tiempo físico ni con costo para alcanzar igual precisión.

## 9. Pruebas manuales de interfaz e instalación

Repetir en **CPU · Swift** y **GPU · Metal**, comprobando el procesador efectivo:

1. Cargar escenario, iniciar, pausar, reanudar, reiniciar y cambiar procesador.
2. Elegir Gauss–Seidel; comprobar iteraciones sin segundos físicos y controles
   accesibles. Verificar también Jacobi y animación CN.
3. Recorrer los nueve criterios. Probar todos/muestra, cantidad y semilla;
   guardar/reabrir escenario y comprobar la persistencia. Residuo y traza no
   deben usar una muestra como sustituto de sus conjuntos completos.
4. Observar un caso que pare por D sin confirmar el residuo; revisar el mensaje,
   la medida y las confirmaciones. Reiniciar y repetir con criterio físico.
5. Dibujar región y recta; seleccionar con el mouse; incluir/excluir; asignar
   fuente, material y contorno por tramo. Aplicar y revisar el campo resultante.
6. Isotermas equiespaciadas **en temperatura**, cantidad, rótulos, escala
   automática/manual, barra de color con mouse, 2D/3D y exportación PNG.
7. Guardar JSON y exportar campo/historial/metadatos. Revisar unidades,
   máscara, tiempo físico o iteraciones, método y condición real de parada.
8. Abrir la app compilada desde Finder/Aplicaciones, incluyendo escenarios y
   recursos. Registrar cualquier aviso de primera apertura y fallos de firma.

Capturas: al menos selector de criterios, Gauss–Seidel, falsa convergencia,
isotermas rotuladas y editor con contorno seleccionado. Anotar resultado por
caso; «abre la ventana» no verifica el solver ni todos los controles.

## 10. Qué devolver para el informe final

Devolver **una carpeta comprimida** con:

| Archivo/conjunto | Para qué sirve |
|---|---|
| `RESUMEN_M1.md` | Qué se integró, qué quedó pendiente y conclusión de cada prueba |
| `equipo.txt` y, si hace falta, datos adicionales de RAM/energía | Identificar M1, macOS, arquitectura, Swift/Xcode y GPU real |
| `swift-test.log`, `mediciones.csv`, `exit-status.txt` de cada ejecución | Valores y pruebas dirigidas, incluidos fallos y repeticiones |
| `swift-test-completo.log` y su código de salida | Regresiones del proyecto completo y omisiones |
| Logs de compilación/app/firma y `binario.sha256` | Identificar el ejecutable efectivamente probado |
| Escenarios JSON, campos CSV y metadatos de los casos comparados | Reproducir grilla, métodos, dt, tolerancias, muestras y diferencias de campo |
| Historiales de convergencia y tabla de criterios | Distinguir criterio satisfecho de residuo físico verificado |
| Tabla de tiempos y repeticiones | Estudiar costo según nodos y método sin atribuir aceleraciones infundadas |
| Capturas PNG y lista de comprobaciones manuales | Documentar interfaz y distribución; complementan los datos numéricos |
| Manifiesto/identificación de entrada y fuentes finales | Saber exactamente qué código produjo la evidencia |

Mínimo de columnas para resultados cuantitativos: ensayo, backend efectivo,
precisión, nx/ny, dx/dy, dt, tiempo físico o iteraciones, método, criterio,
muestreo/semilla/cantidad, tolerancias, medida/escala/límite, residuo físico,
confirmaciones, error contra referencia y motivo de parada. Para energía y flujo,
incluir valor esperado, medido y error con unidades. Para costo, tiempos de cada
repetición y qué operaciones se incluyeron.

Plantilla de `RESUMEN_M1.md` para completar:

```markdown
# Devolución M1
Fecha:
Equipo / RAM / alimentación / carga de fondo:
macOS / arquitectura / Xcode-CLT / Swift:
Identificación de entrada y de las fuentes finales:
App y checksum probados:

## Cambios integrados o corregidos
- Archivo, problema, cambio y motivo:
- Diferencias aún pendientes respecto de OpenCL:

## Pruebas automáticas
Dirigidas: aprobadas / fallidas / omitidas, motivo y logs:
Suite completa: aprobadas / fallidas / omitidas, motivo y logs:
Procesadores efectivamente ejercitados:
Cambios de tolerancia, motivo y error independiente obtenido:

## Resultados numéricos
Conservación, flujo, soluciones analíticas y órdenes observados:
Círculo rasterizado y refinamiento:
Criterios y falsas convergencias:
Comparación CPU Swift / GPU Metal / referencia Linux:
Tiempos y condiciones de medida:
Archivos CSV/JSON asociados:

## Interfaz e instalación
Caso / CPU o Metal / resultado / captura o log:

## Fallos y límites
Cómo reproducir cada fallo pendiente:
Qué no se pudo probar y por qué:
```

### Empaquetar la devolución desde la carpeta Metal

Copiar a la carpeta de campaña los dos archivos de identificación que están
en la raíz del paquete recibido:

```bash
cp ../../MANIFIESTO_TRASPASO.sha256 ../../IDENTIFICACION_TRASPASO.json "$RUN_DIR/"
tar -czf "$RUN_DIR/codigo_metal_final.tar.gz" \
  Package.swift Sources Tests crear_app.sh crear_icono.sh verificar_numerica.sh \
  README.md SCENE_FORMAT.md Assets/AppIcon.png Assets/AppIcon.icns examples
```

Incluir también cualquier archivo de código nuevo fuera de esa lista. Si se
trabajó con Git se puede agregar un diff, pero **un diff no incluye archivos
nuevos sin seguimiento**: las fuentes finales siguen siendo necesarias.

Después de completar el resumen y copiar las mediciones/capturas:

```bash
tar --exclude='*.app' -czf "$HOME/Desktop/YoguiCuentas_resultados_M1.tar.gz" "$RUN_DIR"
shasum -a 256 "$HOME/Desktop/YoguiCuentas_resultados_M1.tar.gz" \
  > "$HOME/Desktop/YoguiCuentas_resultados_M1.tar.gz.sha256"
```

El archivo de devolución excluye la app para reducir tamaño; el código final,
logs y checksum identifican lo probado. Conservar la app en la Mac por si luego
hace falta inspeccionarla. Si se cierra Terminal, volver a definir `RUN_DIR`
con la carpeta real creada, en lugar de inventar una campaña nueva.

## 11. Cómo se usará la devolución

El informe final separará: verificación del operador y los integradores,
criterios de parada y falsas convergencias, error geométrico, costo computacional,
interoperabilidad de formatos y pruebas de interfaz/instalación. Las tablas
distinguirán NumPy float64, OpenCL float32, Swift float32 y Metal float32.

No se declarará verificada una plataforma a partir de resultados de otra, ni
se convertirá una prueba omitida en aprobada. Las versiones publicadas anteriores
y el informe técnico histórico conservan su alcance; la nueva evidencia se
presentará como una campaña identificada de desarrollo.
