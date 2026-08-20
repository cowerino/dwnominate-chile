# Three-engine disk maps, 2026-08-19

**Working comparison artifact, for judging by eye. Not paper figure candidates.** These deliberately
ignore the paper's monochrome convention (`../../CONVENTION.md`) because party colour is what makes
them readable. Nothing here is a design decision.

Generator: `$CLAUDE_JOB_DIR/tmp/maps2.py`. Re-analysis only, no engine run.

## Files

Four panels x (three individual maps + one three-column combined with a party legend).

| panel | individual | combined |
|---|---|---|
| US Senate 90 | `us_sen90_{fortran,ours,modern}.png` | `us_sen90_all3.png` |
| Chile, Chamber, leg 368 | `chile_leg368_{fortran,ours,modern}.png` | `chile_leg368_all3.png` |
| Chile, Chamber, leg 366 | `chile_leg366_{fortran,ours,modern}.png` | `chile_leg366_all3.png` |
| Chile, Chamber, leg 353 | `chile_leg353_{fortran,ours,modern}.png` | `chile_leg353_all3.png` |

Agreement statistics for every arm are in `agreement_stats.csv`.

## The unit-circle constraint. Corrected 2026-08-19

**An earlier version of these maps showed points outside the disk. That was a plotting artifact and
it has been removed.** The first pass centred each configuration before drawing. The Chilean
configuration has a real centroid offset of about **0.21** from the origin, because DW-NOMINATE
constrains the **radius, not the centroid**, so centring shifted every point by that much and pushed
boundary-pinned legislators outside the drawn circle.

**Measured on the raw coordinates, the constraint holds in all three engines:**

| panel | engine | max radius | n |
|---|---|---|---|
| sen90 | 2004 Fortran | **1.000228** | 102 |
| sen90 | ours | **1.000000** | 102 |
| sen90 | modern | **1.000000** | 102 |
| leg 366 | 2004 Fortran | **1.000558** | 155 |
| leg 366 | ours | **1.000000** | 155 |
| leg 366 | modern | **1.000000** | 155 |

Both C++ engines hard-project and never exceed 1. The Fortran permits a handful marginally outside,
by at most ~5.6e-4, which is invisible at plotting resolution and is the behaviour already recorded
in `../../../ENGINE-VERIFICATION-SUMMARY.md` §7. Points sitting exactly *on* the circle are pinned to
the boundary, not violations; rim occupancy is high in static Chilean fits (§7 records 36 % above
radius 0.98 on leg 353).

**These maps are therefore drawn from raw coordinates.** Ours and modern are rotated and reflected
onto the Fortran, with the rotation solved on the centred clouds and then **applied to the raw
coordinates**. A rotation about the origin preserves `|x|` exactly, so the circle means what it says
and amplitude differences remain visible. No scaling, no translation.

## Reading them

Colour is party. US: 100 Democrat blue, 200 Republican red. Chile: right-bloc blues (UDI, RN, EVOP),
centre ambers (DC, PPD, PRad), left reds (PS, PC), Frente Amplio greens (RD, CS, FRVS), grey for
independent or unlabelled. The combined images carry the legend.

- **sen90 and leg 353** are the easy cases. All three engines land on the same map.
- **leg 366 is the one to look at.** Modern's `r2` collapses to **0.677** against ours at 0.9936, and
  the picture shows the mechanism: modern pulls rim legislators inward. That is COBYLA linearising
  the ball constraint, anomaly 4 in `../../../ENGINE-VERIFICATION-SUMMARY.md` §6.
- **leg 368** is where both C++ engines agree with the Fortran while all three disagree with
  W-NOMINATE, which is §6d of `../../../findings/FINDING-chile-static-and-period-structure-2026-08-18.md`.

## Why static panels

All four are single-period fits, deliberately. On a static panel every legislator serves the whole
span, so global `t` and local `t` coincide by construction and the **export-frame defect cannot
bite**. A dynamic panel would need `load_coords_local` and a period choice first.

## Sources

| arm | US Senate 90 | Chile static |
|---|---|---|
| Fortran | `quevotan-db/reproduce/fortran/build_2004/run_static_sen90/us_legout.dat` | `.../run_static_chile_p{8,21,23}/us_legout.dat` |
| ours | `quevotan-api/nominate_cmodule/benchmarks/sen90/out_seedA_postfix77/` | `quevotan-db/reproduce/out/chile/static_panels/p{8,21,23}/out_ours/` |
| modern | `.../sen90/out_seedA_modern77/` | `.../static_panels/p{8,21,23}/out_modern/` |

p8 = leg 353, p21 = leg 366, p23 = leg 368.

## Correction, 2026-08-20: the modern arm is pre-fix, and the leg 366 attribution is not settled

**The `modern` maps here were produced by a pre-fix build.** Provenance, established by tracing the
outputs back to the binary:

- No `modern` output on disk carries the `scalar_search` row that the current engine writes
  unconditionally into `cpp_summary.csv`.
- The `[UC5TRACE]` lines in every `modern` run log show the scalar search on **global** bounds,
  `w2 [0, 1.5]` and `beta [0.05, 25]`, not the re-centred local box the current engine defaults to.
- The runs are stamped 2026-08-17; the fixed `dwnominate-modern.exe` was built 2026-08-19 23:06 and
  has not been run against these panels.

**Beta's first-cycle exit tracks the disagreement exactly.** Reading `idx=2` out of the same logs:

| panel | beta, cycle-1 exit | at the floor? | modern `r2` | ours `r2` |
|---|---|---|---|---|
| US Senate 90 | 0.160069 | no | 0.9952 | 0.9993 |
| leg 353 | 0.784596 | no | 0.9802 | 0.9896 |
| leg 368 | **0.050000** | **yes, exactly** | 0.9348 | 0.9841 |
| leg 366 | **0.050000** | **yes, exactly** | **0.6772** | 0.9936 |

The two panels where beta is pinned to its global lower bound in the first cycle are the two worst
modern arms; the two where it is not are the two best. That is the failure the current engine's
local scalar box was written to prevent: an exact conditional solve on the crude first-cycle state
sends beta to its bound and changes the basin of every later block.

**So the "COBYLA linearising the ball constraint" reading above is not supported by this evidence
and should not be quoted.** It is also not refuted: four panels with a clean rank separation is
suggestive, not decisive, and the two explanations are not exclusive. The test that settles it is a
re-run of these four panels with the current engine under `--scalar-search=local` and again under
`--scalar-search=global`. Until that runs, treat the modern arm here as a property of a superseded
build rather than of the modern engine.
