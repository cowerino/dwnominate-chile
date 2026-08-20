#!/usr/bin/env python3
"""fig5-floor-in-time  --  the identification floor by legislatura, and the estallido null.

FIGURE-DESIGN-2026-08-11.md section 3, fig5-floor-in-time (rank 2, essential).

WHAT THIS DRAWS
  Panel (a): median cross-frame dim-2 spread / median within-fit bootstrap SE, per
             legislatura, legs 346-368, one point per legislatura.
  Panel (b): the two components of that ratio in coordinate units, on one axis
             (same units -- this is NOT a dual axis).
  Optional panel (c) ("nullstrip" variant): the first difference of panel (a),
             so the step into the estallido legislatura can be read against the
             other twenty-one steps. This is the device that makes the NEGATIVE
             legible: absence is drawn as a small step among large ones, not as a
             missing spike.

THE OPEN DECISION THIS SCRIPT RENDERS RATHER THAN SETTLES
  Three ensembles live in the same JSON and disagree on legs 366/367/368:
      ALL            m=42   4.28 / 4.28 / 4.16
      AXIS-BALANCED  m=11   4.24 / 4.31 / 4.29     <- recommended (DESK-PLAN 5.5)
      PAPER-2        m= 2   2.51 / 2.47 / 2.38
  All three are rendered, at the same include width and on the SAME y-scale, plus a
  fourth "ensemble-compare" figure that overlays them. Roberto picks by looking.

PANEL, STATED (DATA-CONTRACT-2026-08-05.md section 8 is binding)
  legislaturas 346-368, 2002-03-19 .. 2021-03-10, 12,952 roll calls,
  692,839 valid votes, reproduce/out/chile/cpp_input/.

ALIGNMENT (FIGURE-DESIGN 5.4)
  1. Panel offset. The upstream series excludes `dwnom2004_chile` (us.num line 1
     `1 103 120 120` -> legs 347-369) by NAME and uses `dwnom2004_chile_per_period`
     (`1 25 119 119` -> legs 346-368). Asserted below; the script dies if the roster
     from _tb_series_out.txt does not match.
  2. Procrustes convention: UNCENTRED, UNSCALED orthogonal Procrustes, one single
     global rotation per frame over all 23 legislaturas stacked, target = iterated
     GPA consensus (operator key `gpa-global`). Not the centred operator used by
     tab:fidelity.
  3. Padding: the upstream series joins on (legislatura, legislator_id) keys that
     carry a bootstrap SE, n = 2,855 placements; padded roster rows never enter.

NO COMPUTE. This reads TEMPORAL-FLOOR-SERIES-2026-08-05.json and plots it. No fit,
no bootstrap, no Procrustes is run here.

Usage:
    python fig5-floor-in-time.py [--version v1]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths

# =============================================================================
# PATHS
# =============================================================================
PAPER = Path("C:/Users/cow/Documents/thesis-quevotan/papers/jcc-2026")
REPO = Path("C:/Users/cow/Documents/GitHub/quevotan-db")
SERIES_JSON = PAPER / "tools/analysis/TEMPORAL-FLOOR-SERIES-2026-08-05.json"  # moved by the 2026-08-13 reorg
SERIES_TXT = PAPER / "tools/analysis/_tb_series_out.txt"                      # moved by the 2026-08-13 reorg
UPSTREAM_GEN = REPO / "reproduce/scripts/_tb_floor_series.py"
LEGMAP_OUT = REPO / "output/legislatura_map.csv"
LEGMAP_IN = REPO / "reproduce/input/legislatura_map.csv"
OUTDIR = _paths.render_dir()   # was PAPER/"figs/v2026-08-11", a path the
                               # 2026-08-13 reorganization retired. Renders go to
                               # figures/renders/<date>/; survivors are copied into
                               # draft/figures/ by hand. reference-renders/ is frozen.

# =============================================================================
# DENOMINATOR.  Named constants, never inlined.  pablo-10 swaps these.
# =============================================================================
# fig5's denominator is a per-legislatura SERIES, not a scalar: the median
# within-fit parametric-bootstrap se2D per legislatura.  It is banked in
# reproduce/out/chile/julio_test/route2/dwnom_se.csv and is carried into the JSON
# as the `se2` field of every row.  A pablo-10 swap to a bootstrap of
# canary_fseed_i4 changes the whole series, so the true swap is one line HERE
# (DENOM_BANK_BASE / DENOM_SERIES_KEY) plus one re-run of the upstream generator
# _tb_floor_series.py:98-100.  DENOM_RESCALE is the interim single-line hook.
DENOM_BANK = "route2"                     # julio_test/route2/dwnom_se.csv
DENOM_BANK_B = 50                         # bootstrap replicates
DENOM_BANK_SIGMA = 0.05                   # parametric bootstrap sigma
DENOM_BANK_BASE = "cpp_run_chile"         # the fit that was bootstrapped
DENOM_SERIES_KEY = "se2"                  # per-legislatura median bootstrap SE, dim 2
DENOM_RESCALE = 1.0                       # multiplies the whole SE series; 1.0 = as banked
DENOM_MED_SE_DIM2_366_368 = 0.0721        # pooled median SE over legs 366-368, route2 B=50
NUMER_SERIES_KEY = "sd2"                  # per-legislatura median cross-frame SD, dim 2
RATIO_SERIES_KEY = "r2"                   # == sd2 / se2, as banked

# =============================================================================
# PANEL + ALIGNMENT CONSTANTS  (asserted, not assumed)
# =============================================================================
PANEL_LEGS = list(range(346, 369))         # 23 legislaturas
PANEL_SPAN = ("2002-03-19", "2021-03-10")
PANEL_ROLLCALLS = 12_952                   # pre-lopsidedness-screen, DATA-CONTRACT s.4
PANEL_VALID_VOTES = 692_839                # DATA-CONTRACT s.4
PANEL_SOURCE = "reproduce/out/chile/cpp_input/"

ALIGN_OPERATOR = "gpa-global"              # uncentred, unscaled, ONE global rotation
THIN_LEGS = (346, 347)                     # 25 and 103 roll calls; DATA-CONTRACT s.6
ESTALLIDO = date(2019, 10, 18)
SHOCK_LEG = 367                            # 2019-03-12 .. 2020-03-10

# The 0.025 minority lopsidedness screen (main_cli.cpp:471, dwnominate.cpp:187,
# dwnom2004.f:324-326) drops 6,094 of the panel's 12,952 roll calls INSIDE both
# engines.  Every roll-call count this figure uses (the thin-legislatura screen
# below, and PANEL_ROLLCALLS) is on the INPUT side of that screen.
SCREEN_SIDE = "pre-screen (input side of the 0.025 minority lopsidedness screen)"
SCREEN_DROPPED = 6_094

# Roster the upstream ensemble must and must not contain.  This is
# non-negotiable #1: reproducing the one-legislatura offset is the worst outcome.
MUST_CONTAIN = ("dwnom2004_chile_per_period",)
MUST_NOT_CONTAIN = ("dwnom2004_chile", "exp10_nofastmath_out", "b2_pablo_run")

# AXIS-BALANCED roster as declared at _tb_floor_series.py:201-214.  `dwnom2004_chile`
# is in that literal list but is dropped by the BADNAME filter at :45-52, which is
# why m=11 and not 12.
AXIS_DECLARED = (
    "cpp_run_chile", "cpp_run_chile_iter4", "canary_fseed_i4",
    "cpp_run_chile_full_seeds", "cpp_run_chile_p24_canon", "cpp_run_chile_p24",
    "cpp_run_chile_lapack_linear", "cpp_run_chile_lapack_cubic",
    "cpp_run_chile_fixed_iter16", "cpp_run_chile_iter1",
    "dwnom2004_chile", "dwnom2004_chile_per_period",
)

ENSEMBLES = [
    # slug,     json label,                     m,  y-axis tag,     human label
    ("all", "ALL", 42, "42 frames",
     "42-frame ensemble (ALL)"),
    ("axis", "AXIS-BALANCED", 11, "11 frames",
     "11-frame axis-balanced ensemble"),
    ("paper2", "PAPER-2 (spanning frames only)", 2, "2 frames",
     "2-frame ensemble (the paper's own two spanning frames)"),
]
RECOMMENDED = "axis"

# =============================================================================
# VISUAL SYSTEM.  FIGURE-DESIGN 7.3, validated 2026-08-11 with
#   node scripts/validate_palette.js "#2a78d6,#eb6834,#4a3aa7" \
#        --mode light --surface "#ffffff" --pairs all      -> ALL CHECKS PASS
# No alpha anywhere (DESK-PLAN 7.4: alpha forces a PDF transparency group).
# =============================================================================
C_SLOT1 = "#2a78d6"   # blue    -- numerator series / ensemble ALL
C_SLOT2 = "#eb6834"   # orange  -- denominator series / ensemble AXIS-BALANCED
C_SLOT3 = "#4a3aa7"   # violet  -- ensemble PAPER-2
C_INK = "#0b0b0b"     # primary ink
C_MUTED = "#898781"   # muted ink
C_GRID = "#e1e0d9"    # gridline, solid hairline, never dashed
C_SPAN_FILL = "#f0efec"
C_SPAN_EDGE = "#c3c2b7"

COL_W_IN = 3.5        # \columnwidth = 252pt.  Author here, never scale.
PNG_DPI = 600

ENS_STYLE = {
    "all": dict(color=C_SLOT1, ls="-", marker="o"),
    "axis": dict(color=C_SLOT2, ls="--", marker="s"),
    "paper2": dict(color=C_SLOT3, ls="-.", marker="^"),
}


def set_rc() -> None:
    plt.rcParams.update({
        "pdf.fonttype": 42,          # IEEE PDF eXpress rejects Type 3
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": 8,              # FIGURE-DESIGN 7.4 floor
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.width": 0.4,
        "ytick.minor.width": 0.4,
        "xtick.major.size": 2.4,
        "ytick.major.size": 2.4,
        "xtick.minor.size": 1.3,
        "lines.solid_capstyle": "round",
        "axes.edgecolor": C_MUTED,
        "xtick.color": C_MUTED,
        "ytick.color": C_MUTED,
        "text.color": C_INK,
        "axes.labelcolor": C_INK,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "legend.frameon": False,
    })


# =============================================================================
# LOAD + ASSERT
# =============================================================================
def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def parse_roster(txt: str) -> tuple[list[str], int]:
    """Frame roster and declared ensemble size from _tb_series_out.txt."""
    m = re.search(r"ENSEMBLE:\s+(\d+)\s+distinct full-span 2D fits", txt)
    if not m:
        sys.exit("FATAL: could not read the ensemble size from _tb_series_out.txt")
    n = int(m.group(1))
    names = re.findall(r"^\s*\d+\.\s+\[(?:cpp|fortran)\s*\]\s+(\S+)\s*$", txt, re.M)
    return names, n


def check_alignment(roster: list[str], n_declared: int) -> dict:
    """NON-NEGOTIABLE #1.  Fail loudly if the roster is not the aligned one."""
    problems = []
    if n_declared != 42:
        problems.append(f"ensemble header says {n_declared} frames, expected 42")
    if len(roster) != n_declared:
        problems.append(f"parsed {len(roster)} frame names, header says {n_declared}")
    for name in MUST_CONTAIN:
        if name not in roster:
            problems.append(f"REQUIRED aligned frame '{name}' missing from roster")
    for name in MUST_NOT_CONTAIN:
        if name in roster:
            problems.append(
                f"PANEL VIOLATOR '{name}' present in roster -- this is the "
                f"one-legislatura offset (FIGURE-DESIGN 5.1/5.2). REFUSING TO RENDER.")
    axis_used = [f for f in AXIS_DECLARED if f in roster]
    if len(axis_used) != 11:
        problems.append(f"AXIS-BALANCED resolves to {len(axis_used)} frames, expected 11")
    if "dwnom2004_chile" in axis_used:
        problems.append("AXIS-BALANCED still contains the 347-369 Fortran run")
    if problems:
        sys.exit("FATAL alignment assertion(s):\n  - " + "\n  - ".join(problems))
    return {"ensemble_all_m": n_declared, "axis_balanced_frames": axis_used}


