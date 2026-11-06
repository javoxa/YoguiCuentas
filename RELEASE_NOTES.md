La distribución actual de esta beta se realiza mediante `git clone` según
el README. Los nombres de archivos de Releases que siguen corresponden al
workflow disponible para publicar instaladores más adelante.

## Actualización de la beta desde fuentes

Gauss–Seidel rojo–negro CPU/GPU, nueve criterios de parada con muestreo
reproducible, auditoría física independiente e historial exportable. Correcciones
Metal de persistencia, tolerancias y metadatos. Verificación: Linux 155 tests
aprobados y dos omisiones de clic nativo; M1 103 XCTest aprobados sin omisiones;
217 comprobaciones numéricas Linux. El informe integrado se adjunta a la entrega.

Se resuelve sobre grilla cartesiana estructurada. Robin sobre círculos escalonados
conserva un sesgo de perímetro que no desaparece aumentando nodos. Las métricas
ΔT, traza y media pueden indicar `criterion_met` sin certificar equilibrio físico.
La aceptación visual y la instalación en equipos de destino deben
cerrarse antes del anuncio estable, según `PREPARACION_PRODUCCION.md`.

La entrega añade **Idioma → Español / English** en ambas ediciones, con
español inicial. Incluye el artículo completo en español e inglés británico.
Metal fue recompilado en M1 con 106 XCTest aprobados sin fallos ni omisiones.
Se corrigió la persistencia de IDs en migraciones v1. Sigue pendiente la
aceptación visual completa descrita en `IDIOMAS.md`.

Se corrigió la selección de condiciones de borde cargadas y se recuperan los
recortes rectangulares v1 como figuras editables cuando conservan exactamente la
máscara original. `prueba_01` permite asignar condiciones por lado a sus recortes.

## Descargas

- **Linux Debian/Devuan (amd64):** descargá `yoguicuentas_@VERSION@_all.deb`; no hace falta extraerlo. Desde la carpeta de descarga, ejecutá `sudo apt install ./yoguicuentas_@VERSION@_all.deb`. Luego abrí YoguiCuentas desde el menú o con `yoguicuentas`. La primera instalación requiere acceso a APT y PyPI.
- **macOS Apple Silicon (arm64):** descargá `YoguiCuentas_Metal_macOS_arm64.zip`, hacé doble clic para extraerlo en Finder y arrastrá `YoguiCuentas Metal.app` a Aplicaciones. Requiere macOS 13 o posterior. La firma es local; la app no tiene Developer ID ni notarización y Gatekeeper puede requerir autorización en la primera apertura.
- **Artículo para revisión:** `YoguiCuentas_Paper_ES.pdf` y `YoguiCuentas_Paper_EN.pdf`, con métodos, resultados, límites y evidencia reproducible.
- **Informe técnico anterior:** `YoguiCuentas_Informe_tecnico_Metal_0.11.0.pdf`, con método, resultados, límites y pasos de reproducción. El informe documenta la versión Metal 0.11.0; la edición OpenCL tiene numeración independiente.
- **Integridad:** `SHA256SUMS` contiene los hashes SHA-256 de los paquetes y del informe.

Si la Release no muestra los archivos todavía, consultá la ejecución **Build release packages** en la pestaña Actions y descargalos cuando termine correctamente.

El código y la documentación se distribuyen bajo Apache License 2.0. `LICENSE` y `NOTICE` se incluyen junto a los archivos de la Release; la imagen del icono puede requerir autorización independiente.

Linux ejecuta con CPU NumPy cuando no encuentra una GPU OpenCL. La app de macOS usa Metal y requiere macOS 13 o posterior.
