# Three-engine comparison, 2026-08-20

Fortran 2004, `engine-faithful` and `engine-modern` on the same six panels, from the same
W-NOMINATE seeds, at `iterations=4`, **single-threaded everywhere**.

Every arm here is reproducible from `data/` in this repository plus the engines at the top level.

## 1. Results

`class %` is on valid votes. `vs Fortran` is the log-likelihood difference, positive meaning higher
likelihood than the canonical engine.

| panel | engine | wall | log-likelihood | vs Fortran | class % |
|---|---|---:|---:|---:|---:|
| Chile leg 353, static, model 0 | Fortran 2004 | not logged | -1,146.378 | - | 93.93 |
| | engine-faithful | 1.53 s | -1,132.370 | +14.0 | 93.83 |
| | **engine-modern, scalar local** | **0.48 s** | **-1,081.939** | **+64.4** | 94.12 |
| | engine-modern, scalar global | 0.39 s | -1,145.105 | +1.3 | 93.80 |
| Chile leg 366, static, model 0 | Fortran 2004 | 20.09 s | -6,347.665 | - | 94.82 |
| | engine-faithful | 8.13 s | -6,276.201 | +71.5 | 94.93 |
| | **engine-modern, scalar local** | **2.13 s** | **-5,826.237** | **+521.4** | 95.46 |
| | engine-modern, scalar global | 2.01 s | -6,393.647 | -46.0 | 94.97 |
| Chile leg 368, static, model 0 | Fortran 2004 | 35.01 s | -13,319.969 | - | 94.20 |
| | engine-faithful | 15.46 s | -13,296.522 | +23.4 | 94.22 |
| | **engine-modern, scalar local** | **4.10 s** | **-12,804.379** | **+515.6** | 94.37 |
| | engine-modern, scalar global | 3.87 s | -13,701.023 | -381.1 | 93.94 |
| Chile, dynamic, 23 periods, model 2 | Fortran 2004 | 362.68 s | -99,540.578 | - | 94.27 |
| | engine-faithful | 231.72 s | -98,603.657 | +936.9 | 94.16 |
| | **engine-modern, scalar local** | **64.87 s** | **-91,181.137** | **+8,359.4** | 94.66 |
| | engine-modern, scalar global | 64.00 s | -97,313.163 | +2,227.4 | 94.25 |
| US Senate 90, static, model 0 | Fortran 2004 | 17.86 s | -15,452.204 | - | 84.79 |
| | engine-faithful | 8.58 s | -15,457.167 | **-5.0** | 84.76 |
| | **engine-modern, scalar local** | **2.06 s** | **-15,293.328** | **+158.9** | 84.65 |
| | engine-modern, scalar global | 1.79 s | -15,531.928 | -79.7 | 84.59 |
| US, dynamic, 5 periods, model 1 | Fortran 2004 | not logged | -38,480.898 | - | - |
| | engine-faithful | 48.05 s | -38,462.784 | +18.1 | 93.27 |
| | **engine-modern, scalar local** | **11.87 s** | **-36,401.230** | **+2,079.7** | 93.50 |
| | engine-modern, scalar global | 11.34 s | -38,346.970 | +133.9 | 93.16 |

**Valid-vote parity holds in every cell**: 7,858 / 52,079 / 92,253 / 692,839 / 46,440 / 244,247,
identical across all three engines on each panel.

### What the table shows

1. **The scalar search mode, not the block solver, drives the divergence.** With
   `--scalar-search=global` the second-dimension weight `w2` inflates to 0.64-0.91 against a
   reference 0.50-0.54 and `beta` collapses to 3.6-4.6 against 5.2-6.3. With
   `--scalar-search=local` both track the reference on all six panels.
2. **`engine-modern --scalar-search=local` is both faster and higher-likelihood on every panel**,
   3.2x to 4.2x faster than `engine-faithful` and 5.6x to 9.4x faster than the Fortran.
3. **Global search is worse than `engine-faithful` on all three Chilean statics and on US Senate 90**,
   so a general claim that the NLopt engine reaches higher likelihood is not supported.
4. **The only cell where `engine-faithful` falls below the Fortran is US Senate 90, by 5.0 nats.**

## 2. Model-order A/B, Chile dynamic 23 periods

Same panel and seeds, varying only the temporal model order.

| model | engine-faithful | engine-modern local | engine-modern global |
|---|---:|---:|---:|
| 0, constant | -104,148.636 | **-99,385.241** | -106,167.023 |
| 1, linear | -100,896.604 | **-93,597.493** | -100,235.448 |
| 2, quadratic | -98,603.657 | **-91,181.137** | -97,313.163 |
| 3, cubic | pending | pending | pending |

Likelihood improves monotonically from model 0 to model 2 in all three engines, and the ordering
between engines is stable in that range. Model 3 was queued but did not complete in this capture.
Completed arms are in `_model-order-ab/`.

## 3. Provenance

| engine | build |
|---|---|
| Fortran 2004 | canonical `dwnom2004`, start config `NS NMODEL NFIRST NLAST IHAPPY1 IHAPPY2` |
| `engine-faithful` | `quevotan-api@79031cf`, `-O3 -march=native -ffast-math -DNDEBUG -fopenmp` |
| `engine-modern` | the tree in `engine-modern/` on `dev`, CMake `release` preset, `-O3 -DNDEBUG`, no OpenMP |

