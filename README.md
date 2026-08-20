# dwnominate-chile

Reproduction package for a verified, parallel C++ reimplementation of **DW-NOMINATE**, checked
component by component against the canonical 2004 Fortran (Poole–Rosenthal / McCarty), and applied
to the Chilean Chamber of Deputies.

Accompanies a paper submitted to the 45th International Conference of the Chilean Computer Science
Society (SCCC / JCC 2026). Roberto Nieves Tocornal, Pablo Antivil Morales, Julio Rojas-Mora.

---

## Contents

**Working engines are top level. Everything pre-fix is quarantined in `experimental/`.**

| path | what |
|---|---|
| `engine-faithful/` | **the paper's engine.** Our C++ port of `dwnom2004` at `quevotan-api@79031cf`, sources, build files, benchmarks and the exact compiler flags. Every number in the paper comes from this tree |
| `engine-modern/` | the complete NLopt variant (COBYLA, SLSQP and BOBYQA), authored by Julio Rojas-Mora. **A second engine and a cross-check, never the paper-faithful one.** Includes analytic gradients, deterministic telemetry, local scalar trust regions, unit/regression tests and the hybrid runner |
| `data/chile-static/` | **the Chilean roll calls used for the static tests**, legislaturas 353, 366 and 368: vote matrix (`votes_matrix_p1.csv`, the name the loader expects), W-NOMINATE seed and metadata each, with a README carrying the padding and screen caveats and our agreement numbers |
| `experimental/` | **two pre-fix trees, kept deliberately, not for results.** `f01e747-prefix-trunk/` is the known-bad build the validation suite is calibrated against; `e27ec21-prefix-projections-restored/` records a measured negative result plus unmerged patches. See `experimental/README.md` |

> **This is the `dev` branch.** It carries the complete `engine-modern` tree, which `main` does not.
> `engine-faithful/` is identical on both branches. Paper numbers come from `engine-faithful/` only;
> nothing here changes that.

## The modern engine on this branch

`engine-modern/` is the full tree rather than the partial `.cpp` subset that `main` ships: both
previously-missing headers (`optimizer_options.hpp`, `parameter_optimizer.hpp`), the SLSQP revision
with analytic gradients, adaptive tolerances, telemetry, the faithful-then-polish hybrid runner, and
a unit and regression test suite.

The modern engine now defaults to a local BOBYQA box for `w2` and `beta`. The box is re-centred at
every outer cycle and preserves the effective 16-step reach of Fortran's `WINT` and `SIGMAS` (`0.16`
and `1.6` respectively). This prevents an exact conditional scalar solve on the crude first-cycle
state from sending `beta` to its global lower bound and changing the basin of every later block.
`--scalar-search=global` retains the former behaviour for explicit experiments.

It builds and tests independently of `engine-faithful`:

```
cmake -S engine-modern -B build/engine-modern -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/engine-modern --parallel
ctest --test-dir build/engine-modern --output-on-failure
```

Add `-DDWNOMINATE_ENABLE_REGRESSION_TESTS=ON` to run all three committed Chile panels, a
byte-repeatability check, and the five-period US comparison against the committed Fortran
coordinates.

---

## Status, 2026-08-20

`engine-faithful/` now tracks `quevotan-api@79031cf`. Two fixes landed on top of the 2026-08-15
alignment fix that the previous sync of this repository shipped. **Neither changes a fit.** The
first changes only how a fit is read out, the second only where one unidentified class of
legislator starts.

**(1) The export frame (`eeb3e34`).** `getCoordinatesAtPeriod` evaluated each legislator's Legendre
polynomial on the *global* time grid, `t = -1 + 2*(period-1)/(numPeriods-1)`, while the optimizer and
the likelihood normalise time over that legislator's own *served* span, `xinc = 2/(kk-1)`. For anyone
not serving the full panel that reads their curve outside the range it was fitted on. The error is
zero at both panel endpoints, where the grids coincide, and maximal mid-panel. The canonical Fortran
counts only served periods (`dwnom2004.f:1941`), so `us_legout.dat` is already in local `t` and the
comparison had never been like-for-like. Two smaller defects rode along: all four Legendre terms were
summed unconditionally, leaking the cubic coefficient the optimizer never touches in linear or
quadratic runs, and a row was written for every `(legislator, period)` cell rather than for served
placements only.

