## Actualización 0.9.5 — fuentes seleccionadas y aplicación

El caso informado usa Q=5000 y una región activa naranja. Se probó seleccionar una región delimitada, asignar fuente, introducir 5000 sin confirmar el campo, aplicar a SimulationModel e iniciar un paso, en CPU y Metal. Se verifica Q en la escena aplicada, campo de fuente=5000 en el interior, máscara activa, temperatura esperada 20+5000/capacidad*dt y ausencia de calentamiento fuera. Esto verifica el recorrido programático; no reproduce por sí solo el fallo visual informado.

Cambios: intensidad de fuente con actualización inmediata y validación de texto (coma decimal y notación científica); reselección de interiores de fuentes/materiales que dejaron de delimitar regiones; rechazo de aplicar fuentes no nulas con cero nodos activos, con acción explícita para incluir la región; informe de nodos/potencia en inspector y simulación; puntos naranjas en 2D basados en el campo aplicado; acceso directo Editar escena. Se quitó el relleno naranja puramente vectorial que podía cubrir áreas inactivas. Aplicar mantiene t=0 y pausa, con indicación de Iniciar.

Verificación: 57 pruebas Swift aprobadas; evidencia `verification/region-apply-final.log` y `verification/region-apply-integration.log`. La inspección por CUA del editor anidado 0.9.4 falló con “native pipe closed before response”. No se afirma revisión visual completa por ese resultado.


### Revisión visual efectuada en 0.9.5 (build 20261025170251)

CUA pudo inspeccionar el acceso directo Editar escena en una copia de prueba con bundle id independiente. Se dibujó un rectángulo (x=0.125, y=0.1875, ancho/alto=0.203125), se pulsó Elegir región y se seleccionó su interior. Se asignó fuente y se escribió 5000 con teclado, sin Enter. El inspector cambió inmediatamente de 50 a 5000 W/m³ y de 2.0630 a 206.30 W. Aplicar al problema cerró la hoja y la simulación mostró “Fuente: 676 nodos (676 libres) · 206,30 W integrados” y “Problema aplicado … Pulsá Iniciar”; la captura mostró puntos en los nodos correspondientes. Al reabrir y seleccionar Región 1 se conservó Q=5000.0. La copia de prueba se cerró; no se cerraron instancias del usuario. Esto verifica selección/asignación/aplicación/persistencia en esa escena real de interfaz, además de los tests CPU/Metal. No reproduce el escenario exacto del usuario, que no fue proporcionado en JSON.
