# Resultado del experimento de inicialización controlada

## Conclusión

La comparación anterior entre Fortran y C++ no permitía evaluar la fidelidad de
la traducción, porque cada implementación partía de un mapa distinto. El
experimento A/B realizado únicamente con C++ demuestra que ese cambio de
inicialización basta para producir diferencias importantes, sobre todo en la
segunda dimensión y en el primer Congreso. Esto no demuestra que la traducción
sea incorrecta ni que NLopt encuentre un óptimo mejor que Fortran.

La prueba definitiva Fortran/C++ queda preparada, pero la corrida Fortran no se
pudo ejecutar en este entorno porque no están disponibles R, `Rscript` ni un
compilador Fortran.

## Diseño

- Congresos 111 a 115; 2.940 votaciones.
- 168 legisladores en el panel y 523 observaciones legislador-período activas.
- Dos dimensiones y modelo temporal lineal.
- Cinco ciclos efectivos WINT-SIGMAS-RC-LEG.
- `beta=5.9539`, `w2=0.3463`, parámetros de votaciones inicialmente nulos.
- Perfil NLopt `standard`; sin redondeo legado a tres decimales.
- Inicio común calculado por SVD con los cinco períodos, escalado a radio máximo
  0,95 y cuantizado una sola vez a IEEE float32.

Para el A/B, ambas corridas C++ son idénticas salvo por el mapa inicial. La
solución iniciada con el archivo antiguo del repositorio se alinea a la solución
de inicio común mediante una transformación ortogonal que conserva el origen:
se permiten rotación y reflexión, pero no traslación ni cambio de escala.

## Función objetivo después de cinco ciclos

| Inicio C++ | Log-verosimilitud | Clasificación reportada | w2 | beta |
|---|---:|---:|---:|---:|
| Común, cinco períodos | -37123,688755 | 93,2916 % | 1,132032 | 4,034787 |
| Archivo del repositorio, Congreso 111 | -37384,549912 | 93,2728 % | 1,370821 | 3,983526 |

El inicio común termina 260,861157 unidades por encima en log-verosimilitud. Es
una diferencia entre cuencas o trayectorias de optimización con solo cinco
ciclos, no una comparación entre optimizadores. La mejora entre los ciclos 4 y
5 todavía es 1.378,416272 para la corrida común, por lo que tampoco se ha
demostrado que ese punto sea el óptimo global.

Una evaluación externa de la misma función probit en doble precisión entrega
-37123,688369 para el inicio común y -37384,549991 para el inicio antiguo. Las
diferencias respecto de la evaluación interna son inferiores a 0,0004.

## Desplazamiento por Congreso

| Congreso | n activo | r dimensión 1 | r dimensión 2 | Distancia media | p90 | Máxima |
|---:|---:|---:|---:|---:|---:|---:|
| 111 | 111 | 0,995140 | 0,051073 | 0,260842 | 0,561906 | 1,453569 |
| 112 | 102 | 0,997394 | 0,454360 | 0,190068 | 0,300589 | 0,844412 |
| 113 | 105 | 0,997252 | 0,620234 | 0,164821 | 0,277055 | 0,688058 |
| 114 | 100 | 0,995771 | 0,760974 | 0,153096 | 0,262640 | 0,688058 |
| 115 | 105 | 0,993915 | 0,748513 | 0,176814 | 0,303139 | 0,688058 |
| Conjunto | 523 | 0,995931 | 0,486452 | 0,190290 | 0,318216 | 1,453569 |

La dimensión 1 es estable. La dimensión 2 es muy sensible al inicio, en especial
con un único Congreso. Por eso una correlación aislada como 0,988759 no basta
para validar una traducción: también deben controlarse el punto inicial, los
ciclos, la orientación, la escala, los parámetros de votaciones y la función
objetivo común.

El archivo antiguo contiene 61 de 168 legisladores en `(0,0)`. Entre los
legisladores activos, la cantidad de inicios nulos aumenta de 4 en el Congreso
111 a 52 en el 115. Esto hace que el mapa del Congreso 111 sea una inicialización
especialmente débil para estimar una trayectoria de cinco períodos.

## Determinismo

Una repetición literal de la corrida común produjo archivos de parámetros de
votaciones, coordenadas y traza de convergencia idénticos byte por byte. El único
cambio fue `elapsed_seconds` (170,24 frente a 173,12 segundos). En esta
configuración, el algoritmo es determinístico; lo observado es dependencia del
inicio, no aleatoriedad.

## Círculo unitario

En la corrida común aparecen 22 posiciones legislador-período activas fuera del
círculo, con radio máximo 1,241125. En la corrida de inicio antiguo aparecen 23,
con radio máximo 1,243880. Los 2.940 puntos medios de las votaciones respetan el
radio unitario dentro de tolerancia numérica.

Este comportamiento es compatible con el Fortran original. La restricción se
aplica al término constante o posición media del legislador; una trayectoria
temporal extrema puede producir posiciones de determinados períodos fuera del
círculo. La FAQ del paquete Fortran documenta explícitamente esta propiedad.

## Prueba Fortran/C++ pendiente

Desde la raíz del repositorio:

```bash
Rscript engine-modern/benchmarks/us-controlled/run_fortran_controlled.R \
  engine-experimental/benchmarks/us \
  engine-modern/benchmarks/us-controlled/common_start_float32.csv \
  engine-modern/benchmarks/us-controlled/fortran_out

python3 engine-modern/benchmarks/us-controlled/compare_controlled.py \
  --benchmark-dir=engine-experimental/benchmarks/us \
  --fortran-dir=engine-modern/benchmarks/us-controlled/fortran_out \
  --cpp-dir=engine-modern/benchmarks/us-controlled/cpp_out \
  --output-dir=engine-modern/benchmarks/us-controlled/comparison
```

Solo después de esa corrida será posible atribuir la diferencia residual a la
traducción, a la aritmética de precisión simple del Fortran, al criterio de
parada o al optimizador.
