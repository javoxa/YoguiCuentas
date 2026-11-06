# Devolución M1 — integración de paridad, 29/10/2026

**Estado:** cambios numéricos y de exportación integrados; campaña automatizada
aprobada. App candidata compilada y firmada localmente, preparada para las
primeras pruebas de uso. **Producción pendiente** de revisión visual y primera
instalación en otra Mac. No hubo publicación ni cambio de etiquetas.

## Identificación y equipo

Entrada: `avances/YoguiCuentas_Metal_M1_desarrollo_20261029.tar.gz`, SHA-256
`7ac4b224958411ca45bfb40388ba43508a3f90852c398ff871497e0c6830de8e`.
El manifiesto interno se verificó completo; no se recibió el checksum externo
anunciado en la guía. Base recibida: commit Linux
`58742d505561a9e75466dca0ec0f748e0b285dc0`, árbol modificado, OpenCL 0.2.4 / Metal 0.11.0.
La entrada extraída se conserva y `metal_antes.tar.gz` permite recuperar el estado
anterior. Fuentes finales: `codigo_metal_final.tar.gz` y `fuentes_finales.sha256`.

Apple M1, GPU 7 núcleos, RAM unificada 8 GiB; macOS 15.4.1 (24E263), arm64,
Xcode 16.4, Swift 6.1.2. En batería y sin aislamiento de carga. Los registros
`final-02/equipo.txt` y `final/equipo.txt` rodean la medición de costo; no se
midió potencia eléctrica ni se fijó un perfil de rendimiento.

## Integración y correcciones

- Se incorporaron Gauss–Seidel rojo–negro ω=1 CPU/Metal, criterios, selectores,
  persistencia y tests preparados en Linux. Jacobi conserva ω=2/3; CN conserva
  su Jacobi interno y el rechazo del lote completo.
- Se corrigieron inicialización prematura de `self` en SimulationModel y
  `Scenario.alpha` inexistente en el ensayo (se usa k/C). Logs de ambos errores conservados.
- Tolerancias físicas: finitas, no negativas, al menos una positiva; se verifica rtol=0.
- Historial de 512 controles, contador de descartes, CSV exportable y limpieza al reiniciar.
- CSV de campo acompañado de JSON de escenario/metadatos e historial del mismo
  campo confirmado, con método, procesador efectivo, pasos/iteraciones, tiempo
  cuando corresponde, tolerancias, auditoría y condición real de parada.
- Cambio de procesador reinicia y detiene; los trabajadores CPU atienden
  cancelación entre pasos/barridos. Se adaptó una aserción antigua de mensaje
  al nuevo contrato; sus comprobaciones físicas se conservaron.
- LICENSE/NOTICE se incluyen dentro de la carpeta Metal: el empaquetado vuelve
  a funcionar con la carpeta independiente, además de admitir la estructura del traspaso.
- Se corrigió el recolector para Bash 3.2 y se guardan los registros JSON
  directamente: una corrida sufrió intercalación stdout/stderr de XCTest.
  No se reconstruyeron mediciones a mano; se repitió la campaña.
- No se modificaron los umbrales de los tests recibidos. El ensayo adicional
  de círculo 17²/33²/65² declara residuo 1e-4 K/s; el original 33² conserva 5e-5.

## Evidencia automática

| Corrida | Resultado | Alcance |
|---|---|---|
| swift-test-inicial.log | No compila por sandbox | No evidencia numérica |
| swift-test-integracion-01.log | Error de inicialización Swift | Corregido |
| swift-test-integracion-02.log | Error alpha inexistente | Corregido |
| swift-test-integracion-03.log | 89 tests, 1 aserción de mensaje fallida | Numérica aprobada; aserción adaptada al contrato de reinicio |
| complementaria-01 | Recolector Bash falló antes de ejecutar tests | Conservado |
| complementaria-02 | 100 tests aprobados, 0 fallos/omisiones | Familias adicionales iniciales |
| final | 103 aprobados, 0 fallos/omisiones | Un registro JSON se intercaló en consola |
| **final-02** | **103 aprobados, 0 fallos/omisiones** | **Evidencia final, 60 filas NUMERIC y 158 registros JSON íntegros** |

