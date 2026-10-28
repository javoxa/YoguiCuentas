# YoguiCuentas OpenCL 0.2.3 — paridad funcional con Metal

Fecha: 27/10/2026. Referencia: Metal 0.11.0 y `metal/yoguicuentas_metal/SCENE_FORMAT.md`.

Esta versión incorpora las funciones principales pendientes del port. La interfaz es una adaptación Tkinter/OpenGL para Linux; no se afirma una réplica nativa de SwiftUI ni equivalencia numérica bit a bit entre implementaciones.

## Escalas e isotermas

- **Escala y cámara → Escala automática** sigue el campo publicado; **Ajustar ahora** encuadra una sola vez. La elección no modifica la física, la cámara ni el ritmo de reproducción.
- En la **barra de colores del lienzo**: rueda para ampliar/reducir el rango alrededor del valor señalado; arrastrar arriba/abajo modifica máximo/mínimo; arrastrar el centro desplaza el rango; doble clic encuadra. En magnitudes, el mínimo permanece en cero. El ajuste manual desactiva la escala automática.
- Las isotermas usan **temperaturas activas del campo actual**, independientemente de la escala de color y del fondo seleccionado. Se generan N niveles interiores `Tmin + i*(Tmax-Tmin)/(N+1)`, i=1…N.
- Se reemplazaron las bandas periódicas del fragment shader por intersecciones explícitas con los triángulos. La prueba gráfica cuenta realmente 1, 5, 12, 20 y 30 curvas sobre un campo lineal; no comprueba únicamente el valor del control.
- **Superposiciones → Temperatura de las isotermas (°C)** activa sus valores, también en 3D y PNG. Los rótulos tienen separación para evitar colisiones y líneas guía cuando se desplazan respecto a la curva.
- N significa niveles de temperatura: un nivel puede tener varias curvas desconectadas. Un campo uniforme no tiene curvas. En componentes desconectadas puede no existir alguna temperatura intermedia; con densidades extremas, recorte de cámara o pocos píxeles no se promete distinguir todos los trazos/rótulos.
- Vectores, isotermas y nodos con fuente son capas independientes. La información de fuentes corresponde al escenario aplicado, no al borrador del editor.

La reducción GL obtiene mínimo/máximo de temperatura y máximos de gradiente/flujo mediante un framebuffer flotante 1×1. Solo lee **cuatro float32** al actualizar el campo, sin descargar temperaturas completas. Los rótulos seleccionan anclajes en GPU y leen un registro de cuatro componentes por nivel. Estas lecturas puntuales sincronizan GL y tienen coste; no se presenta esta función como libre de latencias. El coste de curvas crece con niveles × triángulos.

## Cálculo

| Modo | Referencia / ejecución |
|---|---|
| Euler explícito | NumPy float64 / OpenCL C 1.1 float32; CFL se conserva |
| Estacionario directo | Jacobi ponderado, ω=2/3; iteraciones sin tiempo físico, residuo máximo e integrado, referencia por componente |
| Crank–Nicolson | Sistemas de incrementos con Jacobi interno; tolerancias en K, máximo y frecuencia de control |
| Arranque suavizado CN | Dos medios pasos de Euler implícito únicamente en el primer paso físico |

**Configurar corrida… → Integración** elige el integrador y opciones CN. `dt automático = safety × dtLimit × cn.stepFactor`; el manual tiene prioridad y puede superar la referencia explícita solo con CN. Si un sistema falla, se rechaza el lote completo: no se publica el candidato ni avanza el tiempo. Pausar/reiniciar solicita cancelación en los controles internos. Las tolerancias no se relajan automáticamente; no estiman error temporal. Pasos grandes pueden oscilar: comparar dt/2 y dt/4. Los ejemplos `cn_animacion` y `cn_oscilaciones` permiten estudiarlo.

**Cálculo → Procesador** alterna CPU NumPy/OpenCL. Cambiar detiene y reinicia; no migra una corrida avanzada. CPU utiliza un único trabajador y tickets consultables para mantener la UI disponible. La visualización usa float32 aunque la referencia CPU calcule float64. No hay cambio silencioso de solver ante fallos del dispositivo.

## Escenas y editor v2

- Lectura v1/v2; las escenas editables se guardan en v2 mediante reemplazo atómico. `derived` se ignora. IDs, orden, roles, visibilidad y bloqueo se conservan.
- Rectángulos rotados, círculos/elipses, segmentos, polígonos/polilíneas y mano alzada. Figuras nuevas quedan seleccionadas antes de asignar roles.
- Roles componibles de dominio (`replace`, `union`, `subtract`), material, fuente y contornos por lado/tramo. Ocultar es visual; no elimina roles físicos.
- **Elegir región** identifica componentes delimitadas por trazos; no elimina una franja de nodos. Se puede excluir, incluir, resolver solo esa región o asignarle material/fuente.
- Fuentes de área W/m³ por subceldas 8×8, y fuentes de línea W/m mediante recorte geométrico semiabierto sobre volúmenes duales. Se suman, se recortan al dominio y muestran nodos/potencia. Una fuente no nula sin aporte activo impide aplicar.
- Caras internas con propietario y subsegmento. Con ambos lados activos hay interfaz conductora; la condición del trazo solo actúa al exponer una cara. Contornos Dirichlet, Neumann, adiabático y Robin/Cauchy conservan la formulación del operador.
- Lista de figuras para recuperar objetos ocultos/bloqueados; selección múltiple con Shift, marquesina, movimiento, dos handles opuestos de tamaño, rotación numérica/de rectángulo-elipse con handle, vértices y puntos medios, duplicado, copia/pegado, orden, borrar dependencias y 150 estados de deshacer/rehacer.
- Alt desactiva snap; Shift restringe líneas a 45°, rotación a 15° y proporciones al redimensionar. Las fuentes abiertas pueden cerrarse para calentar su interior. Q acepta coma, punto y notación científica sin reemplazar el texto mientras se edita.
- Aplicar valida, reconstruye recursos y deja la corrida detenida. Los parámetros v2 mantienen el editor geométrico separado de las pestañas heredadas v1, evitando perder roles.

