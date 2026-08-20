#!/usr/bin/env python3
"""fig7-declined-trajectory  --  GATE RUN, 2026-08-11.

FIGURE-DESIGN-2026-08-11.md section 3 (fig7) specifies a trajectory fan: the three
admitted frames' RD/CS second-dimension party means across legs 366-368, whose fan
is claimed to be "as wide as the movement being claimed" (~1.1 units).

FIGURE-DESIGN section 8 flags that claim as UNMEASURED and instructs that the
sub-minute global Procrustes be run BEFORE the figure is drafted, "because it could
come back narrow."

IT CAME BACK NARROW.  The measured cross-frame spread of the 366->368 trajectory is
0.080 (RD) and 0.044 (CS) coordinate units, against a reported movement of ~1.10.
The specified paper figure is therefore NOT drawn.  What this script emits instead
is a desk DIAGNOSTIC that renders the failed premise, plus the byproduct finding
(section "BYPRODUCT" below).  None of these is a paper float.

BYPRODUCT, and it is the reason this run mattered.  The trajectory fan is not small
everywhere.  Ranked over the 11 parties with n>=4, RD and CS have the SMALLEST fans
in the chamber.  The largest belong to EVOP (0.788) and UDI (0.450) -- the two
parties whose crossing the paper ASSERTS in fig:crossing.  In the QueVotan reference
lineage UDI moves -0.434 and 24 of 27 members flip sign across 366->368; in both
admitted C++ frames the same members move +0.017 / +0.005 and flip 0 of 27 and
3 of 27.  See the report for the caveats on that comparison.

NO FITTING IS DONE HERE.  Every input is an artifact already on disk.  The only
computation is a global orthogonal Procrustes and some means.

Deliberate departures from FIGURE-DESIGN section 7, all because this is a desk
diagnostic and not a paper float:
  * section 7.1 "no numbers inside any figure" is broken by the verdict header and
    the reference-magnitude label.  A diagnostic whose job is a verdict must state it.
  * the three-panel variants are taller than any paper float would be.
Everything else (3.5in author width, 8/8/7/7pt type, no alpha, no viridis, solid
hairline grid, legend outside the plotting area, vector PDF with fonttype 42) is
followed, so that if Roberto promotes the by-party panel it is already in register.

Usage:  python fig7-declined-trajectory.py
Env:    JCC_FIGDIR overrides the output directory.
"""
import csv
import glob
import hashlib
import json
import os
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

# ============================================================================
# NAMED CONSTANTS.  Nothing below inlines a magic number.
# ============================================================================

# Within-fit bootstrap SE, second dimension, median over the 482 active placements
# of legs 366-368.  RECOMPUTED HERE from the banked replicates, not transcribed;
# see check_se() -- it must equal this value or the script fails.
# route2_bigB B=150, base cpp_run_chile, CLPRR convention (centred on the point
# estimate X-hat, divisor B-1), matching _den_bigB.py:se_from().
# pablo-10 may replace this bank with a bootstrap on canary_fseed_i4.  That is a
# one-line edit of BOOT_BANK plus this constant.
DENOM_MED_SE_DIM2 = 0.0706  # route2_bigB B=150, base cpp_run_chile, legs 366-368 active
DENOM_MED_SE_DIM1 = 0.0330  # same bank, first dimension

# The movement the paper DECLINES to assert, in coordinate units.
# PROVENANCE IS WEAK AND MUST STAY LABELLED: these come from
# analysis/b2_pablo_run/build_fig_arrival_test.py:37, where FIGURE-DESIGN 3(fig7)
# records them as DIGITIZED FROM A SLIDE DECK -- RIED = {"RD": [(367, 0.633),
# (369, -0.470)], "CS": [(367, 0.503), (369, -0.444)]}.  main-rewrite-2026-08-05.tex:517
# states the same magnitude in prose as "more than a full unit".
# They are used ONLY as a reference LENGTH, never as a position, because they live
# in the conjecture's own frame and legs 367->369 is not this paper's panel.
CLAIMED_MOVEMENT_D2 = {"RD": 1.103, "CS": 0.947}
CLAIMED_MOVEMENT_SPAN = "legs 367->369 (the conjecture's span; NOT this paper's panel)"

# Gate targets from FIGURE-DESIGN 3(fig1)/_joint_niter4.out at k=16.  The script
# refuses to render if the admitted set does not reproduce them.
GATE_SD1, GATE_SD2 = 0.1416, 0.1944
GATE_FLIP1, GATE_FLIP2 = 0.05, 0.53
GATE_TOL_SD, GATE_TOL_FLIP = 0.002, 0.02

# Panel.  DATA-CONTRACT-2026-08-05.md section 4 / section 8.
PANEL_NAME = "reproduce/out/chile/cpp_input/"
PANEL_LEGS = "346-368"
PANEL_VOTES = 692839
PANEL_ROLLCALLS = 12952
FIG_LEGS = [366, 367, 368]

# Lopsidedness screen.  main_cli.cpp:471, dwnominate.cpp:187, dwnom2004.f:324-326.
# 0.025 minority threshold; 6,094 of 12,952 roll calls dropped on this panel.
# THIS FIGURE COUNTS NEITHER ROLL CALLS NOR VOTES.  It counts legislator-period
# placements and party members, so it sits downstream of the screen and the screen
# does not enter any quantity plotted.
LOPSIDED_THRESHOLD = 0.025
LOPSIDED_DROPPED, LOPSIDED_TOTAL = 6094, 12952