| quantity, 23-period Chilean panel | before | after |
|---|---|---|
| exported rows | 7,774 | **2,855** (served placements) |
| log-likelihood | -98603.656973 | **-98603.656973** (unchanged) |
| `r1` vs the 2004 Fortran, single global Procrustes | 0.9927 | **0.9996** |
| `r2` vs the 2004 Fortran, single global Procrustes | 0.9190 | **0.9942** |
| mean 2D distance | 0.1154 | **0.0380** |

That is static-panel agreement (`r` 0.9891-0.9965, mean distance 0.033-0.044) reached on the dynamic
panel. On the static panels the fix is inert, as it must be: coordinates MD5-identical, likelihoods
unchanged at -1132.023505 / -6276.201346 / -13300.413955. **The fit was never wrong; the export was.**
`DWNOM_EXPORT_GLOBAL_T=1` reproduces the previous export exactly.

Also in that commit: vote codes now follow `dwnom2004.f:308-317` (1-3 yea, 4-6 nay, 0 and >6 missing)
at both sites that encoded the convention. Inert on `{1,6,9}` data, required for ICPSR and Voteview
coding, which the previous mapping silently turned into nays. `USE_REF_LAPACK` is now an explicit
CMake option rather than inferred from whether `liblapacke.a` happens to be on disk.

**(2) Seedless legislators start at the origin (`79031cf`).** A legislator W-NOMINATE declined to seed
was given a position derived from their rank in the roster, `x = uIdx/N - 0.5`, which for high IDs
lands near `x = +0.5`. That injects the arbitrary ordering of legislator IDs into the fit. The
Fortran's `us_legstart.dat` gives exactly these legislators `0.000 0.000`.

| static panel | seedless | `r2` before | `r2` after | dim-2 sign flips | ΔLL |
|---|---|---|---|---|---|
| leg 353 | 6 | 0.9965 | **0.9967** | 4 → 2 | -0.35 |
| leg 366 | 0 | — | **byte-identical** (control) | — | 0 |
| leg 368 | 3 | 0.9891 | **0.9913** | 2 → 2 | +3.89 |

**Read this one narrowly.** The three deputies concerned cast 24, 27 and 5 votes of 1023; they are
barely identified at all, and the fix removes an arbitrary input to their placement rather than making
them well determined. A minimum-participation screen for fidelity statistics is a separate question and
is not decided here. `DWNOM_SEED_FALLBACK_RAMP=1` restores the previous placement but, unlike the other
toggles in this codebase, **not bit for bit**: introducing the runtime branch is itself a numerical
perturbation under fast-math, measured at ~8.45 nats on the leg 368 panel. That is a codegen noise floor
worth knowing on its own, since the leg 368 likelihood gap against the Fortran is +10.65 nats.

**Data.** The static roll calls are now `votes_matrix_p1.csv`, which is the name `csv_loader` builds
(`votes_matrix_p<N>.csv`). Under the previous name the shipped engine could not load the shipped data.

---

## Status, 2026-08-19

**The repository was reorganised today.** Until now it held two engine trees at top level, `engine/`
and `engine-experimental/`, **both predating the 2026-08-15 alignment fix**, with nothing marking
which was current. Anyone building either reproduced numbers the paper no longer reports. They are
now under `experimental/`, named by commit, with a README saying what is wrong with them, and the
corrected engine sits at top level as `engine-faithful/`.

**What the fix was.** `prepareRollCallData` filled the coordinate and vote arrays in legislator
order, computed the projection order, and then reordered **only** the vote array, returning the two
misaligned. The one-dimensional branch compensated, so `JAN11PT` was unaffected; the two-dimensional
branch passed both straight to `CUTPLANE`, which therefore classified a shuffled pairing of
legislators to votes. The later optimizer receives coordinates and votes separately, which is why the
likelihood and the derivatives were correct and the defect stayed hidden behind them.

On the 23-period Chilean panel at the procedure's four iterations, corrected:

| quantity | before | after | reference |
|---|---|---|---|
| log-likelihood gap to the Fortran | 26,609 nats | **34.3 nats** | — |
| classification gap | 2.99 points | **0.02 points** | — |
| `CUTPLANE` error after `SEARCH`, first iteration | 25.91 % | **4.20 %** | 4.27 % |

