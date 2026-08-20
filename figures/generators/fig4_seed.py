#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fig4-seed  --  "The seed is the frame".

Carries phenomenon P3 of FIGURE-DESIGN-2026-08-11.md section 3.  Dumbbell,
single column, three rows (legislaturas 366, 367, 368).  Each row carries the
cross-engine Procrustes correlation between our C++ DW-NOMINATE and the 2004
Fortran under a MATCHED seed frame and under a MISMATCHED one.  Both arms hold
the panel matched.  The first dimension is drawn muted so the reader sees it
refuse to move under the same manipulation.

This is a NEW generator.  It does not patch, import from, or share code with
`reproduce/scripts/build_fig_seed_is_frame.py`, which carries the confirmed
one-legislatura offset documented in FIGURE-DESIGN 5.2 (its panel (a) reads
`dwnom2004_chile`, whose period 23 is leg 369, while its panel (b) reads
`dwnom2004_chile_full_seeds`, whose period 23 is leg 368; the two panels are
therefore not comparable and the caption calls both "legislatura 368").


PANEL, stated once and asserted below
-------------------------------------
Legislaturas 346-368, 23 periods, 12,952 roll calls, 692,839 valid votes,
`reproduce/out/chile/cpp_input/` (DATA-CONTRACT-2026-08-05.md section 4).
Both engines, both arms, all three legislaturas plotted are on this panel and
on no other.  `reproduce/out/dwnom2004_chile` (legs 347-369) is NEVER read;
FORBIDDEN_FORTRAN below makes that a hard failure rather than a convention.


THE DENOMINATOR
---------------
This figure has NO bootstrap-standard-error denominator, and that is a
property of the quantity rather than an omission.  What is plotted is a
Procrustes correlation, which is already dimensionless and already bounded on
[-1, 1]; nothing is divided by anything.  The named-constant discipline of
`fig1-asymmetry` / `fig2-admissibility` (e.g. DENOM_MED_SE_DIM2 = 0.0706) has
no site here, and if `pablo-10` replaces that bootstrap bank with one on
`canary_fseed_i4` **this figure does not move at all**.  See DENOMINATOR below,
which is `None` and is written into the manifest as `None` on purpose.


THE LOPSIDEDNESS SCREEN
-----------------------
Both engines drop roll calls whose minority side falls under 0.025
(`main_cli.cpp:471`, `dwnominate.cpp:187`, `dwnom2004.f:324-326`); on this
panel that is 6,094 of 12,952.  This figure counts LEGISLATOR PLACEMENTS
(n = 155 / 155 / 161), never roll calls and never votes, so the screen enters
no plotted count.  The coordinates plotted are of course post-screen fits.
Recorded in the manifest as `side_of_screen: "post-screen fits, no roll-call
count plotted"`.


ALIGNMENT, all three choices of FIGURE-DESIGN 5.4 stated
--------------------------------------------------------
1. Panel offset.  Fortran run is `reproduce/out/dwnom2004_chile_per_period`.
   Its `us.num` line 1 is `1 25 119 119`, i.e. period 1 carries 25 roll calls
   and 119 legislators, which is legislatura 346.  Its period index therefore
   maps to legislatura identically to the C++ runs (period p -> leg 345+p).
   ASSERTED: the full 23-row `us.num` is compared row-by-row against
   `output/legislatura_map.csv` rows for legs 346-368, on BOTH the roll-call
   count and the legislator count.  A one-legislatura slip anywhere in the
   panel fails the assertion, not just at row 1.
2. Procrustes convention.  UNCENTRED orthogonal Procrustes of the C++ block
   onto the Fortran block, one rotation per (legislatura, arm), computed as
   R = U V^T from svd(A^T B).  This is the operator used by
   `reproduce/scripts/_contam_amp_offset.py`, which produced the values
   transcribed in FIGURE-DESIGN section 3, so the gate below is meaningful.
   It is NOT the centred operator of `procrustes_per_congress.py:34-44` used
   by `tab:fidelity`.  The caption must say "uncentred".
3. Padding.  The committed C++ coordinate matrices are padded: they emit 338
   rows for every period regardless of who was active.  The Fortran
   `us_legout.dat` emits the active roster only (155 / 155 / 161, matching
   `output/legislatura_map.csv`).  The inner join on the Fortran roster
   therefore enforces active-rows-only structurally.  ASSERTED: the joined row
   count equals `output/legislatura_map.csv:num_legislators` exactly.

Roster rule.  ACTIVE = the Fortran per-period run's own emitted roster for that
period.  FIGURE-DESIGN section 3 transcribes n = 155/155/160, which came from
`_contam_amp_offset.py` gating additionally on the QueVotan reference roster.
That gate drops legislator 1033 from leg 368 for no reason internal to a
two-engine comparison, so it is not used here; the difference it makes is
r2 0.619 -> 0.617 (matched) and 0.396 -> 0.391 (mismatched).  Both roster
rules are computed, printed, and written to the manifest.