La campaña final ejercitó CPU Swift float32 y GPU Apple M1 Metal float32.
No hubo fallback inadvertido a CPU. Se verificaron energía, soluciones
analíticas, flujo armónico, Neumann/Robin, orden temporal y espacial suave,
GS por barrido independiente, máscara circular, CN oscilatorio/Rannacher,
rechazo de lote, reset/cancelación y formatos/exportación.

Los 158 registros comprenden 144 casos de criterios (4 métodos × 2 procesadores
× todos/muestra × 9 criterios), seis refinamientos de círculo, cuatro factores
modales y cuatro balances. Las paradas de esos 144 casos fueron 72 converged y
72 max_steps; los casos separados de dt diminuto verifican criterion_met sin
atribuir estacionario. Sus resultados no se mezclan con la tabla de 144 casos.

## Resultados numéricos y costos

- Órdenes temporales Euler≈1, CN≈2; espaciales suaves≈2 (tabla completa en el informe).
- Balance independiente Neumann/Robin: máximo error absoluto 7.88148e-8 J/m,
  contra límite 2e-6 J/m. CN integra el flujo con promedio temporal.
- dt·λ=4: factor CN≈−1/3 y Rannacher≈+1/9 en ambos procesadores.
- Círculo Metal: L∞≈0.0129054, 0.00603398, 0.00269434 K a 17²/33²/65².
  Se reporta área y residuo separadamente; no se afirma orden dos en frontera curva.
- Se compara con Linux mediante 48 pares de errores de referencias analíticas,
  en `comparison_linux_m1.csv`; no son diferencias campo a campo con A2000.
- `benchmark-final`: 120 tiempos (5 tamaños, 4 métodos, 2 procesadores, 3 repeticiones),
  compilación -O, calentamiento 4 pasos, medición 64 pasos/barridos.
  Inicialización excluida; transferencia y todas las iteraciones CN incluidas.
  La compilación de la app finalizó antes de medir (22:37:08 UTC; costo 22:37:37–49 UTC).
- Diferencia máxima Swift/Metal en campos a igual conteo fijo: 1.54972e-6 K.
  Los campos/scenarios 17² y 65² se conservan. CPU supera a GPU en casos pequeños;
  a 257² Metal resulta más rápido en estos ensayos. No se promete aceleración universal.

## App y aceptación manual

Build local `20261029223645`, arm64, base 0.11.0. `build-app.log`, `codesign.log`
y `binario.sha256` identifican la candidata. La verificación estricta de firma
ad hoc pasó; recursos, iconos y licencias están incluidos. Se solicitó apertura.
No se inspeccionó visualmente la ventana: la herramienta respondió
“Computer Use was not approved to use YoguiCuentas Metal”. No se inventan capturas.

`PRIMERAS_PRUEBAS.md` detalla los controles pendientes: clics, criterios,
editor/contornos, isotermas/PNG/3D, paneles de exportación y primera instalación.
No se verificó Gatekeeper en otra Mac, Developer ID ni notarización.

## Límites y devolución

Metal sigue devolviendo campos al host y evaluando criterios allí. La reducción
OpenCL de 15 escalares no se implementó en Metal. Permanecen los límites
float32 y geométricos de la grilla cartesiana; no se incorporan mallas polares,
multigrid ni física no lineal. No se certifica la producción antes de la aceptación manual.

Informe nuevo: `technical_report/informe_campana_m1_20261029.tex`, con figuras
vectoriales embebidas; el informe histórico del 26/10 permanece intacto.
El generador `technical_report/scripts/render_campaign.py` produce tablas y
comparaciones desde los registros conservados, usando Python estándar.
