#!/usr/bin/env python
"""fig2-admissibility  --  JCC 2026 paper 149.

Built 2026-08-11 per FIGURE-DESIGN-2026-08-11.md section 3 (fig2-admissibility),
section 5.4 (alignment rule) and section 7 (visual system).

WHAT THIS DRAWS
  Panel (a)  the tolerance-step ladder: nine NITER=4 cell representatives placed at
             their geometric-mean-probability deficit from the best fit, in units of
             the estimator's own convergence tolerance.  Unambiguous, built once.
  Panel (b)  the second-dimension ratio as a function of the admissibility threshold.
             THIS PANEL IS GATED ON AN UNSIGNED RULING.  Two candidate rules exist and
             they disagree.  Both are rendered, never merged:
               GMP    DESK-PLAN-2026-08-06.md section 2.1 ruling, threshold k in
                      convergence-tolerance steps, admitted interval k in [11, 102].
               CLASS  SEC-IV-admissibility-2026-08-06.tex, threshold in classification
                      percentage points, 2.5 points below the best run.

  Three files are emitted:
    fig2-admissibility-gmp      (a) + (b) under the GMP rule        [ship candidate]
    fig2-admissibility-class    (a) + (b) under the classification rule [ship candidate]
    fig2-admissibility-compare  (a) + both (b)s on one shared y-range   [decision aid]

NO COMPUTE.  Every plotted value is transcribed from an artifact on disk.  The only
arithmetic performed here is exp(logL/N) over log-likelihoods already recorded in
_adm_ll_table.json, which reproduces the ladder printed in _joint_niter4.out and is
asserted against it.  No fit is run, no coordinate CSV is opened, no Procrustes.

PANEL.  346-368, 23 periods, 692,839 valid votes, reproduce/out/chile/cpp_input/.
The three legislaturas whose placements enter the numerator are 366, 367, 368
(n = 482 keys for the GMP arm, n = 465 for the classification arm; they are NOT the
same roster and the figure does not pretend otherwise).

ALIGNMENT.  This figure reads NO Fortran artifact.  dwnom2004_chile, the 347-369 panel
that FIGURE-DESIGN 5.1 and 5.2 caught offsetting two current generators by one
legislatura, is never opened; an assertion below fails loudly if any input path names
it.  The numerator behind the plotted ratios was produced by _joint_niter4.py under
uncentred orthogonal Procrustes onto the QueVotan reference, one global rotation over
the stacked (legislatura, legislator) set; that operator is recorded in the manifest
per FIGURE-DESIGN 5.4 item 2.

LOPSIDEDNESS SCREEN.  This figure counts frames, not roll calls and not votes.  The
panel underneath it sits on the far side of the 0.025 minority screen shared by both
engines (main_cli.cpp:471, dwnominate.cpp:187, dwnom2004.f:324-326): 6,094 of 12,952
roll calls are dropped, 6,858 survive, 692,839 valid votes.

Usage:  python fig2-admissibility.py [--figdir DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths

# ---------------------------------------------------------------------------
# 0.  PATHS
# ---------------------------------------------------------------------------
REPO = Path("C:/Users/cow/Documents/GitHub/quevotan-db")
PAPER = Path("C:/Users/cow/Documents/thesis-quevotan/papers/jcc-2026")

SRC_LL_TABLE = REPO / "reproduce/scripts/_adm_ll_table.json"
SRC_JOINT_OUT = Path("C:/Users/cow/.claude/jobs/b43b64d6/tmp/_joint_niter4.out")
SRC_LEGMAP = REPO / "output/legislatura_map.csv"
SRC_R4 = PAPER / "findings/R4-FRAME-ENSEMBLE-2026-08-05.md"      # moved by the 2026-08-13 reorg
SRC_SECIV = PAPER / "reference/SEC-IV-admissibility-2026-08-06.tex"  # moved by the 2026-08-13 reorg

DEFAULT_FIGDIR = _paths.render_dir()   # was PAPER/"figs/v2026-08-11", a path the
                                       # 2026-08-13 reorganization retired. Renders go to
                                       # figures/renders/<date>/; survivors are copied into
                                       # draft/figures/ by hand. reference-renders/ is frozen.
FIGNAME = "fig2-admissibility"
VERSION = "v1"

# ---------------------------------------------------------------------------
# 1.  NAMED CONSTANTS.  Never inline a denominator (FIGURE-DESIGN section 6).
#     pablo-10 may replace the headline denominator with a bootstrap on
#     canary_fseed_i4; that must remain a one-line edit.
# ---------------------------------------------------------------------------
DENOM_MED_SE_DIM2 = 0.0706          # route2_bigB B=150, base fit cpp_run_chile
DENOM_HEADLINE = "bigB B=150 CONST"  # column key in _joint_niter4.out
DENOM_HEADLINE_LABEL = "route2_bigB, B=150"
DENOM_HEADLINE_PATH = "reproduce/out/chile/julio_test/route2_bigB/w{0,1,2}/*.npy (150 replicates)"

# In-ensemble envelope, FIGURE-DESIGN inversion I2.  All four, no more, no fewer.
DENOM_ENVELOPE = ("route2 B=50 CONST", "canon B=50", "canon B=100", "bigB B=150 CONST")
# Excluded from the envelope on stated grounds, DESK-PLAN 1.3: its base fit is not in
# the ensemble, 43.4% of its placements sit at radius > 0.99, and unit-dispersion
# rescaling inverts it from smallest to largest ratio.
DENOM_EXCLUDED = ("p24 B=50",)

# The classification-screen arm exists on ONE denominator only.  There is no
# four-denominator envelope for it anywhere on disk.  This is a gap, not a choice.
DENOM_CLASS = "route2 B=50"
DENOM_CLASS_PATH = "reproduce/out/chile/julio_test/route2/dwnom_se.csv"

PANEL_VOTES = 692839
PANEL_PERIODS = "23"
PANEL_LEGS = (346, 368)
NUMERATOR_LEGS = (366, 367, 368)
TOL = 1e-4                      # optimize_legislators.hpp:23, convergenceTol
PUBLISHED_RATIO = 3.1           # main-rewrite-2026-08-05.tex:371, the number in print

# Admitted threshold interval under the GMP rule (DESK-PLAN 1.2 / 2.3).
GMP_ADMITTED_K = (11.0, 102.0)
# Admitted threshold interval under the classification rule (SEC-IV; R4 section 3):
# retained fits sit 0 to 2.04 points below their best peer, excluded ones 2.60 to 5.20.
CLASS_ADMITTED_PTS = (2.04, 2.60)
CLASS_RULE_PTS = 2.5

# ---------------------------------------------------------------------------
# 2.  PALETTE.  FIGURE-DESIGN 7.3, validated 2026-08-11 with
#     node scripts/validate_palette.js "#2a78d6,#eb6834,#4a3aa7" --mode light
#          --surface "#ffffff" --pairs all      -> ALL CHECKS PASS
#     node scripts/validate_palette.js "#86b6ef,#1c5cab" --ordinal -> ALL CHECKS PASS
#     No alpha anywhere (DESK-PLAN 7.4: alpha forces a PDF transparency group).
# ---------------------------------------------------------------------------
C_SLOT1 = "#2a78d6"     # first named series
C_SLOT2 = "#eb6834"     # second series
C_BAND_WIDE = "#86b6ef"  # denominator envelope
C_BAND_NARROW = "#1c5cab"
C_INK = "#0b0b0b"
C_MUTED = "#898781"
C_GRID = "#e1e0d9"
C_SPAN_FILL = "#f0efec"
C_SPAN_EDGE = "#c3c2b7"
C_SURFACE = "#ffffff"

COL_W_IN = 3.5          # \columnwidth = 252pt.  Author here, never scale.


def rc():
    """FIGURE-DESIGN 7.4.  Base 8pt, labels 8pt, ticks 7pt, legend 7pt, Type 42."""
    plt.rcParams.update({
        "figure.facecolor": C_SURFACE,
        "savefig.facecolor": C_SURFACE,
        "axes.facecolor": C_SURFACE,
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.edgecolor": C_MUTED,
        "axes.linewidth": 0.6,
        "xtick.color": C_MUTED,
        "ytick.color": C_MUTED,
        "xtick.labelcolor": C_INK,
        "ytick.labelcolor": C_INK,
        "text.color": C_INK,
        "axes.labelcolor": C_INK,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "grid.color": C_GRID,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",          # never dashed (anti-patterns)
        "pdf.fonttype": 42,             # IEEE PDF eXpress rejects Type 3
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "figure.dpi": 400,
    })


# ---------------------------------------------------------------------------
# 3.  READ THE ARTIFACTS.  Assert loudly.
# ---------------------------------------------------------------------------
def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_panel_alignment():
    """FIGURE-DESIGN 5.4 item 1.  The signature of the 346-368 panel is that period
    index 1 maps to legislatura 346.  The banned artifact dwnom2004_chile is the
    347-369 panel (us.num line 1 = '1 103 120 120') and must never be read here."""
    rows = [ln.strip().split(",") for ln in
            SRC_LEGMAP.read_text(encoding="utf-8").splitlines() if ln.strip()]
    hdr, body = rows[0], rows[1:]
    ip, il = hdr.index("period_index"), hdr.index("legislatura")
    p2leg = {int(r[ip]): int(r[il]) for r in body}
    for period, leg in ((1, 346), (21, 366), (22, 367), (23, 368)):
        if p2leg.get(period) != leg:
            raise SystemExit(
                f"ALIGNMENT FAILURE: legislatura_map period {period} -> {p2leg.get(period)}, "
                f"expected {leg}.  This is the 347-369 panel, not the paper's 346-368 panel.")
    for src in (SRC_LL_TABLE, SRC_JOINT_OUT, SRC_LEGMAP, SRC_R4, SRC_SECIV):
        if "dwnom2004_chile" in str(src):
            raise SystemExit(f"ALIGNMENT FAILURE: banned Fortran artifact in input path {src}")
    return p2leg


def read_ladder():
    """Nine NITER=4 cell representatives, their GMP deficit in tolerance steps, and
    their classification deficit in percentage points.  Reproduces exactly the cell
    logic of _joint_niter4.py:28-46, which produced the printed ladder."""
    rows = json.load(open(SRC_LL_TABLE, encoding="utf-8"))
    gmp = lambda ll: math.exp(ll / PANEL_VOTES)
    cmp_rows = [r for r in rows if r["votes"] == PANEL_VOTES and r["dims"] == "2"
                and r["periods"] == PANEL_PERIODS and r["iters"] == "4"]
    if not cmp_rows:
        raise SystemExit("ALIGNMENT FAILURE: no NITER=4 fits on the 692,839-vote panel")
    byh = {}
    for r in sorted(cmp_rows, key=lambda x: (len(x["name"]), x["name"])):
        byh.setdefault(r["md5"], []).append(r)
    uniq = sorted([v[0] for v in byh.values()], key=lambda r: -r["ll"])
    best_gmp = gmp(uniq[0]["ll"])

    def cell(r):
        n = r["name"]
        for pat, lin in (("sweep_fseed", "fortran-seed"), ("canary_fseed", "fortran-seed"),
                         ("sweep_wnom", "wnominate-seed"), ("constseed", "constant-space-seed"),
                         ("full_seeds", "full-seeds"), ("chainseed", "chain-seed"),
                         ("ninc25", "chain-seed"), ("cdfmatch", "cdf-match"),
                         ("fixed", "fixed-binary")):
            if pat in n:
                return (lin, "tm" + r["tmodel"])
        return ("base-binary", "tm" + r["tmodel"])

    cells = {}
    for r in uniq:
        cells.setdefault(cell(r), []).append(r)
    reps = sorted([max(v, key=lambda m: m["ll"]) for v in cells.values()], key=lambda r: -r["ll"])
    best_pct = max(r["pct"] for r in reps)
    lad = [{"name": r["name"], "lineage": cell(r)[0], "tmodel": cell(r)[1],
            "logL": r["ll"], "pct": r["pct"],
            "tol_deficit": (best_gmp - gmp(r["ll"])) / TOL,
            "pct_deficit": best_pct - r["pct"]} for r in reps]
    return lad, len(cmp_rows), len(uniq), uniq[0]["name"], best_gmp, best_pct


def read_joint_out():
    """Parse the GMP-screen response table straight out of _joint_niter4.out so the
    figure is traceable to the artifact rather than to a transcription."""
    txt = SRC_JOINT_OUT.read_text(encoding="utf-8")
    m = re.search(r"^\s*k\s+F\s+sd1\s+sd2\s+(.*?)\s+flip1 flip2\s*$", txt, re.M)
    if not m:
        raise SystemExit("PARSE FAILURE: header row of _joint_niter4.out not found")
    # Column headers are truncated to 17 chars and right-padded to 19 in the writer.
    raw = m.group(1)
    cols = [c.strip() for c in re.split(r"\s{2,}", raw) if c.strip()]
    expected = ["route2 B=50 CONST", "canon B=100", "canon B=50", "p24 B=50", "bigB B=150 CONST"]
    if cols != expected:
        raise SystemExit(f"PARSE FAILURE: denominator columns {cols} != {expected}")

    nk = re.search(r"^n keys = (\d+)\s*$", txt, re.M)
    if not nk:
        raise SystemExit("PARSE FAILURE: 'n keys' line not found")
    n_keys = int(nk.group(1))

    table = {}
    for ln in txt.splitlines()[m.start():] if False else txt.splitlines():
        mm = re.match(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+((?:\s*[\d.]+x)+)\s+"
                      r"(\d+)%\s+(\d+)%\s*$", ln)
        if not mm:
            continue
        k = int(mm.group(1))
        ratios = [float(x) for x in re.findall(r"([\d.]+)x", mm.group(5))]
        if len(ratios) != 5:
            raise SystemExit(f"PARSE FAILURE: {len(ratios)} ratios on k={k}, expected 5")
        table[k] = {"F": int(mm.group(2)), "sd1": float(mm.group(3)), "sd2": float(mm.group(4)),
                    "ratios": dict(zip(cols, ratios)),
                    "flip1": int(mm.group(6)) / 100.0, "flip2": int(mm.group(7)) / 100.0}
    if sorted(table) != [1, 8, 10, 16, 32, 50, 100, 200, 300, 400, 10000]:
        raise SystemExit(f"PARSE FAILURE: k rows {sorted(table)} unexpected")
    return table, n_keys, cols


def read_class_table():
    """The classification-percentage screen.  Real output of _r4x_floor.py panel B2,
    transcribed into R4-FRAME-ENSEMBLE-2026-08-05.md section 3.  Re-read and re-parsed
    at generation time so a silent edit of the source fails the build."""
    txt = SRC_R4.read_text(encoding="utf-8")
    blk = re.search(r"\| gate \| m \| dim-1 \| dim-2 \|\n\|[-| ]+\|\n((?:\|.*\|\n)+)", txt)
    if not blk:
        raise SystemExit("PARSE FAILURE: classification gate table not found in R4-FRAME-ENSEMBLE")
    out = []
    for ln in blk.group(1).strip().splitlines():
        cells = [c.strip().strip("*") for c in ln.strip().strip("|").split("|")]
        gate, m_, d1, d2 = cells[0], cells[1], cells[2], cells[3]
        gate = gate.replace(" pt", "")
        if gate == "no gate":
            g = None
        else:
            g = float(gate)
        out.append({"gate_pts": g, "m": int(m_),
                    "dim1": float(d1.rstrip("x")), "dim2": float(d2.rstrip("x"))})
    if len(out) != 7:
        raise SystemExit(f"PARSE FAILURE: {len(out)} gate rows, expected 7")
    # The reported number under this rule is the balanced design, not the census.
    bal = re.search(r"balanced design, over all 28 choices of representative \| 7 \| "
                    r"([\d.]+)x \[([\d.]+), ([\d.]+)\] \| \*\*([\d.]+)x \[([\d.]+), ([\d.]+)\]\*\*",
                    txt)
    if not bal:
        raise SystemExit("PARSE FAILURE: balanced-design row not found in R4-FRAME-ENSEMBLE")
    balanced = {"dim2": float(bal.group(4)), "lo": float(bal.group(5)), "hi": float(bal.group(6))}
    nros = re.search(r"common roster n = (\d+) placements", txt)
    return out, balanced, (int(nros.group(1)) if nros else None)


# ---------------------------------------------------------------------------
# 4.  BUILD THE STEP FUNCTIONS
# ---------------------------------------------------------------------------
def gmp_segments(lad, table):
    """The response curve is a step function whose risers sit exactly at the ladder
    deficits.  Only the plateaus the table actually samples are drawn solid; a plateau
    the table skips is drawn as a dotted connector and is NOT interpolated.

    Returns (solid, dotted, markers) where solid is a list of
    (x0, x1, y_headline, y_env_lo, y_env_hi, F)."""
    d = sorted(r["tol_deficit"] for r in lad)          # 0, 10.29, 103.18, ... 528.17
    edges = d + [float("inf")]

    def F_of(k):
        return 1 + sum(1 for x in d if x <= k)

    # plateau i runs [edges[i], edges[i+1]) and carries F = i+2
    plateaus = []
    for i in range(len(d)):
        lo, hi = edges[i], edges[i + 1]
        if hi - lo < 1e-9:
            continue                                    # coincident admissions (112.07/112.10)
        plateaus.append({"lo": lo, "hi": hi, "F": i + 2})

    # attach the measured ratio, if the table samples a k inside the plateau
    for p in plateaus:
        got = None
        for k, row in table.items():
            if p["lo"] <= k < p["hi"]:
                if got is not None and abs(got["ratios"][DENOM_HEADLINE]
                                           - row["ratios"][DENOM_HEADLINE]) > 1e-9:
                    raise SystemExit(f"CONSISTENCY FAILURE: plateau F={p['F']} sampled twice "
                                     f"with different ratios")
                if row["F"] != p["F"]:
                    raise SystemExit(f"CONSISTENCY FAILURE: k={k} reports F={row['F']}, "
                                     f"ladder says F={p['F']}")
                got = row
        p["row"] = got
        if got is not None:
            vals = [got["ratios"][c] for c in DENOM_ENVELOPE]
            p["y"] = got["ratios"][DENOM_HEADLINE]
            p["lo_env"], p["hi_env"] = min(vals), max(vals)
            p["ks"] = sorted(k for k in table if p["lo"] <= k < p["hi"])
    return plateaus


def draw_step(ax, plateaus, xmax, band=True, color=C_SLOT1, marker_ks=True):
    """Solid where the admitted set is provably constant AND the value is measured;
    dotted where the sampling does not resolve it.  Never interpolate."""
    meas = [p for p in plateaus if p.get("row") is not None and p["lo"] < xmax]
    # envelope
    if band:
        for p in meas:
            x0, x1 = max(p["lo"], 0.0), min(p["hi"], xmax)
            ax.fill_between([x0, x1], [p["lo_env"]] * 2, [p["hi_env"]] * 2,
                            facecolor=C_BAND_WIDE, edgecolor="none", zorder=1.5)
    # solid plateaus
    for p in meas:
        x0, x1 = max(p["lo"], 0.0), min(p["hi"], xmax)
        ax.plot([x0, x1], [p["y"]] * 2, color=color, lw=1.3, solid_capstyle="butt", zorder=3)
    # risers + unresolved connectors
    for a, b in zip(meas, meas[1:]):
        if abs(a["hi"] - b["lo"]) < 1e-9:
            ax.plot([a["hi"]] * 2, [a["y"], b["y"]], color=color, lw=1.3, zorder=3)
        else:
            ax.plot([a["hi"], b["lo"]], [a["y"], b["y"]], color=color, lw=1.0,
                    ls=(0, (1.2, 1.4)), zorder=3)
    if marker_ks:
        xs, ys = [], []
        for p in meas:
            for k in p["ks"]:
                if k <= xmax:
                    xs.append(k); ys.append(p["y"])
        ax.scatter(xs, ys, s=8, facecolor=color, edgecolor="none", zorder=4)


def class_segments(rows):
    """Same discipline for the classification screen.  Membership changes are known
    only where R4 records them: the retained fits sit 0 to 2.04 points below the best
    peer, the four pre-fix per-period runs at 2.60-2.68, and full_seeds at 5.20.  So
    two plateaus are provable, [2.04, 2.60) and [2.68, 5.20), plus the ungated tail."""
    by = {r["gate_pts"]: r for r in rows if r["gate_pts"] is not None}
    nogate = [r for r in rows if r["gate_pts"] is None][0]
    solid = [
        {"lo": 2.04, "hi": 2.60, "y": by[2.5]["dim2"], "m": by[2.5]["m"], "sample": 2.5},
        {"lo": 2.68, "hi": 5.20, "y": by[3.0]["dim2"], "m": by[3.0]["m"], "sample": 3.0},
        {"lo": 5.20, "hi": 5.65, "y": nogate["dim2"], "m": nogate["m"], "sample": None},
    ]
    sampled = [(r["gate_pts"], r["dim2"], r["m"]) for r in rows if r["gate_pts"] is not None]
    return solid, sampled, nogate


# ---------------------------------------------------------------------------
# 5.  PANELS
# ---------------------------------------------------------------------------
def _stack(d):
    """Wilkinson dot-plot stacking, so the near-coincident cluster at 103-115 steps
    reads as five marks and not as one blob.  Nothing is jittered in x."""
    order = np.argsort(d)
    ystack, last, level = np.zeros(len(d)), None, 0
    for i in order:
        lx = math.log10(max(d[i], 0.35))
        level = level + 1 if (last is not None and lx - last < 0.050) else 0
        ystack[i] = 0.5 + level * 1.0
        last = lx
    return ystack


def _ladder_axis(ax, xmax):
    ax.set_xscale("symlog", linthresh=1.0, linscale=0.45)
    ax.set_xlim(-0.30, xmax)
    ax.set_xticks([0, 1, 10, 100])
    ax.set_xticklabels(["0", "1", "10", "100"])
    ax.xaxis.set_minor_locator(matplotlib.ticker.SymmetricalLogLocator(
        base=10, linthresh=1.0, subs=[2, 3, 4, 5, 6, 7, 8, 9]))


def panel_ladder(ax, lad, admitted_kind, xmax=650.0):
    """(a) the ladder.  admitted_kind in {'gmp', 'class', 'both'}."""
    d = np.array([r["tol_deficit"] for r in lad])
    adm_gmp = np.array([r["tol_deficit"] <= GMP_ADMITTED_K[0] for r in lad])
    adm_cls = np.array([r["pct_deficit"] <= CLASS_RULE_PTS for r in lad])
    e_cls = float(max(r["tol_deficit"] for r in lad if r["pct_deficit"] <= CLASS_RULE_PTS))

    _ladder_axis(ax, xmax)
    ylo = -2.7 if admitted_kind == "both" else -0.35
    ax.set_ylim(ylo, 4.7)
    ax.set_yticks([])
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(C_MUTED)

    # admitted span, drawn behind everything
    edge = {"gmp": GMP_ADMITTED_K[1], "both": GMP_ADMITTED_K[1], "class": e_cls}[admitted_kind]
    ax.axvspan(-0.30, edge, facecolor=C_SPAN_FILL, edgecolor="none", zorder=0)
    ax.plot([edge] * 2, [ylo, 4.7], color=C_SPAN_EDGE, lw=0.7, zorder=0.5)

    ystack = _stack(d)
    keep = adm_cls if admitted_kind == "class" else adm_gmp
    ax.scatter(d[keep], ystack[keep], s=13, facecolor=C_SLOT1, edgecolor="none", zorder=4)
    ax.scatter(d[~keep], ystack[~keep], s=13, facecolor=C_SURFACE, edgecolor=C_MUTED,
               linewidths=0.7, zorder=4)

    # the reach of each rule, drawn as a bar, only on the decision sheet
    if admitted_kind == "both":
        ax.plot([0.0, GMP_ADMITTED_K[1]], [-1.05] * 2, color=C_SLOT1, lw=2.0,
                solid_capstyle="butt", zorder=3)
        ax.plot([0.0, e_cls], [-2.05] * 2, color=C_SLOT2, lw=2.0,
                solid_capstyle="butt", zorder=3)
        ax.text(GMP_ADMITTED_K[1] * 1.35, -1.05, "tolerance", ha="left", va="center",
                fontsize=6.5, color=C_SLOT1)
        ax.text(e_cls * 1.28, -2.05, "classification", ha="left", va="center",
                fontsize=6.5, color=C_SLOT2)
    ax.set_xlabel("GMP deficit (tolerance steps)", labelpad=2)


Y_LABEL = "dim-2 SD / SE"


def panel_gmp(ax, plateaus, xmax, ylim, show_ylabel=True):
    ax.axvspan(GMP_ADMITTED_K[0], GMP_ADMITTED_K[1], facecolor=C_SPAN_FILL,
               edgecolor=C_SPAN_EDGE, lw=0.7, zorder=0)
    ax.axhline(PUBLISHED_RATIO, color=C_MUTED, lw=0.8, ls=(0, (3.5, 2.2)), zorder=2)
    draw_step(ax, plateaus, xmax)
    _ladder_axis(ax, xmax)
    ax.set_ylim(*ylim)
    ax.set_yticks([2.2, 2.6, 3.0, 3.4])
    ax.grid(axis="y", zorder=0.2)
    ax.set_axisbelow(True)
    for s in ("right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("threshold $k$ (tolerance steps)", labelpad=2)
    if show_ylabel:
        ax.set_ylabel(Y_LABEL, labelpad=3)


def panel_class(ax, solid, sampled, nogate, balanced, ylim, show_ylabel=True):
    ax.axvspan(CLASS_ADMITTED_PTS[0], CLASS_ADMITTED_PTS[1], facecolor=C_SPAN_FILL,
               edgecolor=C_SPAN_EDGE, lw=0.7, zorder=0)
    ax.axhline(PUBLISHED_RATIO, color=C_MUTED, lw=0.8, ls=(0, (3.5, 2.2)), zorder=2)
    for p in solid:
        ax.plot([p["lo"], p["hi"]], [p["y"]] * 2, color=C_SLOT1, lw=1.3,
                solid_capstyle="butt", zorder=3)
    # unresolved sampling below 2.04 and between 2.60 and 2.68
    pts = sorted(sampled)
    lowx = [x for x, _, _ in pts if x <= 2.0] + [solid[0]["lo"]]
    lowy = [y for x, y, _ in pts if x <= 2.0] + [solid[0]["y"]]
    ax.plot(lowx, lowy, color=C_SLOT1, lw=1.0, ls=(0, (1.2, 1.4)), zorder=3)
    ax.plot([solid[0]["hi"], solid[1]["lo"]], [solid[0]["y"], solid[1]["y"]],
            color=C_SLOT1, lw=1.0, ls=(0, (1.2, 1.4)), zorder=3)
    ax.plot([solid[1]["hi"]] * 2, [solid[1]["y"], solid[2]["y"]], color=C_SLOT1,
            lw=1.3, zorder=3)
    ax.scatter([x for x, _, _ in pts], [y for _, y, _ in pts], s=8,
               facecolor=C_SLOT1, edgecolor="none", zorder=4)
    # what this rule actually reports: the balanced design, not the census
    ax.errorbar([CLASS_RULE_PTS], [balanced["dim2"]],
                yerr=[[balanced["dim2"] - balanced["lo"]], [balanced["hi"] - balanced["dim2"]]],
                fmt="s", ms=3.4, mfc=C_SLOT2, mec=C_SLOT2, ecolor=C_SLOT2,
                elinewidth=1.0, capsize=2.0, capthick=0.9, zorder=5)
    ax.set_xlim(0.0, 5.65)
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_ylim(*ylim)
    ax.set_yticks([2.2, 2.6, 3.0, 3.4])
    ax.grid(axis="y", zorder=0.2)
    ax.set_axisbelow(True)
    for s in ("right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("admissibility threshold (classification percentage points)", labelpad=2)
    if show_ylabel:
        ax.set_ylabel("dim-2 spread / bootstrap SE", labelpad=3)


# ---------------------------------------------------------------------------
# 6.  LEGENDS
# ---------------------------------------------------------------------------
def leg_gmp(fig, y):
    h = [Line2D([], [], color=C_SLOT1, lw=1.3, marker="o", ms=3, mfc=C_SLOT1, mec="none",
                label="reported denominator"),
         Patch(facecolor=C_BAND_WIDE, edgecolor="none", label="in-ensemble denominators"),
         Line2D([], [], color=C_SLOT1, lw=1.0, ls=(0, (1.2, 1.4)), label="not sampled"),
         Line2D([], [], color=C_MUTED, lw=0.8, ls=(0, (3.5, 2.2)), label="published value"),
         Patch(facecolor=C_SPAN_FILL, edgecolor=C_SPAN_EDGE, lw=0.7, label="admitted"),
         Line2D([], [], color="none", label=" ")]
    fig.legend(handles=h[:5], loc="lower center", bbox_to_anchor=(0.5, y), ncol=2,
               frameon=False, handlelength=1.7, columnspacing=1.1, handletextpad=0.5,
               labelspacing=0.32, borderpad=0.0)


def leg_class(fig, y):
    h = [Line2D([], [], color=C_SLOT1, lw=1.3, marker="o", ms=3, mfc=C_SLOT1, mec="none",
                label="census of admitted fits"),
         Line2D([], [], color=C_SLOT2, lw=1.0, marker="s", ms=3.4, mfc=C_SLOT2, mec=C_SLOT2,
                label="balanced design, as reported"),
         Line2D([], [], color=C_SLOT1, lw=1.0, ls=(0, (1.2, 1.4)), label="not sampled"),
         Line2D([], [], color=C_MUTED, lw=0.8, ls=(0, (3.5, 2.2)), label="published value"),
         Patch(facecolor=C_SPAN_FILL, edgecolor=C_SPAN_EDGE, lw=0.7, label="admitted")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, y), ncol=2,
               frameon=False, handlelength=1.7, columnspacing=1.1, handletextpad=0.5,
               labelspacing=0.32, borderpad=0.0)


def leg_ladder(fig, y):
    h = [Line2D([], [], color="none", marker="o", ms=4, mfc=C_SLOT1, mec="none",
                label="admitted"),
         Line2D([], [], color="none", marker="o", ms=4, mfc=C_SURFACE, mec=C_MUTED,
                mew=0.8, label="excluded")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, y), ncol=2,
               frameon=False, handlelength=1.0, columnspacing=1.4, handletextpad=0.4,
               borderpad=0.0)


def tag(ax, s):
    ax.text(-0.155, 1.0, s, transform=ax.transAxes, ha="left", va="top",
            fontsize=8, fontweight="bold", color=C_INK)


# ---------------------------------------------------------------------------
# 7.  FIGURES
# ---------------------------------------------------------------------------
def fig_gmp(lad, plateaus, xmax, ylim, out):
    fig = plt.figure(figsize=(COL_W_IN, 3.15))
    axa = fig.add_axes([0.175, 0.795, 0.795, 0.150])
    axb = fig.add_axes([0.175, 0.335, 0.795, 0.360])
    panel_ladder(axa, lad, "gmp", xmax)
    panel_gmp(axb, plateaus, xmax, ylim)
    tag(axa, "(a)"); tag(axb, "(b)")
    leg_ladder(fig, 0.700)
    leg_gmp(fig, 0.005)
    save(fig, out)


def fig_class(lad, cls_solid, cls_sampled, nogate, balanced, ylim, out, xmax):
    fig = plt.figure(figsize=(COL_W_IN, 3.15))
    axa = fig.add_axes([0.175, 0.795, 0.795, 0.150])
    axb = fig.add_axes([0.175, 0.335, 0.795, 0.360])
    panel_ladder(axa, lad, "class", xmax)
    panel_class(axb, cls_solid, cls_sampled, nogate, balanced, ylim)
    tag(axa, "(a)"); tag(axb, "(b)")
    leg_ladder(fig, 0.700)
    leg_class(fig, 0.005)
    save(fig, out)


def fig_compare(lad, plateaus, xmax, cls_solid, cls_sampled, nogate, balanced, ylim, out):
    fig = plt.figure(figsize=(COL_W_IN, 4.75))
    axa = fig.add_axes([0.175, 0.855, 0.795, 0.098])
    axb = fig.add_axes([0.175, 0.520, 0.795, 0.235])
    axc = fig.add_axes([0.175, 0.185, 0.795, 0.235])
    panel_ladder(axa, lad, "both", xmax)
    panel_gmp(axb, plateaus, xmax, ylim)
    panel_class(axc, cls_solid, cls_sampled, nogate, balanced, ylim)
    tag(axa, "(a)"); tag(axb, "(b)"); tag(axc, "(c)")
    leg_gmp(fig, 0.437)
    leg_class(fig, 0.005)
    save(fig, out)


def save(fig, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    # bbox_inches=None: the emitted canvas must stay exactly 3.5in so
    # \includegraphics[width=\columnwidth] renders at scale 1.0 (FIGURE-DESIGN 7.4)
    fig.savefig(out.with_suffix(".png"), dpi=400, bbox_inches=None, pad_inches=0.01)
    fig.savefig(out.with_suffix(".pdf"), bbox_inches=None, pad_inches=0.01)
    plt.close(fig)
    print(f"  wrote {out.with_suffix('.png').name}  and  {out.with_suffix('.pdf').name}")


# ---------------------------------------------------------------------------
# 8.  MAIN
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--figdir", default=str(DEFAULT_FIGDIR))
    args = ap.parse_args()
    figdir = Path(args.figdir)
    rc()

    p2leg = assert_panel_alignment()
    lad, n_raw, n_uniq, best_name, best_gmp, best_pct = read_ladder()
    table, n_keys, cols = read_joint_out()
    cls_rows, balanced, n_roster_class = read_class_table()

    # cross-check: the ladder recomputed from the log-likelihoods must reproduce the
    # one printed in _joint_niter4.out, to the printed precision
    printed = re.findall(r"^\s{2}(\S+)\s+\S+\s+logL\s+(-[\d.]+)\s+(\d+) tol\s+([\d.]+)%$",
                         SRC_JOINT_OUT.read_text(encoding="utf-8"), re.M)
    if len(printed) != len(lad):
        raise SystemExit(f"LADDER MISMATCH: recomputed {len(lad)} reps, artifact prints {len(printed)}")
    for (pn, pll, ptol, ppct), r in zip(printed, lad):
        if pn != r["name"] or int(ptol) != round(r["tol_deficit"]):
            raise SystemExit(f"LADDER MISMATCH: {pn}/{ptol} vs {r['name']}/{r['tol_deficit']:.4f}")
    if n_keys != 482:
        raise SystemExit(f"ROSTER FAILURE: n keys = {n_keys}, expected 482 on legs 366-368")

    print(f"ladder ok: {n_raw} raw / {n_uniq} distinct NITER=4 fits on the "
          f"{PANEL_VOTES:,}-vote panel; best = {best_name}")
    for r in lad:
        print(f"  {r['name']:<32} {r['tol_deficit']:>9.4f} tol   {r['pct_deficit']:>6.4f} pts")

    plateaus = gmp_segments(lad, table)
    xmax = 650.0
    cls_solid, cls_sampled, nogate = class_segments(cls_rows)

    ys = [p["lo_env"] for p in plateaus if p.get("row")] + \
         [p["hi_env"] for p in plateaus if p.get("row")] + \
         [r["dim2"] for r in cls_rows] + [balanced["lo"], balanced["hi"], PUBLISHED_RATIO]
    ylim = (2.10, 3.62)
    print(f"y data range {min(ys):.2f} .. {max(ys):.2f}, axis {ylim}")

    stem = figdir / f"{FIGNAME}"
    fig_gmp(lad, plateaus, xmax, ylim, Path(f"{stem}-gmp_{VERSION}"))
    fig_class(lad, cls_solid, cls_sampled, nogate, balanced, ylim,
              Path(f"{stem}-class_{VERSION}"), xmax)
    fig_compare(lad, plateaus, xmax, cls_solid, cls_sampled, nogate, balanced, ylim,
                Path(f"{stem}-compare_{VERSION}"))

    write_manifests(figdir, lad, plateaus, table, n_keys, cls_rows, balanced,
                    n_roster_class, n_raw, n_uniq, best_name, best_gmp, best_pct, xmax, ylim)


def _srcs():
    return {str(p): {"md5": md5(p), "bytes": p.stat().st_size} for p in
            (SRC_LL_TABLE, SRC_JOINT_OUT, SRC_LEGMAP, SRC_R4, SRC_SECIV)}


def write_manifests(figdir, lad, plateaus, table, n_keys, cls_rows, balanced,
                    n_roster_class, n_raw, n_uniq, best_name, best_gmp, best_pct, xmax, ylim):
    common = {
        "figure_family": FIGNAME,
        "spec": "FIGURE-DESIGN-2026-08-11.md section 3, fig2-admissibility (rank 3, essential)",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": str(Path(__file__).resolve()),
        "generating_command": f"python \"{Path(__file__).resolve()}\" --figdir \"{figdir}\"",
        "python": sys.version.split()[0],
        "matplotlib": matplotlib.__version__,
        "numpy": np.__version__,
        "include_width": {"figsize_in": [COL_W_IN, None], "columnwidth_pt": 252,
                          "bbox_inches": None, "pad_inches": 0.01,
                          "note": "authored at scale 1.0; never use bbox_inches='tight'"},
        "pdf_fonttype": 42,
        "font_family": matplotlib.rcParams["font.family"],
        "panel": {
            "name": "chile 23-period panel",
            "legislaturas": f"{PANEL_LEGS[0]}-{PANEL_LEGS[1]}",
            "periods": 23,
            "valid_votes": PANEL_VOTES,
            "input_dir": "reproduce/out/chile/cpp_input/",
            "numerator_legislaturas": list(NUMERATOR_LEGS),
            "data_contract": "DATA-CONTRACT-2026-08-05.md section 4 and section 8",
        },
        "alignment": {
            "fortran_artifact_read": None,
            "banned_artifact": "dwnom2004_chile (347-369 panel, us.num line 1 '1 103 120 120')",
            "assertion": "legislatura_map.csv period_index 1->346, 21->366, 22->367, 23->368; "
                         "asserted in assert_panel_alignment(), SystemExit on mismatch",
            "procrustes_operator": "uncentred orthogonal Procrustes onto the QueVotan "
                                   "reference, single global rotation over the stacked "
                                   "(legislatura, legislator) set, no scaling "
                                   "(_joint_niter4.py:50-51, proc())",
            "procrustes_note": "FIGURE-DESIGN 5.4 item 2: tab:fidelity uses CENTRED Procrustes. "
                               "This figure's numerator is UNCENTRED. Do not call both "
                               "'Procrustes-aligned' without saying which.",
            "padding": "the ratios inherit _joint_niter4.py's key join, which is the "
                       "intersection of the reference roster with every admitted fit "
                       f"({n_keys} keys); padded rows never enter",
        },
        "lopsidedness_screen": {
            "side": "post-screen; this figure counts frames, not roll calls or votes",
            "threshold": 0.025,
            "sites": ["main_cli.cpp:471", "dwnominate.cpp:187", "dwnom2004.f:324-326"],
            "roll_calls_total": 12952, "roll_calls_dropped": 6094, "roll_calls_kept": 6858,
        },
        "denominator": {
            "constant_name": "DENOM_MED_SE_DIM2",
            "value": DENOM_MED_SE_DIM2,
            "label": DENOM_HEADLINE_LABEL,
            "base_fit": "cpp_run_chile",
            "artifact": DENOM_HEADLINE_PATH,
            "swap_note": "pablo-10 may replace this with a bootstrap on canary_fseed_i4; "
                         "that is a one-line edit at the top of the generator "
                         "(PABLO-HANDOFF-2026-08-11.md D1)",
            "envelope": list(DENOM_ENVELOPE),
            "excluded_from_envelope": list(DENOM_EXCLUDED),
            "exclusion_grounds": "DESK-PLAN-2026-08-06.md 1.3: base fit not in the ensemble; "
                                 "43.4% of placements at radius > 0.99; unit-dispersion "
                                 "rescaling inverts it from smallest to largest ratio",
        },
        "sources": _srcs(),
        "ladder": [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}
                   for r in lad],
        "ladder_provenance": {
            "recomputed_from": str(SRC_LL_TABLE),
            "formula": "GMP = exp(logL / 692839); deficit = (GMP_best - GMP_fit) / 1e-4",
            "convergence_tol_site": "optimize_legislators.hpp:23, convergenceTol = 1e-4",
            "nats_per_tolerance_step": 80.07,
            "cross_check": "reproduces the ladder printed in _joint_niter4.out "
                           "(0, 10, 103, 112, 112, 115, 139, 301, 528); "
                           "SystemExit on mismatch",
            "fits_considered": {"raw": n_raw, "distinct_payloads": n_uniq,
                                "cell_representatives": len(lad), "best": best_name},
        },
        "compute": "none. No fit, no bootstrap, no Procrustes, no engine invocation. "
                   "The only arithmetic is exp(logL/N) over log-likelihoods already on disk.",
    }

    rows_gmp = []
    for p in plateaus:
        if p.get("row") is None:
            rows_gmp.append({"k_interval": [p["lo"], p["hi"]], "F": p["F"],
                             "ratio_dim2": None, "status": "NOT SAMPLED, drawn dotted"})
        else:
            rows_gmp.append({"k_interval": [round(p["lo"], 4), (None if math.isinf(p["hi"])
                                                                else round(p["hi"], 4))],
                             "F": p["F"], "sampled_k": p["ks"],
                             "ratio_dim2_reported_denominator": p["y"],
                             "envelope_dim2": [p["lo_env"], p["hi_env"]],
                             "ratios_all_denominators": p["row"]["ratios"],
                             "sd2": p["row"]["sd2"], "sd1": p["row"]["sd1"],
                             "flip1": p["row"]["flip1"], "flip2": p["row"]["flip2"],
                             "status": "measured"})

    gmp_block = {
        "variant": "GMP convergence-tolerance screen",
        "rule": "admit a fit whose GMP sits within k convergence-tolerance steps of the "
                "best fit on the same panel, plus the external QueVotan reference",
        "ruling": "DESK-PLAN-2026-08-06.md section 2.1 (unsigned as of 2026-08-11)",
        "admitted_threshold_interval": list(GMP_ADMITTED_K),
        "why_that_interval": "the ladder has a hole: retained fits at 0 and 10.29 steps, "
                             "the next at 103.18, so every k in [11,102] gives the same "
                             "partition. The rule's only free parameter moves by a factor "
                             "of nine and the answer does not move.",
        "ensemble_construction": "one representative per (seed lineage x temporal order) "
                                 "cell, representative chosen by highest log-likelihood, "
                                 "then gated (_joint_niter4.py:39-42)",
        "rows": n_keys, "roster": "482 (legislatura, legislator) keys on legs 366-368",
        "columns_plotted": 4, "denominator_columns": list(DENOM_ENVELOPE),
        "x_axis": {"quantity": "admissibility threshold k, convergence-tolerance steps",
                   "scale": "symlog, linthresh 1", "range": [0, xmax]},
        "y_axis": {"quantity": "median cross-frame dim-2 SD / median bootstrap dim-2 SE",
                   "range": list(ylim)},
        "step_table": rows_gmp,
        "departure_from_spec": "FIGURE-DESIGN 3 says x runs 1 to 400. This runs 0 to 650 so "
                               "the ungated plateau (k >= 528.17, F=10, 3.44x, measured at "
                               "the k=10000 row) is drawn and panel (a) and panel (b) share "
                               "one x quantity. No value is invented by the extension.",
        "not_interpolated": "the plateaus at F=4,5,6,7 (k in [103.18, 138.94]) are not "
                            "sampled by _joint_niter4.out and are drawn as a dotted "
                            "connector, not as a value",
    }

    class_block = {
        "variant": "classification-percentage screen",
        "rule": "admit a fit that classifies within 2.5 percentage points of the best run "
                "on the same panel with the same engine",
        "source_of_rule": "SEC-IV-admissibility-2026-08-06.tex, 'Adequacy of fit'",
        "admitted_threshold_interval": list(CLASS_ADMITTED_PTS),
        "why_that_interval": "retained fits sit 0 to 2.04 points below their best peer and "
                             "excluded ones 2.60 to 5.20 points below (R4-FRAME-ENSEMBLE "
                             "section 3), so any cut in that interval gives the same partition",
        "ensemble_construction": "census of distinct payloads after G1 (same estimand) and "
                                 "G2 (NITER=4), NOT collapsed to cell representatives "
                                 "(_r4x_floor.py panel B2)",
        "roster": f"{n_roster_class} placements (R4-FRAME-ENSEMBLE section 4)",
        "roster_warning": "this is NOT the 482-key roster the GMP arm uses. The two arms "
                          "are not the same computation with a different gate; they differ "
                          "in gate, in ensemble construction and in roster.",
        "denominator": DENOM_CLASS, "denominator_artifact": DENOM_CLASS_PATH,
        "denominator_gap": "no four-denominator envelope exists for this arm anywhere on "
                           "disk. Panel (b) of this variant carries ONE denominator. "
                           "FIGURE-DESIGN inversion I2's envelope is unavailable here.",
        "census_rows": cls_rows,
        "reported_value": {"design": "balanced, one frame per seed construction, over all "
                                     "28 choices of representative",
                           "dim2": balanced["dim2"], "ci": [balanced["lo"], balanced["hi"]],
                           "note": "SEC-IV reports the balanced design (3.3x), not the "
                                   "census (2.8x). Both are drawn."},
        "step_table": [{"gate_interval": [p["lo"], p["hi"]], "m": p["m"],
                        "ratio_dim2": p["y"], "sampled_at": p["sample"],
                        "status": "measured plateau"} for p in class_solid_repr(cls_rows)],
        "not_interpolated": "membership below 2.04 points is sampled at 0.5, 1.0, 1.5 and "
                            "2.0 but the riser positions are not recorded anywhere on disk; "
                            "that stretch is drawn as a dotted connector through the samples",
        "x_axis": {"quantity": "admissibility threshold, classification percentage points",
                   "scale": "linear", "range": [0.0, 5.65],
                   "note": "the 'no gate' row is plotted at 5.20, the largest classification "
                           "deficit on the ladder; it holds for every threshold above that"},
        "y_axis": {"quantity": "median cross-frame dim-2 SD / median bootstrap dim-2 SE",
                   "range": list(ylim)},
    }

    disagreement = {
        "status": "UNRESOLVED, and this figure must not resolve it",
        "level": "the tolerance rule reports 2.55x to 2.75x on its plateau; the "
                 "classification rule reports 2.80x census and 3.30x balanced. "
                 "3.30 / 2.55 = 1.29.",
        "direction": "under the tolerance rule the ratio FALLS as the screen loosens over "
                     "k in [11, 300] (2.75 -> 2.38) and only rises once the screen is "
                     "effectively off. SEC-IV states the opposite for its rule: 'a referee "
                     "who prefers a laxer rule gets a larger number, not a smaller one'.",
        "reach": "the classification rule admits fits 138.9 tolerance steps behind the best; "
                 "the tolerance rule admits none past 10.3. Panel (a) of each variant shades "
                 "its own rule's reach on the same ladder.",
        "who_decides": "Roberto. DESK-PLAN section 2.1 recommends the tolerance rule; it is "
                       "unsigned as of 2026-08-11.",
    }

    files = {
        f"{FIGNAME}-gmp": {"panels": ["(a) ladder, tolerance rule shaded",
                                      "(b) response curve, tolerance rule"],
                           "variant": gmp_block, "figsize_in": [COL_W_IN, 3.15]},
        f"{FIGNAME}-class": {"panels": ["(a) ladder, classification rule shaded",
                                        "(b) response curve, classification rule"],
                             "variant": class_block, "figsize_in": [COL_W_IN, 3.15]},
        f"{FIGNAME}-compare": {"panels": ["(a) ladder, both rules' reach",
                                          "(b) tolerance rule", "(c) classification rule"],
                               "variant": {"gmp": gmp_block, "class": class_block},
                               "figsize_in": [COL_W_IN, 4.75],
                               "purpose": "decision aid, not a paper figure"},
    }
    for name, extra in files.items():
        man = dict(common)
        man["figure"] = name
        man["rendered"] = [f"{name}_{VERSION}.png", f"{name}_{VERSION}.pdf"]
        man.update(extra)
        man["panel_b_disagreement"] = disagreement
        man["caption_draft"] = CAPTIONS[name]
        p = figdir / f"{name}.manifest.json"
        p.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  wrote {p.name}")


def class_solid_repr(cls_rows):
    s, _, _ = class_segments(cls_rows)
    return s


CAPTIONS = {
    "fig2-admissibility-gmp":
        "Fig. 2. Admissibility and its consequence, legislaturas 346 to 368, second "
        "dimension on the 482 placements of legislaturas 366 to 368. (a) Each candidate "
        "fit at its geometric-mean-probability deficit from the best fit at the prescribed "
        "iteration count, in convergence-tolerance steps of the estimator's own criterion; "
        "filled marks are admitted, the shaded span is the admitted region. (b) The "
        "second-dimension spread divided by the bootstrap standard error as a function of "
        "the threshold, solid line on the reported denominator, pale band across the other "
        "in-ensemble denominators; the dotted stretch is not sampled. The dashed rule is "
        "the published value. The threshold falls in an empty interval.",
    "fig2-admissibility-class":
        "Fig. 2. Admissibility and its consequence, legislaturas 346 to 368, second "
        "dimension. (a) Each candidate fit at its geometric-mean-probability deficit from "
        "the best fit, in convergence-tolerance steps; filled marks are those the "
        "classification screen admits. (b) The second-dimension spread divided by the "
        "bootstrap standard error as a function of the classification threshold, over the "
        "census of admitted fits and over the balanced design that is reported; the dotted "
        "stretch is not sampled. The dashed rule is the published value.",
    "fig2-admissibility-compare":
        "Decision sheet, not a paper figure. (a) The nine cell representatives on the "
        "tolerance ladder, with the reach of each candidate admissibility rule marked "
        "beneath. (b) The second-dimension ratio under the convergence-tolerance rule. "
        "(c) The same quantity under the classification rule, on the identical vertical "
        "scale. The two rules disagree on the level and on what loosening the screen does.",
}


if __name__ == "__main__":
    main()
