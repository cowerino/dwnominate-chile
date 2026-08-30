# synthetic-2d

Three synthetic panels whose second dimension is **real by construction**, used to decide whether a
collapsing second dimension is an implementation defect or a property of the data.

On real records the engines disagree about dimension 2, and no comparison between engines can settle
why, because none of them knows the right answer. These panels supply one. Votes are drawn from the
estimator's own model, so a correct implementation must be able to recover the generating
configuration, and the number of roll calls that actually discriminate along dimension 2 is fixed by
construction rather than estimated from a fit.

Scored results are in `results/2026-08-21-synthetic-dim2-ladder/`.

## The three rungs

| rung | dim-2 cleavages | generating `w2` | seed |
|---|---|---|---|
| `strong/` | 363 of 715 (50.8%) | 0.50 | 20260821 |
| `moderate/` | 157 of 715 (22.0%) | 0.40 | 4242 |
| `weak/` | 63 of 715 (8.8%) | 0.30 | 4242 |

**On the names.** `strong` / `moderate` / `weak` describe the dimension-2 *information*
*content* of each panel, not the quality of anything. They are kept as-is deliberately: the
directory names are referenced by `reproduce/score_synthetic_recovery.py` and by the committed
results, and renaming buys nothing now that this experiment is no longer carried in the paper.

**Read the table before describing the ladder.** The rungs are not a one-factor design. Two things
weaken together across them, the share of dim-2 cutting planes **and** the generating second-dimension
weight, and `strong` additionally uses a different seed, so its underlying configuration of ideal
points is not the same one `moderate` and `weak` share. The ladder is a dose-response demonstration
that dim-2 recovery degrades as dim-2 information weakens; it is not an experiment that isolates the
cleavage share on its own.

## Regenerating them

Every panel here is reproducible byte-for-byte from `reproduce/make_synthetic_2d.py`:

    python reproduce/make_synthetic_2d.py --out reproduce/_out/regen/strong
    python reproduce/make_synthetic_2d.py --w2 0.40 --dim2-share 0.25 --seed 4242 --out reproduce/_out/regen/moderate
    python reproduce/make_synthetic_2d.py --w2 0.30 --dim2-share 0.12 --seed 4242 --out reproduce/_out/regen/weak

(`strong` is the script's default configuration, so it needs no flags.) Verified on 2026-08-30:
all five files in each of the three rungs come out MD5-identical to what is committed here. If yours
differ, that is a finding worth reporting rather than a nuisance, and the likely cause is a NumPy
version whose `default_rng` stream has changed.

## File contract

Same contract as every other panel in `data/`, plus two truth files that only synthetic panels have:

- `votes_matrix_p1.csv` — legislators as rows, roll calls as columns. **1 = yea, 6 = nay, 9 = missing.**
- `legislator_metadata.csv` — the roster. Synthetic, so the descriptive columns are deliberately empty.
- `wnominate_coordinates.csv` — the start. **Not** a W-NOMINATE run: it is a double-centred SVD of the
  agreement matrix, computed from the votes alone, so it is identical for every engine and carries no
  knowledge of the truth. Seeding from the truth would answer the wrong question.
- `truth_coordinates.csv` — `legislator_id, true_d1, true_d2`. The generating ideal points.
- `truth_bill_parameters.csv` — `rollcall_id, true_midpoint1D/2D, true_spread1D/2D, dim2_oriented`.
  `dim2_oriented` marks the roll calls deliberately drawn to cut along dimension 2.

## Panel construction, in one paragraph

155 legislators and 716 roll calls, sized to a real Chilean legislatura. Ideal points are two loosely
separated blocs on dimension 1 (means -0.45 and +0.45, sd 0.22) plus an **independent** dimension 2
of comparable spread (sd 0.40), rescaled into the unit disk. Independence is the point: dimension 2
must not be recoverable from dimension 1. Cutting planes get uniformly distributed normal directions,
except for a `--dim2-share` fraction drawn to cut near the dimension-2 axis. Votes come from the
estimator's own model at beta 6.0 with a 6% missing rate. Roll calls failing a 2.5% minority screen
are dropped, which is what takes 716 down to 715.

## The starting values already carry a correct dimension 2

`wnominate_coordinates.csv` correlates with the truth at roughly +0.96 (strong), +0.81 (moderate) and
+0.18 (weak) on dimension 2. That **sharpens** the test rather than weakening it: an engine that
collapses dimension 2 starting from a correct position, on data that genuinely has one, is defective
by elimination. An engine that preserves it here while collapsing on a real record is instead telling
you the real record's second dimension is weak.
