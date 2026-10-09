# Informe de Etapa 2: DW-NOMINATE

**Versión para revisión: 2026-10-08.** Trabajo de título sobre la reimplementación y
refactorización del instrumento científico de Fortran a C++.

- **[Leer el informe completo](informe/main.pdf)**: 30 páginas de cuerpo, 75 páginas totales.
- **[Revisar el portafolio de figuras](figuras/figuras-e2-revision.pdf)**: ocho figuras y el cuadro T5, en nueve páginas.
- **[Descargar el informe y las fuentes de los diagramas](e2-public-review-2026-10-08.zip)**.

El informe está organizado por los cuatro criterios de la Etapa 2: retroalimentación;
avance del diseño; diseño según estándares de calidad; documentación. Incluye decisiones
D-01 a D-32, contratos y protocolos de pruebas. Los diseños y propuestas de la Etapa 3
pendientes se identifican como tales; su publicación no declara que estén implementados.

## Diagramas para revisión

Las figuras y el cuadro están publicados para revisar su correspondencia con el código,
la notación y la legibilidad. Aún no constituyen documentación oficial aprobada de QueVotan.
Su promoción al monorepo requiere la confirmación de autores y revisores y la adaptación
al público de ese repositorio. F5 fue reemplazada por el cuadro T5.

| Vista | PDF | SVG editable |
|---|---|---|
| Contexto | [PDF](figuras/F1-contexto.pdf) | [SVG](figuras/F1-contexto.svg) |
| Casos de uso | [PDF](figuras/F2-casos-de-uso.pdf) | [SVG](figuras/F2-casos-de-uso.svg) |
| Correspondencia Fortran/C++ | [PDF](figuras/F3-fortran-a-cpp.pdf) | [SVG](figuras/F3-fortran-a-cpp.svg) |
| Ciclo de estimación | [PDF](figuras/F4-ciclo-estimacion.pdf) | [SVG](figuras/F4-ciclo-estimacion.svg) |
| Mecanismos fieles y modernos (cuadro) | [PDF](figuras/T5-mecanismos-modernos.pdf) | [SVG](figuras/T5-mecanismos-modernos.svg) |
| Datos y tiempo servido | [PDF](figuras/F6-datos-tiempo-servido.pdf) | [SVG](figuras/F6-datos-tiempo-servido.svg) |
| Verificación | [PDF](figuras/F7-verificacion.pdf) | [SVG](figuras/F7-verificacion.svg) |
| Clases y propiedad del estado | [PDF](figuras/A1-clases-estado.pdf) | [SVG](figuras/A1-clases-estado.svg) |
| Secuencia de una estimación | [PDF](figuras/A2-secuencia-estimacion.pdf) | [SVG](figuras/A2-secuencia-estimacion.svg) |

## Alcance de esta publicación

Este paquete público contiene el informe, sus fuentes LaTeX y las vistas con PDF, SVG,
leyendas, generador, tabla de hechos y comprobaciones. **No incluye el repositorio privado
de investigación, las notas internas de revisión ni extractos de reuniones.**

El PDF conserva los bytes de la versión revisada. Algunos enlaces `run:` de sus anexos
apuntan a evidencia suplementaria del paquete de revisión alojado en el repositorio privado
`Quevotan/quevotan-db`. Esa evidencia requiere acceso separado; no está incluida en este ZIP
y esos enlaces locales no abrirán desde esta edición pública. El informe y todos los
diagramas de este índice sí pueden consultarse sin cuenta ni invitación.

El documento cita la revisión local del motor `ad945a9`, que incluye una reorganización
todavía pendiente de publicación. Este commit agrega únicamente documentación: no publica
esa reorganización, modifica el motor ni actualiza los resultados del artículo.
El Fortran original de 2004 y wmay, referente de reproducción del artículo, son distintos.
No se ejecutó un experimento nuevo para preparar esta publicación. El defecto entre hilos
documentado para el motor fiel no certifica la seguridad del moderno; su auditoría sigue pendiente.

## Fuentes y comprobaciones

- [Fuentes LaTeX](informe/) y [generador de las figuras](figuras/build_figuras.py).
- [Hechos y procedencia de los diagramas](figuras/FACTS.md).
- [Instrucciones de las figuras](figuras/README.md).
- [Comprobaciones del informe](informe/report-qa.json) y [de las figuras](figuras/qa-results.json).
- [Manifest SHA-256](manifest.json) y [checksum del ZIP](e2-public-review-2026-10-08.zip.sha256).

Para reconstruir el informe se utiliza el proyecto LaTeX de varios archivos:
`pdflatex`, `biber` y dos pasadas adicionales de `pdflatex`, desde `informe/`.
Los PDF de `figuras/` deben conservarse como carpeta hermana de `informe/`.
La tabla de hechos registra rutas de procedencia históricas; no todas son rutas del
árbol publicado actual. Para comprobar evidencia suplementaria, usar el paquete de revisión con acceso.