def check_panel(rows: list[dict]) -> dict:
    """NON-NEGOTIABLE #2.  The panel is what the manifest and caption will claim."""
    problems = []
    legs = [r["leg"] for r in rows]
    if legs != PANEL_LEGS:
        problems.append(f"legislatura span is {legs[0]}-{legs[-1]} (n={len(legs)}), "
                        f"expected 346-368 (n=23)")
    rc_total = sum(r["rc"] for r in rows)
    if rc_total != PANEL_ROLLCALLS:
        problems.append(f"roll calls sum to {rc_total}, expected {PANEL_ROLLCALLS}")
    if (rows[0]["start"], rows[-1]["end"]) != PANEL_SPAN:
        problems.append(f"span {rows[0]['start']}..{rows[-1]['end']}, expected "
                        f"{PANEL_SPAN[0]}..{PANEL_SPAN[1]}")
    shock = next(r for r in rows if r["leg"] == SHOCK_LEG)
    if not (date.fromisoformat(shock["start"]) <= ESTALLIDO
            <= date.fromisoformat(shock["end"])):
        problems.append(f"estallido {ESTALLIDO} not inside leg {SHOCK_LEG} "
                        f"({shock['start']}..{shock['end']})")
    for leg, want in ((346, 25), (347, 103), (368, 1023)):
        got = next(r["rc"] for r in rows if r["leg"] == leg)
        if got != want:
            problems.append(f"leg {leg} has {got} roll calls, expected {want}")
    if problems:
        sys.exit("FATAL panel assertion(s):\n  - " + "\n  - ".join(problems))
    return {"rollcalls_total": rc_total,
            "legislators_per_leg": {r["leg"]: r["nlg"] for r in rows}}


