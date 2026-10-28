# Instalación de YoguiCuentas en Mac con Apple M1

Actualizado: **28/10/2026**. Versión documentada: **YoguiCuentas Metal 0.11.0**.

Esta guía corresponde a la aplicación nativa Swift/Metal de la carpeta `yoguicuentas_metal`. En un M1 ejecuta el cálculo en CPU Swift o en GPU Metal. La versión Python es otro programa y no es necesaria para instalar esta app.

## 1. Qué necesitás

| Uso | Requisitos |
|---|---|
| Ejecutar la app ya compilada | Mac Apple M1, macOS **13 Ventura o posterior**, paquete completo `YoguiCuentas Metal.app` |
| Compilar desde fuentes | Lo anterior, código de `yoguicuentas_metal` y herramientas Apple con **Swift 5.9 o posterior**, SDK macOS y SwiftPM |
| Calcular con GPU | Backend **GPU · Metal** disponible en el selector de la app |

El ejecutable disponible es **arm64**: funciona de forma nativa en M1 y no requiere Rosetta, Python, Homebrew, CUDA ni OpenCL. macOS 13 es el mínimo declarado y comprobado en el binario; no significa que se haya probado cada versión del sistema. El entorno de desarrollo inspeccionado usa macOS 15.4.1, Xcode 16.4 y Swift 6.1.2. La instalación en un segundo M1 limpio todavía no fue verificada.

## 2. Instalar la app ya compilada

Es la ruta más corta si ya tenés el paquete completo.