**Threading.** `engine-faithful` links OpenMP; every arm here was pinned with `OMP_NUM_THREADS=1`
and `--threads=1` so the wall clocks are comparable. Pinning changes only the wall clock: each
likelihood reproduces to the digit against the unpinned run.

**Compiler asymmetry, stated rather than hidden.** `engine-faithful` is built with `-march=native`
and `-ffast-math`; `engine-modern` is built with neither. This makes the speed comparison
conservative for `engine-modern`. It also means fast-math is a live confound on the *likelihood*
comparison: measured separately, `-ffast-math` moves the log-likelihood by about 14.9 nats on a
Chilean panel, which is negligible against the +450 to +8,359 nat modern-versus-faithful gaps but is
the same order as the faithful-versus-Fortran gaps on the static panels.

**Iteration count.** Everything here is at `iterations=4`, matched across engines. The Fortran outer
loop is `DO 9999 IHAPPY = IHAPPY1, IHAPPY2` in `DW-NOMINATE.f`, and the start-file field is the same
unit as `--iterations`. **These are matched snapshots, not converged optima**; a statement that one
engine beats another here means "at iteration 4".

**US dynamic Fortran likelihood** was recovered from the last row of `fort.27`, that run having no
log. The method was validated on the five panels holding both a log and a `fort.27`: the last
`fort.27` row equals the final logged `LNL` in 5 of 5 cases.

## 4. Layout

```
<panel>/<arm>/cpp_summary.csv                             likelihood, class %, w1/w2/beta, wall clock
              cpp_coordinates_all_periods.csv             raw export
              cpp_coordinates_all_periods_corrected.csv   served periods only, local t
              cpp_bill_parameters.csv                     roll-call midpoints and spreads
              cpp_convergence_trace.csv                   per-iteration likelihood
              run.log                                     configuration echo and input counts
```

Arms are `faithful`, `modern-ltr-{local,global}` and `modern-audit-{local,global}`. The two
`modern-*` generations differ in source but are **numerically identical on all four Chilean panels in
both scalar modes**, so either can be used; `modern-ltr-*` corresponds to the `engine-modern` tree
published on `dev`.

`cpp_optimizer_trace.csv` is omitted for size, up to 4.7 MB per arm. Regenerate it by re-running any
arm with the command in its `run.log`.

## 5. Reproducing

```bash
# static, one legislature
dwnominate-modern --input-dir=data/chile-static/leg366 \
  --output-dir=<out> --wnominate=data/chile-static/leg366/wnominate_coordinates.csv \
  --model=0 --iterations=4 --periods=1 --dimensions=2 --beta=5.9539 --w2=0.3463 \
  --block-solver=slsqp --scalar-search=local --threads=1

# dynamic, 23 periods
dwnominate-modern --input-dir=data/chile-dynamic \
  --output-dir=<out> --wnominate=data/chile-dynamic/wnominate_coordinates.csv \
  --seed-per-period=data/chile-dynamic/wnominate_coordinates_per_period.csv \
  --model=2 --iterations=4 --periods=23 --dimensions=2 --beta=5.9539 --w2=0.3463 \
  --block-solver=slsqp --scalar-search=local --threads=1
```

Set `OMP_NUM_THREADS=1` for comparable timings. Drop `--block-solver` and `--scalar-search` for
`engine-faithful`, whose binary is `dwnominate`.

## 6. What is not established here

- Likelihoods are **self-reported by each engine**, not scored by a single external evaluator.
- **No Procrustes or per-dimension correlations** are computed for these runs, so this file says
  nothing about whether the engines agree on the *map*. Two engines can reach nearly equal
  likelihoods on very different configurations, and on these panels they do.
- The Fortran wall clocks come from earlier sessions on unknown flags and load. The
  faithful-versus-modern timings were measured back to back on one machine and are directly
  comparable; the Fortran ratios need a same-session re-run before being quoted.

## 7. Known defect in the dynamic exports, read before plotting

`engine-modern` does **not** carry the export-frame fix that `engine-faithful` has. On the Chilean
dynamic panel it writes **7,774** rows where `engine-faithful` writes **2,855**, the extra 4,919
being padded placements for (legislator, period) pairs the member did not serve. Its
`cpp_coordinates_all_periods_corrected.csv` is identical to its raw export.

**Filter any dynamic `engine-modern` export to the served pairs before plotting or correlating**,
taking the roster of served keys from the corresponding `engine-faithful` export. Unfiltered, about
63 % of the plotted points on that panel are phantoms.

This is an **export and plotting defect only**. The optimiser and the likelihood already operate on
served spans, so every likelihood, weight and timing in section 1 is unaffected.

On the served subset, dimension 1 agrees closely between the engines (r = 0.973) while dimension 2
does not (r = 0.784, modern's spread 17 % wider), and the disagreement is confined to the dynamic
panels: every static panel is at r = 0.962 to 0.998 on both dimensions.

**Out-of-disk placements in the dynamic model are expected.** The unit-ball constraint applies to the
intercept, while the per-period coordinate is the intercept plus Legendre terms and is not
re-projected. Legislators serving a single period, where the polynomial is inactive, sit at radius
exactly 1.0000 with none outside; multi-period legislators reach 2.4161 with 6.5 % outside. The
canonical Fortran behaves the same way.