On a static US Senate 90 panel the engine lands **0.611 nats** from the Fortran over 46,440 votes,
with `r1` 0.9997 and `r2` 0.9993, and the fitted weight `w2` is bit-identical to the reference on
three of four static panels.

## Known issues in this tree, stated rather than hidden

- **`engine-faithful/benchmarks/README.md` states two PASS criteria that a defective build passes.**
  The Tier 1 criterion ("dim-1 Pearson `r ≈ 0.992`") is satisfied by the *defective* build at 0.9915
  and marginally missed by the corrected one at 0.9907, so it points the wrong way. The Tier 2
  criterion holds on both sides of a 1.5-nat change and cannot fail. Corrected thresholds, derived
  from a measured good-versus-bad separation rather than copied from a passing run, are pending and
  land with a separate pull request. **Do not use the criteria as written.**
- `engine-faithful/EXPERIMENTS.md` records REQ-004 as a clean faithfulness fix. That reading was
  later corrected: the unit-ball projection it removed is real and lives one level up, in the grid
  search that calls the likelihood evaluator rather than in the evaluator itself. The projections are
  restored in this tree.
- `engine-faithful` filters missing-vote rows before `CUTPLANE`. The canonical Fortran passes all
  `NPC` rows, maps missing votes to code 9 internally, and excludes them only from classification
  counts. `engine-modern` preserves the latter contract. The distinction is documented because it can
  change `SEARCH` geometry without changing the likelihood data.
- The engine is compiled with fast-math relaxations, and its linear-algebra path is now an explicit
  build option, `USE_REF_LAPACK` (default ON), rather than inferred from a file test. It is still
  conditional: the LAPACKE route is taken only when the option is ON **and**
  `external/lapack-3.12.1/build/lib/liblapacke.a` is actually present, otherwise the cutting-plane SVD
  falls back to Eigen's Jacobi implementation without complaint. **The two paths converge to different
  optima** — the CMakeLists records this as the only rung that moves a reported parameter. All reported
  fits use the LAPACKE path, so read the CMake status line rather than assuming it.

## Not here yet

- `reference-fortran/`, the canonical 2004 Fortran. Redistributable under MIT from
  `wmay/dwnominate` with attribution to William May, Keith T. Poole and Nolan McCarty.
- `reproduce/`, the extraction scripts and per-figure receipts.
- A licence file. Proposed: MIT for the code, CC BY 4.0 for data and reproduction scripts. Not yet
  agreed by all three authors.

## Building

**Two dependencies are not vendored here and you must supply them.** Both are gitignored in the
upstream module as well, so this is a property of the sources rather than of this export.

- **Eigen 3.4.0**, unpacked so that the headers sit at `engine-faithful/Eigen/` — that exact path is
  hard-coded as an include directory in `CMakeLists.txt`. Without it the configure step fails.
- **Reference netlib LAPACK 3.12.1**, only if you want the published numbers. `USE_REF_LAPACK`
  defaults ON but is *also* gated on `engine-faithful/external/lapack-3.12.1/build/lib/liblapacke.a`
  existing; if it does not, the build quietly falls back to Eigen's own Jacobi SVD, **which converges
  to a different optimum**. Build it with:

```
cd engine-faithful/external
curl -L https://github.com/Reference-LAPACK/lapack/archive/refs/tags/v3.12.1.tar.gz | tar xz
cd lapack-3.12.1 && mkdir build && cd build
cmake -G "MinGW Makefiles" -DBUILD_SHARED_LIBS=OFF -DLAPACKE=ON -DCBLAS=OFF       -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release ..
cmake --build . -j
```

Then:

```
cd engine-faithful
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

Check the configure output for `Reference LAPACK found at ...` before trusting a fit. If instead you
see `USE_REF_LAPACK=OFF` or no LAPACK line at all, you are on the Jacobi path and your numbers will
not match the ones reported above.

See `engine-faithful/CMakeLists.txt` for the flags and `engine-faithful/SEEDS.md` for the seeding
contract, which matters: the frame the seed supplies is the frame the fit keeps.
