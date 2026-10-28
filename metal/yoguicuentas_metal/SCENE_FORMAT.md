# Escenas JSON v2 — contrato compartido para Metal y la futura fase Python

Fecha: 25/10/2026. Implementación: `Scene.swift`, `Scenario.swift`. Ejemplo cargable: `examples/escena_cobre_v2.json`.

La raíz contiene `version: 2`, `canvas` y `scene`. `derived` puede existir, pero se ignora siempre al leer. Las escrituras son atómicas y siempre v2. Las primitivas mantienen sus identificadores y orden al guardar y abrir.

`canvas` tiene `Lx`, `Ly` (m), `nx`, `ny`, `material: {k,rho,cp}`, `initial: {type,temperature,amplitude,sigma}`, `time`, `defaultBoundary`, `boundaries` e `interfaceMean`. Los perfiles iniciales son `uniform`, `sine`, `gaussian`. `time` contiene `dt` (null o ausente = automático), `tEnd` (null o ausente = sin límite), `safety`, `steady`, `rtol`, `atol`, `checkEvery`, `confirmations`, `maxSteps`. Los parámetros adicionales de tiempo/convergencia son opcionales al leer y usan los defaults del solver; una condición puede omitir `value` y `h` para usar cero. `interfaceMean` acepta `Armónica`, `Aritmética`, `Geométrica`.

`boundaries` tiene claves `top`, `right`, `bottom`, `left`. Un lado ausente hereda `defaultBoundary`; la ausencia se conserva al guardar. Una condición es `{kind,value,h}`: `Adiabático`, `Dirichlet`, `Neumann` o `Robin`. `value` representa °C para Dirichlet/Robin y flujo saliente W/m² para Neumann; `h` se expresa en W/m² K.

Cada primitiva necesita `id`, `type`, `geometry`. `name`, `locked` y `visible` son opcionales. Ocultar es una opción visual: no desactiva roles físicos. Selección e historial son estado de sesión, no datos físicos persistentes.

| `type` | Parámetros de `geometry` (metros salvo rotación) | Claves de contorno |
|---|---|---|
| `rectangle` | `x,y` esquina inferior izquierda; `width,height`; `rotation` en grados alrededor del centro | `top,right,bottom,left` en coordenadas locales |
| `circle` | `x,y` centro; `radius` | `edge` |
| `ellipse` | `x,y` centro; `radiusX,radiusY`; `rotation` en grados | `edge` |
| `segment` | `points`, dos puntos `{x,y}` | `edge` |
| `polyline` | `points`; `closed` opcional, true para polígono | `edge` o índice inicial `0,1,…` |
| `region` | `regionSeed: {x,y}` y `regionBoundaries: [id,…]` | `edge` como fallback; prevalece la condición del trazo que genera la cara |
| `legacyMask` | `raster` booleano por nodo en orden j*nx+i; `rasterGrid: {nx,ny,lx,ly}` | `edge` |

Los bloques independientes opcionales son `domain: {operation}` (`union`, `subtract`, `replace`), `material: {k,rho,cp}`, `source: {Q,unit,type}` y `boundaries: {segmento: condición}`. Las fuentes abiertas usan `type: line`, `unit: W/m`; las regiones cerradas usan `type: area`, `unit: W/m³`. Los polígonos se representan como polilíneas cerradas. Los segmentos y polilíneas abiertos con dominio/material se rasterizan como trazos de media celda de tolerancia; para regiones de área usar geometrías cerradas.

Las regiones delimitadas (`region`, incorporadas en 0.9.1) se derivan por componentes conexas en la grilla cartesiana: las intersecciones con trazos y los cambios dentro/fuera de figuras cerradas bloquean la conectividad durante esta identificación. No eliminan una franja ni cambian por sí solos el operador. `regionSeed` identifica la componente seleccionada y `regionBoundaries` referencia los límites que existían al asignarla. Cada región admite los mismos roles; al excluirla se atribuye el contorno al trazo cruzado, respetando la condición de su subsegmento. Con ambos lados activos se conserva la interfaz conductora sin condición de borde interna. La identificación depende de la resolución; regiones más estrechas que la grilla pueden no distinguirse. Las coordenadas de muestra se desplazan una fracción de celda para resolver empates de nodos sobre una línea. Los límites referenciados deben existir; al borrar uno, el editor elimina las regiones dependientes dentro de la misma operación deshacible.

