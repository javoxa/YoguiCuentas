# Primeras pruebas de uso — candidata Metal M1 (29/10/2026)

Estado: numeración base 0.11.0, desarrollo identificado por build y hashes;
no se publicó una release. Candidata: `YoguiCuentas Metal.app` en esta carpeta.
La app estable de `dist` se conserva. Cerrar voluntariamente instancias anteriores
para identificar la candidata; no se cerraron ventanas con trabajo del usuario.

La compilación release arm64 y la firma ad hoc están verificadas. Se solicitó
la apertura con `open -n`; eso no certifica clics, apariencia ni instalación.
El control de interfaz respondió **“Computer Use was not approved to use
YoguiCuentas Metal”**. Por ese motivo no hay capturas y los casos siguientes
permanecen pendientes de ejecución manual, con CPU Swift y GPU Metal.

| Caso | Procedimiento | Aceptación | Estado |
|---|---|---|---|
| Primera apertura | Copiar la candidata a otra Mac Apple Silicon con macOS 13+, abrir desde Finder | Ventana y recursos cargan; anotar avisos sin desactivar protecciones | Pendiente |
| Solvers | Cargar estacionario_gauss_seidel; iniciar/pausar/reanudar; repetir Jacobi, Euler y CN | GS/Jacobi muestran barridos sin segundos; CN muestra iteraciones internas | Pendiente visual; modelo probado |
| Criterios | Configurar nueve criterios, todos/muestra, cantidad y semilla; guardar/reabrir | Parámetros persisten; residuo/traza no usan la muestra como sustituto | Pendiente visual; persistencia probada |
| Falsa convergencia | Abrir scenarios/falsa_convergencia_dt_pequeno.json e iniciar | «Criterio ΔT cumplido; residuo físico sin confirmar» | Pendiente visual; test automático aprobado |
| Reinicio | Reiniciar durante cálculo y cambiar procesador | Campo inicial, contadores e historial limpios; detenido | Pendiente visual; modelo probado |
| Editor | Dibujar región y recta, seleccionar, incluir/excluir, asignar fuente/material/contorno por tramo y aplicar | Roles conservados y condición efectiva en caras expuestas | Pendiente por clics; modelo probado |
| Representación | Isotermas, etiquetas, escala manual/automática, barra con mouse, 2D/3D y PNG | Curvas equiespaciadas en T; rótulos y leyenda legibles | Pendiente |
| Exportación | Exportar campo e historial durante pausa y al detenerse | CSV, metadata.json, scenario.json y convergence.csv coherentes | Pendiente de paneles; escritura probada |
| Historial largo | Más de 512 controles; exportar y reiniciar | Truncamiento indicado y limpieza al reiniciar | Pendiente visual; límite probado |

Registrar por caso: fecha, equipo, backend efectivo, escenario, resultado,
aviso/error y captura si se dispone del permiso. La aprobación automática
numérica no sustituye esta aceptación. Una firma ad hoc local tampoco equivale
a Developer ID/notarización para distribución pública.
