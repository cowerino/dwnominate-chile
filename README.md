# dwnominate-chile

A verified, parallel C++ reimplementation of **DW-NOMINATE**, checked component by component
against the canonical 2004 Fortran (Poole–Rosenthal / McCarty), and applied to the Chilean
Chamber of Deputies.

Reproduction package for a paper at the 45th International Conference of the Chilean Computer
Science Society (SCCC / JCC 2026) — Roberto Nieves Tocornal, Pablo Antivil Morales, Julio
Rojas-Mora — and the public home of an ongoing dynamic study of the 55th Legislative Period
(2018–2022).

---

## The question this package serves

Whether, and by how much, party positions in the Chilean Chamber moved along the first
(left–right) dimension across the events that partition the 55th Legislative Period: the
*estallido social* (2019-10-18) and the constitutional plebiscite (2020-10-25). The three
sub-periods P1 / P2 / P3 are prespecified from those dates, before looking at any estimate.

Answering that question dynamically with DW-NOMINATE runs into three constraints that shape
everything in this repository, all documented rather than worked around silently:

1. **The per-legislator degree cap.** A legislator serving fewer than 5 discretized periods is
   frozen to a constant trajectory whatever the requested model order; 5 permits linear. The cap
   is per legislator, not per panel, so window and unit-width design is what decides whether the
   2018 cohort can move at all. Trajectories here are linear, on parsimony grounds.
2. **Discretization.** Unit width trades identification per unit against trajectory resolution.
   Several widths are published side by side (annual, 4-month, 3-month) rather than one being
   silently chosen.
3. **A weakly identified second dimension.** Estimations are two-dimensional because the spatial
   model is; substantive inference is restricted to dimension 1. See *Limitations* below.

## Contents

| path | what |
|---|---|
| `engine-faithful/` | **the validated instrument.** Our C++ port of `dwnom2004` at `quevotan-api@79031cf`: sources, build files, benchmarks, exact compiler flags. Every number in the JCC paper comes from this tree |
| `engine-modern/` | **an independent modern reimplementation** on NLopt (COBYLA / BOBYQA), authored by Julio Rojas-Mora. A second engine and a cross-check, never the faithful one. Complete; builds; ctest 9/9 |
| `fortran-canonical/` | **the reference.** Both canonical Fortran sources unmodified — Poole/Rosenthal's 2004 distribution and the `wmay/dwnominate` core — plus the stub and harness that let each run outside R |
| `data/` | every panel any engine here is run on, with real rosters: the Chilean 23-period dynamic panel, static legislaturas 353 / 366 / 368, US Senate 90, and the US 5-congress dynamic panel. See `data/README.md` |
| `figures/` | published figures, one run vintage each: `figures/dynamic/` (the 55th-PL expanding-window study and the 23-period panel) and `figures/static/` |
| `results/` | dated, frozen result sets: three-engine comparison tables (2026-08-20, 2026-08-25), the converged-modern record, and goodness-of-fit including APRE (2026-08-26) |
| `validation/` | falsification harness: `run_falsification.py` plus the known-defect patch it must detect. The reproduction claim is testable, not asserted |
| `reproduce/` | self-checking reproduction of the static three-engine comparison from a clean clone |
| `experimental/` | two pre-fix engine trees kept deliberately, named by commit, **not for results**. See `experimental/README.md` |

## The three engines, and what each is for

- **`engine-faithful`** is the instrument. Its validation is the point of the JCC paper: on a
  static US Senate 90 panel it lands 0.611 nats from the Fortran over 46,440 votes (`r1` 0.9997,
  `r2` 0.9993), and on the 23-period Chilean panel, after the export-frame correction, `r1`
  0.9996 / `r2` 0.9942 against the 2004 Fortran under a single global Procrustes.
- **`fortran-canonical`** is the reference those numbers are measured against, vendored so the
  comparison is reproducible here rather than in a private R setup.
- **`engine-modern`** is an independent cross-check with state-of-the-art local optimizers. It is
  compared against the other two, never mixed with them. It can converge to different optima on
  some panels; `results/2026-08-20-converged-modern/` preserves one such run because it is
  instructive, not because it is quotable. Cross-engine agreement tables live in `results/`.

## The dynamic study of the 55th Legislative Period

`figures/dynamic/` carries an expanding-window design: three fits per discretization, each over a
window opening in 2014 and closing at one of the prespecified boundaries, so each terminal
placement is what an analyst could have produced in real time. Published discretizations:
annual (7 units), 4-month (24 units, plus a lower vote screen variant), and 3-month (31 units).
`figures/dynamic/README-expanding-windows.md` documents the design; each figure directory carries
its run manifest, and the per-legislator *effective* degree (after the cap) is stamped, not just
the requested one.

Fit quality for these runs, including APRE, is tabulated at
`results/2026-08-26-goodness-of-fit/`.

**Data.** The 55th-PL roll calls come from Fábrega's *Data in Brief* release
(DOI `10.1016/j.dib.2025.112163`; Harvard Dataverse `10.7910/DVN/FOXOIT`), dated against the
Cámara de Diputados open-data index. Both sources are public.

**Not here yet.** The estimation pipeline behind these figures — panel builder, W-NOMINATE
seeding and orientation harmonisation, and the parametric-bootstrap inference on party medians —
currently lives in the companion working repository. Promoting it into this package as a runnable
reproduction tier is planned; until then this repository carries the results tier of the study,
with provenance stamps in every result set.

