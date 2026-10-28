# YoguiCuentas: estado actual y base para el informe técnico

**Ampliación vigente, 26/10/2026 · 0.2.0:** CN por incrementos y arranque Rannacher, CPU interactivo consultable/OpenCL, escenas editables JSON v2 con roles componibles, fuentes de línea y contornos por tramo, escala automática con reducción GL de cuatro escalares, curvas triangulares y rótulos en °C. Los detalles y las diferencias respecto al estado histórico están en [PARIDAD_METAL.md](PARIDAD_METAL.md). Los criterios físicos de conservación y el sesgo de la máscara escalonada siguen vigentes. La nueva verificación ejecutó 138 pruebas: 136 aprobadas y dos omisiones por bloqueo de escritorio, registro `resultados/paridad_metal/pruebas_release_020_final.log`.

**Actualización de presentación, 26/10/2026:** barra lateral desplazable, selector de escenarios y capas independientes de vectores/isotermas en los fondos existentes. Las isotermas se obtienen de temperatura interpolada en GLSL con niveles de la escala térmica fija; no son una nueva discretización física. Se incluyen en PNG y no agregan descargas del campo por cuadro. Ver [PARIDAD_METAL.md](PARIDAD_METAL.md) y su registro de verificación. El operador, la estabilidad y los solvers de este informe se conservan.

**Fecha de revisión:** 23 de octubre de 2026.  
**Versión actual del paquete:** 0.2.0; la descripción histórica de partida corresponde a 0.1.0.  
**Alcance:** implementación local existente, revisada sobre el código fuente. Este documento describe funcionalidades implementadas; las propuestas futuras se identifican por separado.

## 1. Propósito y alcance físico

YoguiCuentas simula conducción de calor bidimensional, transitoria o hasta un criterio de estacionario, en materiales con propiedades constantes en el tiempo. La geometría se representa mediante una máscara de nodos activos dentro de una grilla cartesiana rectangular. La interfaz permite configurar escenarios, editar piezas y fuentes, ejecutar el cálculo en OpenCL y visualizarlo con OpenGL.

La ecuación implementada es:

\[
C(x,y)\,\frac{\partial T}{\partial t}
=\nabla\cdot\left(k(x,y)\nabla T\right)+Q(x,y),
\qquad C=\rho c_p.
\]

| Magnitud | Unidad y significado |
|---|---|
| Coordenadas y dimensiones | m |
| Tiempo | s |
| Temperatura mostrada | °C; diferencias de temperatura equivalentes a K |
| Conductividad `k` | W/(m·K), escalar isotrópica |
| Densidad `rho` | kg/m³ |
| Calor específico `cp` | J/(kg·K) |
| Capacidad volumétrica `C` | J/(m³·K) |
| Fuente volumétrica `Q` | W/m³; negativa representa extracción |
| Flujo `q = -k grad(T)` | W/m² |
| Coeficiente Robin `h` | W/(m²·K) |

Los balances integrados de la formulación 2D se expresan por unidad de espesor: potencia en W/m y energía en J/m. No se prescribe actualmente una tercera dimensión física en la configuración.

El interior del material sólo tiene conducción. La condición Robin representa un intercambio en el contorno con un ambiente prescrito; no se resuelve un fluido ni un campo de convección. Tampoco se incluyen radiación, cambio de fase, anisotropía ni propiedades dependientes de temperatura.

## 2. Funcionalidad disponible

| Área | Estado actual |
|---|---|
| Integración temporal | Euler explícito; referencia NumPy `float64` y kernel OpenCL `float32` |
| Ejecución | Consola o interfaz Tkinter; inicio manual, pausa, reanudación y reinicio |
| Duración | Tiempo final, ejecución indefinida o hasta estacionario |
| Ritmo | Multiplicadores del tiempo físico y máxima velocidad disponible |
| Materiales | Material base de catálogo o personalizado; regiones rectangulares con propiedades propias |
| Interfaz entre materiales | Promedio armónico, aritmético o geométrico de conductividades |
| Condiciones iniciales | Uniforme, sinusoidal y gaussiana |
| Fuentes | Aporte uniforme y múltiples fuentes constantes rectangulares/cuadradas o circulares |
| Geometrías base | Rectángulo, L, U, círculo y elipse |
| Edición geométrica | Exclusión/restauración de zonas rectangulares o elípticas |
| Contornos | Dirichlet, Neumann, adiabático y Robin de parámetros constantes |
| Visualización | Temperatura, superficie 3D, magnitud del gradiente, flujo y temperatura con flechas de flujo |
| Configuraciones | Guardar y cargar escenarios JSON |
| Captura | PNG del framebuffer y metadatos |
| Interoperabilidad | Buffer compartido CL/GL cuando funciona; transferencia mediante RAM como alternativa |

La actualización del 26/10/2026 incorpora Jacobi ponderado **estacionario directo**, con referencia CPU y kernel OpenCL; no es integración temporal implícita. No están implementados Gauss–Seidel ni Thomas–ADI. Crank–Nicolson se incorporó en 0.2.0 mediante sistemas de incrementos con tolerancia explícita y rechazo transaccional del lote. Tampoco la grabación de video, las funciones Robin arbitrarias, el mallado no estructurado o un agente VLM. El estacionario puede obtenerse por evolución explícita o por Jacobi directo; ver la actualización funcional de PARIDAD_METAL.md.

## 3. Arquitectura y responsabilidades

Las rutas siguientes son relativas a la raíz del proyecto.

