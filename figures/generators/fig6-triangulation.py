#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""fig6-triangulation  --  "Three lineages, one pole"

Built 2026-08-11 against FIGURE-DESIGN-2026-08-11.md section 3 (fig6-triangulation),
section 5.4 (alignment rule), section 7 (visual system), section 8 (limits).

NEW GENERATOR.  Does not edit, import or share state with
reproduce/scripts/build_fig_f1_poles.py.  That file stays as it is.

WHAT IS PLOTTED
  Horizontal dot plot, single column (3.5 in = \columnwidth 252 pt).  One row per
  party, ordered by our lineage's second-dimension mean.  Three markers per row in
  three vertical slots and three marker shapes, one per estimation lineage:

    slot 1  o  our C++ engine, single-period constant model (static W-NOMINATE),
               one fit per sub-period P1/P2/P3 of legislaturas 366-368
    slot 2  s  the QueVotan reference (production per-votacion W-NOMINATE served
               by the platform), legislaturas 366-368
    slot 3  ^  Fabrega's separately curated 2018-2022 vote matrix, re-scaled at two
               dimensions by our estimator (R wnominate, his pipeline replica)

  A light band per row spans the three values.  A solid vertical rule at zero.
  Direct (bold) labels on RD, CS and PC only.

  THE fig:crossing FOLD.  fig:crossing's transferable content is two arrows and one
  count.  Variants A and B draw the two arrows: on the UDI and EVOP rows only, the
  reference's own legislatura 366 -> 368 movement is drawn as an arrow through the
  reference marker.  The count stays in the caption; nothing numeric is drawn
  inside the figure (FIGURE-DESIGN 7.1).

INDEPENDENCE, AND WHAT MUST NOT BE DRAWN OR WRITTEN
  DESK-PLAN 5.3 / DATA-CONTRACT section 3.  The QueVotan reference reads the SAME
  MongoDB dump as our panel (build_julio_reference.py:37,:46 reads
  quevotanEtiquetado/new_wnominate.bson).  It is an independent ESTIMATOR and an
  independent estimation lineage.  It is NOT an independent vote record and NOT
  independent data.  Only the Fabrega leg is an independently curated vote record,
  and his published estimates are one-dimensional (A_Ideology_Estimation.R:96,
  dims = 1), so his second dimension here is OUR estimator on HIS votes, never his
  own 2D estimate.  Nothing in this generator's labels, legend or caption may blur
  those two.

PANEL, and it is not one panel
  This figure has no Fortran arm, so the dwnom2004 one-legislatura offset class
  (FIGURE-DESIGN 5.1, 5.2) cannot arise here.  It is asserted absent anyway.
  The three lineages sit on three DIFFERENT spans and that is stated, not hidden:
    ours       legislaturas 366-368, 25-unit sub-period split, units 21-25,
               P1 = units 21-22, P2 = 23-24, P3 = 25 (truncated 2021-03-10)
    reference  legislaturas 366-368 only.  The by_leg artifact also contains leg
               369; it is DROPPED here and the drop is asserted.
               julio_reference_periodo9_pooled.csv is NOT used as a coordinate
               series: it pools legs 366-369 (build_julio_reference.py has no leg
               filter before the pooled groupby) and would be a section-4 panel
               violation.  It is used only as (a) the legislator -> party crosswalk
               and (b) the Procrustes target FRAME, which is a gauge, not a series.
    Fabrega    his full 2018-2022 period matrix, legislaturas 366-369, i.e. one
               legislatura beyond our panel.  Unavoidable: the artifact is his, it
               is not sliceable by legislatura here, and DATA-CONTRACT section 5
               already records that his votes run past our snapshot.

THE LOPSIDEDNESS SCREEN (main_cli.cpp:471 marginThreshold = 0.025)
  This figure counts no roll calls and no votes; it plots legislator coordinates
  averaged to party means.  For provenance the manifest records both sides of the
  screen where they are knowable:
    ours       2,665 roll calls loaded across P1+P2+P3; 1,772 carry a non-zero
               estimated cutline post-screen, 893 are zeroed out.
    Fabrega    3,520 roll calls in his matrix; R wnominate dropped 1,227, so 2,293
               post-screen (fabrega/run.log).
    reference  2,217 votaciones as served by the platform; the QueVotan production
               pipeline's own screening is NOT verified here.

VARIANTS.  Two design decisions are open; all four cells are rendered rather than
picked.  See the manifest and the returned report.
  D1  what occupies slot 2:  the QueVotan reference (FIGURE-DESIGN's stated intent
      and its binding caption clause) OR ried_grain/indep_party_means_aligned.csv,
      which is what the existing off-paper PNG actually plots and which is R
      wnominate on OUR matrices, i.e. a different code lineage but the same
      curation and NOT the reference.
  D2  how the Fabrega leg is gauged:  centred orthogonal Procrustes onto the
      reference frame (same operator as our arm already carries, and it reproduces
      the r = 0.833 the paper cites) OR the RD-anchored reflection used by
      build_fig_f1_poles.py:49, under which RD's Fabrega sign is DEFINITIONAL and
      therefore carries no evidence.
  D3  do the two crossing arrows earn their ink.

  A  = reference slot | Fabrega Procrustes | arrows      -> fig6-triangulation_v1
  B  = reference slot | Fabrega RD-anchor  | arrows      -> ...-B-rdgauge_v1
  C  = reference slot | Fabrega Procrustes | no arrows   -> ...-C-noarrows_v1
  D  = indep slot     | Fabrega RD-anchor  | no arrows   -> ...-D-indepslot_v1