# Minimum party size at leg 366 for the by-party panel.  Below this a "party mean"
# is one or two legislators and is not a party mean.
MIN_PARTY_N = 4

# Palette, FIGURE-DESIGN 7.3, revalidated 2026-08-11 with
#   node scripts/validate_palette.js "#2a78d6,#eb6834,#4a3aa7" --mode light --surface "#ffffff" --pairs all
#   -> ALL CHECKS PASS
C_BLUE, C_ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"
SPAN_FILL, SPAN_EDGE = "#f0efec", "#c3c2b7"
# within-hue ramps, validated with --ordinal on 2026-08-11 -> ALL CHECKS PASS
RAMP_BLUE = ["#17417a", "#2a78d6", "#7fa9e8"]    # dark -> light
RAMP_ORANGE = ["#9c3d13", "#eb6834", "#f0a07c"]

# ============================================================================
# PATHS
# ============================================================================
REPO = Path("C:/Users/cow/Documents/GitHub/quevotan-db")
PAPER = Path("C:/Users/cow/Documents/thesis-quevotan/papers/jcc-2026")
MAP = REPO / "output/legislatura_map.csv"          # 24-period map, period 1 = leg 346
REF = REPO / "reproduce/out/chile/julio_reference_periodo9_by_leg.csv"
BOOT_BANK = REPO / "reproduce/out/chile/julio_test/route2_bigB"
OUTDIR = _paths.render_dir()   # was PAPER/"figs/v2026-08-11", a path the
                               # 2026-08-13 reorganization retired. Renders go to
                               # figures/renders/<date>/; survivors are copied into
                               # draft/figures/ by hand. reference-renders/ is frozen.

# The admitted set at k in [11,102]: 0 and 10 tolerance steps plus the external
# reference.  FIGURE-DESIGN 3(fig1), _joint_niter4.out, COMPUTE-RESULTS C1.
# cpp_run_chile (317 steps) and cpp_run_chile_p24_canon (24-period, 743,910 votes)
# are EXCLUDED -- they are the superseded 3.1x cell that defect 5.3 describes.
FRAMES = {
    "julio_reference": REF,
    "canary_fseed_i4": REPO / "reproduce/out/chile/canary_fseed_i4/cpp_coordinates_all_periods.csv",
    "cpp_run_chile_constseed": REPO / "reproduce/out/chile/cpp_run_chile_constseed/cpp_coordinates_all_periods.csv",
}
FRAME_ORDER = ["julio_reference", "canary_fseed_i4", "cpp_run_chile_constseed"]
FRAME_LABEL = {
    "julio_reference": "reference (0 steps)",
    "canary_fseed_i4": "canary_fseed_i4 (0)",
    "cpp_run_chile_constseed": "constseed (10)",
}
FRAME_MARKER = {"julio_reference": "o", "canary_fseed_i4": "s", "cpp_run_chile_constseed": "^"}
FRAME_LS = {"julio_reference": "-", "canary_fseed_i4": (0, (4, 1.6)), "cpp_run_chile_constseed": (0, (1.2, 1.4))}

# Alignment operator, named once and stated in every manifest.
ALIGNMENT = ("uncentred orthogonal Procrustes, SINGLE GLOBAL rotation over the stacked "
             "(legislatura, legislator) set of all 482 active placements on legs 366-368, "
             "each C++ frame onto julio_reference. Per-period rotation is NOT used: it "
             "hides cross-frame disagreement (recorded policy).")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_many(paths):
    """One digest over an ordered list of files (the 150-replicate bank)."""
    h = hashlib.md5()
    for p in paths:
        h.update(Path(p).name.encode())
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


# ============================================================================
# LOAD, WITH THE ALIGNMENT ASSERTED
# ============================================================================
P2LEG = {int(d["period_index"]): int(d["legislatura"]) for d in csv.DictReader(open(MAP))}

# NON-NEGOTIABLE 1, adapted.  This figure never touches the Fortran, so
# dwnom2004_chile_per_period does not enter.  What it MUST assert is the C++ panel
# offset that produced defects 5.1 and 5.2: the cpp_input panel is 346-368, so
# period 21/22/23 are legs 366/367/368.  If a future run swaps in a 347-369 panel
# this fails loudly instead of drawing leg 367 under a 366 label.
assert P2LEG[21] == 366 and P2LEG[22] == 367 and P2LEG[23] == 368, (
    f"PANEL OFFSET: period 21/22/23 map to {P2LEG[21]}/{P2LEG[22]}/{P2LEG[23]}, "
    f"expected 366/367/368. Refusing to draw (this is defect 5.1/5.2)."
)

ref_df = pd.read_csv(REF)
ref_df["legislatura"] = pd.to_numeric(ref_df["legislatura"], errors="coerce")
ref_df = ref_df.dropna(subset=["legislatura", "x", "y"])
ref_df["legislatura"] = ref_df["legislatura"].astype(int)
ref_df = ref_df[ref_df.legislatura.isin(FIG_LEGS)]
refmap = {(int(r.legislatura), int(r.legislator_id)): (float(r.x), float(r.y)) for r in ref_df.itertuples()}
party_of = {(int(r.legislatura), int(r.legislator_id)): r.partido for r in ref_df.itertuples()}


