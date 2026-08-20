# Figure intent

**Living document. Update in place. Opened 2026-08-13.**

Written after Roberto's ruling of 2026-08-13: **none of the figures produced so far are
satisfactory.** The 129 renders in `reference-renders/2026-08-11/` are a record of what we tried,
not a shortlist. Some of the earlier figures in `reference-renders/2026-07/` are closer to what we
actually meant to show; they are named in §4.

The diagnosis is not that the renders are ugly. It is that **we never wrote down what each figure
was supposed to make the reader see**, so each generator optimized a look instead of an argument,
and produced variants instead of a decision.

## 0. Order of work, not negotiable

1. **Intent.** Per slot: what claim, what the reader must take away, why seen rather than read.
2. **Research.** What the data actually supports showing, at what scope, from which artifact, in
   which coordinate frame.
3. **Style.** Apply the venue style spec (`reference/VENUE-CONVENTIONS.md` §10) verbatim.

**Nothing is rendered for the paper until 1 and 2 are agreed for that slot.** The reason the last
round produced 129 files for 7 slots is that it started at 3.

## 1. The form test, condensed

From a reference IEEE paper in this venue: 1 figure against 5 tables. **The default form is a table.**
Promote to a figure only on:

- **F1** the claim is about a *shape* (trend, spread, fan, plateau, coincidence) needing many
  values seen at once;
- **F2** the claim is about *many items* (n ≳ 10) where no individual value matters;
- **F3** the phenomenon is materially more digestible seen than read, and that digestibility is
  part of the contribution.

Keep as a table on:

- **T1** ≲6 items whose individual values matter;
- **T2** the reader will want to quote or check exact values;
- **T3** the caption would have to forbid the comparison the layout invites. *"A figure whose
  across-panel comparison is illegal is a table with axes drawn on it."*

Realistic endpoint: **~4 figures, 5--6 tables.**

## 2. Blocking constraint on every slot

**Both blockers below were fixed on 2026-08-13. Rendering is unblocked.** Kept in place rather
than deleted, because what the correction moved is now part of the paper's own argument.

**Blocker 1, the frame. CLOSED (M-2).** Every generator read the defective global-axis export.
The corrected reader now lives on `main` as `generators/_coords.py`, lifted from the
quevotan-db#3 attachment with its numerics unchanged, and carries its own self-test:

    python generators/_coords.py <fit_dir>

It reproduces the registry's counts exactly (7,774 exported rows, 2,855 served, 4,919 padded,
14 full-span legislators of 338) and the invariant that proves the correction is the right one:
a full-span legislator displaces by 1.1e-15, i.e. not at all. `fig1-asymmetry.py` reads through
it now and its gates are rebased. The remaining generators are repointed but read *derived*
artifacts, so their frame question is upstream, not in the generator: see §6.

**What the correction moved,** measured by `generators/frame_audit.py`, which runs fig1's exact
construction under both frames and separates the two effects:

| | n | median SD dim1 | median SD dim2 | sign-unstable dim1 | sign-unstable dim2 |
|---|---|---|---|---|---|
| global frame, padded roster (what we drew) | 482 | 0.1416 | 0.1944 | 4.6 % | 53.3 % |
| global frame, corrected roster | 470 | 0.1421 | 0.1970 | 4.7 % | 53.4 % |
| **local frame, corrected roster** | **470** | **0.1430** | **0.1915** | **4.9 %** | **51.7 %** |

The whole of the 53.3 → 51.7 move is the *frame*; the roster contributes nothing to it. The two
corrected values reproduce, from artifacts alone and without the engine, the 51.7 % and 4.9 %
recorded independently in `../reference/NUMBERS-2026-08-13.md`. That agreement is the acceptance
test for the port, and it passed.

**M-4 is settled as a side effect, and it has a name.** The roster falls 482 → 470 because the
padded export invented twelve placements. They are six legislators, ids 1088 to 1093, who served
period 23 only, i.e. legislatura 368, being drawn into legislaturas 366 and 367 where they had
not yet arrived. Not missing data: placements for people who were not there.

