# Mapas de disco unitario, 2026-08-20

**Una proyección de disco unitario por figura. Una.** Puntos coloreados por partido, leyenda de
partidos debajo. Generador `../../generators/map_disk.py`, driver `_render_disk_maps.py`. PDF + PNG.

Sigue la convención ya establecida en `quevotan-db/maps_2026-05-24/make_maps.py`: color de partido
desde un puntaje izquierda-derecha a través de la rampa `coolwarm`, dimensión 1 orientada para que el
bloque de derecha quede positivo (la polaridad es un gauge libre), ejes punteados por el origen.
Agregado aquí: el círculo unitario como regla de referencia.

## Las 20 figuras

**Chile, estático (un ajuste por legislatura)** — `cl-static-leg{353,366,368}-{fortran,ours}`

**US, estático, motores corregidos** — `us-static-sen90-{fortran,ours}`

**Chile, dinámico (panel de 23 períodos)** — `cl-dyn-leg{353,366,368}-{fortran,ours}` son cortes
transversales del ajuste conjunto en las mismas tres legislaturas que tienen ajuste estático, de modo
que el par estático/dinámico es directamente comparable. `cl-dyn-carrera-{fortran,ours}` es el
promedio sobre los períodos servidos, 2002-2021.

**US, dinámico (panel de 5 períodos)** — `us-dyn-p5-{fortran,ours}` y `us-dyn-carrera-{fortran,ours}`.

## Procedencia

Todos los brazos C++ se corrieron el 2026-08-20 con el binario **completamente corregido**:
absence-fix, códigos de voto canónicos, exportador (t local, orden polinómico efectivo, sin relleno)
y semilla de respaldo en el origen. `quevotan-api@79031cf`.

| panel | LL | placements |
|---|---|---|
| Chile leg 353 / 366 / 368 | −1132.370286 / −6276.201346 / −13296.521959 | 121 / 155 / 161 |
| US Senate 90 | −15457.166891 | 102 |
| Chile 23 períodos | −98603.656973 | 2,855 |
| US 5 períodos | −38462.783549 | 523 |

Los conteos de placements del panel dinámico coinciden **exactamente** con los del Fortran, panel por
panel (US: 111/102/105/100/105 en los cinco períodos; Chile: 2,855), porque el exportador corregido
emite sólo los períodos servidos, igual que `us_legout.dat`.

## Dos cosas que un lector va a preguntar

1. **En el panel dinámico hay puntos fuera del círculo, y es normal.** El Fortran llega a radio
   máximo 2.3509 con 188 de 2,855 fuera; nosotros 2.4161 con 185. Es una propiedad del polinomio
   temporal, compartida por ambos motores. En los paneles **estáticos** todos los motores C++ están
   en radio máximo **exactamente 1.000000**, ninguno fuera; el 1.0002-1.0006 del Fortran es su
   redondeo de salida a 3 decimales.
2. **En US Senate 90 los partidos se separan en diagonal, no a lo largo de la dimensión 1.** Está
   igual en el Fortran. Es una propiedad del ajuste, no un problema de orientación.

## Formas rechazadas

`../rejected-2026-08-20/` guarda las dos series anteriores del mismo día: las de segmentos de
desplazamiento (tres estilos de datos en un panel) y las facetadas por partido (muchos discos por
figura). Ambas rechazadas por Roberto. **Un disco por figura.**
