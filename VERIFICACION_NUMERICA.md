# Verificación numérica y alcance educativo

Campaña de desarrollo del 28/10/2026, posterior al paquete 0.2.4. Los cambios
locales incorporan Gauss–Seidel y verificaciones cuantitativas; no modifican por
sí mismos una Release ya descargada. El informe Metal 0.11.0 conserva su alcance
histórico. Los resultados de esta campaña se identifican por un hash de las
fuentes numéricas y el estado Git, además de la fecha.

Los criterios de parada agregados el 29/10 y sus comparaciones están en
[CRITERIOS_ESTACIONARIO.md](CRITERIOS_ESTACIONARIO.md). La evidencia del 28/10
se conserva como registro de ese árbol de desarrollo.

## Qué problema se discretiza

La aplicación resuelve conducción térmica bidimensional sobre una **grilla
cartesiana estructurada**, uniforme en cada eje: `dx=Lx/(nx−1)`, `dy=Ly/(ny−1)`.
Los espaciamientos pueden ser distintos. Un stencil de cinco puntos conecta
vecinos horizontales y verticales; los balances se construyen sobre volúmenes
duales. Las magnitudes energéticas se expresan por metro de espesor.

Las figuras del editor se rasterizan sobre esa misma grilla. Un círculo dibujado
no crea una malla polar ni elementos curvos: selecciona nodos activos y caras
de contorno escalonadas. Refinar mejora su aproximación, pero aumenta memoria,
trabajo por iteración y, en Euler, el número de pasos necesario para alcanzar
un mismo tiempo físico. No se promete orden espacial dos para esas fronteras.

El objetivo es educativo: observar conservación, precisión, estabilidad,
convergencia, límites de los métodos y costo al aumentar los nodos. Un solver
que converge no demuestra por sí solo que la grilla o el paso temporal resuelvan
adecuadamente el problema continuo.

## Métodos disponibles en el desarrollo actual

| Método | Qué avanza | Condiciones y límites |
|---|---|---|
| Euler explícito | Tiempo físico | Paso restringido por difusión y pérdidas de contorno |
| Crank–Nicolson | Tiempo físico | Orden temporal dos en soluciones suaves; sistemas internos con Jacobi ponderado; pasos grandes pueden oscilar |
| Jacobi ponderado, ω=2/3 | Iteraciones estacionarias | Sin tiempo físico; requiere referencia de temperatura en cada componente |
| Gauss–Seidel rojo–negro, ω=1 | Iteraciones estacionarias | Una iteración es un barrido rojo y uno negro; mismos requisitos de referencia |

Gauss–Seidel está en **Configurar corrida → Estacionario**, en CPU NumPy y
OpenCL y en CPU Swift/GPU Metal, verificados en el M1.
La palabra «directo» en la interfaz indica que se resuelve el sistema
estacionario sin evolución temporal: Jacobi y Gauss–Seidel siguen siendo
métodos algebraicos **iterativos**, no métodos directos de factorización.
Ejemplo: `estacionario_gauss_seidel.json`. En consola:

```bash
bash ejecutar.sh --console --backend numpy --steady-method gaussSeidel --output resultados/gs_cpu
bash ejecutar.sh --console --backend opencl --device 1 --steady-method gaussSeidel --output resultados/gs_gpu
```

