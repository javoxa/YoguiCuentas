# Criterios de parada del estacionario

Desarrollo del 29/10/2026, posterior a la etiqueta 0.2.4. Selección en
**Configurar corrida → Estacionario → Criterio de parada**. Funciona con Euler,
CN, Jacobi y Gauss–Seidel, en NumPy y OpenCL. El mismo selector está preparado
en Swift/Metal; su compilación y ejecución siguen pendientes en el M1.

## Criterio que se usaba y que permanece predeterminado

Se evalúa el residuo físico nodal `r=f−A T`, en K/s, en todos los nodos libres.
No se observa simplemente si la imagen o las temperaturas cambiaron poco.
Se exigen simultáneamente:

- `R∞ = max |r_i| ≤ atol + rtol R∞_inicial`.
- `B1 = Σ |r_i| C_i V_i ≤ atol Σ C_i V_i + rtol B1_inicial`.

`C_i=ρ_i cp_i`; `V_i` es el área del volumen dual por unidad de espesor. El
segundo residuo se expresa en W/m de espesor: es una **suma absoluta local**,
no un balance global con signo en el que se puedan cancelar errores opuestos.
Los nodos inactivos y los de temperatura impuesta quedan fuera de los controles.

Por defecto se comprueba cada **128 pasos/iteraciones**, se exigen **3 controles
consecutivos** y se detiene sin convergencia al alcanzar **1 000 000 pasos**.
Las tolerancias predeterminadas son `atol=1e−5 K/s`, `rtol=1e−5`. No dependen
de dt ni del cero elegido para las temperaturas; no certifican por sí solas un
error de temperatura ni la precisión de la discretización.

## Criterios nuevos sobre el cambio de temperatura

Se define `D = T_control_actual − T_control_anterior`. El primer control se
compara con el campo inicial. No se comparan cuadros dibujados ni medios
barridos de Gauss–Seidel: se comparan campos físicos confirmados. Con
«Comprobar cada N pasos», D abarca N pasos, no necesariamente uno; usar N=1
permite comparar iteraciones consecutivas. El último control puede abarcar
menos pasos si coincide con el límite final.

Sea `S` el conjunto de nodos seleccionados y `n=|S|`. Para las normas matriciales,
se pone D=0 fuera de S. Las opciones son:

| Identificador | Medida | Observación pedagógica |
|---|---|---|
| `residual` | Máximo y balance físico anteriores | Predeterminado; siempre usa todos los nodos libres |
| `delta_l1` | `Σ_S |D_i|` | La suma crece con la cantidad de nodos |
| `delta_l2` | `sqrt(Σ_S D_i²)` | Norma euclídea del vector de nodos; equivale a Frobenius de la matriz |
| `delta_rms` | `sqrt(Σ_S D_i²/n)` | Promedio cuadrático; puede diluir cambios locales |
| `delta_linf` | `max_S |D_i|` | Máximo absoluto y norma infinito **nodal** son la misma medida |
| `delta_matrix_1` | `max_columna Σ_fila |D|` | Norma 1 matricial inducida |
| `delta_matrix_inf` | `max_fila Σ_columna |D|` | Norma infinito matricial; no es el máximo nodal |
| `delta_trace` | `|Σ_i D_ii|` | Traza solo si la matriz es cuadrada; en otra grilla, suma diagonal |
| `delta_mean` | `|Σ_S D_i/n|` | Cambio de la media, no media del cambio absoluto |

La traza y el cambio de media **no son normas**: pueden dar cero para un campo
de cambios no nulo. La traza además ignora todo lo que ocurre fuera de la
diagonal. La norma matricial 2, que requeriría el mayor valor singular, no se
confunde con la euclídea/Frobenius ni se ofrece como si fueran equivalentes.
Definiciones de referencia: [normas de matrices y vectores en NumPy](https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html).

### Tolerancias separadas

Los criterios D usan **kelvin**, no K/s: `valor ≤ delta_atol + delta_rtol escala`.
La escala se calcula con la misma norma sobre `T_actual−T_ref`, donde
`T_ref` es la temperatura inicial base del escenario. Para traza y media se usa
la suma/media de valores absolutos de esa referencia, evitando una escala que
se anule por cancelación. Los valores predeterminados son `delta_atol=1e−5 K`
y `delta_rtol=1e−5`. Cambiar grados Celsius por un cero desplazado no altera
el resultado si también se desplaza T_ref.

Las tolerancias del residuo físico se conservan como auditoría independiente.
No se convierten ni se sustituyen por las de D. Un dt muy pequeño puede hacer
D casi cero aunque la ecuación estacionaria esté lejos de satisfacerse; por
eso conviene comparar ambos controles en clase.

