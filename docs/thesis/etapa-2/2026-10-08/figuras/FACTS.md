# FACTS: cada elemento dibujado y su evidencia

Juego de exposición, construido 2026-10-08. Mismos hechos que `../diagramas-corregidos/`
(juego de auditoría), con etiquetas funcionales. Cada elemento de cada figura se verificó contra
el código local; "intención" marca actores y conceptos del protocolo que no tienen una línea de
código que los defina.

**Actualizado 2026-10-08 tras el red team** (`../2026-10-08-redteam-figuras.md`): cada fila que
describe un elemento cambiado se reescribió en su lugar y se reverificó contra el código (mismo
commit `ad945a91`; `quevotan-db` en `3cb203e3`). Las filas marcadas «RT» son nuevas o cambiaron.
El índice hallazgo → cambio está en `README.md`, sección «Correcciones del red team». Las filas «RT2» vienen de la segunda pasada (`../2026-10-08-redteam-figuras-2.md`, N-2 a N-15),
también reverificadas contra el código. La edición de regeneración separa F3 (correspondencia), el cuadro T5 (mecanismos) y las
dependencias C++ en anexo. Las filas históricas no vigentes se preservan en `historical/`.

Abreviaturas de ruta: `F` = `dwnominate-chile/engines/faithful`, `M` = `engines/modern`,
`FT` = `engines/fortran`, `DC` = `dwnominate-chile/reproduce`, `Q` = `quevotan-db`,
`TH` = `thesis-quevotan/thesis/draft`. Los 64 archivos citados coinciden con los hashes de
`../diagramas-corregidos/source-provenance.json` (comprobado 2026-10-08; commit local del motor
`ad945a91aafaba12203dbd3d62529020c9d897ee`). Los números de línea son de esa instantánea.

## F1 Contexto y alcance

| elemento | evidencia |
|---|---|
| Analista, Verificador (actores) | intención; las funciones que ejercen son RF01 a RF12, `TH/cap3.tex:150-253` |
| Fuentes de paneles («actor») | intención; contrato de archivos que el instrumento lee, `F/include/csv_loader.hpp:8-17`; Cámara de Diputados vía QueVotan `TH/cap1.tex:13`; VoteView `TH/cap1.tex:44-45` |
| «entrega panel» | `Q/reproduce/R/dwnom.R:271` (`read_votes(input_dir)`), `F/src/csv_loader.cpp:221` |
| Servicio de semillas: W-NOMINATE en R | `dwnom.R:158` (`dwnom_seed`), `dwnom.R:309` (ajusta W-NOMINATE sobre `mats[[1]]`) |
| «envía votos» / «devuelve semillas» | `dwnom.R:309-312` (votos a `dwnom_seed`, resultado escrito como `wnominate_coordinates.csv`); negativa a sembrar en proceso paneles multiperiodo `dwnom.R:293` |
| Instrumento DW-NOMINATE: motores fiel y moderno (C++); preparación de entradas y verificación | `dwnom.R:52-66` (`ENGINES`: fortran, faithful, nlopt); `F/src/main_cli.cpp:524-581`; `M/src/main_cli.cpp` |
| RT «portal R: entrada común a los motores y a la referencia; sella cada corrida» (F1-2) | una función para los tres brazos `dwnom.R:246-252` (`engine = c("fortran", "faithful", "nlopt")`), binarios `:52-66`; sello `run_stamp` `:192-235` (binario, md5, `svd_backend`, `omp_num_threads`, semilla y su md5, ciclos, banderas) y `:420-436` (`faithful_mode`, linaje, `RUN-STAMP.csv`). «Común» y no «único»: las CLI de los motores se pueden invocar directamente (`F/src/main_cli.cpp`, `M/src/main_cli.cpp`); el portal es la entrada del protocolo y rechaza banderas que alteren el contrato `dwnom.R:338-340` |
| RT «declara panel, semillas y motor» (F1-1) | firma de `dwnom_run`, `dwnom.R:246-252` (`input_dir`, `engine`, `model`, `niter`, `start`, `seed_per_period`, `faithful_mode`) |
| RT2 leyenda: «el motor se declara al portal R, que también recibe el linaje del motor fiel (por omisión, wmay)» (N-2c) | quien llama elige `faithful_mode`; el portal lo aplica: `dwnom.R:252` (`faithful_mode = c("wmay", "2004-safeguard")`), `:254` (`match.arg`: sin argumento, el primero, `"wmay"`), `:362-365` (`"wmay"` añade `--wmay-replication`) |
| RT2 «sella cada corrida aceptada» (cuerpo del componente y pie; N-2a) | el sello se escribe solo después de aceptar: `dwnom.R:380-381` y `:387-391` (`stop` antes), `RUN-STAMP.csv` en `:436` |
| RT clave de notación sin número de cláusula UML | el «§20.1.4» no se verificó contra el PDF de OMG (red team A2-4, [I]); se retiró |
| RT2 «devuelve coordenadas y parámetros» (N-2b) | `dwnom.R:439-442` (devuelve `coordinates`, `bill_parameters`, `scalars`); exportación `F/src/main_cli.cpp:613-630` |
| «solicita / devuelve comparación» | intención del verificador; mecanismos en `DC/map_agreement.py:102-111` y `FT/stage_terminal_state.py:85-108` |
| Referencia wmay («actor», Fortran, evaluador común) | `FT/DW-NOMINATE-wmay.f:65-70` (subrutina `dwnom`); envoltorio `FT/standalone_main.f90:8-9, 233`; binario `fortran-canonical/dwnominate_fortran` en `dwnom.R:54-56` |
| «a wmay: panel, semillas o estado» | `dwnom.R:344-359` (INPUT escenificado, semilla por legislador, `args = c(staged_input, out_dir, niter, model)`); estado terminal `FT/standalone_main.f90:212` |
| «de wmay: coordenadas o LL» | `FT/standalone_main.f90:240-247` (`PLOG` tras `dwnom`; `XDATAOUT`, `ZMIDOUT`, `DYNOUT`) |
| Límite lógico (preparación, motores, verificación) | intención, siguiendo `../diagramas-corregidos/D1`; la plataforma QueVotan queda fuera (`TH/cap1.tex:222`) |