El identificador JSON es `gaussSeidel`, tanto en v1 como en v2. Los CSV registran
iteraciones y dejan vacío el tiempo físico. Este agregado no cambia el solver
interno de CN a Gauss–Seidel. La ordenación rojo–negro no produce los mismos
iterados intermedios que un barrido lexicográfico; ambas son ordenaciones de
Gauss–Seidel. En GPU se usan dos despachos ordenados con buffers separados,
evitando carreras entre grupos. Referencia: [Templates, Netlib/SIAM](https://www.netlib.org/templates/templates.html).

## Ensayos reproducibles

`yoguicuentas.verification` ejecuta las mismas familias en NumPy float64 y
OpenCL float32. No requiere ventana ni OpenGL. Pedir OpenCL sin un dispositivo
disponible es un fallo explícito, nunca una omisión silenciosa.

| Familia | Referencia independiente | Qué se comprueba |
|---|---|---|
| Energía aislada | Suma de `ρ cp V T` y aporte integrado `Q V dt` | Euler/CN, caja/elipse, materiales heterogéneos, con y sin fuente |
| Intercambio de contorno | Integral del flujo saliente | Neumann/Robin; flujo al inicio para Euler y promedio temporal para CN |
| Refinamiento temporal | Exponencial exacta del autovalor discreto | Orden uno de Euler y dos de CN sin mezclar error espacial |
| Refinamiento espacial | Modo senoidal de la ecuación continua | Grillas 17×9, 33×17 y 65×33; `dx` y `dy` distintos |
| Placa 1D embebida en 2D | Perfil parabólico con fuente | Euler hasta estacionario, Jacobi y Gauss–Seidel |
| Interfaz de materiales | Resistencias en serie, perfil por tramos | Media armónica, continuidad de flujo e invariancia transversal |
| Contornos mixtos | Perfil lineal Neumann/Robin | Signos del flujo y disipación |
| Círculo con fuente | `T=Q(R²−r²)/(4k)` | Error geométrico con 17², 33² y 65² nodos; conservación de nodos inactivos |
| Paso grande de CN | Factor de amplificación −1/3; con Rannacher +1/9 | Estabilidad no equivale a ausencia de oscilaciones |
| Precisión finita | Tolerancia de residuo 1e−10 K/s en float32 | Un caso que se estanca debe informar límite sin convergencia |
| CPU/GPU | Comparación de campos de cada ensayo | Error máximo por experimento, además de las referencias analíticas |
| Costo | 64 pasos/barridos tras calentamiento | Tiempo observado según nodos y método, sin incluir compilación |

La interfaz de los dos materiales está colocada a mitad entre nodos. Esto
separa el error del operador del error de representar una interfaz desplazada.
Las pruebas unitarias complementan estos ensayos con sistemas densos pequeños,
fuentes de línea y área, dominios desconectados, escenas v2, contornos por tramo,
rechazo de lotes CN no convergentes, reinicio y paso final abreviado.

Los órdenes se estiman con `p=log2(error_grueso/error_fino)` al dividir por dos
el espaciamiento o el paso temporal. Para Euler espacial se reduce `dt` como
`h²`; para CN se usa un paso pequeño, comprobando que el error temporal no domine.
Es una verificación de casos suaves, no una garantía de esos órdenes para toda
geometría, material discontinuo o condición inicial. Referencia metodológica:
[notas de diferencias finitas de Berkeley](https://persson.berkeley.edu/math228b/html/finite_difference_methods_for_PDEs.html).

### Tolerancias y límites de precisión

Las tolerancias son datos del ensayo y se guardan en `report.json`. Para CN se
usan `atol=1e−13 K, rtol=1e−12` en NumPy y `atol=1e−8 K, rtol=1e−6` en OpenCL.
Son distintas porque float64 y float32 tienen distinta precisión. No se cambian
automáticamente en la aplicación cuando un sistema falla.

Para los perfiles estacionarios se exige residuo absoluto `1e−10 K/s` en CPU y
`2e−5 K/s` en GPU, con tolerancia relativa cero. Se comprueba **además** el error
de temperatura, limitado a `2e−8 K` y `2e−4 K`, respectivamente; el error del
flujo de interfaz debe quedar bajo `1e−7` y `5e−4 W/m²`. El círculo usa residuos
`1e−9`/`1e−5 K/s`; su error contra el círculo continuo se informa por separado.

En los ensayos exploratorios de la A2000, pedir residuos de alrededor de
`1e−6 K/s` o menores produjo estancamiento en algunos perfiles float32. Por
ejemplo, el caso mixto de Gauss–Seidel se estancó cerca de `2.27e−6 K/s`.
Esto motivó separar el ensayo de precisión finita del ensayo de exactitud,
en lugar de presentar el límite de iteraciones como convergencia. También se
detectaron tolerancias CN inferiores al piso de redondeo del sistema GPU;
la configuración anterior rechazó correctamente el lote. Las tolerancias de
esta campaña están publicadas para que el resultado no dependa de ajustes ocultos.

### Ejecutar en esta workstation

```bash
cd /home/javo/Programas/opencl/YoguiCuentas
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas --list-devices
env -u CUDA_VISIBLE_DEVICES .venv/bin/python -m yoguicuentas.verification \
  --backend all --device 1 --output verification/local
env -u CUDA_VISIBLE_DEVICES YOGUI_TEST_DEVICE=1 YOGUI_TEST_GL=1 \
  .venv/bin/python -m unittest discover -s tests -v
```

En esta estación el índice **1 es la RTX A2000**; el índice es local y debe
consultarse de nuevo en otro equipo. No usar la A4000 reservada para otros trabajos.
Los tiempos sobre la A2000 pueden incluir la carga del escritorio; no son un
benchmark exclusivo ni justifican prometer una aceleración universal.

Para CPU sin PyOpenCL ni entorno gráfico:

```bash
python3 -m yoguicuentas.verification --backend numpy --output verification/local
```

Los resultados son `report.json` (equipo, hash de fuentes, tolerancias, métricas
y comprobaciones), `experiments.csv` y `README.md`. El proceso sale con código
distinto de cero si falla una comprobación. `--skip-benchmark` omite solo las
mediciones de costo. La CI ejecuta la campaña NumPy en pushes/PR y antes de
publicar los paquetes; la GPU se verifica en hardware real.

## Verificación en Mac M1

Desde una copia actualizada del repositorio completo:

```bash
cd YoguiCuentas/metal/yoguicuentas_metal
bash verificar_numerica.sh
```

Requiere herramientas Apple con Swift 5.9 o posterior, como la compilación desde
fuentes. No basta con descargar la `.app` para ejecutar los XCTest. El script
ejecuta `NumericalVerificationTests`, `StationaryTests`, `CrankNicolsonTests` y
`ConvergenceCriteriaTests`;
guarda `equipo.txt`, `swift-test.log`, `mediciones.csv` y `exit-status.txt` en
`verification/numerica-FECHA-HORA`. Conserva esos cuatro archivos incluso si
fallan pruebas y traelos para analizar los resultados.

La campaña M1 comprueba órdenes temporal/espacial, energía, perfiles de fuente,
interfaz y contornos mixtos, Gauss–Seidel, máscara circular y los ensayos previos
de CN y Jacobi. **CPU Swift y GPU Metal usan float32**, no la referencia NumPy
float64. Por eso se reportan sus propias tolerancias. Si no hay dispositivo
Metal, XCTest lo informa como omitido y esa corrida no valida GPU.

La devolución M1 del 29/10 registra 103 XCTest aprobados, sin fallos ni omisiones.
Las fuentes finales se integraron y sus hashes coinciden con los ensayos recibidos.
El [informe integrado](INFORME_VALIDACION_CPU_GPU_20261029.md) documenta la revisión
independiente y el sesgo persistente de Robin sobre círculos escalonados.
La aceptación visual, Gatekeeper y la instalación de la app siguen pendientes. La instalación del `.deb` también sigue requiriendo las
pruebas independientes en Debian/Devuan de destino.

## Etapas siguientes de discretización

Se propone estudiar una grilla adaptada al círculo y la ecuación en coordenadas
polares planas `(r, θ)`, incluyendo tratamiento del origen, periodicidad angular,
balances y restricciones de paso. Una grilla polar **puede seguir siendo
estructurada**: cambiar coordenadas no equivale a usar una malla no estructurada.
Las mallas no estructuradas para geometrías generales son otra extensión del
modelo y del ensamblado, con sus propios ensayos de convergencia.

Adaptar la frontera puede reducir el error geométrico con menos nodos. No
elimina la necesidad de refinamiento ni los errores espaciales, temporales y
algebraicos. Estas extensiones no están implementadas en esta versión.
