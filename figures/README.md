# Figures

Unit-disk projection maps for every cell of the three-engine comparison, one directory
per panel. Rebuilt 2026-08-25 from a single run vintage; the previous flat tree of 104
files at this level was replaced.

## Layout

```
figures/
  dynamic/
    chile-dynamic-23p/      23 periods, quadratic
    us-dynamic-5p/          Senates 111-115, linear
  static/
    chile-static-leg353/
    chile-static-leg366/
    chile-static-leg368/
    us-static-sen90/
```

Each panel directory holds, per engine:

| file | what it is |
|---|---|
| `disk-<engine>.pdf` / `.png` | the paper form. Monochrome, category by marker shape |
| `party-<engine>.pdf` / `.png` | the same placements coloured by party, with a labelled cross at each party centroid. A **working diagnostic**, not the paper form |
| `trajectories-<engine>.pdf` / `.png` | dynamic panels only. Each legislator's fitted polynomial drawn continuously over their served span |
| `MANIFEST.csv` | source artifact, roster counts, frame, and the numbers depicted, per figure |

`<engine>` is one of:

| file name | arm in the run tree | what it is |
|---|---|---|
| `fortran` | `fortran` | the canonical `DW-NOMINATE-wmay.f` reference |
| `faithful` | `adhoc` | `engine-faithful`, the C++ port of the ad hoc searches |
| `modern` | `nlopt` | `engine-modern`, derivative-free NLopt solvers |

There is no `trajectories-fortran`: the Fortran harness exports no per-legislator
effective degree, so its polynomial cannot be reconstructed. Rather than infer a degree
from the served span inside a figure, the generator refuses.

## Provenance

Every figure here comes from one run directory, produced by
`reproduce/scripts/isolation_matrix.py` on the panels in `data/`, four outer cycles, one
thread. Five of the six panels reproduce bit-identically against the preceding vintage;
only `us-dynamic-5p` moved, because its seed was regenerated the same day. Each
`MANIFEST.csv` names the run root and the source file, relative, never absolute.

## Two things to know before reading a dynamic map

**The unit disk bounds a static panel exactly and does not bound a dynamic one.** The
estimator constrains the Legendre *constant* term, not the reconstructed per-period
placement, so a trajectory with large linear or quadratic terms can leave the circle.
Measured here: all four static panels sit at max radius 1.0000 with zero placements
outside, while `chile-dynamic-23p` puts 52 of 161 outside at its terminal period. The
canonical Fortran does the same, and by the same amount. Each figure records its own
`outside_disk` and `max_radius` in the manifest.

The effect is structural in the model order. On this panel, at four cycles, terminal
placements outside the disk run **0** at constant, then 54, 52 and 46 at linear,
quadratic and cubic. The constant case is exactly zero because a degree-0 curve *is* the
bounded constant term.

**Dimension 2 is plotted at unit scale but enters the model at weight `w2` of about
0.35.** Separation read off these maps overstates its role by roughly 3x in distance and
8x in the model's squared metric. The maps are deliberately drawn unweighted, which is
the published convention for this literature; any statistic that computes a distance
between legislators must apply the weight.