def load_cpp(path):
    d = pd.read_csv(path)
    d["leg"] = d.period.map(P2LEG)
    d = d[d.leg.isin(FIG_LEGS)]
    return {(int(r.leg), int(r.legislator_id)): (float(r.coord1D), float(r.coord2D)) for r in d.itertuples()}


fits = {n: load_cpp(p) for n, p in FRAMES.items() if n != "julio_reference"}

# ACTIVE ROWS ONLY (alignment rule 5.4 clause 3).  Committed matrices are 340 rows
# with 155/155/161 active; the reference roster is the active set.  Padded rows
# would move dim-1 agreement 0.9865 -> 0.970.
KEYS = sorted(k for k in refmap if all(k in f for f in fits.values()))
N_PER_LEG = {L: sum(1 for k in KEYS if k[0] == L) for L in FIG_LEGS}
assert len(KEYS) == 482, f"expected 482 active placements, got {len(KEYS)}"
assert N_PER_LEG == {366: 161, 367: 161, 368: 160}, N_PER_LEG

R = np.array([refmap[k] for k in KEYS])
LEG_ARR = np.array([k[0] for k in KEYS])
ID_ARR = np.array([k[1] for k in KEYS])
PARTY_ARR = np.array([party_of[k] for k in KEYS])


def procrustes_uncentred(A, B):
    """Single global uncentred orthogonal Procrustes of A onto B."""
    U, _, Vt = np.linalg.svd(A.T @ B)
    Q = U @ Vt
    return A @ Q, Q


ALIGNED = {"julio_reference": R}
ROT = {}
for name, f in fits.items():
    A = np.array([f[k] for k in KEYS])
    ALIGNED[name], ROT[name] = procrustes_uncentred(A, R)

# ============================================================================
# GATE.  Refuse to render if the admitted set does not reproduce the headline.
# ============================================================================
M2 = np.stack([ALIGNED[fr][:, 1] for fr in FRAME_ORDER])
M1 = np.stack([ALIGNED[fr][:, 0] for fr in FRAME_ORDER])
sd2 = float(np.median(M2.std(axis=0, ddof=0)))
sd1 = float(np.median(M1.std(axis=0, ddof=0)))
flip2 = float(np.mean(~((M2 > 0).all(axis=0) | (M2 < 0).all(axis=0))))
flip1 = float(np.mean(~((M1 > 0).all(axis=0) | (M1 < 0).all(axis=0))))
print(f"GATE  sd1={sd1:.4f} (want {GATE_SD1})  sd2={sd2:.4f} (want {GATE_SD2})")
print(f"GATE  flip1={flip1:.3f} (want {GATE_FLIP1})  flip2={flip2:.3f} (want {GATE_FLIP2})")
for got, want, tol, lab in ((sd1, GATE_SD1, GATE_TOL_SD, "sd1"), (sd2, GATE_SD2, GATE_TOL_SD, "sd2"),
                            (flip1, GATE_FLIP1, GATE_TOL_FLIP, "flip1"), (flip2, GATE_FLIP2, GATE_TOL_FLIP, "flip2")):
    assert abs(got - want) <= tol, f"GATE FAIL {lab}: {got:.4f} vs {want} (tol {tol})"
print("GATE  admitted set reproduces the headline. Alignment is correct.\n")


def check_se():
    """Recompute the denominator from the bank instead of trusting the constant."""
    files = [f for w in ("w0", "w1", "w2") for f in sorted(glob.glob(str(BOOT_BANK / w / "t*.npy")))]
    # plain unicode array, no allow_pickle (same as _den_bigB.py); refuse object arrays
    bkeys = np.load(BOOT_BANK / "keys.npy")
    Xref = np.load(BOOT_BANK / "Xref.npy")
    A = np.stack([np.load(f) for f in files])
    D = A - Xref[None, :, :]
    se = np.sqrt(np.nansum(D * D, axis=0) / (A.shape[0] - 1))   # CLPRR, _den_bigB.py:se_from
    parts = [k.split("|") for k in bkeys]
    blegid = np.array([int(a) for a, b in parts])
    bleg = np.array([P2LEG.get(int(b), -1) for a, b in parts])
    m = np.array([(l, i) in refmap for l, i in zip(bleg, blegid)])
    got1, got2 = float(np.median(se[m, 0])), float(np.median(se[m, 1]))
    assert int(m.sum()) == 482, f"bank/roster mismatch: {int(m.sum())}"
    assert abs(got2 - DENOM_MED_SE_DIM2) < 5e-4, f"DENOM_MED_SE_DIM2 {got2:.4f} != {DENOM_MED_SE_DIM2}"
    assert abs(got1 - DENOM_MED_SE_DIM1) < 5e-4, f"DENOM_MED_SE_DIM1 {got1:.4f} != {DENOM_MED_SE_DIM1}"
    print(f"DENOM recomputed from bank (B={A.shape[0]}): d1={got1:.4f} d2={got2:.4f}  OK")
    return files, A.shape[0], Xref, bkeys, se


BOOT_FILES, BOOT_B, BOOT_XREF, BOOT_KEYS, BOOT_SE = check_se()


