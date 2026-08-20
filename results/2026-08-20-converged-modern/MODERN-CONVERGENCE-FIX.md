# Engine-modern: exportación dinámica y convergencia certificada

## Fallos corregidos

1. `engine-modern` estaba incompleto en `main`: CMake referenciaba directorios
   `src/`, `include/` y `tests/` que no estaban publicados. Este paquete incorpora
   el árbol compilable completo.
2. La reconstrucción exportada usaba el índice temporal del panel completo. El
   objetivo, en cambio, construye la base de Legendre sobre la secuencia compacta
   de períodos servidos por cada legislador. En Chile, recargar el CSV anterior
   cambiaba la log-likelihood en 30.496 nats.
3. Los CSV dinámicos incluían posiciones extrapoladas para períodos no servidos.
   Ambos exportadores ahora contienen únicamente pares `(legislator_id, period)`
   observados: 2.855 en Chile y 523 en EE. UU.
4. El ejecutable sólo admitía un número fijo de ciclos. Ahora puede detenerse por
   mejora absoluta o relativa, con mínimo de ciclos y paciencia configurables; un
   descenso global superior a la tolerancia aborta la ejecución.

## Contrato de factibilidad

El modelo histórico restringe el intercepto temporal de cada legislador y el
punto medio de cada votación al disco unitario. Los términos temporales no están
restringidos; por ello una posición reconstruida para un período puede quedar
fuera del círculo sin que el retorno del optimizador sea inviable.

Las corridas publicadas usan SLSQP para los bloques restringidos y BOBYQA para
los escalares. Ningún retorno materialmente inviable es proyectado y aceptado:
los retornos fuera de tolerancia son rechazados. Una corrección radial sólo puede
eliminar un residuo que ya se encuentre dentro de la tolerancia declarada.

## Criterio y resultados

Se exigió una mejora de log-likelihood no superior a 1 nat durante dos ciclos
consecutivos, después de un mínimo de cuatro ciclos. La búsqueda escalar fue
global dentro de `0.01 <= w2 <= 2` y `0.05 <= beta <= 20`.

| Panel | Ciclos | LL común | Mejora final | w2 | beta | Estado |
|---|---:|---:|---:|---:|---:|---|
| Chile dinámico, modelo 2 | 238 | -81,521.360302 | 0.998650 | 1.526389 | 20 | Convergido bajo cotas |
| EE. UU. dinámico, modelo 1 | 62 | -33,166.396767 | 0.953403 | 1.386233 | 20 | Convergido bajo cotas |

En ambos paneles `beta` termina en su cota superior. Estos resultados no deben
describirse como máximos interiores: son óptimos numéricos condicionados por las
cajas declaradas. Elevar la cota constituye otro modelo computacional y exige una
nueva prueba de sensibilidad.

## Certificación

- Chile: 849.364 bloques aceptados en el segmento final auditado; cero retornos
  inviables aceptados y cero disminuciones aceptadas.
- EE. UU.: 166.780 bloques aceptados; cero retornos inviables aceptados y cero
  disminuciones aceptadas.
- La recarga serial de los estados exportados reproduce la LL de Chile exactamente
  y la de EE. UU. con diferencia `2.18e-11`.
- Las nueve pruebas de CTest pasan, incluida una prueba dinámica de exportación,
  recarga y reevaluación común.

## Gráficas

El círculo unitario de las figuras es una referencia para las cantidades que sí
están restringidas; no es una frontera para las coordenadas dinámicas realizadas.
El generador ajusta los ejes para no ocultar trayectorias legítimas fuera del
círculo. El archivo `data/chile-dynamic/legislator_metadata.csv` de `main` tiene
vacíos los campos `nombres` y `partido`. Por eso las figuras chilenas se publican
en gris y lo declaran en el subtítulo; no se imputaron etiquetas partidarias.

## Ejecución

```bash
cmake -S engine-modern -B engine-modern/build -DCMAKE_BUILD_TYPE=Release
cmake --build engine-modern/build -j
ctest --test-dir engine-modern/build --output-on-failure

engine-modern/build/dwnominate-modern \
  --input-dir=data/chile-dynamic \
  --output-dir=out/chile \
  --wnominate=data/chile-dynamic/wnominate_coordinates.csv \
  --seed-per-period=data/chile-dynamic/wnominate_coordinates_per_period.csv \
  --model=2 --periods=23 --dimensions=2 \
  --iterations=300 --min-iterations=4 \
  --convergence-abs=1 --convergence-patience=2 \
  --block-solver=slsqp --scalar-search=global --threads=1
```

---

## Verificación independiente, 2026-08-20

Medido sobre los CSV publicados aquí, sin volver a correr el motor.

**Las dos correcciones de exportación se confirman.** Chile entrega 2.855 filas y EE. UU. 523, que
coinciden exactamente con los pares `(legislator_id, period)` servidos según la exportación de
`engine-faithful`. Cero filas rellenadas. Este defecto se había detectado por separado el mismo día
en `engine-modern`, en el motor Fortran y en las figuras derivadas de ambos.

**El objeto restringido queda dentro del disco.** El nivel de carrera, que es lo que el modelo
restringe:

| panel | radio máximo | fuera del disco |
|---|---:|---:|
| EE. UU. dinámico | **1.0000** | **0 de 168** |
| Chile dinámico | 1.0326 | 5 de 338 |

Los cinco casos chilenos exceden por menos de 3,3 %, consistente con que el promedio sobre períodos
servidos es una aproximación del término constante y no el término mismo.

**Las reconstrucciones por período siguen saliendo, y deben hacerlo.** Chile 294 de 2.855 (10,30 %),
máximo 2,9905. La masa está concentrada en el inicio del panel y decae de forma monótona:

| período | 1 | 2 | 3 | 4 | 5 | 21 | 23 |
|---|---:|---:|---:|---:|---:|---:|---:|
| fuera | 42,0 % | 27,5 % | 18,3 % | 15,7 % | 13,9 % | 0,0 % | 0,6 % |

**Advertencia para las figuras**: los cortes publicados (períodos 8, 21 y 23) caen en la zona limpia,
con 16, 0 y 1 punto fuera respectivamente. Una figura de esos cortes no representa la tasa del panel
completo. Debe citarse el 10,30 % junto a cualquier corte.

**Lo que estas corridas no son.** `beta` termina en su cota superior de 20 en ambos paneles, como el
propio documento advierte, y `w2` llega a 1,5264 en Chile frente a la referencia de 0,5063. Medido
contra `engine-faithful`: `r1 = +0,9803`, `r2 = +0,7763`, y la dispersión de la dimensión 2 queda en
**0,718 veces** la de `engine-faithful`, es decir, la compresión de la segunda dimensión persiste en
esta corrida global convergida.

**No son comparables con la tabla de `2026-08-20-three-engine/`**, que fija 4 ciclos en los tres
motores. Estas pararon por criterio de mejora, 238 ciclos en Chile y 62 en EE. UU., y se ejecutaron
con 4 hilos, de modo que ni el número de ciclos ni el tiempo de pared son comparables.