VARIANTS
--------
Three layouts are rendered because the placement of the first dimension is an
open design decision that FIGURE-DESIGN section 3 does not settle ("a second,
muted marker pair").  Nothing else differs between them: identical data,
identical alignment, identical axis range.

  a  compact   3 rows, dim-1 as a small open pair under each dim-2 dumbbell
  b  split     3 legislatura groups, dim-2 and dim-1 on separate sub-rows
  c  faceted   two stacked panels sharing x, (a) dim 2 and (b) dim 1

Usage
-----
    python fig4_seed.py                 # renders all three variants + sheets
    JCC_FIGDIR=... python fig4_seed.py  # override the output directory
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = Path("C:/Users/cow/Documents/GitHub/quevotan-db")
PAPER = Path("C:/Users/cow/Documents/thesis-quevotan/papers/jcc-2026")
OUTDIR = _paths.render_dir()   # was PAPER/"figs/v2026-08-11", a path the
                               # 2026-08-13 reorganization retired. Renders go to
                               # figures/renders/<date>/; survivors are copied into
                               # draft/figures/ by hand. reference-renders/ is frozen.
FIGNAME = "fig4-seed"
VERSION = "v2"
# v1 (kept on disk, never deleted): identical data and identical alignment; the
# frame ended at x = 1.00 exactly, so the first-dimension markers at r = 0.997
# were clipped by the right spine and the last x tick label was cut.  v2 pads
# the frame to 1.05, keeps the last tick at 1.0, and gives the legend its own
# band under the axis label.  No plotted value changed between v1 and v2.
VERSION_HISTORY = {
    "v1": "clipped first-dimension markers at the right spine; superseded",
    "v2": "frame padded to 1.05, legend given its own band; values identical to v1",
}

CPP_MATCHED = "reproduce/out/chile/cpp_run_chile_per_period/cpp_coordinates_all_periods.csv"
CPP_MISMATCHED = "reproduce/out/chile/cpp_run_chile/cpp_coordinates_all_periods.csv"
FORTRAN = "reproduce/out/dwnom2004_chile_per_period/us_legout.dat"
FORTRAN_USNUM = "reproduce/out/dwnom2004_chile_per_period/us.num"
LEGMAP = "output/legislatura_map.csv"
REFERENCE = "reproduce/out/chile/julio_reference_periodo9_by_leg.csv"

# FIGURE-DESIGN non-negotiable 1.  This run is the legs 347-369 panel and is a
# DATA-CONTRACT section 4 violator when set beside a 346-368 C++ run.
FORBIDDEN_FORTRAN = "dwnom2004_chile/"

# ---------------------------------------------------------------------------
# Named constants.  Everything the figure could ever need to be re-pointed at
# lives here so a swap is a one-line edit.
# ---------------------------------------------------------------------------
DENOMINATOR = None  # fig4-seed plots a correlation; nothing is divided. See docstring.
DENOMINATOR_NOTE = ("no bootstrap-SE denominator enters this figure; a pablo-10 "
                    "swap of the SE bank leaves every plotted value unchanged")

PANEL_LEGS = (346, 368)          # the panel both engines are fit on
PLOT_LEGS = (366, 367, 368)      # the legislaturas drawn
PANEL_ROLLCALLS = 12952
PANEL_VALID_VOTES = 692839
LOPSIDED_THRESHOLD = 0.025
LOPSIDED_DROPPED = 6094          # of PANEL_ROLLCALLS, on this panel

# Gate.  FIGURE-DESIGN section 3 transcription of _contam_amp_offset.py blocks
# C and D, under the reference-gated roster (n = 155/155/160).
GATE = {
    ("matched", 366): (0.997, 0.845), ("mismatched", 366): (0.987, 0.397),
    ("matched", 367): (0.995, 0.768), ("mismatched", 367): (0.987, 0.426),
    ("matched", 368): (0.987, 0.617), ("mismatched", 368): (0.985, 0.391),
}
GATE_TOL = 0.0015

# ---------------------------------------------------------------------------
# Visual system.  FIGURE-DESIGN section 7.3, validator output reproduced today:
#   node validate_palette.js "#2a78d6,#eb6834" --mode light --surface "#ffffff" --pairs all
#     [PASS] lightness band / chroma floor / CVD sep dE 24.7 protan /
#     [PASS] normal-vision dE 33.6 / contrast vs surface all >= 3:1
# ---------------------------------------------------------------------------
C_MATCHED = "#2a78d6"     # categorical slot 1
C_MISMATCHED = "#eb6834"  # categorical slot 2
INK = "#0b0b0b"           # primary ink
MUTED = "#898781"         # muted ink
GRID = "#e1e0d9"          # gridline, solid hairline, never dashed
SURFACE = "#ffffff"

COL_W_IN = 3.5            # \columnwidth = 252pt.  Author here, never scale.
FS_BASE, FS_AXIS, FS_TICK, FS_LEGEND = 8, 8, 7, 7

MS_D2, MS_D1 = 5.2, 4.2   # marker diameters in points, matched (front) marker
# The mismatched square is drawn behind the matched circle and is given a
# constant +1.1pt so that it still peeks out when the two coincide, which is
# what happens on the first dimension (0.985 against 0.987 at leg 368 is 0.4pt
# of separation at 3.5in).  Size carries no data here; it is an overplotting
# fix and it is constant across every row, arm and variant.
MS_BACK_BONUS = 1.1
LW_CONNECT_D2, LW_CONNECT_D1 = 1.1, 0.8
RING = 0.9                # surface ring on markers, in points


def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "savefig.transparent": False,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": FS_BASE,
        "axes.labelsize": FS_AXIS, "axes.titlesize": FS_AXIS,
        "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
        "legend.fontsize": FS_LEGEND,
        "axes.linewidth": 0.6, "axes.edgecolor": MUTED,
        "xtick.major.width": 0.6, "ytick.major.width": 0.0,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.major.size": 2.5, "ytick.major.size": 0.0,
        "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "pdf.fonttype": 42, "ps.fonttype": 42,          # IEEE PDF eXpress rejects Type 3
        "svg.fonttype": "none",
        "figure.dpi": 400,
    })


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_fortran(rel: str) -> pd.DataFrame:
    """Fixed-width us_legout.dat.  Columns per the 2004 Fortran write format."""
    if FORBIDDEN_FORTRAN in rel.replace("\\", "/"):
        raise SystemExit(
            f"ABORT: refused to read {rel}.  `dwnom2004_chile` is the legs 347-369 "
            "panel; setting it beside a 346-368 C++ run is the one-legislatura "
            "offset of FIGURE-DESIGN 5.1/5.2.  Use dwnom2004_chile_per_period."
        )
    rows = []
    for line in open(REPO / rel):
        if len(line.rstrip("\r\n")) < 54:
            continue
        try:
            rows.append((int(line[0:4]), int(line[4:10]),
                         float(line[40:47]), float(line[47:54])))
        except ValueError:
            continue
    return (pd.DataFrame(rows, columns=["period", "legislator_id", "d1", "d2"])
            .drop_duplicates(["period", "legislator_id"], keep="last"))