**Ratio caveat, live.** Every ratio this generator prints now has a frame-corrected numerator
over a denominator bank that was banked in the global frame. **No ratio is publishable until
quevotan-db#3 lands** with the corrected reader. The gate constant is a regression check on our
own arithmetic, nothing more.

**Blocker 2, the retired output path. CLOSED.** All seven generators wrote to `figs/v2026-08-11`.
They now write to `figures/renders/<UTC date>/` through `generators/_paths.py`.
`reference-renders/` stays frozen and is never written to; a survivor is copied into
`../draft/figures/` by hand, because the copy is the decision.

## 3. Slot inventory

Each block is a **strawman for Roberto to correct**, not a finished decision. `INTENT` is my
proposal; `OPEN` is what I cannot answer.

---

### S1. The identification floor
*Currently `fig:floor`. Generators: `fig1-asymmetry.py`, `fig5-floor-in-time.py`.*

- **Claim.** Cross-frame disagreement dwarfs within-fit sampling error on dimension two, and about
  half of second-dimension placements do not keep their sign.
- **INTENT.** The reader must see *two bands of visibly different width on the same axis*, and see
  that the wide one is wide enough to cross zero for most of the middle of the distribution. The
  takeaway is a ratio made visual: the error bar the field prints is the narrow one.
- **Form.** **Figure.** F1 and F2 both hold: 482 items, and the claim is the shape of two nested
  spreads. This is the paper's central figure and the one slot where a figure is unarguable.
- **Data.** 482-cell roster, legislaturas 366--368. Frame-clean only after M-2.
- **Why the current one fails.** It shows the bands but the reader cannot extract the ratio from
  it, and the sign-instability encoding (dark vs grey points) carries the second finding as an
  afterthought. Two claims, one panel, neither landing cleanly.

**RULING 2026-08-13, Roberto: the deliverable is the sign instability.** He is right, and the
reasoning below is why, plus the answer to the three questions he asked with it.

*What "cross-frame disagreement" means here.* Fit the same votes under several defensible analyst
choices (two admissible C++ fits at 0 and 10 tolerance steps, plus the QueVotan reference, an
independent estimator on the same vote record), align them onto one target, and measure how far
one placement sits from itself across those fits. Median 0.1430 on dimension one, 0.1915 on
dimension two.

*Why it matters that within-fit sampling error is dwarfed.* The bootstrap SE answers "how much
would this coordinate move if the chamber had voted slightly differently": 0.0327 and 0.0705.
That is the bar the field prints. It is not wrong; it answers a question nobody asked. The
analyst-choice variation is 2.7 times larger on dimension two, and no printed error bar contains
it. **A reader looking at the published interval concludes a placement is pinned down, when what
is pinned down is only its sampling behaviour under one arbitrary frame.**

*How the two are related, and this is the connection worth drawing.* They are the same quantity
in different units. The ratio is the measurement; the sign flip is what the measurement costs
you. A dim-2 coordinate that reads +0.15 in one admissible frame and −0.10 in another has not
merely moved by 0.25, it has changed sides. On dimension two that happens to **51.7 % of
placements**; on dimension one, to 4.9 %.

*And this is exactly the movement in the unit-disk maps.* Movement on a disk is the difference of
two positions. A difference of positions is only meaningful inside one frame. The paper's hinge
claim (S2) is that the frame is supplied by the seed rather than estimated. So any displacement
read off a pair of independently fitted disks is real movement **plus** a frame difference, and
on dimension two the frame difference term is the larger one. The sign-instability number is the
sharpest available statement of that: for half the chamber the frame difference alone is big
enough to carry a legislator across the origin, with no change in voting behaviour whatsoever.
That single sentence is the bridge from S1 to S5, and it is why they are one argument seen twice.

**Consequences, all three of them.**

1. **The ratio leaves this figure and becomes a row in the sensitivity-ledger table.** It fails
   the form test on its own terms: a reader wants to quote it (T2), it is a range rather than a
   value once the ledger framing lands (2.7 to 3.85 across admissibility rules), and its
   denominator is not settled until quevotan-db#3 returns. A number under active revision does
   not belong in the paper's central figure.
