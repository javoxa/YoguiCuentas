# Informe de revisión — YoguiCuentas Metal 0.12.0

Fecha: 6 de noviembre de 2026 (Argentina).
Proyecto revisado: `para_mc/yoguicuentas_metal`. La carpeta indicada como para_mac se encuentra en esta entrega con el nombre para_mc.

## Resultado

**Validación automática con un fallo; no aprobar todavía la candidata para publicación.** Se ejecutaron 105 XCTest: 104 aprobados y 1 fallido, sin omisiones registradas. La construcción release y la verificación de firma local terminaron correctamente. Se abrió la app nueva y se comprobó su proceso activo. Esto no certifica los recorridos visuales del protocolo manual.

## Entorno y trazabilidad

Apple M1, 8 GB RAM, GPU de 7 núcleos; macOS 15.4.1 (24E263), Xcode 16.4 y Swift 6.1.2. Versión empaquetada 0.12.0; build 20261106221536. Origen declarado: commit 317065cb65a1e8541bd29e6494465b81db45c40c. Integridad de entrada aprobada. No se editaron las fuentes Swift ni se ajustaron tolerancias.

Orden ejecutada: `bash para_mc/01_probar_mac.sh --benchmark`; apertura: `bash para_mc/02_abrir_app.sh`.

## Pruebas y hallazgo

Las suites numéricas, escenas, regiones, fuentes, convergencia, métodos estacionarios, Crank–Nicolson y contratos de paridad finalizaron sin fallos. Hubo ejecución real de CPU Swift y GPU Metal. El log completo contiene los resultados analíticos y de campaña; no se confunden los casos que alcanzan max_steps con convergencia.

Falló `LanguageTests.testLanguageChangesDoNotMutateScenarioOrCanonicalChoices`, en `Tests/SceneTests/LanguageTests.swift:27`: la comparación de los objetos JSON del escenario antes y después del cambio de idioma no fue igual. La otra prueba de idioma pasó. La causa raíz queda pendiente: este resultado por sí solo no demuestra que el selector visible altere físicamente el problema. Se conserva la comparación completa en `fallo_idioma.txt`; revisar la serialización del escenario y sus identificadores, además del cambio de idioma, antes de modificar código o pruebas.

El benchmark generó 120 registros en `benchmark/timings.csv`, con campos y escenarios de Euler, CN, Jacobi y GS en Swift/Metal. Son tiempos de esta ejecución, sin aislamiento de carga, y no mediciones de FPS ni garantía universal de aceleración.

## Aplicación y límites

La app construida está en esta carpeta de resultados, con firma ad hoc verificada mediante codesign. La apertura devolvió éxito y el proceso se observó activo. No se verificaron manualmente los apartados A–F del protocolo: ventana pequeña, cambio de idioma durante cálculo, formularios, interacción 2D/3D, isotermas, edición de bordes, dibujo y exportación desde la interfaz. Permanecen NO PROBADOS y no deben contarse como aprobados. Tampoco se probó instalación en otra Mac, Developer ID ni notarización.

La importación v1 mantiene la limitación conocida de máscara; para edición de recortes se entrega el escenario v2. No se cambió esta funcionalidad.

## Evidencias y próximos pasos

Consultar `etapas.tsv`, `suite_completa.log`, `pruebas/swift-test.log`, `pruebas/campaign.jsonl`, `construir_app.log`, `firma_app.log`, `equipo.txt`, `benchmark/timings.csv` y `fallo_idioma.txt`. Los hashes y las fuentes utilizadas se incluyen en la devolución.

1. Investigar y corregir la desigualdad de serialización en el test de idioma; repetir esa prueba y la regresión afectada.
2. Completar la aceptación manual A–F con capturas y exportaciones.
3. Probar la distribución en otra Mac antes de publicar.

El primer intento previo a esta corrida encontró restricciones de caché de Swift del entorno de ejecución; se conserva separado y no se atribuye a un fallo del producto. La corrida descrita aquí se realizó con acceso normal a las herramientas.

Carpeta de evidencia: `resultados/m1-20261106-221337-u2MrjB`.

## Repetición de idioma

Se repitieron las pruebas el 06/11: macOS declara AppleLanguages en-GB, es-AR. La prueba de español inicial y traducción a inglés británico vuelve a aprobar; la comparación de escenario vuelve a fallar. El diff del fallo original contiene únicamente el UUID de la máscara legacyMask: Scenario.encode llama migrated(), que crea una ScenePrimitive con UUID nuevo en cada serialización. Esto explica la desigualdad sin atribuirla a la traducción. AppLanguage inicia explícitamente en es, independientemente del idioma del sistema. No se modificó código. Evidencia adicional en resultados/idioma-retest-20261106.