def load_cpp(rel: str) -> pd.DataFrame:
    d = pd.read_csv(REPO / rel).rename(columns={"coord1D": "d1", "coord2D": "d2"})
    return d[["period", "legislator_id", "d1", "d2"]].dropna()


# ---------------------------------------------------------------------------
# Alignment assertions.  FIGURE-DESIGN non-negotiable 1: fail loudly.
# ---------------------------------------------------------------------------
def assert_panel_alignment(legmap: pd.DataFrame) -> dict:
    """The Fortran run's us.num must BE the 346-368 panel, row for row."""
    usnum = []
    for line in open(REPO / FORTRAN_USNUM):
        t = line.split()
        if len(t) == 4:
            usnum.append([int(x) for x in t])
    usnum = pd.DataFrame(usnum, columns=["period", "rollcalls", "nleg", "nleg_matrix"])

    exp = legmap[legmap.legislatura.between(*PANEL_LEGS)].reset_index(drop=True)
    if len(usnum) != len(exp):
        raise SystemExit(
            f"ABORT: {FORTRAN_USNUM} has {len(usnum)} periods, the {PANEL_LEGS[0]}-"
            f"{PANEL_LEGS[1]} panel has {len(exp)}.  Wrong Fortran run."
        )
    bad_rc = np.flatnonzero(usnum.rollcalls.values != exp.num_votes.values)
    bad_nl = np.flatnonzero(usnum.nleg.values != exp.num_legislators.values)
    if bad_rc.size or bad_nl.size:
        i = int(bad_rc[0]) if bad_rc.size else int(bad_nl[0])
        raise SystemExit(
            "ABORT: Fortran panel does not match legs "
            f"{PANEL_LEGS[0]}-{PANEL_LEGS[1]}.  First mismatch at period "
            f"{i+1}: us.num says rollcalls={usnum.rollcalls[i]} nleg={usnum.nleg[i]}, "
            f"legislatura {exp.legislatura[i]} should have "
            f"rollcalls={exp.num_votes[i]} nleg={exp.num_legislators[i]}.  This is "
            "the one-legislatura offset of FIGURE-DESIGN 5.1/5.2.  Refusing to plot."
        )
    return {
        "us_num_line1": " ".join(str(x) for x in usnum.iloc[0].tolist()),
        "periods": int(len(usnum)),
        "first_legislatura": int(exp.legislatura.iloc[0]),
        "last_legislatura": int(exp.legislatura.iloc[-1]),
        "rollcalls_match_legislatura_map": True,
        "nlegislators_match_legislatura_map": True,
    }


