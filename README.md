# YoguiCuentas

## Versión 0.2.4 — escala, isotermas, CN y escenas editables

La ventana se identifica como **YoguiCuentas OpenCL · 0.2.4**. Resumen vigente: [PARIDAD_METAL.md](PARIDAD_METAL.md). Los apartados históricos siguientes describen también etapas v1; este resumen y ESTADO_PROYECTO.md prevalecen para las funciones nuevas.

YoguiCuentas es un proyecto educativo de simulación de transferencia de calor, con una edición OpenCL para Linux y una edición Metal para macOS.

El código y la documentación se distribuyen bajo [Apache License 2.0](LICENSE); [NOTICE](NOTICE) aclara el alcance y los permisos independientes del nombre y del icono.

El [informe técnico de YoguiCuentas Metal 0.11.0](metal/technical_report/informe_tecnico_yoguicuentas_metal.pdf) está disponible para lectura. En [metal/technical_report](metal/technical_report/README.md) se incluyen su fuente LaTeX, datos, instantánea de las fuentes analizadas y pasos para reproducirlo. La versión OpenCL y la versión Metal llevan numeración propia.

## Descargar e instalar

Los instaladores están en [Releases](https://github.com/javoxa/YoguiCuentas/releases/latest). Elegí el archivo según tu sistema. No hace falta descargar el código fuente para usar la aplicación.

Si la página todavía no muestra una Release, abrí la pestaña [Actions](https://github.com/javoxa/YoguiCuentas/actions): el primer paquete aparece cuando termina correctamente **Build release packages** para la etiqueta `v0.2.4`.

### Debian / Devuan

1. En **Assets**, descargá `yoguicuentas_0.2.4_all.deb`.
2. Abrí una terminal en la carpeta donde quedó el archivo, normalmente `Descargas`:

   ```bash
   cd ~/Descargas
   sudo apt update
   sudo apt install ./yoguicuentas_0.2.4_all.deb
   ```

   El `.deb` no se extrae manualmente. APT lo instala y resuelve las dependencias del sistema; durante la primera instalación también hace falta Internet para instalar las dependencias Python.
3. Abrí **YoguiCuentas** desde el menú de aplicaciones o ejecutá `yoguicuentas` en una terminal. El lanzador elige una GPU OpenCL si hay una disponible; si no, inicia con CPU.

Si tu Debian/Devuan no tiene `sudo`, entrá como administrador con `su -` y ejecutá `apt install /home/USUARIO/Descargas/yoguicuentas_0.2.4_all.deb`, reemplazando `USUARIO` por tu nombre de usuario.

### macOS (Apple Silicon)

1. En **Assets**, descargá `YoguiCuentas_Metal_macOS_arm64.zip`. Requiere macOS 13 o posterior en una Mac con procesador Apple Silicon (M1 o posterior).
2. En Finder, abrí **Descargas** y hacé doble clic en el ZIP. macOS extraerá `YoguiCuentas Metal.app`.
3. Arrastrá la app extraída a **Aplicaciones** y abrila desde allí.

La app está firmada localmente, pero no notarizada por Apple. Si macOS bloquea la primera apertura, seguí el apartado [“Si macOS bloquea la primera apertura”](metal/yoguicuentas_metal/INSTALACION_APPLE_M1.md#si-macos-bloquea-la-primera-apertura).

La Release también ofrece el informe PDF y `SHA256SUMS` para verificar los archivos descargados.

- **Escala y cámara → Escala automática** sigue el campo visible. **Ajustar ahora** encuadra una vez. En la barra de colores: rueda para ampliar/reducir, arrastre de extremos para límites, arrastre del centro para desplazar y doble clic para encuadrar. El ajuste manual desactiva automático.
- **Superposiciones → Isotermas** usa N niveles entre las temperaturas activas actuales, independientemente del color de fondo. **Temperatura de las isotermas (°C)** muestra rótulos con separación y líneas guía. Se incluyen en PNG y funcionan en 3D. N son niveles: puede haber varias curvas por nivel, y un campo uniforme no tiene curvas.
- **Nodos con fuente** muestra el aporte aplicado, con nodos libres y potencia en la información. No representa el borrador del editor.
- **Configurar corrida… → Integración** permite Euler explícito o Crank–Nicolson, factor de paso, tolerancias del sistema y arranque suavizado. CN rechaza el lote completo si no converge. Comparar dt/2 y dt/4 para precisión; los pasos grandes pueden oscilar.
- **Cálculo → Procesador** alterna CPU NumPy y GPU OpenCL; el cambio reinicia y deja detenido. CPU calcula en un trabajador. La referencia es float64 y la visualización float32.
- **Editar escena…** permite figuras rotadas, líneas, polígonos, mano alzada, regiones delimitadas y roles de dominio/material/fuente/contornos por tramo. La lista permite recuperar figuras ocultas o bloqueadas. Hay handles, vértices/puntos medios, selección múltiple, copia/duplicado, orden e historial.
- La carga admite **JSON v1 y v2**. Las escenas editables se guardan en v2 de forma atómica. Las fuentes v2 usan áreas 8×8 y líneas W/m; al migrar una fuente v1 puede variar su discretización de área. Abrir/cancelar el editor no sustituye la corrida ni el archivo original.
- La versión conserva Jacobi estacionario directo, PNG y exportación CSV del campo visible.

Ejemplos nuevos del selector: **cn animacion**, **cn oscilaciones**, **trapecio fuente v2**, **trapecio bordes v2**, **corte regiones v2** y **escena cobre v2**.

```bash
bash ejecutar.sh --device 1
bash ejecutar.sh --device 1 --processor cpu
bash ejecutar.sh --console --backend opencl --device 1 --scenario scenarios/cn_animacion.json --steps 20 --output resultados/cn_nueva
```

Validación final: **138 pruebas ejecutadas: 136 aprobadas y 2 omitidas por sesión gráfica bloqueada** (hit-testing nativo), en A2000. Registro: `resultados/paridad_metal/pruebas_release_020_final.log`. Las pruebas de kernels, framebuffer, conteo real de curvas, escenas/editor y CPU/GPU sí se ejecutaron. [Captura del trapecio con 12 isotermas](resultados/paridad_metal/visuales/trapecio_12_isotermas.png).


## Menú accesible, Jacobi y CSV — 26/10/2026

Se corrigió la barra lateral que quedaba reducida a 47 px: ahora tiene una columna de 320 px y OpenGL se aloja en un contenedor separado. El pie de estado se reserva antes del área de contenido para que siga visible al reducir la ventana. Se verifica el acceso por clic a parámetros con 3D activo en ventanas 1150×820, 900×620 y 720×420.

**Configurar corrida… → Grilla y tiempo → Hasta estacionario → Estacionario → Método → Estacionario directo · Jacobi** resuelve el operador conservativo mediante Jacobi ponderado (ω=2/3), en CPU de referencia y OpenCL C 1.1. Aplicar y después Iniciar. También está disponible el escenario **estacionario jacobi**. Las iteraciones no representan tiempo físico: se muestran iteraciones/s, sin dt ni velocidad física. Cada componente necesita Dirichlet o Robin con h>0; el modo explícito anterior conserva su tratamiento de componentes aisladas compatibles. Las tolerancias son del residuo en K/s y W/m de espesor, y no se relajan automáticamente. Alcanzar el límite no significa converger. Esto no incorpora CN ni un integrador temporal implícito.

```bash
bash ejecutar.sh --console --backend opencl --device 1 --steady-method jacobi --output resultados/jacobi
```

**Exportar campo CSV…**, también en Archivo, guarda el próximo campo visible disponible, con coordenadas en m, temperatura en °C, máscara activa y paso/tiempo o iteración. Las filas inactivas tienen temperatura vacía. La lectura de GL ocurre una vez por exportación explícita; la codificación se realiza en un trabajador y se reemplaza el destino de forma atómica. La consola también exporta `temperature.csv`. En Jacobi `time_s` y `dt_s` del informe son null, y el CSV deja vacíos paso y tiempo físico.

## Avance hacia Metal — 26/10/2026

La ventana OpenCL tiene barra lateral desplazable, selector de escenarios, icono compartido con Metal y sección **Superposiciones** contraída al abrir. Permite activar vectores e isotermas independientemente del fondo, incluso en 3D; editar densidad/cantidad; incluirlas en PNG. Las isotermas usan la escala térmica manual y todavía no tienen rótulos. Esa etapa conservaba Euler y JSON v1; la versión 0.2.0 descrita arriba incorpora CN y escenas v2. Alcance y siguientes etapas: [PARIDAD_METAL.md](PARIDAD_METAL.md).

Para instalar en una estación nueva: `bash instalar.sh` y luego
`bash ejecutar.sh`. El archivo de dependencias es `requisitos.txt`.
Ver [PORTABILIDAD.md](PORTABILIDAD.md) para drivers, selección de GPU y diagnóstico.
Para instalar en varias PCs Debian/Devuan como paquete `.deb`, ver [PORTABILIDAD.md](PORTABILIDAD.md#paquete-instalable-debiandevuan-para-laboratorios): `bash construir_deb.sh` genera `dist/yoguicuentas_0.2.4_all.deb`. El lanzador automático usa GPU OpenCL si aparece; si solo está PoCL CPU, elige CPU NumPy.
Para compilar Metal desde el código fuente, consultar [la guía de instalación](metal/yoguicuentas_metal/INSTALACION_APPLE_M1.md). GitHub Actions genera los instaladores en cada Release. Las versiones OpenCL (`0.2.4`) y Metal (`0.11.0`) se identifican por separado.

Simulación de calor 2D sobre una grilla estructurada. Primera etapa:
referencia de consola NumPy y backend OpenCL C 1.1, Euler explícito y diferencias centradas.

## Ejecutar

Desde esta carpeta, con Python >= 3.10 y NumPy:

```bash
python3 -m yoguicuentas --steps 1000
python3 -m yoguicuentas --scenario scenarios/cobre_seno.json --steps 1000 --output resultados/seno
python3 -m yoguicuentas --scenario scenarios/cobre_fuente.json --steps 500 --batch-size 64 --output resultados/fuente
python3 -m unittest discover -s tests -v
```

Para instalar el paquete opcionalmente: `python3 -m pip install -e .`.
El backend NumPy no requiere OpenCL ni servidor gráfico. El backend OpenCL es opcional.
Cada ejecución escribe `temperature.npy`, `scenario.json` y `report.json`.
La temperatura tiene forma `(ny, nx)` y coordenadas `x=i*dx`, `y=j*dy`.
El reporte incluye tiempo físico, tiempo de ejecución, extremos y, cuando
corresponde, error contra la solución continua analítica. Los archivos de una
misma carpeta se sobrescriben; usar una carpeta por corrida.

## Backend OpenCL y A2000

Instalación opcional: `python3 -m pip install -e '.[opencl]'`.
En este equipo la A2000 es el dispositivo 1 al quitar el filtro CUDA:

```bash
env -u CUDA_VISIBLE_DEVICES python3 -m yoguicuentas --list-devices
env -u CUDA_VISIBLE_DEVICES python3 -m yoguicuentas --backend opencl --device 1 --steps 1000 --output resultados/a2000
env -u CUDA_VISIBLE_DEVICES YOGUI_TEST_DEVICE=1 python3 -m unittest discover -s tests -v
```

`env -u` recibe el nombre de la variable, sin `=1`. Los índices pueden cambiar;
comprobar siempre el nombre registrado en report.json. No se cambia el entorno
permanente ni se selecciona silenciosamente otra GPU ante un error.

El kernel se compila con `-cl-std=CL1.1`; usa float32, dos buffers privados
persistentes y ningún viaje a CPU entre pasos. La fuente uniforme se pasa como
incremento escalar. El scheduler acepta un lote pendiente y devuelve Ticket:
`poll(ticket)` confirma sin esperar, `wait(ticket)` espera en consola.
`steps` cuenta pasos confirmados. Cada ticket sólo se confirma una vez.
El controller de consola espera al finalizar cada lote; todavía no es el tick
asíncrono del futuro frontend. Snapshot espera y descarga explícitamente.

Se pueden inyectar contexto y cola in-order al scheduler para conectar después
el contexto compartido GL. La publicación al VBO está implementada en la vista gráfica.
El reporte añade dispositivo, driver, opciones y log de compilación, suma de
tiempos de kernels, esperas CPU y descarga. wall_s excluye inicialización,
compilación y exportación; kernel_s sólo mide ejecución de kernels.

Validado en RTX A2000: 10 pruebas aprobadas, incluidas mallas rectangulares,
fuente, equilibrio, lotes, propiedad de tickets y comparación con NumPy.
La tolerancia GPU/CPU es rtol=3e-6 y atol=2e-4 K para los casos probados.
La enumeración sin plataforma se omite en tests; fallos de compilación o
comparación en un dispositivo disponible hacen fallar las pruebas.

## Vista Tkinter y OpenGL en la A2000

El entorno local `.venv` tiene PyOpenCL 2026.1.2 compilado con GL habilitado,
además de pyopengltk. La instalación global permanece sin modificar.

```bash
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas --gui --device 1 --batch-size 8
# Corrida que se cierra sola y verifica el VBO contra NumPy:
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas --gui --device 1 --batch-size 8 --smoke-seconds 3 --output resultados/interop
# Suite completa con ventana temporal y límite de tiempo:
env -u CUDA_VISIBLE_DEVICES YOGUI_TEST_DEVICE=1 YOGUI_TEST_GL=1 .venv/bin/python -m unittest discover -s tests -v
```

El selector ofrece cuatro vistas sobre la misma malla y el mismo VBO de visualización:
mapa de temperatura, superficie 3D, magnitud del gradiente térmico y flujo de calor.
En 3D se gira arrastrando con el botón izquierdo y se hace zoom con la rueda;
Restablecer cámara recupera la orientación inicial. La altura es relativa a la
escala térmica seleccionada, no una coordenada espacial física. La proyección
es ortográfica y el color sigue representando temperatura.

Gradiente y flujo usan diferencias centradas interiores y unilaterales de primer
orden en frontera. El shader toma vecinos mediante samplerBuffer (OpenGL 3.1 /
GLSL 1.40) ligado al mismo GLBuffer de OpenCL 1.1: no es una GLTexture de CL,
no requiere CL 1.2 y no duplica el campo. ∇T se expresa en K/m; q=-k∇T en W/m².
Se interpola el vector nodal dentro de cada triángulo antes de calcular su
magnitud. Las flechas del flujo muestran dirección y tienen longitud fija;
la magnitud está codificada por el color. El flujo visual se reconstruye promediando los flujos de caras calculados con
la misma media de conductividad que el solver; también admite regiones materiales.

Escala de color permite editar mínimos/máximos térmicos o el máximo positivo de
magnitud, según la vista. Las escalas no se ajustan automáticamente ni cambian
el estado físico. Gradiente y flujo empiezan con escalas calculadas a partir del campo inicial
float32 y las conductividades de cara, con 5 % de margen. Se calculan una sola
vez al iniciar/aplicar: pueden saturarse durante la evolución, y se pueden editar. Cambiar de vista
o cámara tampoco inicia ni reanuda la simulación. Conserva el aspecto físico y muestra rango fijo, dispositivo,
paso y tiempo visibles. Abre detenida y muestra el campo inicial: el botón **Iniciar** comienza el
cálculo y luego cambia a **Pausar** / **Reanudar**. Al pausar se termina y publica
el lote ya enviado antes de quedar en reposo; el repintado sigue activo.
**Mostrar información** permite ocultar o recuperar el panel sin alterar el
solver. El resumen de estado, tiempo físico visible y paso permanece en la barra.
El panel muestra grilla y dominio, dx/dy, dt y límite de estabilidad, materiales,
fuente, bordes, GPU, FPS, tamaño de lote y rango fijo de color. Los datos dinámicos
se actualizan como máximo cinco veces por segundo y no descargan el campo GPU.
El rango de color es la escala visual, no los extremos actuales de temperatura. No
implementa todavía pintura ni grabación de video. Para una fuente que
supere el rango de color habrá saturación; el rango se puede ajustar con Escala de color.
El tamaño del lote controla la velocidad física de reproducción; no modifica dt.

`simulation/live.py` consulta eventos sin esperar y mantiene un lote pendiente.
`render/interop.py` selecciona la transferencia con --transfer auto|shared|host.
Auto usa VBO compartido si la GPU/driver/contexto GL lo permiten; en caso contrario
usa OpenCL → RAM → VBO. No se requiere cl_khr_gl_sharing ni have_gl=True para la
ruta host. El panel y el reporte identifican la ruta activa. Se conserva la GPU
OpenCL elegida, los kernels y toda la configuración física.

La ruta compartida usa fence GL, acquire, copia GPU y release. La ruta host
encola una lectura asíncrona a un array persistente, consulta el evento y sube el
campo al VBO cuando GL terminó su uso anterior. Publica como máximo a 30 Hz y
puede omitir cuadros intermedios para no frenar cada lote; no omite pasos físicos.
Pausa, reinicio y tf esperan la publicación final. Las copias todavía consumen
CPU/ancho de banda y su coste depende de la grilla. Esta ruta sigue el principio
de lectura a host usado por el proyecto osciladores_acoplados_OpenGL.

Para instalación nueva, ver PORTABILIDAD.md: el instalador comprueba/recupera
pip en el venv y ya no obliga a compilar PyOpenCL con GL. La compilación se puede
solicitar con --recompilar-opencl sólo para habilitar sharing opcional.

El modo smoke escribe display.npy, canvas.png e interop.json. En el cierre
compara el VBO con la referencia CPU en su paso publicado, no con un paso privado
más reciente. La imagen exportada es el canvas GL sin los controles Tkinter.
En modo smoke se verifica primero que no avanzó ningún paso y se acciona el
botón Iniciar automáticamente; la ventana normal siempre espera al usuario.
También se comprueba ocultar/mostrar el panel, se exporta mode_0.png a
mode_3.png, se comprueba que las vistas difieren y no generan errores GL.
Un campo lineal T=5+2x+3y prueba los shaders con ∇T=(2,3) K/m y q=-k(2,3);
se compara el color de magnitud contra el esperado, con tolerancia de 5 niveles
RGB sobre 255 por cuantización/interpolación. En la A2000 el error fue 0.25.
Esta prueba verifica magnitudes; la dirección se revisa también en la captura.
La prueba real se ejecuta en subprocess con timeout; sin YOGUI_TEST_GL=1 se omite.

La instalación portable y el diagnóstico de iGPU se describen en
[PORTABILIDAD.md](PORTABILIDAD.md). En PyOpenCL 2026.1.2 se encapsula la consulta
KHR a través de _cl cuando no está reexportada; no se invoca en la ruta host.

## Configurar condiciones iniciales, bordes y materiales

**Configurar corrida…** abre seis pestañas. Los campos inicialmente reproducen
la corrida actual: cobre k=401 W/(m K), ρ=8960 kg/m³, cp=385 J/(kg K), base
25 °C, perfil seno de amplitud 50 K, Q=0 y Dirichlet 25 °C en los cuatro lados.
No se altera la corrida al editar o cancelar. **Aplicar y reiniciar** valida el
borrador, pausa la corrida, termina el lote/publicación pendiente y sustituye
el escenario conservando el contexto CL/GL. Queda en t=0 esperando Iniciar.
La configuración puede demorar brevemente por creación de buffers; sólo ocurre
al aplicar. Las vistas y la cámara se conservan; las escalas se recalculan para
el campo inicial nuevo. Reiniciar vuelve a la última configuración aplicada.

- Inicial: uniforme, seno o gaussiana centrada, base, amplitud y sigma en metros.
- Fuente volumétrica uniforme Q en W/m³, constante en el tiempo.
- Material: Cu, Al, Ag, Au, Fe o Personalizado con k, ρ y cp editables.
- Cada lado: Dirichlet, Neumann, adiabático o Robin, con sus valores propios.
- Grilla y tiempo: dimensiones, nodos, dt automático/manual y duración finita o sin límite.

Los presets son constantes orientativas cerca de ambiente, no datos de una
aleación certificada ni funciones de temperatura. Cu conserva los valores del
proyecto original. Al=(237,2700,900), Ag=(429,10490,235), Au=(317,19300,129),
Fe=(80,7870,449), en el orden k,ρ,cp y las unidades indicadas. Personalizado
conserva ρ y cp por separado en JSON, además de C=ρcp. Como referencia para
seleccionar datos específicos, las compilaciones NIST muestran la dependencia
con temperatura y pureza:
https://nvlpubs.nist.gov/nistpubs/legacy/nsrds/nbsnsrds8.pdf
https://www.nist.gov/publications/critical-analysis-heat-capacity-data-literature-and-evaluation-thermodynamic-properties

**Guardar escenario…** exporta el borrador validado como JSON sin aplicarlo.
Puede cargarse al arrancar con `--scenario archivo.json`. Los escenarios previos
sin bordes por lado ni temperatura base explícita siguen funcionando.

### Convención de bordes y discretización

Neumann prescribe flujo saliente q=-k ∂T/∂n, en W/m²: q positivo enfría y
negativo inyecta energía. Robin prescribe q=h(T−Tamb), con h≥0 y Tamb en °C.
En esta versión sus parámetros son constantes, no expresiones de usuario.
Adiabático es q=0. Una frontera nodal no Dirichlet usa medio volumen de control:
la sustitución de un ghost Tg=Ti−2*d*q/k añade 2α(Ti−Tb)/d² y −2q/(C*d).
Robin añade un sumidero 2h/(C*d) y aporte 2h*Tamb/(C*d). Las esquinas suman
ambas contribuciones; si toca Dirichlet, se prescribe ese valor. Dos Dirichlet
con valores diferentes usan la media en su nodo común.

La conservación se evalúa con pesos trapezoidales: medio peso en caras y cuarto
en esquinas. El operador se preensambla en CPU como cuatro coeficientes vecinos,
diagonal y fuente; los seis arrays permanecen en GPU. El kernel sigue siendo
OpenCL C 1.1. Es un coste adicional de memoria a cambio de un contrato idéntico
CPU/GPU y selección de bordes sin ramificaciones complejas por paso.
El límite de dt incluye pérdidas Robin; usar sólo el límite de difusión podría
ser inestable para h grande. El gradiente visual sigue siendo una reconstrucción
por diferencias del campo y puede aproximar el flujo normal de frontera con
error espacial; no se presenta como un flujo impuesto exacto en el shader.

Las pruebas incluyen energía aislada con fuente, signo del flujo, perfiles
lineales estacionarios Neumann/Robin, esquinas, materiales CPU/GPU, formulario
Tk y sustitución de escenario durante una corrida con contexto GL compartido.

## Guardar, cargar y definir regiones materiales

**Archivo → Guardar configuración actual…** exporta el escenario aplicado.
**Archivo → Cargar configuración…** abre un JSON en el editor: se puede revisar,
modificar, cancelar o pulsar Aplicar y reiniciar. La carga por sí sola no altera
la corrida. El editor también tiene Cargar escenario y Guardar escenario para
trabajar con borradores. Se incluyen grilla, duración, inicial, fuentes, bordes,
material de fondo, regiones y media de interfaz. No se guarda el campo térmico
actual ni cámara/velocidad de reproducción como parte de un escenario inicial.
Los archivos anteriores sin regiones siguen siendo válidos.

En **Configurar corrida… → Regiones**, la cantidad y **Crear franjas X** generan
una lista de rectángulos que cubren el dominio. Esta acción reemplaza la lista
con franjas de cobre; se pueden editar, agregar o eliminar filas después.
Seleccionar una fila y Editar permite ingresar xmin/xmax/ymin/ymax en metros y
Cu/Al/Ag/Au/Fe o Personalizado con k,ρ,cp. Los sectores no cubiertos usan el
material de fondo de la pestaña Material. La cantidad visible sigue la lista.

Los rectángulos no pueden solaparse ni salir del dominio. Se asigna material
al nodo cuya coordenada esté en [mínimo,máximo), incluyendo el borde exterior
cuando máximo coincide con Lx o Ly. Por ello dos rectángulos adyacentes no
reclaman el mismo nodo de unión. Se rechazan regiones sin nodos: hace falta
refinar o ampliar el rectángulo. Los límites físicos se rasterizan sobre la
malla; no hay geometría subcelda ni seguimiento exacto de una interfaz que cae
entre nodos. El intercambio representa dos semidistancias iguales entre nodos.

Para nodos vecinos con k1 y k2 positivos, la conductividad de cara usa:

- Armónica, predeterminada: 2*k1*k2/(k1+k2). Equivale a las resistencias de dos
  semidistancias en serie; apropiada como base para saltos de material.
- Aritmética: (k1+k2)/2.
- Geométrica: sqrt(k1*k2).

La selección es global y se guarda en JSON. Las tres generan la misma cara para
ambas celdas, de modo que intercambian flujos opuestos y conservan energía.
Aritmética y geométrica permiten comparar modelos; no se consideran equivalentes
a la resistencia en serie para un salto abrupto. Como referencia primaria de
interpolación de coeficientes a caras:
https://pages.nist.gov/fipy/en/stable/generated/fipy.variables.distanceVariable.html#fipy.variables.distanceVariable.DistanceVariable.harmonicFaceValue

No se incluye una expresión arbitraria de interfaz en esta versión. Una futura
ruta experimental deberá imponer conductividades positivas, simetría de cara,
valores finitos y revalidar estabilidad; una resistencia térmica de contacto
explícita sería además una alternativa físicamente interpretable.

El operador es div(k grad T)/C por nodo, no alpha(x,y)*laplaciano(T). Las fuentes
se dividen por la capacidad local, y Robin/Neumann usan esa misma capacidad en
sus medios volúmenes de frontera. La cota CFL es conservadora: max(k)/min(C),
con las pérdidas Robin, incluso si esos extremos pertenecen a regiones distintas.
La conservación se comprueba sumando C*T*volumen local. El render mantiene en
GPU un buffer estático adicional con las cuatro conductividades de cara; los
shaders reconstruyen el flujo con ellas sin descargar temperatura por cuadro.
La imagen interpola el flujo nodal reconstruido y no constituye una integración
exacta de energía a través de una sección arbitraria.

Ejemplo listo para cargar: `scenarios/cobre_aluminio_regiones.json`, con dos
mitades de Cu/Al y media armónica. Las pruebas incluyen perfiles estacionarios
por resistencias discretas, flujo constante en interfaces, energía conservada,
contrastes de k y C, las tres medias CPU/GPU, guardado/carga y controles Tk.

## Fuentes constantes localizadas

La nueva pestaña **Fuentes constantes** abre con lista vacía y el fondo uniforme
sigue siendo Q=0 por defecto: **S(x,y)=0**. La gaussiana/seno inicial no es una
fuente: especifica temperatura en t=0, mientras las fuentes suministran energía
continuamente después de Iniciar. Agregar cuadrada abre una plantilla centrada
con lado 20 % del menor lado del dominio e intensidad 1e6 W/m³; cancelar no
agrega ni activa nada. También hay cantidad + Crear fuentes cuadradas, que
reemplaza la lista con N fuentes distribuidas en X. Cada fila se puede editar
o eliminar; volver a cantidad cero elimina las fuentes locales al crear.

Cada fuente tiene geometría Cuadrada, Rectangular o Circular, centro (x,y) en
metros desde la esquina inferior izquierda, dimensiones físicas e intensidad
Q constante en W/m³. En cuadradas se ingresa lado; en rectángulos ancho y alto;
en círculos diámetro. Los tamaños no están en nodos ni en píxeles. Las fuentes
se suman entre sí y al Q uniforme de fondo; un valor negativo representa una
extracción de energía. Se rechazan geometrías fuera del dominio, medidas no
positivas y valores no finitos. Se guardan y cargan junto con el escenario.

El aporte se calcula por cobertura de los volúmenes duales de los nodos:
para cada nodo, Q promedio = Q de fuente × área de intersección / área dual.
Las áreas rectangulares y circulares se integran geométricamente, en vez de
preguntar únicamente si el nodo cae dentro de la figura. Así incluso una fuente
subnodo aporta energía, aunque su forma térmica no pueda resolverse sin refinar.
La suma Q_nodo*área_dual coincide con Q*área_de_fuente independientemente del
refinamiento, salvo redondeo. Las superposiciones son aditivas.

La ecuación conserva C_nodo*dT/dt = div(k grad T)+Q_nodo. No se confunde Q con
K/s: se divide por la capacidad local. Para una placa 2D, integrar Q en área da
W por metro de espesor; no potencia total en W sin especificar el espesor.
En nodos Dirichlet se conserva la temperatura impuesta y no se integra la fuente:
si el soporte alcanza su medio volumen, esa parte no calienta grados de libertad
libres. Con aislamiento total, las pruebas verifican energía total igual al
aporte de todas las fuentes por el tiempo, incluyendo capacidades por regiones.

Las fuentes son estáticas durante la corrida y se preensamblan en el buffer de
aporte OpenCL ya existente. No agregan transferencias CPU/GPU por paso ni cambian
CFL por sí mismas. Aplicar y reiniciar es necesario para cambiar la lista; dt,
material, bordes y grilla se validan juntos. Las escalas visuales iniciales quedan
fijas y pueden saturarse al calentarse: Escala de color permite ajustarlas.

Ejemplo opt-in: `scenarios/fuente_cuadrada.json`: placa inicialmente uniforme a
25 °C, aislada, fuente cuadrada central y tiempo final 60 s. Cargar ese archivo
activa la fuente sólo al aplicar el escenario; los valores de arranque de la
aplicación no cambian. Los archivos anteriores sin sources conservan su Q de
fondo y no adquieren fuentes locales automáticamente.

## Grilla, paso temporal y duración

En **Configurar corrida… → Grilla y tiempo** se eligen Lx y Ly en metros, y Nx
/Ny enteros ≥3. Los espaciamientos se calculan como Lx/(Nx−1) y Ly/(Ny−1).
Se conservan 0.5 × 0.5 m y 65 × 65 nodos por defecto.

- **Automático (CFL)**: dt=factor×límite estable; el factor debe estar en (0,1].
- **Manual**: dt en segundos, positivo y no mayor al límite del material,
  grilla y bordes actuales. No se corrige silenciosamente un dt inestable.
- **Sin límite** (predeterminado): continúa hasta pausar o reiniciar.
- **Tiempo final**: positivo, en segundos. Los lotes no cruzan ese tiempo;
  el último paso se acorta si hace falta. Ejemplo: dt=0.01 y tf=0.025 produce
  pasos 0.01, 0.01 y 0.005. El tiempo mostrado es 0.025, no 0.03.

**Validar grilla y paso** muestra dx, dy, dt seleccionado, límite estable y número
de pasos del borrador usando el material y bordes de todas las pestañas.
Aplicar sustituye también malla, índices y buffers GL/CL; no reutiliza tamaños
anteriores. Conserva vista y cámara, y queda esperando Iniciar. Se rechazan
grillas que excedan los índices o el presupuesto conservador de memoria GPU.
Una grilla grande aumenta tanto el coste numérico como el gráfico, ya que se
visualiza la malla completa.

Al finalizar se publica el último campo, aparece **Finalizado** y se deshabilita
el avance; cámara, cambio de vista, captura y configuración siguen disponibles.
**Reiniciar** permite ejecutar nuevamente la misma corrida desde t=0.
La configuración JSON guarda dt=null para automático y final_time=null para
sin límite. Las exportaciones PNG y reportes usan el tiempo físico incluyendo
el último paso parcial. En GPU dt se representa en float32, de modo que la
solución conserva su tolerancia de redondeo aunque el contador indique tf exacto.
En consola, --steps sigue siendo un máximo de pasos y el tiempo final del
escenario puede detener la corrida antes; Sin límite no elimina ese máximo CLI.

## Velocidad respecto del tiempo real

La barra **Velocidad** ofrece 0.25×, 0.5×, 1×, 2×, 4×, 8×, Personalizada y
**Máxima velocidad** (predeterminada, comportamiento anterior). El factor es
segundos simulados por segundo de reloj monotónico: 0.25× tarda cuatro segundos
reales por segundo físico; 2× intenta avanzar dos segundos físicos por segundo
real. Personalizar acepta cualquier factor positivo y finito. El factor se puede
cambiar en marcha o en pausa, sin reiniciar la solución.

La barra muestra objetivo y velocidad **efectiva** del campo publicado, estimada
en una ventana de aproximadamente un segundo, separada de los FPS de render.
Si la corrida queda por detrás del reloj solicitado aparece «por debajo del
objetivo». Esto puede depender de cómputo, render, tamaño de grilla, dt y carga del
sistema. No garantiza el mismo factor en una A2000, RX 550 o iGPU.

El regulador sólo limita cuándo y cuántos pasos se encolan. No modifica dt, no
omite pasos, no cambia la fuente ni altera el tiempo final. Usa el mismo solver
y mantiene un único lote pendiente, de hasta el tamaño configurado. Si la GPU se
atrasa, intenta recuperar ritmo con lotes acotados; no genera una cola de trabajo
sin límite. Máxima velocidad elimina la espera del reloj y conserva la ruta
actual de cálculo/publicación, con sus costes de render y sincronización.

En espera se siguen atendiendo Tkinter, cámara y renderizado; no hay sleep ni
wait de GPU para regular la velocidad. Como el campo sólo cambia en pasos
físicos completos, a factores bajos o dt grande se verán cuadros repetidos;
no se interpola una solución ficticia. La latencia de cómputo/publicación puede
hacer que el campo visible quede algo detrás del reloj aun en hardware capaz.

Pausa/reanudación y cambios de factor reanclan el reloj en el tiempo calculado
o ya enviado a GPU: no se intenta recuperar el tiempo que estuvo en pausa ni
se cancela un lote que ya empezó. Ese lote puede terminar después de elegir
una velocidad más baja. Reiniciar y aplicar otra configuración conservan el
factor elegido y vuelven a quedar detenidos. Es una preferencia de reproducción
de la sesión, no un parámetro físico del JSON. Las capturas PNG registran el
factor solicitado y la velocidad efectiva al tomar el frame.

Las pruebas usan relojes controlados para factores, pausas, cambios con lotes
en vuelo, paso final parcial y hardware simulado lento; la prueba gráfica de la
A2000 selecciona 0.5× y verifica que no se adelante al reloj al finalizar.

## Reiniciar y guardar imágenes

**Reiniciar** vuelve al campo inicial y pone tiempo/pasos a cero. La aplicación
queda detenida, lista para Iniciar. Conserva la vista, cámara, escalas y el panel.
Si hay un lote o publicación en marcha, se consulta su finalización antes de
restaurar y volver a publicar. El botón Iniciar queda deshabilitado durante esa
transición; no se cancela un kernel a mitad de paso ni se recrean contextos.
La condición inicial tiene una copia privada residente en GPU. El reinicio es
una copia GPU y reutiliza los buffers existentes; no hace transferencias host.
Los tiempos acumulados del scheduler también se reinician al confirmar la copia.

**Guardar imagen…** permite elegir un PNG del próximo frame renderizado, tanto
en marcha como en pausa. Incluye la cámara, vista y escalas actuales; los controles
Tkinter quedan fuera. El PNG incorpora metadatos con paso, tiempo, modo, escala
y cámara bajo la clave YoguiCuentas. Se guarda el estado del frame capturado,
que puede ser posterior al momento del clic si la simulación está avanzando.

La lectura se encola a un PBO y se consulta un fence sin esperar en el callback.
Cuando está lista, se copia el RGB y un trabajador dedicado codifica el PNG.
Hay un pedido permitido a la vez; el botón vuelve a habilitarse al terminar y
la barra inferior informa la ruta o el error. Al cerrar se drena una captura ya
enviada y se cancela un pedido que todavía no llegó a un frame. La codificación
puede demorar el cierre; no bloquea el bucle durante la simulación.

El modo smoke prueba también reinicio, retorno al paso visible cero, guardado
a screenshot.png y reanudación. Las pruebas GPU comprueban restauración exacta
float32 y avance correcto después de reiniciar. Aún no hay grabación de video.

## Física y estabilidad

Se resuelve `C dT/dt = k laplaciano(T) + Q`, con k y C=rho*cp constantes.
Unidades: longitud m, tiempo s, temperatura °C, k W/(m K), C J/(m³ K),
Q W/m³. Las diferencias de temperatura en °C equivalen a K.
La fuente se divide por C una sola vez; no se interpreta como K/s.

Por defecto los cuatro lados tienen Dirichlet constante y uniforme. La inicialización
`sine` es `Tb + A sin(pi*x/Lx) sin(pi*y/Ly)`; `uniform` es Tb.
La fuente es uniforme y estacionaria; se aplica a todos los nodos que no tengan
Dirichlet, incluyendo sus volúmenes medios de frontera. Las propiedades son constantes por región, con un material de fondo fuera de
los rectángulos explícitos.

El paso máximo es `1 / (2*alpha*(1/dx²+1/dy²))`, alpha=k/C.
Si dt es null, se usa safety por ese máximo. Un dt explícito inválido se
rechaza antes de ejecutar. El tamaño del lote no modifica dt.

Para seno sin fuente, la solución continua es la condición inicial relativa
a Tb multiplicada por `exp(-alpha*pi²*(1/Lx²+1/Ly²)*t)`.
La referencia CPU usa float64 para separar errores de discretización de los de
redondeo de un futuro backend GPU float32.

## Separación de responsabilidades implementada

- `model/grid.py`: grilla, coordenadas y espaciamientos.
- `config/scenarios.py`: escenario inmutable, validación y JSON versión 1.
- `numerics/reference/explicit.py`: paso explícito y solución analítica.
- `compute/scheduler.py`: dos buffers CPU alternados, lotes y snapshot.
- `simulation/controller.py`: pausa, reanudación, conteo y tiempo físico.
- `app.py`: argumentos y exportación; no contiene el bucle temporal.
- `tests/test_explicit.py`: validación numérica y ejecución reproducible.

El scheduler CPU es síncrono. `advance()` es una operación de consola y no
debe llamarse con lotes largos desde Tkinter. No se presentan estas clases
como una implementación asíncrona todavía.

## Fronteras para las siguientes etapas

1. Implementado: kernel OpenCL C 1.1, scheduler GPU, comparación con NumPy,
   selección explícita del dispositivo, log de compilación y profiling.
2. Tickets consultables implementados en el backend OpenCL; falta el tick de UI: el controller mantiene a lo sumo un lote
   de simulación pendiente y confirma pasos completados al consultar el evento.
   Un `tick()` futuro retorna sin esperar a la GPU. Pausar impide nuevos lotes;
   el lote ya enviado termina. El ritmo de reproducción y presupuesto de
   trabajo deciden pasos por cuadro; la estabilidad determina dt.
3. `compute/buffers.py` contiene sólo memoria CL privada. El campo permanece en
   GPU: no habrá snapshot CPU por cuadro. `snapshot()` es una exportación
   explícita, potencialmente bloqueante.
4. `render/interop.py` poseerá GLBuffer y sus envoltorios CL, creados con el
   contexto GL activo. El dispositivo CL se elegirá por compatibilidad con GL,
   no por ser la primera GPU enumerada. `have_gl()` no es suficiente.
5. Un kernel publicará temperatura desde CL privado al VBO compartido. Usar
   una malla completa, plana para mapa o elevada para superficie. Un quad de
   cuatro vértices no alcanza para interpolar todo el campo. Texturas quedan
   como ruta opcional posterior según API y capacidades verificadas.
6. Cada objeto compartido tendrá propiedad explícita: GL terminado → acquire
   CL → publicación → release CL completado → dibujo GL → GL terminado.
   Doble buffer no reemplaza sincronización. La ruta inicial conservadora se
   medirá antes de incorporar fences/extensiones o más buffers.
7. Tkinter y GL quedarán en el hilo principal. El controlador consultará
   eventos con after(); el renderer reutilizará la última imagen terminada.
   Gradientes se calcularán en coordenadas físicas mediante vecinos, nunca
   interpretando derivadas de pantalla como flujo térmico.
8. Las pintadas producirán Patch inmutables. El controller las aplicará al
   terminar lotes completos, actualizará versión e invalidará coeficientes.
   La UI no escribirá buffers CL. Este contrato aún no está implementado.
9. Captura: productor en hilo GL tras el frame; consumidor dedicado con cola
   acotada. Tiempo real descarta el pendiente más antiguo; exportación
   determinista aplica contrapresión. flush fuera del callback UI.

Render y UI iniciales ya están implementados; captura y otros esquemas se
agregarán con sus pruebas.
Las pruebas GPU/interop futuras distinguirán falta de capacidad (skip) de
fallos en un dispositivo compatible y tendrán límite de tiempo por proceso.

## Referencias revisadas

- [LaboII-Explicito2D](https://github.com/javoxa/LaboII-Explicito2D): stencil explícito y alternancia de buffers.
- [LaboII-ImplicitoCN2D](https://github.com/javoxa/LaboII-ImplicitoCN2D): implementación previa de Crank–Nicolson.
- [LaboII-Osciladores_Acoplados_OpenCL](https://github.com/javoxa/LaboII-Osciladores_Acoplados_OpenCL): referencia de instrucciones de instalación y ejecución en Linux.

No se modifican esos proyectos. La referencia verificable valida ahora el solver OpenCL y su publicación al VBO.

## Diagnóstico inicial de mix_base.json

Se corrigió la escala inicial de magnitudes: antes se estimaba el gradiente con
A*pi/min(Lx,Ly), apropiado como orden de magnitud de un seno pero insuficiente
para gaussianas estrechas. Ahora se reconstruyen gradiente y flujo iniciales con
el mismo stencil visual y se toma su máximo más 5 %. No se modifica la condición
inicial ni se ajusta la escala automáticamente durante cada frame.

En mix_base la base es 25 °C y la amplitud es 75 K: el pico inicial es 100 °C,
no 75 °C. La gaussiana tiene sigma=0.1 m. Su gradiente es cero en el pico y
máximo cerca de un anillo r=sigma: el valor continuo es A/sigma*exp(-1/2), unos
454.9 K/m; la grilla actual da 453.85 K/m. La escala anterior cortaba en 235.62
K/m y saturaba aproximadamente 10.78 % de los nodos.

Los cuatro materiales no prescriben temperaturas iniciales distintas: comparten
el perfil de temperatura elegido. En t=0 T y su gradiente son radialmente
simétricos, mientras que el flujo cambia con k de cada región. La evolución
posterior deja de ser radial por las distintas conductividades y capacidades.
En interfaces la imagen del flujo es una reconstrucción nodal desde caras,
no una evaluación continua exacta en el punto de encuentro de cuatro materiales.

La gaussiana sin recorte tampoco tiene exactamente derivada normal nula en los
bordes: su cola deja una incompatibilidad inicial pequeña con aislamiento
estricto. El solver impone flujo normal cero mediante el stencil de frontera;
el gradiente visual sigue siendo la diferencia unilateral del campo. Esta
aproximación de frontera no explica el recorte del anillo, que era de escala.

El diagnóstico de GPU se hizo detenido, en paso cero, comparando el VBO con la
referencia inicial convertida a float32. Las pruebas usan una copia fija del
escenario en tests/fixtures para no depender de futuras ediciones del usuario.

## Explícito hasta estacionario

En **Configurar → Grilla y tiempo → Duración → Hasta estacionario** se activa
la búsqueda del estacionario. La pestaña **Estacionario** permite ajustar las
tolerancias, intervalo de comprobación, confirmaciones y límite de pasos.
Aplicar deja la corrida detenida; se inicia con **Iniciar**. Este modo usa la
máxima velocidad disponible, manteniendo el dt explícito estable. El selector
habitual de velocidad vuelve a estar disponible al elegir otro modo de duración.
Se puede pausar, guardar el escenario y reiniciar como en una corrida transitoria.

El criterio es un residuo de las ecuaciones de balance, al estilo de los
métodos de volúmenes finitos difundidos por Patankar; no se presupone una
normalización ni tolerancia universal «de Patankar». Para cada nodo libre:

```
rP = QP/CP + sum(aPN * (TN - TP)) + términos Neumann/Robin  [K/s]
Rmax = max(abs(rP))
RL1 = sum(CP * VP * abs(rP))                              [W/m de espesor]
```

VP es el área dual nodal (media en bordes, cuarta parte en esquinas). Los nodos
Dirichlet no forman parte del sistema de incógnitas. El residuo incluye fuentes,
materiales por regiones, la media de conductividad seleccionada y los bordes.
Se exige **simultáneamente**:

```
Rmax <= atol + rtol * Rmax_inicial
RL1  <= atol * sum(CP * VP) + rtol * RL1_inicial
```

Las referencias iniciales se fijan al iniciar/reiniciar la corrida. No se divide
por temperatura absoluta ni por dt, no se suman residuos con signo y no basta
que float32 deje de cambiar. El valor absoluto de temperatura se elimina usando
diferencias entre vecinos; Robin se evalúa respecto de la temperatura base.
Esto reduce cancelación numérica y permite comparar escenarios desplazados en °C.
La normalización relativa depende del estado inicial: para comparaciones entre
corridas debe observarse también el residuo dimensional y conservar tolerancias.
La tolerancia es sobre el balance, **no una cota del error de temperatura**.

Por defecto: rtol=1e-5, atol=1e-5 K/s, comprobación cada 128 pasos,
3 confirmaciones consecutivas y como máximo 1 000 000 pasos. La interfaz
muestra ambos residuos y sus umbrales. Un límite alcanzado se muestra como
**sin converger**, nunca como estacionario. Un dt muy pequeño no produce una
falsa convergencia, pero puede hacer que se alcance ese límite. Con float32,
grillas finas o campos con gran rango dinámico pueden necesitar tolerancias
compatibles con su precisión; reducir dt no soluciona el piso de redondeo.

Sin Dirichlet ni Robin con h>0 se verifica primero la compatibilidad energética:
integral de Q menos flujo impuesto saliente igual a cero. Una placa aislada con
calentamiento neto no tiene estacionario y se rechaza en este modo. Con aporte
neto nulo, el nivel de temperatura queda determinado por la energía inicial.

La comprobación GPU es OpenCL C 1.1: una reducción calcula máximo y suma absoluta
y devuelve solamente dos float32 por comprobación, mediante copia asíncrona.
No se descarga el campo para evaluar convergencia ni se bloquea Tkinter. Los
lotes terminan en los puntos de comprobación; al converger se publica el último
campo antes de declarar la corrida terminada. Las transferencias shared/host y
la recuperación automática de interoperabilidad siguen el mismo contrato.

En consola:

```bash
./ejecutar.sh --console --backend opencl --device 1 --steady --output resultados_estacionario
```

También se puede usar `python -m yoguicuentas --backend numpy --steady` para la
referencia CPU (según el entorno activo). `--steps N` limita adicionalmente el
presupuesto de una invocación; el JSON del informe permite distinguir convergencia
(`reason: converged`), agotamiento del límite configurado (`max_steps`) y una
corrida que aún no satisface el criterio (`reason: null`). Los escenarios antiguos
siguen cargando con el modo estacionario desactivado.

Referencia sobre por qué la definición y escala del residuo deben explicitarse:
[OpenFOAM: residuals](https://doc.openfoam.com/2306/tools/processing/numerics/solvers/residuals/).

## Geometrías dentro de la grilla estructurada

En **Configurar corrida → Geometría** se edita la pieza en un lienzo con
coordenadas físicas (origen abajo a la izquierda). Se incluyen bases rectangular,
en **L** y en **U**; las fracciones X/Y controlan los brazos. En U, X es el ancho
total de los dos brazos laterales; Y es la altura del brazo inferior.

Arrastrar permite recortar o restaurar rectángulos y elipses, crear fuentes
rectangulares/circulares con Q constante y agregar regiones rectangulares de
material. Las regiones dibujadas toman k, ρ y cp del material de fondo elegido;
se pueden modificar después desde **Regiones**. No se permiten solapamientos de
regiones materiales. Las fuentes sí pueden superponerse y sus aportes se suman.
El botón Deshacer revierte el último trazo; Actualizar vista reconstruye la
vista previa con la grilla y propiedades del borrador actual.

**Aplicar y reiniciar** valida el borrador y reemplaza la corrida entre lotes
completos, dejándola detenida. Dibujar no escribe buffers de OpenCL. Guardar y
cargar escenarios incluye la geometría y todos los trazos. Los escenarios
anteriores siguen siendo rectangulares. Hay ejemplos en `scenarios/pieza_L.json`
y `scenarios/pieza_U.json`.

### Representación y condiciones de contorno

- La máscara booleana define nodos activos; los arreglos mantienen dimensiones
  `(ny,nx)`. El kernel explícito OpenCL 1.1 omite los nodos excluidos y conserva
  el ping-pong habitual de temperaturas. Sólo caras entre nodos activos conducen.
- Cada nodo activo representa su volumen dual: área dx·dy, media en el borde
  de la caja y cuarta parte en sus esquinas. El contorno de un recorte está a
  **medio espaciado** entre el nodo activo y el excluido. Es una aproximación
  escalonada de la geometría, no una malla ajustada ni un método de cut cells.
  Un trazo subnodo puede no eliminar ningún nodo; conviene refinar y comprobar
  convergencia espacial. La vista previa muestra la rasterización efectiva.
- El contorno de los recortes es **adiabático por defecto**, con conductancia
  normal cero. También se puede imponer una única temperatura o un flujo
  saliente o Robin para todos esos contornos desde Geometría. Los cuatro lados de la
  caja conservan sus condiciones independientes; sólo se aplican donde hay
  material activo. El interior sigue resolviendo conducción; Robin representa un intercambio
  prescrito en la pared, sin resolver un fluido.
- Para Dirichlet en un recorte, la distancia nodo–pared es d/2: el término de
  pérdida es `2*k/(C*ancho_dual*d)` y el aporte es ese coeficiente multiplicado
  por la temperatura prescrita. Para Neumann se resta
  `q_saliente/(C*ancho_dual)`. Se ajusta la cota explícita estable si hay
  Dirichlet o Robin en recortes. No se prescribe la temperatura del nodo excluido.
- Material y generación existen sólo en el dominio activo. Una fuente que
  atraviesa un recorte aporta únicamente su fracción dentro de los volúmenes
  activos; una fuente totalmente fuera no aporta. No se redistribuye su potencia
  a los nodos restantes. Tampoco se asigna k=0 a un material ficticio.

### Visualización y estacionario

La geometría se prepara una vez al configurar: para dominios recortados se
triangulan sólo volúmenes activos, con vértices centrales y en las esquinas de
esos volúmenes. Las esquinas interpolan nodos activos conectados localmente por
caras. No se construyen superficies a través de huecos; también se muestran
piezas de un nodo o canales de una fila. La temperatura continúa en el buffer
CL/GL compartido o en el transporte host alternativo; no se reconstruye la malla
ni se descarga el campo por frame para ocultar el exterior.

Gradiente y flujo se reconstruyen a partir de diferencias de vecinos activos y
de los flujos de cara del contorno. El recorte adiabático aporta flujo normal
cero; Dirichlet y Neumann aportan el flujo correspondiente a su condición. Las
magnitudes son reconstrucciones nodales interpoladas: el flujo en una cara
adiabática es exactamente cero, aunque la flecha del nodo interior próximo al
contorno puede tener componente normal por el flujo de la cara interior opuesta.
Las escalas ignoran los valores de almacenamiento de los nodos excluidos.

La búsqueda del estacionario usa únicamente ecuaciones activas y verifica el
balance **por componente conectada por caras**. Una pieza separada que encierre
una fuente sin disipación ni temperatura impuesta se rechaza, aunque otra pieza
tenga Dirichlet en la caja. Dos piezas que sólo se tocan en una esquina no
intercambian calor. El modo transitorio permite estudiar su calentamiento.

La exportación de consola agrega `active_mask.npy`; `temperature.npy` conserva
su forma rectangular y valores finitos de almacenamiento fuera de la pieza,
que deben ignorarse usando esa máscara. El informe muestra temperaturas mínima
y máxima únicamente del material activo. JSON almacena las operaciones físicas,
no una lista de índices de nodos: al refinar se vuelven a rasterizar. Las bases
L/U se adaptan a las dimensiones de la caja; los trazos conservan sus metros y
se rechazan si al reducir la caja quedan fuera de ella.

Quedan para etapas posteriores la selección de condiciones por segmentos del
contorno, las curvas con representación de frontera de mayor precisión y la
interpretación automática de dibujos mediante VLM. El contrato `Domain` +
`DomainEdit` ya mantiene los datos geométricos separados de UI, materiales,
fuentes y backend de cálculo.


## Edición de fuentes, vista combinada y Robin en el lienzo

- **Eliminar fuente** (herramienta de Geometría): hacer clic dentro de la fuente.
  Si hay fuentes superpuestas se elimina la última dibujada que contiene el
  punto. En círculos se comprueba el disco real, no su rectángulo envolvente.
  **Borrar todas las fuentes** vacía la lista; ambas acciones admiten Deshacer.
  También sigue disponible la eliminación individual desde Fuentes constantes.
- Las fuentes circulares se previsualizan con el mismo diámetro que se aplica
  al soltar el mouse, incluso si el arrastre es rectangular. La vista de diseño
  dibuja los contornos físicos con suavizado y muestra sólo el identificador;
  al pasar el mouse se informa geometría e intensidad. El suavizado es visual:
  el solver sigue integrando el área de la fuente en los volúmenes activos.
  Se corrigió el soporte del área circular para anular exactamente celdas que
  no intersectan el disco, evitando trazos espurios de redondeo fuera de él.
- **Temperatura + flujo** es la quinta visualización. El color usa la escala
  de temperatura y las flechas muestran la dirección del flujo de calor, con
  borde claro para legibilidad. La longitud de las flechas no codifica |q|;
  para analizar su magnitud sigue disponible Flujo de calor.
- En **Geometría → Contorno de recortes → Robin** se ingresan **Tamb [°C]** y
  **h [W/(m² K)]**, constantes. Esta condición se guarda en JSON y se aplica
  a todos los contornos de recorte; la selección por segmentos sigue pendiente.

En Robin la temperatura del nodo activo no es la temperatura de la pared. Para
una cara a distancia d/2, se combinan las resistencias conductiva y de borde:

```
h_efectivo = 1 / (1/h + d/(2*k))
q_saliente = h_efectivo * (T_nodo - Tamb)
```

El balance divide ese flujo por `C*ancho_dual`; se usa la misma expresión al
reconstruir gradiente y flujo en los shaders. Para h=0 se recupera aislamiento;
para h grande se aproxima Dirichlet en la cara. El paso estable y el criterio
estacionario incluyen este sumidero. Se valida con una solución lineal 1D,
comparación CPU/OpenCL y comprobación de color en el shader del contorno Robin.

## Ventanas HD/FHD y herramientas del lienzo

La configuración se abre con un tamaño limitado por la pantalla y se puede
redimensionar. **Cargar, Guardar, Cancelar y Aplicar y reiniciar** quedan en un
pie fijo, fuera del área desplazable. Cada sección mantiene su propio scroll;
se puede usar la rueda, las barras o Tab para alcanzar los campos. Si los
botones no caben en una fila, el pie pasa a dos filas. Las secciones usan títulos
cortos y, cuando la anchura o el tamaño de letra no permiten mostrar todas las
pestañas, se ofrece un selector **Sección** con las ocho opciones.

En **Geometría**, la barra principal muestra sólo el grupo **Dominio**, **Fuentes**
o **Material** y las herramientas correspondientes. Los controles de Q y borrado
aparecen únicamente en Fuentes. **Pieza y contorno…** despliega los ajustes:

- **Pieza base:** rectángulo/L/U y dimensiones relativas de brazos.
- **Contorno:** aislamiento, Dirichlet, Neumann o Robin con sus parámetros.
- **Ayuda:** convenciones del lienzo y edición de materiales.

**Ocultar opciones** recupera espacio para dibujar. El lienzo ajusta su tamaño y
su escala física al espacio disponible; el cambio de disposición no altera los
trazos ni las condiciones guardadas. La ventana principal también limita su
tamaño inicial a la pantalla disponible. Las pruebas verifican ventanas de
1280×720 y 1920×1080 emuladas, tamaños de letra ampliados y reducción manual,
además de aplicar los parámetros mediante el pie fijo.

## Barra lateral de colores

El menú **Ver**, junto a Archivo, permite activar o desactivar **Barra de colores**.
Por defecto está oculta. La barra usa el mismo mapa de colores que la imagen y
muestra valores numéricos y unidades de la vista actual:

- Temperatura, superficie 3D y Temperatura + flujo: temperatura en °C.
- Gradiente térmico: magnitud |∇T| en K/m.
- Flujo de calor: magnitud |q| en W/m².

**Ver → Ajustar escala de color…** modifica el rango, igual que el botón existente.
La leyenda se actualiza al cambiar vista o límites y mantiene la elección de
mostrar/ocultar al reiniciar o aplicar otro escenario. En Temperatura + flujo,
el color representa temperatura; las flechas siguen indicando dirección de q.

Se dibuja dentro del framebuffer OpenGL, a la derecha de la imagen, reservando
espacio sin deformar las proporciones del dominio. Por eso aparece también en
Guardar imagen cuando está habilitada. La textura de la leyenda sólo se regenera
al cambiar su escala o tamaño; no descarga el campo de temperaturas de la GPU.
La visibilidad es una preferencia de la ventana y no modifica el escenario físico.

## Seleccionar, duplicar y reajustar objetos del lienzo

Al terminar de dibujar una fuente o un recorte/restauración, el editor pasa a
**Seleccionar fuente** o **Seleccionar geometría**. También se puede elegir esa
herramienta dentro de su grupo. Hacer clic selecciona el objeto; el marco amarillo
indica la selección. Arrastrar lo mueve conservando su tamaño. El cambio se
confirma al soltar; Esc cancela el arrastre. No se altera una corrida en ejecución.

Con el foco en el lienzo:

- **Ctrl+C / Ctrl+V:** copiar y pegar una fuente o trazo mediante el portapapeles
  interno del editor. La copia conserva forma, dimensiones y Q, o el tipo de
  recorte/restauración. Se desplaza inicialmente un espaciado de la grilla.
- **Ctrl+D:** duplicar el seleccionado.
- **Flechas:** desplazar un espaciado en X/Y; **Shift+flechas:** un décimo.
- **Supr:** eliminar la selección; **Ctrl+Z** o Deshacer revierte el cambio.
- **Doble clic**, menú **Objeto** o clic derecho → **Editar posición y tamaño…**:
  ingresar centro y dimensiones en metros, además de Q para las fuentes.

El menú Objeto reúne estas operaciones sin añadir más filas de controles. Los
atajos se limitan al lienzo para conservar copiar/pegar normal en las entradas de
texto. Si hay superposición se selecciona el último objeto dibujado del grupo
activo. Los movimientos se limitan a la caja sin recortar el objeto; un cambio
numérico inválido se rechaza antes de modificar el borrador. Las geometrías base
L/U se siguen ajustando desde Pieza y contorno; la selección manipula los trazos
individuales. Las operaciones de dominio conservan su orden de aplicación: mover
un trazo puede cambiar cómo se combina con los trazos posteriores.

Los contornos de recorte adiabáticos muestran **///** en una banda del exterior
excluido del editor, junto a la superficie. No se raya el material activo ni las
fuentes, ni se marca como aislado un contorno Dirichlet, Neumann o Robin. Es una
convención gráfica del editor; no añade material ni modifica los coeficientes
numéricos. Guardar el escenario conserva las fuentes y trazos ya reajustados.

## Bases circular y elíptica

En **Geometría → Pieza y contorno… → Pieza base → Geometría base** se puede elegir
**Circular** o **Elíptica**, además de Rectángulo/L/U. Se configuran **Centro X/Y**
en metros y un **radio** para el círculo o **semiejes X/Y** para la elipse (no
son diámetros). El semieje Y se deshabilita para el círculo.

Un campo vacío significa automático: centro en la mitad de la caja; radio
igual a 0.4·min(Lx,Ly) para el círculo; semiejes 0.4·Lx y 0.4·Ly para la elipse.
Los parámetros explícitos conservan sus metros al cambiar la grilla. Se rechaza
una base que sobresalga de la caja o que no contenga nodos en la resolución usada.
**Usar base / borrar trazos** reconstruye la base sin las ediciones anteriores;
se pueden agregar después recortes y restauraciones, fuentes y materiales.

El borde de una pieza encerrada dentro de la caja usa la condición seleccionada
en **Contorno** (adiabática por defecto). Los bordes externos de la caja sólo
actúan si existen nodos activos sobre ellos. Esto evita interpretar un Dirichlet
de la caja como una temperatura aplicada a una pieza que no toca ese lado.
Los ejemplos `scenarios/pieza_circular.json` y `scenarios/pieza_eliptica.json`
usan condiciones en el contorno de la propia pieza.

`Domain` guarda centro y radios físicos; `ellipse_parameters(domain, grid)`
expone esa geometría continua. La máscara se reconstruye en cada resolución
mediante `((x-cx)/rx)^2 + ((y-cy)/ry)^2 <= 1`, antes de aplicar los trazos. Esos
datos pueden alimentar un futuro mallador no estructurado, pero esta versión
sigue calculando con el operador cartesiano y visualizando sólo volúmenes activos.

**Alcance geométrico:** el contorno numérico sigue siendo escalonado, con caras
horizontales y verticales a medio espaciado del nodo. Dirichlet/Neumann/Robin se
aplican a esas caras, no al arco ideal. En particular, Neumann/Robin integran
la superficie escalonada; refinar la máscara no garantiza por sí solo recuperar
el intercambio de una curva ideal, porque su longitud y normales difieren.
Una frontera ajustada o una corrección geométrica de las caras será necesaria
para estudios cuantitativos de ese intercambio sobre curvas. La separación
actual permite incorporar esa mejora sin cambiar los parámetros de la geometría.