def load() -> tuple[dict, dict, dict]:
    blob = json.loads(SERIES_JSON.read_text(encoding="utf-8"))
    txt = SERIES_TXT.read_text(encoding="utf-8-sig")
    roster, n_declared = parse_roster(txt)
    align_info = check_alignment(roster, n_declared)

    series = {}
    for slug, label, m, _tag, _human in ENSEMBLES:
        key = f"{ALIGN_OPERATOR}|{label}"
        if key not in blob:
            sys.exit(f"FATAL: '{key}' not in {SERIES_JSON.name}")
        rows = blob[key]
        check_panel(rows)
        series[slug] = rows

    # se2 is a property of the bootstrap bank, not of the ensemble: it must be
    # identical across all three.  If it is not, the three panels (b) are not
    # comparable and the whole variant sheet is meaningless.
    ref = np.array([r[DENOM_SERIES_KEY] for r in series["all"]])
    for slug in ("axis", "paper2"):
        got = np.array([r[DENOM_SERIES_KEY] for r in series[slug]])
        if not np.allclose(ref, got, rtol=0, atol=1e-12):
            sys.exit(f"FATAL: the bootstrap SE series differs between ALL and {slug}")

    # the banked r2 must be sd2/se2 exactly; if not, one of the three is stale.
    for slug, rows in series.items():
        sd = np.array([r[NUMER_SERIES_KEY] for r in rows])
        se = np.array([r[DENOM_SERIES_KEY] for r in rows])
        r = np.array([r[RATIO_SERIES_KEY] for r in rows])
        if not np.allclose(sd / se, r, rtol=1e-9, atol=0):
            sys.exit(f"FATAL: r2 != sd2/se2 for ensemble {slug}")

    panel_info = check_panel(series["all"])
    return series, align_info, panel_info


