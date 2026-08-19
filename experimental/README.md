# experimental/

**Nothing in this directory is the paper's engine. Do not build these for results.**

Both trees predate the 2026-08-15 alignment fix. They are kept because the benchmark thresholds are
calibrated against them and because the second one records a measured negative result that is worth
more than its outcome.

| tree | commit | what it is |
|---|---|---|
| `f01e747-prefix-trunk/` | `f01e747`, 2026-06-13 | the pre-fix trunk. **This is the "known bad" build** the validation suite is calibrated to separate from the corrected one |
| `e27ec21-prefix-projections-restored/` | `e27ec21`, 2026-08-06 | trunk plus the REQ-004 roll-call midpoint unit-sphere projection restored, and `unmerged-patches/` |

## What is wrong with them

The defect is a coordinate/vote misalignment in the `CUTPLANE` caller. `prepareRollCallData` filled
the coordinate and vote arrays in legislator order, computed the projection order, then reordered
**only** the vote array. The one-dimensional branch compensated; the two-dimensional branch passed
both straight to `CUTPLANE`, which classified a shuffled pairing. Corrected in `../engine-faithful/`.

On the 23-period Chilean panel the log-likelihood gap to the Fortran falls from **26,609 nats to
34.3** and classification from **2.99 points to 0.02** once fixed.

## Why the second tree exists

`e27ec21` restores all three unit-ball projection sites. That change is **right** and it is in
`engine-faithful/`, but the argument originally given for removing them was wrong twice over: the
constraint is real and lives one level up, in the grid search that calls the likelihood evaluator
rather than in the evaluator itself, and the reference rows read as out-of-ball midpoints in fact
interleave a spread with a midpoint. Restoring the projections on the *defective* build makes
agreement **worse**, which is why this tree is a negative result and not a fix.

`unmerged-patches/` holds work on neither tree: the REQ-004 restore as a patch, and an unevaluated
`normal_cdf` divergence.