def boot_se_of_party_trajectory(p, lo=366, hi=368):
    """Sampling SE of the SAME quantity the figure plots: the 366->368 change in a
    party's dim-2 mean.  Replicates are rotated into the reference frame by the
    fixed Q0 that carries the bank's point estimate onto the reference, so the
    quantity is expressed in the figure's own frame.

    CAVEAT, recorded in every manifest: the bank's base fit is cpp_run_chile, which
    is NOT one of the three admitted frames (317 tolerance steps).  This is a SCALE
    for "how much does a party-mean trajectory wobble under resampling", not the
    sampling error of any admitted frame.  It is printed, never drawn.
    """
    parts = [k.split("|") for k in BOOT_KEYS]
    blegid = np.array([int(a) for a, b in parts])
    bleg = np.array([P2LEG.get(int(b), -1) for a, b in parts])
    idx = {(l, i): j for j, (l, i) in enumerate(zip(bleg, blegid))}
    sel = np.array([idx[k] for k in KEYS])
    Xb = BOOT_XREF[sel]
    _, Q0 = procrustes_uncentred(Xb, R)
    files = BOOT_FILES
    mask_lo = (PARTY_ARR == p) & (LEG_ARR == lo)
    mask_hi = (PARTY_ARR == p) & (LEG_ARR == hi)
    point = (Xb @ Q0)[mask_hi, 1].mean() - (Xb @ Q0)[mask_lo, 1].mean()
    deltas = []
    for f in files:
        R_h = (np.load(f)[sel] @ Q0)
        deltas.append(R_h[mask_hi, 1].mean() - R_h[mask_lo, 1].mean())
    deltas = np.array(deltas)
    return float(np.sqrt(np.nansum((deltas - point) ** 2) / (len(deltas) - 1))), float(point)


# ============================================================================
# MEASURE
# ============================================================================
rows = []
for p in sorted(set(PARTY_ARR)):
    n366 = int(((PARTY_ARR == p) & (LEG_ARR == 366)).sum())
    rec = {"party": p, "n_366": n366}
    for fr in FRAME_ORDER:
        for L in FIG_LEGS:
            m = (PARTY_ARR == p) & (LEG_ARR == L)
            rec[f"{fr}|{L}"] = float(ALIGNED[fr][m, 1].mean())
    deltas = {fr: rec[f"{fr}|368"] - rec[f"{fr}|366"] for fr in FRAME_ORDER}
    rec["traj_fan"] = max(deltas.values()) - min(deltas.values())
    rec["max_abs_delta"] = max(abs(v) for v in deltas.values())
    rec["level_fan_med"] = float(np.median([
        max(rec[f"{fr}|{L}"] for fr in FRAME_ORDER) - min(rec[f"{fr}|{L}"] for fr in FRAME_ORDER)
        for L in FIG_LEGS]))
    for fr in FRAME_ORDER:
        rec[f"delta|{fr}"] = deltas[fr]
    rows.append(rec)
T = pd.DataFrame(rows).set_index("party")

print("=== fig7 GATE: cross-frame spread of the 366->368 dim-2 party-mean trajectory ===")
print(f"panel {PANEL_NAME} legs {PANEL_LEGS}; figure legs {FIG_LEGS}; "
      f"{len(KEYS)} active placements ({N_PER_LEG})")
for p in ("RD", "CS"):
    d = {fr: T.loc[p, f"delta|{fr}"] for fr in FRAME_ORDER}
    se_traj, pt = boot_se_of_party_trajectory(p)
    print(f"  {p}: deltas " + "  ".join(f"{FRAME_LABEL[fr].split(' ')[0]}={v:+.4f}" for fr, v in d.items()))
    print(f"      cross-frame TRAJECTORY fan = {T.loc[p,'traj_fan']:.4f}   "
          f"reported movement = {CLAIMED_MOVEMENT_D2[p]:.3f}   "
          f"fan / reported = {T.loc[p,'traj_fan']/CLAIMED_MOVEMENT_D2[p]:.1%}")
    print(f"      median cross-frame LEVEL fan = {T.loc[p,'level_fan_med']:.4f}   "
          f"bootstrap SE of this same trajectory = {se_traj:.4f} (scale only, base cpp_run_chile)")
print()
print("=== by party (n>=%d at leg 366), ranked by trajectory fan ===" % MIN_PARTY_N)
BY = T[T.n_366 >= MIN_PARTY_N].sort_values("traj_fan")
print(BY[["n_366", "traj_fan", "max_abs_delta", "level_fan_med"]].round(4).to_string())
print()

GATE_VERDICT = "FAILED"
GATE_REASON = (
    f"FIGURE-DESIGN 3(fig7) premise: the admitted frames' trajectory fan is as wide as the "
    f"~1.1-unit reported movement. MEASURED: RD fan {T.loc['RD','traj_fan']:.4f} "
    f"({T.loc['RD','traj_fan']/CLAIMED_MOVEMENT_D2['RD']:.0%} of reported), "
    f"CS fan {T.loc['CS','traj_fan']:.4f} "
    f"({T.loc['CS','traj_fan']/CLAIMED_MOVEMENT_D2['CS']:.0%}). Premise not supported. "
    f"The specified paper figure is NOT drawn."
)
print("GATE VERDICT:", GATE_VERDICT)
print(GATE_REASON, "\n")