def assert_roster(leg: int, roster: set, joined: set, legmap: pd.DataFrame) -> None:
    expected = int(legmap.loc[legmap.legislatura == leg, "num_legislators"].iloc[0])
    if len(roster) != expected:
        raise SystemExit(
            f"ABORT: leg {leg}: Fortran emitted {len(roster)} legislators, "
            f"output/legislatura_map.csv says {expected} active.  Roster mismatch."
        )
    if len(joined) != expected:
        missing = sorted(roster - joined)
        raise SystemExit(
            f"ABORT: leg {leg}: only {len(joined)} of {expected} active legislators "
            f"survive the engine join.  Missing {missing[:12]}.  Refusing to plot a "
            "cross-engine correlation on a partial roster."
        )


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------
def procrustes_r(A: np.ndarray, B: np.ndarray) -> tuple[float, float]:
    """UNCENTRED orthogonal Procrustes of A onto B; per-dimension Pearson r.

    Matches proc() in _contam_amp_offset.py, NOT the centred operator of
    procrustes_per_congress.py:34-44 used by tab:fidelity.
    """
    U, _, Vt = np.linalg.svd(A.T @ B)
    Ao = A @ (U @ Vt)
    return (float(np.corrcoef(Ao[:, 0], B[:, 0])[0, 1]),
            float(np.corrcoef(Ao[:, 1], B[:, 1])[0, 1]))


def measure(cpp: pd.DataFrame, fort: pd.DataFrame, leg2p: dict, leg: int,
            roster: set) -> tuple[float, float, int]:
    per = leg2p[leg]
    a = (cpp[(cpp.period == per) & (cpp.legislator_id.isin(roster))]
         .set_index("legislator_id")[["d1", "d2"]].sort_index())
    b = (fort[(fort.period == per) & (fort.legislator_id.isin(roster))]
         .set_index("legislator_id")[["d1", "d2"]].sort_index())
    j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
    r1, r2 = procrustes_r(j[["d1_a", "d2_a"]].to_numpy(), j[["d1_b", "d2_b"]].to_numpy())
    return r1, r2, len(j)


def collect() -> dict:
    legmap = pd.read_csv(REPO / LEGMAP)
    leg2p = {int(d["legislatura"]): int(d["period_index"])
             for d in csv.DictReader(open(REPO / LEGMAP))}

    panel = assert_panel_alignment(legmap)

    cpp_m = load_cpp(CPP_MATCHED)
    cpp_x = load_cpp(CPP_MISMATCHED)
    fort = load_fortran(FORTRAN)

    ref = pd.read_csv(REPO / REFERENCE)
    ref["legislatura"] = pd.to_numeric(ref["legislatura"], errors="coerce")

    out, alt = {}, {}
    for leg in PLOT_LEGS:
        per = leg2p[leg]
        roster = set(fort[fort.period == per].legislator_id)
        joined = roster & set(cpp_m[cpp_m.period == per].legislator_id) \
                        & set(cpp_x[cpp_x.period == per].legislator_id)
        assert_roster(leg, roster, joined, legmap)

        ref_roster = roster & set(
            ref[ref.legislatura == leg].dropna(subset=["x", "y"]).legislator_id)

        for arm, cpp in (("matched", cpp_m), ("mismatched", cpp_x)):
            r1, r2, n = measure(cpp, fort, leg2p, leg, roster)
            out[(arm, leg)] = {"r1": r1, "r2": r2, "n": n}
            ar1, ar2, an = measure(cpp, fort, leg2p, leg, ref_roster)
            alt[(arm, leg)] = {"r1": ar1, "r2": ar2, "n": an}

    return {"panel": panel, "primary": out, "reference_gated": alt, "legmap": legmap}


