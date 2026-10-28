## Descargas

- **Linux Debian/Devuan (amd64):** descargá `yoguicuentas_@VERSION@_all.deb`; no hace falta extraerlo. Desde la carpeta de descarga, ejecutá `sudo apt install ./yoguicuentas_@VERSION@_all.deb`. Luego abrí YoguiCuentas desde el menú o con `yoguicuentas`. La primera instalación requiere acceso a APT y PyPI.
- **macOS Apple Silicon (arm64):** descargá `YoguiCuentas_Metal_macOS_arm64.zip`, hacé doble clic para extraerlo en Finder y arrastrá `YoguiCuentas Metal.app` a Aplicaciones. Requiere macOS 13 o posterior. La firma es local; la app no tiene Developer ID ni notarización y Gatekeeper puede requerir autorización en la primera apertura.
- **Informe técnico:** `YoguiCuentas_Informe_tecnico_Metal_0.11.0.pdf`, con método, resultados, límites y pasos de reproducción. El informe documenta la versión Metal 0.11.0; la edición OpenCL tiene numeración independiente.
- **Integridad:** `SHA256SUMS` contiene los hashes SHA-256 de los paquetes y del informe.

Si la Release no muestra los archivos todavía, consultá la ejecución **Build release packages** en la pestaña Actions y descargalos cuando termine correctamente.

El código y la documentación se distribuyen bajo Apache License 2.0. `LICENSE` y `NOTICE` se incluyen junto a los archivos de la Release; la imagen del icono puede requerir autorización independiente.

Linux ejecuta con CPU NumPy cuando no encuentra una GPU OpenCL. La app de macOS usa Metal y requiere macOS 13 o posterior.