## F2 Objetivos de los usuarios

| elemento | evidencia |
|---|---|
| RT2 Declarar panel y semillas (RF02) (N-12) | `TH/cap3.tex:160-167` (RF02, valores iniciales declarados); `dwnom.R:246-252, 320-326` (validación de la semilla) |
| RT2 Estimar posiciones (RF01, RF03 a RF07), abstracto, nombre en cursiva (F2-2, N-12) | `TH/cap3.tex:150-158` (RF01, ingesta y validación de entradas: ocurre al cargar, dentro de la estimación, `F/src/csv_loader.cpp:221-271`, como dice el pie), `:169-203`; `dwnom.R:252` (`model = 0..3`, `niter`); cursiva: notación de clasificador abstracto |
| RT «con motor fiel o moderno (RF05, RF06)» (F2-2) | `TH/cap3.tex:183` (RF05 motor fiel), `:191` (RF06 motor moderno); `dwnom.R:246` (`engine`) |
| Estimar estático / dinámico (especialización) | `TH/cap3.tex:169-181`; misma maquinaria con `model` y `periods`, `dwnom.R:252, 272-276` |
| RT Verificar y comparar (RF08, RF09) «contra la referencia wmay» (F2-3) | `TH/cap3.tex:205-224`; `DC/map_agreement.py:102-111`; `FT/standalone_main.f90:198-204, 240-241`; referencia wmay `dwnom.R:54-56` |
| RT Validar con el caso chileno (RF10 a RF12), flujo de investigación; elipse dentro del sujeto (D01) | `TH/cap3.tex:226-253`; `Q/reproduce/scripts/ried2022/refit_one.py:118-176` (bootstrap: semillas, armonización, motor). El sujeto lógico de investigación incluye estimación, validación y comparación; todos los casos quedan dentro (decisión de alcance, no una nueva función CLI). La reformulación del objetivo chileno sigue pendiente |
| «include» Validar a Estimar posiciones (abstracto) | `refit_one.py:118` (`--model` por defecto 1, cualquier modelo admitido) y `:170-176` (invoca el motor con `--model`) |
| RF01 dentro de la estimación | `F/src/csv_loader.cpp:221-271` (lista unificada, filtra fantasmas); `dwnom.R:271-276` |
| Roles ejercidos por la misma persona | intención |