def gate_report(alt: dict) -> list:
    """Print our own numbers before drawing anything, gated on FIGURE-DESIGN 3."""
    print("fig4-seed gate.  Our own uncentred-Procrustes values under the "
          "reference-gated roster, against the FIGURE-DESIGN section 3 transcription "
          "of _contam_amp_offset.py blocks C and D:")
    fails = []
    for (arm, leg), v in sorted(alt.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        g1, g2 = GATE[(arm, leg)]
        d1, d2 = abs(v["r1"] - g1), abs(v["r2"] - g2)
        ok = d1 <= GATE_TOL and d2 <= GATE_TOL
        print(f"  leg {leg} {arm:<11s} n={v['n']:3d}  r1={v['r1']:.3f} (gate {g1:.3f})"
              f"  r2={v['r2']:.3f} (gate {g2:.3f})   {'OK' if ok else 'FAIL'}")
        if not ok:
            fails.append((arm, leg, v, (g1, g2)))
    if fails:
        raise SystemExit(f"ABORT: {len(fails)} gate failures.  Refusing to render.")
    print("  all 12 values inside +/-%.4f of the transcription.\n" % GATE_TOL)
    return fails


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
# The axis runs 0 to 1 because a correlation has a meaningful zero and the
# halving of the second dimension must be read at true proportion.  The upper
# limit is padded past 1.0 only so that a marker sitting at r = 0.997 is not
# clipped by the frame; the last tick is still 1.0.
XLIM = (0.0, 1.05)
XTICKS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


def _axis_dress(ax, xlabel: bool) -> None:
    ax.set_xlim(*XLIM)
    ax.set_xticks(XTICKS)
    ax.set_xticklabels([f"{t:.1f}" for t in XTICKS] if xlabel else [])
    ax.xaxis.grid(True, zorder=0)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(axis="y", length=0, pad=2)
    ax.tick_params(axis="x", pad=2, colors=MUTED)
    for lab in ax.get_xticklabels():
        lab.set_color(MUTED)


def _dumbbell(ax, y, x_matched, x_mismatched, *, ms, lw, filled: bool) -> None:
    face_m = C_MATCHED if filled else SURFACE
    face_x = C_MISMATCHED if filled else SURFACE
    ax.plot([x_mismatched, x_matched], [y, y], "-", color=MUTED, lw=lw,
            solid_capstyle="round", zorder=2)
    ax.plot([x_mismatched], [y], "s", color=face_x, mec=SURFACE if filled else C_MISMATCHED,
            mew=RING if filled else 1.0, ms=ms + MS_BACK_BONUS, zorder=3)
    ax.plot([x_matched], [y], "o", color=face_m, mec=SURFACE if filled else C_MATCHED,
            mew=RING if filled else 1.0, ms=ms, zorder=4)


def _legend_handles(with_dim: bool) -> list:
    h = [Line2D([], [], marker="o", color="none", markerfacecolor=C_MATCHED,
                markeredgecolor=SURFACE, markeredgewidth=RING, markersize=MS_D2,
                label="matched seed frame"),
         Line2D([], [], marker="s", color="none", markerfacecolor=C_MISMATCHED,
                markeredgecolor=SURFACE, markeredgewidth=RING,
                markersize=MS_D2 + MS_BACK_BONUS, label="mismatched seed frame")]
    if with_dim:
        h += [Line2D([], [], marker="o", color="none", markerfacecolor=SURFACE,
                     markeredgecolor=C_MATCHED, markeredgewidth=1.0, markersize=MS_D1,
                     label="matched, first dim."),
              Line2D([], [], marker="s", color="none", markerfacecolor=SURFACE,
                     markeredgecolor=C_MISMATCHED, markeredgewidth=1.0,
                     markersize=MS_D1 + MS_BACK_BONUS, label="mismatched, first dim.")]
    return h


def draw_a(vals: dict):
    """Compact: 3 rows, dim-1 as a small open pair beneath each dim-2 dumbbell."""
    fig, ax = plt.subplots(figsize=(COL_W_IN, 1.66))
    fig.subplots_adjust(left=0.135, right=0.965, top=0.985, bottom=0.395)
    ys = {366: 2.0, 367: 1.0, 368: 0.0}
    for leg, y in ys.items():
        _dumbbell(ax, y + 0.14, vals[("matched", leg)]["r2"],
                  vals[("mismatched", leg)]["r2"], ms=MS_D2, lw=LW_CONNECT_D2, filled=True)
        _dumbbell(ax, y - 0.20, vals[("matched", leg)]["r1"],
                  vals[("mismatched", leg)]["r1"], ms=MS_D1, lw=LW_CONNECT_D1, filled=False)
    ax.set_yticks(list(ys.values()))
    ax.set_yticklabels([str(l) for l in ys], color=INK, fontsize=FS_TICK)
    ax.set_ylim(-0.72, 2.62)
    ax.set_ylabel("legislatura", fontsize=FS_AXIS, color=INK, labelpad=2)
    ax.set_xlabel("cross-engine correlation, uncentred Procrustes",
                  fontsize=FS_AXIS, color=INK, labelpad=2)
    _axis_dress(ax, True)
    leg = fig.legend(handles=_legend_handles(True), loc="lower center",
                     bbox_to_anchor=(0.5, 0.005), ncol=2, frameon=False,
                     handletextpad=0.35, columnspacing=1.1, labelspacing=0.22,
                     borderpad=0.0)
    for t in leg.get_texts():
        t.set_color(INK)
    return fig


def draw_b(vals: dict):
    """Split: 3 legislatura groups, dim-2 and dim-1 on their own sub-rows."""
    fig, ax = plt.subplots(figsize=(COL_W_IN, 2.05))
    fig.subplots_adjust(left=0.155, right=0.965, top=0.985, bottom=0.245)
    rows, labels = [], []
    y = 0.0
    for leg in reversed(PLOT_LEGS):
        _dumbbell(ax, y, vals[("matched", leg)]["r1"], vals[("mismatched", leg)]["r1"],
                  ms=MS_D1, lw=LW_CONNECT_D1, filled=False)
        rows.append(y); labels.append("dim 1")
        y += 0.62
        _dumbbell(ax, y, vals[("matched", leg)]["r2"], vals[("mismatched", leg)]["r2"],
                  ms=MS_D2, lw=LW_CONNECT_D2, filled=True)
        rows.append(y); labels.append("dim 2")
        # The group label sits in the dead left third of the axis (no mark falls
        # below r = 0.39), which is cheaper than a second label column.
        ax.text(0.012, y - 0.31, f"leg. {leg}", ha="left", va="center",
                fontsize=FS_TICK, color=INK)
        y += 1.05
    ax.set_yticks(rows)
    ax.set_yticklabels(labels, color=MUTED, fontsize=FS_TICK)
    ax.set_ylim(-0.62, y - 0.45)
    ax.set_xlabel("cross-engine correlation, uncentred Procrustes",
                  fontsize=FS_AXIS, color=INK, labelpad=2)
    _axis_dress(ax, True)
    leg = fig.legend(handles=_legend_handles(False), loc="lower center",
                     bbox_to_anchor=(0.5, 0.002), ncol=2, frameon=False,
                     handletextpad=0.35, columnspacing=1.4, borderpad=0.0)
    for t in leg.get_texts():
        t.set_color(INK)
    return fig


def draw_c(vals: dict):
    """Faceted: two stacked panels sharing x, (a) dim 2 and (b) dim 1."""
    fig, axes = plt.subplots(2, 1, figsize=(COL_W_IN, 2.42), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1], "hspace": 0.34})
    fig.subplots_adjust(left=0.155, right=0.965, top=0.945, bottom=0.235)
    ys = {366: 2.0, 367: 1.0, 368: 0.0}
    for ax, dim, tag in ((axes[0], "r2", "(a)  second dimension"),
                         (axes[1], "r1", "(b)  first dimension")):
        for leg, y in ys.items():
            _dumbbell(ax, y, vals[("matched", leg)][dim], vals[("mismatched", leg)][dim],
                      ms=MS_D2, lw=LW_CONNECT_D2, filled=True)
        ax.set_yticks(list(ys.values()))
        ax.set_yticklabels([str(l) for l in ys], color=INK, fontsize=FS_TICK)
        ax.set_ylim(-0.75, 2.95)
        ax.set_ylabel("legislatura", fontsize=FS_AXIS, color=INK, labelpad=2)
        _axis_dress(ax, ax is axes[1])
        ax.text(0.0, 1.0, tag, transform=ax.transAxes, ha="left", va="top",
                fontsize=FS_TICK, color=INK)
    axes[0].spines["bottom"].set_visible(False)
    axes[0].tick_params(axis="x", length=0)
    axes[1].set_xlabel("cross-engine correlation, uncentred Procrustes",
                       fontsize=FS_AXIS, color=INK, labelpad=2)
    leg = fig.legend(handles=_legend_handles(False), loc="lower center",
                     bbox_to_anchor=(0.5, 0.002), ncol=2, frameon=False,
                     handletextpad=0.35, columnspacing=1.4, borderpad=0.0)
    for t in leg.get_texts():
        t.set_color(INK)
    return fig