NO COMPUTE.  No fit is run.  The only arithmetic beyond means is a 2x2 centred
orthogonal Procrustes over coordinates already on disk (same class as the alignment
FIGURE-DESIGN specifies for fig1, which it lists as needing no compute).

Usage:  python fig6-triangulation.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths

# ---------------------------------------------------------------------------
# NAMED CONSTANTS.  Nothing below this block is inlined.
# ---------------------------------------------------------------------------

# fig6 plots no ratio and no error band, so it has no denominator.  The slot is
# declared anyway so that the pablo-10 swap contract (FIGURE-DESIGN section 6) is
# visible here as a one-line edit if this figure ever grows an error bar.
DENOM_MED_SE_DIM2 = None            # not used by fig6.  route2_bigB B=150 value is
                                    # 0.0706 on base cpp_run_chile if ever needed.

LOPSIDEDNESS_THRESHOLD = 0.025      # main_cli.cpp:471, dwnominate.cpp:187,
                                    # dwnom2004.f:324-326.  Both engines screen.
PANEL_LEGS = (366, 367, 368)        # the figure's legislatura span for ours + reference
REF_ARTIFACT_LEGS_PRESENT = (366, 367, 368, 369)   # what the by_leg CSV contains
MIN_PARTY_N = 4                     # inherited from _req013_analysis.py:189 (sm.n >= 4)
GAUGE_ANCHOR_PARTY = "RD"           # RD-anchored reflection gauge (variants B, D)
MOVERS = ("UDI", "EVOP")            # fig:crossing's two arrows
LABEL_PARTIES = ("RD", "CS", "PC")  # FIGURE-DESIGN: direct labels on these only
EXPECT_FAB_REF_R2 = 0.833           # main-rewrite-2026-08-05.tex:449-451
EXPECT_FAB_REF_R2_TOL = 0.01
EXPECT_N_LEGISLATORS = 163
PUBLISHED_UDI_FLIP = "22 of 26"     # main-rewrite-2026-08-05.tex:495, derived in
                                    # analysis/MAP3-udi-decomposition.md on the
                                    # service-filtered set.  NOT reproducible from
                                    # the by_leg artifact; see the printed gate.

# --- palette, FIGURE-DESIGN 7.3.  Re-validated 2026-08-11:
#     node scripts/validate_palette.js "#2a78d6,#eb6834,#4a3aa7" --mode light \
#          --surface "#ffffff" --pairs all   -> ALL CHECKS PASS
C_OURS = "#2a78d6"    # categorical slot 1, blue
C_REF = "#eb6834"     # categorical slot 2, orange
C_FAB = "#4a3aa7"     # categorical slot 3, violet
C_BAND = "#e1e0d9"    # gridline tone, used as the per-row spread band
C_INK = "#0b0b0b"     # primary ink
C_MUTED = "#898781"   # muted ink
C_RULE = "#898781"    # the zero rule
SURFACE = "#ffffff"   # the paper renders on white

# --- geometry, FIGURE-DESIGN 7.4.  Author at the include width, never scale.
COL_IN = 3.5          # \columnwidth 252 pt
FIG_H_IN = 3.35
AXES_RECT = (0.155, 0.175, 0.825, 0.760)
SLOT_DY = 0.26        # vertical offset of the three lineage slots inside a row
BAND_LW = 8.2         # points; the per-row spread band
FS_BASE, FS_LABEL, FS_TICK, FS_LEG = 8, 8, 7, 7

