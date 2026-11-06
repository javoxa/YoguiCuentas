# Beta y preparación de producción futura — 06/11/2026

Estado: beta preparada para instalación mediante `git clone`. La edición estable
tendrá otro nombre, aún por definir después de validar la entrega.
Verificación numérica aprobada en el alcance ensayado; la aceptación manual de
equipos de destino sigue pendiente de registro. No se publicó ni se modificaron etiquetas.
Versiones de la candidata: Linux **0.2.5** y Metal **0.12.0**. Versiones base
anteriores: Linux 0.2.4 y Metal 0.11.0. No reutilizar una etiqueta publicada.
La devolución M1 nueva acredita 106 XCTest aprobados y la app release
0.12.0 reconstruida. Se integró una corrección de IDs de migración v1 y su test.
[Informe de revisión](INFORME_REVISION_METAL_20261106.md). La aceptación visual
completa permanece pendiente; el checklist recibido no está completado.

## Contenido listo

- [Informe final de validación](INFORME_VALIDACION_CPU_GPU_20261029.md),
  [estado actualizado](ESTADO_PROYECTO.md) y evidencia con hashes en
  `verification/2026-10-29/m1`.
- Fuentes finales Metal integradas, cotejadas con la campaña M1 del 06/11.
- Construcción Debian/Devuan y macOS automatizada. La publicación depende de la
  campaña CPU y de los tests Swift/Metal; una falla detiene el empaquetado/publicación.
  Un test Metal omitido en CI no reemplaza la evidencia GPU del M1 real.
- Notas de entrega, licencias, informe y checksums incluidos como assets.
- Devolución original y metadatos Finder excluidos de Git; evidencia pública
  seleccionada sin binarios duplicados. El paquete de traspaso original es histórico.

## Aceptación antes del anuncio estable

Registrar fecha, sistema, equipo, hash del instalador, resultado y log/captura.
Marcar cada punto aprobado o fallido, sin sustituirlo por un test numérico.

- [ ] Debian y Devuan: instalar con `sudo apt install ./yoguicuentas_VERSION_all.deb`
  desde una cuenta normal; comprobar menú, recursos y escenarios.
- [ ] Equipo sin GPU dedicada: arranque automático CPU; repetir con
  `yoguicuentas --processor cpu`; ejecutar Euler, CN, Jacobi y Gauss–Seidel.
- [ ] Reinstalar/actualizar y desinstalar; conservar los escenarios/resultados del usuario.
- [ ] Otra Mac Apple Silicon: extraer ZIP, mover la app a Aplicaciones, primera
  apertura y comprobar escenarios. Documentar la intervención de Gatekeeper.
  La firma recibida es ad hoc; no hay Developer ID ni notarización.
- [ ] En ambas interfaces: dibujar y seleccionar rectas/regiones, incluir/excluir,
  aplicar fuente/material/contorno, deshacer, guardar/reabrir JSON v2.
- [ ] Escala automática/manual con mouse, isotermas y rótulos, vistas 2D/3D,
  barra lateral accesible y PNG sin superposiciones indebidas.
- [ ] Exportar campo, escenario, metadatos e historial; reiniciar y cambiar CPU/GPU.
  Verificar que no reaparezcan campos ni controles de la corrida anterior.
- [ ] Repetir los dos tests Linux de clic nativo cuando la sesión esté disponible.

## Construcción y publicación

Desde la raíz, Linux:

```bash
bash construir_deb.sh
sha256sum dist/yoguicuentas_*_all.deb
```

En macOS, sobre las mismas fuentes finales:

```bash
bash metal/yoguicuentas_metal/verificar_numerica.sh verification/aceptacion full
YOGUI_SKIP_OPEN=1 bash metal/yoguicuentas_metal/crear_app.sh
```

Para publicar, ejecutar CI sobre la revisión final y cerrar la lista anterior.
La etiqueta nueva `v0.2.5` debe coincidir con la versión Linux: el workflow lo comprueba.
La acción de publicar crea assets y `SHA256SUMS` con nombres relativos que permiten
`sha256sum -c SHA256SUMS` en la carpeta descargada (macOS: `shasum -a 256 -c SHA256SUMS`).

El entorno Linux no recompila Metal. La candidata macOS debe construirse en Apple
Silicon/CI y probarse como ZIP distribuido; no se presenta un binario Linux como
sustituto de esa verificación. Los tiempos medidos no prometen aceleración universal.

## Datos que faltan para cerrar la aceptación

Devolver la lista marcada, logs de instalación/desinstalación, hash de cada paquete,
capturas de las interfaces y cualquier escenario que reproduzca un fallo.
El informe numérico está terminado; el acta de aceptación de distribución queda
abierta hasta contar con esas pruebas reales.