```text
yoguicuentas/
├── app.py                       # consola, ejecución y exportación
├── launcher.py                  # arranque GUI/selector de dispositivo
├── portability.py               # diagnóstico del entorno
├── config/scenarios.py          # escenario, validación y JSON
├── model/
│   ├── grid.py                  # dimensiones y coordenadas
│   ├── materials.py             # catálogo de materiales
│   ├── regions.py               # campos de propiedades
│   ├── boundaries.py            # condiciones de contorno
│   ├── sources.py               # fuentes y fracciones de área
│   └── domain.py                # máscaras, geometrías y conectividad
├── numerics/
│   ├── reference/explicit.py    # referencia NumPy y caso analítico
│   ├── operators.py             # coeficientes conservativos y contornos
│   ├── steady.py                # residuo y validación estacionaria
│   └── visual_fields.py         # reconstrucciones de referencia
├── compute/
│   ├── device.py                # inventario y selección OpenCL
│   ├── buffers.py               # dos campos de temperatura privados
│   ├── scheduler.py             # ejecución CPU
│   ├── opencl_scheduler.py      # lotes, eventos, residuos y diagnóstico
│   └── kernels/explicit.cl      # evolución y reducción del residuo
├── simulation/
│   ├── controller.py            # avance en consola
│   ├── live.py                  # máquina de estados interactiva
│   └── playback.py              # relación tiempo físico/reloj
├── render/
│   ├── canvas.py                # contexto GL y coordinación del lienzo
│   ├── interop.py               # transporte compartido o mediante RAM
│   ├── mesh.py                  # malla gráfica y máscara
│   ├── renderer.py              # recursos GL y shaders
│   └── colorbar.py              # escala de colores
├── ui/                          # configuración, editor y ventana principal
└── capture/screenshots.py       # lectura diferida y codificación PNG
```

La configuración es la descripción física reproducible. El modelo la transforma en máscaras, campos y coeficientes. El scheduler sólo ejecuta operaciones numéricas; el controlador decide cuándo enviarlas y publicarlas. El transporte administra el recurso de presentación y su propiedad CL/GL. El renderer interpreta ese recurso y dibuja; Tkinter gestiona eventos y formularios.

La implementación actual utiliza módulos con nombres propios, no todos los módulos de la arquitectura originalmente propuesta. Por ejemplo, los diagnósticos OpenCL están en `opencl_scheduler.py`; no existe todavía un subsistema independiente de diagnóstico ni un trabajador de video.

## 4. Discretización espacial y temporal

### 4.1 Grilla y representación

Para `nx, ny >= 3`:

\[
\Delta x=L_x/(n_x-1),\qquad \Delta y=L_y/(n_y-1).
\]

Los campos tienen forma NumPy `(ny, nx)` y almacenamiento contiguo por filas. El índice lineal de los kernels es `p = y*nx + x`. El origen físico está en `(0,0)`; los objetos se definen en metros, no por índices de nodos.

La estructura de almacenamiento sigue siendo rectangular incluso para una L o una elipse. Una máscara determina los nodos activos. Los nodos excluidos conservan valores finitos, no evolucionan y no aportan a fuentes, balances o dibujo de la pieza. No se utiliza `k=0` como sustituto general de una cavidad: se anula explícitamente la conexión térmica con la región excluida.

La conectividad se define por caras cartesianas. Dos nodos que sólo se tocan diagonalmente no pertenecen necesariamente al mismo componente térmico.

### 4.2 Operador conservativo

La construcción de coeficientes combina diferencias sobre una red estructurada con balances sobre volúmenes duales nodales. El volumen por unidad de espesor es `dx*dy` en el interior, la mitad en un lado exterior y un cuarto en una esquina exterior.

Para una cara entre nodos activos se construye una conductancia común. En un segmento interior uniforme, un coeficiente direccional toma la forma:

\[
a_E = \frac{k_{P,E}}{C_P\Delta x^2}.
\]

La formulación completa incorpora el ancho dual y las condiciones de contorno. El intercambio por una cara es igual y opuesto en los balances energéticos de ambos nodos, aunque sus tasas de temperatura difieran si cambia `C`.

Las opciones para una interfaz de igual semidistancia son:

\[
k_h=\frac{2k_Pk_N}{k_P+k_N},\quad
k_a=\frac{k_P+k_N}{2},\quad
k_g=\sqrt{k_Pk_N}.
\]

El promedio armónico es la opción física por defecto para resistencias conductivas en serie. Los otros promedios permiten comparación experimental; no equivalen al mismo modelo de interfaz para un salto fuerte de material.

### 4.3 Paso explícito

El kernel aplica:

\[
T_P^{n+1}=T_P^n+\Delta t\left[
\sum_{N}a_{PN}(T_N^n-T_P^n)
-s_P(T_P^n-T_{ref})+f_P\right].
\]

`Tref` es la temperatura base inicial. El término `f` se construye con ese desplazamiento para mantener la misma ecuación física. Las diferencias de temperatura y el desplazamiento reducen cancelaciones entre temperaturas absolutas en precisión simple.

El kernel lee exclusivamente el campo actual y escribe el siguiente. La máscara evita actualizar nodos excluidos. Las condiciones Dirichlet se incorporan al campo inicial y al operador para preservar su valor prescrito.

### 4.4 Estabilidad

En un material homogéneo sin pérdidas adicionales, la condición habitual es:

\[
\alpha\Delta t(\Delta x^{-2}+\Delta y^{-2})\leq 1/2,
\qquad \alpha=k/C.
\]

La aplicación calcula una cota conservadora usando `k_max`, `C_min` y las pérdidas Robin exteriores:

\[
\Delta t_{lim}^{-1}=
\beta\frac{k_{max}}{C_{min}}(\Delta x^{-2}+\Delta y^{-2})+
\frac{2}{C_{min}}\left(\frac{h_{x,max}}{\Delta x}+\frac{h_{y,max}}{\Delta y}\right).
\]

