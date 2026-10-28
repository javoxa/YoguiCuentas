# Estado de portabilidad

## Equivalencias

| YoguiCuentas Python | YoguiCuentas Metal |
|---|---|
| `Scenario` JSON v1 | `Scenario` Codable |
| `CpuScheduler` / OpenCL | solver Swift CPU / Metal compute |
| Tkinter + OpenGL | SwiftUI + Canvas; Metal compute |
| cinco modos de `HeatmapRenderer` | cuatro fondos con vectores e isotermas independientes |

El kernel GPU usa buffers de coeficientes preparados una vez por escenario y dos campos térmicos alternados, como el paso explícito del proyecto original. El backend CPU aplica el mismo operador discreto para servir de referencia.

## Diferencias del primer port

- Se incluyen los presets JSON v1 y se pueden abrir/guardar archivos JSON. El editor nativo cubre grilla, geometría, condición inicial, material de fondo, bordes externos e internos, regiones, fuentes localizadas, paso manual/automático y convergencia.
- Fuentes, regiones y trazos internos se pueden revisar y editar con controles nativos. En el editor gráfico se pueden dibujar, seleccionar, mover, copiar, pegar, duplicar y eliminar objetos con mouse/trackpad y atajos ⌘C, ⌘V, ⌘D y Supr. La validación del editor informa errores de geometría y parámetros antes de aplicar.
- La superficie 3D nativa triangula los nodos activos, con muestreo limitado a aproximadamente 192 puntos por eje. Los bordes recortados pueden verse más escalonados que en un mallador dedicado.
- La geometría admite dominio triangular, trazos triangulares en cuatro orientaciones y fuentes localizadas triangulares. Las regiones de material todavía son rectangulares.
- La geometría, interfaces de materiales y fuentes se rasterizan sobre la grilla. El área de fuentes localizadas se integra por subceldas (8 × 8); la implementación Python puede usar una rasterización diferente. Hay que comparar resultados numéricos por escenario antes de afirmar equivalencia exacta.
- Los mapas y flechas usan `Canvas` de SwiftUI. La superficie 3D se dibuja con una malla SceneKit, normales, iluminación y controles nativos sobre el renderer de macOS acelerado por Metal.
- Las flechas de flujo y las isotermas son capas independientes en todos los fondos, incluida la superficie 3D. Las isotermas se extraen por interpolación triangular de la temperatura, independientemente de la variable del mapa de colores; sus valores en °C se pueden ocultar sin ocultar las líneas. Las flechas muestran el sentido del flujo con longitud normalizada. Las capas se incluyen en el PNG exportado.
- El estado estacionario usa el residuo del operador discreto y exige confirmaciones consecutivas. El campo actual se puede exportar como CSV.
- La velocidad de reproducción ofrece presets o un factor personalizado positivo; se informa la velocidad simulada efectiva. La vista permite alternar una ficha con GPU/backend, tiempo, paso, dt, rango de temperatura y resolución, y exportar una imagen PNG.
- El esquema JSON conserva la versión 1. La implementación Swift prepara un operador discreto para ambos backends; el stencil se revisó para dividir cada cara por capacidad y distancia antes de formar la diagonal.

## Requisitos

- macOS 13 o posterior.
- Xcode 15+ para abrir y ejecutar el paquete desde Xcode; alternativamente, `bash crear_app.sh` genera un `.app` local firmado ad hoc. La distribución pública requiere firma Developer ID y notarización.
- La compilación CPU puede realizarse con SwiftPM; GPU Metal requiere un dispositivo compatible en tiempo de ejecución.
