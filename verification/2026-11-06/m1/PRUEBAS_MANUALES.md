# Aceptación manual — YoguiCuentas Metal

Fecha y hora de prueba:
Equipo / macOS:
Carpeta de resultados:
Versión y build mostrados en la app:
Alimentación (batería / cargador):
Cambios hechos al código, si los hubo:

Marcar cada caso **APROBADO / FALLÓ / NO PROBADO**. Anotar pasos exactos para
reproducir cualquier error, procesador, escenario e idioma. Guardar siempre el
escenario usado y una captura si el problema es visual. No dejar un casillero
vacío interpretado como aprobación.

## A. Primera apertura y ventana

- Abrir la app con `bash 02_abrir_app.sh` y confirmar versión/build.
- Registrar autorización o mensaje de Gatekeeper, si aparece.
- Comprobar que sidebar, menús y botones no quedan tapados por el lienzo 2D/3D.
- Achicar la ventana y probar una pantalla pequeña/letras grandes. Comprobar
  acceso a Aplicar y Cancelar, desplazamiento lateral y ausencia de controles cortados.

Resultado:
Observaciones / capturas:

## B. Idioma durante la corrida y con formularios abiertos

- Al iniciar, la interfaz debe estar en español, aunque macOS use otro idioma.
- Abrir `cobre_seno` desde los escenarios incluidos e iniciar con CPU Swift.
- Cambiar **Idioma → English** durante la corrida. Tiempo/pasos deben continuar;
  no debe reiniciarse ni sustituirse el escenario.
- Volver a Español y repetir con GPU Metal, si está disponible.
- Abrir parámetros, cambiar material/método/borde y alternar idioma antes de
  aplicar. Los valores y la selección deben conservarse.
- Revisar menús, títulos, ayudas, nueve criterios de parada y textos de estado.
- Repetir con el editor geométrico abierto, una figura seleccionada y un valor Q
  escrito. Guardar un escenario y volver a abrirlo; conservar la selección de
  método/contorno y sus identificadores JSON.
- Cerrar y abrir una instancia nueva: debe volver al español inicial.

Resultado:
Observaciones / textos sin traducir / capturas:

## C. Escala, visualización e isotermas

- En `cobre_seno`, alternar mapa T, superficie 3D, gradiente y flujo.
- Girar/acercar la superficie; comprobar acceso al menú y la barra lateral.
- Activar ajuste automático y luego modificar mínimo/máximo manualmente.
- Arrastrar extremos y centro de la barra de colores; comprobar el ajuste actual.
- Pedir 3 y luego 10 niveles de isotermas. Comprobar valores de temperatura y
  activación/desactivación de sus etiquetas en 2D y 3D.
- Los niveles deben ser equiespaciados en temperatura; no se exige igual distancia
  espacial ni un número de curvas conexas igual al de niveles. Si un nivel cruza
  varias regiones, puede producir varias curvas. Un campo uniforme no tiene
  contornos internos que mostrar.
- Guardar PNG y comprobar correspondencia con el campo visible, etiquetas y escala.

Resultado:
Observaciones / capturas / PNG:

## D. Recortes de prueba_01 y condiciones de borde

Abrir desde Archivo/Abrir JSON el archivo de `escenarios_de_prueba/` indicado.

1. Abrir `prueba_01_original_v1.json`, comprobar que carga y que se ven los dos
   recortes. Anotar límites de edición de la máscara v1. En Swift todavía no se
   recuperan automáticamente los rectángulos como se hace ahora en Linux.
2. Abrir **`prueba_01_bordes_editables_v2.json`** y entrar en Editar escena.
3. Con Elegir borde, seleccionar un lado de un rectángulo excluido. Comprobar
   resaltado y aparición de sus campos de condición.
4. Asignar al primer recorte: inferior Dirichlet 50 °C; derecho Neumann
   +123 W/m²; superior Robin con ambiente 20 °C y h=9 W/(m² K); izquierdo adiabático.
   El flujo Neumann positivo sale del dominio activo.
5. Volver a seleccionar cada lado y verificar sus valores. El otro recorte debe
   conservar su condición adiabática.
6. Elegir sucesivamente bordes exteriores del lienzo. Deben poder leerse y editarse
   condiciones ya cargadas, sin errores.
7. Aplicar al problema, guardar JSON, cerrar/reabrir el escenario y comprobar
   persistencia. Exportar un campo tras calcular en CPU y otro en Metal.
8. Registrar si el borde resaltado corresponde al lado elegido o si otra figura,
   material o fuente intercepta la selección.

Resultado v1 (carga y limitación conocida):
Resultado v2 (edición por lado):
JSON, CSV y capturas guardados:
Observaciones:

## E. Dibujo, regiones, fuentes y materiales

- En una escena nueva, dibujar un rectángulo, seleccionarlo e incluir/excluir su
  interior. Aplicar y comprobar que se modifica el dominio.
- Dibujar una línea de borde a borde; elegir una región de cada lado. Excluir una
  y asignar una condición al segmento que ahora queda expuesto.
- Asignar material y fuente a figuras. Cambiar Q, mover, duplicar, deshacer y
  rehacer; comprobar que la selección se corresponde con la figura visible.
- Entre dos regiones activas hay conducción; no exigir un borde externo allí.
- Guardar y reabrir la escena con sus materiales, fuentes y contornos.

Resultado:
Observaciones / escenario:

## F. Métodos, parada y exportación

La suite automática ya verifica referencias analíticas y balances. Aquí se
comprueba el recorrido visible del usuario:

- Ejecutar Euler y CN (`cn_animacion`), CPU y Metal. Pausar, reanudar y reiniciar.
- Abrir `cn_oscilaciones`; comprobar comportamiento de CN y opción Rannacher.
  Un paso grande puede oscilar aunque sea estable; no atribuirlo al renderizado.
- Abrir `estacionario_jacobi` y `estacionario_gauss_seidel`. Ambos deben avanzar
  iteraciones sin asignarles segundos físicos.
- Revisar los nueve criterios y selección todos/muestra con semilla. Ejecutar al
  menos residuo, máximo nodal y traza. Registrar criterio, tolerancias y parada.
- No interpretar `criterion_met` como equilibrio si el residuo físico no cumple;
  un límite de pasos/iteraciones debe informarse sin declarar convergencia.
- Exportar campo e historial. Guardar cada corrida con un nombre que identifique
  método, CPU/Metal e idioma. Verificar que corresponden al estado mostrado.

Resultado:
Archivos / observaciones:

## G. Resumen para la devolución

Casos aprobados:
Casos fallidos:
Casos no probados:
Tests automáticos omitidos (copiar nombres del log):
Problemas que impiden usar la app:
Problemas menores de interfaz/traducción:
Resultados o gráficos que parecen incorrectos:
Cambios propuestos o realizados:

Después de completar este archivo dentro de resultados y guardar los adjuntos,
ejecutar **`bash 03_reunir_resultados.sh`** desde para_mc y traer el ZIP y su SHA-256.
