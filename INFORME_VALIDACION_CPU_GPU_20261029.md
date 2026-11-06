# Validación CPU/GPU de YoguiCuentas — campaña del 29/10/2026

Candidata de entrega: Linux **0.2.5**, Metal **0.12.0**; sin publicar.

## Resultado y alcance

La campaña recibida del M1 registra **103 XCTest aprobados, sin fallos ni omisiones**. Se revisaron de forma independiente en Linux la integridad, los datos y las cuentas de los resultados; no se ejecutó Metal en Linux. Las fuentes verificadas del M1 se incorporaron a `metal/yoguicuentas_metal`, con copia de respaldo del estado previo y sin modificar la devolución original.

La referencia Linux conserva **155 unittest aprobados y 2 omisiones de clic nativo por escritorio bloqueado**, además de **217 comprobaciones numéricas aprobadas**. Los conteos corresponden a campañas y casos diferentes; no deben sumarse como si fueran pruebas independientes equivalentes.

Está verificado el alcance numérico ensayado. La aceptación visual, la primera instalación en otra Mac, Gatekeeper y la notarización siguen pendientes. El programa continúa siendo un prototipo educativo sobre grilla cartesiana estructurada.

## Integridad y procedencia

- Entrada M1: paquete de desarrollo SHA-256 `7ac4b224958411ca45bfb40388ba43508a3f90852c398ff871497e0c6830de8e`.
- Manifiestos recibidos: 71/71 archivos finales, 32/32 fuentes de XCTest, 18/18 del benchmark y 1.374/1.374 archivos de entrega coinciden.
- Las fuentes Swift y XCTest del proyecto coinciden con los manifiestos de la campaña y del benchmark. Después de la integración, el script `crear_app.sh` cambia únicamente su versión predeterminada de 0.11.0 a 0.12.0 para la candidata; ese metadato de empaquetado es posterior a la campaña.
- El binario recibido coincide con su SHA-256 registrado: `22ae2a2609a65878a755ebc0b64570f4e3b8c9c6581096444e6af9b2e2d9237d`.
- La firma ad hoc está respaldada por el log macOS recibido. Aquí se comprobó el hash del binario; no se reejecutó `codesign` en Linux.
- Se preservaron los fallos de integración previos y la corrida final `final-02`; las fuentes finales no son la instantánea histórica del informe Metal 0.11.0.

Equipo M1: Apple M1, GPU de 7 núcleos, RAM unificada de 8 GiB, macOS 15.4.1 (24E263), arm64, Xcode 16.4, Swift 6.1.2. Las mediciones se realizaron en batería, sin aislamiento de carga y sin medir potencia eléctrica. Referencia Linux: Ryzen 9 5900X y RTX A2000, NumPy float64/OpenCL float32. Swift y Metal usan float32.

## Cambios que quedaron integrados

- Gauss–Seidel rojo–negro CPU/Metal y verificación contra un barrido independiente; Jacobi conserva su ponderación y CN su solver interno.
- Nueve criterios de parada, muestra reproducible, persistencia y auditoría física con confirmaciones independientes.
- Correcciones de inicialización Swift y del ensayo que usaba una propiedad `alpha` inexistente.
- Tolerancias físicas no negativas con al menos una positiva; aceptación de `rtol=0`.
- Historial acotado a 512 controles, truncamiento indicado y limpieza al reiniciar.
- Exportación de campo con escenario, metadatos e historial coherentes; procesador efectivo, pasos o iteraciones y tiempo físico según corresponda.
- Cambio de procesador con reinicio y detención; atención de cancelación en trabajadores CPU.
- Empaquetado con licencias locales o de la raíz; recolección compatible con Bash de macOS y registros JSON escritos directamente para evitar intercalación de consola.

## Exactitud y convergencia

| Familia | Swift float32: órdenes sucesivos | Metal float32: órdenes sucesivos |
|---|---:|---:|
| Temporal Euler | 1.0275 / 1.0135 | 1.0275 / 1.0135 |
| Temporal CN | 2.0011 / 2.0159 | 2.0011 / 2.0159 |
| Espacial Euler | 2.0047 / 1.9456 | 2.0065 / 1.9410 |
| Espacial CN | 1.9953 / 1.9795 | 1.9953 / 1.9820 |

Los órdenes corresponden a casos suaves con referencias analíticas o semidiscretas. No garantizan el mismo orden para una discontinuidad material o una frontera rasterizada. Se verificaron 60 mediciones NUMERIC y 158 registros JSON íntegros: 144 casos de criterios, seis círculos, cuatro factores modales y cuatro balances.

Máximo error absoluto del balance transitorio independiente Neumann/Robin: **7.88148e-08 J/m**, frente al límite declarado de 2e−6 J/m. Los factores de alta frecuencia reproducen CN≈−1/3 y Rannacher≈+1/9 en CPU y GPU.

## Criterios y exportaciones

Los 144 casos combinan cuatro métodos, dos procesadores, todos/muestra y nueve criterios. Se verificaron los 144 conjuntos de campo CSV, escenario JSON, metadatos e historial: coordenadas, tamaño, temperaturas finitas, procesador solicitado/efectivo, paso final y condición de parada son coherentes.

Hubo **72 `converged` y 72 `max_steps`**. Los límites pertenecen al ensayo deliberadamente corto de 64 pasos; no significan que 72 tests fallaran ni que todos los criterios alcanzaran el estacionario. Los casos de dt diminuto son pruebas separadas que exigen `criterion_met` sin afirmar convergencia física.

## Frontera circular: resultados y límite geométrico