VARIANTS = {
    "a": (draw_a, "compact: one row per legislatura, first dimension as a small "
                  "open marker pair beneath each second-dimension dumbbell"),
    "b": (draw_b, "split: one group per legislatura, second and first dimension on "
                  "their own labelled sub-rows"),
    "c": (draw_c, "faceted: two stacked panels sharing one x-axis, (a) second "
                  "dimension and (b) first dimension"),
}


def save(fig, stem: str) -> list:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    png = OUTDIR / f"{stem}.png"
    pdf = OUTDIR / f"{stem}.pdf"
    # bbox_inches=None: never 'tight'.  A tight box changes the emitted canvas so
    # \includegraphics[width=\columnwidth] no longer renders at scale 1.0 and every
    # in-figure point size drifts.  FIGURE-DESIGN 7.4.
    fig.savefig(png, dpi=400, bbox_inches=None, pad_inches=0.01, facecolor=SURFACE)
    fig.savefig(pdf, bbox_inches=None, pad_inches=0.01, facecolor=SURFACE)
    plt.close(fig)
    return [png, pdf]


def contact_sheet(paths: dict, stem: str, invert: bool) -> Path:
    """Three variants side by side at their true include width, for review only."""
    import matplotlib.image as mpimg
    imgs = [mpimg.imread(paths[k]) for k in ("a", "b", "c")]
    hmax = max(im.shape[0] / 400 for im in imgs)
    fig, axes = plt.subplots(1, 3, figsize=(3 * COL_W_IN + 0.6, hmax + 0.42))
    for ax, key, im in zip(axes, ("a", "b", "c"), imgs):
        ax.imshow(1.0 - im[..., :3] if invert else im[..., :3])
        ax.set_title(f"variant {key}", fontsize=9,
                     color="#ffffff" if invert else INK, pad=4)
        ax.axis("off")
    fig.patch.set_facecolor("#111111" if invert else SURFACE)
    fig.subplots_adjust(left=0.005, right=0.995, top=0.93, bottom=0.01, wspace=0.04)
    out = OUTDIR / f"{stem}.png"
    fig.savefig(out, dpi=200, bbox_inches=None, pad_inches=0.02,
                facecolor="#111111" if invert else SURFACE)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
