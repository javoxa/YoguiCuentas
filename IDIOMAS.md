# Idiomas de la interfaz

Actualización: 6 de noviembre de 2026.

Las ediciones Linux/OpenCL y macOS/Metal ofrecen **Idioma → Español / English**.
Cada inicio usa español. En Linux, el menú está inmediatamente después de **Ver**;
en macOS se añade a la barra de menús de la aplicación mediante `CommandMenu`.
El menú se denomina **Language** al elegir inglés.

El cambio actualiza los controles, formularios abiertos, ayudas y estados de la
aplicación. Conserva el escenario, la selección de métodos, los materiales y las
condiciones de borde. No reinicia la simulación. Los nombres elegidos por el
usuario y los identificadores técnicos de JSON/CSV se conservan; los diálogos
nativos del sistema mantienen el idioma configurado en el sistema operativo.

El catálogo compartido está en `yoguicuentas/ui/translations.py`. Para actualizar
su copia Swift después de editarlo:

```bash
python3 scripts/sincronizar_traducciones.py
python3 scripts/sincronizar_traducciones.py --check
```

## Comprobación realizada en Linux

- Cuatro pruebas de idioma: español inicial; menús, títulos y formularios abiertos;
  textos de estado; rutas intactas; selectores con valores internos estables;
  aplicación del formulario en inglés sin alterar el escenario original.
- Tres pruebas de configuración, tres del editor de escena y una de adaptación
  de ventanas, incluidas fuentes grandes.
- Prueba breve de la aplicación completa: solver CPU NumPy, dibujo OpenGL en
  RTX A2000; cambios a inglés y español conservando las instancias del solver,
  controlador y escenario. Sin errores gráficos ni de aplicación registrados.

Los resultados están en `verification/2026-11-06/localisation/`. Esta revisión de
presentación no vuelve a ejecutar ni sustituye las campañas numéricas de octubre.

## Resultado automático recibido de macOS

La revisión del 06/11 se integró con 106 XCTest aprobados, sin fallos ni omisiones
registradas, y app release construida en M1. Incluye tres pruebas de idioma y
migración: se corrigió la creación de IDs nuevos al serializar escenarios v1.
[Informe de revisión](INFORME_REVISION_METAL_20261106.md).

## Aceptación manual pendiente y repetición en macOS

Desde `metal/yoguicuentas_metal`, ejecutar en la Mac:

```bash
swift test --filter LanguageTests
swift test
YOGUI_SKIP_OPEN=1 bash crear_app.sh
```

Abrir la app recién construida y verificar:

1. Inicio en español y presencia de Idioma junto a los menús de visualización.
2. Cambiar a English durante una corrida: tiempo/iteraciones continúan y el
   procesador, escala, cámara y escenario se conservan.
3. Abrir parámetros y escena, seleccionar material, fuente y borde, cambiar
   idioma y comprobar que los valores y la selección se mantienen.
4. Aplicar una condición Robin, volver a español y exportar campo e historial.
   Comparar identificadores y valores de los archivos, no sus etiquetas visuales.
5. Revisar textos y accesibilidad con una ventana pequeña y letras grandes;
   comprobar que el menú de idioma muestra la elección correcta.

Traer el log de compilación, resultado de XCTest y observaciones/capturas de
estos cinco puntos. La nueva campaña acredita compilación y tests automáticos de esta revisión;
el checklist manual recibido sigue sin completar.