## F3 Correspondencia de responsabilidades

Todas las líneas horizontales significan correspondencia conceptual, no dependencia UML.
La asignación de responsabilidades es interpretación del código identificado abajo.

| Elemento | Evidencia |
|---|---|
| Entrada/ejecución original 2004 | `FT/DW-NOMINATE-2004.FOR:11-45,149,401,961-962` |
| Entrada/ejecución wmay y fiel | `FT/DW-NOMINATE-wmay.f:65-73,228`; `FT/standalone_main.f90:233`; `F/src/main_cli.cpp:524-581,613-630` |
| Configuración/estado: COMMON en 2004, módulos wmay, configuración explícita/estado fiel | `2004.FOR:23-32`; `wmay.f:13-63,71-73`; `F/include/dwnominate.hpp:35-76,477-519` |
| Búsquedas WINT, SIGMAS, RCINT2, XINT y GRID | `wmay.f:616,701,1404,2447`; `2004.FOR:1808,2067-2068`; `F/src/optimize_legislators.cpp:262-275`; `F/src/main_cli.cpp:566-567` |
| Geometría: CUTPLANE/SEARCH/JAN11PT; LSVRR original y DGESDD wmay | `2004.FOR:1160,4244,4409,4623,4639,5088`; `wmay.f:785,2940,3104,3319,3333`; `F/src/cutting_plane.cpp:285-337` |
| Verosimilitud y derivadas | `wmay.f:970,1139,2327`; `F/include/likelihood.hpp`; `rollcall_derivatives.hpp:6-8`; `legislator_derivatives.hpp:1` |
| Soporte: RSORT, REGA, normal tabulada | `wmay.f:32-63,2266,2806`; `2004.FOR:243-259`; `F/include/sort_utils.hpp`, `simple_ols.hpp`, `normal_cdf.hpp` |
| Grafo de inclusiones, cuadro independiente de anexo | `F/include/dwnominate.hpp:14-23`; `grid_optimizer.hpp:12-13`; `rollcall_derivatives.hpp:11`; `legislator_derivatives.hpp:6`; `rollcall_optimizer.hpp:12`; `optimize_legislators.hpp:10-12`; `likelihood.hpp:4`; `cutting_plane.hpp:10`; `cutting_point.hpp:9` |

El estado sigue concentrado; ni correspondencia ni inclusiones demuestran mantenibilidad.
La salvaguarda GRID del fiel no vuelve idénticos original 2004, wmay y C++.

## F4 Ciclo de estimación

| elemento | evidencia |
|---|---|
| Cargar panel y semillas; marcar votaciones válidas; ciclo := 1 | `F/src/main_cli.cpp:524-541`; validez por margen `include/dwnominate.hpp:684` con umbral 0,025 `:43, 68`; `firstIteration = 1` `src/main_cli.cpp:556` |
| Ajustar los parámetros globales (WINT, SIGMAS) | `src/dwnominate.cpp:449-461` (solo si `ns >= 2`), `:476`; `wmay.f:235, 242`; `2004.FOR:405-414` |
| RT Actualizar las posiciones de las votaciones: «corte: CUTPLANE (2D) o JAN11PT (1D); búsqueda: RCINT2» (F4-1) | la elección es por dimensión, no por votación: `wmay.f:361` (`IF(NS.EQ.1)` JAN11PT), `:406` (`IF(NS.GT.1)` CUTPLANE), RCINT2 `:458`; `src/dwnominate.cpp:490`; `include/dwnominate.hpp:633` (`applyJan11pt`), `:646` (`applyCutplane`) |
| Evaluar la verosimilitud (PLOG) | `src/dwnominate.cpp:496` y `:516`; `wmay.f:485, 562` |
| Actualizar las posiciones de los legisladores (XINT; tiempo servido) | `src/dwnominate.cpp:510`, `:1523` (`optimizeLegislator`), `:1814-1836` (tiempo local); `wmay.f:516` |
| ¿ciclo ≤ T?: número fijo de ciclos, sin convergencia | `src/dwnominate.cpp:446` (`for ihappy = first..last`, sin `break`); `lastIteration = iterations` `src/main_cli.cpp:557`; `wmay.f:228`; `2004.FOR:401` |
| Exportar parámetros terminales y resumen fiel mixto (FR-03) | `src/main_cli.cpp:613-630`; `src/dwnominate.cpp:550,553-554` separa estadísticas finales de clasificación/votos de fase previa; I2 pendiente |
| Perfil: dos dimensiones, cuatro ciclos | `dwnom.R:252` (`niter = 4`), `README` del juego de auditoría; intención del perfil mostrado |
| Parámetros terminales, resumen mixto (FR-03) | F4/A2 distinguen el estado de los parámetros del resumen de clasificación; F7 puntúa parámetros terminales y no valida la clasificación del resumen |
| RT disposición compacta (182 → 170 mm) | solo geometría: acciones de 36 pt, paso de 46 pt; ningún hecho cambia |