# ============================================================================
# RENDER.  Diagnostics only.
# ============================================================================
matplotlib.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.major.size": 2.2, "ytick.major.size": 2.2,
    "grid.color": GRID, "grid.linewidth": 0.5, "grid.linestyle": "-",
    "axes.grid": False, "figure.dpi": 300, "savefig.dpi": 300,
})
COLW_IN = 3.5   # \columnwidth = 252pt.  Author here, never scale.
OUTDIR.mkdir(parents=True, exist_ok=True)


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelcolor=MUTED)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)


def draw_party(ax, p, by_lightness, ylim):
    """One party's dim-2 mean across 366-368, one line per admitted frame.
    Faceted by party: hue is a panel constant, so the only series is the frame and
    one legend describes the whole figure."""
    base, ramp = (C_BLUE, RAMP_BLUE) if p == "RD" else (C_ORANGE, RAMP_ORANGE)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, lw=0.5, ls="-")
    for j, fr in enumerate(FRAME_ORDER):
        y = [T.loc[p, f"{fr}|{L}"] for L in FIG_LEGS]
        col = ramp[j] if by_lightness else base
        ls = "-" if by_lightness else FRAME_LS[fr]
        ax.plot(FIG_LEGS, y, ls=ls, lw=1.2, color=col, zorder=3,
                marker=FRAME_MARKER[fr], ms=3.2, mew=0.0,
                markerfacecolor=col, markeredgecolor="none", clip_on=False)
    ax.set_xticks(FIG_LEGS)
    ax.set_xlim(365.6, 368.4)
    ax.set_ylim(*ylim)
    ax.set_ylabel("dim-2 party mean", labelpad=2)
    style(ax)


def draw_byparty(ax, label_x=True):
    order = BY.index.tolist()
    ypos = np.arange(len(order))
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, lw=0.5, ls="-")
    for i, p in enumerate(order):
        a, b = T.loc[p, "traj_fan"], T.loc[p, "max_abs_delta"]
        ax.plot([min(a, b), max(a, b)], [i, i], color=GRID, lw=2.2, zorder=1,
                solid_capstyle="round")
    # diamond drawn on top carries a thin surface ring, the dataviz separator for
    # overlapping marks (a separator, not an encoding -- 7.5 stays satisfied)
    ax.scatter(BY["traj_fan"], ypos, s=18, marker="o", color=C_BLUE, zorder=3,
               edgecolor="none", label="spread across the 3 frames")
    ax.scatter(BY["max_abs_delta"], ypos, s=18, marker="D", color=C_ORANGE, zorder=4,
               edgecolor="#ffffff", linewidth=0.55, label="largest in any one frame")
    claim = CLAIMED_MOVEMENT_D2["RD"]
    ax.axvline(claim, color=INK, lw=0.8, ls=(0, (5, 2.5)), zorder=2)
    ax.text(claim - 0.035, (len(order) - 1) / 2.0, "reported movement", fontsize=6.4,
            color=INK, ha="center", va="center", rotation=90)
    ax.set_yticks(ypos)
    ax.set_yticklabels(order)
    # emphasis is WEIGHT, not hue: text never wears a series colour (dataviz rule).
    # bold = the four parties the paper makes a claim about.
    for t, p in zip(ax.get_yticklabels(), order):
        t.set_color(INK if p in ("RD", "CS", "UDI", "EVOP") else MUTED)
        if p in ("RD", "CS", "UDI", "EVOP"):
            t.set_fontweight("bold")
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xlim(-0.03, claim + 0.055)
    if label_x:
        ax.set_xlabel("dim-2 movement, 366$\\rightarrow$368", labelpad=1.5)
    style(ax)


def frame_legend_handles(by_lightness):
    """Frame identity. In the lightness variant the swatches use the blue ramp;
    the orange facet applies the identical dark-to-light ordering."""
    hs = []
    for j, fr in enumerate(FRAME_ORDER):
        col = RAMP_BLUE[j] if by_lightness else INK
        ls = "-" if by_lightness else FRAME_LS[fr]
        hs.append(Line2D([], [], color=col, ls=ls, lw=1.2, marker=FRAME_MARKER[fr],
                         ms=3.2, markerfacecolor=col, markeredgecolor="none",
                         label=FRAME_LABEL[fr]))
    return hs


def verdict_header(fig):
    fig.text(0.008, 0.995,
             "GATE FAILED \u2014 not a paper figure. Measured cross-frame trajectory fan: "
             f"RD {T.loc['RD','traj_fan']:.3f}, CS {T.loc['CS','traj_fan']:.3f}, "
             f"against a reported movement of {CLAIMED_MOVEMENT_D2['RD']:.2f}.",
             fontsize=6.0, color=INK, va="top", ha="left", wrap=True)


def save(fig, name):
    png, pdf = OUTDIR / f"{name}_v1.png", OUTDIR / f"{name}_v1.pdf"
    # NEVER bbox_inches='tight' (7.4): it changes the emitted canvas so
    # \includegraphics[width=\columnwidth] no longer renders at scale 1.0.
    fig.savefig(png, bbox_inches=None, pad_inches=0.01, dpi=300)
    fig.savefig(pdf, bbox_inches=None, pad_inches=0.01)
    plt.close(fig)
    print("wrote", png)
    print("wrote", pdf)
    return png, pdf


