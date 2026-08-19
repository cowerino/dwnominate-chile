# Per-(legislator, period) seeding — `--seed-per-period`

Interface contract for the DW-NOMINATE C++ module's external seed override.
Landed in commit `8c46459` (REQ-001), on `feature/dwnominate-cpp`. Optimizer math
is untouched by this flag; it only sets starting coordinates.

## What it is

DW-NOMINATE fits each legislator a *trajectory* (Legendre polynomial coefficients
over the period range), starting from a seed coordinate. By default the engine seeds
every period of a legislator with the **same** per-leg coordinate (`--wnominate`).
For long-career movers that career-average seed zeroes the Legendre curvature and
collapses the late-period trajectory (the Chilean estallido/constitutional periods).

`--seed-per-period` lets you supply a **distinct seed per (legislator, period)**, so
the dynamic model starts from the period-specific W-NOMINATE position.

## CLI

```
dwnominate --input-dir=<dir> --periods=<N> --model=<m> --dimensions=2 \
           --seed-per-period=<seeds.csv> \
           [--wnominate=<per-leg-fallback.csv>] \
           --iterations=<k> --output-dir=<out>
```

- `--seed-per-period=<path>` is **optional** and **off by default**. When absent, the
  engine behaves exactly as before (per-leg path), so US/sen90 benchmarks are inert
  to this flag (byte-identical regression confirmed in `8c46459`).
- It is a **priority override**, not a replacement: the seed-application loop dispatches
  **per-(leg,period) seed → per-leg `--wnominate` → deterministic fallback (0,0)**.
  Keep `--wnominate` set as the fallback for tuples missing from the per-period file.

## Seed file format

4-column CSV, **header row required** (the first line is unconditionally skipped):

```
legislator_id,period,coord1D,coord2D
12345,1,-0.42,0.10
12345,2,-0.38,0.12
...
```

Hard requirements (each is a silent-failure trap if violated):

| Rule | Violation symptom |
|---|---|
| **Header row present** (line 1 skipped) | first real legislator dropped |
| **`period` is 1-based**, matching `legislatura_map.csv` | every lookup misses → falls back to (0,0) → flat trajectory → looks like "1 point per legislator" |
| **≥4 columns per row** | row silently skipped |
| `legislator_id` namespace matches the input matrices | unmatched ids fall back |

Rows with `legId <= 0` or `period <= 0` are dropped. Extra columns are ignored.

## Diagnostic: confirm the seeds were ingested

On load, the module prints to **stdout**:

```
  W-NOMINATE per-period: Cargadas N coordenadas (leg, periodo) desde <path>
```

- `N == 0` → path or format wrong (header/columns/namespace). Not a code bug.
- **line absent entirely** → the binary predates `8c46459`; rebuild from
  `feature/dwnominate-cpp`. (An old binary handed `--seed-per-period=` prints
  `Advertencia: argumento desconocido` to stderr and silently continues per-leg.)

The run also reports the seed breakdown: per-(leg,period) applied / per-leg fallback /
deterministic fallback. For the canonical Chilean run expect **2685 per-period, 170
per-leg fallback, 0 deterministic**.

## Important: seeds ≠ trajectory

The seed file sets *starting values only*. The number of output rows per legislator
(the trajectory itself) comes from the **multi-period stacking** (`--periods` +
`legislatura_map.csv` + the Finding-C multi-period fix `99b7891`). A correct seed file
on a binary that lacks `99b7891`, or a run with `--periods=1`, still yields **one point
per legislator**. Both `8c46459` (this flag) and `99b7891` (multi-period) must be in the
binary. Both are on `feature/dwnominate-cpp`.

## Canonical Chilean invocation

Inputs and the seed generator live in the companion reproduction package:

```
# 1. build seeds from per-legislatura W-NOMINATE (chain-Procrustes aligned)
python reproduce/scripts/build_chile_seeds_per_period.py   # -> ~2685 rows, 22 periods

# 2. run the engine (23 legislaturas 347-369, quadratic temporal model)
dwnominate --input-dir=reproduce/input --periods=23 --model=2 --dimensions=2 \
           --seed-per-period=<seeds.csv> --wnominate=reproduce/input/wnominate_coordinates.csv \
           --iterations=4 --output-dir=<out>
```

Established reference result (C++ vs Fortran 2004, both per-period seeded — see
the reproduction package's REQ-001 record):

| Engine | Class % | β | w2 |
|---|---:|---:|---:|
| Fortran 2004 NMODEL=2 | 94.15% | 5.30 | 0.5163 |
| C++ `--model=2 --seed-per-period` | 91.16% | 5.20 | 0.5263 |

β ≈ 0.5 or a single output row per multi-period legislator = Finding-C collapse =
wrong/stale binary, **not** a seed-file problem.