## T5 Mecanismos de la intervención moderna

| Elemento | Evidencia |
|---|---|
| Peso: rejilla WINT frente a BOBYQA local | `F/include/grid_optimizer.hpp:150`; `M/src/parameter_optimizer.cpp:76-81,100`; `M/include/parameter_optimizer.hpp:39-42,113` |
| Beta: rejilla SIGMAS frente a BOBYQA local | `F/include/grid_optimizer.hpp`; `M/src/parameter_optimizer.cpp:100`; `M/include/parameter_optimizer.hpp:100` |
| Votación: RCINT2 por término frente a COBYLA de bloque | `wmay.f:2447,2469`; `M/src/rollcall_optimizer.cpp:154-158,241-242`; norma sobre punto medio `:109-135`; separaciones libres |
| Legislador: XINT por término frente a COBYLA de bloque | `wmay.f:1404,1535`; `M/src/optimize_legislators.cpp:247-251,367-368`; norma sobre término constante `:197-223`; términos temporales libres |
| Activo: replicación, precisión estricta, local y COBYLA | `M/src/main_cli.cpp:379-390`; `Q/reproduce/R/dwnom.R:362-364` |
| Opciones fuera del perfil: global, SLSQP/híbrido | `M/include/optimizer_options.hpp:7-18`; `M/src/main_cli.cpp:1118`; `parameter_optimizer.hpp` |
| Retirar cotas globales preserva intervalo local | `M/src/dwnominate.cpp:567-576,661-670`; `parameter_optimizer.cpp:76-89` |

Controles de panel, semillas, ciclos, evaluador y tiempos pertenecen a los protocolos; no son
relaciones estructurales de T5. No se afirma idéntico recorrido de optimización ni resultados.

## F6 Datos y tiempo servido