2. **The figure becomes a disk, not a caterpillar.** Recommended construction: one unit disk, the
   470 placements at their cross-frame mean, with **filled markers for placements that keep their
   dim-2 sign across all admitted frames and open markers for those that do not**. This is the
   object Roberto already reads, with the finding drawn on it, and open-versus-filled is the
   encoding `CONVENTION.md` N2 explicitly reserves for sign. It carries one claim, so its caption
   fits in one sentence, and it invites no cross-panel comparison, so it passes A6 by
   construction. The frame is declared in the caption per N5.
3. **Do not fade the unstable points.** N4. The finding *is* that half the map is undetermined;
   fading it would make the map look cleaner than the data.

- **OPEN, narrowed.** Only one question left: does the disk plot all 470 placements from
  legislaturas 366 to 368 at once, or one disk per legislatura? Three small disks would show
  whether the instability is uniform across the three; one big disk is more legible. Recommend
  one, and report the per-legislatura rates in the text.

---

### S2. The seed fixes the frame
*Currently `fig:seed` + Table II. Generator: `fig4_seed.py`.*

- **Claim.** DW-NOMINATE inherits its frame from the seed rather than estimating it.
- **INTENT.** This is the *hinge* of the paper: everything downstream depends on the reader
  accepting it. It has to be shown in a way that survives a skeptical reading.
- **Form.** **Table**, per the reference test. T1: three items, and the values (0.99/0.82 vs
  0.17/0.48) are exactly what a reader wants to quote. Table II already carries them.
  the venue style spec reaches the same conclusion independently.
- **Recommendation.** Retire the figure, keep Table II, and spend the reclaimed space on S1.
  This alone recovers most of the ~0.9pp of the page overrun.
**RULING 2026-08-13, Roberto: retire the figure, keep Table II, look at the result.** Iterate
after seeing it rather than deciding in the abstract. `fig4_seed.py` is therefore **not** ported
to the corrected frame: it is repointed and left otherwise untouched, so no effort goes into a
generator whose output is being removed. If the retirement is reversed, the port is a ten-line
change through `_coords`, the same one fig1 took.

**Note on the hinge worry.** A table does not weaken the claim if the prose treats it as the
hinge. What weakens it is a figure the reader cannot check. The 0.99/0.82 against 0.17/0.48
contrast is quotable, and quotable is what a skeptical reader wants here.

---

### S3. Verification against the oracle
*Currently Table I. Generators: `fig3-verification.py`, and the retired `US_timeline`.*

- **Claim.** The C++ engine reproduces the canonical Fortran component by component, and where it
  does not, we state the size of the gap.
- **INTENT.** For a **CS** audience this is the contribution they will judge us on. Julio's ask 7
  and Reviewer 4's principal request are both for a *component / tolerance / benchmark input /
  observed discrepancy* table.
- **Form.** **Table, decisively.** T2: a referee will check these values. A figure here actively
  hurts. The four measured rows already exist in
  `planning/PLAN-DRAFT-TO-JULIO-2026-08-12.md` §1.3.
- **Status.** This is the **highest-value unblocked item in the paper** and it needs no figure work
  at all. It should not wait on the figure replan.

**RULING 2026-08-13, Roberto: table, and it has to be the strongest thing in the paper.** The
existing one was sloppily generated. Treat this as the deliverable a CS referee grades us on, not
as a supporting exhibit. Concretely that means: every row states component, tolerance with its
basis, benchmark input, and observed discrepancy; **every float clause carries a tolerance**, per
the standing rule that cost us the pablo-10 gate; and no row is transcribed from a planning
document without being re-read from the artifact it came from. Four measured rows exist (L1 host
and compiler, L2 LAPACKE implementation, L3 SVD path, L4 portable versus paper flags from the
cold clone). This is M-5 and it belongs to the writing lane, not the figure lane.

---

### S4. The Chamber before and after the *estallido*
*Currently `fig:chilemap`. Generators: `nominate_maps.py`, `b2_scatter_maps.py`.*

