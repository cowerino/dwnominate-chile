# Per-party ideal-point maps, 2026-08-20

Generator: `../../generators/map_party.py`, drivers `_render_party_maps.py` (static) and
`_render_party_maps_dyn.py` (dynamic). PDF + PNG.

**Form.** One small map per party. Each facet draws the full panel in light grey for context and
that party's members in the party's colour. Identity is carried by the **facet label**; the colour
only reinforces it.

**Why faceted rather than one coloured scatter.** On a scatter the colour separation gates apply to
all pairs, not just adjacent ones, and only three categorical slots clear them. A six-party single
scatter FAILS outright, measured, not guessed:

    node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4,#008300" --mode light --pairs all
    [FAIL] CVD separation      worst #008300<->#eb6834 dE 3.2 (protan)
    [FAIL] Normal-vision floor worst #e87ba4<->#eb6834 dE 12.9  (below the 15 floor)

Faceting removes the problem instead of arguing with it: each panel holds exactly one coloured
category, so no confusable pair is ever formed.

**Convention note.** `../../CONVENTION.md` N1 is monochrome with category by marker shape. It is
suspended here by Roberto's instruction, **for discussion maps only, not for paper floats**. The
reasoning behind N2 is untouched: N2 forbids encoding an *estimated signed position* as a ramp,
because that asserts the identification the paper denies. Party is an **external categorical
label**, not an estimated coordinate, so colouring by it asserts nothing about the frame. It is the
independent attribute the map's coherence is judged against. Kept from the convention: no numeric
annotation inside any figure, axis titles once for the grid, bare facet labels, white panel with
light grey grid and a dark border on all four sides.

**Alignment.** Rotation about the origin only, no translation and no scaling, so the unit circle
stays meaningful (DW-NOMINATE constrains the radius, not the centroid). C++ arms are rotated onto
the Fortran; the Fortran is drawn in its own frame. Dynamic panels use ONE global rotation fitted on
all 2,855 served placements, then sliced by period.

## Files

| file | panel | engine |
|---|---|---|
| `map-leg{353,366,368}-fortran` | static, fitted alone | 2004 Fortran, the reference |
| `map-leg{353,366,368}-ours` | static, fitted alone | C++ engine-faithful |
| `map-leg{353,366,368}-modern-global` | static, fitted alone | engine-modern, global scalar search |
| `map-leg{353,366,368}-modern-local` | static, fitted alone | engine-modern, local trust region |
| `mapdyn-leg{353,366,368}-{fortran,ours}` | cross-section of the 23-period dynamic fit | as labelled |

The static and dynamic maps of the same legislatura are directly comparable: same roster, same
alignment convention, same drawing code.

## Provenance

- Static C++ arms: re-run 2026-08-20 on the current binary (post absence-fix, post exporter-fix).
  Likelihoods -1132.023505 / -6276.201346 / -13300.413955.
- Dynamic C++ arm: `expfix_dyn`, LL -98603.656973, **2,855 exported rows** (served only) from the
  fixed exporter. No frame reconstruction is applied or needed.
- Party labels: `quevotan-db/reproduce/input/legislator_metadata.csv`, 337 of 340 populated, one
  stable party per legislator (no legislator has more than one party in `partidos_history`).
- ⚠ The `modern` arms carry the standing provenance blocker: that tree is not a git repository and
  the binary that produced them is not the one on disk.