| elemento | evidencia |
|---|---|
| Panel: periodos y votaciones | `F/include/csv_loader.hpp:8-17` (`votes_matrix_pN.csv` por periodo), `:44-54` (`PeriodData`) |
| Legislador (identificador único) | `csv_loader.hpp:31-41`; presencia por periodo `dwnominate.hpp:105-128` |
| Periodo (índice en el panel) | `csv_loader.hpp:47` (`periodIndex`); `dwnominate.hpp:83-99` (`CongressInfo`) |
| Fila servida: legislador en un periodo; /tiempo local; /coordenadas | `src/dwnominate.cpp:1780-1814` (`servedPeriods`, `servedIdx`), `:1821` (`xinc = 2/(kk-1)`), `:1836` (`xtime`); `dwnominate.hpp:344-367` |
| Celda de voto: fila y votación; sí, no o ausente | `csv_loader.hpp:52` (1, 0, -1); `dwnominate.hpp:480` (`votes_`, RCVOTE1/RCVOTE9) |
| RT2 Votación: periodo y columna; «válida: margen de la minoría ≥ 2,5 %» (N-13c) | margen = min(sí, no) / (sí + no): motor fiel `src/dwnominate.cpp:1660-1669` (`minority / total >= marginThreshold`), umbral `dwnominate.hpp:43, 68`; wmay `wmay.f:322-332` (`KRCMIN=MIN0(KYES,KNO)`, `XMARG=KRCMIN/KRCTOT`, `.GE..025`); `csv_loader.hpp:8-11` |
| Semilla por legislador (0..1) | `csv_loader.hpp:91-106` (`WNominateCoords`); `src/csv_loader.cpp:285-326` (mapa por `legislatorId`); `dwnom.R:320-323` |
| Semilla por fila (0..1, opcional) | `csv_loader.hpp:118-128` (sobreescritura por (legislador, periodo), opcional, con reserva (0,0)); `src/csv_loader.cpp:339-369`; la referencia wmay solo admite semilla por legislador `dwnom.R:303` |
| Trayectoria: coeficientes por legislador, evaluada en los periodos servidos | `dwnominate.hpp:250-252, 257-261, 290-385`; orden efectivo `:406-425`; grado limitado por periodos servidos `src/dwnominate.cpp:1500-1511` |
| RT asociación Legislador (1) a Trayectoria (0..1) (F6-2) | `include/dwnominate.hpp:512` (`temporalCoefficients_` por `uniqueId`: una por legislador); `src/dwnominate.cpp:1456-1459` (sin periodo servido en el rango, se omite: de ahí 0..1), `:1463-1465` (una entrada por legislador válido) |
| «Derive»: coordenadas de la fila desde trayectoria y tiempo local | `dwnominate.hpp:369-384` |
| Ejemplo: periodos 2 y 4 servidos, t = −1 y +1; periodo 3 sin fila ni exportación | `dwnominate.hpp:360-363` (kk = 2, t = −1 + idx·2); `:356-359` (periodo no servido devuelve vector vacío); `src/main_cli.cpp:249` (solo se escribe si hay coordenadas) |
| RT «modelo efectivo: constante; el término lineal exige al menos 5 periodos servidos (cuadrático 6, cúbico 7); ambas filas reciben las mismas coordenadas» (F6-1) | motor fiel `src/dwnominate.cpp:1500-1511` (`congressCount >= 5/6/7` junto con `temporalModel >= 1/2/3`); wmay, XINT `wmay.f:1723` (`NNMODEL.GE.1.AND.NEPCONG.GE.5`), `:1872` (`.GE.2`, `.GE.6`), `:2020` (`.GE.3`, `.GE.7`); arranque OLS con la misma regla `:1480-1501`. Con modelo constante la coordenada es el término constante en todo periodo servido. (El red team citó `wmay.f:536-548`, que es el almacenamiento de varianzas en `dwnom`, no la elección del grado) |
| RT columnas desplazadas: separación de 28 pt entre Fila servida y Semilla por fila | solo geometría: las multiplicidades 1 y 0..1 ya no se superponen en horizontal |
| Sin validación uno a uno (red team D10 a D12) | `src/csv_loader.cpp:144-156` (padrón: la última fila con el mismo id prevalece), `:365-369` (semilla por fila, igual), `:836-866` (parámetros de referencia anexados sin unicidad) |

## F7 Proceso de verificación