- **Claim.** Both engines place the parties in the same left--right order and at the same
  second-dimension poles, before and after the shock.
- **INTENT.** Two jobs are currently fused into one figure: (i) *engine agreement*, a verification
  claim, and (ii) *what the Chamber looks like*, a substantive claim. Fusing them is why it needs
  four panels and satisfies nobody.
- **Form.** Split. Engine agreement is a **table** (it is a correlation, T2, and Table I already
  reports it). What the Chamber looks like may be a **figure** on F3.
- **Style violation, live.** The caption says *"Colour runs with left--right position."* The
  monochrome policy forbids exactly this, and for this figure's precise reason: a signed political
  quantity needs a diverging ramp, diverging ramps are dark--light--dark, so greyscale collapses
  both poles to the same grey. Encoding left--right as a ramp also asserts the frame
  identification this paper exists to deny.
**RULING 2026-08-13, Roberto: the map stays, and colour is allowed here.** Identify the top 9 to
10 parties, give each a colour **and** a letter label, place the labels carefully, and do not let
labelling occlude the plotted points. Digestibility is the point: the reader must be able to see
the chamber, find the groups, and know who they are.

**This ruling and `CONVENTION.md` N2 are compatible, and the distinction matters enough to write
down.** N2 forbids **a colour ramp encoding a signed political position**, because a ramp asserts
that left-to-right is an estimated axis, which is the identification this paper denies. Colouring
nine parties as **categories** asserts nothing about the axis. So what the ruling relaxes is N1's
blanket monochrome; what stays dead is the ramp, and the current caption's *"Colour runs with
left--right position"* stays forbidden.

**Two risks, both cheap to insure against.**

1. **Nine or ten categorical colours is past the reliable limit**, and it is past it for
   everybody, not only colour-blind readers. The insurance is the lettering Roberto already asked
   for: **put the party label at the group's own position so colour is redundant rather than
   load-bearing.** If the letters carry the identification, the colour count stops mattering.
2. **Confirm the proceedings print in colour before relying on it.** If JCC prints greyscale, ten
   hues collapse to five indistinguishable greys and the figure dies on the page. Same insurance.

- **Still open.** Whether engine agreement rides on this figure at all. It should not: that is a
  correlation, Table I already reports it, and fusing it with "what the chamber looks like" is why
  the current version needs four panels. Split it: agreement to the table, chamber to the map.

---

### S5. The declined trajectory
*Currently `fig:arrival`. Generator: `fig7-declined-trajectory.py`.*

- **Claim.** Independent per-sub-period scaling reads as a journey of |Δ|≈1.1; one coherent frame
  leaves the same parties stationary at |Δ|≈0.02--0.03. We therefore decline the arrival.
- **INTENT.** This is the paper's most rhetorically loaded object: it shows the *previous
  literature's finding dissolving*. The reader must see that the big movement and the null result
  are the **same data under two procedures**.
- **Form.** **Figure**, on F3. The side-by-side collapse is more persuasive seen than read, and
  that persuasion is part of the contribution.
- **Warning, T3.** The current caption says *"Only within-panel movement is meaningful."* A caption
  that has to forbid the comparison the layout invites is the definition of a figure that should
  be a table. Either the design must make across-panel comparison visually impossible, or this
  becomes a table.
**RULING 2026-08-13, Roberto**, with two corrections and a strict verdict he asked for.

*Correction he made, and it is right:* we are **not** arguing against previous literature. D-R2
already resolved this by rebuilding the motivation on our own panel, so the object is a procedure
we ran, not a claim someone else published. Any drafting that reads as rebuttal is off-spec.

*His proposal:* show the disk under the coherent global frame, say in the text what that frame
means, then show the cherry-picked frames, and use the pair to explain why a reader might judge
that movement occurred. He asked for a strict judge, not a sale.

**Verdict: the rhetorical structure is right and should survive. The map form of it should not.**

What is right: coherent frame first, split procedure second. That order puts the null result in
the position of the baseline and the apparent journey in the position of the artifact, which is
the correct relation between them. Reversing it makes the paper look like it is explaining away
an inconvenience.