`beta=2` normalmente y `beta=4` para una máscara no rectangular con Dirichlet interno o Robin interno con `h>0`. El segundo caso contempla una cota más restrictiva por la distancia reducida al corte. El paso automático es `safety*dt_limit`; un paso manual debe respetar el límite. También se comprueba la monotonía con los coeficientes y el redondeo `float32` al crear el scheduler OpenCL.

Al alcanzar un tiempo final se acorta el último paso. La velocidad visual nunca se obtiene aumentando arbitrariamente `dt`.

## 5. Condiciones de contorno

Se selecciona una condición independiente para cada lado del rectángulo exterior. Los cortes creados por la máscara tienen una condición interna global; todavía no se asignan tipos diferentes a cada segmento dibujado.

- **Dirichlet:** temperatura prescrita. Si confluyen temperaturas exteriores diferentes en una esquina se utiliza el promedio como convención numérica.
- **Neumann:** flujo saliente prescrito `q_out`; positivo extrae energía.
- **Adiabático:** flujo normal nulo.
- **Robin:** `q_out = h*(T_wall-T_amb)`, con `h` y ambiente constantes.

### 5.1 Robin exterior

La frontera exterior pasa por el nodo. Su volumen dual tiene semiancho normal. Para un lado normal a `x`, el aporte a la tasa es:

\[
-\frac{2h}{C\Delta x}(T_P-T_{amb}).
\]

No se agrega una resistencia de medio paso, porque en este caso el nodo está sobre la frontera.

### 5.2 Robin sobre una cara de la máscara

El corte está a media distancia entre el nodo activo y el excluido. Por lo tanto, la temperatura del nodo y la temperatura de pared no son idénticas. Se combinan la conducción hasta la cara y el intercambio Robin:

\[
h_{eff}=\left(\frac1h+\frac{d}{2k_P}\right)^{-1},
\qquad q_{out}=h_{eff}(T_P-T_{amb}).
\]

Con ancho dual normal `w_P`, el sumidero es `h_eff/(C_P*w_P)`. Para `h=0` se impone aislamiento; al crecer `h` el límite corresponde a una pared de temperatura prescrita situada a `d/2`.

En el mismo corte, Dirichlet utiliza `2k_P/(C_P*w_P*d)` como coeficiente de pérdida hacia la temperatura de pared. Neumann agrega `-q_out/(C_P*w_P)` a la tasa.

Estas expresiones describen las caras cartesianas de la máscara. En un círculo rasterizado no se calcula aún la normal continua exacta del círculo.

## 6. Materiales, fuentes y geometría editable

Los materiales de catálogo, por ejemplo Cu, Al y Ag, son valores constantes orientativos; para un informe experimental deben consignarse procedencia, temperatura de referencia y valores efectivos utilizados. La opción personalizada permite introducir `k`, `rho` y `cp`.

En v1 las regiones materiales son rectangulares y no se superponen. En v2 se usan las máscaras de primitivas/regiones delimitadas y prevalece la última coincidencia de material. Ambos reemplazan las propiedades de fondo donde corresponda. La parte no cubierta conserva el material base.

Las fuentes usan centro y dimensiones físicas. Su aporte nodal se calcula mediante fracciones de intersección de área con los volúmenes duales, incluyendo integración de fuentes circulares. Así se evita depender sólo de si el centro del nodo cae dentro de la fuente. Las fuentes superpuestas se suman. La máscara recorta su aporte sin redistribuir hacia otros nodos la potencia de la parte excluida. El escenario predeterminado utiliza `Q=0`.

Las bases circular y elíptica almacenan centro y radios físicos. La activación nodal se decide mediante la ecuación de la elipse. La pieza debe caber en el dominio exterior. Las bases L y U se parametrizan mediante fracciones de las dimensiones de la caja.

Las ediciones rectangulares o elípticas de exclusión/restauración se aplican en orden: una edición posterior puede modificar el efecto de otra anterior. El editor permite seleccionar fuentes y ediciones, mover, duplicar, copiar/pegar, eliminar, deshacer y ajustar valores numéricamente. Los cambios se validan antes de confirmar; no se modifica un buffer CL durante un paso.

El rayado `///` señala en el editor los contornos internos adiabáticos del lado excluido. Es una convención gráfica y no altera las propiedades térmicas.

**Límite geométrico importante:** la máscara produce un contorno escalonado. Las pérdidas Neumann/Robin se integran sobre esas caras cartesianas. Refinar nodos no garantiza por sí solo recuperar el intercambio de una curva ideal, porque también intervienen la longitud escalonada y las normales. Para ese objetivo se requiere una corrección geométrica, un método de celdas cortadas o una malla adaptada al contorno. El suavizado visual no corrige este error geométrico.

## 7. Memoria OpenCL: propiedad y ciclo de vida

### 7.1 Campos privados del solver

`compute/buffers.py` administra dos buffers CL de temperatura:

1. `current`: campo leído por el paso.
2. `next`: campo escrito por el paso.
3. Al encolar cada kernel se intercambian las referencias Python.

El intercambio de referencias no copia el campo. Una única cola **in-order** garantiza que los kernels vean los resultados de los anteriores, aun cuando las operaciones sigan pendientes en el dispositivo. El scheduler no permite un segundo lote hasta confirmar el anterior.

Hay además una copia CL del campo inicial para reiniciar mediante una copia dispositivo a dispositivo; no es necesario recompilar el kernel ni descargar el estado para reiniciar.

### 7.2 Inventario lógico de memoria numérica

Sea `N=nx*ny`. La asignación privada principal de OpenCL es:

| Recurso | Tamaño lógico |
|---|---:|
| Temperatura actual y siguiente | `8N` bytes |
| Temperatura inicial para reinicio | `4N` bytes |
| Seis campos: E, W, N, S, sumidero y forzamiento desplazado | `24N` bytes |
| Máscara activa `uint8` | `N` bytes |
| Pesos capacidad·volumen para residuo | `4N` bytes |
| Resultado de dos residuos escalares `float32` | `8` bytes |
| **Total privado principal CL** | **`41N+8` bytes** |

A esto se suman programa, eventos, memoria local de reducción, alineamiento y reservas del driver. Las matrices NumPy de configuración y la referencia CPU también ocupan RAM; el pico de inicialización puede superar el tamaño del estado permanente.

El buffer GL de presentación agrega `4N` bytes lógicos. Su envoltorio `cl.GLBuffer` no es otro campo de temperatura independiente. También existen buffers estáticos de malla, propiedades y máscara para los shaders, texturas auxiliares, framebuffer y recursos de captura.

En una máscara recortada la malla gráfica puede tener cinco vértices por volumen activo y doce índices. Con el formato actual de 40 bytes por vértice y cuatro bytes por índice, esto supone aproximadamente `248*N_activos` bytes sólo para vértices e índices. Por ello el coste de visualización puede superar el de las dos temperaturas; la grilla no debe dimensionarse usando únicamente `8N`.

Las comprobaciones preventivas de memoria son cotas prácticas; no constituyen una garantía de asignación del driver ni un inventario exacto de toda la VRAM.

## 8. Transferencia OpenCL–OpenGL

### 8.1 Qué se comparte realmente

`render/interop.py` crea un buffer GL de escalares `float32`, uno por nodo. Se expone a OpenCL mediante `cl.GLBuffer` y al shader mediante una **buffer texture** `GL_TEXTURE_BUFFER` de formato `GL_R32F`.

No se comparte una textura 2D mediante `cl.GLTexture`. Tampoco se recalculan en OpenCL posiciones de vértices para cada modo: las coordenadas de la malla son estáticas y el shader usa la temperatura para color o altura.

El solver mantiene privados sus dos campos. Al publicar, copia el campo calculado al buffer de presentación. La ruta compartida evita la descarga a CPU, pero **mantiene una copia dispositivo a dispositivo**. Por eso no debe describirse como ausencia absoluta de copias.

### 8.2 Inicialización y selección de transporte

Con el contexto GL actual se verifican:

1. Soporte GL en PyOpenCL: `cl.have_gl()`.
2. Extensión `cl_khr_gl_sharing` del dispositivo elegido.
3. Compatibilidad del dispositivo con el contexto GL mediante consulta de interoperabilidad.
4. Creación del contexto CL compartido y del envoltorio del buffer.
5. Prueba real de adquisición/liberación durante la inicialización.

`--transfer auto` intenta esa vía y, si no es viable, conserva el dispositivo de cálculo seleccionado y utiliza RAM. `--transfer shared` exige interoperabilidad y falla si no puede garantizarla. `--transfer host` fuerza la vía mediante RAM.

El inventario sin ventana no puede demostrar compatibilidad con un contexto GL que todavía no existe. La extensión anunciada tampoco basta: algunos drivers fallan al adquirir el objeto.

### 8.3 Secuencia de publicación compartida

```text
OpenGL termina de usar el buffer → fence GL
                 ↓ consulta sin espera bloqueante
OpenCL adquiere el objeto GL
                 ↓
copia current → buffer de presentación
                 ↓
OpenCL libera el objeto GL → evento CL
                 ↓ consulta hasta COMPLETE
OpenGL lee el buffer y dibuja
                 ↓
nuevo fence GL
```

El transporte utiliza `enqueue_acquire_gl_objects`, una copia dependiente de la adquisición y `enqueue_release_gl_objects` dependiente de la copia. Se envía la cola con `flush()`. El renderer sólo puede dibujar cuando el evento de liberación terminó.

Después del dibujo se inserta `glFenceSync`; antes de volver a adquirir se consulta con espera de duración cero. La aplicación mantiene como máximo una publicación pendiente sobre ese recurso. Esta propiedad evita lecturas y escrituras concurrentes no definidas.

`glFinish()` aparece en la prueba inicial y en liberación/reconfiguración de recursos; no es la sincronización utilizada para cada frame. La liberación final espera los recursos antes de destruirlos, con un contexto GL válido.

### 8.4 Alternativa mediante RAM

La ruta `HostTemperature` conserva un arreglo NumPy `float32` y un buffer GL:

```text
current CL → copia no bloqueante a RAM → evento CL
          → fence GL disponible → glBufferSubData → dibujo
```

La publicación se limita por defecto a unas 30 actualizaciones por segundo. Si conviene, se omiten imágenes intermedias y se sigue calculando; no se eliminan pasos físicos. La imagen final, la pausa y el reinicio deben quedar publicados.

Esta ruta permite utilizar dispositivos sin `cl_khr_gl_sharing`, incluidas iGPU compatibles con el resto de requisitos. No garantiza el mismo rendimiento entre fabricantes. El arreglo NumPy no implica memoria fijada ni solapamiento DMA garantizado; la subida GL también puede tener un coste perceptible.

### 8.5 Recuperación ante fallo tardío

En modo automático, un fallo de adquisición CL/GL anterior a la transferencia de propiedad puede activar la alternativa mediante RAM. Se recupera el último campo presentado desde GL, se cambia el transporte y se mantiene el estado privado del scheduler, con su tiempo y pasos.

La recuperación no oculta cualquier excepción de OpenCL: un error posterior durante copia o liberación requiere tratar la propiedad del recurso con cuidado y no se convierte indiscriminadamente en un cambio de transporte.

## 9. Control del cálculo y respuesta de Tkinter