## Limitations, stated up front

- **Dimension 2 is weakly identified on this data.** The fitted second-dimension weight sits
  near 0.53–0.54 in the published runs (see `results/2026-08-26-goodness-of-fit/`), per-unit seed
  orientation comes back reflected across boundaries unless explicitly harmonised, and
  cross-engine and cross-window disagreement concentrates on dimension 2. Substantive claims in
  this line of work are dimension-1 claims; dimension 2 is retained because the model is
  two-dimensional and vote probabilities depend on it, not as an interpretable quantity.
- **The degree cap is a design constraint, not a data fact.** Identical legislators, votes and
  engine produce frozen trajectories on a coarse grid and moving ones on a fine grid. Any
  trajectory read off these figures must be read jointly with the discretization that produced it.
- **The engines are evidence about each other, not interchangeable.** Agreement supports a
  conclusion; where they disagree (dimension 2, some optima), the disagreement is reported, not
  averaged away.

## Engine fix history, condensed

Full narratives are preserved verbatim in `docs/HISTORY.md`; headline entries:

| date | fix | effect |
|---|---|---|
| 2026-08-15 | coordinate/vote misalignment into `CUTPLANE` | LL gap to Fortran on the 23p panel: 26,609 → **34.3 nats**; classification gap 2.99 → 0.02 points |
| 2026-08-19 | pre-fix trees quarantined into `experimental/` | building the wrong engine no longer reproduces retracted numbers |
| 2026-08-20 | export frame (global-t → served/local-t), vote-code mapping, seedless-legislator origin start | `r2` vs Fortran on the 23p panel 0.9190 → **0.9942**; export rows 7,774 → 2,855; fits unchanged |
| 2026-08-20 | package reproducibility: real rosters in `data/`, US panels added, Fortran arm vendored, absolute paths removed | figures regenerate byte-identically off the authoring machine |
| 2026-08-25 | deterministic parallel log-likelihood; US 5-congress seed generator | 12-thread LL spread 38.04 → **0 nats**; seed origin rows 61 → 4 |

## Known issues, stated rather than hidden

- **`engine-faithful/benchmarks/README.md` PASS thresholds are dated 2026-05-24 and predate the
  2026-08 fixes.** The Tier 1 dim-1 criterion (`r ≈ 0.992`) is satisfied by the *defective*
  pre-fix build and marginally missed by the corrected one, so it points the wrong way, and the
  Tier 2 floor (`≥ 0.95` flat) is too coarse to separate the two. Read the thresholds as a
  description of the 2026-05-24 run, not as diagnostic gates; corrected thresholds derived from a
  measured good-versus-bad separation are pending.
- The faithful engine is compiled with fast-math relaxations, and its linear-algebra path is an
  explicit build option, `USE_REF_LAPACK` (default ON) — but the LAPACKE route is taken only when
  the option is ON **and** `external/lapack-3.12.1/build/lib/liblapacke.a` exists; otherwise the
  cutting-plane SVD silently falls back to Eigen's Jacobi implementation. **The two paths
  converge to different optima.** All reported fits use the LAPACKE path; read the CMake status
  line rather than assuming it.

## Building

**Two dependencies are not vendored and you must supply them** (both are gitignored upstream as
well, so this is a property of the sources, not of this export):

- **Eigen 3.4.0**, unpacked so the headers sit at `engine-faithful/Eigen/` — that exact path is
  hard-coded as an include directory in `CMakeLists.txt`.
- **Reference netlib LAPACK 3.12.1**, if you want the published numbers:

```
cd engine-faithful/external
curl -L https://github.com/Reference-LAPACK/lapack/archive/refs/tags/v3.12.1.tar.gz | tar xz
cd lapack-3.12.1 && mkdir build && cd build
cmake -G "MinGW Makefiles" -DBUILD_SHARED_LIBS=OFF -DLAPACKE=ON -DCBLAS=OFF -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release ..
cmake --build . -j
```

Then:

```
cd engine-faithful
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

Check the configure output for `Reference LAPACK found at ...` before trusting a fit; if you see
`USE_REF_LAPACK=OFF` or no LAPACK line, you are on the Jacobi path and your numbers will not
match the ones reported above.

### engine-modern, and one Windows trap

```
cmake -S engine-modern -B engine-modern/build -DCMAKE_BUILD_TYPE=Release
cmake --build engine-modern/build -j
ctest --test-dir engine-modern/build --output-on-failure
```

NLopt is fetched and built by the configure step. On Windows/MinGW it lands as
`engine-modern/build/_deps/nlopt-build/libnlopt.dll`, which is **not** beside the test binaries
and is not found through an RPATH the way it is on Linux; every test then fails with
`0xc0000135`, `STATUS_DLL_NOT_FOUND`, which reads like a broken build and is not one. Put that
directory and the MinGW `bin` on `PATH` and the suite passes 9/9.

See `engine-faithful/CMakeLists.txt` for the flags and `engine-faithful/SEEDS.md` for the seeding
contract, which matters: the frame the seed supplies is the frame the fit keeps.

## Licensing

MIT for the source code, a separate licence for data, third-party components under their own
terms. `LICENSING.md` has the complete map; `LICENSE` and `LICENSE-DATA` carry the texts.
