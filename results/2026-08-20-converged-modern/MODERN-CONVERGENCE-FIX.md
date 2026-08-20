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

La FAQ original describe ese intercepto como la media de los scores. Esto es
exacto para el modelo lineal sobre la malla simétrica de períodos servidos. Para
el modelo cuadrático y una cantidad finita `S` de períodos,

```text
media(x) = beta_0 + beta_2 / (S - 1),
```

porque la media discreta de `P2(t)=(3t^2-1)/2` es `1/(S-1)`. Por consiguiente,
la implementación y la auditoría denominan *centro restringido* a `beta_0`, sin
identificarlo en general con el promedio aritmético.

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
- La reconstrucción de los coeficientes desde los CSV tiene error máximo
  `1.33e-15` en Chile y `8.88e-16` en EE. UU.
- Los 338 interceptos chilenos y los 168 estadounidenses cumplen el disco
  unitario. El máximo es `1 + 4e-16`, residuo de punto flotante.
- En Chile hay 294 posiciones legislatura-a-legislatura fuera del círculo y
  cinco promedios aritméticos fuera de él, pero ningún intercepto fuera. En
  EE. UU. hay cinco posiciones temporales fuera y ningún intercepto fuera.

## Gráficas

El círculo unitario de las figuras es una referencia para las cantidades que sí
están restringidas; no es una frontera para las coordenadas dinámicas realizadas.
La figura de carrera representa ahora `beta_0`, no el promedio aritmético, y el
generador ajusta los ejes para no ocultar trayectorias legítimas fuera del
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
