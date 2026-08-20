# data

Every panel any engine in this repository is run on. All four Chilean panels plus the two US panels
the comparison table uses.

| path | panel | shape | used by |
|---|---|---|---|
| `chile-dynamic/` | Chilean Chamber, legislaturas 346-368 | 23 periods, 340 legislators | the dynamic arm, `--periods=23 --model=2` |
| `chile-static/leg353/` | legislatura 353 | 1 period | static arm. Same bytes as period 8 of the dynamic panel |
| `chile-static/leg366/` | legislatura 366 | 1 period | static arm. Same bytes as period 21 |
| `chile-static/leg368/` | legislatura 368 | 1 period | static arm. Same bytes as period 23 |
| `us-sen90/` | US Senate, 90th Congress | 1 period, 102 legislators | the static confirmation arm |
| `us-dynamic-5p/` | US Senate, 5 congresses | 5 periods, 168 legislators | the dynamic confirmation arm, `--periods=5 --model=1` |

## File contract

Each panel directory carries the names the loader builds, not descriptive ones:

- `votes_matrix_p<N>.csv` — legislators as rows, roll calls as columns. `csv_loader` constructs this
  name from the period index, so a single-period panel must be `votes_matrix_p1.csv`.
- `legislator_metadata.csv` — the roster.
- `wnominate_coordinates.csv` — the W-NOMINATE seed. **The frame the seed supplies is the frame the
  fit keeps**, so this file is load-bearing, not a convenience. See `engine-faithful/SEEDS.md`.
- `chile-dynamic/wnominate_coordinates_per_period.csv` — per-(legislator, period) seeds. Canonical
  seeding is per-period, not one constant position per legislator.

**Vote codes are 1 = yea, 6 = nay, 9 = missing** in these matrices. The engines map 1-3 to yea, 4-6
to nay, and 0 or >6 to missing, so those literal codes are correct as written.

## Two things that were wrong here until 2026-08-20

**The metadata was a skeleton.** Every `legislator_metadata.csv` shipped with the `legislator_id`
column populated and `nombres`, `partido`, `region` and `distrito` empty. Party is what colours every
figure, so no one outside the authoring machine could regenerate one, and the figure scripts silently
read the real rosters from a sibling checkout by absolute path. Both are fixed: the rosters are real
here, and the scripts read this directory. Verified by regenerating all 20 map slots — the PNGs come
out byte-identical to the published ones.

**The US panels were absent entirely** while `results/` carried US arms and the comparison table
quoted them. They are here now.

## Provenance

The Chilean roll calls come from the QueVotan database, itself downstream of a scraper over the
Chilean Chamber of Deputies' published records. The US panels are Voteview roll-call data. The
W-NOMINATE seeds are produced by the `wnominate` R package on these same matrices.

The Chilean roster is one file replicated across the four Chilean panel directories, because all four
draw on the same 340-legislator roster keyed by `legislator_id` and the loader expects a copy beside
each vote matrix.
