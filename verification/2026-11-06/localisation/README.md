# Verificación de idioma — 06/11/2026

Once pruebas de idioma y regresión de interfaz aprobadas, sin fallos ni omisiones.
Cuatro de idioma, tres de configuración, tres de escena y una de adaptación de
ventana. Ejecución gráfica habilitada con `YOGUI_TEST_GL=1`.

`window.json` registra los cambios de idioma sin sustituir solver, controlador ni
escenario y sin modificar el contador de pasos durante la operación.
`cpu-opengl-smoke.json` conserva la prueba de la aplicación con CPU NumPy y
renderizado OpenGL en RTX A2000, con `errors: []` y comprobaciones de controles,
captura y reinicio. No es un benchmark interactivo.

`LanguageTests.swift` añade dos tests para macOS; no se ejecutaron en Linux.
La aceptación visual del menú, formularios y corrida en M1 está en `IDIOMAS.md`.
