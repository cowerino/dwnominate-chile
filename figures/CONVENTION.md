# Figure convention

**Ours. Living document, opened 2026-08-13.**

Roberto, 2026-08-13: the existing figures are rejected wholesale and will be regenerated. The
convention below is **ours**, not inherited from an external template. It is informed by a measured
extraction of a reference IEEE paper in the venue's style, which remains the fallback for anything
this file does not cover, but where the two differ **this file wins**, because our figures carry a
different kind of argument.

**A convention is not adopted until it has passed section 6 on a real figure.** Until then it is a
proposal.

---

## 1. Why ours has to differ from his

His figures report a measured quantity with uncertainty attached. Ours report **uncertainty as the
subject**. Three consequences he never had to deal with:

1. **The frame problem is ours to not commit.** The paper's whole claim is that second-dimension
   orientation is analyst-supplied, not estimated. A figure that encodes left--right as a colour
   ramp, or that puts two independently-fitted maps side by side without a stated alignment,
   **asserts exactly the identification the paper denies**. Our figures must not do that even
   incidentally.
2. **We plot nested spreads, not point-plus-error-bar.** The core object is two bands of different
   width on one axis, and the reader has to be able to see the ratio between them.
3. **We plot 482 overlapping placements.** Overplotting is a real design constraint for us and is
   not one for him.

## 2. Non-negotiables

**N1. Monochrome.** No hue anywhere. Category is encoded by **marker shape**, at most five levels
(filled circle, filled triangle, filled square, plus, boxed-X). Line identity by dash pattern.

**N2. A gradient may encode only an unsigned magnitude with a meaningful zero.** Grey, monotonic in
lightness. **Never a signed political position.** A signed quantity needs a diverging ramp;
diverging ramps are dark--light--dark, so greyscale collapses both poles to the same grey, and
making the extremes read as opposed poles asserts the frame we deny. Sign gets **position**, or
filled-versus-open marker, or its own panel.

**N3. Never encode fit as confidence.** Classification rate and GMP measure fit, not identification,
and they come apart precisely on a weak second dimension: a party-line voter is classified
near-perfectly while their second-dimension coordinate is nearly free. A fit ramp would read
"confident" exactly where we are least confident, which is the error the paper diagnoses in others.
When a confidence ramp is wanted, use `s = |x| / SE` with the bootstrap SE, which is the field's
optimistic denominator and therefore makes the point on the sceptic's own terms.

**N4. Uncertainty is geometry before it is lightness.** A reader can decode an extent into a number
and nobody can decode a lightness. Preference order: segment, bar or ellipse; then invert the ramp
so the uncertain end is salient; gradient only where extent would overplot. **Never fade uncertain
points**, which makes the map look cleaner than the data is and hides a finding whose entire content
is that much of the map is undetermined.

**N5. Every coordinate figure declares its frame in the caption.** Global export or local estimator,
and the alignment operator if one was applied (centred or uncentred Procrustes). Two of our own
artifacts use different operators and the paper has called both "Procrustes".

**N6. Every number visible in a figure traces to `../reference/NUMBERS-2026-08-13.md`.** If it is
not a row there, it is not reconciled and does not go in a figure.

**N7. No figure without a manifest.** Source artifact, frame, roster, span, ensemble, generator
path, and the numbers depicted. Written beside the render.

## 3. Form

**The default form is a table.** Promote to a figure only on shape, on many items where no
individual value matters, or where the phenomenon is materially more digestible seen than read.
Keep it a table when values will be quoted or checked, when there are few items, or when the caption
would have to forbid the comparison the layout invites.

Target for this paper: **~4 figures, 5--6 tables.**

**The illegal-comparison rule.** If a caption has to say "only within-panel movement is meaningful",
the design has failed. Either make the illegal comparison visually impossible (separate axes,
explicit break, or a shared baseline that removes the temptation) or make it a table. We currently
violate this in the declined-trajectory figure.

## 4. Geometry and type