# =============================================================================
# DRAWING PRIMITIVES
# =============================================================================
def leg_to_x(leg: int) -> float:
    return float(leg)


def estallido_x(rows: list[dict]) -> float:
    """The estallido date placed proportionally inside leg 367's own span."""
    r = next(x for x in rows if x["leg"] == SHOCK_LEG)
    a, b = date.fromisoformat(r["start"]), date.fromisoformat(r["end"])
    frac = (ESTALLIDO - a).days / (b - a).days
    return SHOCK_LEG - 0.5 + frac


def cohort_boundaries(rows: list[dict]) -> list[float]:
    """x positions between two different congresses (the `cohort` field)."""
    out = []
    for prev, cur in zip(rows, rows[1:]):
        if cur["cohort"] != prev["cohort"]:
            out.append(cur["leg"] - 0.5)
    return out


def chrome(ax, rows, *, shock=True, xlabels=False, ylabel="", ymin=None, ymax=None):
    """Shared axis furniture: grid, spans, congress rules, ticks."""
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=C_GRID, linewidth=0.4, linestyle="-")
    ax.xaxis.grid(False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(C_MUTED)
    ax.spines["bottom"].set_color(C_MUTED)

    # congress (cohort) boundaries: structural chrome, solid hairline
    for x in cohort_boundaries(rows):
        ax.axvline(x, color=C_SPAN_EDGE, linewidth=0.5, zorder=0.5)

    if shock:
        ax.axvspan(SHOCK_LEG - 0.5, SHOCK_LEG + 0.5, facecolor=C_SPAN_FILL,
                   edgecolor=C_SPAN_EDGE, linewidth=0.5, zorder=0.4)
        ax.axvline(estallido_x(rows), color=C_INK, linewidth=0.7,
                   linestyle=(0, (2.2, 1.6)), zorder=0.6)

    ax.set_xlim(345.4, 368.6)
    if ymin is not None:
        ax.set_ylim(ymin, ymax)
    ax.set_xticks(list(range(346, 369, 3)))
    ax.set_xticks(PANEL_LEGS, minor=True)
    if xlabels:
        yr = {r["leg"]: r["start"][:4] for r in rows}
        ax.set_xticklabels([f"{l}\n{yr[l]}" for l in range(346, 369, 3)], color=C_INK)
    else:
        ax.set_xticklabels([])
    if ylabel:
        ax.set_ylabel(ylabel, color=C_INK)
    ax.tick_params(axis="y", labelcolor=C_INK)


def panel_tag(ax, tag):
    ax.text(0.012, 0.965, tag, transform=ax.transAxes, ha="left", va="top",
            fontsize=7.5, color=C_INK)


def draw_ratio(ax, rows, *, color=C_INK, ls="-", marker="o", lw=1.0, label=None):
    """Panel (a) series.  Thin legislaturas get open markers + a dashed segment."""
    x = np.array([leg_to_x(r["leg"]) for r in rows], float)
    y = np.array([r[RATIO_SERIES_KEY] for r in rows], float)
    thin = np.array([r["leg"] in THIN_LEGS for r in rows])
    k = int(np.argmax(~thin))                     # first scalable legislatura

    ax.plot(x[k:], y[k:], color=color, linewidth=lw, linestyle=ls,
            marker=marker, markersize=2.6, markerfacecolor=color,
            markeredgecolor=color, markeredgewidth=0.0, zorder=3, label=label,
            solid_joinstyle="round")
    # the thin head, drawn as unscalable: open markers, dashed connector
    ax.plot(x[:k + 1], y[:k + 1], color=color, linewidth=lw * 0.8,
            linestyle=(0, (1.6, 1.6)), zorder=2.4)
    ax.plot(x[:k], y[:k], linestyle="none", marker=marker, markersize=2.6,
            markerfacecolor="none", markeredgecolor=color, markeredgewidth=0.7,
            zorder=3)


def draw_components(ax, rows, *, sd_color=C_SLOT1, label_sd=None, label_se=None):
    """Panel (b): numerator and denominator, one axis, same coordinate units."""
    x = np.array([leg_to_x(r["leg"]) for r in rows], float)
    sd = np.array([r[NUMER_SERIES_KEY] for r in rows], float)
    se = np.array([r[DENOM_SERIES_KEY] for r in rows], float) * DENOM_RESCALE
    ax.plot(x, sd, color=sd_color, linewidth=1.0, linestyle="-", marker="o",
            markersize=2.4, markerfacecolor=sd_color, markeredgewidth=0.0,
            zorder=3, label=label_sd)
    ax.plot(x, se, color=C_SLOT2, linewidth=1.0, linestyle=(0, (3.0, 1.7)),
            marker="s", markersize=2.2, markerfacecolor=C_SLOT2,
            markeredgewidth=0.0, zorder=3, label=label_se)


def draw_steps(ax, rows, *, color=C_INK):
    """Panel (c): first difference of the ratio.  The null, made legible.

    The stem at legislatura L is r2(L) - r2(L-1), the change INTO L, so the stem
    inside the shaded band is the change into the estallido legislatura.  A step
    is muted when either of its two endpoints is an unscalable thin legislatura.
    """
    legs = [r["leg"] for r in rows]
    x = np.array(legs, float)[1:]
    y = np.diff([r[RATIO_SERIES_KEY] for r in rows])
    thin = np.array([(legs[i] in THIN_LEGS) or (legs[i - 1] in THIN_LEGS)
                     for i in range(1, len(legs))])
    ax.axhline(0.0, color=C_MUTED, linewidth=0.6, zorder=1.5)
    for xi, yi, ti in zip(x, y, thin):
        ax.plot([xi, xi], [0.0, yi], color=C_MUTED if ti else color,
                linewidth=0.9, zorder=2.5, solid_capstyle="butt")
    ax.plot(x[~thin], y[~thin], linestyle="none", marker="o", markersize=2.6,
            markerfacecolor=color, markeredgecolor=color, markeredgewidth=0.0,
            zorder=3)
    ax.plot(x[thin], y[thin], linestyle="none", marker="o", markersize=2.6,
            markerfacecolor="none", markeredgecolor=C_MUTED, markeredgewidth=0.7,
            zorder=3)
    return y


def span_handles():
    return [
        (Patch(facecolor=C_SPAN_FILL, edgecolor=C_SPAN_EDGE, linewidth=0.5),
         "legislatura 367"),
        (Line2D([], [], color=C_INK, linewidth=0.7, linestyle=(0, (2.2, 1.6))),
         "estallido, 2019-10-18"),
        (Line2D([], [], color=C_SPAN_EDGE, linewidth=0.8), "congress boundary"),
        (Line2D([], [], color=C_MUTED, linewidth=0.0, marker="o", markersize=2.8,
                markerfacecolor="none", markeredgecolor=C_MUTED,
                markeredgewidth=0.7), "too thin to scale"),
    ]


def put_legend(fig, entries, *, ncol, y):
    handles = [h for h, _ in entries]
    labels = [l for _, l in entries]
    leg = fig.legend(handles, labels, loc="lower center", ncol=ncol,
                     bbox_to_anchor=(0.5, y), frameon=False, handlelength=1.5,
                     handletextpad=0.45, columnspacing=1.0, borderpad=0.0,
                     labelspacing=0.28)
    for t in leg.get_texts():
        t.set_color(C_INK)          # text wears text tokens, never the series color
    return leg


# =============================================================================
# FIGURES
# =============================================================================
Y_RATIO = (0.85, 4.6)      # shared across all three ensembles: the level IS the decision
Y_COMP = (0.045, 0.35)
Y_STEP = (-0.72, 0.72)


def fig_candidate(rows, tag, *, nullstrip: bool):
    h = 4.00 if nullstrip else 3.55
    fig = plt.figure(figsize=(COL_W_IN, h))
    if nullstrip:
        gs = fig.add_gridspec(3, 1, height_ratios=[1.32, 0.92, 0.66],
                              left=0.175, right=0.985, top=0.985, bottom=0.222,
                              hspace=0.14)
    else:
        gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 1.0],
                              left=0.175, right=0.985, top=0.985, bottom=0.248,
                              hspace=0.14)
    axes = [fig.add_subplot(g) for g in gs]

    ax = axes[0]
    chrome(ax, rows, ylabel=f"spread \u00f7 bootstrap SE\n({tag})",
           ymin=Y_RATIO[0], ymax=Y_RATIO[1])
    draw_ratio(ax, rows)
    panel_tag(ax, "(a)")
    ax.set_yticks([1, 2, 3, 4])

    ax = axes[1]
    chrome(ax, rows, ylabel="coordinate units", ymin=Y_COMP[0], ymax=Y_COMP[1],
           xlabels=not nullstrip)
    draw_components(ax, rows, label_sd="median cross-frame spread",
                    label_se="median bootstrap SE")
    panel_tag(ax, "(b)")
    ax.set_yticks([0.1, 0.2, 0.3])

    if nullstrip:
        ax = axes[2]
        chrome(ax, rows, ylabel="step change", ymin=Y_STEP[0], ymax=Y_STEP[1],
               xlabels=True)
        draw_steps(ax, rows)
        panel_tag(ax, "(c)")
        ax.set_yticks([-0.5, 0.0, 0.5])

    axes[-1].set_xlabel("legislatura", color=C_INK, labelpad=1.5)

    ent = span_handles() + [
        (Line2D([], [], color=C_SLOT1, linewidth=1.0, marker="o", markersize=2.6,
                markerfacecolor=C_SLOT1, markeredgewidth=0.0),
         "median cross-frame spread"),
        (Line2D([], [], color=C_SLOT2, linewidth=1.0, linestyle=(0, (3.0, 1.7)),
                marker="s", markersize=2.4, markerfacecolor=C_SLOT2,
                markeredgewidth=0.0), "median bootstrap SE"),
    ]
    put_legend(fig, ent, ncol=2, y=0.006)
    return fig


