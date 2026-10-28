# Revisión en ejecución: fuente dentro del trapecio

Fecha: 25/10/2026. Versión 0.9.3, build 20261025161100.

Se revisó una copia temporal del ejecutable Release, con un identificador de bundle distinto para evitar seleccionar una instancia previa del usuario. La ventana mostró la versión y build indicados. Se usó CUA para abrir el selector y cargar `trapecio fuente` desde los recursos incluidos.

1. La carga inicial mostró el trapecio activo y una temperatura inicial de 30 °C, con borde superior prescrito a 50 °C.
2. Se pulsó Iniciar con CPU Swift. La fuente calentó una región circular interior, sin generar un hueco en la máscara.
3. La corrida alcanzó t=100 s y paso 1598; la ficha informó T máxima=95,21 °C y Tiempo final alcanzado.
4. Se pulsó Ajustar ahora. La imagen mostró claramente el foco térmico dentro del trapecio y el exterior inactivo separado por el lado inclinado.
5. Se cerró únicamente la instancia temporal con Cmd+Q.

Ejemplo: `examples/trapecio_fuente_v2.json`. Q=10 MW/m³, círculo de radio 0,04 m y profundidad de referencia 1 m. Potencia integrada medida por prueba: 50287,2467041 W en 102 nodos. El máximo observado corresponde a este ejemplo y estos parámetros.

Las rutas de edición se verifican en `Tests/SceneTests/SourceDomainTests.swift`: añadir antes/después del dominio, convertir figura en fuente, fuente sobre región con replace, fuente sobre límite ya referenciado, material/fuente simultáneos, selección de fuente, recorte y reapertura. No se afirma haber completado una revisión visual manual de todos esos paneles.
