# DW-NOMINATE C++ module — validation record

This C++ module reimplements DW-NOMINATE. Its fidelity is validated against the
canonical **Fortran 2004 (Poole–Rosenthal / McCarty) oracle** on two datasets:
US Senate 1–117 (external VoteView ground truth) and the Chilean Congress
(2002–2021). For Chile, dim-1 is now externally validated against an
expert-ratified production reference (REQ-011: C++ arms r 0.966–0.987 every
overlapping year, periodo 9; Fortran ~0.93); dim-2 lacks an external anchor for
the post-2018 years (the reference's rolling-accumulation frame froze in 2018),
so dim-2 is engine-vs-engine there. **Earlier "no external ground truth" framing
is stale (corrected 2026-06-13).**

**Panel naming (binding).** Two Chilean panels coexist: the **replication panel**
(`reproduce/input/`, legs **347–369-partial**, the fidelity-matrix numbers below)
and the **experiment panel** (`out/chile/cpp_input/`, legs **346–368**, the
REQ-011..015 headline results). Every citable Chilean number must name its panel.

Full reproduction harness, Fortran oracle binary, seeds, and per-Congress
Procrustes scripts live in the companion reproduction package (`REPLICATION.md`,
`BRIDGE.md` = coordination ledger, `FINDINGS.md` = empirical record).

## Build

Standard build:

```
cmake -S . -B build
cmake --build build --target dwnominate -j 4
```

**Reference-LAPACK routing (REQ-005, recommended for best fidelity).** Routing
Eigen's SVD/BLAS through reference netlib LAPACK 3.12.1 reduces the residual gap
vs Fortran in ill-conditioned regimes. The library is large (~30 MB) and is
git-ignored; regenerate it once with the command embedded in `.gitignore`
(`/external/` section): download `lapack-3.12.1`, then
`cmake -G "MinGW Makefiles" -DBUILD_SHARED_LIBS=OFF -DLAPACKE=ON -DCBLAS=OFF
-DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release .. && cmake --build . -j`.
CMake auto-detects it at `external/lapack-3.12.1/build` and defines
`EIGEN_USE_LAPACKE` + `EIGEN_USE_BLAS`. Without it the build falls back to
pure Eigen (still correct, slightly larger residual on worst-case congresses).

## Fix ladder (REQ-001 → REQ-006)

| REQ | Fix | Effect |
|---|---|---|
| 001 | `--seed-per-period` per-(leg,period) seeding (see `SEEDS.md`) | Chile late-period dim-1 collapse 0.19 → 0.99 |
| 003 | Zero Legendre coefficients above active `temporalModel` (output-path cubic leak) | Chile dim-2 trajectory 0.60 → 0.80 |
| 004 | Remove 4 rollcall-phase unit-sphere clamps + restore `numSearchPoints=25` (Fortran NINC) | Chile dim-2 0.85 → **0.93**; US dim-2 0.958 → **0.967**; sen90 +1.0pp |
| 005 | Route Eigen SVD/BLAS through reference LAPACK 3.12.1 | Worst-case congresses +0.02–0.06 dim-2; halved the iter-1 LL deficit (26k → 12k) |
| 006 | RC line search hardcoded `array<…,15>` + `min(numSearchPoints,15)` silently clamped REQ-004's restored `=25` back to 15; raised both to 25 (`@dba3128`) | Fortran-faithfulness fix; verified non-regressive; **null on the residual** — the chase then concluded the residual is FP-floor (see below) |

## Fidelity matrix (post REQ-004 + REQ-005 + REQ-006, NITER=4, Procrustes vs Fortran 2004)

**Chile rows below are on the 347–369-partial replication panel.** The 25-unit sub-period
experiment panel (REQ-013..015) has a quad cross-engine median of 0.992/0.930 — do not reuse the
rows below for it.

| Cell | dim-1 r (median) | dim-2 r (median) | worst congress dim-2 |
|---|---|---|---|
| US linear v=1, 1–117 | 0.986 | 0.969 | 0.830 |
| US quadratic v=2, 1–117 | 0.981 | 0.955 | 0.818 |
| US cubic v=3, 1–117 | 0.980 | 0.950 | 0.760 |
| Chile linear v=1, 23-period | 0.995 | 0.938 | 0.876 |
| Chile quadratic v=2, 23-period | 0.993 | 0.932 | 0.766 |
| Chile cubic v=3, 23-period | 0.992 | 0.882 | 0.722 |

All cells dim-1 ≥ 0.98, dim-2 ≥ 0.88; principal/well-converged regimes ≥ 0.93.

## Determinism and the nature of the residual

Established by a five-test diagnostic sweep (2026-06-07; full record in
the reproduction package's findings record):

- **The engine is bit-reproducible.** Identical inputs give byte-identical
  output across thread counts and run-to-run (OpenMP reduction is order-stable
  on this workload).
- **The residual vs Fortran is NOT non-identifiability.** Under seed
  perturbation the engine returns to within dim-2 r 0.97–0.999 of itself in
  every regime, while disagreeing with Fortran by more — so the cross-engine
  gap is a systematic implementation/optimization-path difference, not seed or
  basin noise.
- **It is NOT a weaker optimizer or a different likelihood.** Seeded near
  Fortran's solution the engine reaches comparable (even higher) log-likelihood;
  the objective is shared.
- **The comparison is valid only at matched iteration count (NITER=4).** The
  DW-NOMINATE answer is procedure-defined, not likelihood-maximal: beyond NITER=4
  the β parameter drifts upward and map agreement with Fortran *degrades*. Do not
  "fix" fidelity by adding iterations.

**The residual is fully attributed (REQ-006 concluded 2026-06-09): single-vs-double
floating-point path divergence in the non-convex fixed-NITER procedure, by exhaustive
exclusion of every *identified* algorithmic alternative.** The earlier "leading suspect:
β-step / SVD family" framing is SUPERSEDED — both were tested and exonerated: β is
bit-identical to Fortran through iter-2 and within 0.05 at iter-4 (the runaway is a
>iter-4 artifact); the SVD/cutting-plane family does not track cloud degeneracy
(corr −0.03); the NINC 15→25 fix and the CDF nearest-neighbour match are both faithful
but null. Every estimation formula is verified bit-identical to Fortran; the only
remaining difference is arithmetic precision. The one un-run confirmation is a direct
single-precision downcast (D7) — left as future work because it would make C++ *less*
accurate (on US, Fortran-vs-VoteView 0.985 > C++ 0.977). Forward-stated summary:
the fidelity-findings record; receipts are kept with the reproduction package.

## Performance (timing receipt — FACTORED 2026-06-13)

Identical input/model/NITER on the Chilean 25-unit sub-period panel (quad, NITER=4),
AMD Ryzen 5 5600 (6c/12t), Windows. Fortran 2004 = serial.

| Run | Wall clock | per-core vs Fortran |
|---|---|---|
| Fortran 2004 (serial) | 334s (5m34s) | 1.00× |
| C++ serial (`OMP_NUM_THREADS=1`) | 339.6s | **0.98× (parity)** |
| C++ OpenMP (≤12 threads) | 42.2s | (7.9× combined) |

**The speedup is parallelism, not compiled-code speed.** Per core the C++ engine is at
parity with the canonical Fortran (0.98×, marginally slower); the ~8× wall-clock advantage
comes entirely from OpenMP parallelizing the roll-call phase (RC 287.2s → 35.1s = 8.19×,
~85% of runtime). Single-thread numerics are byte-identical to the parallel run (LL
−99530.16, class 93.49%, β 5.9289 — OpenMP math-neutral, Canary 0). **Report the speed as a
parallelization result, always with the single-thread parity number; do NOT claim a faster
engine.** The canonical Fortran could be parallelized similarly. Receipt:
the timing receipt in the reproduction package.
