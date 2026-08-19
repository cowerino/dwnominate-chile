# DW-NOMINATE C++ regression benchmarks

Version-controlled regression oracle for the C++ DW-NOMINATE module, anchored on
**external, published** reference data (US Senate). Two tiers:

- `sen90/` — **Tier 1**, single-period static W-NOMINATE reproduction. Cheap gate:
  if the static core breaks, stop here.
- `us/` — **Tier 2**, multi-period dynamic DW-NOMINATE reproduction on 5 contiguous
  US Senates (Congresses 111-115), against both the in-house Fortran (`wmay/dwnominate`)
  and VoteView's **published** DW-NOMINATE scores.

Polarity and rotation are free gauges in NOMINATE, so all comparisons
orthogonal-Procrustes-align (rotation + reflection, no scaling) before correlating.

## Why this exists (the Finding C fix)

The C++ engine was written for a **stacked XDATA** layout (one matrix row per
*(legislator, period)* appearance, Fortran style) — every coordinate-access path
(`computeLogLikelihood`, `computeRollCallDerivatives`, the per-period
`computeLegislatorDerivatives`, presence-detection, `reconstructLegislatorCoords`,
and the `legislatorOffset` accounting) assumes it. But the CSV loader built
**unique-legislator** storage (one row per legislator, spanning all periods).
Two consequences ("Finding C"):

1. Per-period roll-call addressing (`legislatorOffset + localLeg`) ran off the end
   for periods 2+, so later periods were silently skipped → beta collapsed
   (5.95 → ~0.5), classification cratered, and the recovered map degenerated
   (Chilean center-left clustered with the right).
2. Per-period coordinates collapsed onto a single row (`reconstructLegislatorCoords`
   overwrote it each period), so the global likelihood used one flat coordinate for
   all of a multi-period legislator's votes.

**Fix (2026-05-24), two pure-indexing changes, no optimizer math:**

- `src/csv_loader.cpp` `buildDWNominateInput`: build the **stacked** layout the engine
  already expects (one row per legislator-period-active; votes non-missing only in that
  period's roll calls; `congressMetadata` carries per-period active counts).
- `src/dwnominate.cpp` `buildLegislatorPeriodInfo`: populate `rollCallCounts` for **all**
  periods in range, not just served ones. The global roll-call offset in
  `computeLegislatorDerivatives` is `sum(rollCallCounts[0..j-1])`; leaving non-served
  periods at 0 mis-addressed any legislator entering after period 0 → in the stacked
  layout that points at all-missing columns → 0 votes → the legislator froze at its
  seed coordinate. (Found during verification: the storage fix alone made every
  *internal* metric healthy but left the per-period *output* correlation flat-bad,
  because partial-tenure legislators — the bulk of each period's roster — were frozen.)

Single-period runs collapse to the prior behaviour (one period ⇒ stacked == unique),
so Tier 1 is unchanged.

## How to run

Build first: `cmake --build build --target dwnominate`. Needs Python (numpy, pandas).
The R scripts (`01_acquire.R`, `02_dwnominate.R`, `build_sen90_input.R`) regenerate the
reference data from CRAN `wnominate` / `Rvoteview` / the `wmay/dwnominate` Fortran and are
provided for provenance; the committed reference CSVs let you run the comparison without R.

### Tier 1 (sen90, single-period)
```
dwnominate.exe --input-dir=sen90 --output-dir=sen90/out_seedA \
  --wnominate=sen90/wnominate_coordinates.csv --periods=1 --model=0 --iterations=4
dwnominate.exe --input-dir=sen90 --output-dir=sen90/out_seedB \
  --wnominate=sen90/wnominate_coordinates_perturbed.csv --periods=1 --model=0 --iterations=4
python sen90/compare_sen90.py        # run from sen90/
```

### Tier 2 (US 5 Senates, multi-period)
```
dwnominate.exe --input-dir=us/cpp_input --output-dir=us/cpp_out \
  --wnominate=us/cpp_input/wnominate_coordinates.csv --periods=5 --model=1 --iterations=4
python us/03_compare.py              # C++ vs Fortran vs VoteView, per period
python us/04_final_vs_voteview.py    # final confirmation: both modules vs published VoteView
```

## Expected results (PASS thresholds, post-fix 2026-05-24)

**Tier 1 sen90** — C++ vs published W-NOMINATE `sen90wnom`, dim1 Pearson **r ≈ 0.992**
(Spearman 0.990, dim2 0.988, mean 2D dist 0.129); perturbed-seed run reproduces it
(estimates, not regurgitates); seedA-vs-seedB init stability r ≈ 0.995; party means
D = −0.151 / R = +0.265.

**Tier 2 US** — C++ vs Fortran dim1 **flat ≈ 0.99 across all 5 periods**
(0.987 / 0.992 / 0.992 / 0.992 / 0.990); the bar is **≥ 0.95 flat, not 1.0**.
Both modules vs **published VoteView**: C++ ≈ 0.97-0.98, Fortran ≈ 0.985, both flat.
Beta stays ~6 (no collapse), classification ~92%.

**Known residual (not Finding C):** C++ ideal points are amplitude-inflated and
trajectory slopes slightly steeper than Fortran/VoteView (e.g. a far-right senator
~1.0 in C++ vs ~0.55 in VoteView). Rank/correlation is preserved. This is the
CUTPLANE/SEARCH divergence ("Finding B"), tracked separately — do not chase r = 1.0.
