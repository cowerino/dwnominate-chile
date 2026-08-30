# Second-dimension recovery against a known truth, by information content

Run 2026-08-21. Each engine is scored against the generating configuration of the three synthetic
panels in `data/synthetic-2d/`, so "collapse" of dimension 2 is measured against a right answer
rather than against another engine.

## Result

| dim-2 cleavages | engine | r2 | ampl.2 | polarity |
|---|---|---|---|---|
| **Strong** 363/715 (50.8%) | faithful | 0.9921 | 0.961 | 3.9% |
| | modern (local box) | 0.9911 | 1.025 | 3.2% |
| | modern (global box) | 0.9877 | 0.755 | 4.3% |
| **Moderate** 157/715 (22.0%) | faithful | 0.9692 | 0.843 | 13.0% |
| | modern (local box) | 0.9735 | 0.889 | 11.5% |
| | modern (global box) | 0.9635 | 0.658 | 12.0% |
| **Weak** 63/715 (8.8%) | faithful | 0.2424 | 0.792 | 45.5% |
| | modern (local box) | 0.7128 | 0.882 | 28.5% |
| | modern (global box) | 0.7123 | 0.511 | 33.3% |

`r2` is the Procrustes-aligned dimension-2 correlation with truth, `ampl.2` the recovered
dimension-2 sd over the true sd after that rotation, and `polarity` the share of roll calls whose
fitted dimension-2 spread sign disagrees with the truth (polarity is a free global gauge, so the
better of the two orientations is taken).

Dimension 1 is essentially unaffected across the whole ladder: every arm recovers it at r1 between
0.987 and 0.996. What degrades is dimension 2, and it degrades with how much dimension-2 information
the record carries.

Each `recovery-*.csv` also carries a `SEED (votes-only start)` row, the double-centred SVD the
engines all start from. It is not in the table above because it is an input, not a result.

## Verify it

    python reproduce/score_synthetic_recovery.py strong
    python reproduce/score_synthetic_recovery.py moderate
    python reproduce/score_synthetic_recovery.py weak

Each run rescores the committed arms in `arms/` against the committed panels in
`data/synthetic-2d/`, writes to `reproduce/_out/`, and compares against the `recovery-*.csv` here,
printing MATCHES or DIFFERS and exiting non-zero on a mismatch. It needs no engine build. Checked
2026-08-30: all three match to within 2e-15.

To regenerate the panels themselves rather than trust them, see `data/synthetic-2d/README.md`.

## What is here

- `recovery-{strong,moderate,weak}.csv` — the scored rows, one per arm.
- `arms/<rung>/{faithful,modern-local,modern-global}/` — the fitted coordinates and bill parameters
  each engine produced. These are what the scorer reads, so the table is verifiable without building
  an engine.

## How the arms were run

All nine runs share the panel, the votes-only start, and the estimation settings. Only the search
differs.

    model 0 (constant), 4 iterations, 1 period, 2 dimensions, beta 5.9539, initial w2 0.3463, 1 thread

- `faithful` — the reference-faithful engine.
- `modern-local` — the modern engine, `--scalar-search=local --block-solver=slsqp`. Scalar parameters
  confined to the local box.
- `modern-global` — identical except `--scalar-search=global`, a wider experimental box for the
  scalar parameters. Reported elsewhere as the "unbounded" arm, which oversells it: it is a wider
  box, not an unbounded search.

## Caveat on the ladder

The three rungs vary the dimension-2 cleavage share **and** the generating `w2` together, and the
strong rung uses a different seed from the other two. Read `data/synthetic-2d/README.md` before
describing this as a one-factor design.