def build_three_panel(by_lightness, name):
    fig, axes = plt.subplots(3, 1, figsize=(COLW_IN, 6.05), layout="constrained")
    fig.get_layout_engine().set(h_pad=0.035, w_pad=0.02, hspace=0.06, rect=(0, 0, 1, 0.972))
    lo = min(T.loc[p, f"{fr}|{L}"] for p in ("RD", "CS") for fr in FRAME_ORDER for L in FIG_LEGS)
    hi = max(T.loc[p, f"{fr}|{L}"] for p in ("RD", "CS") for fr in FRAME_ORDER for L in FIG_LEGS)
    pad = 0.06 * (hi - lo)
    draw_trajectories(axes[0], by_lightness, (-0.62, 0.62), True,
                      "dim-2 party mean")
    draw_trajectories(axes[1], by_lightness, (lo - pad, hi + pad), False,
                      "dim-2 party mean")
    draw_byparty(axes[2])
    for ax, tag in zip(axes, ("(a) at the scale of the reported claim",
                              "(b) same series, y-axis zoomed to the fits",
                              "(c) every party with n$\\geq$%d, ranked" % MIN_PARTY_N)):
        ax.set_title(tag, loc="left", fontsize=7.2, color=INK, pad=2.5)
    h1 = frame_legend_handles(by_lightness)
    h2 = [Line2D([], [], ls="none", marker="o", ms=4, color=C_BLUE,
                 label="spread across the 3 admitted frames"),
          Line2D([], [], ls="none", marker="D", ms=4, color=C_ORANGE,
                 label="largest movement in any one frame")]
    fig.legend(handles=h1 + h2, loc="outside lower center", ncol=2, frameon=False,
               handlelength=1.9, columnspacing=1.0, handletextpad=0.5,
               labelcolor=INK, borderaxespad=0.2)
    verdict_header(fig)
    return save(fig, name)


def build_byparty_only(name):
    fig, ax = plt.subplots(figsize=(COLW_IN, 2.45), layout="constrained")
    fig.get_layout_engine().set(h_pad=0.03, w_pad=0.02, rect=(0, 0, 1, 1))
    draw_byparty(ax)
    ax.legend(loc="lower right", frameon=False, handletextpad=0.4,
              borderaxespad=0.3, labelcolor=INK, scatterpoints=1)
    return save(fig, name)


OUT_A = build_three_panel(True, "fig7-declined-trajectory-GATE")
OUT_B = build_three_panel(False, "fig7-declined-trajectory-GATE-linestyle")
OUT_C = build_byparty_only("fig7-declined-trajectory-BYPARTY")

# ============================================================================
# MANIFESTS
# ============================================================================
CMD = f"python {Path(__file__).name}"
SRC = {
    "legislatura_map": {"path": str(MAP), "md5": md5(MAP),
                        "note": "24-period map; period_index 1 = leg 346. reproduce/input/legislatura_map.csv "
                                "is the OTHER panel (347-369) and is NOT used."},
    "julio_reference_periodo9_by_leg": {"path": str(REF), "md5": md5(REF)},
    "canary_fseed_i4": {"path": str(FRAMES["canary_fseed_i4"]), "md5": md5(FRAMES["canary_fseed_i4"])},
    "cpp_run_chile_constseed": {"path": str(FRAMES["cpp_run_chile_constseed"]),
                                "md5": md5(FRAMES["cpp_run_chile_constseed"])},
    "route2_bigB_keys": {"path": str(BOOT_BANK / "keys.npy"), "md5": md5(BOOT_BANK / "keys.npy")},
    "route2_bigB_Xref": {"path": str(BOOT_BANK / "Xref.npy"), "md5": md5(BOOT_BANK / "Xref.npy")},
    "route2_bigB_replicates": {"path": str(BOOT_BANK) + "/w{0,1,2}/t*.npy",
                               "n_files": len(BOOT_FILES), "B": BOOT_B,
                               "md5_of_ordered_concat": md5_many(BOOT_FILES)},
}

boot_traj = {p: dict(zip(("se", "point"), boot_se_of_party_trajectory(p))) for p in ("RD", "CS")}


