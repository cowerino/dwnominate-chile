# Chilean expanding-window dynamic fits

Three dynamic DW-NOMINATE fits over an **expanding window**, each stopping at one of
the three sub-period boundaries of Chile's 55th Legislative Period:

| window | ends at | boundary event |
| :--- | :--- | :--- |
| A | P1 | start of the period, to the *estallido* of 2019-10-18 |
| B | P2 | *estallido*, to the national plebiscite of 2020-10-25 |
| C | P3 | plebiscite, to the end of the period, 2022-03-10 |

Each window's terminal placement is the estimate an analyst could have produced **in
real time**, with no knowledge of anything after that date. Comparing them separates
the **frame effect** (the same sub-period seen through different windows) from the
**time effect** (different sub-periods within one fit). A per-period static design
cannot tell those apart.

`chile-dynamic-23p/` is the global run over the whole available history. The
`chile-expanding-*` directories are these scoped runs.

## How a dynamic result is allowed to be plotted

A dynamic coordinate at an intermediate period is a point on a *fitted polynomial*,
not an independent per-period measurement. Every figure here shows one of exactly two
things and never anything in between:

- a **terminal** position, where the trajectory stops being an interpolation and
  becomes the thing the window was fitted to, or
- the **complete route**, where the polynomial is visible as a polynomial.

## Model order

All figures are at **requested order 1**. The degree cap is per legislator, so a
requested order of 2 leaves a grid change free to reshuffle how many members are
fitted linear against quadratic, and an amplitude difference between two grids then
reads as a width effect when it is a degree effect. Holding the requested order at 1
removes that confound: the cap binds identically on every grid here.

## The five grids

All at identical engine settings, differing only in how the calendar is cut into time
units. Read them together rather than picking one.

| directory | units | min-votes |
| :--- | ---: | ---: |
| `chile-expanding-annual-7u` | 7 | 50 |
| `chile-expanding-equalcount-28u` | 28 | 20 |
| `chile-expanding-4month-24u` | 24 | 20 |
| `chile-expanding-4month-24u-mv12` | 24 | 12 |
| `chile-expanding-3month-31u` | 31 | 12 |

⚠ The annual grid is the only one at min-votes 50 and the one where the sub-5-period
degree cap freezes the most members, so it differs from the others in more than one
way at once. It is a different specification, not a data point about unit width.

⚠ The 3-month grid contains the summer recess quarter, which has 19 roll calls
surviving the lopsidedness screen. It is the only unit in any grid here whose
**dimension-1** orientation could not be pinned against the seed reference.

## Frame

Three separate fits are identified only up to an orthogonal transform. They are placed
in one frame by an **uncentred orthogonal Procrustes** (rotation and reflection about
the origin, no translation and no scaling) estimated on the warm-up units, which are
identical inputs in all three windows. Without a declared alignment, a segment joining
two windows' centroids would assert a comparability the estimator never promised.

## Display is unweighted

Both axes are drawn at unit scale on a circle of radius 1, but dimension 2 enters the
model at weight `w2`, which these fits put near 0.52. Separation read off the vertical
axis therefore overstates its role by roughly 2x in distance and 4x in the model's
squared metric.

## What dimension 2 will and will not carry

**Dimension 1 is robust across every grid here. Dimension 2 is not.** Cross-grid
position agreement is r 0.988 to 0.999 on dimension 1 in every window. On dimension 2
the same comparison runs far lower and the direction of a party's travel agrees across
grids at close to the rate of a coin toss. Read the horizontal movement in
`disk-movement`; do not read the vertical movement without checking the numbers in
`quevotan-db`.

The reason is measured rather than asserted: `w2` near 0.52 means dimension-2
displacement enters the objective at about 0.28, only a fifth of roll calls
discriminate mainly on dimension 2 once weighted, and total discriminating power runs
about 3.3:1 in dimension 1's favour. That leaves dimension-2 orientation nearly free.

## Data

Roll calls from Fabrega, *Data in Brief*, December 2025
(DOI `10.1016/j.dib.2025.112163`; Harvard Dataverse `10.7910/DVN/FOXOIT`), dated
against the Chilean Chamber's open-data service
(`WSLegislativo.asmx/retornarVotacionesXAnno`), which resolves all 3520 roll-call
columns. A roll call is dropped when the minority side is at or under 2.5 per cent of
votes cast.

`MANIFEST.csv` in each directory records the source, frame, settings and terminal unit
for every figure. `units.csv` records the panel construction. `party-summary.csv`
records the per-party terminal statistics behind the ridge figures.
