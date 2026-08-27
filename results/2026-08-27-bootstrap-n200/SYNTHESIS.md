# Parametric bootstrap of dimension-1 party medians, n = 200: synthesis (2026-08-27)

Frozen synthesis of the 200-replicate parametric bootstrap on the
`chile-expanding-4month-24u` panel. Numbers here are copied from the analysis
tables in `summary/` and `drift/`; nothing is re-derived in this document.

## Design

Carroll, Lewis, Lo, Poole & Rosenthal (2009) parametric bootstrap: every
observed vote is redrawn from its fitted DW-NOMINATE probability (missingness
preserved), and the **complete estimator** is rerun per replicate: per-unit
W-NOMINATE seeds rebuilt from the pseudo-sample, seed-orientation
harmonisation, then the dynamic fit. Each replicate is aligned to the observed
fit by one global orthogonal Procrustes over all 3,265 (legislator, period)
rows before any statistic is read.

- Observed fit: 24 units of ~4 months, 2014-03-11 to 2022-03-10, 2 dimensions,
  temporal order 1, 4 iterations, `scalar_search=local`, `engine-modern`
  (this repository, `main` at `c9a1a39`).
- Slices fixed from the calendar before any dimension-1 look:
  **P1 = unit 17** (2019-06-23 to 2019-10-17, the last unit entirely before
  the estallido social of 2019-10-18), **P2 = unit 20** (2020-06-23 to
  2020-10-25, ending at the constitutional plebiscite), **P3 = unit 24**
  (2021-11-06 to 2022-03-10, the end of the 55th legislative period).
- Membership: per-unit roster, party affiliation time-resolved.
- 200 replicates, master seed 20260826; 200/200 fits succeeded, none
  discarded. The first 20 replicates are the published pilot subset
  (seed-spawned, not re-fit).
- Sign convention: negative dimension 1 = left; the right bloc (UDI/RN/EVOP)
  is positive.

## Validation

- The simulation basis reproduces the engine's own log-likelihood from the
  exported state to 7e-9 relative.
- Refit-on-observed canary and repeat-refit determinism canary: both
  **bitwise identical**.
- Alignment: 3,265 anchor rows constant; 3/200 replicates came back globally
  reflected and were absorbed by the alignment (determinant -1, normal
  residuals afterwards).
- Estimated scalars stay near the observed fit across replicates
  (w2 0.525-0.535 against observed 0.527).
- **Dimension-2 fragility census:** 1/200 replicates landed in a different
  dimension-2 basin (replicate 13; dimension-1 unaffected). Dimension 1 never
  flipped. This is an incidental measurement of how weakly identified the
  second dimension is on this panel, and it is why no dimension-2 statistic is
  interpreted anywhere in this analysis.

## Median changes, with bootstrap uncertainty

`sign` = replicates sharing the majority delta sign. Read the drift-bias
section before reading percentile intervals: percentile CIs on changes are
shifted left by a known common tilt, so the **basic (bias-aware) intervals
carry the inference**. Full tables including basic CIs:
`summary/party_change_intervals.csv` and `summary/readout_n200.csv`.

### P1 to P2 (pre-estallido to plebiscite)

| party | delta | boot SE | sign | normal 95% | percentile 95% | verdict |
|---|---:|---:|---:|---|---|---|
| UDI | -0.0168 | 0.0159 | 181/200 | [-0.048, +0.014] | [-0.052, +0.008] | incl 0 |
| RN | -0.0017 | 0.0127 | 199/200 | [-0.027, +0.023] | [-0.052, -0.005] | incl 0 |
| RD | +0.0049 | 0.0109 | 125/200 | [-0.017, +0.026] | [-0.028, +0.014] | incl 0 |
| PC | +0.0057 | 0.0067 | 166/200 | [-0.007, +0.019] | [-0.020, +0.006] | incl 0 |
| PS | +0.0160 | 0.0073 | 135/200 | [+0.002, +0.030] | [-0.010, +0.016] | RIGHT |
| PPD | +0.0245 | 0.0133 | 160/200 | [-0.002, +0.050] | [-0.016, +0.033] | incl 0 |
| EVOP | +0.0356 | 0.0221 | 165/200 | [-0.008, +0.079] | [-0.064, +0.021] | incl 0 |
| DC | +0.0378 | 0.0125 | 140/200 | [+0.013, +0.062] | [-0.020, +0.029] | RIGHT |
| IND | +0.0473 | 0.0127 | 195/200 | [+0.022, +0.072] | [+0.000, +0.049] | RIGHT |
| PR | +0.0724 | 0.0073 | 200/200 | [+0.058, +0.087] | [+0.044, +0.074] | RIGHT |

### P1 to P3 (pre-estallido to end of term)

| party | delta | boot SE | sign | normal 95% | percentile 95% | verdict |
|---|---:|---:|---:|---|---|---|
| IND | -0.0938 | 0.0317 | 200/200 | [-0.156, -0.032] | [-0.173, -0.047] | LEFT |
| PPD | -0.0227 | 0.0260 | 194/200 | [-0.074, +0.028] | [-0.097, +0.002] | incl 0 |
| RN | -0.0144 | 0.0224 | 200/200 | [-0.058, +0.029] | [-0.122, -0.043] | incl 0 |
| UDI | +0.0126 | 0.0229 | 175/200 | [-0.032, +0.057] | [-0.069, +0.016] | incl 0 |
| PC | +0.0161 | 0.0154 | 153/200 | [-0.014, +0.046] | [-0.042, +0.016] | incl 0 |
| RD | +0.0303 | 0.0215 | 103/200 | [-0.012, +0.073] | [-0.051, +0.042] | incl 0 |
| PS | +0.0374 | 0.0130 | 153/200 | [+0.012, +0.063] | [-0.017, +0.035] | RIGHT |
| DC | +0.0882 | 0.0178 | 197/200 | [+0.053, +0.123] | [+0.008, +0.073] | RIGHT |
| EVOP | +0.0988 | 0.0427 | 168/200 | [+0.015, +0.183] | [-0.113, +0.047] | RIGHT |
| PR | +0.1690 | 0.0132 | 200/200 | [+0.143, +0.195] | [+0.122, +0.173] | RIGHT |

