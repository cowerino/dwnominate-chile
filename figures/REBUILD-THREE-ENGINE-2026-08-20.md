> ## RESOLVED 2026-08-20: dynamic modern maps rebuilt with a served-pair filter
>
> Both defects below are fixed in `generate_modern_maps.py`, which now calls `filter_served()` on
> every arm before slicing. Rebuilt cross-sections match `engine-faithful` exactly: 121 / 155 / 161
> points for legs 353 / 366 / 368 and 105 for `us-dyn-p5`; the career maps now average 8.45 periods
> per Chilean legislator and 3.11 per US senator, not 23.00 and 5.00. Static panels were never
> affected and the filter is inert on them.
>
> **Second defect, found while verifying: a polarity flip between the two modern figure sets.** The
> interim set under `figures/rerun-2026-08-20/` was filtered from the **raw** export, whose sign is
> the negation of the `_corrected` export. Checked: keys identical, and every coordinate matches
> after negation to `0.00e+00`, correlation exactly `-1.000000`. It is the same run, mirrored, not a
> different one. `orient_dim1()` pins dimension 1 by party but nothing pins dimension 2, so the two
> sets rendered as vertical mirrors of each other. The interim directory has been removed; the
> top-level slots are canonical because they read the same `_corrected` export as the `ours` figures.
>
> **Rule going forward: every engine in a comparison series reads
> `cpp_coordinates_all_periods_corrected.csv`, never the raw export.** Mixing the two silently
> mirrors a map, and dimension-2 polarity is not corrected downstream.

> ## The Fortran dynamic export is padded too, rebuilt 2026-08-20
>
> Same defect, same fix. The canonical Fortran coordinate export carries **7,820** rows on the
> Chilean dynamic panel against 2,855 served cells, so the published `cl-dyn-*-fortran` slots were
> drawn with 340 points per cross-section instead of 121 / 155 / 161. Rebuilt via
> `generate_fortran_dyn_maps.py`. Static Fortran slots were never padded and are untouched.
>
> Filtering changes the Fortran's own out-of-disk story: **244 outside (3.12 %, max r 2.1089)
> unfiltered, against 68 (2.38 %, max 1.4694) on the served cells.**
>
> **Dimension-2 gauge against the Fortran is ambiguous on this panel**: its career-level dim-2
> correlates `r = -0.02` with `engine-faithful`. The polarity guard deliberately does **not** fire
> below `|r| = 0.3`, because flipping on the sign of a near-zero correlation is arbitrary. Treat any
> Fortran-versus-C++ dimension-2 comparison on this panel as unresolved until the export frames are
> reconciled: this Fortran export is labelled `global` while our corrected C++ export is at local t.

## Original defect report, kept for the record

> ## STOP: the dynamic engine-modern maps are contaminated and must be rebuilt
>
> `engine-modern` lacks the export-frame fix. On the Chilean dynamic panel it emits **7,774** rows
> against `engine-faithful`'s **2,855**; the extra 4,919 are placements for (legislator, period)
> pairs the member never served, and its `..._corrected.csv` is identical to its raw export.
>
> Measured effect on the figures already rendered:
>
> | figure | faithful points | modern points | phantom |
> |---|---:|---:|---:|
> | `cl-dyn-leg353-modern-*` | 121 | 338 | 217 (64 %) |
> | `cl-dyn-leg366-modern-*` | 155 | 338 | 183 (54 %) |
> | `cl-dyn-leg368-modern-*` | 161 | 338 | 177 (52 %) |
> | `cl-dyn-carrera-modern-*` | mean over 8.45 periods | mean over 23.00 | every average contaminated |
>
> **Fix:** build the served-pair key set from the matching `engine-faithful` export
> (`cpp_coordinates_all_periods_corrected.csv`, columns `legislator_id` and `period`) and inner-join
> every `engine-modern` dynamic export to it before plotting or averaging. The static panels are
> unaffected. Likelihoods, weights and timings are unaffected: the optimiser already uses served
> spans, so this is an export defect only.

# Figure rebuild playbook (one map per figure)

This document is the handoff for an external agent to regenerate figures from the published
three-engine results while preserving the current convention in this repository:

- One disk map per figure.
- PDF + PNG for each figure.
- File naming stays slot-based (panel + engine), no multi-panel montages.

## 1) Source of truth

Use outputs from:

- results/2026-08-20-three-engine/

Use `cpp_coordinates_all_periods_corrected.csv` for maps.

## 2) Engine-to-arm mapping

Use this mapping consistently:

- fortran: existing Fortran coordinate exports already used by current figures.
- ours: results/2026-08-20-three-engine/<panel>/faithful/cpp_coordinates_all_periods_corrected.csv
- modern-local: results/2026-08-20-three-engine/<panel>/modern-ltr-local/cpp_coordinates_all_periods_corrected.csv
- modern-global: results/2026-08-20-three-engine/<panel>/modern-ltr-global/cpp_coordinates_all_periods_corrected.csv

Notes:

- `modern-audit-*` is numerically identical to `modern-ltr-*` for the Chile panels in this capture.
  Use `modern-ltr-*` as canonical for publication.
- Keep party coloring and orientation policy from figures/README.md.

## 3) Panel mapping

Static panels:

- cl-static-leg353 <= chile-static-p8
- cl-static-leg366 <= chile-static-p21
- cl-static-leg368 <= chile-static-p23
- us-static-sen90 <= us-sen90-static

Dynamic panels:

- cl-dyn-leg353 <= chile-dyn-m2 filtered to period 8
- cl-dyn-leg366 <= chile-dyn-m2 filtered to period 21
- cl-dyn-leg368 <= chile-dyn-m2 filtered to period 23
- cl-dyn-carrera <= chile-dyn-m2 mean coordinates per legislator across served periods
- us-dyn-p5 <= us-dyn-5p using all periods
- us-dyn-carrera <= us-dyn-5p mean coordinates per legislator across served periods

## 4) Required output filenames

Keep existing files. Add modern variants with explicit suffixes:

Chile static:

- cl-static-leg353-modern-local.{pdf,png}
- cl-static-leg353-modern-global.{pdf,png}
- cl-static-leg366-modern-local.{pdf,png}
- cl-static-leg366-modern-global.{pdf,png}
- cl-static-leg368-modern-local.{pdf,png}
- cl-static-leg368-modern-global.{pdf,png}

US static:

- us-static-sen90-modern-local.{pdf,png}
- us-static-sen90-modern-global.{pdf,png}

Chile dynamic:

- cl-dyn-leg353-modern-local.{pdf,png}
- cl-dyn-leg353-modern-global.{pdf,png}
- cl-dyn-leg366-modern-local.{pdf,png}
- cl-dyn-leg366-modern-global.{pdf,png}
- cl-dyn-leg368-modern-local.{pdf,png}
- cl-dyn-leg368-modern-global.{pdf,png}
- cl-dyn-carrera-modern-local.{pdf,png}
- cl-dyn-carrera-modern-global.{pdf,png}

US dynamic:

- us-dyn-p5-modern-local.{pdf,png}
- us-dyn-p5-modern-global.{pdf,png}
- us-dyn-carrera-modern-local.{pdf,png}
- us-dyn-carrera-modern-global.{pdf,png}

Total new outputs: 20 map slots x 2 formats = 40 files.

## 5) Minimal generation algorithm

For each source coordinate file:

1. Load columns: `legislator_id`, `period`, `coord1D`, `coord2D`.
2. Build the requested slice:
   - static: use all rows (single period)
   - dynamic leg slice: filter by target period
   - carrera: group by legislator_id and average coord1D/coord2D over available periods
3. Join party metadata used by current pipeline (same metadata source as existing figures).
4. Apply current orientation/gauge rule from figures/README.md.
5. Render disk map with party colors and unit circle reference.
6. Save PDF and PNG with exact filenames above.

## 6) Verification checklist before commit

- All 40 new modern files exist.
- No existing fortran/ours files were deleted.
- Styling matches current figures (font scale, legend placement, color ramp, unit circle).
- Dynamic leg files are period-filtered, not full-panel overlays.
- Carrera files are legislator means, not period overlays.

## 7) Commit guidance

Commit figures separately from data/results if possible:

1. data + results commit
2. figures rebuild commit

This keeps provenance and visual changes easy to review.