def fig_compare(series):
    """The decision object: the three ensembles at once."""
    fig = plt.figure(figsize=(COL_W_IN, 3.72))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 1.0],
                          left=0.165, right=0.985, top=0.985, bottom=0.288,
                          hspace=0.14)
    axes = [fig.add_subplot(g) for g in gs]
    rows_any = series["all"]

    ax = axes[0]
    chrome(ax, rows_any, ylabel="spread \u00f7 bootstrap SE",
           ymin=Y_RATIO[0], ymax=Y_RATIO[1])
    for slug, _label, m, _tag, _human in ENSEMBLES:
        st = ENS_STYLE[slug]
        draw_ratio(ax, series[slug], color=st["color"], ls=st["ls"],
                   marker=st["marker"], lw=1.0)
    panel_tag(ax, "(a)")
    ax.set_yticks([1, 2, 3, 4])

    ax = axes[1]
    chrome(ax, rows_any, ylabel="coordinate units", ymin=Y_COMP[0], ymax=Y_COMP[1],
           xlabels=True)
    for slug, _label, m, _tag, _human in ENSEMBLES:
        st = ENS_STYLE[slug]
        x = np.array([r["leg"] for r in series[slug]], float)
        sd = np.array([r[NUMER_SERIES_KEY] for r in series[slug]], float)
        ax.plot(x, sd, color=st["color"], linewidth=1.0, linestyle=st["ls"],
                marker=st["marker"], markersize=2.4, markerfacecolor=st["color"],
                markeredgewidth=0.0, zorder=3)
    se = np.array([r[DENOM_SERIES_KEY] for r in series["all"]], float) * DENOM_RESCALE
    x = np.array([r["leg"] for r in series["all"]], float)
    ax.plot(x, se, color=C_MUTED, linewidth=1.0, linestyle=(0, (1.2, 1.4)),
            marker="D", markersize=2.0, markerfacecolor=C_MUTED,
            markeredgewidth=0.0, zorder=3)
    panel_tag(ax, "(b)")
    ax.set_yticks([0.1, 0.2, 0.3])
    axes[-1].set_xlabel("legislatura", color=C_INK, labelpad=1.5)

    ent = []
    for slug, _label, m, _tag, _human in ENSEMBLES:
        st = ENS_STYLE[slug]
        ent.append((Line2D([], [], color=st["color"], linewidth=1.0,
                           linestyle=st["ls"], marker=st["marker"], markersize=2.6,
                           markerfacecolor=st["color"], markeredgewidth=0.0),
                    f"{m}-frame ensemble"))
    ent.append((Line2D([], [], color=C_MUTED, linewidth=1.0, linestyle=(0, (1.2, 1.4)),
                       marker="D", markersize=2.2, markerfacecolor=C_MUTED,
                       markeredgewidth=0.0), "bootstrap SE (shared)"))
    ent += span_handles()
    put_legend(fig, ent, ncol=2, y=0.006)
    return fig