matplotlib.rcParams.update({
    "pdf.fonttype": 42,          # IEEE PDF eXpress rejects Type 3
    "ps.fonttype": 42,
    "font.size": FS_BASE,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "axes.linewidth": 0.6,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
REPO = Path("C:/Users/cow/Documents/GitHub/quevotan-db")
CH = REPO / "reproduce/out/chile"
P_OURS = CH / "subperiod25/statics_party_means.csv"
P_INDEP = CH / "subperiod25/ried_grain/indep_party_means_aligned.csv"
P_REF_BYLEG = CH / "julio_reference_periodo9_by_leg.csv"
P_REF_POOLED = CH / "julio_reference_periodo9_pooled.csv"   # crosswalk + gauge frame ONLY
P_FAB = CH / "fabrega/fabrega_wnom2d_2018_22.csv"

OUTDIR = _paths.render_dir()   # was PAPER/"figs/v2026-08-11", a path the
                               # 2026-08-13 reorganization retired. Renders go to
                               # figures/renders/<date>/; survivors are copied into
                               # draft/figures/ by hand. reference-renders/ is frozen.
FIGNAME = "fig6-triangulation"

SOURCES = {
    "ours_static_party_means": P_OURS,
    "indep_rwnom_party_means_aligned": P_INDEP,
    "quevotan_reference_by_leg": P_REF_BYLEG,
    "quevotan_reference_pooled_GAUGE_AND_CROSSWALK_ONLY": P_REF_POOLED,
    "fabrega_wnom2d_2018_22": P_FAB,
}


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def fail(msg: str) -> None:
    raise SystemExit(f"\n*** ALIGNMENT / PANEL ASSERTION FAILED ***\n{msg}\n")


# ---------------------------------------------------------------------------
# LOAD + ASSERT
# ---------------------------------------------------------------------------
print("=" * 74)
print("fig6-triangulation  --  gates")
print("=" * 74)

# Non-negotiable 1.  This figure has no Fortran arm.  Prove it.
for k, p in SOURCES.items():
    if "dwnom2004" in str(p).lower():
        fail(f"a dwnom2004 artifact reached fig6: {k} = {p}")
print("[gate 0] no dwnom2004_* artifact is read by this figure          PASS")
print("         (fig6 has no Fortran arm, so the 5.1/5.2 offset class")
print("          cannot arise; dwnom2004_chile is nowhere in SOURCES.)")

ours_raw = pd.read_csv(P_OURS)
indep_raw = pd.read_csv(P_INDEP)
byleg = pd.read_csv(P_REF_BYLEG)
pooled = pd.read_csv(P_REF_POOLED)
fab = pd.read_csv(P_FAB)

# --- gate 1: the reference artifact really contains leg 369, and we really drop it
legs_in_artifact = tuple(sorted(byleg["legislatura"].unique()))
if legs_in_artifact != REF_ARTIFACT_LEGS_PRESENT:
    fail(f"reference by_leg legs are {legs_in_artifact}, expected {REF_ARTIFACT_LEGS_PRESENT}")
ref = byleg[byleg["legislatura"].isin(PANEL_LEGS)].copy()
if tuple(sorted(ref["legislatura"].unique())) != PANEL_LEGS:
    fail("reference frame after the panel filter is not exactly 366/367/368")
if (ref["legislatura"] == 369).any():
    fail("legislatura 369 survived the panel filter")
roster = ref.groupby("legislatura")["legislator_id"].nunique().to_dict()
n_ref_legislators = ref["legislator_id"].nunique()
if n_ref_legislators != EXPECT_N_LEGISLATORS:
    fail(f"reference roster is {n_ref_legislators} legislators, expected {EXPECT_N_LEGISLATORS}")
print(f"[gate 1] reference panel = legs {PANEL_LEGS}, 369 dropped            PASS")
print(f"         per-leg roster {roster}, {n_ref_legislators} distinct legislators")

# --- gate 2: pooled is a 366-369 object and is never plotted as a series
print("[gate 2] julio_reference_periodo9_pooled.csv used as gauge frame +")
print("         party crosswalk ONLY, never as a plotted series.        PASS")
print("         (it pools legs 366-369; plotting it under a '366-368'")
print("          caption would be a DATA-CONTRACT section 4 violation.)")

# --- party columns
for df in (ours_raw, indep_raw):
    df["d2"] = df[["d2_P1", "d2_P2", "d2_P3"]].mean(axis=1)
    df["d1"] = df[["d1_P1", "d1_P2", "d1_P3"]].mean(axis=1)
ours = ours_raw.set_index("partido")["d2"]
indep = indep_raw.set_index("partido")["d2"]

PARTIES_ALL = sorted(ours.index)
if len(PARTIES_ALL) != 11 or not set(LABEL_PARTIES) <= set(PARTIES_ALL):
    fail(f"our lineage yields {len(PARTIES_ALL)} parties {PARTIES_ALL}; expected 11 incl. RD/CS/PC")
print(f"[gate 3] party set = {len(PARTIES_ALL)} parties at n >= {MIN_PARTY_N}          PASS")
print(f"         {PARTIES_ALL}")

# --- reference party means over legs 366-368.
#     unit = legislator placement (mean of that legislator's per-leg medians),
#     then party mean.  Matches the unit the other two lineages use.
ref_leg_party = ref.groupby(["partido", "legislatura"])["y"].mean().unstack("legislatura")
ref_by_legislator = ref.groupby(["legislator_id", "partido"])["y"].mean().reset_index()
ref_mean = ref_by_legislator.groupby("partido")["y"].mean()
ref_alt = ref_leg_party.mean(axis=1)          # equal weight per legislatura
_gap = (ref_mean - ref_alt).abs().reindex(PARTIES_ALL).max()
if _gap > 0.02:
    fail(f"the two reference aggregations disagree by {_gap:.3f} (> 0.02); resolve before plotting")
print(f"[gate 4] reference aggregation stable: legislator-first vs leg-first")
print(f"         max |diff| = {_gap:.4f} over the plotted parties           PASS")

# --- Fabrega, joined to party via the pooled crosswalk (static labels)
party_of = pooled.set_index("legislator_id")["partido"].to_dict()
fab = fab.copy()
fab["legislator_id"] = fab["DiputadoId"].astype(int)
fab["partido"] = fab["legislator_id"].map(party_of)
if fab["partido"].isna().any():
    fail(f"{int(fab['partido'].isna().sum())} Fabrega legislators failed the party join")
if len(fab) != EXPECT_N_LEGISLATORS:
    fail(f"Fabrega artifact has {len(fab)} rows, expected {EXPECT_N_LEGISLATORS}")
print(f"[gate 5] Fabrega join: {len(fab)}/{EXPECT_N_LEGISLATORS} legislators matched to a party   PASS")


def procrustes_rot(A: np.ndarray, B: np.ndarray):
    """Centred orthogonal Procrustes (rotation + reflection, no scaling).
    Identical operator to _req013_analysis.py:24-28, which is the operator our
    own arm already carries in statics_party_means.csv.  FIGURE-DESIGN 5.4(2):
    name the convention.  This is the CENTRED one."""
    Ac, Bc = A - A.mean(0), B - B.mean(0)
    U, _, Vt = np.linalg.svd(Ac.T @ Bc)
    return A.mean(0), B.mean(0), U @ Vt


# D2 arm (i): Procrustes onto the reference frame
j = fab.merge(pooled[["legislator_id", "x", "y"]], on="legislator_id")
ma, mb, R = procrustes_rot(j[["coord1D", "coord2D"]].to_numpy(), j[["x", "y"]].to_numpy())
XY = (fab[["coord1D", "coord2D"]].to_numpy() - ma) @ R + mb
fab["d2_proc"] = XY[:, 1]
JXY = (j[["coord1D", "coord2D"]].to_numpy() - ma) @ R + mb
fab_r1 = float(np.corrcoef(JXY[:, 0], j["x"])[0, 1])
fab_r2 = float(np.corrcoef(JXY[:, 1], j["y"])[0, 1])
if abs(fab_r2 - EXPECT_FAB_REF_R2) > EXPECT_FAB_REF_R2_TOL:
    fail(f"Fabrega-vs-reference post-align r2 = {fab_r2:.3f}, paper says {EXPECT_FAB_REF_R2}")
print(f"[gate 6] Fabrega Procrustes onto reference: r1 {fab_r1:.3f}  r2 {fab_r2:.3f}  PASS")
print(f"         paper cites r = {EXPECT_FAB_REF_R2} (tex:449-451); det(R) = {np.linalg.det(R):+.3f}")

fab_proc = fab.groupby("partido")["d2_proc"].mean()

# D2 arm (ii): RD-anchored reflection, build_fig_f1_poles.py:49
fab_raw_mean = fab.groupby("partido")["coord2D"].mean()
flip = -1.0 if fab_raw_mean.get(GAUGE_ANCHOR_PARTY, 0.0) > 0 else 1.0
fab_anchor = fab_raw_mean * flip
print(f"[gate 7] RD-anchored gauge: flip = {flip:+.0f}.  NOTE {GAUGE_ANCHOR_PARTY}'s sign in this")
print( "         arm is DEFINITIONAL and carries no evidence.")

# --- sign gauge sanity across every plotted lineage
for name, ser in (("ours", ours), ("reference", ref_mean), ("indep", indep),
                  ("fabrega_procrustes", fab_proc), ("fabrega_rdanchor", fab_anchor)):
    v = float(ser[GAUGE_ANCHOR_PARTY])
    if v >= 0:
        fail(f"{name}: {GAUGE_ANCHOR_PARTY} is {v:+.3f}, expected the negative pole after gauging")
print(f"[gate 8] {GAUGE_ANCHOR_PARTY} sits on the negative pole in all five candidate series  PASS")

# --- the fig:crossing count, recomputed from the artifact
u = ref[ref["partido"] == "UDI"].pivot_table(index="legislator_id", columns="legislatura", values="y")
both = u.dropna(subset=[366, 367])
udi_n, udi_flips = len(both), int(((both[366] > 0) != (both[367] > 0)).sum())
ctl = {}
for p in ("RD", "CS", "PC", "PS"):
    q = ref[ref["partido"] == p].pivot_table(index="legislator_id", columns="legislatura", values="y")
    q = q.dropna(subset=[366, 367])
    ctl[p] = (int(((q[366] > 0) != (q[367] > 0)).sum()), len(q))
print(f"[gate 9] UDI member sign flips 366 -> 367 on THIS artifact: {udi_flips} of {udi_n}")
print(f"         the paper's caption prints '{PUBLISHED_UDI_FLIP}' (MAP3-udi-decomposition.md,")
print( "         service-filtered set).  The two do not agree and the figure prints")
print( "         no count; whichever is used in the caption must name its filter.")
print(f"         control parties (flips/n): {ctl}")

# --- movers, from the reference itself
mover_track = {p: {L: float(ref_leg_party.loc[p, L]) for L in PANEL_LEGS} for p in MOVERS}
for p in MOVERS:
    a, b = mover_track[p][366], mover_track[p][368]
    if (a > 0) == (b > 0):
        fail(f"{p} does not change sign 366 -> 368 in the reference ({a:+.3f} -> {b:+.3f}); "
             "the crossing fold is not supported and the arrows must be dropped")
print(f"[gate 10] both movers change sign in the reference 366 -> 368        PASS")
for p in MOVERS:
    print(f"          {p}: " + "  ".join(f"{L} {mover_track[p][L]:+.3f}" for L in PANEL_LEGS))

# --- sign agreement across lineages, the figure's honest read
def agreement(slot2: pd.Series, fabser: pd.Series):
    out = {}
    for p in PARTIES_ALL:
        vs = [float(ours[p]), float(slot2[p]), float(fabser[p])]
        out[p] = all(v < 0 for v in vs) or all(v > 0 for v in vs)
    return out


agree_A = agreement(ref_mean, fab_proc)
print("[gate 11] sign agreement across the three lineages, variant A:")
print("          agree : " + " ".join(p for p in PARTIES_ALL if agree_A[p]))
print("          split : " + " ".join(p for p in PARTIES_ALL if not agree_A[p]))
print("          FIGURE-DESIGN's three-second read ('for every party, the three")
print("          markers land on the same side') is NOT what the data shows.")
print("=" * 74)


# ---------------------------------------------------------------------------
# DRAW
# ---------------------------------------------------------------------------
def draw(ax, slot2: pd.Series, slot2_label: str, fabser: pd.Series, arrows: bool):
    order = sorted(PARTIES_ALL, key=lambda p: float(ours[p]))   # by our lineage's dim-2
    ypos = {p: i for i, p in enumerate(order)}

    # per-row spread band, behind everything
    for p in order:
        vs = [float(ours[p]), float(slot2[p]), float(fabser[p])]
        ax.plot([min(vs), max(vs)], [ypos[p]] * 2, color=C_BAND, lw=BAND_LW,
                solid_capstyle="round", zorder=1)

    # the zero rule, solid
    ax.axvline(0.0, color=C_RULE, lw=0.9, ls="-", zorder=2)

    # the two arrows: the reference's own 366 -> 368 movement, movers only
    if arrows:
        for p in MOVERS:
            if p not in ypos:
                continue
            a, b = mover_track[p][366], mover_track[p][368]
            ax.annotate("", xy=(b, ypos[p]), xytext=(a, ypos[p]),
                        arrowprops=dict(arrowstyle="-|>,head_width=0.13,head_length=0.30",
                                        color=C_REF, lw=1.0, shrinkA=0, shrinkB=0),
                        zorder=3)

    ax.scatter([float(ours[p]) for p in order], [ypos[p] + SLOT_DY for p in order],
               marker="o", s=18, color=C_OURS, edgecolor="none", zorder=5)
    ax.scatter([float(slot2[p]) for p in order], [ypos[p] for p in order],
               marker="s", s=15, color=C_REF, edgecolor="none", zorder=5)
    ax.scatter([float(fabser[p]) for p in order], [ypos[p] - SLOT_DY for p in order],
               marker="^", s=22, color=C_FAB, edgecolor="none", zorder=5)

    ax.set_yticks([ypos[p] for p in order])
    ax.set_yticklabels(order)
    for t, p in zip(ax.get_yticklabels(), order):
        if p in LABEL_PARTIES:
            t.set_color(C_INK); t.set_fontweight("bold")
        else:
            t.set_color(C_MUTED)
        t.set_fontsize(FS_TICK)

    ax.set_xlim(-0.72, 0.72)
    ax.set_ylim(-0.75, len(order) - 0.25)
    ax.set_xticks([-0.6, -0.3, 0.0, 0.3, 0.6])
    ax.set_xticklabels(["-0.6", "-0.3", "0", "0.3", "0.6"], fontsize=FS_TICK, color=C_MUTED)
    ax.set_xlabel("second-dimension party mean, gauged", fontsize=FS_LABEL, color=C_INK,
                  labelpad=2)
    ax.tick_params(axis="both", length=2.2, width=0.6, color=C_MUTED, pad=1.8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(C_MUTED)

    handles = [
        Line2D([], [], marker="o", ls="none", ms=3.9, mfc=C_OURS, mec="none",
               label="our engine, static P1-P3"),
        Line2D([], [], marker="s", ls="none", ms=3.5, mfc=C_REF, mec="none",
               label=slot2_label),
        Line2D([], [], marker="^", ls="none", ms=4.1, mfc=C_FAB, mec="none",
               label="Fabrega votes, our estimator"),
    ]
    if arrows:
        handles.append(Line2D([], [], marker=">", ls="-", lw=1.0, ms=3.2,
                              color=C_REF, mfc=C_REF, mec="none",
                              label="reference, leg. 366 to 368"))
    leg = ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.105),
                    ncol=2, frameon=False, fontsize=FS_LEG, handletextpad=0.35,
                    columnspacing=0.9, labelspacing=0.30, borderpad=0.0,
                    handlelength=1.0)
    for t in leg.get_texts():
        t.set_color(C_INK)
    return order


VARIANTS = {
    "fig6-triangulation": dict(
        slot2=("ref", "QueVotan reference"), fab="proc", arrows=True,
        note="A. slot 2 = QueVotan reference; Fabrega gauged by Procrustes onto the "
             "reference frame; the two crossing arrows drawn. RECOMMENDED."),
    "fig6-triangulation-B-rdgauge": dict(
        slot2=("ref", "QueVotan reference"), fab="anchor", arrows=True,
        note="B. as A but Fabrega gauged by the RD-anchored reflection used at "
             "build_fig_f1_poles.py:49. RD's Fabrega marker is definitional here."),
    "fig6-triangulation-C-noarrows": dict(
        slot2=("ref", "QueVotan reference"), fab="proc", arrows=False,
        note="C. as A with the crossing arrows removed. Does the fold earn its ink?"),
    "fig6-triangulation-D-indepslot": dict(
        slot2=("indep", "independent W-NOMINATE"), fab="anchor", arrows=False,
        note="D. faithful restyle of the existing off-paper F1_three_pipeline_dim2_poles.png: "
             "slot 2 is R wnominate on OUR matrices, NOT the QueVotan reference."),
}
SLOT2_SERIES = {"ref": ref_mean, "indep": indep}
FAB_SERIES = {"proc": fab_proc, "anchor": fab_anchor}

OUTDIR.mkdir(parents=True, exist_ok=True)
written, plotted_values = [], {}

for name, cfg in VARIANTS.items():
    s2key, s2label = cfg["slot2"]
    s2, fs = SLOT2_SERIES[s2key], FAB_SERIES[cfg["fab"]]
    fig = plt.figure(figsize=(COL_IN, FIG_H_IN))
    ax = fig.add_axes(AXES_RECT)
    order = draw(ax, s2, s2label, fs, cfg["arrows"])
    for ext, kw in ((".png", dict(dpi=400)), (".pdf", {})):
        p = OUTDIR / f"{name}_v1{ext}"
        fig.savefig(p, bbox_inches=None, pad_inches=0.01, **kw)
        written.append(str(p))
    plt.close(fig)
    plotted_values[name] = {
        "row_order_bottom_to_top": order,
        "slot1_ours": {p: round(float(ours[p]), 4) for p in order},
        "slot2": {p: round(float(s2[p]), 4) for p in order},
        "slot3_fabrega": {p: round(float(fs[p]), 4) for p in order},
        "sign_agreement": agreement(s2, fs),
        "arrows_drawn": ({p: {str(L): round(mover_track[p][L], 4) for L in PANEL_LEGS}
                          for p in MOVERS} if cfg["arrows"] else None),
    }
    print(f"wrote {name}_v1.png / .pdf   ({cfg['note'][:2]})")

# --- unversioned pointer at the primary variant, as the brief asks for <figname>.pdf
import shutil
shutil.copyfile(OUTDIR / f"{FIGNAME}_v1.pdf", OUTDIR / f"{FIGNAME}.pdf")
written.append(str(OUTDIR / f"{FIGNAME}.pdf"))

# --- contact sheet: the four variants side by side at true include width.
#     REVIEW ARTIFACT ONLY.  Never included in the paper.
sheet = plt.figure(figsize=(COL_IN * 4 + 0.2, FIG_H_IN + 0.28))
titles = ["A  reference + Procrustes + arrows", "B  reference + RD-anchor + arrows",
          "C  reference + Procrustes, no arrows", "D  indep slot + RD-anchor, no arrows"]
for i, (name, cfg) in enumerate(VARIANTS.items()):
    s2key, s2label = cfg["slot2"]
    left = (i * COL_IN + 0.05) / (COL_IN * 4 + 0.2)
    w = COL_IN / (COL_IN * 4 + 0.2)
    ax = sheet.add_axes((left + AXES_RECT[0] * w, AXES_RECT[1] * FIG_H_IN / (FIG_H_IN + 0.28),
                         AXES_RECT[2] * w, AXES_RECT[3] * FIG_H_IN / (FIG_H_IN + 0.28)))
    draw(ax, SLOT2_SERIES[s2key], s2label, FAB_SERIES[cfg["fab"]], cfg["arrows"])
    sheet.text(left + 0.5 * w, 0.975, titles[i], ha="center", va="top",
               fontsize=8, color=C_INK)
p = OUTDIR / f"{FIGNAME}-variants_v1.png"
sheet.savefig(p, dpi=200, bbox_inches=None, pad_inches=0.02)
plt.close(sheet)
written.append(str(p))
print(f"wrote {p.name}  (review contact sheet, 4 variants at true include width)")

# --- FIGURE-DESIGN 7.5: light / inverted / greyscale check on the primary variant.
#     A print figure cannot be theme-aware; the requirement is met structurally
#     (marker shape carries identity in parallel with hue, legend always present).
#     This renders the two hostile cases so the claim can be looked at.
img = plt.imread(OUTDIR / f"{FIGNAME}_v1.png")[:, :, :3]
inv = 1.0 - img
grey = np.repeat((img @ np.array([0.2126, 0.7152, 0.0722]))[:, :, None], 3, axis=2)
chk = plt.figure(figsize=(COL_IN * 3 + 0.2, FIG_H_IN + 0.28))
for i, (arr, lbl) in enumerate(((img, "as printed (white surface)"),
                                (inv, "reader inversion (dark mode)"),
                                (grey, "greyscale / full CVD"))):
    ax = chk.add_axes(((i * COL_IN + 0.06) / (COL_IN * 3 + 0.2), 0.005,
                       COL_IN / (COL_IN * 3 + 0.2) - 0.01, FIG_H_IN / (FIG_H_IN + 0.28)))
    ax.imshow(arr); ax.set_axis_off()
    chk.text((i * COL_IN + 0.06 + COL_IN / 2) / (COL_IN * 3 + 0.2), 0.985, lbl,
             ha="center", va="top", fontsize=8, color=C_INK)
p = OUTDIR / f"{FIGNAME}-rendercheck_v1.png"
chk.savefig(p, dpi=200, bbox_inches=None, pad_inches=0.02, facecolor="#ffffff")
plt.close(chk)
written.append(str(p))
print(f"wrote {p.name}  (7.5 light / inversion / greyscale check)")

# ---------------------------------------------------------------------------
# MANIFEST
# ---------------------------------------------------------------------------
manifest = {
    "figure": FIGNAME,
    "title": "Three lineages, one pole",
    "carries": "P5, triangulation of the static second-dimension cleavage",
    "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "generator": str(Path(__file__).resolve()),
    "generating_command": f"{sys.executable} \"{Path(__file__).resolve()}\"",
    "python": sys.version.split()[0],
    "numpy": np.__version__, "pandas": pd.__version__, "matplotlib": matplotlib.__version__,

    "panel_and_span": {
        "figure_span_stated_in_caption": "legislaturas 366-368",
        "slot1_ours": {
            "artifact": str(P_OURS),
            "span": "legislaturas 366-368, 25-unit sub-period split (units 21-25)",
            "sub_periods": {"P1": "units 21-22 (leg 366 + 367 pre-estallido)",
                            "P2": "units 23-24 (367 post-estallido + 368 pre-plebiscito)",
                            "P3": "unit 25 (368 post-plebiscito, truncated 2021-03-10)"},
            "engine": "our C++ DW-NOMINATE CLI, temporal model 0 (constant), 1 period, "
                      "2 dimensions, 4 iterations -> a static W-NOMINATE per sub-period",
            "legislators_per_fit": {"P1": 155, "P2": 158, "P3": 158},
            "note": "each of the three fits was rotated onto the QueVotan reference pooled "
                    "frame inside _req013_analysis.py:174-182 BEFORE the party means were "
                    "written; this generator does not re-rotate it",
        },
        "slot2_reference": {
            "artifact": str(P_REF_BYLEG),
            "span": "legislaturas 366, 367, 368 only; the artifact also holds 369 and "
                    "this generator drops it and asserts the drop",
            "roster_per_leg": {str(k): int(v) for k, v in roster.items()},
            "distinct_legislators": int(n_ref_legislators),
            "estimator": "QueVotan production per-votacion accumulating W-NOMINATE, "
                         "served by the platform, expert-ratified",
            "independence": "INDEPENDENT ESTIMATOR AND LINEAGE, NOT INDEPENDENT DATA. "
                            "It reads the same MongoDB dump as our panel "
                            "(build_julio_reference.py:37,:46 -> quevotanEtiquetado/"
                            "new_wnominate.bson). DESK-PLAN 5.3. Must never be drawn or "
                            "captioned as an independent vote record.",
            "aggregation": "per legislator, mean of that legislator's per-legislatura "
                           "medians over 366-368; then party mean",
            "aggregation_alternative_checked": "equal weight per legislatura; max "
                                               f"|difference| {float(_gap):.4f} over the plotted parties",
        },
        "slot2_alternative_variant_D": {
            "artifact": str(P_INDEP),
            "what_it_is": "three INDEPENDENT R wnominate runs on OUR P1/P2/P3 matrices "
                          "(_req017_ried_grain.py), anchor-only frame alignment, then "
                          "per-run Procrustes onto the reference pooled frame",
            "warning": "this is a different CODE lineage on the SAME curation. It is not "
                       "the QueVotan reference and must not be labelled as one. The "
                       "existing off-paper PNG plots this in slot 2.",
        },
        "slot3_fabrega": {
            "artifact": str(P_FAB),
            "span": "his full 2018-2022 period matrix = legislaturas 366-369, ONE "
                    "LEGISLATURA BEYOND our 366-368 panel. DATA-CONTRACT section 5 "
                    "records that his votes run past our snapshot. Not sliceable here.",
            "curation": "independently curated vote record (only ~10 percent roll-call id "
                        "overlap with ours, DATA-CONTRACT section 2)",
            "estimator": "OUR estimator (R wnominate, 2 dimensions, replica of his "
                         "pipeline). His published estimates are 1D only "
                         "(A_Ideology_Estimation.R:96 dims = 1) and are NOT used.",
            "legislators": int(len(fab)),
            "party_crosswalk": "julio_reference_periodo9_pooled.csv, first-observed "
                               "(static) party label per legislator",
        },
    },

    "alignment_operator": {
        "slot1_ours": "centred orthogonal Procrustes (rotation + reflection, no scaling) "
                      "onto the QueVotan reference pooled coordinates, applied per "
                      "sub-period upstream in _req013_analysis.py:24-28,174-182",
        "slot2_reference": "none; it is the target frame",
        "slot3_fabrega_variants_A_C": "centred orthogonal Procrustes onto the QueVotan "
                                      "reference pooled coordinates over the 163 shared "
                                      f"legislators; det(R) = {float(np.linalg.det(R)):+.6f}; "
                                      f"post-align r1 = {fab_r1:.4f}, r2 = {fab_r2:.4f} "
                                      f"(paper cites {EXPECT_FAB_REF_R2})",
        "slot3_fabrega_variants_B_D": f"reflection of dimension 2 only, sign chosen so the "
                                      f"{GAUGE_ANCHOR_PARTY} party mean is negative "
                                      f"(build_fig_f1_poles.py:49); flip = {flip:+.0f}. "
                                      f"Under this gauge {GAUGE_ANCHOR_PARTY}'s marker is "
                                      "DEFINITIONAL and carries no evidence.",
        "gauge_frame_source": "julio_reference_periodo9_pooled.csv, which pools legs "
                              "366-369. Used as a FRAME (a gauge choice), never as a "
                              "plotted series.",
        "padding": "not applicable; no correlation over a padded 340-row matrix is "
                   "computed. All means are over rows present in each artifact.",
        "fortran_arm": "none. This figure never touches dwnom2004_chile or "
                       "dwnom2004_chile_per_period, so the one-legislatura offset class "
                       "of FIGURE-DESIGN 5.1/5.2 cannot arise. Asserted at gate 0.",
    },

    "denominator_constant": {
        "value": DENOM_MED_SE_DIM2,
        "reason": "fig6 plots no ratio and no error band, so it has no denominator. "
                  "DENOM_MED_SE_DIM2 is declared at the top of the generator anyway so "
                  "the pablo-10 swap stays a one-line edit if this figure ever grows an "
                  "error bar. Never inline it.",
    },

    "lopsidedness_screen": {
        "threshold": LOPSIDEDNESS_THRESHOLD,
        "sites": ["main_cli.cpp:471", "dwnominate.cpp:187", "dwnom2004.f:324-326"],
        "does_this_figure_count_roll_calls_or_votes": False,
        "which_side_of_the_screen": {
            "slot1_ours": "POST-SCREEN. 2,665 roll calls loaded across P1+P2+P3 "
                          "(1,125 + 1,081 + 459); 1,772 carry a non-zero estimated "
                          "cutline, 893 are zeroed by the screen. Valid votes as loaded: "
                          "84,056 + 97,677 + 43,584 = 225,317.",
            "slot2_reference": "UNVERIFIED. 2,217 votaciones as served by the platform "
                               "(build_julio_reference.py docstring). The QueVotan "
                               "production pipeline's own screening was not inspected.",
            "slot3_fabrega": "POST-SCREEN. 3,520 roll calls in his matrix; R wnominate "
                             "dropped 1,227; 2,293 used (fabrega/run.log).",
        },
    },

    "rows_and_columns": {
        "rows": len(PARTIES_ALL),
        "row_unit": "party",
        "parties": PARTIES_ALL,
        "party_inclusion_rule": f"the 11 parties with n >= {MIN_PARTY_N} legislators in "
                                "statics_party_means.csv (_req013_analysis.py:189)",
        "columns": 3,
        "column_unit": "estimation lineage (three vertical slots inside each row)",
        "markers_per_row": 3,
        "total_markers": 3 * len(PARTIES_ALL),
        "row_order": "ascending by our lineage's second-dimension mean, negative pole at "
                     "the bottom",
    },

    "crossing_fold": {
        "what_was_folded_in": "fig:crossing's transferable content, i.e. two arrows and "
                              "one count",
        "arrows": "the QueVotan reference's own legislatura 366 -> 368 movement, drawn on "
                  "the UDI and EVOP rows only, in the reference's colour, through the "
                  "reference marker",
        "mover_track_reference_per_leg": {p: {str(L): round(mover_track[p][L], 4)
                                              for L in PANEL_LEGS} for p in MOVERS},
        "count_recomputed_here": f"{udi_flips} of {udi_n} UDI members change second-"
                                 "dimension sign between legislaturas 366 and 367 in "
                                 "julio_reference_periodo9_by_leg.csv",
        "count_published_in_the_paper": PUBLISHED_UDI_FLIP,
        "discrepancy": "the two do not agree. The published 22 of 26 is derived in "
                       "analysis/MAP3-udi-decomposition.md on a service-filtered set; "
                       "_investigation-2026-08-06/recovered3.md:1066 also records 23 of 26 "
                       "under contemporaneous party labels and 25 of 29 under static "
                       "labels, which is what this artifact reproduces. The figure prints "
                       "no count. Whichever number the caption uses must name its filter.",
        "control_parties_flips_over_n": {k: list(v) for k, v in ctl.items()},
    },

    "sign_agreement": {
        "note": "FIGURE-DESIGN's stated three-second read, 'for every party the three "
                "markers land on the same side of the zero rule', is NOT what the data "
                "shows. Seven of eleven parties agree in sign across the three lineages; "
                "four split, and the four are the right-bloc parties plus IND. RD, CS and "
                "PC, which are the parties the claim is about, do agree.",
        "per_variant": {k: v["sign_agreement"] for k, v in plotted_values.items()},
    },

    "values_plotted": plotted_values,

    "variants": {k: v["note"] for k, v in VARIANTS.items()},

    "visual_system": {
        "palette": {"slot1_ours": C_OURS, "slot2": C_REF, "slot3_fabrega": C_FAB,
                    "band": C_BAND, "primary_ink": C_INK, "muted_ink": C_MUTED,
                    "zero_rule": C_RULE},
        "palette_validation": "node scripts/validate_palette.js "
                              "\"#2a78d6,#eb6834,#4a3aa7\" --mode light --surface "
                              "\"#ffffff\" --pairs all  ->  ALL CHECKS PASS "
                              "(worst all-pairs CVD dE 13.0 deutan, normal-vision 16.3, "
                              "all >= 3:1 contrast). Re-run 2026-08-11.",
        "alpha_used": False,
        "authored_width_in": COL_IN,
        "figure_height_in": FIG_H_IN,
        "include_width": "\\columnwidth = 252 pt; include at width=\\columnwidth, scale 1.0",
        "estimated_col_pt": round(252 * FIG_H_IN / COL_IN),
        "bbox_inches": None,
        "pad_inches": 0.01,
        "pdf_fonttype": 42,
        "font_sizes": {"base": FS_BASE, "axis_label": FS_LABEL, "tick": FS_TICK,
                       "legend": FS_LEG},
        "numbers_inside_the_figure": "none (FIGURE-DESIGN 7.1); axis tick values only",
        "secondary_encoding": "marker shape carries lineage identity in parallel with hue "
                              "(o / square / triangle); legend always present; verified in "
                              "greyscale and under reader inversion in the rendercheck PNG",
    },

    "sources": {k: {"path": str(p), "md5": md5(p), "bytes": p.stat().st_size}
                for k, p in SOURCES.items()},

    "outputs": written,

    "gaps": [
        "The paper's published UDI crossing count (22 of 26) is not reproducible from "
        "julio_reference_periodo9_by_leg.csv, which gives 25 of 29. Not resolved here.",
        "The QueVotan reference's own lopsidedness screening is unverified.",
        "The Fabrega leg spans legislaturas 366-369 while the other two span 366-368. "
        "The artifact is not sliceable by legislatura without re-running his fit, which "
        "this run is forbidden to do.",
        "Slot 1 is Procrustes-rotated onto the reference frame upstream, so the two "
        "lineages' global dimension-2 gauge is shared by construction. Only the PATTERN "
        "across parties is evidence, not any single party's sign.",
    ],
}
mpath = OUTDIR / f"{FIGNAME}.manifest.json"
mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
print(f"wrote {mpath}")
print("done.")