1. Abrí [Releases de YoguiCuentas](https://github.com/javoxa/YoguiCuentas/releases/latest) y descargá `YoguiCuentas_Metal_macOS_arm64.zip` en **Assets**.
2. En Finder, abrí **Descargas** y hacé doble clic en el ZIP. Se extraerá `YoguiCuentas Metal.app`.
3. Arrastrá la app completa a **Aplicaciones**. También podés instalarla para tu usuario en `~/Applications`.
4. Abrila desde **Aplicaciones** o Spotlight buscando “YoguiCuentas Metal”. La app requiere una Mac Apple Silicon (M1 o posterior) y macOS 13 o posterior.
5. Si Gatekeeper bloquea la primera apertura, seguí las instrucciones de la sección siguiente.

Si estás compilando desde el código fuente, la app local queda en `metal/yoguicuentas_metal/dist/YoguiCuentas Metal.app`, dentro de la copia del repositorio. Copiá **toda la app**, no solo `Contents/MacOS/yoguicuentas_metal`: el paquete incluye los escenarios que necesita para arrancar. Guardá los JSON de usuario en Documentos, fuera de la app, antes de sustituirla en una actualización.

Si la página [Releases](https://github.com/javoxa/YoguiCuentas/releases/latest) aún no ofrece el ZIP, revisá [Actions](https://github.com/javoxa/YoguiCuentas/actions) y esperá que termine correctamente **Build release packages** para `v0.2.4`.

### Si macOS bloquea la primera apertura

El paquete actual tiene firma **ad hoc local**, sin Developer ID ni notarización. La comprobación de firma local no equivale a una aprobación de Gatekeeper ni a notarización de Apple.

Si recibiste la app de una fuente que reconocés y querés autorizar esa copia, intentá abrirla primero y después revisá **Ajustes del Sistema → Privacidad y seguridad → Abrir igualmente** para esa aplicación, si aparece la opción. Seguí la confirmación que muestre macOS. Es el procedimiento de [Apple para abrir apps de forma segura](https://support.apple.com/en-us/102445).

Si el mensaje indica que la app está dañada, la firma no verifica o no conocés su procedencia, conseguí de nuevo el paquete completo o compilalo desde las fuentes. Esta guía no requiere desactivar Gatekeeper ni borrar atributos de cuarentena mediante comandos.

## 3. Compilar e instalar desde el código fuente

Esta ruta no requiere una suscripción de pago al Apple Developer Program para la firma local que usa el proyecto. La distribución notarizada es un paso distinto y aún pendiente.

### 3.1 Preparar las herramientas Apple

Podés usar Xcode o las Command Line Tools compatibles con tu versión de macOS. La ruta de compilación ya probada en este proyecto utiliza Xcode 16.4; el manifiesto exige Swift 5.9 o posterior. Instalá una versión de herramientas compatible con el macOS del equipo, no necesariamente la más reciente.

Para solicitar las herramientas de línea de comandos desde Terminal:

```bash
xcode-select --install
```

Completá el instalador de Apple. Si ya están instaladas, el comando puede indicarlo. Apple describe esta opción en [Instalar las herramientas de línea de comandos](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/).

Si utilizás Xcode completo, abrilo una vez y terminá su preparación inicial. Comprobá en Terminal:

```bash
uname -m
sw_vers -productVersion
xcode-select -p
xcrun --find swift
swift --version
```

Para una sesión de desarrollo nativa M1, `uname -m` debería mostrar `arm64`. Si muestra `x86_64`, revisá si Terminal se está ejecutando con Rosetta antes de compilar. La arquitectura del binario generado se comprueba más adelante con `file`.

Si hay varios Xcode instalados, elegí el adecuado en **Xcode → Settings → Locations → Command Line Tools**. Para un Xcode instalado exactamente en `/Applications/Xcode.app`, también se puede seleccionar desde Terminal:

```bash
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
```

Este comando modifica qué herramientas usa el sistema y pide la contraseña de administrador; usalo solo si necesitás corregir esa selección. No es necesario para ejecutar la app precompilada.

### 3.2 Preparar la carpeta del proyecto

Copiá la carpeta completa `yoguicuentas_metal` a una ubicación de trabajo de tu usuario, por ejemplo `~/Documents/yogui/yoguicuentas_metal`. Debe contener al menos `Package.swift`, `crear_app.sh` y `Sources/YoguiCuentasMetal/Resources/Scenarios`.

No dependas de la carpeta `.build` copiada desde otro equipo: SwiftPM genera sus propios artefactos locales. Abrí Terminal y entrá a la carpeta que contiene Package.swift. Para la ubicación usada como ejemplo:

```bash
cd "$HOME/Documents/yogui/yoguicuentas_metal"
```

Si guardaste el código en otro lugar, reemplazá la ruta del comando. No uses `sudo` para compilar en tu carpeta de usuario.

### 3.3 Generar la aplicación

Desde esa carpeta:

```bash
bash crear_app.sh
```

El script realiza estas operaciones:

1. Compila el ejecutable en modo Release mediante SwiftPM.
2. Copia ejecutable y escenarios a `dist/YoguiCuentas Metal.app`.
3. Escribe versión y build UTC en Info.plist.
4. Firma ad hoc y verifica la integridad del paquete con codesign.
5. Abre una **instancia nueva** de la aplicación.

El build obtenido será distinto de `20261025230605` porque se genera al ejecutar el script. No hay dependencias de paquetes Swift de terceros declaradas en Package.swift. Después de instalar las herramientas Apple no se necesita descargar librerías Python ni controladores de GPU externos para esta ruta.

El script **no cierra instancias anteriores**. Confirmá la versión/build del proceso que estás usando antes de evaluar un cambio. Finalmente copiá el paquete generado a Aplicaciones como en la sección 2.

### 3.4 Comprobar el resultado

Desde la carpeta del proyecto:

```bash
file "dist/YoguiCuentas Metal.app/Contents/MacOS/yoguicuentas_metal"
codesign --verify --deep --strict "dist/YoguiCuentas Metal.app"
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "dist/YoguiCuentas Metal.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "dist/YoguiCuentas Metal.app/Contents/Info.plist"
```

`file` debe identificar un ejecutable **arm64**. `codesign --verify` normalmente no imprime nada cuando termina correctamente. PlistBuddy muestra versión y build. La verificación codesign acredita integridad de la firma, no notarización.

Para volver a abrir el paquete de desarrollo en otro momento:

```bash
open "dist/YoguiCuentas Metal.app"
```

## 4. Primera comprobación funcional

1. Abrí la app y verificá versión/build.
2. En **Escenario**, elegí un caso incluido, por ejemplo **trapecio fuente**.
3. En **Cálculo → Procesador**, seleccioná CPU Swift para una primera corrida. Después podés repetir con **GPU · Metal** si está disponible.
4. Pulsá **Iniciar**, comprobá que avancen tiempo y pasos y luego **Pausar**. Usá **Reiniciar** para volver al estado inicial.
5. Expandí **Superposiciones** si querés ver el informe de fuente, puntos de nodos con aporte, vectores o isotermas.

Para editar: **Editar escena… → dibujar/seleccionar una región → asignar fuente o material → configurar valores → Aplicar al problema**. Aplicar reconstruye el problema y lo deja en **t=0, detenido**; luego hay que pulsar **Iniciar**. Una figura naranja no basta para acreditar fuente: comprobá el informe de nodos y potencia.

La intensidad Q de una fuente interior está en **W/m³** y la de una línea en **W/m**. El informe de potencia está en W, con profundidad de referencia de 1 m. Con intensidades moderadas, la variación térmica puede ser lenta; ajustar la escala de color no modifica la solución física.

## 5. Pruebas para desarrollo

Opcionalmente, desde la carpeta con Package.swift:

```bash
swift test
```

La última suite completa registrada aprobó **57 pruebas en 0.9.5**. Para 0.9.6 se registraron compilación Debug/Release y revisión visual de los controles modificados. Ejecutar `swift test` en un equipo nuevo produce evidencia nueva: registrá qué pruebas pasan, se omiten o fallan, especialmente las que dependen de Metal.

No hace falta ejecutar tests ni instalar Xcode para usar la app ya compilada. Esta guía se redactó comprobando fuentes, metadatos y firma del paquete existente; no representa una instalación limpia realizada en otro M1.

## 6. Resolución de problemas

| Síntoma | Comprobación y acción |
|---|---|
| `swift` o herramientas no disponibles | Terminá la instalación de Command Line Tools/Xcode y revisá `xcode-select -p` y `xcrun --find swift`. |
| Swift informa manifiesto no compatible | El proyecto exige Swift 5.9 o posterior; revisá `swift --version` y seleccioná un toolchain compatible. |
| La compilación no puede escribir cachés | Compilá desde una Terminal normal en una carpeta de tu usuario; en un entorno automatizado puede hacer falta autorización de escritura. No es por sí solo un fallo del solver. |
| No aparecen escenarios o no abre correctamente | Confirmá que copiaste toda la app, incluidos sus recursos, y verificá codesign; volvé a generar/copiar el paquete si falta algo. |
| No aparece GPU · Metal | Usá CPU Swift y anotá el error y la versión de macOS. Metal se ofrece solo si se crean correctamente dispositivo y pipeline. |
| Metal falla durante una corrida | La app detiene la ejecución y selecciona CPU; conservá el error, reiniciá el caso y probá CPU. No hay reanudación automática. |
| Se ven controles antiguos | Revisá versión/build en la ventana y cerrá las instancias viejas antes de abrir la copia nueva. |
| La fuente no cambia la temperatura al aplicar | Aplicar deja t=0. Verificá nodos con aporte y Q, pulsá Iniciar y comprobá el tiempo físico transcurrido. |
| El JSON nuevo no abre en Python | La app nativa guarda v2; Python todavía rechaza esa versión. Conservá los originales v1 si necesitás la ruta Python. |

## 7. Alternativa Python y documentación

Si necesitás específicamente la aplicación Python/OpenCL, esa es la edición para Linux. Su código e instrucciones están en la raíz del repositorio: [README](../../README.md) y [PORTABILIDAD](../../PORTABILIDAD.md).

- [Estado del proyecto](../../ESTADO_PROYECTO.md).
- [Informe técnico Metal](../technical_report/informe_tecnico_yoguicuentas_metal.pdf).
- [README nativo](README.md).
- [Formato de escenarios v2](SCENE_FORMAT.md).
