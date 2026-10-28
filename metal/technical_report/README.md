# Informe técnico · YoguiCuentas Metal 0.11.0

Documento en castellano para revisión técnica y preparación de revisión por pares. Fecha de corte: 26 de octubre de 2026.

El código fuente y la documentación de este repositorio usan Apache License 2.0, salvo materiales de terceros o archivos con condiciones propias. El icono tiene condiciones de uso independientes.

- `informe_tecnico_yoguicuentas_metal.tex`: documento autocontenido; incluye figuras vectoriales TikZ/PGFPlots y bibliografía interna.
- `informe_tecnico_yoguicuentas_metal.pdf`: copia compilada para lectura y revisión.
- `data/`: datos JSON/CSV de los ensayos, registro de las 77 pruebas Swift sin fallos ni omisiones, escenarios y manifiesto SHA-256 de fuentes y pruebas.
- `source_snapshot/`: siete archivos de cálculo originales usados por el arnés reproducible. No se modificó el solver de la aplicación para producir el informe.
- `scripts/measure.swift`: ensayos con el código real, sin traducción del solver a otro lenguaje.
- `scripts/report_template.tex.in`: plantilla editable para regenerar el documento con los datos archivados. Editar este archivo si se quiere preservar cambios al regenerar; el `.tex` final también es editable de forma independiente.
- `build/`: compilación y control visual, no es necesario distribuir esta carpeta para leer o compilar el `.tex`.

## Contenido

Modelo y unidades, malla nodal, medias de interfaz, fuentes y contornos, Euler explícito, Crank–Nicolson, arranque suavizado, Jacobi estacionario e interno, criterios de estabilidad/positividad/convergencia, precisión Float, arquitectura CPU/Metal, memoria y costos, postproceso, ventajas, límites y comprobaciones pendientes. Siete figuras distinguen esquemas conceptuales, análisis modal y resultados medidos.

El informe separa las pruebas implementadas de la validación experimental pendiente. El contraejemplo de positividad construye un `Scenario` v1 directamente; no se atribuye el mismo paso a la ruta normal de importación, que migra a v2.

La referencia de Luis Cardon conserva el título, la impresión de noviembre de 2022 y el identificador interno proporcionados por el solicitante. Se verificó el perfil GitHub, pero no una copia pública de esa edición. No se inventaron editorial, ISBN ni números de página. Antes de envío editorial deben cotejarse esa ficha y la autoría/afiliaciones del informe.

## Reproducir

Se requiere macOS, Swift con Metal y una instalación LaTeX con `babel` (español), `lmodern`, `tikz` y `pgfplots` 1.17 o posterior. Python solo usa la biblioteca estándar.

Desde la raíz del proyecto:

```sh
bash technical_report/scripts/run_measurements.sh
python3 technical_report/scripts/render_report.py
bash technical_report/scripts/build_pdf.sh
```

El primer comando vuelve a medir con los fuentes de `source_snapshot/`; requiere acceso a Metal para obtener resultados GPU. Si no hay GPU, el JSON declara esa condición. El documento archivado corresponde a Apple M1, no al archivo auxiliar `measurements_cpu.json` obtenido inicialmente con la GPU oculta por el sandbox.

Para revisar visualmente el PDF en macOS:

```sh
swift technical_report/scripts/render_pdf.swift /ruta/absoluta/a/technical_report
```

Para repetir las pruebas completas se necesita además el proyecto de aplicación adyacente:

```sh
swift test --package-path yoguicuentas_metal
```

Los datos reportados son verificación de casos definidos. No se afirma que CN sea siempre más rápido, que CPU y GPU sean idénticas bit a bit ni que la frontera curva escalonada converja al intercambio del círculo ideal.