- Author at **final print size**, include at **scale 1.0**. Never author large and scale down.
- Single-column 3.5 in, double-column 7.05 in. Aspect near 1.7:1 for wide panels.
- **In-figure text is at least as large as body text.** Ticks and strip labels ~9 pt against a 9 pt
  body and 8 pt caption. This is the single most common failure in what we have produced so far.
- **Vector, never raster.** PDF with embedded fonts, `pdf.fonttype=42`. Julio asked for
  vector explicitly and it is doable throughout: every generator is matplotlib, which
  emits PDF directly. **Every figure currently in the draft is PNG**, so this alone
  requires regenerating all of them, which the wholesale rejection was going to require
  anyway. Type 3 fonts are rejected by IEEE PDF eXpress, so `fonttype=42` is a hard gate,
  not a preference.
- Panel background white, light grey major and minor gridlines, dark rule on all four sides.
- Axis titles once per grid, not per panel. Legend below the panels, outside the plotting area, no
  box.
- No plot title, no inset, no arrow, no callout, no highlighted region, no alpha fill.

## 5. Captions

**One sentence. No exceptions.** Roberto, 2026-08-13: the current captions are excessive,
and **a figure must be self-explanatory to a reader who has the context**. A caption that
has to explain the figure is a symptom that the figure failed.

This departs deliberately from the three-sentence, ~57-word caption template common in the
venue. Such captions carry the reading because the figures report a quantity; ours must carry
the reading in the geometry, because ours are the argument.

**No plot title.** The caption is the only text outside the axes.

What the single sentence must contain, compressed: what the panels are, and the frame
declaration required by N5. Everything else belongs in the body text or in a table. If a
mark's meaning cannot be inferred by a reader with context, fix the mark, not the caption.

**Test.** If the caption cannot be written in one sentence, the figure is doing more than
one job. Split it or demote it to a table.

In running text the float is the subject of an active verb. "Fig. 1 reports...", never
"(see Fig. 1)".

## 6. Acceptance test

**A figure is not accepted until all ten pass.** Record the result in the figure's manifest.

| # | test | passes when |
|---|---|---|
| A1 | **Greyscale proof** | converted to greyscale, every category is still distinguishable and every ramp still reads in the correct order |
| A2 | **Chromatic pixel count** | zero chromatic pixels in a sample of 150,000. This is measurable, and it is how the reference figure was verified |
| A3 | **Print-size read** | printed or viewed at 100 per cent at final column width, every glyph is legible and no text is smaller than the 8 pt caption |
| A4 | **Font type** | no Type 3 font in the PDF |
| A5 | **Cover-the-caption test** | a reader who cannot see the caption can state the claim the figure makes. If they cannot, the figure is decoration |
| A6 | **Illegal-comparison test** | the caption does not need to forbid any comparison the layout invites |
| A7 | **One-sentence caption** | the caption is a single sentence and there is no plot title |
| A8 | **Vector** | the figure is PDF, not raster, at every stage from generator to draft |
| A9 | **Frame declaration** | the caption names the frame, and the alignment operator if one was applied |
| A10 | **Manifest and traceability** | manifest exists and every depicted number is a row in the number registry |

The chromatic-pixel, print-size, font-type and vector checks are mechanical and should be a script,
`figures/generators/check_convention.py`, run over every candidate PDF. **Not yet written**; it is
the first thing to build when figure work resumes, because a convention that is not checked will
drift within two sessions.

The greyscale proof, the cover-the-caption test and the illegal-comparison test need a human. The cover-the-caption test is the one that would have caught the previous round: several of
those 129 renders are readable and still do not state a claim.

## 7. What this convention rejects in what we have

Named so the regeneration does not reproduce them:

- **Colour running with left--right position** on the Chamber maps. Violates N2 twice over, and
  asserts the frame we deny.
- **Arrows tracking party movement** on the crossing figure. Violates section 4, and an arrow
  between two independently-fitted maps asserts a comparability the estimator never promised.
- **Dark-versus-grey points** carrying sign stability on the floor figure. It is a second claim
  smuggled in as a shading, and it violates N4 by encoding a finding as lightness.
- **Variant sweeps as a substitute for a decision.** 129 renders for 7 slots. The convention exists
  so that a slot has one candidate, not fourteen.