What sinks it: **two independently fitted disks side by side is the one construction this figure
already failed on.** It is the reason the current caption has to say *"Only within-panel movement
is meaningful."* A caption that forbids the comparison the layout invites is the definition of a
figure that should be a table (T3, and A6 in the acceptance test). Putting the disks side by side
reintroduces exactly that defect in a new costume, and it is a costume the referee will see
through faster than we will, because the whole paper has just finished telling them that
across-frame comparison is illegitimate.

**The fix is cheaper than the figure he proposed. Do not show two maps. Show one number.** The
quantity carrying the claim is displacement magnitude: |Δ| ≈ 1.1 under independent per-sub-period
scaling against |Δ| ≈ 0.02 to 0.03 in one coherent frame, the same parties, the same votes. One
axis, two sets of marks, roughly a fortyfold separation visible without reading a label. It
invites no cross-panel comparison because there are no panels. **And it contains no coordinates
at all, so it is immune to the frame problem it is about** — which is the same reason the S6
schematic is attractive.

*Is it valuable? Yes, and unambiguously.* It is the only place the paper shows a null result being
manufactured rather than asserting that one can be. Keep it. But keep it as a displacement
contrast, not as a map.

*Where the map does belong:* S4. There it is a substantive claim about the chamber rather than a
rhetorical device, and colour is already authorised.

- **Owed before this prints.** The ~1.1 against ~0.02 pair is our own measurement and the
  Introduction already prints it. Confirm it has a finding file behind it; the standing rule is
  that a number with no finding file is not ready to print, and this one carries a lot of weight
  for a number that arrived through a draft edit.

---

### S6. Triangulation across lineages
*Currently prose only. Generator: `fig6-triangulation.py`. Julio's ask 5 pre-authorises a table
**or** a schematic.*

- **Claim.** Three independently built estimations agree on pole membership; they do not share a
  common frame.
- **INTENT.** The reader must see that agreement is on *membership*, not on coordinates. The
  distinction is the whole claim and it is what prose keeps failing to make crisp.
- **Form.** **Table** for the agreement values (T2), possibly **plus a schematic** showing the
  three lineages and what each shares with the others. Julio explicitly allowed a schematic, and a
  schematic is the one figure type here that carries no coordinates and therefore cannot be
  undermined by the frame problem.
- **Recommendation.** A lineage schematic is the highest-value *new* figure in the set. It is also
  the cheapest: it is drawn from provenance, not from data, so it is immune to M-2.

**RULING 2026-08-13, Roberto: build the schematic, then evaluate it.** Draw it and judge the
artifact rather than the description. It shares the property that makes the S5 replacement work:
no coordinates, therefore nothing in it can be undermined by the frame argument the paper spends
its length making.

---

### S7. Admissibility / convergence screening
*Generator: `fig2-admissibility.py`.*

- **Claim.** Which fits are admissible changes the headline ratio (2.7 to 3.85), the widest single
  analyst knob.
- **INTENT.** Under the ledger framing this is a **row in Table III**, not a figure.
- **Form.** **Table.** Already carried by the sensitivity ledger table.
- **Recommendation.** Cut the slot. If D-L1 (ledger adoption) goes the other way, revisit.

**RULING 2026-08-13, Roberto: cut.** `fig2-admissibility.py` is repointed and otherwise left
alone. The admissibility range lives in the sensitivity-ledger table, which is also where the S1
ratio now goes.

---

## 4. Earlier figures worth reviewing

Per Roberto: earlier versions may be closer to the intentions. In
`reference-renders/2026-07/`, these express a core claim directly rather than as a variant sweep:

| file | expresses | why it may be closer |
|---|---|---|
| `F1_three_pipeline_dim2_poles.png` | S6 triangulation | states the pole claim as pole membership, not as coordinates |
| `PAPER-s5_signflip_RDCS_3frames_truncation.png` | S1 sign instability | isolates sign instability as its own object instead of as a shading on the floor plot |
| `RIED-vs-ours_D2-arrival_RDCS-to-PCpole.png` | S5 declined trajectory | frames it as *the prior claim versus ours*, which is the actual rhetorical move |
| `PAPER-s4_dim2_threshold_band_vs_L.png` | S1 ratio | shows the band against a swept parameter, closer to "the ratio is a range" |
| `DIAG_seed_frame_scramble_leg368.png` | S2 seed | more legible as a demonstration than the polished replacement |

**Review these before designing anything new.** They predate the style work, so they will look
wrong; judge them on whether the *object* is right.

## 5. What is owed, and by whom

Rewritten 2026-08-13 after Roberto ruled on all seven slots and both blockers were cleared.

**The surviving set is four figures and six tables**, which is the target `CONVENTION.md` §3
names:

| slot | form | state |
|---|---|---|
| S1 identification floor | **figure**, sign-instability disk | designed, not drawn. Data path corrected and gated |
| S4 the chamber | **figure**, party map with colour and lettering | ruled, needs design |
| S5 declined trajectory | **figure**, displacement contrast, no map | ruled, needs design |
| S6 triangulation | **figure**, lineage schematic | ruled, needs drawing. Immune to M-2 |
| S2 seed | table (Table II) | figure retired |
| S3 verification | table | **highest-value unblocked item.** M-5 |
| S7 admissibility | table row | slot cut |

| | |
|---|---|
| **Roberto** | One narrowed question only: S1 as one disk or three (§3, S1). Everything else is ruled. |
| **Ours, unblocked** | S3's verification table. Needs no figure decision at all. |
| **Ours, next** | Design the four survivors, draw, then run `check_convention.py` before showing anything. |
| **Ours, upstream** | The four generators reading derived artifacts, §6. |

## 6. The frame question that is left, and it is not in the generators

`fig1` reads coordinates directly, so correcting its reader corrected it. **Four generators do
not read coordinates at all**, and for them swapping a reader fixes nothing, because the defect
may already be baked into the artifact they read:

| generator | reads | frame status |
|---|---|---|
| `fig5-floor-in-time.py` | `TEMPORAL-FLOOR-SERIES-2026-08-05.json`, `julio_test/route2/dwnom_se.csv` | **unverified.** Both predate the frame finding by six days |
| `fig2-admissibility.py` | `_adm_ll_table.json`, `dwnom_se.csv` | slot cut, so moot unless D-L1 reverses |
| `fig3-verification.py` | `procrustes_*.csv` from the US run | probably immune, unverified. US legislators are mostly full-span, where the two frames coincide |
| `fig6-triangulation.py` | party-means CSVs | schematic form carries no coordinates, so the successor is immune by construction |

**Only `fig5` matters**, since it is an S1 generator. The question is not a figure question: it is
whether the temporal floor series was computed over global-t coordinates, and if so it has to be
recomputed upstream, in `tools/analysis/`, which is the researcher lane's write scope, not this
one. **Filed, not fixed here, deliberately**, because fixing it in the figure layer would mean a
second lineage computing the same statistic, which is the trap already recorded as M-1.

## 7. Tooling built 2026-08-13

Under `generators/`, all four verified by running them:

| file | does |
|---|---|
| `_coords.py` | the corrected reader, with a self-test and a padded-row report. `python _coords.py <fit_dir>` |
| `_paths.py` | shared paths; renders go to `figures/renders/<date>/`, `reference-renders/` stays frozen |
| `frame_audit.py` | runs fig1's construction under both frames and separates roster effect from frame effect. Run it before moving any gate constant |
| `check_convention.py` | the mechanical half of the §6 acceptance test: A2 chromatic, A3 print-size type, A4 Type 3, A8 vector. Prints the six human-only tests every time so a mechanical pass is never mistaken for acceptance |

**First run of `check_convention.py` failed the current fig1 on two counts**, which is the
convention doing its job on day one: 52 chromatic colour operators (`#1c5cab`, `#86b6ef`, the
band fills) and 7 pt type against the 8 pt floor. Both are in the rejected list at
`CONVENTION.md` §7 already; now they are measured rather than remembered.