### P2 to P3 (plebiscite to end of term)

| party | delta | boot SE | sign | normal 95% | percentile 95% | verdict |
|---|---:|---:|---:|---|---|---|
| IND | -0.1411 | 0.0268 | 200/200 | [-0.194, -0.089] | [-0.191, -0.091] | LEFT |
| PPD | -0.0471 | 0.0232 | 200/200 | [-0.093, -0.002] | [-0.105, -0.017] | LEFT |
| RN | -0.0128 | 0.0147 | 200/200 | [-0.042, +0.016] | [-0.085, -0.030] | incl 0 |
| PC | +0.0104 | 0.0111 | 140/200 | [-0.011, +0.032] | [-0.026, +0.018] | incl 0 |
| PS | +0.0213 | 0.0086 | 154/200 | [+0.004, +0.038] | [-0.009, +0.022] | RIGHT |
| RD | +0.0254 | 0.0145 | 119/200 | [-0.003, +0.054] | [-0.026, +0.032] | incl 0 |
| UDI | +0.0294 | 0.0174 | 120/200 | [-0.005, +0.064] | [-0.041, +0.027] | incl 0 |
| DC | +0.0504 | 0.0131 | 198/200 | [+0.025, +0.076] | [+0.009, +0.057] | RIGHT |
| EVOP | +0.0632 | 0.0261 | 155/200 | [+0.012, +0.114] | [-0.068, +0.027] | RIGHT |
| PR | +0.0965 | 0.0072 | 200/200 | [+0.082, +0.111] | [+0.073, +0.099] | RIGHT |

## Drift bias, and its mechanism

Replicate refits carry a common leftward time-drift: the bootstrap-mean median
sits left of the observed median, monotonically more so in later slices, for
every party (per-party values in `summary/party_median_intervals.csv`, bias
column). The mechanism analysis (`drift/`) resolves it into two components:

1. **Amplitude inflation, ~5% on dimension 1.** Per-dimension no-intercept
   regression of observed on aligned replicate coordinates gives a mean scale
   of 0.9514 (sd 0.0071) on dimension 1 and 0.9257 (sd 0.0606) on dimension 2:
   refitting on pseudo-data systematically inflates amplitude, tightly on
   dimension 1, an order of magnitude looser on dimension 2.
2. **A common trend tilt.** The per-period mean dimension-1 shift of aligned
   replicates against the observed fit falls approximately linearly within
   each cohort's own time span and resets at the 2018 chamber boundary: the
   signature of inflated linear trend coefficients, not of a translation.

A global per-dimension rescaling (the amplitude gauge) removes most of the
bias on slice **levels** but leaves the bias on slice-to-slice **changes**
unchanged: cross-party mean delta bias is -0.017 (P1 to P2), **-0.040**
(P1 to P3), -0.023 (P2 to P3), scaled or not. The tilt is therefore treated
as a systematic bias of the refit procedure, of known size, and the
**bias-aware (basic) intervals carry the inference on changes**; percentile
intervals on changes are shifted left by approximately the tilt.

## Verdicts

Bias correction (observed delta minus delta bias, per party) leaves the
headline verdicts intact and removes exactly the readings already flagged:

1. **PR moves RIGHT, +0.169 from P1 to P3** (corrected ~ +0.192): pure
   movement by the same 6 deputies, 200/200 sign-consistent, the largest and
   most robust movement in the panel.
2. **DC moves RIGHT, +0.088 from P1 to P3** (corrected ~ +0.138; +0.075
   restricted to continuing members), 197/200.
3. **IND moves LEFT, -0.094 from P1 to P3, by composition**: continuing
   members move +0.079 right, so the leftward median shift is a change in who
   the independents are, not movement by the same people. 200/200.
4. **PPD P2 to P3 LEFT, -0.047**, clears both intervals, but continuing
   members move only -0.006: composition-driven, same caveat as IND.
5. PS shows a small rightward movement (+0.037, same members), unsettled
   between interval constructions. EVOP reads right but is noisy (SE 0.043,
   n = 6) and its correction is unreliable at that n.
6. **UDI, RN, PC, RD: no defensible direction.** For RN the delta bias
   (-0.070) is about 3 times the observed delta (-0.014) and sign-flips it
   under correction; UDI is in the same class. Their 200/200 sign
   consistencies are the common tilt, not evidence of movement.
7. **From P1 to P2 (the estallido window itself), no party moves left
   detectably.**

## Statistical footnotes

- Bootstrap SEs were already accurate at n = 20 (e.g. PR P1 to P3: 0.0132 at
  n = 200 vs 0.0131 at n = 20); no headline verdict changed between n = 20
  and n = 200.
- The empirical two-sided p floor at n = 200 is 1/201 = 0.005, so a Holm
  correction across the 30 reported cells cannot reach 0.05 (30 x 0.005 =
  0.15). That is a Monte Carlo resolution floor, not evidence weakness (PR's
  delta is ~13 SE). Printing Holm-significant results requires B >= 599.
- Interpretation constraints: order-1 linear trajectories cannot represent a
  step-and-revert path; no causal claims; dimension 2 is estimated but never
  interpreted.
