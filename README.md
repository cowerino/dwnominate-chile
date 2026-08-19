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
| `engine-faithful/` | **the paper's engine.** Our C++ port of `dwnom2004` at `quevotan-api@77bfeea`, sources, build files, benchmarks and the exact compiler flags. Every number in the paper comes from this tree |
| `engine-modern/` | the NLopt variant (COBYLA / BOBYQA), authored by Julio Rojas-Mora. **A second engine and a cross-check, never the faithful one.** Partial: the `.cpp` files and build as of 2026-08-13. Two headers (`optimizer_options.hpp`, `parameter_optimizer.hpp`) and the newer SLSQP revision are not here yet |
| `experimental/` | **two pre-fix trees, kept deliberately, not for results.** `f01e747-prefix-trunk/` is the known-bad build the validation suite is calibrated against; `e27ec21-prefix-projections-restored/` records a measured negative result plus unmerged patches. See `experimental/README.md` |

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
- The engine is compiled with fast-math relaxations and selects its linear-algebra path implicitly at
  build time. When a LAPACKE route is present the cutting-plane SVD dispatches to `LAPACKE_dgesvd`,
  otherwise to Eigen's Jacobi implementation, and **the two paths converge to different optima**. All
  reported fits use the LAPACKE path.

## Not here yet

- The newer `engine-modern` revision (SLSQP with analytic gradients, adaptive tolerances, telemetry,
  and a faithful-then-polish hybrid). Its authoritative copy is Julio's.
- `reference-fortran/`, the canonical 2004 Fortran. Redistributable under MIT from
  `wmay/dwnominate` with attribution to William May, Keith T. Poole and Nolan McCarty.
- `reproduce/`, the extraction scripts and per-figure receipts.
- A licence file. Proposed: MIT for the code, CC BY 4.0 for data and reproduction scripts. Not yet
  agreed by all three authors.

## Building

```
cd engine-faithful
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

See `engine-faithful/CMakeLists.txt` for the flags and `engine-faithful/SEEDS.md` for the seeding
contract, which matters: the frame the seed supplies is the frame the fit keeps.
