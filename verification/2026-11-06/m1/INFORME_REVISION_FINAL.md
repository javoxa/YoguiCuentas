# Informe final — YoguiCuentas Metal revisado

6 de noviembre de 2026. Candidata 0.12.0, revisión local posterior a la base indicada en ORIGEN.json.

## Corrección

La serialización de un escenario v1 invocaba migrated(), que creaba UUID aleatorios en cada exportación. Por eso fallaba la comparación antes/después de cambiar idioma, aun cuando los valores físicos se conservaban. La migración ahora asigna IDs deterministas por rol e índice: v1-domain, v1-material-N, v1-source-N y v1-uniform-source. Son únicos dentro de la escena migrada. Las escenas v2 existentes conservan sus IDs y las figuras nuevas siguen usando UUID. No se modificó el operador numérico ni las tolerancias.

Se conservó la prueba original de idioma y se añadió una regresión de serialización repetida, migración repetida y persistencia de IDs al reabrir JSON, sin alternar idioma.

## Verificación nueva

Apple M1, 8 GB, macOS 15.4.1, Xcode 16.4, Swift 6.1.2. Idiomas del sistema en-GB y es-AR. Español inicial explícito de la app, independiente de macOS.

**106 XCTest aprobados, cero fallos y sin omisiones registradas**, incluidos CPU Swift/GPU Metal y las tres pruebas de idioma/migración. Benchmark completado: 120 mediciones, sin aislamiento de carga, no FPS.

App release reconstruida desde cero, build 20261106222457, versión 0.12.0, firma ad hoc verificada por el script. La primera construcción en la nueva ruta falló por una caché PCH copiada de la carpeta original. Se retiró esa caché y el reintento limpio aprobó; ambos logs y códigos se conservan. RESULTADO_AUTOMATICO.txt registra el primer intento y debe leerse junto a este informe y las etapas añadidas.

## Entrega y pendientes de producción

Proyecto, escenarios, contexto, parche, protocolo y evidencias reunidos en para_mac_revisado. No se alteraron las fuentes originales de para_mc. El manifiesto de entrega identifica esta revisión; el manifiesto de entrada de la corrida conserva el estado probado.

La aceptación visual completa de esta construcción sigue pendiente: completar PRUEBAS_MANUALES.md de resultados. La prueba favorable que informó el usuario corresponde a la app previa y no especifica cada recorrido. También quedan primera apertura en otra Mac y preparación de firma Developer ID/notarización si se requiere distribución pública. No se hizo publicación, push ni etiquetado.

Evidencia: resultados/m1-20261106-222317-ZTWfQj, suite_completa.log, pruebas/swift-test.log, pruebas/campaign.jsonl, benchmark/timings.csv, construir_app-reintento.log y etapas.tsv.