| elemento | evidencia |
|---|---|
| RT pie: «dos de los tres niveles de RF08»; el nivel de componente va al cuadro de niveles (F7-1) | `TH/cap3.tex:205` («RF08 & Verificación en tres niveles»); nivel de componente: modos que fijan bloques en el fiel `F/include/dwnominate.hpp:44-53`, respetados en `F/src/dwnominate.cpp:453, 468, 482, 502` pero apagados por su CLI `F/src/main_cli.cpp:562-564`; en el moderno, banderas `--evaluate-only` y `--fix-*` `M/src/main_cli.cpp:156-159, 232-246`; ocho pruebas en `M/tests/` |
| Corridas controladas: mismo panel, semillas y horizonte | `dwnom.R:246-252`; un hilo para fortran y fiel `:263`; mismo perfil de semilla por legislador en ambos brazos `:303` |
| RT «la comparación controlada usa la semilla por legislador, único contrato que acepta wmay» (F6-3, en el pie y la leyenda de F7) | `dwnom.R:303-304` (`stop("the wmay standalone harness cannot consume seed_per_period ...")`) |
| (a) Preparar el estado (`stage_terminal_state.py`) | `FT/stage_terminal_state.py:85-108` (resumen, coordenadas, parámetros de votaciones), `:117` (manifiesto) |
| (a) Evaluar con la referencia wmay sin ajustar: cero ciclos | `FT/standalone_main.f90:198-204` (`NOMSTARTIN(5) = 1`, `NOMSTARTIN(6) = 0`), `:212` (carga el estado), `:233` (`dwnom`), `:240-241` (`PLOG`) |
| (a) LL del estado C++ bajo el evaluador de wmay; diferencia con la LL de la corrida wmay | `standalone_main.f90:241` (`native_plog`); comparación como protocolo: intención (RF08, RF09 `TH/cap3.tex:205-224`) |
| RT «LL de su resumen: summary.csv» (F7-3) | la corrida wmay ajustada escribe su LL final en `summary.csv`: `FT/standalone_main.f90:741` (`log_likelihood = sum(xbiglog(:, 2))`, del PLOG final de `dwnom`), `:771-774`; el portal lo lee como resumen del brazo fortran `dwnom.R:52-56` (`summary = "summary.csv"`) |
| RT (b) Comparar coordenadas: emparejar por (legislador, periodo); centrar y alinear sin reescalar; alineación ortogonal (F7-2) | `DC/map_agreement.py:124` (`merge` por `legislator_id`, `period`), `:90-98` (`procrustes_noscale`: «Rotate/reflect ... Orthogonal only, no scaling»), es decir rotación o reflexión |
| RT clave: «región rotulada (a), (b), partición de actividad; la pestaña es una marca propia» (F7-4) | notación; sin hecho de código |
| (b) Medidas: n, r1, r2, amplitud, distancia media | `DC/map_agreement.py:102-111` |
| Cobertura por lado, claves únicas y marco | `DC/map_agreement.py:75-87` descarta no finitos, `:124` hace merge sin validar unicidad y `:125` da un conteo agregado; `:133-136` selecciona marco. Cobertura completa y claves únicas son requisitos pendientes de I5, no controles ya implementados |
| El referente de corridas es wmay, no el original 2004 | `../../../START-HERE.md` (identidades de motor); `dwnom.R:54-56` |

## A1 Clases y propiedad del estado

| elemento | evidencia |
|---|---|
| `CSVLoader` (+ `loadInput`) | `F/include/csv_loader.hpp:133-224`; `loadInput` `:149, 162` |
| «Create» `DWNominateInput` | `src/main_cli.cpp:541`; estructura `dwnominate.hpp:170-212` (`legislatorCoords` 177, `rollCallMidpoints` 181, `rollCallSpreads` 185, `votes` 188, `congressMetadata` 201) |
| `DWNominateConfig` (atributos mostrados) | `dwnominate.hpp:37, 38, 41, 42, 43, 59` |
| RT `fixGlobalParams, fixRollCalls, fixLegislators (validación)`; la CLI construye la configuración y los deja apagados (A1-2) | `dwnominate.hpp:46-53`, por defecto `false` `:70-72`; respetados en `src/dwnominate.cpp:453, 468, 482, 502`; la CLI llena la configuración `src/main_cli.cpp:553-567` y fija los tres en `false` `:562-564`; ningún otro llamador del árbol fiel los activa. Solo el moderno los expone como banderas (`M/src/main_cli.cpp:156-159`) |
| RT pie: `use2004GridSafeguard` activa la salvaguarda GRID de 2004, encendida por defecto, `--wmay-replication` la apaga (F3-3) | `dwnominate.hpp:55-59, 73`; `src/main_cli.cpp:567` |
| `DWNominate`: atributos | `config_` 477, `votes_` 480, `weights_` 490, `legislatorCoords_` 491, `rollCallMidpoints_` 492, `rollCallSpreads_` 493, `temporalCoefficients_` 512, `servedPeriodsByLeg_` 516 |
| `DWNominate`: operaciones por fase | constructor 442, `run` 449, `executeWeightPhase` 547, `executeBetaPhase` 552, `executeRollCallPhase` 559, `computeLogLikelihood` 669, `executeLegislatorPhase` 564 |
| RT «use» de la entrada: el constructor copia lo que necesita y no retiene el objeto (A1-1) | constructor `dwnominate.hpp:442`; `src/dwnominate.cpp:190-193` (`votes_(input.votes)`), `:217` (`loadRollCalls(input)`: puntos medios y dispersiones), `:220` (`loadLegislators(input)`: coordenadas); ningún miembro `input_` en `dwnominate.hpp:477-519` |
| RT «inicialización» en `loadInput`: semillas, beta y W2 (X-2) | `src/main_cli.cpp:528-537` (`InitializationConfig`: `beta`, `w2`, semilla W-NOMINATE, semilla por periodo); `csv_loader.hpp:111-128, 162` |
| Composición `config_` (1) | `dwnominate.hpp:477` |
| Composición `congressInfo_` (*) | `dwnominate.hpp:481`; `CongressInfo` `:83-99` |
| Composición `legislatorPresence_` (*) | `dwnominate.hpp:486`; `LegislatorPresence` `:105-128` |
| RT2 nombres de rol en el extremo de la parte, multiplicidad sobre la línea y rol bajo ella; «inicialización» sin comillas angulares; W2 expandido (N-11, N-13b) | notación; los nombres son los miembros `config_` `:477`, `congressInfo_` `:481`, `legislatorPresence_` `:486`; «inicialización»: `InitializationConfig` (`src/main_cli.cpp:528-537`) |
| «Utility» Búsquedas: `optimizeWeight2`, `optimizeBeta`, `optimizeRollCall`, `optimizeLegislator` | `grid_optimizer.hpp:150, 138`; `rollcall_optimizer.hpp:107, 118`; `optimize_legislators.hpp:65`; llamadas en `src/dwnominate.cpp:699, 942, 1125, 1523` |
| «Create» `DWNominateResult` | `src/dwnominate.cpp:432-434` (`run` construye `result`), `:605`; estructura `dwnominate.hpp:218-426` (`finalLogLikelihood` 239, `temporalCoefficients` 252, `servedPeriodsByLegislator` 261, `getCoordinatesAtPeriod` 290) |