`simulation/live.py` administra inicio, pausa, reinicio, lote pendiente, publicación y pasos realmente visibles. La aplicación arranca detenida. La pausa deja terminar el lote enviado antes de quedar en reposo; no cancela un kernel a mitad de ejecución.

El hilo principal conserva el contexto GL y atiende Tkinter. Las consultas periódicas del lienzo comprueban eventos y envían trabajo; los kernels se ejecutan de forma asíncrona en el dispositivo. No se utiliza un hilo Python para hacer los pasos numéricos ni se llama a `queue.finish()` en cada actualización.

Este diseño evita esperas deliberadas en el bucle normal, aunque Python todavía paga el coste de encolar cada kernel y el driver puede introducir latencias. Un lote enorme puede perjudicar la interacción. El tamaño de lote es un compromiso entre coste de envío, frecuencia de publicación y latencia de pausa.

El controlador diferencia pasos calculados de pasos publicados. La información asociada a una captura corresponde al estado visible, no simplemente al último kernel encolado.

Los multiplicadores de reproducción regulan cuántos pasos se autorizan según el reloj y el tiempo físico. Si el equipo no alcanza la velocidad solicitada, se muestra la velocidad efectiva. La opción máxima depende del hardware. El modo estacionario utiliza máxima velocidad y su propio criterio de parada.

Al aplicar una configuración se espera un punto seguro, se reconstruyen coeficientes y recursos dependientes de la geometría y se vuelve al estado inicial detenido. Actualmente no hay un contrato general de parches físicos incrementales aplicados a buffers existentes durante una corrida.

## 10. Renderizado científico

El lienzo es `pyopengltk.OpenGLFrame`, embebido en Tkinter. El camino probado usa OpenGL de escritorio y shaders GLSL 1.40; el requisito operativo documentado para la GUI es OpenGL 3.2 o superior sobre Linux con X11/XWayland.

La malla gráfica contiene posición, cuatro índices de muestras y pesos de interpolación. En un rectángulo completo se utiliza la triangulación nodal. Para una máscara recortada se dibujan los volúmenes activos con centro y esquinas; la interpolación utiliza muestras activas conectadas localmente por caras. No se extienden triángulos a través de los huecos de la pieza.

Los shaders leen temperatura, coeficientes de caras, máscara y conductividad nodal desde recursos GL. Color, altura y reconstrucciones se obtienen en GPU; no se descarga el campo completo para generar cada imagen.

| Modo | Interpretación |
|---|---|
| Mapa de temperatura | Color asociado a T |
| Superficie 3D | Altura asociada a T, con cámara e iluminación |
| Gradiente | Magnitud de grad(T), en K/m |
| Flujo | Magnitud reconstruida de q, en W/m², y dirección con flechas |
| Temperatura + flujo | Color de T y flechas de dirección de q |

Las flechas tienen longitud simbólica: no son una escala cuantitativa de magnitud. El flujo nodal reconstruido tampoco es idéntico al flujo de cada cara del balance. Cerca de una pared aislada, una flecha reconstruida puede contener una componente normal proveniente de caras interiores sin que exista transferencia a través de la pared. Para verificar conservación debe examinarse el balance de caras, no sólo la apariencia de las flechas.

La escala de color se inicia a partir del campo inicial efectivo y puede ajustarse. No se recalcula mediante una descarga completa en cada frame. El menú **Ver** permite mostrar u ocultar la barra; al activarla se reserva espacio lateral y se conserva la proporción del área física.

La barra se dibuja en el mismo framebuffer. Su textura de etiquetas y gradiente sólo se regenera al cambiar tamaño, escala o modo. Por ello aparece también en la captura. Las preferencias de cámara o visibilidad de la barra son estado de presentación, no toda la configuración física serializada.

## 11. Estacionario: criterio y límites

El residuo evalúa el balance estacionario dividido por capacidad, en K/s. No usa exclusivamente `T(n+1)-T(n)`, que podría parecer pequeño sólo por elegir un paso temporal pequeño.

Sean `r_P` las tasas residuales y `w_P=C_P*V_P` para nodos activos libres:

\[
R_\infty=\max_P|r_P|,\qquad R_1=\sum_P w_P|r_P|.
\]

Se requieren simultáneamente:

\[
R_\infty\leq a_{tol}+r_{tol}R_{\infty,0},
\qquad
R_1\leq a_{tol}\sum_Pw_P+r_{tol}R_{1,0}.
\]

La referencia inicial se mantiene fija. Los nodos de temperatura exterior prescrita no aportan grados de libertad al balance; también se consideran componentes aislados de uno o pocos nodos.

Los valores predeterminados son `rtol=1e-5`, `atol=1e-5 K/s`, comprobación cada 128 pasos, tres confirmaciones y máximo de 1 000 000 de pasos. Llegar al máximo no se informa como convergencia.

OpenCL reduce el residuo con un grupo de trabajo que recorre el campo por tramos y descarga sólo dos escalares por comprobación. Es un mecanismo simple y verificable; para grillas grandes la reducción con un solo grupo es una oportunidad de optimización.

Se verifica además la compatibilidad por componente conectado: una pieza sin Dirichlet ni Robin disipativo no puede tener un aporte neto de calor distinto de cero y alcanzar un estado estacionario. Con aislamiento y balance neto cero puede existir una familia de soluciones; la energía inicial fija la media durante el transitorio.

El criterio está basado en residuos de balance, en el espíritu de una formulación conservativa. No constituye un único umbral universal atribuible a Patankar ni una cota automática del error de temperatura. La precisión simple puede imponer una meseta residual; tolerancias demasiado exigentes deben producir parada por límite, no una convergencia ficticia.

## 12. Capturas y diagnóstico