def main() -> None:
    style()
    data = collect()
    vals, alt, panel = data["primary"], data["reference_gated"], data["panel"]
    gate_report(alt)

    print("fig4-seed plotted values.  Roster = the Fortran per-period run's own "
          "active roster, equal to output/legislatura_map.csv:num_legislators:")
    for leg in PLOT_LEGS:
        m, x = vals[("matched", leg)], vals[("mismatched", leg)]
        print(f"  leg {leg}  n={m['n']:3d}   dim2 matched {m['r2']:.3f} -> mismatched "
              f"{x['r2']:.3f}   |   dim1 matched {m['r1']:.3f} -> mismatched {x['r1']:.3f}")
    print()

    written, per_variant = [], {}
    for key, (fn, desc) in VARIANTS.items():
        stem = f"{FIGNAME}-{key}_{VERSION}"
        outs = save(fn(vals), stem)
        per_variant[key] = outs[0]
        written += outs
        print(f"  wrote {outs[0].name}, {outs[1].name}   [{desc}]")

    written.append(contact_sheet(per_variant, f"{FIGNAME}-variants_{VERSION}", False))
    written.append(contact_sheet(per_variant, f"{FIGNAME}-variants-darkcheck_{VERSION}", True))
    print(f"  wrote {written[-2].name}, {written[-1].name}   [review sheets, not for inclusion]")

    # ---- manifest ---------------------------------------------------------
    legmap = data["legmap"]
    manifest = {
        "figure": FIGNAME,
        "version": VERSION,
        "version_history": VERSION_HISTORY,
        "title": "The seed is the frame",
        "carries": "P3, FIGURE-DESIGN-2026-08-11.md section 3, rank 6, supporting",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generating_command": f"python {Path(__file__).as_posix()}",
        "generator": Path(__file__).as_posix(),
        "generator_md5": md5(Path(__file__)),
        "environment": {
            "python": sys.version.split()[0],
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "panel": {
            "legs": f"{PANEL_LEGS[0]}-{PANEL_LEGS[1]}",
            "periods": panel["periods"],
            "rollcalls": PANEL_ROLLCALLS,
            "valid_votes": PANEL_VALID_VOTES,
            "source": "reproduce/out/chile/cpp_input/",
            "authority": "DATA-CONTRACT-2026-08-05.md section 4",
            "legislaturas_plotted": list(PLOT_LEGS),
            "us_num_line1": panel["us_num_line1"],
            "us_num_matches_legislatura_map": True,
            "forbidden_run_not_read": "reproduce/out/dwnom2004_chile (legs 347-369)",
        },
        "alignment": {
            "panel_offset": "none; Fortran period p and C++ period p both map to "
                            "legislatura 345+p.  Asserted row-by-row over all 23 "
                            "periods on rollcall count and legislator count.",
            "procrustes_operator": "uncentred orthogonal Procrustes, R = U V^T from "
                                   "svd(A^T B), C++ rotated onto Fortran, one rotation "
                                   "per (legislatura, arm)",
            "procrustes_note": "NOT the centred operator of procrustes_per_congress.py"
                               ":34-44 used by tab:fidelity.  FIGURE-DESIGN 5.4 item 2.",
            "padding": "active rows only.  The C++ CSVs emit 338 padded rows per "
                       "period; the inner join onto the Fortran roster (which emits "
                       "the active set only) enforces this structurally.",
            "roster_rule": "Fortran per-period active roster, asserted equal to "
                           "output/legislatura_map.csv:num_legislators",
        },
        "denominator": {
            "value": DENOMINATOR,
            "note": DENOMINATOR_NOTE,
            "pablo_10_sensitivity": "none",
        },
        "lopsidedness_screen": {
            "threshold": LOPSIDED_THRESHOLD,
            "dropped_on_panel": LOPSIDED_DROPPED,
            "of_total_rollcalls": PANEL_ROLLCALLS,
            "sites": ["main_cli.cpp:471", "dwnominate.cpp:187", "dwnom2004.f:324-326"],
            "side_of_screen": "post-screen fits; this figure counts legislator "
                              "placements only, never roll calls or votes, so no "
                              "plotted count is affected by the screen",
        },
        "rows_and_columns": {
            "rows_plotted": len(PLOT_LEGS),
            "series_per_row": 4,
            "series": ["dim2 matched seed", "dim2 mismatched seed",
                       "dim1 matched seed", "dim1 mismatched seed"],
            "legislator_placements_per_row": {
                str(l): int(vals[("matched", l)]["n"]) for l in PLOT_LEGS},
            "legislator_placements_total": int(
                sum(vals[("matched", l)]["n"] for l in PLOT_LEGS)),
            "legislatura_map_num_legislators": {
                str(l): int(legmap.loc[legmap.legislatura == l, "num_legislators"].iloc[0])
                for l in PLOT_LEGS},
            "rollcalls_per_legislatura": {
                str(l): int(legmap.loc[legmap.legislatura == l, "num_votes"].iloc[0])
                for l in PLOT_LEGS},
        },
        "arms": {
            "matched": {
                "cpp": CPP_MATCHED,
                "cpp_seed": "per-period W-NOMINATE seed (run.log 'SeedPP:' present)",
                "fortran": FORTRAN,
                "fortran_seed": "per-period seeds",
            },
            "mismatched": {
                "cpp": CPP_MISMATCHED,
                "cpp_seed": "single constant W-NOMINATE seed (run.log has no 'SeedPP:')",
                "fortran": FORTRAN,
                "fortran_seed": "per-period seeds",
            },
        },
        "sources": {
            rel: {"path": (REPO / rel).as_posix(), "md5": md5(REPO / rel)}
            for rel in (CPP_MATCHED, CPP_MISMATCHED, FORTRAN, FORTRAN_USNUM,
                        LEGMAP, REFERENCE)
        },
        "values_plotted": {
            f"{arm}_{leg}": {"r1": round(v["r1"], 6), "r2": round(v["r2"], 6),
                             "n": v["n"]}
            for (arm, leg), v in vals.items()
        },
        "values_reference_gated_roster": {
            f"{arm}_{leg}": {"r1": round(v["r1"], 6), "r2": round(v["r2"], 6),
                             "n": v["n"]}
            for (arm, leg), v in alt.items()
        },
        "gate": {
            "against": "FIGURE-DESIGN-2026-08-11.md section 3, blocks C and D, "
                       "transcribed from reproduce/scripts/_contam_amp_offset.py",
            "roster_used_for_gate": "reference-gated (n = 155/155/160)",
            "tolerance": GATE_TOL,
            "result": "all 12 values pass",
        },
        "palette": {
            "matched": C_MATCHED, "mismatched": C_MISMATCHED,
            "ink": INK, "muted": MUTED, "grid": GRID, "surface": SURFACE,
            "validator": "node validate_palette.js \"#2a78d6,#eb6834\" --mode light "
                         "--surface \"#ffffff\" --pairs all -> ALL CHECKS PASS "
                         "(CVD dE 24.7 protan, normal-vision dE 33.6, contrast >= 3:1)",
            "alpha_used": False,
            "identity_without_colour": "marker shape (circle = matched, square = "
                                       "mismatched) and, in variants a and b, fill "
                                       "(solid = second dimension, open = first)",
        },
        "geometry": {
            "column_width_pt": 252,
            "authored_width_in": COL_W_IN,
            "include_at": "\\includegraphics[width=\\columnwidth]{...}  scale 1.0",
            "bbox_inches": None,
            "pad_inches": 0.01,
            "pdf_fonttype": 42,
            "emitted_mediabox_pt": {"a": [252, 119.5], "b": [252, 147.6],
                                    "c": [252, 174.24]},
            "emitted_mediabox_note": "width is 252pt exactly, i.e. \\columnwidth, so "
                                     "the include renders at scale 1.0 and no in-figure "
                                     "point size drifts.  Heights are the figure body "
                                     "only; add roughly 30-35 col-pt of caption and the "
                                     "float skips.  FIGURE-DESIGN section 4 budgeted "
                                     "~130 col-pt for fig4-seed; variant a lands near "
                                     "that, b and c cost more.",
            "pdf_has_transparency_group": False,
            "font_sizes": {"base": FS_BASE, "axis": FS_AXIS, "tick": FS_TICK,
                           "legend": FS_LEGEND},
            "x_axis_range": list(XLIM),
            "x_axis_not_cropped": "correlation has a meaningful zero; the axis runs "
                                  "0 to 1 so the halving of the second dimension is "
                                  "read at true proportion",
        },
        "variants": {k: {"description": d,
                         "png": f"{FIGNAME}-{k}_{VERSION}.png",
                         "pdf": f"{FIGNAME}-{k}_{VERSION}.pdf"}
                     for k, (_, d) in VARIANTS.items()},
        "review_only": [f"{FIGNAME}-variants_{VERSION}.png",
                        f"{FIGNAME}-variants-darkcheck_{VERSION}.png"],
        "gaps": [
            "No number in this figure depends on an unrun experiment.",
            "Font family is DejaVu Sans, matplotlib's default sans.  Not matched to "
            "the IEEEtran body face; change font.sans-serif in style() if Roberto "
            "wants figure text to match the paper's Times.",
            "The dimension-one dumbbells are ~0.01 long at legs 367 and 368, which "
            "is under one marker diameter at 3.5in; the two markers overlap by "
            "design and the read is 'no movement', not 'two values'.",
        ],
        "caption_draft":
            "Cross-engine agreement between our reimplementation and the 2004 "
            "Fortran, legislaturas 366 to 368 of the 346 to 368 panel, under a "
            "matched and a mismatched seed frame. Both arms hold the panel and the "
            "legislators fixed (155, 155 and 161 active placements); only the seed "
            "differs. Correlations are per legislatura after an uncentred orthogonal "
            "Procrustes rotation onto the Fortran, on active rows only. The first "
            "dimension, muted, is unaffected by either condition.",
    }
    for key in list(VARIANTS) + [None]:
        stem = FIGNAME if key is None else f"{FIGNAME}-{key}"
        m = dict(manifest)
        m["variant"] = key
        m["outputs"] = ([f"{stem}_{VERSION}.png", f"{stem}_{VERSION}.pdf"]
                        if key else [v["png"] for v in manifest["variants"].values()]
                        + [v["pdf"] for v in manifest["variants"].values()])
        p = OUTDIR / f"{stem}.manifest.json"
        p.write_text(json.dumps(m, indent=2), encoding="utf-8")
        print(f"  wrote {p.name}")


if __name__ == "__main__":
    main()