def manifest(name, files, panels, extra):
    m = {
        "figure": name,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generating_command": CMD,
        "generator": str(Path(__file__).resolve()),
        "python": sys.version.split()[0],
        "matplotlib": matplotlib.__version__, "numpy": np.__version__, "pandas": pd.__version__,
        "status": "DIAGNOSTIC. NOT A PAPER FIGURE.",
        "gate": {
            "verdict": GATE_VERDICT,
            "reason": GATE_REASON,
            "specified_figure_drawn": False,
            "spec": "FIGURE-DESIGN-2026-08-11.md section 3, fig7-declined-trajectory",
            "spec_warning_honoured": "FIGURE-DESIGN section 8: 'fig7's fan width is unmeasured ... "
                                     "it should be run before the figure is drafted, not after, "
                                     "because it could come back narrow.' It came back narrow.",
            "headline_reproduction": {"sd1": round(sd1, 4), "sd2": round(sd2, 4),
                                      "flip1": round(flip1, 4), "flip2": round(flip2, 4),
                                      "targets": {"sd1": GATE_SD1, "sd2": GATE_SD2,
                                                  "flip1": GATE_FLIP1, "flip2": GATE_FLIP2},
                                      "source_of_targets": "_joint_niter4.out at k=16, via FIGURE-DESIGN 3(fig1)"},
        },
        "panel": {
            "name": PANEL_NAME, "legislatura_span": PANEL_LEGS,
            "valid_votes": PANEL_VOTES, "rollcalls": PANEL_ROLLCALLS,
            "figure_legislaturas": FIG_LEGS,
            "period_to_legislatura": {str(k): P2LEG[k] for k in (21, 22, 23)},
            "asserted_in_code": "P2LEG[21,22,23] == 366,367,368; AssertionError otherwise",
            "data_contract": "DATA-CONTRACT-2026-08-05.md sections 4 and 8",
            "note": "This figure never reads a Fortran run, so dwnom2004_chile vs "
                    "dwnom2004_chile_per_period does not arise. The offset class it CAN hit "
                    "is the C++ 346-368 vs 347-369 panel swap, which is asserted.",
        },
        "frames": {
            "admitted_set": FRAME_ORDER,
            "rule": "k in [11,102] tolerance steps: 0 (canary_fseed_i4), 10 (cpp_run_chile_constseed), "
                    "plus the external QueVotan reference. F=3.",
            "excluded": {"cpp_run_chile": "317 tolerance steps",
                         "cpp_run_chile_p24_canon": "24-period fit, 743,910 votes, wrong panel"},
        },
        "alignment_operator": ALIGNMENT,
        "rotations": {k: np.round(v, 6).tolist() for k, v in ROT.items()},
        "rotation_determinants": {k: round(float(np.linalg.det(v)), 6) for k, v in ROT.items()},
        "rows_and_columns": {
            "active_placements_total": len(KEYS),
            "per_legislatura": {str(k): v for k, v in N_PER_LEG.items()},
            "padded_rows_excluded": "yes; roster = julio_reference active rows (340-row matrices "
                                    "carry 155/155/161 active). Alignment rule 5.4 clause 3.",
            "parties_measured": int(T.shape[0]),
            "parties_plotted_in_panel_c": int(BY.shape[0]),
            "min_party_n_at_leg_366": MIN_PARTY_N,
            "parties_dropped_for_size": sorted(T[T.n_366 < MIN_PARTY_N].index.tolist()),
        },
        "denominator_constants": {
            "DENOM_MED_SE_DIM2": DENOM_MED_SE_DIM2,
            "DENOM_MED_SE_DIM1": DENOM_MED_SE_DIM1,
            "source": "route2_bigB, B=150, base cpp_run_chile, CLPRR convention (centred on X-hat, "
                      "divisor B-1) per _den_bigB.py:se_from; median over the 482 active placements "
                      "of legs 366-368",
            "recomputed_not_transcribed": True,
            "swap_note": "pablo-10 may replace this with a bootstrap on canary_fseed_i4: edit "
                         "BOOT_BANK and these two constants. One-line each. Never inlined.",
            "used_in_this_figure": "NOT DRAWN. Printed only, as a scale for the fan.",
        },
        "claimed_movement": {
            "values": CLAIMED_MOVEMENT_D2,
            "span": CLAIMED_MOVEMENT_SPAN,
            "provenance": "DIGITIZED FROM A SLIDE DECK. analysis/b2_pablo_run/build_fig_arrival_test.py:37, "
                          "flagged as digitized by FIGURE-DESIGN 3(fig7). Prose twin at "
                          "main-rewrite-2026-08-05.tex:517 ('more than a full unit').",
            "drawn_as": "a LENGTH only (double-headed arrow / vertical rule), never a position, "
                        "because it lives in the conjecture's own frame and its span "
                        "(367-369) is not this paper's panel.",
        },
        "lopsidedness_screen": {
            "threshold": LOPSIDED_THRESHOLD,
            "dropped_of_total": [LOPSIDED_DROPPED, LOPSIDED_TOTAL],
            "sources": ["main_cli.cpp:471", "dwnominate.cpp:187", "dwnom2004.f:324-326"],
            "which_side": "DOWNSTREAM. This figure counts legislator-period placements and party "
                          "members, not roll calls or votes. The screen has already been applied "
                          "upstream by both engines and no quantity plotted here is a roll-call count.",
        },
        "numbers_plotted": extra,
        "source_artifacts": SRC,
        "files": [str(p) for p in files],
        "panels": panels,
        "visual_system": {
            "authored_width_in": COLW_IN,
            "column_width_pt": 252,
            "include_at": "\\includegraphics[width=\\columnwidth]{...} scale 1.0",
            "bbox_inches": None, "pad_inches": 0.01, "pdf.fonttype": 42,
            "palette": {"blue": C_BLUE, "orange": C_ORANGE, "ink": INK, "muted": MUTED, "grid": GRID,
                        "ramp_blue": RAMP_BLUE, "ramp_orange": RAMP_ORANGE},
            "palette_validation": "validate_palette.js '#2a78d6,#eb6834,#4a3aa7' --mode light "
                                  "--surface '#ffffff' --pairs all -> ALL PASS; both within-hue ramps "
                                  "--ordinal -> ALL PASS (2026-08-11)",
            "alpha_used": False, "viridis_used": False, "white_halos": False,
            "deliberate_departures": [
                "FIGURE-DESIGN 7.1 'no numbers inside any figure' is broken by the verdict header "
                "and the reference-magnitude label. This is a desk diagnostic whose job is a verdict.",
                "Three-panel height exceeds any paper float budget. Not intended as a float.",
            ],
        },
        "not_established": [
            "Whether the flatness of the two C++ frames is an identification result or a model-order "
            "artifact. 17 of 20 RD and 9 of 12 CS placements carry effective_model = 0 (constant "
            "trajectory) in BOTH admitted C++ frames, so most of those members cannot move by "
            "construction. Measured, not inferred: see per_member_model_order.",
            "Whether the UDI/EVOP byproduct is an identification failure or an estimator-class "
            "difference. julio_reference is an independent per-legislatura scaling with no "
            "cross-period constraint; the C++ frames are DW-NOMINATE polynomial trajectories with "
            "order selection. Those classes are not expected to agree on movement a priori.",
            "The bootstrap SE of the party-mean trajectory is computed on the route2_bigB bank whose "
            "base is cpp_run_chile, NOT an admitted frame. Scale only.",
        ],
        "per_member_model_order": {
            "note": "effective_model column of cpp_coordinates_all_periods.csv; 0 = constant, "
                    "2 = quadratic. Counted over active placements on legs 366-368.",
            "canary_fseed_i4": {"RD": {"0": 17, "2": 3}, "CS": {"0": 9, "2": 3},
                                "UDI": {"0": 24, "2": 57}, "EVOP": {"0": 18}},
            "cpp_run_chile_constseed": {"RD": {"0": 17, "2": 3}, "CS": {"0": 9, "2": 3},
                                        "UDI": {"0": 24, "2": 57}, "EVOP": {"0": 18}},
        },
        "bootstrap_se_of_plotted_trajectory": boot_traj,
    }
    m.update(extra.get("_top", {}))
    p = OUTDIR / f"{name}.manifest.json"
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", p)


