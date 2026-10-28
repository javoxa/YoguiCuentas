# Estacionario directo · Metal 0.10.0

Se agregó Jacobi ponderado (ω=2/3) sobre el operador estacionario existente. La iteración se implementa como T += ω D⁻¹ r, acumulando diferencias de temperaturas vecinas y una corrección diagonal precomputada para conservar el sistema ensamblado y reducir cancelación en Float. Se mantienen campos dobles para lectura/escritura independientes; Metal reutiliza sus buffers y serializa el acceso entre corridas canceladas/reiniciadas.

La configuración se persiste en canvas.time.method y conserva explicit como valor predeterminado de archivos anteriores. La interfaz cuenta iteraciones, muestra el residuo actual y separa alcanzar el límite de converger. Cada componente requiere Dirichlet o Robin con h positivo; el tratamiento de Neumann puro con restricción de media queda pendiente. No se implementó integración temporal implícita, aceleración Chebyshev ni multigrid, ni se afirma una ventaja de velocidad frente al explícito.

## Verificación

- Suite completa final: 68 pruebas, 0 fallos y 0 omisiones, con acceso real a Metal. Incluye 11 pruebas estacionarias.
- Solución analítica de placa con fuente uniforme y lados aislados; comparación con el transitorio explícito.
- Solución analítica de placa con Neumann/Robin; materiales heterogéneos con media armónica de interfaces.
- Máscara circular con Robin e invariancia de nodos inactivos.
- Componentes desconectadas: rechazo de componentes sin referencia incluso cuando otra tiene Dirichlet.
- JSON v1/v2, valor predeterminado de archivos anteriores, residuo no finito, límite sin convergencia y convergencia en la última iteración.
- Corrida completa desde SimulationModel en CPU y GPU, reinicio y ausencia de tiempo físico en el modo directo.
- Ejemplo incluido estacionario_jacobi, 65×65: 14.080 iteraciones, residuo máximo 1,0898002756221103e-5 K/s, con las tolerancias originales y tres confirmaciones. No es un benchmark.
- Release compilada, app 0.10.0 empaquetada y firmada localmente; codesign --verify --deep --strict correcto. Script de apertura ejecutado correctamente. Build final 20261026041335.
- La inspección visual automatizada no se realizó: el acceso de Computer Use a YoguiCuentas Metal no estaba aprobado. La interfaz se validó por compilación y pruebas del modelo.

Comando de pruebas (fuera del sandbox para que Metal esté disponible):

```sh
CLANG_MODULE_CACHE_PATH=/private/tmp/yoguicuentas-clang-cache swift test --package-path yoguicuentas_metal --scratch-path /private/tmp/yoguicuentas-metal-build -Xswiftc -module-cache-path -Xswiftc /private/tmp/yoguicuentas-swift-cache
```

La primera formulación mediante suma de temperaturas absolutas se estancaba por redondeo en el ejemplo de 65×65. La prueba de regresión cubre la corrección por residuo; no se relajaron las tolerancias.
