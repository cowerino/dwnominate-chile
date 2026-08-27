# Parametric bootstrap of dimension-1 party medians, n = 200

Uncertainty estimates for the dimension-1 party medians of the
`chile-expanding-4month-24u` panel (Chilean Chamber of Deputies, 24 units of
roughly four months, 2014-03-11 to 2022-03-10), at three prespecified slices of
the 55th legislative period. Design: Carroll, Lewis, Lo, Poole & Rosenthal
(2009) parametric bootstrap; 200 replicates, each one a complete re-estimation
on votes redrawn from the fitted model. Findings and method detail:
[`SYNTHESIS.md`](SYNTHESIS.md).

## Layout

| path | contents |
|---|---|
| `SYNTHESIS.md` | design, validation, result tables, drift-bias mechanism, verdicts |
| `summary/` | the analysis tables (per-replicate party medians and changes, observed values, intervals, readouts, diagnostics) |
| `replicates/replicate_coordinates.csv.gz` | all 200 replicate coordinate exports in one file: `replicate, legislator_id, period, coord1D, coord2D, effective_model`; 3,265 served (legislator, period) rows per replicate, in each refit's own frame (pre-alignment) |
| `observed/` | the observed reference fit this bootstrap resamples: coordinate export and run summary |
| `drift/` | outputs of the drift-bias mechanism analysis (per-dimension scale fits, per-period shift profile, bias comparison) |
| `party_membership.csv` | time-resolved party per (legislator, period) |
| `period_calendar.csv` | the 24 units: dates, roll-call counts, panel tags |
| `target_slices.csv` | the three prespecified slices and their event anchors |
| `workflow_status.csv` | per-replicate RNG seeds and stage status |

## Estimation configuration

One estimation per replicate, identical to the observed fit: 2 dimensions,
temporal order 1, 4 iterations, `scalar_search=local`, `block_solver=cobyla`,
single-threaded, `engine-modern` built from this repository (`main` at
`c9a1a39`). Per-unit W-NOMINATE seeds are rebuilt from each pseudo-sample and
orientation-harmonised before the fit. Master seed 20260826; per-replicate
seeds are in `workflow_status.csv`. Every run's own configuration is recorded
in its `cpp_summary.csv`; the observed fit's copy is in `observed/`.

## Reproducing the tables

- `summary/party_median_intervals.csv` and `summary/party_change_intervals.csv`
  are arithmetic over `summary/bootstrap_party_medians.csv` /
  `summary/bootstrap_party_changes.csv` against the `observed_*` files:
  bootstrap SE, bias (bootstrap mean minus observed), percentile 95% CI, and
  basic 95% CI (2 x observed minus the opposite percentile endpoint).
- `summary/readout_n200.csv` adds sign-consistency counts, empirical two-sided
  p-values (floor 1/201 = 0.005), and Holm correction across the 30 reported
  cells.
- The per-replicate medians themselves are computed after aligning each
  replicate to the observed fit by one global orthogonal Procrustes over all
  3,265 (legislator, period) rows. To redo that step from scratch, use
  `replicates/replicate_coordinates.csv.gz` (raw frames) against
  `observed/cpp_coordinates_all_periods.csv`, then take party medians per
  slice using `party_membership.csv` and `target_slices.csv`.

## Withheld for size

The 200 pseudo-sample input trees (vote matrices, rebuilt seeds; about 220 MB)
and the per-replicate optimizer traces. They regenerate deterministically from
the observed fit in `observed/` and the seeds in `workflow_status.csv`; the
redraw covers every observed non-missing vote (missingness preserved), and the
2.5% minority filter is recomputed on the simulated data.