Al entrar desde v1, el editor conserva la máscara como `legacyMask` y los materiales por intervalos semiabiertos. Las fuentes migradas se evalúan con el muestreo 8×8 de v2: no se promete igualdad exacta con la integración analítica de áreas v1. El escenario v1 original no se modifica al abrir ni al cancelar. No se sobrescribió `scenarios/mix_base.json`.

Ejemplos incluidos: `escena_cobre_v2`, `corte_regiones_v2`, `trapecio_bordes_v2`, `trapecio_fuente_v2`. El trapecio reproduce **2535 nodos activos**, **102 nodos con fuente**, potencia **50287,24670410156** con profundidad de referencia 1 m y máximo final cercano a **95,21 °C**, coincidentes con los valores registrados en Metal para ese caso. No se extrapola esa comparación a todas las geometrías/drivers.

## Exportación

PNG del framebuffer con capas, escalas y metadatos. CSV del campo publicado con coordenadas, máscara, temperatura y paso/tiempo o iteración. Las filas inactivas no contienen una temperatura física. CPU/GPU y capturas respetan los estados confirmados/publicados. La consola exporta NPY, máscara, escenario, informe y CSV.

## Restricciones y verificación

Se mantiene Linux/X11 o XWayland, OpenGL de escritorio y OpenCL 1.1 para los kernels; no hay dependencias geométricas nuevas. El contorno curvo continúa escalonado: no se garantiza convergencia a Robin de una curva ideal. El editor es una implementación nueva y requiere uso/revisión adicional para certificar todas las combinaciones de gestos de Metal. El rendimiento no se compara con Apple M1 ni se promete una aceleración fija de CN.

Pruebas de esta ampliación: orden temporal, eliminación matricial independiente, conservación, oscilaciones/Rannacher, rechazo y cancelación, CPU/OpenCL, backend interactivo, escenas v2, fuentes de línea, contornos por tramo, editor/historial, conteo de curvas por píxeles, rótulos, mouse en leyenda y capturas.

Registro final: `resultados/paridad_metal/pruebas_release_020_final.log`. Dos pruebas de hit-testing nativo se omiten cuando `loginctl` informa sesión bloqueada; la omisión no equivale a validación visual. Las pruebas de kernels/framebuffer y eventos programáticos siguen ejecutándose.

Capturas: `resultados/paridad_metal/visuales/isotermas_7_rotuladas.png` y `trapecio_12_isotermas.png`. Los registros anteriores, incluidos fallos corregidos durante la implementación, quedan conservados en esa carpeta. El estado anterior de este documento está archivado como `paridad_metal_antes_020.md`.

Resultado final 0.2.0: **138 pruebas ejecutadas, 136 aprobadas, 2 omitidas**, 68,263 s, RTX A2000 (índice OpenCL 1, kernels CL 1.1). Las dos omisiones son de hit-testing nativo porque `LockedHint=yes`; no se omitieron las pruebas numéricas GPU ni las de framebuffer. Registro `resultados/paridad_metal/pruebas_release_020_final.log`.


## Correcciones del editor en 0.2.1

La selección de fuentes no usa snap y tiene prioridad ante figuras envolventes. La lista identifica las fuentes. Elegir una región existente la reutiliza y ofrece sus lados exteriores y tramos generadores en el inspector superior para editar condiciones reales. Los contornos internos solo actúan cuando hay una frontera expuesta; entre materiales activos hay conducción.

En configuración, elegir Jacobi activa la duración estacionaria. Elegir Euler/CN desactiva Jacobi directo, evitando guardar un integrador que después queda ignorado.


## Selección de segmentos en 0.2.2

Elegir borde detecta directamente rectas y subtramos dibujados, incluso antes de excluir una región; muestra el tramo naranja y recupera su condición guardada. Las condiciones del separador se aplican a sus caras expuestas después de excluir una región adyacente. Con ambos lados activos se conserva conducción.


## Flujo de edición 0.2.3

Dibujar → seleccionar con clic → Incluir/Excluir o Fuente/Material/Contorno. Las acciones quedan fijas; las propiedades están en pestañas. Un clic interior en un dominio subdividido selecciona la región resultante; Región por clic permite elegirla explícitamente. Las isotermas conservan igual intervalo en °C y muestran ΔT; no se promete igual separación espacial para campos con gradiente variable.