La captura PNG solicita una lectura RGB del framebuffer hacia un PBO, inserta un fence y consulta su finalización. Una vez disponible se transfiere a CPU y se codifica con Pillow en un trabajador dedicado. La lectura final a RAM sigue teniendo coste; el objetivo es diferir la espera y sacar la compresión del hilo gráfico.

Los metadatos de captura incluyen tiempo/paso visible, modo, escala, barra de colores, cámara y velocidad solicitada/efectiva. La grabación continua de video todavía requiere un subsistema propio de cola, descarte y cierre.

El scheduler registra dispositivo, opciones y log de compilación, tiempo de eventos, esperas y descargas explícitas. El acumulador llamado `kernel_s` puede incluir eventos adicionales del control de residuo; no debe interpretarse sin más como tiempo puro de evolución ni como tiempo total de aplicación.

## 13. Reproducción en otra estación

### 13.1 Requisitos

- Linux, Python 3.10 o posterior, Tkinter y soporte de entornos virtuales.
- Runtime/ICD OpenCL del fabricante del dispositivo de cálculo.
- Driver OpenGL y sesión gráfica `DISPLAY` para la GUI.
- Compatibilidad GL/CL adicional sólo si se desea transferencia compartida.

El instalador prepara paquetes Python, pero no instala ni cambia drivers. En Debian, los paquetes básicos de sistema se instalan como administrador; no se presupone que exista `sudo`:

```bash
su -
apt update
apt install python3-venv python3-tk
exit
```

El runtime OpenCL y el driver GL deben elegirse según la estación. Una iGPU no queda descartada por carecer de interoperabilidad: puede funcionar con `--transfer host`.

### 13.2 Preparar y comprobar el entorno

Desde la carpeta del proyecto:

```bash
bash instalar.sh
bash instalar.sh --comprobar
bash ejecutar.sh --list-devices
```

Si el entorno existe pero le falta `pip`:

```bash
bash instalar.sh --preparar-entorno
bash instalar.sh
```

El instalador verifica que sea un entorno virtual real e intenta reparar `pip` mediante `ensurepip`. Si Debian no dispone del soporte correspondiente, debe instalarse `python3-venv` o el paquete de la versión de Python utilizada.

Para intentar una compilación local de PyOpenCL con soporte GL:

```bash
bash instalar.sh --recompilar-opencl
```

Esta opción requiere compilador y cabeceras de desarrollo indicadas en [PORTABILIDAD.md](PORTABILIDAD.md). No soluciona por sí sola la ausencia de `cl_khr_gl_sharing` en el driver.

`YOGUI_PYTHON` permite elegir Python y `YOGUI_VENV` la ruta del entorno. El instalador deja el inventario de paquetes en `.venv-portable/requisitos-instalados.txt`.

### 13.3 Abrir y comparar transportes

```bash
bash ejecutar.sh --scenario scenarios/pieza_eliptica.json --transfer auto
bash ejecutar.sh --scenario scenarios/pieza_eliptica.json --transfer host
```

En equipos con varias GPU se puede elegir al abrir o indicar el índice enumerado:

```bash
bash ejecutar.sh --device 1 --transfer shared
```

El índice `1` identifica la A2000 en la estación de desarrollo, pero no debe suponerse en otra máquina. La GPU que presenta el contexto GL puede ser distinta del dispositivo CL; en ese caso el modo automático puede necesitar RAM.

`ejecutar.sh` elimina `CUDA_VISIBLE_DEVICES` del entorno de ejecución y valida el entorno Python. La sintaxis de eliminación es `env -u CUDA_VISIBLE_DEVICES`, sin `=1`. La aplicación usa OpenCL, incluso si el nombre de la plataforma de NVIDIA contiene la palabra CUDA.

### 13.4 Consola reproducible

La entrada directa del paquete es de consola; no existe un `main.py` que deba usarse en las instrucciones actuales:

```bash
.venv-portable/bin/python -m yoguicuentas \
  --scenario scenarios/cobre_seno.json --backend numpy \
  --steps 1000 --batch-size 128 --output resultados_informe/cpu

.venv-portable/bin/python -m yoguicuentas \
  --scenario scenarios/cobre_seno.json --backend opencl --device 1 \
  --steps 1000 --batch-size 128 --output resultados_informe/opencl

.venv-portable/bin/python -m yoguicuentas \
  --scenario scenarios/estacionario.json --backend opencl --device 1 \
  --steady --output resultados_informe/estacionario
```

También puede utilizarse `bash ejecutar.sh --console` con los mismos parámetros. La consola NumPy no necesita crear un contexto GL. La GUI actual utiliza OpenCL; no cambia silenciosamente al solver NumPy cuando falta el runtime.

Cada ejecución de consola exporta:

| Archivo | Contenido |
|---|---|
| `scenario.json` | Parámetros efectivos reproducibles |
| `temperature.npy` | Temperatura rectangular, `float64` CPU o `float32` CL |
| `active_mask.npy` | Máscara que debe aplicarse al analizar la temperatura |
| `report.json` | Pasos, tiempo, dt, límites, extremos activos y diagnósticos disponibles |

Los valores almacenados fuera de la máscara no son temperatura física de una cavidad. Para comparar resultados se deben seleccionar los nodos activos y usar el mismo escenario y tiempo efectivo. En el caso sinusoidal compatible, el informe incluye error respecto a la solución analítica.

### 13.5 Qué conservar para un informe reproducible

Conservar el código fuente exacto, escenario exportado, informe JSON, matriz y máscara, captura con escala y metadatos, inventario de paquetes y salida del diagnóstico del dispositivo. Registrar sistema operativo, driver GL/OpenCL, GPU de cálculo y GPU de presentación, resolución, tamaño de lote, transporte efectivo y criterio de parada.

