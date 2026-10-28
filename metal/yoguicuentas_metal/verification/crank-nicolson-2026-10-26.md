# Crank–Nicolson · Metal 0.11.0

Se agregó evolución temporal CN en CPU/Metal, conservando Euler explícito por defecto y Jacobi estacionario directo como método separado. La configuración v2 usa canvas.time.temporalMethod y canvas.time.cn; v1 acepta temporal_method y cn. Los campos ausentes mantienen el comportamiento anterior.

Para T′=f−AT se resuelve (I+dt A/2)δ=dt(f−AT_old) con Jacobi ponderado, y se publica T_old+δ. El incremento evita cancelación con las temperaturas absolutas. La formulación admite componentes Neumann/adiabáticas sin referencia estacionaria. Las fuentes y contornos siguen siendo constantes en el tiempo.

Metal usa buffers residentes y una reducción paralela del residuo por grupos de 256 nodos. Solo los máximos por grupo se leen en CPU. El código CN Metal desactiva fast math para conservar comprobaciones de finitud. CPU acumula el residuo del sistema ensamblado en Double; GPU lo evalúa en Float. Las tolerancias son del sistema lineal, no una estimación del error temporal; atol está en K. El lote completo se rechaza si un sistema no converge; no avanza el campo ni el tiempo visibles. La cancelación del modelo se propaga al worker y se observa entre lotes internos de iteraciones.

Se permite dt CN superior al límite explícito. El paso automático es safety × dtLimit × stepFactor (factor 10 por defecto), y el manual tiene prioridad. El explícito mantiene su validación CFL. La interfaz muestra dt, tiempo físico, velocidad efectiva, iteraciones internas por lote y residuo del último sistema. El indicador de posible oscilación usa dt × max(diagonal) > 1; es una advertencia conservadora, no una garantía en el caso contrario ni un estimador de precisión.

El arranque suavizado opcional usa dos medios pasos de Euler implícito únicamente en el primer paso físico. Después usa CN puro; pausar/reanudar no repite el arranque y reiniciar sí. Está desactivado por defecto.

## Verificación

Suite completa: **77 pruebas, 0 fallos, 0 omisiones**, incluyendo las pruebas de Metal y 9 pruebas específicas CN:

- Comparación CPU/GPU con eliminación matricial densa independiente para un paso CN, con máscara, materiales diferentes, fuente y condiciones Dirichlet/Robin/Neumann/adiabáticas.
- Convergencia temporal de orden 2 frente a la solución exponencial del modo propio discreto, separando error temporal del espacial.
- Modo de alta frecuencia: el paso grande cambia el signo, conserva módulo menor que 1 y el arranque suavizado lo amortigua.
- Calentamiento uniforme con fuente en dominio aislado y conservación de energía sin fuente.
- Arranque Metal aplicado una sola vez a través de lotes separados, y calentamiento aislado en GPU.
- Persistencia, valores anteriores predeterminados, dt superior a CFL aceptado solo para CN y validación de tolerancias no finitas.
- Animación CPU/Metal con último paso acortado hasta el tiempo final; sistema interno fallido rechaza el lote sin alterar campo, tiempo ni backend.
- Cancelación observada por el solver.
- Los ejemplos incluidos se ejecutan en ambos backends con tolerancias predeterminadas.

Resultados de dos pasos de los ejemplos (no son un benchmark de velocidad):

| Ejemplo | dt CN | Referencia estable explícita | Iteraciones internas CPU/GPU | Residuo del último sistema GPU |
| --- | --- | --- | --- | --- |
| cn_animacion | 1,050109102 s | 0,131263638 s | 160 / 160 | 4,8577e-6 K |
| cn_oscilaciones | 21,002182045 s | 0,525054551 s | 192 / 192 | 0,01064936 K |

Un factor de paso mayor no garantiza acelerar el cálculo en ese mismo factor. Cada paso implícito requiere trabajo interno; la mejora real depende de malla, tolerancia y paso. No se implementó adaptación automática de dt ni estimación automática del error temporal. No se recortan temperaturas ni se ocultan oscilaciones. Tolerancias inferiores a la precisión de Float pueden causar rechazo; no se relajan automáticamente.

Comando de pruebas:

```sh
CLANG_MODULE_CACHE_PATH=/private/tmp/yoguicuentas-clang-cache swift test --package-path yoguicuentas_metal --scratch-path /private/tmp/yoguicuentas-metal-build -Xswiftc -module-cache-path -Xswiftc /private/tmp/yoguicuentas-swift-cache
```

Release 0.11.0 compilada, empaquetada y firmada localmente; codesign --verify --deep --strict pasó. Build 20261026043009. El script abrió la nueva app. La interfaz fue validada por compilación y pruebas del modelo; no se realizó inspección visual automatizada.
