# Manuscrito técnico para revisión por pares

**Implementación de un simulador educativo de conducción térmica de bajo costo computacional.**
Grillas reducidas y visualización mediante OpenGL.

Autor: Javier Armando Gutierrez. Departamento de Física, FCE, Universidad Nacional
de Salta, Salta, Argentina. Correspondencia: g.javier.ar@gmail.com.

Fecha: 02/11/2026. Revisión 2, para devolución técnica. No enviado ni publicado.
El informe Metal 0.11.0 permanece como antecedente y no se sobrescribe.

## Versión en inglés técnico británico

Traducción completa del 06/11/2026, basada en la revisión española 2:
[PDF en inglés](../output/pdf/yoguicuentas_paper_en.pdf) y
[fuente LaTeX autónoma](yoguicuentas_paper_en.tex). Incluye las cuatro figuras,
siete tablas, ecuaciones, referencias y apéndices. Se conservaron las coordenadas
de gráficos y los valores numéricos. La afiliación mantiene su nombre oficial.
[Control documental](control_documental_en.json).

```bash
python3 technical_report/verificar_traduccion.py
```

Para compilar esta traducción, usar los comandos de reproducción de abajo con
`technical_report/yoguicuentas_paper_en.tex` y un directorio de salida separado.
El regenerador de datos modifica solamente el manuscrito español; al actualizar
resultados, trasladar los bloques numéricos a inglés conservando sus pies y rótulos
traducidos, actualizar el control documental y volver a verificar ambos documentos.
Los cambios posteriores de interfaz no se atribuyen a las campañas de octubre.

## Archivos

- [PDF para lectura y devolución](../output/pdf/yoguicuentas_paper_20261030.pdf).
- [Fuente LaTeX autónoma](yoguicuentas_paper_20261030.tex): contiene coordenadas,
  tablas y bibliografía, sin requerir archivos externos para compilar.
- [Datos derivados del manuscrito](datos_manuscrito.json): valores de tablas y
  figuras, con hashes de los archivos originales utilizados.
- [Regeneración de tablas y figuras](preparar_datos.py): utiliza solo la biblioteca
  estándar de Python y los datos del repositorio; no vuelve a ejecutar solvers.
- [Carta de presentación editable](CARTA_PRESENTACION.md).

El eje del artículo es separar grilla física y resolución de pantalla para utilizar
pocos nodos cuando el ejercicio lo permite. Se documentan OpenGL, interpolación,
transferencia y animación con cálculo CPU, además de modelo continuo e integradores,
criterios de parada, métodos iterativos, precisión, protocolo de pruebas y de
costo, resultados, limitaciones y disponibilidad de artefactos. No presenta
validación experimental, eficacia educativa medida ni aceptación final de instalación.

## Reproducción documental

Desde la raíz del repositorio:

```bash
python3 technical_report/preparar_datos.py
mkdir -p tmp/pdfs/paper20261030
pdflatex -interaction=nonstopmode -halt-on-error \
  -output-directory=tmp/pdfs/paper20261030 \
  technical_report/yoguicuentas_paper_20261030.tex
pdflatex -interaction=nonstopmode -halt-on-error \
  -output-directory=tmp/pdfs/paper20261030 \
  technical_report/yoguicuentas_paper_20261030.tex
```

Abrir la fuente en el editor LaTeX permite editar el mismo documento con vista
previa. En esta sesión el compilador integrado no estuvo disponible por un
componente de sandbox ausente; el PDF se generó con pdfLaTeX ya instalado y se
revisaron las páginas renderizadas. No se instaló un entorno TeX adicional.

La verificación documental no reejecuta las campañas físicas. Los parámetros,
programas de ensayo y resultados numéricos se conservan en el repositorio.
El apéndice identifica la evidencia y explica cómo repetir las campañas.

## Antes de enviar

1. Confirmar financiación y conflictos de interés; la pregunta al autor está
   pendiente y el manuscrito no inventa una declaración negativa.
2. Revisar y asumir la autoría y el contenido, incluida la declaración de uso de IA.
3. Adaptar la plantilla a la institución o destino elegido, si exige otro formato.
4. Al depositar, identificar la revisión pública concreta por commit/manifiesto;
   comprobar acceso a los datos. No hay DOI asignado a esta revisión.
5. Si luego se incorpora validación de instalación o de interfaz, documentarla como
   revisión posterior con evidencia, sin alterar retrospectivamente las campañas.

## Reorientación de la revisión 2

Se reescribieron título, resúmenes, introducción, discusión y conclusiones en torno
al renderizado OpenGL como recurso de accesibilidad de hardware. Se agregó una
sección de implementación y un esquema del recorrido de datos. Las mediciones
numéricas conservan su alcance; no se presentan como FPS ni como una comparación
de renderizadores. Los antecedentes i3/i5 son pruebas de uso comunicadas por el
autor y todavía no incluyen un benchmark instrumentado. La revisión 1 permanece
en el paquete de publicación del 30/10 y en el respaldo local.
