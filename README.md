# dwnominate-chile

Reproduction package for a verified, parallel C++ reimplementation of **DW-NOMINATE**, checked
component by component against the canonical 2004 Fortran (Poole–Rosenthal / McCarty), and applied
to the Chilean Chamber of Deputies.

Accompanies a paper submitted to the 45th International Conference of the Chilean Computer Science
Society (SCCC / JCC 2026). Roberto Nieves Tocornal, Pablo Antivil Morales, Julio Rojas-Mora.

---

## Contents

| path | what |
|---|---|
| `engine-faithful/` | **the engine.** Our C++ port of `dwnom2004`, sources, build files, benchmarks and the exact compiler flags used. This is the tree the paper's numbers come from |

## Status, 2026-08-19

**This repository was just updated and the previous contents were replaced.** Until today it held two
**pre-fix** engine trees, `engine/` at `f01e747` and `engine-experimental/` at `e27ec21`. Both
predate a defect fix and **both have been removed**, because anyone building them would reproduce
numbers the paper no longer reports.

**What changed in the engine.** `prepareRollCallData` filled the coordinate and vote arrays in
legislator order, computed the projection order, and then reordered **only** the vote array,
returning the two misaligned. The one-dimensional branch compensated, so `JAN11PT` was unaffected;
the two-dimensional branch passed both straight to `CUTPLANE`, which therefore classified a shuffled
pairing of legislators to votes. The later optimizer receives coordinates and votes separately, which
is why the likelihood and the derivatives were correct and the defect stayed hidden behind them.

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

- `engine-modern/`, the NLopt variant (COBYLA / BOBYQA, and now SLSQP with analytic gradients). It is
  a second engine and a cross-check, never the faithful one. Its authoritative copy is Julio's.
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
