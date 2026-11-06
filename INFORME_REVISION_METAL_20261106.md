# Revisión e integración de la devolución Metal — 6 de noviembre de 2026

Edición candidata 0.12.0. Base de la entrega: commit
`317065cb65a1e8541bd29e6494465b81db45c40c`. La revisión recibida se identifica como
`mac-20261106-stable-v1-ids`. No se ejecutó Metal en Linux.

## Cambios integrados

Se integraron los dos archivos Swift diferentes de la base:

- `Scene.swift`: IDs deterministas al migrar escenas v1: `v1-domain`,
  `v1-material-N`, `v1-source-N` y `v1-uniform-source`. Antes, serializar varias
  veces el mismo escenario generaba UUID nuevos. Los IDs de escenas v2 existentes
  se conservan y las figuras nuevas siguen utilizando UUID.
- `LanguageTests.swift`: conserva las pruebas de idioma y añade serialización y
  migración repetidas, con persistencia de identificadores tras guardar/reabrir.

La modificación resuelve la inestabilidad de identidad en exportaciones. No cambia
el operador numérico ni sus tolerancias. Los bytes de las fuentes integradas se
cotejaron con las fuentes identificadas en la campaña recibida.

## Evidencia comprobada

Equipo registrado: Apple M1, GPU de siete núcleos, 8 GiB, macOS 15.4.1,
Xcode 16.4 y Swift 6.1.2.

| Comprobación | Resultado |
|---|---|
| Manifiesto de entrega | 109/109 archivos coincidentes |
| Manifiesto de resultados | 742/742 archivos coincidentes |
| Fuentes de la suite | 35/35 entradas coincidentes |
| Fuentes del benchmark | 20/20 entradas coincidentes |
| Suite XCTest recibida | 106 aprobadas, cero fallos; sin casos omitidos registrados |
| Pruebas de idioma/migración | Tres aprobadas dentro de la suite |
| Campaña complementaria | 158 registros: 144 criterios, seis círculos, cuatro modos y cuatro balances |
| Exportaciones | 144 conjuntos cotejados: campo, escenario, metadatos e historial |
| Benchmark | 120 registros: 60 Swift y 60 Metal |
| Mayor diferencia Swift/Metal registrada | 1.5497207641601562e-6 K |
| App release | 0.12.0, build 20261106222457 |

El cotejo de exportaciones verifica dimensiones, índices y coordenadas del campo,
valores activos finitos, escenario coincidente con metadatos, procesador solicitado
igual al efectivo, longitud de historial y último paso. Las iteraciones
estacionarias no declaran tiempo físico. Estas comprobaciones se limitan a los
casos recibidos; no constituyen aceptación de todos los recorridos de interfaz.

El primer empaquetado falló porque una caché PCH conservaba una ruta anterior.
El reintento limpio terminó con código cero; se preservaron ambos logs y las
etapas. `RESULTADO_AUTOMATICO.txt` refleja el primer intento: no debe leerse
sin `etapas.tsv` y `construir_app-reintento.log`.

La firma ad hoc se acredita mediante el script y los registros macOS recibidos.
En Linux se comprobó el hash del binario, no se volvió a ejecutar `codesign`.
Hash SHA-256 del ejecutable recibido:

`bf3c94e68c4bf71bfcbed20ad07201fe016d963cd49144f93e388002cb7d9040`

## Alcance y pendientes

La compilación y las pruebas automáticas de la interfaz bilingüe quedan
acreditadas por esta campaña M1. La plantilla de aceptación manual recibida está
sin completar y no contiene capturas/exportaciones manuales: los recorridos de
uso, la primera apertura en otra Mac y la aceptación de distribución siguen
pendientes. No se infiere su aprobación a partir de XCTest.

La recuperación de rectángulos v1 editables incorporada en Linux no forma parte
de este parche Swift. En Metal se mantiene la máscara v1 de edición limitada;
para probar bordes independientes está el escenario convertido v2 de la entrega.

Los tiempos son mediciones del solver con las condiciones del benchmark,
no FPS, eficiencia energética ni una comparación controlada con A2000. El sesgo
geométrico Robin y las limitaciones de grilla estructurada siguen vigentes.
Los papers existentes conservan sus campañas originales de octubre; esta revisión
se documenta como evidencia nueva, sin reemplazar retrospectivamente sus datos.

## Archivos conservados

- Evidencia pública seleccionada: `verification/2026-11-06/m1/` (632 archivos,
  más su manifiesto público).
- Auditoría, informes y parche recibidos: `verification/2026-11-06/m1-review/`.
- Devolución original íntegra: `para_mac_revisado/`, excluida de Git. Incluye
  la app, binarios y archivos duplicados que no se incorporan a la evidencia pública.

Los manifiestos originales se conservan sin alterar y hacen referencia a la
entrega completa; para comprobar la selección pública usar
`m1/MANIFIESTO_PUBLICO.sha256`. No se ejecutaron binarios macOS en Linux ni se
creó una publicación remota durante esta integración.