### Todos los nodos o una muestra

Las normas D pueden usar todos los nodos libres o una **muestra fija sin
reemplazo**, con cantidad y semilla configurables. Se excluyen nodos inactivos
y Dirichlet; si se piden más nodos que los disponibles se usan todos. La semilla
y selección son reproducibles entre CPU, OpenCL y el código preparado para Metal.

La muestra no se vuelve a sortear en cada control: así se observa la evolución
de los mismos sensores. Una muestra puede omitir un foco caliente o una región
que cambia. No proporciona una garantía sobre el campo completo. La traza
siempre usa la diagonal elegible y el criterio residual siempre usa todos los
nodos: en esas dos opciones el selector de muestreo se desactiva.

Una diagonal sin nodos libres no puede confirmar ese criterio. La aplicación
informa la falta de nodos y no la interpreta como una medida cero satisfactoria.

El residuo físico completo se calcula **siempre**, incluso al elegir una muestra.
Por eso el muestreo se ofrece para estudiar su alcance y sus fallos, sin prometer
que el control completo se vuelva proporcional al tamaño de la muestra. En
OpenCL el campo anterior permanece en GPU y solo se leen 15 escalares por
control: dos residuos y 13 acumuladores para las medidas D y sus escalas.

## Qué significa que la corrida se detenga

Se conservan contadores consecutivos **independientes** para el criterio elegido
y el residuo físico completo:

- **Estacionario alcanzado** (`converged`): criterio de parada cumplido y auditoría
  física confirmada durante el número de controles requerido.
- **Criterio ΔT cumplido; residuo físico sin confirmar** (`criterion_met`): la
  medida elegida permite detenerse, pero no se certifica el estacionario físico.
- **Límite sin convergencia** (`max_steps`): se agotaron los pasos sin confirmar
  el criterio elegido.

Una magnitud física no finita detiene el cálculo; no puede ocultarse detrás de
una traza o un cambio cero. No se relajan las tolerancias automáticamente.

## Guardar y comparar resultados

Los JSON v1 guardan `steady_criterion`, `steady_sampling`, `steady_sample_count`,
`steady_sample_seed`, `steady_delta_atol` y `steady_delta_rtol`. Los v2 guardan
esos parámetros dentro de `canvas.time.convergence`, sin el prefijo `steady_`.
Los archivos anteriores usan el residuo físico y todos los nodos por defecto.

La consola guarda las medidas finales, escalas, muestreo y auditoría en
`report.json`, además de `convergence.csv` con los últimos **512 controles**.
El informe indica si el historial se truncó; se limita su tamaño para no
acumular memoria durante corridas largas.

```bash
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas \
  --steady-method gaussSeidel --steady-criterion delta_linf \
  --steady-sampling random --steady-sample-count 32 --steady-sample-seed 123 \
  --backend opencl --device 1 --output resultados/criterio_muestra
```

Para repetir las **64 comparaciones** de criterios sobre una placa aislada,
incluido un caso con dt deliberadamente diminuto:

```bash
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas.compare_criteria \
  --backend all --device 1 --output verification/local/criteria
```

El equilibrio exacto de ese ensayo es la temperatura uniforme determinada por
la energía inicial. La tabla informa error al equilibrio, pasos y residuo real
en la parada. La campaña usa CPU NumPy y A2000, sin utilizar la A4000.

Resultados del 29/10: [comparación de criterios](verification/2026-10-29/criteria/README.md),
[suite completa](verification/2026-10-29/unittest.log),
[pruebas específicas](verification/2026-10-29/criteria-unittest.log) y
[campaña numérica](verification/2026-10-29/numerical/README.md).
En la suite completa: 155 pruebas aprobadas y 2 omitidas por escritorio bloqueado
(clic nativo). Las 10 pruebas de criterios, incluidos OpenCL e interfaz de
configuración, se ejecutaron; las 217 comprobaciones numéricas se aprobaron.

En M1: `bash verificar_numerica.sh` incluye ahora `ConvergenceCriteriaTests`.
Esos tests verifican normas, cancelaciones, la misma semilla de muestreo,
persistencia y el caso de dt pequeño. La campaña M1 aprobó los 103 XCTest y
produjo 144 casos de criterios; 72 alcanzaron convergencia y 72 agotaron el
presupuesto de 64 pasos, una salida prevista del experimento. Véase el
[informe integrado](INFORME_VALIDACION_CPU_GPU_20261029.md).