NUMBERS = {
    "quantity": "second-dimension party mean, per legislatura, per admitted frame, after the "
                "single global Procrustes",
    "rd_cs_detail": {
        p: {
            "n_members": {str(L): int(((PARTY_ARR == p) & (LEG_ARR == L)).sum()) for L in FIG_LEGS},
            "means": {fr: {str(L): round(float(T.loc[p, f"{fr}|{L}"]), 4) for L in FIG_LEGS}
                      for fr in FRAME_ORDER},
            "delta_366_to_368": {fr: round(float(T.loc[p, f"delta|{fr}"]), 4) for fr in FRAME_ORDER},
            "cross_frame_trajectory_fan": round(float(T.loc[p, "traj_fan"]), 4),
            "median_cross_frame_level_fan": round(float(T.loc[p, "level_fan_med"]), 4),
            "reported_movement": CLAIMED_MOVEMENT_D2[p],
            "fan_as_share_of_reported": round(float(T.loc[p, "traj_fan"]) / CLAIMED_MOVEMENT_D2[p], 4),
        } for p in ("RD", "CS")
    },
    "by_party_ranked": {
        p: {"n_366": int(BY.loc[p, "n_366"]),
            "traj_fan": round(float(BY.loc[p, "traj_fan"]), 4),
            "max_abs_delta": round(float(BY.loc[p, "max_abs_delta"]), 4),
            "level_fan_med": round(float(BY.loc[p, "level_fan_med"]), 4),
            "delta_per_frame": {fr: round(float(T.loc[p, f"delta|{fr}"]), 4) for fr in FRAME_ORDER}}
        for p in BY.sort_values("traj_fan", ascending=False).index
    },
    "robustness": {
        "balanced_roster_only": {"RD": 0.0868, "CS": 0.0437,
                                 "note": "members present in all three legislaturas, n=480"},
        "centred_procrustes": {"RD": 0.0801, "CS": 0.0442},
        "subspan_367_to_368": {"RD": 0.0387, "CS": 0.0433},
        "note": "verdict is unchanged under every variant; computed in the gate run, "
                "not re-emitted by this script",
    },
}

PANELS_3 = [
    {"id": "a", "content": "RD and CS dim-2 party means, legs 366-368, one line per admitted frame, "
                           "y-axis spanning the reported movement; the reported movement drawn once "
                           "as a length"},
    {"id": "b", "content": "identical series, y-axis zoomed to the fits, so the level fan is legible"},
    {"id": "c", "content": f"cross-frame trajectory fan and largest single-frame movement, one row per "
                           f"party with n>={MIN_PARTY_N} at leg 366, ranked"},
]
manifest("fig7-declined-trajectory-GATE", OUT_A, PANELS_3,
         {**NUMBERS, "variant": "frames encoded by LIGHTNESS within party hue (as FIGURE-DESIGN 3(fig7) "
                                "specifies) plus marker shape"})
manifest("fig7-declined-trajectory-GATE-linestyle", OUT_B, PANELS_3,
         {**NUMBERS, "variant": "frames encoded by LINESTYLE at full hue strength plus marker shape; "
                                "every line clears 3:1 on white, which the lightness ramp's light end "
                                "(2.09-2.40:1) does not"})
manifest("fig7-declined-trajectory-BYPARTY", OUT_C, [PANELS_3[2]],
         {**NUMBERS, "variant": "panel (c) alone at true single-column include size. The ONLY object "
                                "from this run that could plausibly earn a page slot, and it carries a "
                                "byproduct finding about fig:crossing, not about fig7."})
print("\nDONE. Specified paper figure NOT drawn: gate failed.")
