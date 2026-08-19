# Chilean static roll calls, as used in the static tests

Cámara de Diputados de Chile. Three single-period panels, one directory each.

| directory | legislatura | roll calls | rows in the matrix |
|---|---|---|---|
| `leg353/` | 353 | 298 | 340 |
| `leg366/` | 366 | 716 | 340 |
| `leg368/` | 368 | 1023 | 340 |

## Files, per directory

- `votes_matrix.csv` — the roll call. First column is `legislator_id`, one column per roll call.
  Codes are the NOMINATE convention: **1-3 yea, 4-6 nay, 7-9 missing.** Abstentions,
  dispensations and absences are all coded missing.
- `wnominate_coordinates.csv` — the W-NOMINATE starting coordinates (the seed).
- `legislator_metadata.csv` — identifiers. **Party fields are empty in this export**; party labels
  live in the QueVotan reference, not here.

## Two things that matter before comparing anything

1. **The matrix is padded.** All three periods carry an identical 340-row roster whether or not the
   legislator served. Only **2,855** of the 7,820 (legislator, period) cells in the full 23-period
   panel are served. Restrict to rows with at least one code in 1-6 before computing anything, or
   the padding will flatter agreement.
2. **The screen is applied inside the engine, not here.** A roll call enters the estimation only if
   its minority side reaches 2.5 % of those voting and its spread is non-zero. On the full
   23-period panel that removes 6,094 of 12,952 roll calls (47.1 %), leaving 6,858 carrying 692,839
   votes. The 2.5 % rule alone reproduces the retained set exactly; the non-zero-spread condition
   binds nowhere on this panel.

## The commands we ran

Static, single period, two dimensions, four iterations, no temporal model:

```
dwnominate --input-dir=<dir> \
           --wnominate=<dir>/wnominate_coordinates.csv \
           --model=0 --iterations=4 --periods=1 --dimensions=2 \
           --output-dir=<out>
```

## What we get on these panels

Our engine against the 2004 Fortran on the same panel, orthogonal Procrustes without scaling:

| legislatura | `r1` | `r2` | mean 2-D distance | amplitude |
|---|---|---|---|---|
| 353 | 0.9981 | 0.9896 | 0.0690 | 1.0077 |
| 366 | 0.9994 | 0.9936 | 0.0335 | 1.0108 |
| 368 | 0.9991 | 0.9841 | 0.0497 | 0.9892 |