## A2 Secuencia de una estimación

| elemento | evidencia |
|---|---|
| Portal R ejecuta la CLI (`system2`) | `dwnom.R:362-377` (argumentos `--input-dir`, `--model`, `--iterations`, `--periods`, `--wnominate`, `--seed-per-period`, `--output-dir`, `--wmay-replication`); `system2` `:377` |
| RT Llamada válida con argumentos nombrados, con `faithful_mode = "wmay"` (A2-2) | firma `dwnom.R:246-252` (`engines`, `runs_dir`, `panel` son obligatorios; `model`, `niter`, `start` nombrados); `faithful_mode = "wmay"` añade `--wmay-replication` `:362-365` |
| CLI carga y valida (`loadInput`) | `src/main_cli.cpp:524-541` |
| RT2 guardas «[loadInput y run() sin excepción]» / «[excepción en loadInput o run()]» (A2-1, N-9a) | solo esas dos llamadas están en `try`: `src/main_cli.cpp:539-547`, `:579-587`; fuera de todo `try`: el constructor `:576` y las exportaciones `:613-630`, funciones `void` que ante un error escriben en `stderr` y retornan (`:228-238`), así que la CLI sale con 0 y es el portal el que rechaza por archivos faltantes (`dwnom.R:387-391`) |
| RT2 estado de la CLI «termina: código 1, sin salidas» en lugar de una respuesta dentro del `alt` (N-9b) | la llamada síncrona del portal (`system2`, `dwnom.R:377`) recibe una sola respuesta, el código de salida, después del `alt`; con `return 1` (`:546, :586`) no se ha escrito ningún archivo `cpp_*.csv` (las exportaciones vienen después, `:613-630`) |
| RT2 nota OpenMP: búsqueda de los parámetros globales (su verosimilitud) y fases de votaciones y de legisladores (N-10) | tres regiones paralelas: la verosimilitud dentro de la búsqueda de W2 y beta (`src/grid_optimizer.cpp:39` llama a `computeLogLikelihoodParallel`, `src/likelihood.cpp:277`, `#pragma omp` en `:330, 338`), la fase de votaciones (`src/dwnominate.cpp:762`) y la de legisladores (`:1478`). La evaluación del ciclo es serial (`DWNominate::computeLogLikelihood`, `:1613-1628`, llama a `::computeLogLikelihood`, `src/likelihood.cpp:115`, sin `pragma`) |
| RT alt [sin excepción] / [excepción]: ambas fallas terminan con código 1 (A2-1) | `src/main_cli.cpp:539-547` (`loadInput` en `try`, `catch`, `return 1`) y `:579-587` (`run()` en `try`, `catch`, `return 1`). No dibujado: el constructor `:576` está fuera de todo `try`. El aborto por caída de la LL entre ciclos es del motor moderno (`M/src/dwnominate.cpp:385-393`), no de este; va al cuadro de errores. Las guardas se colocan junto a la línea de vida del primer evento del operando |
| «Create» `DWNominate(configuración, entrada)` | `src/main_cli.cpp:576` |
| D04 una llamada `run()` y nota documental a F4, sin `loop/ref` | `F/src/main_cli.cpp:581`; `F/src/dwnominate.cpp:446-520` contiene los ciclos internos; UML 2.5.1 §17.7: InteractionUse referencia una Interaction, no una Activity |
| Parámetros terminales y resumen fiel mixto (FR-03) | `F/src/dwnominate.cpp:550,553-554`: estadísticas de la pasada final separadas de clasificación/votos de la fase de votaciones; `F/src/main_cli.cpp:396-401,613-630`. I2 pendiente |
| RT destrucción (X) de `:CSVLoader`, `:DWNominate` y `:CLI` | `loader` y `nominate` son locales de `main` (`src/main_cli.cpp:524, 576`) y se destruyen al salir de `main` (`return 1` en `:546, 586`; `return 0` en `:634`); el proceso de la CLI termina y el portal recibe el código. Con esto el fragmento de aceptación y la nota cubren solo la línea de vida del portal |
| RT clave sin números de cláusula UML (A2-4) | «§17.6» y «§17.7» no se verificaron contra el PDF de OMG; se retiraron |
| alt [salida 0; CSV requeridos legibles] (FR-05) | `dwnom.R:380-391` verifica salida cero y archivos leídos no NULL; no exige filas, unicidad, esquema ni cobertura completa. `:416` escribe `DROPPED.csv`, `:436` escribe `RUN-STAMP.csv`, `:439-442` devuelve el estado. El caso de cabecera sin filas en 1D sigue abierto en I2 |
| Paralelismo disponible; corrida comparativa a un hilo | `src/dwnominate.cpp:762` y `:1478` (`#pragma omp parallel for`), y `src/likelihood.cpp:330, 338` dentro de la búsqueda de los parámetros globales (ver fila RT2 anterior); `dwnom.R:334` (`OMP_NUM_THREADS`), `:263` |
| Inserción concurrente sin sincronización (P-01) | `src/dwnominate.cpp:1814` dentro de `reconstructLegislatorCoords`, llamada desde `processLegislator` (`:1485`, en el bucle paralelo); sin `omp critical` ni mutex en el archivo. P-01: intención (decisión de diseño pendiente, red team D08) |