En el círculo Dirichlet de R=0.31 m, k=1, Q=4 y T de borde 0, los errores Metal L∞ son aproximadamente 0.0129054, 0.00603398 y 0.00269434 K para 17², 33² y 65² nodos. El refinamiento mejora ese ensayo; la tolerancia algebraica del ensayo complementario es 1e−4 K/s y se distingue del error geométrico.

El contorno **Robin circular** presenta un límite distinto y material para la interpretación:

| Grilla | Conductancia discreta [W/K] | Ideal [W/K] | Error relativo |
|---|---:|---:|---:|
| 41² | 24.744215 | 18.849556 | 31.272% |
| 81² | 24.372151 | 18.849556 | 29.298% |
| 161² | 24.186086 | 18.849556 | 28.311% |

La frontera escalonada mide longitudes de caras cartesianas, no la longitud euclídea de la circunferencia. El sesgo observado es compatible con el exceso geométrico límite `4/π−1≈27.32%`. **Aumentar los nodos no basta para eliminar este sesgo de Robin.** No es un fallo de convergencia del sistema lineal; se resuelve el problema discreto con esa representación geométrica. Una prueba aprobada aquí documenta el sesgo, no certifica exactitud frente al círculo físico.

Una futura discretización polar o una representación conservativa de contornos adaptados debe incorporar longitudes/áreas y normales adecuadas, con nuevas pruebas. Una grilla polar puede ser estructurada; no se implementó ninguna de esas extensiones en esta campaña.

## Comparación entre procesadores y equipos

En las 120 mediciones se registró una diferencia máxima Swift/Metal de **1.54972e-06 K** a igual conteo fijo. Se recalcularon ocho pares de campos 17²/65² reconstruyendo float32 desde los CSV: máximo **1.49012e-06 K**.

Los 48 pares Linux/M1 comparan **errores frente a referencias analíticas**, no campos M1 contra A2000. No justifican afirmar identidad bit a bit ni un ranking de rendimiento entre esas máquinas.

## Costo observado en M1

Cinco tamaños, cuatro métodos, dos procesadores y tres repeticiones: 120 tiempos. Compilación `-O`, calentamiento de cuatro pasos y medición de 64 pasos/barridos. Se excluye inicialización/compilación y se incluyen despacho, carga/lectura y las iteraciones internas CN.

| Método, 257² nodos | Mediana Swift [s] | Mediana Metal [s] | Tiempo Swift / Metal |
|---|---:|---:|---:|
| Euler | 0.016355 | 0.002231 | 7.33 |
| CN | 1.793044 | 0.350358 | 5.12 |
| Jacobi | 0.035471 | 0.002535 | 13.99 |
| GS | 0.041021 | 0.005071 | 8.09 |

CPU resulta más rápida en varios tamaños pequeños y Metal domina los ensayos mayores de esta campaña. Son observaciones del M1 en esas condiciones, no aceleraciones universales. Cada barrido GS incluye rojo y negro. No se compara igual tiempo físico o igual error entre métodos; CN ejecuta sus sistemas internos. El benchmark Linux tiene otra ruta de transferencia y condiciones de medida, por lo que no se usan estos tiempos para ordenar A2000 frente a M1.

## Qué falta antes de anunciar distribución verificada

1. Aceptación manual SwiftUI: selección, edición de contornos, criterios, isotermas/rótulos, barra de escala, 2D/3D y paneles de exportación. El modelo se probó, pero no hay inspección visual ni capturas del M1.
2. Primera apertura e instalación de la candidata en otra Mac. Firma local ad hoc no equivale a Developer ID ni notarización.
3. Instalación/desinstalación final del `.deb` en Debian/Devuan de destino y arranque CPU automático; las pruebas numéricas no reemplazan esa prueba.
4. Repetición de las dos pruebas Linux de clic nativo cuando el escritorio esté disponible.
5. Mantener explícitos el sesgo Robin curvo, la precisión float32, las tolerancias y el costo de transferencias.

## Evidencia y reproducción de esta revisión

- [Auditoría recalculada](verification/2026-10-29/m1-review/audit.json).
- [Devolución M1](verification/2026-10-29/m1/RESUMEN_M1.md) y [aceptación manual pendiente](verification/2026-10-29/m1/PRIMERAS_PRUEBAS.md).
- [Log final XCTest](verification/2026-10-29/m1/final-02/swift-test.log), [CSV numérico](verification/2026-10-29/m1/final-02/mediciones.csv) y [registros de campaña](verification/2026-10-29/m1/final-02/campaign.jsonl).
- [Tiempos originales](verification/2026-10-29/m1/benchmark-final/timings.csv) y [comparación de errores Linux/M1](verification/2026-10-29/m1/comparison_linux_m1.csv).
- [Referencia Linux del 28/10](verification/2026-10-28/RESUMEN.md) y [criterios del 29/10](CRITERIOS_ESTACIONARIO.md).
- La carpeta recibida `metal_test_00` queda intacta; la selección pública de evidencia omite binarios, archivos comprimidos duplicados y metadatos de Finder. Cada archivo seleccionado tiene hash en `verification/2026-10-29/m1/MANIFIESTO_EVIDENCIA.sha256`.
- La devolución contiene además `metal_test_00/technical_report/informe_campana_m1_20261029.tex`; se conserva como documento recibido, separado del informe técnico histórico Metal 0.11.0.

Para repetir la auditoría sobre la devolución original desde la raíz del proyecto:

```bash
.venv/bin/python verification/revisar_m1.py metal_test_00 \
  --output verification/2026-10-29/m1-review
```

La auditoría no ejecuta código recibido. Verifica hashes, integridad de registros, coherencia de exportaciones y vuelve a calcular órdenes, comparaciones y resúmenes. No recompila Swift ni reejecuta la firma macOS en Linux.
