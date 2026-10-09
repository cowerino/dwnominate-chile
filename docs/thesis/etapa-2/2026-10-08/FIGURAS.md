# Figuras y cuadro de mecanismos del informe E2

Estado: regenerado localmente el 8 de octubre de 2026. El handoff y la revisión Astra de esa
fecha gobiernan esta edición. `diagramas/`, `diagramas-corregidos/`, los red teams y el papel
JCC quedan preservados. La versión anterior del generador y los documentos está en
`figuras/historical/pre-regeneration-2026-10-08/`.

Seis figuras de cuerpo (F1, F2, F3, F4, F6, F7), un cuadro de mecanismos (T5, que reemplaza F5)
y dos figuras de anexo (A1, A2). Los números impresos de figuras y cuadros los asigna LaTeX;
los identificadores de artefacto no constituyen una cantidad obligatoria de diagramas.

| ID | Pregunta y alcance | Relaciones |
|---|---|---|
| F1 | Entorno del instrumento lógico de investigación; ruta R/ejecutables | flujos etiquetados |
| F2 | Metas de estimación, validación y comparación dentro del sujeto | casos de uso UML; todas las elipses dentro |
| F3 | Correspondencia de responsabilidades desde 2004 y wmay hacia C++ fiel | una correspondencia horizontal por fila; sin dependencias |
| F4 | Fases de un ajuste del perfil wmay/fiel, 2D, T=4 | actividad, ciclos fijos, parámetros terminales y resumen fiel mixto (M-02) |
| T5 | Búsquedas fieles/modernas, restricciones y mecanismo activo | cuadro: peso, beta, votaciones, legisladores |
| F6 | Panel, fila servida, tiempo local, semillas y trayectoria | modelo conceptual, no esquema de CSV/base de datos |
| F7 | Puntuación común con wmay y comparación de mapas | actividad con objetos; cobertura, marco, sin reescalar |
| A1 | Propiedad del estado fiel y funciones auxiliares | clases UML, anexo |
| A2 | Una invocación del portal, aceptación y fallos | secuencia UML; salida cero/CSV legibles, cobertura por validar; nota a F4 |

Reglas: Palatino, ancho de inserción 13,5 cm, fuente mínima de 8 pt, sin reducir para paginar.
El dibujo declara el sujeto/perfil. Pies breves identifican alcance y procedencia; la leyenda
explica notación necesaria, y la justificación científica se desarrolla en la prosa.
Se verifican semántica, flechas, cruces, recorte y legibilidad en los PNG y dentro del informe.

La correspondencia F3 no prueba ocultamiento completo ni mantenibilidad medida. Las inclusiones
C++ están en un cuadro independiente del anexo de correspondencia; A1 cubre propiedad del estado.
T5 distingue BOBYQA escalar local y COBYLA por bloques de SLSQP/híbrido opcionales. Los controles
de medición van a los protocolos de reproducción wmay y aceptación original 2004. GRID activo
en el fiel no establece equivalencia de todo el motor con 2004.

Chile como validación en lugar de objetivo propio, el umbral RNF01 y el diseño de periodización
siguen pendientes de ratificación. La inspección visual no equivale a una prueba de comprensión
con un lector externo; esa prueba sigue abierta.
