"""English presentation catalogue. Spanish is the source/default language."""
EN = dict(line.split('|', 1) for line in '''Idioma|Language
Archivo|File
Ver|View
Conducción térmica 2D|2D heat conduction
calor 2D|2D heat conduction
Escenario|Scenario
Cálculo|Computation
Corrida|Run
Superposiciones|Overlays
Escala y cámara|Scale and camera
Información de la simulación|Simulation information
Inicializando…|Initialising…
Preparando contexto gráfico y solver…|Preparing graphics context and solver…
Iniciar|Start
Pausar|Pause
Reanudar|Resume
Reiniciar|Restart
Configurar corrida…|Configure run…
Editar escena…|Edit scene…
Guardar imagen…|Save image…
Exportar campo CSV…|Export field CSV…
Mostrar información|Show information
Mostrar controles|Show controls
Procesador (cambiar reinicia):|Processor (changing it restarts the run):
Visualización:|Visualisation:
Velocidad:|Speed:
Máxima velocidad|Maximum speed
Personalizada…|Custom…
Personalizar…|Customise…
Restablecer cámara|Reset camera
Escala automática|Automatic scale
Ajustar ahora|Fit now
Barra de colores|Colour bar
Ajustar escala de color…|Adjust colour scale…
Escala de color…|Colour scale…
Vectores de flujo|Heat-flux vectors
Isotermas|Isotherms
Temperatura de las isotermas (°C)|Isotherm temperatures (°C)
Nodos con fuente|Source nodes
Cantidad:|Count:
Densidad:|Density:
Guardar lienzo|Save canvas
Exportar campo visible|Export visible field
Exportar campo visible a CSV…|Export visible field to CSV…
Cargar configuración…|Load configuration…
Guardar configuración actual…|Save current configuration…
Cargar configuración|Load configuration
Guardar configuración actual|Save current configuration
Configurar nueva corrida|Configure a new run
Aplicar reemplaza la corrida y la deja detenida en t=0.|Apply replaces the run and leaves it paused at t=0.
Inicial|Initial state
Material|Material
Bordes|Boundaries
Grilla y tiempo|Grid and time
Perfil inicial|Initial profile
Material de fondo|Background material
Media en interfaces|Interface average
Interfaz:|Interface:
Integración|Integration
Integrador temporal|Time integrator
Paso temporal|Time step
Duración|Duration
Estacionario|Steady state
Método estacionario|Steady-state method
Criterio de parada|Stopping criterion
Nodos para las normas ΔT|Nodes for ΔT norms
Arranque suavizado: dos medios pasos de Euler implícito|Smoothed start: two backward-Euler half-steps
Aplicar y reiniciar|Apply and restart
Aplicar|Apply
Cancelar|Cancel
Aceptar|Accept
Cerrar|Close
Validar grilla y paso|Validate grid and time step
Regiones|Regions
Fuentes|Sources
Agregar región|Add region
Aceptar región|Accept region
Eliminar seleccionada|Delete selected
Editar seleccionada…|Edit selected…
Crear franjas X|Create X strips
Agregar cuadrada…|Add square…
Crear fuentes cuadradas|Create square sources
Editar fuente…|Edit source…
Eliminar fuente|Delete source
Borrar todas las fuentes|Delete all sources
Aceptar fuente|Accept source
Guardar fuente|Save source
Guardar geometría|Save geometry
Guardar material|Save material
Fuente|Source
Contorno|Boundary condition
Pieza y contorno…|Domain and boundary…
Pieza base|Base domain
Geometría base:|Base geometry:
Contorno de recortes:|Cut-out boundary:
Geometría [m]|Geometry [m]
Geometría|Geometry
Dominio|Domain
Contorno por lado / tramo|Boundary by side / segment
Actualizar figura / contorno|Update shape / boundary
Aplicar al problema|Apply to problem
Cargar escenario…|Load scenario…
Guardar escenario…|Save scenario…
Guardar escena…|Save scene…
Lienzo nuevo|New canvas
Escena v2|Scene v2
Dibujá → seleccioná → elegí una acción|Draw → select → choose an action
Dibujar:|Draw:
Objeto ▾|Object ▾
Asignar fuente|Assign source
Asignar material|Assign material
Deshacer|Undo
Rehacer|Redo
Usar base / borrar trazos|Use base / clear paths
Cerrar trazo y calentar interior|Close path and heat interior
Visible (solo presentación)|Visible (presentation only)
Bloqueada|Locked
Delimita regiones|Defines regions
Ayuda|Help
Sección:|Section:
Copiar|Copy
Pegar|Paste
Duplicar|Duplicate
Eliminar|Delete
Seleccionar|Select
Incluir|Include
Excluir|Exclude
Rectángulo|Rectangle
Cuadrado|Square
Círculo|Circle
Circular|Circular
Elipse|Ellipse
Elíptica|Elliptical
Polígono|Polygon
Polilínea|Polyline
Línea|Line
Mano alzada|Freehand
Uniforme|Uniform
Senoidal|Sinusoidal
Gaussiana|Gaussian
Armónica|Harmonic
Aritmética|Arithmetic
Geométrica|Geometric
Adiabático|Adiabatic
Adiabática|Adiabatic
Todos los nodos libres|All free nodes
Muestra aleatoria fija|Fixed random sample
Residuo físico: máximo + balance L1|Physical residual: maximum + L1 balance
ΔT · L1: suma de cambios absolutos|ΔT · L1: sum of absolute changes
ΔT · Euclídea / Frobenius|ΔT · Euclidean / Frobenius
ΔT · RMS: cambio cuadrático medio|ΔT · RMS: root-mean-square change
ΔT · Máximo absoluto / L∞ nodal|ΔT · Maximum absolute / nodal L∞
ΔT · Norma matricial 1: máxima suma por columna|ΔT · Matrix 1-norm: maximum column sum
ΔT · Norma matricial ∞: máxima suma por fila|ΔT · Matrix infinity-norm: maximum row sum
ΔT · Traza / suma diagonal (con cancelación)|ΔT · Trace / diagonal sum (with cancellation)
ΔT · Cambio de media (con cancelación)|ΔT · Change in mean (with cancellation)
Mapa de temperatura|Temperature map
Superficie 3D|3D surface
Gradiente térmico|Temperature gradient
Flujo de calor|Heat flux
Temperatura + flujo|Temperature + flux
Hasta estacionario|Until steady state
Tiempo final|Final time
Sin límite|Unlimited
Automático|Automatic
Manual|Manual
Euler explícito|Explicit Euler
Jacobi ponderado|Weighted Jacobi
Gauss–Seidel rojo–negro|Red–black Gauss–Seidel
Listo para iniciar|Ready to start
Reiniciando…|Restarting…
Pausando…|Pausing…
Pausado|Paused
En ejecución|Running
Finalizado|Finished
Estacionario alcanzado|Steady state reached
Criterio ΔT cumplido · residuo físico sin verificar|ΔT criterion met · physical residual unverified
sin converger|not converged
Límite de|Limit of
iteraciones|iterations
iteración|iteration
pasos|steps
paso|step
Campo guardado:|Field saved:
Exportando campo visible…|Exporting visible field…
Error al guardar:|Save error:
Imagen guardada:|Image saved:
Guardando imagen…|Saving image…
residuo pendiente|residual pending
balance L1|L1 balance
confirma|confirmations
control|check
Criterio sin nodos elegibles: no puede confirmar|No eligible nodes: criterion cannot be confirmed
ΔT entre controles|ΔT between checks
residuo físico cumple|physical residual satisfied
residuo físico aún sin confirmar|physical residual not yet confirmed
Objetivo|Target
efectiva|effective
por debajo del objetivo|below target
Procesador:|Processor:
Vista:|View:
Lote máximo:|Maximum batch:
Azul: frío · verde: intermedio · rojo: caliente|Blue: cold · green: intermediate · red: hot
Potencia:|Power:
profundidad|depth
nodos|nodes
libres|free
fondo|background
Fuentes constantes localizadas:|Localised constant sources:
internas / lote|internal / batch
residuo|residual
Inicial:|Initial:
Izq.|Left
Der.|Right
Inf.|Bottom
Sup.|Top
Brazos X/Y (fracción):|X/Y arms (fraction):
3D: arrastrar para girar · rueda para zoom|3D: drag to rotate · scroll to zoom
Imagen PNG|PNG image
Velocidad personalizada|Custom speed
Factor de tiempo simulado / tiempo real (positivo):|Simulated time / real time factor (positive):
Velocidad inválida|Invalid speed
Ingresar un factor positivo y finito.|Enter a positive finite factor.
Temperatura base (°C)|Base temperature (°C)
Amplitud (K)|Amplitude (K)
Conductividad k [W/(m K)]|Conductivity k [W/(m K)]
Densidad ρ [kg/m³]|Density ρ [kg/m³]
Calor específico cp [J/(kg K)]|Specific heat cp [J/(kg K)]
Número de nodos X|Number of X nodes
Número de nodos Y|Number of Y nodes
'''.splitlines())
EN.update({
'En la barra de colores: rueda para ampliar,\narrastrar extremos o centro para ajustar,\ndoble clic para encuadrar.':'On the colour bar: scroll to zoom,\ndrag the ends or centre to adjust,\ndouble-click to fit.',
'Isotermas: igual intervalo de temperatura.\nMás juntas = mayor gradiente térmico.\nUna temperatura puede formar varias curvas.\nLíneas y valores se incluyen en PNG.':'Isotherms: equal temperature intervals.\nCloser lines = steeper temperature gradient.\nOne temperature may form several curves.\nLines and values are included in PNG files.',
'Shift: selección múltiple / restricción.\nAlt: sin snap. Doble clic: cerrar polígono.\nArrastrar puntos amarillos: editar vértices.\nLa máscara curva sigue siendo escalonada.':'Shift: multiple selection / constraint.\nAlt: disable snapping. Double-click: close polygon.\nDrag yellow points to edit vertices.\nCurved masks remain stair-stepped.',
})
EN.update(dict(line.split('|', 1) for line in '''1× (tiempo real)|1× (real time)
Acercá el clic a una recta o a un lado del contorno.|Click closer to a line or a boundary side.
Alto (m)|Height (m)
Amplitud sobre la base (K)|Amplitude above baseline (K)
Ancho (m)|Width (m)
Ancho / diámetro (m)|Width / diameter (m)
Automático (CFL)|Automatic (CFL)
Bajar en orden|Move down
Borde del lienzo:|Canvas boundary:
Borde por clic|Boundary by click
Borrador inválido:|Invalid draft:
Calor específico cp (J/(kg K))|Specific heat cp (J/(kg K))
Campo CSV|CSV field
Campo uniforme: sin curvas de nivel|Uniform field: no contours
Cantidad de isotermas|Number of isotherms
Cantidad de nodos aleatorios|Number of random nodes
Cantidad entre 0 y 256|Count between 0 and 256
Centro (x,y) [m]|Centre (x,y) [m]
Centro X (m)|Centre X (m)
Centro Y (m)|Centre Y (m)
Comprobaciones consecutivas|Consecutive confirmations
Comprobar cada N iteraciones|Check every N iterations
Comprobar cada N pasos / iteraciones|Check every N steps / iterations
Conductividad k (W/(m K))|Conductivity k (W/(m K))
Configuración actual|Current configuration
Configuración inválida|Invalid configuration
Cu — Cobre|Cu — Copper
Densidad de vectores|Vector density
Densidad y calor específico deben ser positivos|Density and specific heat must be positive
Densidad ρ (kg/m³)|Density ρ (kg/m³)
Descartar cambios|Discard changes
Dibujá una figura, seleccionála y asigná sus propiedades. Aplicar reinicia la corrida.|Draw a shape, select it and assign its properties. Apply restarts the run.
Dimensiones positivas|Positive dimensions
Diámetro (m)|Diameter (m)
Editar objeto seleccionado|Edit selected object
Editar posición y tamaño…|Edit position and size…
Ejecución sin límite temporal.|Run without a time limit.
El máximo debe ser finito y mayor al mínimo.|The maximum must be finite and greater than the minimum.
El objeto no cabe en la grilla actual|The object does not fit in the current grid
Elegir borde|Select boundary
Elegir región|Select region
Elegí el lado o tramo, su condición y pulsá Actualizar figura / contorno.|Select the side or segment and its condition, then press Update shape / boundary.
Eliminar: clic dentro de la fuente.|Delete: click inside the source.
Escala de temperatura|Temperature scale
Escala inválida|Invalid scale
Escena JSON v2|JSON scene v2
Escenario JSON|JSON scenario
Estacionario directo · Jacobi|Steady-state iteration · Jacobi
Estado:|Status:
Evolución con integrador temporal|Evolution with time integrator
Excluir región|Exclude region
Factor dt automático CN|Automatic CN dt factor
Figura y contorno actualizados. Aplicar al problema reinicia la corrida.|Shape and boundary updated. Apply to problem restarts the run.
Fondo k:|Background k:
Fuente S|Source S
Fuente circular|Circular source
Fuente constante|Constant source
Fuente inválida|Invalid source
Fuente rectangular|Rectangular source
Fuentes inválidas|Invalid sources
Gaussiana centrada|Centred Gaussian
Grilla:|Grid:
Hasta estacionario (máxima velocidad).|Until steady state (maximum speed).
Incluir región|Include region
Ingresar un máximo positivo y finito.|Enter a positive finite maximum.
Intensidad Q (W/m³)|Source strength Q (W/m³)
Intensidad de fuente inválida|Invalid source strength
La media puede permanecer constante mientras se redistribuye el calor.|The mean may remain constant while heat is redistributed.
La selección cambió; volver a abrir el editor del objeto|The selection changed; reopen the object editor
Lado (m)|Side (m)
Lienzo|Canvas
Longitud X (m)|X length (m)
Longitud Y (m)|Y length (m)
Límite de pasos / iteraciones|Step / iteration limit
Límite estable|Stability limit
Material rectangular|Rectangular material
Material y límites de región|Material and region boundaries
Movimiento inválido|Invalid move
Máximo de iteraciones por sistema|Maximum iterations per system
No hay una fuente en ese punto. También se puede eliminar desde Fuentes constantes.|There is no source at that point. Sources can also be deleted from Constant sources.
No se pudo abrir la escena|Could not open scene
No se pudo cargar|Could not load
No se pudo cargar el escenario|Could not load scenario
No se pudo guardar|Could not save
No se puede aplicar:|Cannot apply:
No se puede eliminar|Cannot delete
No se puede pegar|Cannot paste
Nodos X (entero ≥ 3)|X nodes (integer ≥ 3)
Nodos Y (entero ≥ 3)|Y nodes (integer ≥ 3)
Ocultar opciones|Hide options
Origen (0,0): esquina inferior izquierda. Arrastrar para dibujar.|Origin (0,0): bottom-left corner. Drag to draw.
Parámetros inválidos|Invalid parameters
Propiedad inválida:|Invalid property:
Q uniforme de fondo (W/m³)|Uniform background Q (W/m³)
Radio (m)|Radius (m)
Radio / semieje X (m)|Radius / X semi-axis (m)
Rango:|Range:
Recortar elipse|Cut out ellipse
Recortar rectángulo|Cut out rectangle
Referencia explícita|Explicit reference
Regiones inválidas|Invalid regions
Región inválida|Invalid region
Región por clic|Region by click
Residuo en todos los nodos: máximo local y balance L1. No depende de dt.|Residual at all nodes: local maximum and L1 balance. Independent of dt.
Residuo: tolerancia absoluta (K/s)|Residual: absolute tolerance (K/s)
Resolver solo esta región|Solve only this region
Restaurar elipse|Restore ellipse
Restaurar rectángulo|Restore rectangle
Rotación (grados)|Rotation (degrees)
Seguridad CFL (0 < f ≤ 1)|CFL safety factor (0 < f ≤ 1)
Seleccionar fuente|Select source
Seleccionar geometría|Select geometry
Seleccionar una figura|Select a shape
Semieje X|X semi-axis
Semieje Y|Y semi-axis
Semilla reproducible (0…4294967295)|Reproducible seed (0…4294967295)
Sigma de la gaussiana (m)|Gaussian sigma (m)
Sin operación|No operation
Sin tiempo físico|No physical time
Subir en orden|Move up
T / q / T ambiente|T / q / ambient T
T / q saliente / T ambiente|T / outward q / ambient T
Tamaño [m]|Size [m]
Temperatura máxima (°C)|Maximum temperature (°C)
Temperatura mínima (°C)|Minimum temperature (°C)
Tiempo final (s)|Final time (s)
Tiempo visible:|Visible time:
Todos los valores deben ser finitos|All values must be finite
Tolerancia absoluta del sistema (K)|System absolute tolerance (K)
Tolerancia relativa|Relative tolerance
Tolerancia relativa del sistema|System relative tolerance
Tramo seleccionado. Elegí la condición y pulsá Actualizar figura / contorno.|Segment selected. Choose the condition and press Update shape / boundary.
Trazo inválido|Invalid path
Vacío = automático: centro de la caja y radio/semiejes al 40 %.|Empty = automatic: box centre and radius/semi-axes at 40%.
Validar muestra dx, dy y el paso estable del borrador.|Validate shows dx, dy and the draft stability limit.
Valores inválidos|Invalid values
Vista de diseño suavizada; no modifica la rasterización física del solver.|Smoothed design view; does not change the solver's physical rasterisation.
X máximo (m)|Maximum X (m)
X mínimo (m)|Minimum X (m)
Y máximo (m)|Maximum Y (m)
Y mínimo (m)|Minimum Y (m)
YoguiCuentas — Editar escena|YoguiCuentas — Edit scene
dt manual (s)|Manual dt (s)
sin límite|unlimited
¿Descartar los cambios de esta escena?|Discard changes to this scene?
ΔT: tolerancia absoluta (K)|ΔT: absolute tolerance (K)
ΔT: tolerancia relativa|ΔT: relative tolerance
Procesador|Processor
Vista|View
Velocidad|Speed
Escala|Scale
Tiempo|Time
Tipo|Type
Método|Method
Perfil|Profile
Forma|Shape
Condición inicial|Initial condition
Condiciones de borde|Boundary conditions
Grilla y dominio|Grid and domain
Convergencia estacionaria|Steady-state convergence
Resolución interna de CN · Jacobi|Internal CN solution · Jacobi
Simulación térmica|Thermal simulation
Escena geométrica|Geometric scene
Cálculo local en CPU|Local CPU computation
Abrir archivo JSON…|Open JSON file…
Editar parámetros…|Edit parameters…
Exportar campo…|Export field…
Exportar historial…|Export history…
Ocultar información|Hide information
Vista alta|Top view
Vista frontal|Front view
Ajuste automático|Automatic adjustment
Mínimo (°C)|Minimum (°C)
Máximo (°C)|Maximum (°C)
Máximo (K/m)|Maximum (K/m)
Máximo (W/m²)|Maximum (W/m²)
Mostrar valores (°C)|Show values (°C)
Nodos con fuente (puntos naranjas · vista 2D)|Source nodes (orange dots · 2D view)
Vectores de flujo de calor|Heat-flux vectors
Las flechas indican la dirección del flujo q = −k∇T.|The arrows show the heat-flux direction q = −k∇T.
Líneas de igual temperatura (°C), disponibles en todas las vistas.|Lines of equal temperature (°C), available in all views.
Configuración de corrida|Run configuration
Editar escena geométrica…|Edit geometric scene…
Eliminar región|Delete region
Agregar fuente cuadrada|Add square source
Material presente|Material present
Eliminar trazo|Delete path
Contorno de cortes|Cut-out boundary
Agregar trazo rectangular|Add rectangular path
Paso manual|Manual time step
Cuadrada|Square
Rectangular|Rectangular
Triangular|Triangular
Arranque suavizado (dos medios pasos de Euler implícito)|Smoothed start (two backward-Euler half-steps)
El estacionario directo ignora el integrador temporal y dt.|Steady-state iteration ignores the time integrator and dt.
CN es de orden 2 en tiempo y permite superar el límite estable explícito. Un dt grande puede producir oscilaciones y perder precisión aunque sea estable. Compará con la mitad del paso.|CN is second-order in time and allows steps beyond the explicit stability limit. A large dt may cause oscillations and reduce accuracy despite remaining stable. Compare with half the time step.
Dirichlet fija T; Neumann define el flujo saliente; Robin usa h y temperatura ambiente.|Dirichlet fixes T; Neumann specifies outward heat flux; Robin uses h and ambient temperature.
Sin convergencia interna se rechaza el lote y se detiene la animación. El suavizado modifica solo el primer paso físico; luego se usa CN puro.|If the internal solver fails to converge, the batch is rejected and animation stops. Smoothing changes only the first physical step; subsequent steps use CN.
Resuelve A·T = f sin avanzar tiempo físico: Jacobi ponderado (ω = 2/3) o Gauss–Seidel rojo–negro (ω = 1; dos colores por iteración). Requiere Dirichlet o Robin con h > 0 en cada componente del dominio.|Solves A·T = f without advancing physical time: weighted Jacobi (ω = 2/3) or red–black Gauss–Seidel (ω = 1; both colours per iteration). Requires Dirichlet or Robin with h > 0 in each connected component.
ΔT compara controles consecutivos, no cuadros. La traza, la media o una muestra pueden ocultar cambios. Máximo absoluto = L∞ nodal; L∞ matricial suma por filas. El residuo físico completo se informa siempre.|ΔT compares consecutive checks, not frames. The trace, mean or a sample may hide changes. Absolute maximum = nodal L∞; matrix L∞ sums by row. The full physical residual is always reported.
La corrida termina al cumplir el criterio elegido durante las confirmaciones requeridas. Una parada por ΔT no certifica estacionario si el residuo físico no cumple.|The run stops when the selected criterion passes the required consecutive checks. A ΔT stop does not certify steady state unless the physical residual also passes.
Factor de tiempo simulado por segundo real. Por ejemplo, 2× avanza dos segundos de simulación por segundo real.|Simulated time per real second. For example, 2× advances two seconds of simulation per real second.
Arrastrá el extremo superior o inferior para cambiar el rango; arrastrá el centro para desplazarlo|Drag the upper or lower end to change the range; drag the centre to shift it
'''.splitlines()))
EN.update(dict(line.split('|',1) for line in '''Nombre|Name
Intensidad|Strength
Visible|Visible
Descartar|Discard
Descartar cambios de la escena|Discard scene changes
Cámara|Camera
Región|Region
Ancho|Width
Alto|Height
Radio|Radius
Rotación|Rotation
Operación|Operation
Unir|Union
Restar|Subtract
Reemplazar|Replace
Cobre|Copper
Aluminio|Aluminium
Agua|Water
Contorno por defecto|Default boundary
Capas · última operación gana|Layers · last operation takes precedence
Propiedad de la figura seleccionada|Selected shape property
Cerrar trazo y añadir fuente en su interior|Close path and add an interior source
Cerrar trazo para usar su interior|Close path to use its interior
Añadir fuente sobre la línea|Add a source along the line
Para asignar un dominio a un lado del corte, usá Elegir región.|Use Select region to assign a domain on one side of the cut.
Añadir fuente en esta región|Add a source in this region
Excluir del dominio|Exclude from domain
Incluir en el dominio|Include in domain
Ingresá un número; también podés usar 1e7 o coma decimal.|Enter a number; scientific notation (1e7) and decimal commas are also accepted.
Parte de esta región está excluida. La fuente solo actúa sobre los nodos activos.|Part of this region is excluded. The source acts only on active nodes.
Incluir esta región en la malla y conservar su fuente|Include this region in the mesh and retain its source
Aplicar actualiza el problema y lo deja en t = 0. Pulsá Iniciar para calcular el calentamiento.|Apply updates the problem and resets it to t = 0. Press Start to calculate heating.
Fuente aplicada a toda la superficie interior que pertenece al dominio activo.|Source applied throughout the interior area belonging to the active domain.
Fuente aplicada a lo largo del trazo dentro del dominio activo.|Source applied along the path within the active domain.
Geometría (m)|Geometry (m)
Máscara rasterizada v1; se puede eliminar o combinar con nuevas primitivas.|Rasterised v1 mask; it can be deleted or combined with new primitives.
Región delimitada por trazos y figuras. Se recalcula al mover sus límites.|Region bounded by paths and shapes. Recalculated when its boundaries move.
Este trazo delimita regiones. Sus contornos se aplican cuando un lado es inactivo.|This path defines regions. Its boundary conditions apply when one side is inactive.
Este trazo aporta su fuente sobre el dominio activo; no lo divide en regiones.|This path applies its source within the active domain; it does not divide the domain into regions.
Este trazo no delimita regiones. Activá Delimita regiones para usarlo como corte.|This path does not define regions. Enable Defines regions to use it as a cut.
Condiciones por borde|Conditions by boundary
Elegí un lado de esta lista o hacé clic sobre su trazo. Cada borde conserva su propia condición.|Choose a side from this list or click its path. Each boundary retains its own condition.
Esta condición se aplica al lado o tramo resaltado.|This condition applies to the highlighted side or segment.
Heredar condición|Inherit condition
No hay caras expuestas de este trazo. La condición se aplicará al excluir una de las regiones adyacentes; dos materiales activos conservan una interfaz conductora.|This path has no exposed faces. The condition applies when an adjacent region is excluded; two active materials retain a conducting interface.
Volver a la región o figura|Return to region or shape
Flujo saliente (W/m²)|Outward heat flux (W/m²)
T ambiente (°C)|Ambient T (°C)
Temperatura (°C)|Temperature (°C)
Robin / Cauchy: q saliente = h (T − T ambiente)|Robin / Cauchy: outward q = h (T − ambient T)
Curvas: borde escalonado; refinar no garantiza el perímetro ni el balance Robin ideales sin ponderación geométrica. Las máscaras v1 tienen edición limitada.|Curves: stair-stepped boundary; refinement does not guarantee the ideal perimeter or Robin balance without geometric weighting. Editing of v1 masks is limited.
Dibujá una figura y asignale una propiedad. Para un corte de borde a borde, usá Elegir región para seleccionar uno de sus lados.|Draw a shape and assign a property. For an edge-to-edge cut, use Select region to select one side.
Alt desactiva snap · Shift: círculo / rotación 15° · Enter cierra polígono · Esc cancela · ⌘Z / ⇧⌘Z · ⌘C/V/D · Supr · Tab · ⌘[ / ⌘]|Alt disables snapping · Shift: circle / 15° rotation · Enter closes polygon · Esc cancels · ⌘Z / ⇧⌘Z · ⌘C/V/D · Delete · Tab · ⌘[ / ⌘]
Regiones de material|Material regions
Fuentes localizadas|Localised sources
Bordes internos del dominio|Internal domain boundaries
Editar velocidad|Edit speed
Editar vértices|Edit vertices
Fuente en la malla:|Source in mesh:
Aporte local Q/(ρ·cp): hasta|Local contribution Q/(ρ·cp): up to
antes de conducción y pérdidas.|before conduction and losses.
objetos seleccionados. Arrastrá para mover el conjunto.|objects selected. Drag to move the group.
Historial:|History:
controles|checks
descartados|discarded
grilla|grid
Valores de 1 a|Values from 1 to
según la resolución de la malla.|depending on mesh resolution.
Paso seleccionado:|Selected time step:
referencia explícita|explicit reference
confirmaciones|confirmations
Residuo máx.|Maximum residual
'''.splitlines()))