# =============================================================================
# EMIT
# =============================================================================
def invert_png(src: Path, dst: Path) -> None:
    """Simulate a PDF reader's inversion mode: check nothing is encoded in white."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return
    im = Image.open(src).convert("RGB")
    ImageOps.invert(im).save(dst)


def emit(fig, name: str, version: str) -> dict:
    png = OUTDIR / f"{name}_{version}.png"
    pdf = OUTDIR / f"{name}.pdf"              # the path \includegraphics will use
    pdf_v = OUTDIR / f"{name}_{version}.pdf"  # versioned archive; never overwritten
    # bbox_inches=None: the emitted canvas is exactly \columnwidth, so
    # \includegraphics[width=\columnwidth] renders at scale 1.0 (FIGURE-DESIGN 7.4)
    fig.savefig(png, dpi=PNG_DPI, bbox_inches=None, pad_inches=0.01)
    fig.savefig(pdf, bbox_inches=None, pad_inches=0.01)
    fig.savefig(pdf_v, bbox_inches=None, pad_inches=0.01)
    inv = OUTDIR / f"{name}_{version}_inverted.png"
    invert_png(png, inv)
    size = [round(float(v), 3) for v in fig.get_size_inches()]
    plt.close(fig)
    return {"png": str(png), "pdf": str(pdf), "pdf_versioned": str(pdf_v),
            "inverted_preview": str(inv),
            "figsize_in": size, "figsize_pt": [round(v * 72, 1) for v in size],
            "png_dpi": PNG_DPI}


def manifest(name, version, rows, slug, human, align_info, panel_info, files,
             layout, extra):
    step = np.diff([r[RATIO_SERIES_KEY] for r in rows])
    legs = [r["leg"] for r in rows]
    doc = {
        "figure": name,
        "version": version,
        "generated_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        "generating_command": f"python {Path(__file__).name} --version {version}",
        "generator": str(Path(__file__).resolve()),
        "spec": "FIGURE-DESIGN-2026-08-11.md section 3, fig5-floor-in-time",
        "layout": layout,
        "include_width": {"columnwidth_pt": 252, "authored_in": COL_W_IN,
                          "scale_at_include": 1.0,
                          "bbox_inches": None, "pad_inches": 0.01},

        "panel": {
            "legislaturas": f"{legs[0]}-{legs[-1]}",
            "n_legislaturas": len(legs),
            "span": f"{rows[0]['start']} .. {rows[-1]['end']}",
            "rollcalls_total": panel_info["rollcalls_total"],
            "valid_votes": PANEL_VALID_VOTES,
            "source": PANEL_SOURCE,
            "data_contract": "DATA-CONTRACT-2026-08-05.md section 4 / section 8",
        },
        "lopsidedness_screen": {
            "threshold": 0.025,
            "sites": ["main_cli.cpp:471", "dwnominate.cpp:187", "dwnom2004.f:324-326"],
            "side_this_figure_is_on": SCREEN_SIDE,
            "dropped_on_this_panel": SCREEN_DROPPED,
            "note": ("This figure plots no roll-call count. Roll-call counts enter "
                     "only as the thin-legislatura screen (legs 346 and 347 at 25 and "
                     "103 roll calls) and as the panel total 12,952; both are "
                     "pre-screen input counts, not post-screen estimated counts."),
        },
        "alignment": {
            "operator": ALIGN_OPERATOR,
            "operator_description": ("uncentred, unscaled orthogonal Procrustes, ONE "
                                     "global rotation per frame over all 23 "
                                     "legislaturas stacked; target = iterated "
                                     "generalized-Procrustes consensus"),
            "not_the_centred_operator_used_by": "tab:fidelity "
                                                "(procrustes_per_congress.py:34-44)",
            "fortran_arm_used": "dwnom2004_chile_per_period (us.num line 1 "
                                "`1 25 119 119` -> legs 346-368)",
            "fortran_arm_refused": "dwnom2004_chile (us.num line 1 `1 103 120 120` "
                                   "-> legs 347-369, DATA-CONTRACT s.4 violator)",
            "other_refused": ["exp10_nofastmath_out", "b2_pablo_run"],
            "assertion": "generator exits non-zero if the roster from "
                         "_tb_series_out.txt contains any refused run or lacks "
                         "dwnom2004_chile_per_period",
            "padding": "join is on (legislatura, legislator_id) keys carrying a "
                       "bootstrap SE; n = 2,855 placements; padded roster rows "
                       "never enter",
        },
        "ensemble": {
            "slug": slug,
            "label": human,
            "m_frames": extra["m"],
            "frames": align_info["axis_balanced_frames"] if slug == "axis" else None,
            "roster_source": str(SERIES_TXT),
            "all_ensemble_m": align_info["ensemble_all_m"],
            "recommended_by": ("DESK-PLAN-2026-08-06.md 5.5 recommends AXIS-BALANCED"
                               if slug == "axis" else
                               "not the recommended series; rendered as a variant"),
        },
        "denominator": {
            "named_constant_block": "fig5-floor-in-time.py, DENOMINATOR section",
            "DENOM_BANK": DENOM_BANK,
            "DENOM_BANK_B": DENOM_BANK_B,
            "DENOM_BANK_SIGMA": DENOM_BANK_SIGMA,
            "DENOM_BANK_BASE": DENOM_BANK_BASE,
            "DENOM_SERIES_KEY": DENOM_SERIES_KEY,
            "DENOM_RESCALE": DENOM_RESCALE,
            "DENOM_MED_SE_DIM2_366_368": DENOM_MED_SE_DIM2_366_368,
            "bank_path": "reproduce/out/chile/julio_test/route2/dwnom_se.csv",
            "shape": "per-legislatura series, not a scalar",
            "pablo10_swap": ("a bootstrap of canary_fseed_i4 changes the whole SE "
                             "series, so the swap is one line here (DENOM_BANK_BASE) "
                             "PLUS one re-run of _tb_floor_series.py:98-100. "
                             "DENOM_RESCALE is the interim single-line hook."),
            "identical_across_ensembles": True,
        },
        "rows_and_columns": {
            "rows_plotted": len(rows),
            "row_key": "legislatura",
            "columns_plotted": {
                "panel_a": [RATIO_SERIES_KEY],
                "panel_b": [NUMER_SERIES_KEY, DENOM_SERIES_KEY],
                "panel_c": ["first difference of " + RATIO_SERIES_KEY]
                           if layout == "nullstrip" else None,
            },
            "legislators_per_legislatura": panel_info["legislators_per_leg"],
        },
        "values_plotted": {
            "legislatura": legs,
            RATIO_SERIES_KEY: [round(r[RATIO_SERIES_KEY], 4) for r in rows],
            NUMER_SERIES_KEY: [round(r[NUMER_SERIES_KEY], 4) for r in rows],
            DENOM_SERIES_KEY: [round(r[DENOM_SERIES_KEY] * DENOM_RESCALE, 4)
                               for r in rows],
            "rollcalls_pre_screen": [r["rc"] for r in rows],
            "congress_cohort": [r["cohort"] for r in rows],
        },
        "shock_window": {
            "legislatura": SHOCK_LEG,
            "span": f"{rows[SHOCK_LEG-346]['start']} .. {rows[SHOCK_LEG-346]['end']}",
            "event": "estallido social, 2019-10-18",
            "ratio_366_367_368": [round(r[RATIO_SERIES_KEY], 4)
                                  for r in rows if r["leg"] in (366, 367, 368)],
            "spread_pct_across_366_368": round(
                100 * (max(r[RATIO_SERIES_KEY] for r in rows if r["leg"] in (366, 367, 368))
                       - min(r[RATIO_SERIES_KEY] for r in rows if r["leg"] in (366, 367, 368)))
                / np.mean([r[RATIO_SERIES_KEY] for r in rows if r["leg"] in (366, 367, 368)]), 2),
            "step_into_shock_366_to_367": round(float(step[SHOCK_LEG - 347]), 4),
            "abs_step_rank_of_shock_step": int(
                1 + np.sum(np.abs(step) < abs(step[SHOCK_LEG - 347]))),
            "n_steps": int(step.size),
        },
        "thin_legislaturas": {
            "legs": list(THIN_LEGS),
            "rollcalls": [next(r["rc"] for r in rows if r["leg"] == l) for l in THIN_LEGS],
            "treatment": "open markers + dashed connector; DATA-CONTRACT s.6",
        },
        "sources": [
            {"path": str(p), "md5": md5(p), "role": role}
            for p, role in (
                (SERIES_JSON, "the plotted series (all three ensembles)"),
                (SERIES_TXT, "frame roster + text twin of the same run"),
                (UPSTREAM_GEN, "upstream generator that produced both artifacts"),
                (LEGMAP_OUT, "period_index -> legislatura, roll-call and roster counts"),
                (LEGMAP_IN, "legislatura -> date span"),
            ) if p.exists()
        ],
        "palette": {
            "validated_with": 'node scripts/validate_palette.js '
                              '"#2a78d6,#eb6834,#4a3aa7" --mode light '
                              '--surface "#ffffff" --pairs all',
            "result": "ALL CHECKS PASS (worst all-pairs dE 13.0 deutan, "
                      "normal-vision 16.3, all >= 3:1 on white)",
            "slots": {"slot1": C_SLOT1, "slot2": C_SLOT2, "slot3": C_SLOT3,
                      "ink": C_INK, "muted": C_MUTED, "grid": C_GRID,
                      "span_fill": C_SPAN_FILL, "span_edge": C_SPAN_EDGE},
            "alpha_used": False,
            "greyscale_safe": "every series carries line style + marker shape in "
                              "parallel with hue",
        },
        "files": files,
        "no_compute": "This generator reads banked artifacts only. No fit, no "
                      "bootstrap, no Procrustes is executed here.",
        "known_gaps": extra.get("gaps", []),
    }
    p = OUTDIR / f"{name}.manifest.json"
    p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return p


GAPS = [
    "The AXIS-BALANCED ensemble includes cpp_run_chile_p24 and "
    "cpp_run_chile_p24_canon, which are 24-period fits (743,910 votes). Their "
    "period 1 IS legislatura 346, so the period->legislatura join is correct and "
    "no offset is introduced (FIGURE-DESIGN 5.3), but their ESTIMATION panel is "
    "not the 692,839-vote panel this figure names. Fixing that needs a refit, "
    "which this run is forbidden from doing.",
    "DESK-PLAN 5.5's covariance decomposition (54 per cent numerator, 46 per cent "
    "denominator) is not recomputed here and is not drawn; panel (b) shows the two "
    "components so the reader can see the split, but the percentage itself lives "
    "in prose.",
    "The bootstrap SE series is B=50 on cpp_run_chile (route2). pablo-10 would "
    "move it to canary_fseed_i4; that re-run has not happened, so every ratio "
    "here is on the current denominator.",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    args = ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    set_rc()

    series, align_info, panel_info = load()
    print(f"alignment OK: ALL m={align_info['ensemble_all_m']}, "
          f"AXIS-BALANCED m={len(align_info['axis_balanced_frames'])}, "
          f"dwnom2004_chile refused")
    print(f"panel OK: legs 346-368, {panel_info['rollcalls_total']:,} roll calls "
          f"(pre-screen), span {PANEL_SPAN[0]}..{PANEL_SPAN[1]}")

    written = []
    for slug, _label, m, tag, human in ENSEMBLES:
        rows = series[slug]
        r366, r367, r368 = (next(r[RATIO_SERIES_KEY] for r in rows if r["leg"] == L)
                            for L in (366, 367, 368))
        step = np.diff([r[RATIO_SERIES_KEY] for r in rows])
        shock_step = step[SHOCK_LEG - 347]
        rank = 1 + int(np.sum(np.abs(step) < abs(shock_step)))
        print(f"  {slug:7s} m={m:2d}  366/367/368 = "
              f"{r366:.2f} / {r367:.2f} / {r368:.2f}"
              f"  spread {100*(max(r366,r367,r368)-min(r366,r367,r368))/np.mean([r366,r367,r368]):.1f}%"
              f"  step into 367 = {shock_step:+.3f} "
              f"(|rank| {rank}/{step.size}, 1 = smallest)"
              + ("   <- recommended" if slug == RECOMMENDED else ""))

        for layout, nullstrip in (("2panel", False), ("nullstrip", True)):
            name = f"fig5-floor-in-time_{slug}" + ("" if layout == "2panel"
                                                   else "-nullstrip")
            fig = fig_candidate(rows, tag, nullstrip=nullstrip)
            files = emit(fig, name, args.version)
            mp = manifest(name, args.version, rows, slug, human, align_info,
                          panel_info, files, layout,
                          {"m": m, "gaps": GAPS})
            written += [files["png"], files["pdf"], str(mp)]

    name = "fig5-floor-in-time_ensemble-compare"
    fig = fig_compare(series)
    files = emit(fig, name, args.version)
    mp = manifest(name, args.version, series["axis"], "compare",
                  "all three ensembles overlaid", align_info, panel_info, files,
                  "compare",
                  {"m": "42 / 11 / 2",
                   "gaps": GAPS + [
                       "values_plotted in this manifest are the AXIS-BALANCED "
                       "series; the other two are in their own manifests."]})
    written += [files["png"], files["pdf"], str(mp)]

    print("\nwrote:")
    for w in written:
        print("  " + w)


if __name__ == "__main__":
    main()