La carpeta revisada no dispone de una identificación de commit Git utilizable. Hasta incorporar control de versiones, conviene archivar el árbol fuente junto con sus sumas SHA-256. La versión `0.1.0` por sí sola no identifica todas las modificaciones locales.

No se debe copiar `.venv-portable` entre estaciones: se copian código y escenarios y se recrea el entorno. Las versiones parcialmente abiertas de `requisitos.txt` no forman un bloqueo completo de dependencias; guardar el inventario instalado permite identificar la combinación realmente utilizada.

Versiones observadas durante esta revisión documental:

| Componente | Versión local |
|---|---|
| Python | 3.11.2 |
| NumPy | 2.4.6 |
| PyOpenCL | 2026.1.2 |
| PyOpenGL | 3.1.10 |
| pyopengltk | 0.0.4 |
| Pillow | 12.3.0 |

Estas versiones describen la estación revisada; no garantizan igualdad de drivers ni de resultados bit a bit entre dispositivos. El orden de las reducciones y la aritmética del compilador pueden producir diferencias pequeñas.

## 14. Validación y metodología de evaluación

La suite cubre referencia explícita, condiciones de borde, energía, regiones y fuentes, máscaras y componentes, estacionario, reproducción temporal, transporte, edición y configuración visible, captura y renderizado.

Entre las comprobaciones relevantes se encuentran perfiles de contorno, solución sinusoidal, conservación ponderada por capacidad, integración de fuentes, resistencia Robin en cortes, comparación CPU/OpenCL y exclusión gráfica de zonas inactivas. Hay pruebas de interoperabilidad y de recuperación ante fallo de adquisición, además de pruebas de los cinco modos gráficos y de la barra de colores.

En la validación completa previa registrada durante el desarrollo se ejecutaron **104 pruebas con resultado satisfactorio en la A2000**. Posteriormente se verificaron cinco pruebas dirigidas de geometrías curvas tras un ajuste menor de sus controles. Estos antecedentes no sustituyen una nueva ejecución en cada estación; en esta revisión documental se inspeccionaron fuentes y versiones, sin repetir toda la batería GPU.

Comando para repetir la batería completa con pruebas GL habilitadas:

```bash
env -u CUDA_VISIBLE_DEVICES YOGUI_TEST_DEVICE=1 YOGUI_TEST_GL=1 \
  .venv-portable/bin/python -m unittest discover -s tests -v
```

Debe reemplazarse el índice por el dispositivo apropiado. Las pruebas que requieren capacidades gráficas o dispositivos no disponibles pueden omitirse; un resultado con omisiones no demuestra compatibilidad GPU/GL. La salida completa de la suite debe acompañar el informe de validación.

Para evaluar rendimiento hay que separar:

1. Compilación e inicialización.
2. Tiempo de evolución sin renderizado.
3. Coste de publicación compartida o mediante RAM.
4. Dibujo y frecuencia visible.
5. Capturas y operaciones de exportación.

Comparar estaciones con el mismo escenario, tolerancias, precisión, número de nodos activos y modo de transferencia. Reportar pasos/s, tiempo físico simulado/s, latencia de interacción y coste de memoria. No hay aquí una campaña controlada de rendimiento A2000/RX 550/iGPU, por lo que no se atribuyen aceleraciones numéricas generales.

El caso sinusoidal rectangular sirve para estudiar error temporal y espacial sin mezclarlo con error de geometría. Las piezas curvas necesitan además una validación específica de perímetro, normal y flujo integrado; una imagen suave no acredita exactitud del contorno.

## 15. Riesgos técnicos y siguientes desarrollos

| Riesgo o límite | Medida actual / siguiente trabajo |
|---|---|
| Compartición anunciada pero defectuosa | Prueba real de acquire/release y alternativa RAM |
| Carreras entre GL y CL | Propiedad explícita, eventos CL y fences GL |
| Lotes demasiado largos | Control de lote y publicación; medir latencia antes de aumentar tamaño |
| Restricción CFL al refinar la red | Validación del paso; futuro solver implícito conservando el mismo operador |
| Saturación de residuo en `float32` | Tolerancias explícitas, límite de pasos y diagnóstico de parada |
| Contornos curvos escalonados | Documentar error; futura geometría de caras o malla adaptada |
| Flechas interpretadas como flujo de pared | Distinguir reconstrucción nodal y balance conservativo por cara |
| Malla gráfica costosa | Medir memoria y considerar representación compacta/instanciada |
| Reducción estacionaria poco paralela | Futuro esquema de reducción en varias etapas |
| Escenarios/versiones insuficientemente identificados | Archivo de fuentes, versiones y futuro control de versiones |
| Drivers y backend gráfico diferentes | Diagnóstico por estación; no asumir portabilidad binaria del entorno |

Las siguientes etapas pueden introducir un solver implícito sin cambiar el contrato físico del escenario, ampliar contornos internos por segmentos, mejorar el tratamiento geométrico de curvas y agregar video. El contrato de publicación CL/GL debe seguir independiente del método numérico: el renderer necesita un campo coherente y disponible, no conocer cómo se obtuvo.

## 16. Mapa de fuentes para ampliar el informe

