# Revisión documental — 26/10/2026

Actualizados ESTADO_PROYECTO.md e ESTADO_ACTUAL_INFORME_TECNICO.md en YoguiCuentas. Sus contenidos previos se conservaron íntegros en documentacion/historial/2026-10-26_antes_consolidacion_*.md. Creada INSTALACION_APPLE_M1.md en yoguicuentas_metal y enlazada desde ambos README.

Comprobaciones de solo lectura: Info.plist 0.9.6 / 20261025230605; file identifica arm64; vtool identifica minos 13.0 / SDK 15.5; codesign --verify --deep --strict sin error y codesign -dv confirma Signature=adhoc, TeamIdentifier no definido. Estación inspeccionada: macOS 15.4.1, Xcode 16.4, Swift 6.1.2.

Validados enlaces locales y cierre de bloques de código en los cinco documentos editados/creados. Corregidas instrucciones antiguas del README sobre Rol al dibujar. Se distinguen las 57 pruebas de 0.9.5 de la compilación y revisión visual 0.9.6; no se ejecutaron compilaciones, suites, simulaciones ni instalación nueva en esta tarea.

Referencias oficiales consultadas para instalación de herramientas y primera apertura:
- https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/
- https://support.apple.com/en-us/102445
