# Juego actual de exposición E2

Regenerado el 8 de octubre de 2026. Fuente: `build_figuras.py`. Alcance y orden en `../FIGURAS.md`;
evidencia por elemento en `FACTS.md`. Se generan seis figuras de cuerpo, el cuadro T5 y dos
figuras de anexo: nueve elementos, ocho figuras y un cuadro, más el portfolio de revisión.

F5 fue reemplazada por `T5-mecanismos-modernos.{pdf,svg,caption.txt}`. F5 y el generador anterior
se preservan en `historical/pre-regeneration-2026-10-08/`; no entran en el manifest ni portfolio
actuales. El manifest enumera los archivos activos explícitamente, sin incluir PDFs antiguos.

## Reconstrucción

```powershell
& 'C:/Users/cow/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' build_figuras.py
python qa_figuras.py
```

ReportLab usa Palatino de `C:/Windows/Fonts/pala.ttf`, `palab.ttf`, `palai.ttf`. PyMuPDF genera
`qa/*.png` a 220 ppp y `qa-results.json`: ancho 135 mm, altura máxima 190 mm, fuentes incrustadas,
sin raster, texto dentro del lienzo, sin solapamiento y mínimo 8 pt. El generador mide cajas y
textos antes de exportar. La revisión final verifica también cada elemento insertado en el PDF.

Cada elemento tiene SVG editable, PDF vectorial y pie breve `.caption.txt`. Los pies del informe
añaden referencias internas/decisiones y son la versión de entrega; ambos describen el mismo
alcance. `figuras-e2-revision.pdf` incluye la pregunta y la lectura esperada por elemento.

El informe carga este directorio mediante `../figuras/`. La copia anidada `informe/figuras/` es
histórica y no se usa. El paquete de revisión conserva `informe/`, estos archivos activos y
`evidence/` para resolver vínculos locales; no distribuye copias divergentes como autoridad.

## Cambios de esta pasada

F1 simplifica el contexto lógico y conserva portal/ejecutable; F2 incluye toda la validación en
el sujeto; F3 usa solo correspondencia, con dependencias en cuadro de anexo; F4 mantiene orden,
ciclos fijos y perfil wmay/fiel; T5 muestra mecanismos y restricciones; F6 mantiene datos/tiempo
conceptuales; F7 conserva evaluador wmay, cobertura y marco; A1 conserva propiedad; A2 muestra
una llamada run() y nota a F4. No se mide ventaja numérica o de mantenimiento con estas vistas.

El registro de regeneración describe hashes, QA, compilación, páginas y pendientes externos.

La pasada de consistencia posterior al red team final precisa el resumen fiel mixto (M-02)
en F4/A2, la aceptación por CSV legibles en A2 y la validación de claves/cobertura pendiente
de I5 en F7. Se corrigen descripciones, no el código de los motores ni sus resultados.