- Modelo y serialización: [config/scenarios.py](yoguicuentas/config/scenarios.py).
- Ensamblado espacial y contornos: [operators.py](yoguicuentas/numerics/operators.py).
- Referencia: [explicit.py](yoguicuentas/numerics/reference/explicit.py).
- Kernel: [explicit.cl](yoguicuentas/compute/kernels/explicit.cl).
- Lotes y memoria CL: [opencl_scheduler.py](yoguicuentas/compute/opencl_scheduler.py) y [buffers.py](yoguicuentas/compute/buffers.py).
- Propiedad y publicación CL/GL: [interop.py](yoguicuentas/render/interop.py).
- Orquestación interactiva: [live.py](yoguicuentas/simulation/live.py).
- Renderizado y malla: [renderer.py](yoguicuentas/render/renderer.py) y [mesh.py](yoguicuentas/render/mesh.py).
- Residuo y compatibilidad estacionaria: [steady.py](yoguicuentas/numerics/steady.py).
- Geometría y fuentes: [domain.py](yoguicuentas/model/domain.py) y [sources.py](yoguicuentas/model/sources.py).
- Portabilidad: [PORTABILIDAD.md](PORTABILIDAD.md), [instalar.sh](instalar.sh), [ejecutar.sh](ejecutar.sh) y [requisitos.txt](requisitos.txt).
- Casos reproducibles: [scenarios/](scenarios/). Validación: [tests/](tests/).

Este mapa permite vincular las decisiones del informe con la implementación concreta y actualizar el documento cuando cambien el operador, el transporte o el esquema temporal.

## Actualización funcional del 26/10/2026: Jacobi y CSV

Jacobi aplica `T_new = T_old + (2/3) D^{-1} r(T_old)` en nodos libres, con `D = aE+aW+aN+aS+sink` y el mismo residuo conservativo por diferencias. Los nodos Dirichlet e inactivos se conservan. El kernel OpenCL C 1.1 reutiliza los dos campos privados y los coeficientes existentes; no añade matriz densa ni una copia a CPU por iteración. La referencia NumPy usa float64. La convergencia sigue exigiendo máximo y suma absoluta integrada durante las confirmaciones indicadas, y el límite se interpreta como iteraciones. Cada componente necesita referencia Dirichlet o Robin con h>0. Las familias Neumann compatibles se mantienen disponibles mediante evolución explícita, sin inventar una referencia para el solver directo.

Las iteraciones directas carecen de tiempo físico. `steady_method=jacobi` se conserva en JSON v1; los archivos anteriores usan `explicit`. UI e informes distinguen iteración, iteraciones/s y tiempo físico ausente. El CLI acepta `--steady-method jacobi`. La exportación puntual CSV usa el campo publicado y su máscara; escribe coordenadas SI, temperatura, actividad y paso/tiempo o iteración. Se realiza lectura explícita GL→RAM y codificación en trabajador con reemplazo atómico; no se introduce una lectura por cuadro.

Verificación nueva: soluciones analíticas y eliminación matricial independiente con fuente/materiales/bordes mixtos, máscara Robin, componentes sin referencia, límite/convergencia, persistencia, independencia de dt, CPU/OpenCL, reinicio y exportación del campo visible. Evidencia y conteo final en PARIDAD_METAL.md.

Verificación final del segundo avance: **116 pruebas, OK, 0 omisiones, 61,832 s**, GPU NVIDIA RTX A2000, índice OpenCL 1. Suite con GPU y GL habilitados; registro completo en `resultados/paridad_metal/pruebas_jacobi_csv_layout.log`. Incluye las nuevas pruebas de layout/hit-testing 3D (con subcasos explícito/Jacobi), siete de Jacobi y tres de exportación CSV, además de la batería previa.

## Ampliación 0.2.0: implementación y límites comprobados

CN resuelve `(I + θ dt A) δ = dt (f − A T)` y forma `T+δ`, con θ=1/2. El arranque opcional usa θ=1 en dos medios pasos del primer paso físico. CPU acumula en float64; OpenCL usa float32, buffers residentes de candidatos/incrementos/RHS y máximos residuales por grupos. El lote privado no se sustituye ni se confirma hasta que todos sus sistemas convergen; la cancelación se observa entre controles. La tolerancia absoluta interna está en K y no mide error temporal. Las pruebas verifican orden 2 con un modo propio discreto, oscilación de alta frecuencia, amortiguación del arranque, matriz independiente, conservación y fallo/cancelación sin cambio de campo confirmado.

CN agrega cinco campos float32 (`20N` bytes) y residuos parciales por grupos a la memoria numérica histórica; no confundir el inventario de Euler con el de CN. El renderer agrega cuatro condiciones RGBA32F por nodo (`64N` bytes), además de puntos de fuente, atlas de texto y framebuffers auxiliares. El coste geométrico de isotermas escala con niveles × triángulos, y sus lecturas de extrema/anclajes sincronizan GL. No se descarga el campo completo para esas funciones, pero no se promete coste nulo ni igual fluidez en todas las grillas.

La escena v2 conserva geometría física, IDs, orden y roles. Los separadores bloquean conectividad solo para identificar regiones; no perforan por sí solos una franja. El operador conduce entre nodos activos y aplica condiciones por cara expuesta, con la misma resistencia de medio paso para Robin interno. Área v2 usa 8×8 muestras por volumen dual; línea usa Liang–Barsky con celdas semiabiertas y profundidad de referencia 1 m. El parser no utiliza `derived`. La migración al editor conserva máscara/intervalos materiales heredados, pero no afirma igualdad exacta de las fuentes analíticas v1 con el muestreo v2.

Las comparaciones con el ejemplo Metal `trapecio_fuente_v2` reproducen 2535 nodos activos, 102 nodos con fuente, potencia 50287,24670410156 para profundidad de referencia 1 m y máximo final cercano a 95,21 °C. La comparación CPU/OpenCL utiliza tolerancias explícitas, no igualdad de bits. Estos ensayos no sustituyen una campaña de todas las escenas, drivers ni un experimento físico.

El bloqueo del escritorio impidió dos comprobaciones nuevas de hit-testing nativo. Se mantuvieron sus omisiones identificadas y se ejecutaron las pruebas de framebuffer, eventos programáticos del editor, CPU/GPU y transporte. Las capturas del framebuffer sí se inspeccionaron; no equivalen a una revisión completa de la ventana nativa.
