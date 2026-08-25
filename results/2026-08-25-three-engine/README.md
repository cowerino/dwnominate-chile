# Three-engine comparison, 2026-08-25

Six panels by three engines, four outer cycles, one thread. This is the vintage the figures in
`figures/` were rendered from, so the maps there and the numbers here are the same fits.

## The table

`comparison-table.csv`, one row per panel.

| column | meaning |
|---|---|
| `panel` | panel name, matching the directory names here and under `figures/` |
| `votes` | valid votes after the 2.5 % lopsidedness screen |
| `fortran` | log-likelihood of the canonical `DW-NOMINATE-wmay.f` arm |
| `adhoc` | log-likelihood of `engine-faithful`, the C++ port of the ad hoc searches |
| `adhoc_native` | that C++ terminal state re-scored by the Fortran's own `PLOG` |
| `nlopt` | log-likelihood of `engine-modern`, derivative-free NLopt solvers |
| `nlopt_native` | that terminal state re-scored by the Fortran's own `PLOG` |
| `adhoc_gain_per_vote` | (`adhoc_native` − `fortran`) / `votes` |
| `nlopt_gain_per_vote` | (`nlopt_native` − `fortran`) / `votes` |
| `seconds` | wall time for the panel's three arms plus the two re-scores |

The `*_native` columns exist so the gains are not an evaluator artifact: the C++ states are
handed back to the Fortran and scored by it. Where a `*_native` value is present the gain column
uses it in preference to the engine's self-reported likelihood.

Read the gains as a percentage of the reference likelihood rather than per vote if that is
easier: on `us-dynamic-5p` the ad hoc arm is 0.36 % and the NLopt arm 2.44 % better than the
Fortran; on `chile-dynamic-23p`, 1.22 % and 17.27 %.

## Per panel, per engine

`<panel>/<engine>/` where `<engine>` is `fortran`, `faithful` or `modern`, carrying:

- `summary.csv` or `cpp_summary.csv` — log-likelihood, valid votes, correct classifications,
  classification percentage, the fitted weights `w1`/`w2`, `beta`, model order, periods
- `coordinates.csv` or `cpp_coordinates_all_periods.csv` — the fitted coordinates

Bill parameters are not shipped here, to keep the directory to 640 KB against the 15 MB the
full output tree occupies. They regenerate from the same command; ask if they are needed as
artifacts rather than as a re-run.

## What produced it

`reproduce/scripts/isolation_matrix.py` in the `quevotan-db` working repository, against the
panels in `data/`, `--iterations 4`, `OMP_NUM_THREADS=1` pinned by the driver. Both C++ engines
and the Fortran harness were built from a clean tree with dependencies pinned by commit.

Five of the six panels reproduce **bit-identically** against the preceding vintage; the three
`us-dynamic-5p` arms are the only files that differ, because that panel's seed was regenerated
the same day (origin rows 61 → 4).

## Two things to know before reading these numbers

**The dynamic panels are seeded per legislator, not per period.** Every arm here is started from
`data/<panel>/wnominate_coordinates.csv`, one coordinate pair per member reused in every period.
The canonical seeding for a dynamic panel is per-(legislator, period), and this repository ships
that file for the Chilean panel as `data/chile-dynamic/wnominate_coordinates_per_period.csv`.

All three arms are deliberately held to the per-legislator seed, because the standalone Fortran
harness reads only that filename and the comparison has to start every arm from the same place.
The consequence is that on `chile-dynamic-23p` the seed accounts for most of the distance between
the ad hoc and NLopt arms: a per-period-seeded ad hoc fit lands within about 120 nats of the
per-legislator-seeded NLopt fit shown here. Read the dynamic rows as a comparison of how the two
searches behave **from a degenerate start**, which is a real question, rather than as a measure of
which finds the better optimum. The static panels are unaffected — a single period has no
per-period seed to differ from.

**`temporal_model` is the order requested, not the order fitted.** Degree is gated on periods
served, so a `--model=2` run reports `2` while much of the chamber is held at a constant. Counted
from the `effective_model` column of the coordinate files shipped here:

| panel | constant | linear | quadratic |
|---|---|---|---|
| `chile-dynamic-23p` (requested 2) | **126 of 338** | 2 | 210 |
| `us-dynamic-5p` (requested 1) | **118 of 168** (faithful) | 50 | — |

The gate is canonical (`fortran-canonical/DW-NOMINATE-wmay.f:1479-1494`, mirrored in
`engine-faithful/src/dwnominate.cpp`), so a static majority on a short panel is a property of
DW-NOMINATE rather than of this implementation. Two caveats: the split is engine-specific
(`modern` gives 116/52 on `us-dynamic-5p`), and it is a **fit output rather than a roster
property** — the same panel yields 126/4/208 under a different seed lineage.

Runs made after 2026-08-25 stamp these counts into the summary directly as
`effective_model_<degree>,<count>`. The summaries in this directory predate that and do not
carry them.