`canvas.uniformSource` es opcional (default 0 W/m³). La fuente uniforme del panel se suma a las fuentes por primitivas, se conserva al guardar y solo actúa en nodos activos.

La evaluación arranca con todo el lienzo activo. Aplica operaciones de dominio en orden; luego materiales con última coincidencia ganadora; luego suma fuentes. Las fuentes de área conservan el muestreo 8×8 de v1 en cada volumen dual. Las fuentes de línea usan recorte Liang–Barsky sobre cada volumen dual, con celdas semiabiertas para evitar duplicar una línea coincidente con un límite. Se asume profundidad unitaria de 1 m para convertir W/m a W/m³. La potencia conservada es la longitud dentro de los volúmenes duales activos de la máscara discretizada; cerca de una curva difiere de la longitud dentro de la curva ideal.

Cada cara expuesta conserva nodo, dirección, propietario, subsegmento y condición. Una cara exterior pertenece al lienzo. Una interior pertenece a la operación cronológica que creó su separación activa/inactiva; las operaciones posteriores que recrean esa separación actualizan el propietario. Una operación que afecta ambos nodos sin cambiar la separación no roba el contorno. La proximidad se mide en la geometría local rotada; en empates de distancia se prioriza la alineación con la dirección de la cara para evitar mezclar lados en las esquinas; el orden top/right/bottom/left resuelve los empates restantes.

Dirichlet exterior fija el nodo (promedia esquinas); Dirichlet interior aporta pérdida a media celda. Robin exterior usa h sin resistencia extra, Robin interior usa `1/(1/h+d/(2k))`. La cota usa beta 4 cuando el mapa contiene caras internas Dirichlet o Robin con h>0; beta 2 en otro caso. El kernel y sus buffers privados permanecen sin cambios; recibe coeficientes ya derivados en Float.

La migración v1 conserva la máscara exacta del operador anterior como `legacyMask`, con su condición global aplicada a `edge`. Regiones rectangulares y fuentes se convierten a primitivas; los lados exteriores conservan sus condiciones. `geometry.legacyShape: materialV1` mantiene los intervalos semiabiertos de los materiales heredados. Si se cambia la grilla, la máscara legacy se remuestrea por nodo más cercano desde `rasterGrid`; las primitivas nuevas se evalúan analíticamente en la nueva grilla. El array legacy se almacena sin comprimir en esta fase.

## Límite geométrico medido

El contorno escalonado no garantiza convergencia de Robin al círculo ideal. Para un círculo de radio 0,2 m, las longitudes cartesianas tienden a 8r = 1,6 m; el perímetro ideal es 2πr ≈ 1,25664 m. Con h=15 y k=401, el ensayo de conductancia a temperatura uniforme da:

| nx=ny | Conductancia escalonada W/K | Ideal W/K | Diferencia |
|---|---:|---:|---:|
| 41 | 24,744215 | 18,849556 | +31,27 % |
| 81 | 24,372151 | 18,849556 | +29,30 % |
| 161 | 24,186086 | 18,849556 | +28,31 % |

El límite sin ponderación es 24 W/K (+27,32 %), no el ideal. Esto contradice el criterio de aceptación de convergencia al balance circular ideal sin corrección geométrica. Se conserva la fórmula solicitada y se informa la limitación en el editor; alcanzar ese criterio requiere ampliar el alcance para ponderar caras u otra discretización. No se afirma equivalencia completa Python/Metal.

## Selección por lados y trazos (0.9.2)

El inspector de una región deriva la lista de bordes a partir de su máscara y de los trazos originales: los lados del lienzo usan sus claves `bottom/right/top/left`, y cada corte o tramo conserva su `owner` y clave de subsegmento. La región no se presenta como un único `edge`. Las asignaciones desde esa lista escriben en el lado del canvas o en `boundaries` del trazo original. Un `region.boundaries.edge` de archivos anteriores continúa como fallback interno, por debajo de una condición explícita del trazo. En las polilíneas los empates geométricos junto a un vértice se resuelven con la alineación de la normal de la cara.

