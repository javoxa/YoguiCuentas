## Actualización 0.9.4 — dibujar y después asignar

Se quitó el selector de rol previo al dibujo. Cada figura nueva queda seleccionada; el inspector ofrece fuente interior, dominio y material antes de los campos geométricos. Los vértices de mano alzada se editan en una sección plegable. Los trazos que vuelven al inicio se cierran sin duplicar el primer vértice; se capturan sin snap y sin muestras consecutivas repetidas. Los trazos abiertos permiten cierre explícito para fuente interior o fuente de línea.

Verificación: 53 pruebas Swift aprobadas, incluyendo eventos AppKit de pulsar/arrastrar/soltar, cierre automático con/sin simplificación, cierre posterior, fuente de línea y calentamiento CPU del interior sin cambiar la máscara activa. Evidencia: `yoguicuentas_metal/verification/freehand-tests-final.log`. Esta evidencia no equivale a una revisión visual completa del editor.

