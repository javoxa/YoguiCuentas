# YoguiCuentas Metal

Port nativo para macOS con SwiftUI, AppKit y Metal. La versión Metal y la versión Python/OpenCL tienen numeración independiente. Los archivos JSON de escenario están en `Sources/YoguiCuentasMetal/Resources/Scenarios`.

## Instalar la versión para macOS

1. Abrí [Releases de YoguiCuentas](https://github.com/javoxa/YoguiCuentas/releases/latest) y descargá `YoguiCuentas_Metal_macOS_arm64.zip` desde **Assets**.
2. En Finder, hacé doble clic en el ZIP para extraer `YoguiCuentas Metal.app`.
3. Arrastrá la app a **Aplicaciones** y abrila con doble clic. Requiere macOS 13 o posterior y una Mac Apple Silicon (M1 o posterior).

El ZIP se genera automáticamente al publicar una Release. La app usa firma local y no está notarizada; si macOS bloquea la primera apertura, seguí [estos pasos](INSTALACION_APPLE_M1.md#si-macos-bloquea-la-primera-apertura). No necesitás instalar Xcode, Python, Homebrew ni OpenCL para usar el ZIP.

Si aún no aparece el ZIP en **Assets**, consultá [Actions](https://github.com/javoxa/YoguiCuentas/actions) y esperá a que termine correctamente **Build release packages** para `v0.2.4`.

## Animación con Crank–Nicolson (0.11.0)

En **Editar parámetros… → Tiempo → Integrador temporal**, seleccioná **Crank–Nicolson (CN)**. Elegí tiempo final o corrida sin límite, aplicá y pulsá **Iniciar**. Se conserva Euler explícito como predeterminado de los escenarios anteriores. En **Hasta estacionario → Evolución temporal** también puede usarse CN; **Estacionario directo · Jacobi** continúa resolviendo sin tiempo físico.

El paso automático es `safety × dtLimit × cn.stepFactor`, con factor CN inicial 10. El paso manual de CN puede superar la referencia explícita; Euler explícito mantiene su validación CFL. Un factor 10 significa diez veces menos pasos físicos para cubrir el mismo intervalo, no una garantía de diez veces más velocidad de ejecución: CN resuelve un sistema en cada paso. La velocidad efectiva en × permite observar el costo real, que depende del tamaño de malla, dt y tolerancias.

Para `T′ = f − A·T`, CN resuelve:

```text
(I + dt·A/2) T[n+1] = (I − dt·A/2) T[n] + dt·f
```

La implementación calcula el incremento `δ = T[n+1] − T[n]` mediante `(I + dt·A/2) δ = dt·(f − A·T[n])`. Usa Jacobi ponderado, con diferencias vecinas para reducir cancelación, y conserva la discretización de fuentes, materiales y bordes. La matriz desplazada permite evolución en componentes adiabáticas o Neumann sin imponer una referencia de temperatura estacionaria. Las fuentes y condiciones son constantes en el tiempo, como en el solver existente.

CPU y Metal usan tolerancias explícitas del sistema lineal: `‖r‖∞ ≤ atol + rtol·‖rhs inicial‖∞`, donde `atol` está en K, no en K/s. Se puede ajustar máximo y frecuencia de comprobación. Metal mantiene buffers residentes de incrementos/RHS y reduce el residuo en GPU por grupos de 256 nodos; la CPU solo lee los máximos de cada grupo. Los coeficientes y campos continúan en Float; CPU comprueba el residuo del sistema ensamblado con acumulación Double y GPU lo evalúa en Float. No se rebajan tolerancias automáticamente. Si no converge o produce valores no finitos, se rechaza el lote sin publicar su campo ni avanzar el tiempo visible. Pausar/reiniciar cancela el cálculo en los puntos de comprobación internos.

**Para enseñar estabilidad y precisión:** CN es de orden 2 en tiempo para soluciones suficientemente regulares y resolución interna suficientemente precisa. Es estable sin la restricción temporal del explícito para el problema difusivo, pero no amortigua bien las frecuencias más rápidas con dt grande. Un modo con autovalor λ tiene factor `g = (1 − dt·λ/2)/(1 + dt·λ/2)`: si `dt·λ > 2`, cambia de signo entre pasos. No se recortan temperaturas para ocultar ese efecto. Compará siempre con `dt/2` y luego `dt/4`; la tolerancia del sistema lineal no estima el error temporal. El aviso de paso grande usa la diagonal del operador como indicador conservador de posible oscilación, no como un detector de error.

**Arranque suavizado opcional:** activa dos medios pasos de Euler implícito en el primer paso físico, y usa CN puro después. Es una variante de arranque Rannacher, útil para condiciones abruptas; queda desactivada por defecto para poder estudiar CN puro. Reiniciar vuelve a aplicar el arranque; pausar y reanudar una corrida ya avanzada no lo repite.

Ejemplos del selector: **cn animacion** (perfil suave, factor 10) y **cn oscilaciones** (gaussiana estrecha, factor 50). En el segundo, compará CN puro con el arranque suavizado y activá escala automática para ver temperaturas fuera del rango inicial.

Referencias: [PETSc: esquema theta y CN](https://petsc.org/main/manualpages/TS/TSTHETA/), [Cambridge: métodos para difusión](https://www.damtp.cam.ac.uk/research/afha/lectures/Part_II_NumAn/Lect_6_slides_alt.pdf).

## Estacionario directo con Jacobi (0.10.0)

En **Editar parámetros… → Tiempo → Duración**, elegí **Hasta estacionario**. En **Convergencia estacionaria → Método**, seleccioná **Estacionario directo · Jacobi**, aplicá y pulsá **Iniciar**. El procesador CPU / GPU Metal se elige en la barra lateral. También está incluido el escenario **estacionario jacobi**.

Resuelve directamente el sistema estacionario del operador existente, `D·T − Σ a_vecino·T_vecino = f`, mediante Jacobi ponderado con ω = 2/3. La actualización usa una corrección por residuo con diferencias de temperaturas vecinas para reducir la cancelación numérica. Cada iteración lee el campo anterior y escribe otro; en Metal se reutilizan dos buffers y cada nodo se procesa en paralelo, sin construir una matriz densa. Las fuentes, interfaces de materiales, máscaras y contornos conservan su discretización. No es integración temporal implícita: no hay tiempo físico ni paso dt asociado a las iteraciones. La condición inicial solo aporta la primera estimación; los controles de velocidad física quedan desactivados.

La parada exige residuo máximo y residuo absoluto integrado dentro de las tolerancias existentes, durante las confirmaciones indicadas. La tolerancia absoluta mantiene unidades K/s porque se utiliza el operador dividido por capacidad térmica. Se muestra el residuo actual, iteraciones e iteraciones/s. Alcanzar el límite se informa como **Límite sin convergencia**; no equivale a resolver el problema. Los campos y coeficientes usan Float; tolerancias por debajo de su precisión pueden impedir la convergencia y no se relajan automáticamente.

Cada componente conectada libre debe tener una referencia: Dirichlet o Robin con h > 0. Las componentes puramente Neumann/adiabáticas se rechazan con una explicación, incluso si otra componente sí tiene referencia. Resolverlas con balance compatible y una restricción de temperatura media queda pendiente.

Jacobi es paralelo por iteración, pero su cantidad de iteraciones aumenta con el refinamiento. Esta versión no garantiza acelerar el explícito en todos los problemas; deja la base para Chebyshev o multigrid. Referencia: [Templates for the Solution of Linear Systems, Netlib](https://www.netlib.org/templates/templates.html).

El JSON v2 guarda `canvas.time.method` como `jacobi` o `explicit`; los archivos anteriores usan `explicit` por defecto. La lectura v1 también acepta `steady_method`. El método se usa únicamente cuando `steady` es verdadero.

## Barra lateral y edición numérica (0.9.6)

El orden es Escenario → Cálculo → Corrida → Superposiciones → Escala. Superposiciones se puede contraer y empieza cerrado. Densidad de vectores por eje y cantidad de isotermas permiten escribir el número o usar los botones; su rango es 1…max(nx, ny), mostrado en el panel. La cantidad de flechas efectiva depende del muestreo y del dominio activo.

Temperatura ambiente y h de Robin/Cauchy conservan el cursor mientras se escribe. Los valores enteros se muestran con una cifra decimal (por ejemplo `25,0`), sin redondear los valores físicos guardados; se aceptan coma, punto y notación científica. La barra lateral se recorta a su área y la barra de título usa fondo opaco para evitar superponer controles al desplazar.

## Fuentes y aplicación a la malla (0.9.5)

**Editar escena…** abre directamente el lienzo. Después de asignar una fuente, Q se guarda mientras se escribe (acepta `5000`, `5000,5` y `5e3`). El inspector indica nodos y potencia integrada. Una fuente no nula sin nodos activos impide aplicar y explica el motivo; una región excluida puede incluirse explícitamente en la malla conservando la fuente.

Tras **Aplicar al problema**, la simulación muestra la cantidad de nodos con fuente y su potencia. En 2D, **Nodos con fuente** los marca con puntos naranjas a partir del campo aplicado. El problema queda en t=0: pulsá **Iniciar** para avanzar. Q está en W/m³ para áreas y en W/m para líneas; no representa potencia total en W. Para áreas, el aporte térmico local es Q/(ρ·cp), antes de conducción y pérdidas.

## Dibujar y asignar propiedades (0.9.4)

Dibujá una figura: queda seleccionada automáticamente. En el panel derecho elegí fuente, dominio o material; configurá sus valores y pulsá **Aplicar al problema**. Ya no se elige un rol antes de dibujar.

En **Mano alzada**, volver al inicio cierra el contorno y permite aplicar una fuente a su interior. Si quedó abierto, usá **Cerrar trazo y añadir fuente en su interior**; para calentar solo el recorrido elegí **Añadir fuente sobre la línea**. Las fuentes se recortan al dominio activo. Para elegir un lado de un corte que atraviesa el lienzo, usá **Elegir región**.

## Instalación en Apple M1

La [guía de instalación Apple M1](INSTALACION_APPLE_M1.md) explica cómo instalar la app precompilada, compilar desde fuentes, comprobar arm64/firma y resolver problemas de primera apertura. El [estado del proyecto](../../ESTADO_PROYECTO.md) y el [informe técnico](../technical_report/informe_tecnico_yoguicuentas_metal.pdf) resumen el alcance y sus verificaciones.

## Abrir y ejecutar

1. Abrir `Package.swift` con Xcode 15 o posterior.
2. Elegir el esquema `yoguicuentas_metal` y ejecutarlo en macOS.

También se puede compilar e iniciar desde Terminal con Swift 5.9 o posterior:

```sh
swift build
swift run yoguicuentas_metal
```

Para crear una app que puedas abrir con doble clic, ejecutá:

```sh
bash crear_app.sh
```

El resultado queda en `dist/YoguiCuentas Metal.app`. El script compila la versión Release, incorpora los escenarios, firma la app localmente y la abre en una instancia nueva. Cada compilación lleva un número identificador en Finder para distinguirla de una ejecución abierta desde Xcode. Para distribuirla a otros usuarios fuera de esta Mac todavía harían falta una firma Developer ID y notarización de Apple.

## Alcance del port inicial

- Interfaz macOS nativa SwiftUI, sin Tkinter ni OpenGL.
- Cuatro vistas de fondo: mapa de temperatura, superficie 3D, módulo del gradiente y módulo del flujo.
- Campo vectorial de flujo e isotermas como superposiciones independientes en cualquier vista, también al exportar PNG. La cantidad de isotermas y la densidad de flechas son ajustables; sus rótulos de temperatura se pueden ocultar sin quitar las líneas. Las isotermas se calculan a partir del rango de temperaturas activas y se rotulan en °C; las flechas indican dirección, con longitud normalizada.
- Selector CPU / GPU Metal, velocidad estándar o personalizada, escenarios JSON, editor de grilla/materiales/bordes/regiones/fuentes/geometría/tiempo, lienzos triangulares, escalas de color, cámara, ficha de estado y control de corrida.
- Exportación del campo a CSV e imagen del lienzo a PNG.
- Kernels Metal para evolución explícita y estacionario directo con Jacobi ponderado, con implementaciones CPU de referencia.
- Se incluyen los escenarios JSON de la versión Python para que sean seleccionables desde la app.

La carga migra JSON versión 1 y acepta versión 2; el guardado escribe la escena editable v2. El editor gráfico usa primitivas geométricas con roles componibles, contornos por segmento y fuentes de línea. Revisar `PORTABILIDAD.md` para las diferencias numéricas que todavía requieren comparación con la implementación Python.

## Desarrollo

El kernel de cómputo vive en `ThermalSolver.swift` y se compila en tiempo de ejecución desde Metal Shading Language. Esto evita depender del build phase de Xcode para los archivos `.metal` y permite compilar el paquete SwiftPM. La UI usa SwiftUI, los mapas y flechas se dibujan con Canvas y la superficie 3D usa una malla SceneKit con aceleración Metal.

## Editor de escena vigente (0.9.6)

Abrir **Editar escena…** desde la barra lateral; también se puede acceder desde parámetros. **Lienzo nuevo** inicia una escena vacía con el lienzo completo activo y contornos heredados del default adiabático. Las herramientas crean rectángulos, elipses/círculos (Shift), líneas, polígonos y trazos libres simplificados. El panel permite combinar dominio, material, fuente y contornos en la misma primitiva. **Aplicar al problema**, dentro del editor geométrico, reconstruye el operador, detiene la corrida y vuelve a t=0. **Volver a parámetros** conserva un borrador sin aplicarlo todavía.

Para dividir el lienzo, trazar una línea de borde a borde o una figura cerrada. La figura nueva queda seleccionada; para elegir una componente, pulsar **Elegir región** y hacer clic en uno de los lados o dentro de la figura, que se resalta en amarillo. El panel ofrece **Excluir del dominio**, **Incluir en el dominio**, **Asignar material** y **Añadir fuente en esta región**. Un trazo abierto que no cierra una región no elimina una franja de celdas; se avisa si solo existe una región. La resolución debe permitir distinguir sus regiones.

Las regiones se guardan mediante un punto interior y los identificadores de sus límites; se recalculan al mover los trazos o cambiar la grilla. Si el límite atraviesa el punto guardado, este identifica el lado seleccionado en la geometría nueva. Borrar un límite borra también sus asignaciones de región dependientes; deshacer recupera ambos. Con dos regiones activas de materiales distintos hay conducción por interfaz. Al excluir una región, sus caras expuestas usan la condición del trazo original; se configura con **Seleccionar figura → corte → Contornos**, o desde **Contorno** sobre el borde expuesto. Ejemplo incluido en el selector de escenarios: **corte regiones** ([JSON editable](examples/corte_regiones_v2.json)).

**Condiciones por borde (0.9.2):** al seleccionar una región, el panel lista por separado los lados del lienzo y los trazos que forman su perímetro. **Resolver solo esta región** conserva únicamente la región elegida. Hacer clic sobre un borde (también desde Elegir región) o usar **Elegir borde** abre su condición individual y resalta únicamente ese lado/tramo. En polígonos y polilíneas cada tramo entre vértices tiene su propia condición; el predeterminado del trazo completo sigue disponible como herencia. El selector muestra **Robin / Cauchy**, con h y temperatura ambiente, además de Dirichlet, Neumann y adiabático. El JSON conserva el nombre canónico `Robin`. Los lados exteriores pertenecen al lienzo aun cuando coincidan con el borde de una figura.

Ejemplo **trapecio bordes**: base inferior adiabática, lateral derecho Neumann (1200 W/m² salientes), lado superior Dirichlet (50 °C), corte inclinado Robin/Cauchy (h=15 W/m² K, T ambiente=80 °C). [JSON editable](examples/trapecio_bordes_v2.json).

**Fuentes dentro del dominio:** dibujar la figura, seleccionarla y pulsar **Añadir fuente en esta región**; la fuente se superpone al dominio y conserva los límites ya referenciados. Al asignarla se activa el overlay de fuentes y se puede editar Q. También se puede seleccionar una región y pulsar **Añadir fuente en esta región**: se conserva su operación de dominio, material y condiciones. El panel muestra la potencia integrada en el dominio y el número de nodos con aporte (profundidad de referencia: 1 m). La porción exterior al dominio no aporta; una fuente no nula totalmente exterior muestra cero y bloquea Aplicar hasta corregir su geometría o incluir explícitamente la región en la malla. Los valores de Q mantienen sus unidades físicas, por lo que una intensidad pequeña puede producir cambios de temperatura lentos.

La opción **Delimita regiones** permite usar explícitamente una misma figura como límite y fuente. Un corte ya usado por el dominio conserva esa función al añadirle una fuente de línea. Al convertir una figura aún no usada como límite en fuente, deja de dividir el lienzo. Borrar una fuente superpuesta conserva el dominio. Ejemplo incluido: **trapecio fuente** ([JSON](examples/trapecio_fuente_v2.json)), con una fuente circular dentro del trapecio y sus cuatro condiciones de borde.

Alt desactiva snap; Shift restringe rotación a 15°. Selección múltiple con Shift/Cmd y marquesina, handles de tamaño y rotación, edición de vértices e inserción con puntos medios, ⌘C/V/D, Supr, Tab/Shift+Tab y ⌘[/⌘] para orden. El historial admite 150 cambios con ⌘Z y ⇧⌘Z. La selección múltiple muestra acciones de conjunto; los valores numéricos se editan al seleccionar una sola primitiva. Los handles de figuras cerradas mantienen fijo el lado opuesto y siguen el puntero, también con rotación. Shift restringe las líneas a incrementos de 45°; sin Shift conservan el ángulo libre y sus extremos pueden ajustarse al borde del lienzo.

Los contornos expuestos se resaltan al pasar el mouse; clic cerca de una cara o la herramienta Contorno abre su condición. También se pueden elegir desde la lista de subsegmentos y los botones de lados del lienzo. El editor ofrece overlays de máscara, k y fuente, mensajes inline y confirmación al cancelar cambios. Ocultar una capa solo afecta el dibujo de su primitiva, no sus roles físicos ni el overlay derivado.

La carga acepta v1 y v2; el guardado siempre escribe v2. Las máscaras v1 se conservan como capas rasterizadas con edición limitada. Python rechaza v2 hasta la fase 2. Ver [contrato compartido](SCENE_FORMAT.md) y [ejemplo](examples/escena_cobre_v2.json).

**Curvas:** no se garantiza convergencia del balance Robin al círculo ideal sin ponderación geométrica. El documento de formato registra el sesgo de perímetro y el ensayo de refinamiento; se conserva el esquema escalonado solicitado.

Pruebas: `swift test`. Compilación, firma y apertura: `bash crear_app.sh`. La equivalencia completa con Python/OpenCL sigue pendiente de una campaña específica.