El nombre visible Robin / Cauchy corresponde a `kind: Robin`, q saliente = h (T − T ambiente); no se crea otro tipo ni se cambia su formulación en el solver. Ejemplo: `examples/trapecio_bordes_v2.json`.

## Separadores y fuentes superpuestas (0.9.3)

`ScenePrimitive.dividesRegions` es un booleano opcional. Identifica el uso de una geometría como separador durante la selección/evaluación de regiones; no habilita ni elimina sus roles físicos. Las herramientas nuevas guardan `true` para cortes/dominio y `false` para fuentes, materiales superpuestos y referencias. Cuando falta el campo, una geometría con dominio sigue delimitando; una fuente sin dominio se trata como superposición; los materiales sin fuente conservan el comportamiento histórico de separador. Esta inferencia también evita que identificadores de fuentes capturados en `regionBoundaries` por versiones anteriores generen huecos en el dominio elegido.

Al activar fuente o material sobre un límite ya referenciado se conserva explícitamente `dividesRegions: true`. Los botones de roles de una región no cambian su operación de dominio: `replace`, `subtract`, `union` o ausencia permanecen intactos. La eliminación de una fuente no separadora limpia sus referencias antiguas sin eliminar las regiones; borrar un separador sí mantiene el borrado de sus regiones dependientes dentro de la operación deshacible.

`sourceContributions` es un diagnóstico en memoria por primitiva: potencia neta, potencia absoluta y nodos con contribución dentro de la máscara activa. No se serializa como fuente de verdad. Las fuentes se siguen sumando y recortando al dominio discretizado, con las unidades y la formulación anteriores. El ejemplo `trapecio_fuente_v2.json` aporta aproximadamente 50,287 kW en 102 nodos de una grilla 65×65; su intensidad es 10 MW/m³, con profundidad unitaria.

### Edición de mano alzada (0.9.4)

Los contornos cerrados se guardan como `polyline` con `geometry.closed=true`, sin repetir el primer vértice al final. Un gesto que vuelve a menos de 12 px del inicio se cierra automáticamente; también se puede cerrar desde el inspector. La captura no aplica snap a la mano alzada y elimina muestras consecutivas idénticas. La propiedad se asigna después de dibujar. Fuentes interiores usan `area` / `W/m³`; fuentes sobre trazos abiertos usan `line` / `W/m`. Cerrar una fuente de línea cambia su interpretación a área, conservando el valor numérico Q mostrado con su nueva unidad.


## Método estacionario (Metal 0.10.0)

`canvas.time.method` es opcional: `explicit` (predeterminado para archivos anteriores) o `jacobi`. Solo tiene efecto con `canvas.time.steady = true`. Con Jacobi, `checkEvery` y `maxSteps` cuentan iteraciones algebraicas; `dt`, `safety` y `tEnd` no controlan dichas iteraciones. Se conservan las validaciones escalares del escenario para poder volver al modo temporal. El formato v1 admite el campo opcional `steady_method` con los mismos valores. El guardado sigue siendo v2.


## Integrador temporal (Metal 0.11.0)

`canvas.time.temporalMethod` es opcional: `explicit` (predeterminado) o `crankNicolson`. Se conserva `canvas.time.method` para elegir entre evolución temporal y Jacobi estacionario directo. Con `steady = true` y `method = jacobi`, se ignora el integrador temporal.

`canvas.time.cn` es opcional y acepta campos parciales:

```json
{"stepFactor":10,"rtol":1e-5,"atol":1e-6,"maxIterations":2000,"checkEvery":16,"rannacher":false}
```

`atol` está en K para el residuo del sistema de incrementos. `stepFactor` afecta únicamente dt automático CN; dt manual sigue teniendo prioridad. Cada sistema tiene su propio máximo de iteraciones (dos sistemas en el primer paso físico si se activa `rannacher`). La lectura v1 admite `temporal_method` y `cn`. La ausencia de los nuevos campos mantiene Euler explícito y las opciones CN predeterminadas; el guardado sigue siendo v2.