## Correcciones del informe verificadas en esta pasada

R02: `Q/reproduce/scripts/ried2022/dwnominate_parametric_bootstrap.py:372-420` fija la máscara
observada de redibujo; `refit_one.py:144-178` regenera semillas por periodo y ejecuta el motor;
`M/src/dwnominate.cpp:172-204` recalcula `validRollCalls_` por minoría en cada panel simulado.
La misma regla/umbral no promete el mismo conjunto retenido.

R03: counts son diagnósticos. Se conserva hash de matrices/orden/semillas/configuración en los
manifiestos de linaje, junto a RUN-STAMP para binario, argumentos y semillas; no se atribuye al
sello hashes de matriz que no contiene. Evidencia en `../evidence/lineage/` y `dwnom.R:192-235`.

R01: original 2004 vinculado al SHA-256 `276e3cb5...`, ejecutable reconstruido `08dc4e04...` y
comandos en `../evidence/lineage/builds/`. Reproducción wmay, aceptación original y rendimiento
son protocolos distintos del informe. No se realizó otro replay ni se alteró el papel.

## Estado local y publicación

El portal local SHA-256 `170d8a46...` coincide con `source-provenance.json` del 7 de octubre,
pero está modificado respecto de `quevotan-db` HEAD `3cb203e3`. Los números de línea citan
esa copia exacta incluida en `../evidence/research/reproduce/R/dwnom.R`, no el blob remoto.
Backlog I1--I7 y ETAPA-3 se conservan como fuentes locales propuestas; I6 requiere la
ratificación del referente original 2004, ya explícito en el informe.
