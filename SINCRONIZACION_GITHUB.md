# Sincronización preparada — 6 de noviembre de 2026

Repositorio: https://github.com/javoxa/YoguiCuentas

La candidata conserva OpenCL 0.2.5 y Metal 0.12.0. Esta actualización incorpora
el selector de idioma en ambas ediciones, su catálogo compartido, las pruebas,
el paper en inglés técnico británico y los PDF español/inglés en el empaquetado
y en los adjuntos de la Release.

## Preparar y llevar a la Mac

Desde la raíz de YoguiCuentas:

```bash
python3 scripts/preparar_sincronizacion.py
```

Se generan `dist/YoguiCuentas_github_20261106.zip` y su `.sha256`. El ZIP contiene
una carpeta `YoguiCuentas` con los archivos publicables actuales y un manifiesto
SHA-256 de cada archivo. Incluye fuentes Metal, escenarios, evidencia y papers.
No incorpora el entorno Python, los resultados temporales ni la carpeta `.git`.
En la Mac, extraerlo en una carpeta nueva y seguir `IDIOMAS.md`. El ZIP es una
instantánea de fuentes para transferencia; la app macOS debe compilarse allí.

## Subir la actualización preparada

Los cambios acumulados se reúnen en un commit local sobre `main`. Incluyen la
interfaz bilingüe, los criterios y verificaciones numéricas, los papers y la
corrección de condiciones de borde de `prueba_01`.

Desde `/home/javo/Programas/opencl/YoguiCuentas`, comprobar y subir:

```bash
git status --short
git log -1 --oneline
git push origin main
```

La autenticación utiliza la configuración de Git ya disponible en la máquina.
El commit está preparado localmente; la subida remota se realiza con el comando
anterior. No es necesario guardar usuario ni token dentro del proyecto.

Para futuras modificaciones, antes de crear un nuevo commit:

```bash
python3 scripts/sincronizar_traducciones.py --check
python3 technical_report/verificar_traduccion.py
git diff --check
git add .
git diff --cached --stat
git commit -m "Describir los cambios incorporados"
```

## Publicar los instaladores después de aceptar la candidata

El workflow de `main` comprobará la campaña CPU, el catálogo y las pruebas de
idioma. La publicación por etiqueta ejecuta además las pruebas Swift/Metal y
construye el `.deb` y la app. Para anunciar una candidata aceptada, después de
completar las comprobaciones de `PREPARACION_PRODUCCION.md` e `IDIOMAS.md`:

```bash
git tag -a v0.2.5 -m "YoguiCuentas 0.2.5; Metal 0.12.0"
git push origin v0.2.5
```

Usar esa etiqueta solamente si aún no existe para otro contenido. El workflow
exige que coincida con la versión de `pyproject.toml` y adjunta los dos papers,
el informe previo Metal, licencias e integridad de los paquetes.

La comprobación local del `.deb` cubre su construcción y contenido. La instalación
y desinstalación en Debian/Devuan y la nueva compilación/aceptación de macOS
continúan como pruebas de destino. El paquete macOS anterior no incluye el menú
nuevo: debe utilizarse una app reconstruida desde estas fuentes.