EN.update({
'Uniforme: sólo base. Seno: base + A·sen(πx/Lx)·sen(πy/Ly).\nGaussiana: centrada en el dominio. Los nodos Dirichlet se fijan al borde.\nEl paso y la duración se configuran en Grilla y tiempo.': 'Uniform: baseline only. Sine: baseline + A·sin(πx/Lx)·sin(πy/Ly).\nGaussian: centred in the domain. Dirichlet nodes are fixed at the boundary.\nSet the time step and duration in Grid and time.',
'Valores orientativos constantes cerca de temperatura ambiente.\nNo modelan aleaciones ni dependencia con la temperatura.\nPersonalizado permite editar las tres propiedades.': 'Indicative constant values near room temperature.\nThey do not model alloys or temperature dependence.\nCustom allows editing all three properties.',
'Dirichlet: T fija (°C). Neumann: q saliente (W/m²); negativo aporta calor.\nAdiabático: q=0. Robin: q=h·(T−Tamb), h≥0; Tamb en °C.\nEn esquinas con dos Dirichlet distintos se usa su media.': 'Dirichlet: fixed T (°C). Neumann: outward q (W/m²); negative values add heat.\nAdiabatic: q=0. Robin: q=h·(T−Tamb), h≥0; Tamb in °C.\nCorners with different Dirichlet values use their mean.',
'Elegir Jacobi o Gauss–Seidel activa Duración → Hasta estacionario.\nEuler avanza con dt estable. Los directos no avanzan tiempo físico.\nLos directos exigen Dirichlet o Robin disipativo en cada componente.\nΔT compara el campo con el control anterior; la muestra no cambia durante la corrida.\nEl límite de pasos detiene la corrida sin declararla convergida.\nLas tolerancias controlan el residuo; no garantizan un error en K.': 'Choosing Jacobi or Gauss–Seidel sets Duration → Until steady state.\nEuler advances with a stable dt. Steady-state methods do not advance physical time.\nThey require Dirichlet or dissipative Robin in each connected component.\nΔT compares against the previous check; the sample stays fixed during the run.\nThe step limit stops the run without declaring convergence.\nTolerances control the residual; they do not guarantee an error in K.',
'CN automático: seguridad × límite explícito × factor. El dt manual tiene prioridad.\nLas tolerancias son del sistema lineal, no del error temporal.\nUn paso grande puede producir oscilaciones: comparar dt/2 y dt/4.\nSi un sistema no converge, se rechaza todo el lote sin avanzar el campo.\nJacobi y Gauss–Seidel estacionarios ignoran el integrador temporal.': 'Automatic CN: safety factor × explicit limit × factor. Manual dt takes precedence.\nTolerances apply to the linear system, not temporal error.\nA large step may cause oscillations: compare dt/2 and dt/4.\nIf a system fails to converge, the whole batch is rejected without advancing the field.\nSteady-state Jacobi and Gauss–Seidel ignore the time integrator.',
'Dominio, fuentes, materiales y contornos por tramo se editan en el lienzo de escena.\nLos parámetros de grilla, material base, tiempo y bordes del lienzo siguen en estas secciones.': 'Edit the domain, sources, materials and segment boundaries in the scene canvas.\nGrid, background material, time and canvas boundary parameters remain in these sections.',
'Origen (0,0): esquina inferior izquierda. (x,y) es el centro en metros.\nQ es constante en el tiempo: positivo calienta, negativo enfría.\nLas fuentes superpuestas se suman al fondo uniforme de la primera pestaña.\nLista vacía y Q de fondo=0 ⇒ S(x,y)=0. Crear reemplaza la lista.\nSe integra el área de cada fuente en los volúmenes de la grilla, incluso subnodo.': 'Origin (0,0): bottom-left corner. (x,y) is the centre in metres.\nQ is constant in time: positive heats, negative cools.\nOverlapping sources are added to the uniform background in the first tab.\nEmpty list and background Q=0 ⇒ S(x,y)=0. Create replaces the list.\nEach source area is integrated over grid volumes, including subnode sources.',
'El borde de la pieza se configura en Contorno; los bordes de la caja sólo actúan donde hay nodos activos.': 'Set the domain boundary in Boundary condition; box boundaries act only where nodes are active.',
'Oscuro: exterior. Claro/color: material. Naranja/azul: fuente ±.\nSeleccionar: arrastrar para mover; flechas ajustan un nodo (Shift: 1/10).\nObjeto / clic derecho: editar, copiar, pegar, duplicar y eliminar.\nMaterial dibujado: propiedades del fondo; editar después en Regiones.\nLos bordes de la caja se configuran en Bordes. Aplicar reinicia la corrida.': 'Dark: exterior. Light/colour: material. Orange/blue: positive/negative source.\nSelect: drag to move; arrows move one node (Shift: 1/10).\nObject / right-click: edit, copy, paste, duplicate and delete.\nDrawn material uses background properties; edit later in Regions.\nSet box boundaries in Boundaries. Apply restarts the run.',
'El material de fondo cubre lo no definido. No se permiten solapamientos.\nCrear franjas reemplaza la lista. Luego editar límites y material de cada fila.\nRectángulos [mín, máx); se incluye el extremo exterior del dominio.\nArmónica: recomendada; aritmética y geométrica: comparación experimental.': "Background material fills undefined areas. Overlaps are not allowed.\nCreate strips replaces the list. Then edit each row's bounds and material.\nRectangles use [min, max); the outer domain endpoint is included.\nHarmonic: recommended; arithmetic and geometric: experimental comparisons.",
})
EN.update(dict(line.split('|',1) for line in '''1. Dibujá una figura → 2. Asigná su propiedad a la derecha → 3. Aplicar al problema|1. Draw a shape → 2. Assign its property on the right → 3. Apply to problem
Cerrá el trazo volviendo al inicio para usar su interior. También podés cerrarlo después desde sus propiedades.|Close the path by returning to its start to use its interior. You can also close it later from its properties.
Círculo / elipse|Circle / ellipse
Herramienta|Tool
Mantener trazo|Keep path
Material k|Material k
Máscara|Mask
Ninguno|None
Overlay|Overlay
Seleccionar figura|Select shape
Volver a parámetros|Return to parameters
Arrastra la escala para ajustarla|Drag the scale to adjust it
Arrastrar para girar · pellizcar para acercar|Drag to rotate · pinch to zoom
Factor (×)|Factor (×)
Personalizado|Custom
Al — Aluminio|Al — Aluminium
Tolerancia (px)|Tolerance (px)
Temperatura|Temperature
Izquierda|Left
Derecha|Right
Superior|Top
Inferior|Bottom
'''.splitlines()))
EN.update(dict(line.split('|',1) for line in '''ΔT · L1: suma absoluta|ΔT · L1: absolute sum
ΔT · Norma matricial 1 (columnas)|ΔT · Matrix 1-norm (columns)
ΔT · Norma matricial ∞ (filas)|ΔT · Matrix infinity norm (rows)
ΔT · Traza / suma diagonal|ΔT · Trace / diagonal sum
ΔT · Cambio de media|ΔT · Change in mean
Evolución temporal|Time evolution
Máxima|Maximum
Criterio ΔT cumplido; residuo físico sin confirmar|ΔT criterion met; physical residual unconfirmed
Cálculo no finito|Non-finite computation
Límite sin convergencia|Limit reached without convergence
Sistema estacionario sin referencia|Steady-state system without thermal reference
Resolviendo|Solving
Corrida estacionaria terminada|Steady-state run finished
Tiempo final alcanzado|Final time reached
No disponible|Unavailable
Paso grande: pueden aparecer oscilaciones; compará con dt/2.|Large step: oscillations may occur; compare with dt/2.
Verificá precisión comparando con dt/2.|Check accuracy by comparing with dt/2.
iter. internas/lote|internal iterations/batch
explícito|explicit
sin tiempo físico|without physical time
estacionario|steady state
Iteración|Iteration
Iteraciones|Iterations
Paso|Step
Pasos|Steps
visible|visible
calculados|computed
Nodos activos|Active nodes
Iteraciones algebraicas: sin dt|Algebraic iterations: no dt
límite|limit
interfaz|interface
Sin fuentes|No sources
oculta|hidden
bloqueada|locked
fuente|source
'''.splitlines()))
EN.update(dict(line.split('|',1) for line in '''No se pudo renderizar la imagen.|Could not render the image.
Fracción X|X fraction
Fracción Y|Y fraction
Calor específico cp (J/kg K)|Specific heat cp (J/kg K)
Factor dt automático sobre explícito|Automatic dt factor relative to explicit
Máximo de iteraciones|Maximum iterations
Máximo de pasos|Maximum steps
Solo hay una región: el corte debe llegar de borde a borde o cerrar una figura. Revisá también la resolución de la grilla.|There is only one region: the cut must reach from edge to edge or enclose a shape. Also check the grid resolution.
regiones delimitadas. La región seleccionada se resalta en amarillo.|bounded regions. The selected region is highlighted in yellow.
El trazo necesita encerrar una superficie.|The path must enclose an area.
escribí una intensidad Q válida antes de aplicar.|enter a valid source strength Q before applying.
la fuente no alcanza ningún nodo activo. Incluí su región en la malla o modificá su geometría antes de aplicar.|the source reaches no active nodes. Include its region in the mesh or change its geometry before applying.
No se pudo actualizar el problema. Revisá el error del cálculo.|Could not update the problem. Review the computation error.
clic para editar este borde|click to edit this boundary
CN sin convergencia · lote rechazado|CN failed to converge · batch rejected
Falló el cálculo; se detuvo la corrida|Computation failed; the run has stopped
La velocidad personalizada debe ser un número positivo y finito.|Custom speed must be a positive finite number.
Escenario migrado a v2 · máscara v1 con edición limitada|Scenario migrated to v2 · limited editing of v1 mask
Problema aplicado|Problem applied
Pulsá Iniciar|Press Start
No se encontró el escenario|Scenario not found
'''.splitlines()))
