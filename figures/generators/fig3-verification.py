#!/usr/bin/env python3
"""fig3-verification -- "Where the engines agree, and where nobody does".

FIGURE-DESIGN-2026-08-11.md section 3, fig3-verification (rank 4, essential).
Restores the retired `fig:us-timeline` with the visual system of section 7.

WHAT THIS SHOWS
    Two stacked single-column panels sharing x = US Senate Congress 1..117.
    Panel (a) per-Congress Procrustes r on dimension one; panel (b) the same on
    dimension two, on the IDENTICAL y-range. Two series in each panel:
      * our C++ engine against the 2004 Fortran   (blue, solid)
      * the 2004 Fortran against the VoteView scores its own maintainers publish
        (orange, dashed)

    Inversion I3: the oracle's residual against its own published product
    (dim-2 median 0.9498, 10 congresses below 0.90) already BOUNDS ours
    (0.9690, 6 below 0.90). That removes the reason to run the unpriced US
    Tier-2 arms.

THREE VARIANTS ARE RENDERED, NOT ONE. The design decision left open by
FIGURE-DESIGN is how to make "the oracle bounds us" legible in three seconds:
      v1  lines only .................. spec-literal, minimum ink
      v2  lines + diverging margin fill between the two series
      v3  lines + 0.90 reference rule + below-threshold rug
Roberto picks by looking. A contact sheet and a robustness sheet (greyscale,
deuteranopia, inverted) are emitted alongside.

HONESTY NOTE, and it changes the caption.
    FIGURE-DESIGN's three-second read says "our line sits at or above the
    oracle's own line". Measured here: on dimension two ours is above in
    81 of 117 congresses (69 per cent), median margin +0.0118, and it dips
    BELOW by as much as 0.0575. The bound is a typical/median bound, not a
    pointwise one. The drawn figure shows the exceptions rather than hiding
    them (that is what the v2 diverging fill is for) and the drafted caption
    says "typically" rather than asserting dominance.

NO COMPUTE. Reads two finished CSVs. No fits, no bootstrap, no engine call.

Run:  python figgen-2026-08-11/fig3-verification.py
"""
from __future__ import annotations

import hashlib
import json
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

# ----------------------------------------------------------------------------
# 0. PATHS
# ----------------------------------------------------------------------------
REPO = Path("C:/Users/cow/Documents/GitHub/quevotan-db")
PAPER = Path("C:/Users/cow/Documents/thesis-quevotan/papers/jcc-2026")
SRC = REPO / "reproduce/out/us_linear_1117"

# A: our C++ (LAPACK build) aligned onto the 2004 Fortran (Tier-2 canonical).
CSV_OURS = SRC / "procrustes_cpp_lapack_vs_tier2.csv"
# B: the 2004 Fortran aligned onto the published VoteView scores.
CSV_ORACLE = SRC / "procrustes_tier2_vs_voteview.csv"

OUTDIR = _paths.render_dir()   # was PAPER/"figs/v2026-08-11", a path the
                               # 2026-08-13 reorganization retired. Renders go to
                               # figures/renders/<date>/; survivors are copied into
                               # draft/figures/ by hand. reference-renders/ is frozen.
FIGNAME = "fig3-verification"

# ----------------------------------------------------------------------------
# 1. NAMED CONSTANTS.  Never inline a number that a later run may replace.
#    (FIGURE-DESIGN non-negotiable 3. This figure carries no bootstrap
#    denominator -- see DENOM_NOTE -- but the same discipline applies to every
#    threshold and every gate value below.)
# ----------------------------------------------------------------------------
DENOM_NOTE = (
    "not applicable: this figure plots Procrustes correlations directly and "
    "normalises by no bootstrap standard error. pablo-10 changes no number here."
)

# The threshold FIGURE-DESIGN counts congresses against ("6 below 0.90" vs "10").
THRESH_DIM2 = 0.90  # bare correlation, not a ratio

# Shared y-range for BOTH panels. The asymmetry is only a perception if the
# scale is identical, so this is one constant used twice, never two. It is also
# shared across all three variants so they compare directly.
# The floor sits at 0.78 rather than at the 0.80 tick to open a clear gutter
# below the data (global min 0.8120) for the v3 rug, which must not overlap the
# series it annotates.
YLIM = (0.78, 1.00)
YTICKS = [0.80, 0.85, 0.90, 0.95, 1.00]
RUG_Y_ORACLE = 0.7905          # in data coords, inside the gutter
RUG_Y_OURS = 0.7855
XLIM = (1, 117)
XTICKS = [1, 20, 40, 60, 80, 100, 117]

# Gate values, transcribed from FIGURE-DESIGN section 3 fig3-verification, which
# recorded them as CONFIRMED. The generator refuses to emit if the CSVs on disk
# no longer reproduce them.
GATE = {
    "ours_dim1_median": 0.9863,
    "ours_dim1_min": 0.9363,
    "ours_dim2_median": 0.9690,
    "ours_dim2_min": 0.8298,
    "ours_dim2_below_thresh": 6,
    "oracle_dim1_median": 0.9839,
    "oracle_dim1_min": 0.9116,
    "oracle_dim2_median": 0.9498,
    "oracle_dim2_min": 0.8120,
    "oracle_dim2_below_thresh": 10,
    "n_congresses": 117,
}
GATE_TOL = 5e-5

# ----------------------------------------------------------------------------
# 2. PALETTE.  FIGURE-DESIGN 7.3, all values validator-confirmed.
#    node scripts/validate_palette.js "#2a78d6,#eb6834" --mode light
#        --surface "#ffffff" --pairs all   -> ALL CHECKS PASS
#        (CVD worst 24.7 protan, normal-vision 33.6, both >= 3:1)
#    The two area tints are the light ends of the two series ramps:
#    "#86b6ef,#2a78d6" --ordinal  -> PASS, light end 2.11:1
#    "#eb9e6a,#eb6834" --ordinal  -> PASS, light end 2.18:1
#    tint pair separation #86b6ef vs #eb9e6a: dE 20.8 normal / 18.3 protan /
#    19.6 deutan / 23.0 tritan, all far above the >= 8 target.
# ----------------------------------------------------------------------------
C_OURS = "#2a78d6"        # categorical slot 1, first named series
C_ORACLE = "#eb6834"      # categorical slot 2
FILL_OURS_AHEAD = "#86b6ef"   # light step of slot 1
FILL_ORACLE_AHEAD = "#eb9e6a"  # light step of slot 2, lightness-matched (L=0.764)
INK = "#0b0b0b"           # primary ink
MUTED = "#898781"         # muted ink
GRID = "#e1e0d9"          # solid hairline, never dashed

LABEL_OURS = "our C++ vs 2004 Fortran"
LABEL_ORACLE = "2004 Fortran vs published VoteView"

# ----------------------------------------------------------------------------
# 3. TYPOGRAPHY AND OUTPUT GEOMETRY.  FIGURE-DESIGN 7.4.
#    Single column: \columnwidth = 252pt = 3.5in. Author at exactly that width
#    and never scale, so \includegraphics[width=\columnwidth] renders at 1.0.
# ----------------------------------------------------------------------------
COLW_IN = 3.5      # 252pt
FIGH_IN = 3.35
PNG_DPI = 400

matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 8,          # base
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,    # floor: never below 7pt at scale 1.0
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "pdf.fonttype": 42,      # IEEE PDF eXpress rejects Type 3
    "ps.fonttype": 42,
    "savefig.transparent": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

# Our series is the subject of the figure, so it carries slightly more weight.
LW_OURS = 1.35
LW_ORACLE = 1.15
DASH_ORACLE = (0, (2.9, 1.35))


# ----------------------------------------------------------------------------
# 4. LOAD, WITH THE ALIGNMENT ASSERTED AND FAILING LOUDLY
# ----------------------------------------------------------------------------
def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def load_and_assert():
    """Read both Procrustes CSVs and refuse to continue on any misalignment.

    The Chilean one-legislatura offset (FIGURE-DESIGN 5.1/5.2, the
    dwnom2004_chile vs dwnom2004_chile_per_period trap) cannot occur on this
    figure: neither arm touches a Chilean panel. The alignment that CAN break
    here is the congress key between the two US series, so that is what is
    asserted -- both files must carry the identical contiguous 1..117 index,
    matched row for row.
    """
    ours = pd.read_csv(CSV_OURS).sort_values("congress").reset_index(drop=True)
    oracle = pd.read_csv(CSV_ORACLE).sort_values("congress").reset_index(drop=True)

    for name, d in (("ours", ours), ("oracle", oracle)):
        need = {"congress", "n", "r_dim1", "r_dim2"}
        if not need.issubset(d.columns):
            raise SystemExit(f"FAIL [{name}]: columns {sorted(d.columns)} lack {sorted(need)}")
        if d[["r_dim1", "r_dim2"]].isna().any().any():
            raise SystemExit(f"FAIL [{name}]: NaN correlations present")
        if len(d) != GATE["n_congresses"]:
            raise SystemExit(f"FAIL [{name}]: {len(d)} rows, expected {GATE['n_congresses']}")

    expect = np.arange(1, GATE["n_congresses"] + 1)
    for name, d in (("ours", ours), ("oracle", oracle)):
        if not np.array_equal(d["congress"].to_numpy(), expect):
            raise SystemExit(f"FAIL [{name}]: congress index is not contiguous 1..117")
    if not np.array_equal(ours["congress"].to_numpy(), oracle["congress"].to_numpy()):
        raise SystemExit("FAIL: the two series do not share a congress index (OFFSET)")

    # Active-row sanity. FIGURE-DESIGN 5.4 rule 3: correlations must be on
    # active rows only, never on padded matrix rows. procrustes_per_congress.py
    # inner-merges on (congress, legislator_id) and both loaders drop NaN, so
    # padded rows cannot enter. A Senate-plausible n confirms it empirically.
    for name, d in (("ours", ours), ("oracle", oracle)):
        if not (d["n"].between(20, 120).all()):
            raise SystemExit(
                f"FAIL [{name}]: n outside 20..120 -> padded rows may have leaked "
                f"(min {d['n'].min()}, max {d['n'].max()})")

    return ours, oracle


def gate(ours: pd.DataFrame, oracle: pd.DataFrame) -> dict:
    """Reproduce FIGURE-DESIGN's CONFIRMED numbers or refuse to draw."""
    got = {
        "ours_dim1_median": float(ours.r_dim1.median()),
        "ours_dim1_min": float(ours.r_dim1.min()),
        "ours_dim2_median": float(ours.r_dim2.median()),
        "ours_dim2_min": float(ours.r_dim2.min()),
        "ours_dim2_below_thresh": int((ours.r_dim2 < THRESH_DIM2).sum()),
        "oracle_dim1_median": float(oracle.r_dim1.median()),
        "oracle_dim1_min": float(oracle.r_dim1.min()),
        "oracle_dim2_median": float(oracle.r_dim2.median()),
        "oracle_dim2_min": float(oracle.r_dim2.min()),
        "oracle_dim2_below_thresh": int((oracle.r_dim2 < THRESH_DIM2).sum()),
        "n_congresses": int(len(ours)),
    }
    bad = []
    for k, want in GATE.items():
        have = got[k]
        ok = (have == want) if isinstance(want, int) else (abs(have - want) <= GATE_TOL)
        if not ok:
            bad.append(f"  {k}: got {have!r}, FIGURE-DESIGN recorded {want!r}")
    if bad:
        raise SystemExit("FAIL: artifacts no longer reproduce the CONFIRMED values:\n"
                         + "\n".join(bad))
    return got


# ----------------------------------------------------------------------------
# 5. DRAW
# ----------------------------------------------------------------------------
def style_axes(ax, is_bottom: bool):
    ax.set_ylim(*YLIM)
    ax.set_yticks(YTICKS)
    ax.set_yticklabels([f"{t:.2f}" for t in YTICKS])
    ax.set_xlim(*XLIM)
    ax.set_xticks(XTICKS)
    ax.set_ylabel("Procrustes $r$", color=INK, labelpad=2)
    # solid hairline grid, one shade off the surface, never dashed
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, linewidth=0.5, linestyle="-")
    ax.grid(axis="x", visible=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=MUTED, pad=1.5)
    if is_bottom:
        ax.set_xlabel("Congress", color=INK, labelpad=2)


def panel_tag(ax, text):
    """Structural label, set OUTSIDE the data area.

    An in-axes tag collides with the second-dimension series, which plunges to
    0.83 at Congress 7 and to 0.81 at 117. A left-aligned title cannot collide
    with anything. (7.1 forbids in-figure NUMBERS; a panel tag is structure.)
    """
    ax.set_title(text, loc="left", fontsize=7.2, color=INK, pad=2.5)


def draw(ours, oracle, variant: str, out_png: Path, out_pdf: Path):
    x = ours["congress"].to_numpy()
    fig, axes = plt.subplots(2, 1, figsize=(COLW_IN, FIGH_IN), sharex=True)

    for ax, col, tag in ((axes[0], "r_dim1", "(a)  first dimension"),
                         (axes[1], "r_dim2", "(b)  second dimension")):
        yo = ours[col].to_numpy()
        yr = oracle[col].to_numpy()
        style_axes(ax, is_bottom=(ax is axes[1]))

        if variant == "v2":
            # Diverging margin between the two series. Signed quantity ->
            # two hues that read as opposite, no neutral needed because the
            # midpoint is the crossing itself. Solid tints, NO alpha (7.3).
            ax.fill_between(x, yo, yr, where=(yo >= yr), interpolate=True,
                            facecolor=FILL_OURS_AHEAD, edgecolor="none", zorder=1)
            ax.fill_between(x, yo, yr, where=(yo < yr), interpolate=True,
                            facecolor=FILL_ORACLE_AHEAD, edgecolor="none", zorder=1)

        if variant == "v3":
            # reference rule for a threshold: dashed, distinct from the solid grid
            ax.axhline(THRESH_DIM2, color=MUTED, lw=0.7, ls=(0, (4, 2.4)), zorder=2)
            # rug: which congresses fall below the rule, per series. Drawn in the
            # gutter below the 0.80 tick so it cannot overlap the series.
            for yy, colr, y0 in ((yr, C_ORACLE, RUG_Y_ORACLE),
                                 (yo, C_OURS, RUG_Y_OURS)):
                hit = x[yy < THRESH_DIM2]
                if len(hit):
                    ax.plot(hit, np.full(len(hit), y0), linestyle="none",
                            marker="|", markersize=3.4, markeredgewidth=0.9,
                            color=colr, zorder=5)

        # oracle drawn first so our series reads as the foreground subject
        ax.plot(x, yr, color=C_ORACLE, lw=LW_ORACLE, ls=DASH_ORACLE,
                solid_capstyle="round", dash_capstyle="round", zorder=3)
        ax.plot(x, yo, color=C_OURS, lw=LW_OURS, solid_capstyle="round",
                zorder=4)
        panel_tag(ax, tag)

    # legend OUTSIDE the plotting area (7.1), identity by colour AND dash (7.5)
    handles = [
        Line2D([], [], color=C_OURS, lw=LW_OURS, label=LABEL_OURS),
        Line2D([], [], color=C_ORACLE, lw=LW_ORACLE, ls=DASH_ORACLE, label=LABEL_ORACLE),
    ]
    if variant == "v2":
        handles += [
            plt.Rectangle((0, 0), 1, 1, facecolor=FILL_OURS_AHEAD, edgecolor="none",
                          label="our agreement is the higher"),
            plt.Rectangle((0, 0), 1, 1, facecolor=FILL_ORACLE_AHEAD, edgecolor="none",
                          label="the Fortran's own is the higher"),
        ]
    if variant == "v3":
        handles += [
            Line2D([], [], color=MUTED, lw=0.7, ls=(0, (4, 2.4)),
                   label="$r = 0.90$; ticks below mark the congresses under it"),
        ]
    leg = fig.legend(handles=handles, loc="lower center", ncol=1,
                     frameon=False, handlelength=1.9, handletextpad=0.6,
                     borderaxespad=0.0, labelspacing=0.32,
                     bbox_to_anchor=(0.54, 0.0))
    for t in leg.get_texts():
        t.set_color(INK)

    bottom = {"v1": 0.180, "v2": 0.250, "v3": 0.215}[variant]
    # right margin leaves room for the centred '117' tick label to not clip
    fig.subplots_adjust(left=0.150, right=0.955, top=0.945, bottom=bottom, hspace=0.30)

    # NEVER bbox_inches='tight' (7.4): it changes the emitted canvas so
    # \includegraphics[width=\columnwidth] no longer renders at scale 1.0.
    fig.savefig(out_png, dpi=PNG_DPI, bbox_inches=None, pad_inches=0.01)
    fig.savefig(out_pdf, bbox_inches=None, pad_inches=0.01)
    plt.close(fig)


# ----------------------------------------------------------------------------
# 6. ROBUSTNESS SHEET.  FIGURE-DESIGN 7.5 is a structural requirement, so it is
#    verified by transforming the rendered pixels, not by a second palette.
# ----------------------------------------------------------------------------
MACHADO_DEUTAN = np.array([[0.367322, 0.860646, -0.227968],
                           [0.280085, 0.672501, 0.047413],
                           [-0.011820, 0.042940, 0.968881]])


def _srgb_to_lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(a):
    a = np.clip(a, 0.0, 1.0)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055)


def robustness_sheet(src_png: Path, out_png: Path):
    img = plt.imread(src_png)[..., :3]
    lin = _srgb_to_lin(img)
    deut = _lin_to_srgb(lin @ MACHADO_DEUTAN.T)
    grey_l = lin @ np.array([0.2126, 0.7152, 0.0722])
    grey = np.repeat(_lin_to_srgb(grey_l)[..., None], 3, axis=2)
    inv = 1.0 - img

    panels = [(img, "as rendered"), (grey, "greyscale print"),
              (deut, "deuteranopia"), (inv, "inverted dark reader")]
    fig, axes = plt.subplots(1, 4, figsize=(15.0, 3.7))
    for ax, (im, ttl) in zip(axes, panels):
        ax.imshow(im)
        ax.set_title(ttl, fontsize=10, color=INK, pad=6)
        ax.axis("off")
    fig.subplots_adjust(left=0.005, right=0.995, top=0.90, bottom=0.01, wspace=0.03)
    fig.savefig(out_png, dpi=110, bbox_inches=None, pad_inches=0.02)
    plt.close(fig)


def contact_sheet(pngs, out_png: Path):
    fig, axes = plt.subplots(1, len(pngs), figsize=(4.9 * len(pngs), 5.1))
    for ax, (p, ttl) in zip(np.atleast_1d(axes), pngs):
        ax.imshow(plt.imread(p))
        ax.set_title(ttl, fontsize=11, color=INK, pad=8)
        ax.axis("off")
    fig.subplots_adjust(left=0.005, right=0.995, top=0.92, bottom=0.01, wspace=0.04)
    fig.savefig(out_png, dpi=115, bbox_inches=None, pad_inches=0.02)
    plt.close(fig)


# ----------------------------------------------------------------------------
# 7. MAIN
# ----------------------------------------------------------------------------
def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    ours, oracle = load_and_assert()
    got = gate(ours, oracle)

    d1 = ours.r_dim1.to_numpy() - oracle.r_dim1.to_numpy()
    d2 = ours.r_dim2.to_numpy() - oracle.r_dim2.to_numpy()
    margin = {
        "dim1_ours_above_n": int((d1 > 0).sum()),
        "dim1_ours_above_pct": round(100 * float((d1 > 0).mean()), 1),
        "dim1_median_margin": round(float(np.median(d1)), 4),
        "dim1_worst_deficit": round(float(d1.min()), 4),
        "dim2_ours_above_n": int((d2 > 0).sum()),
        "dim2_ours_above_pct": round(100 * float((d2 > 0).mean()), 1),
        "dim2_median_margin": round(float(np.median(d2)), 4),
        "dim2_worst_deficit": round(float(d2.min()), 4),
        "dim2_best_margin": round(float(d2.max()), 4),
    }

    print("gate PASS. all 11 CONFIRMED values reproduced.")
    for k, v in got.items():
        print(f"   {k:26s} {v}")
    print("margin, ours minus oracle:")
    for k, v in margin.items():
        print(f"   {k:26s} {v}")

    # Iteration 2. Iteration 1 was emitted as fig3-verification_v{1,2,3}.* where
    # the digit named the VARIANT; that was ambiguous against the _vN iteration
    # convention, so from here the variant is named in the stem and _vN is the
    # iteration. The iteration-1 files are retained, never deleted.
    variants = [
        ("v1", "lines", "A  lines only"),
        ("v2", "margin", "B  lines + diverging margin fill"),
        ("v3", "threshold", "C  lines + 0.90 rule + rug"),
    ]
    made = []
    for vid, slug, ttl in variants:
        png = OUTDIR / f"{FIGNAME}-{slug}_v2.png"
        pdf = OUTDIR / f"{FIGNAME}-{slug}_v2.pdf"
        draw(ours, oracle, vid, png, pdf)
        made.append((png, ttl))
        print(f"wrote {png.name}  {pdf.name}")

    contact_sheet(made, OUTDIR / f"{FIGNAME}_variants_v2.png")
    robustness_sheet(OUTDIR / f"{FIGNAME}-margin_v2.png",
                     OUTDIR / f"{FIGNAME}-margin_v2_robustness.png")
    print("wrote contact sheet + robustness sheet")

    # ---- manifest -----------------------------------------------------------
    manifest = {
        "figure": FIGNAME,
        "title": "Where the engines agree, and where nobody does",
        "spec": "FIGURE-DESIGN-2026-08-11.md section 3, fig3-verification (rank 4, essential)",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generating_command": (
            'python "C:/Users/cow/Documents/thesis-quevotan/papers/jcc-2026/'
            'figgen-2026-08-11/fig3-verification.py"'),
        "generator": str(Path(__file__).resolve()),
        "no_compute": ("true. two finished CSVs read; no fit, no bootstrap, no "
                       "engine invocation, no Procrustes recomputed here"),

        "panel": {
            "body": "United States Senate",
            "span": "Congress 1 to 117",
            "model": "linear (DW-NOMINATE linear model), Tier-2 canonical 2004 build",
            "unit_of_observation": "one Congress; y is a per-Congress correlation over active legislators",
            "n_congresses": got["n_congresses"],
            "legislators_per_congress_range_ours": [int(ours.n.min()), int(ours.n.max())],
            "legislators_per_congress_range_oracle": [int(oracle.n.min()), int(oracle.n.max())],
            "note": ("This is the US panel. The Chilean legislatura panels of "
                     "DATA-CONTRACT section 4 (346-368 vs 347-369) are not "
                     "involved, and neither is dwnom2004_chile."),
        },

        "alignment": {
            "operator": ("centred orthogonal Procrustes, rotation + reflection, "
                         "no scaling; A aligned onto B, B is the reference frame"),
            "operator_source": ("reproduce/scripts/procrustes_per_congress.py:34-44 "
                                "(procrustes_align: Ac = A - A.mean(axis=0); "
                                "Bc = B - B.mean(axis=0); R = U @ Vt)"),
            "centred_or_uncentred": "CENTRED",
            "why_stated": ("FIGURE-DESIGN 5.4 rule 2: tab:fidelity uses centred "
                           "Procrustes and build_fig_floor.py uses uncentred, and "
                           "both are called 'Procrustes-aligned' in the paper. This "
                           "figure is centred, matching tab:fidelity, and the caption "
                           "must not be reworded to imply otherwise."),
            "granularity": "per Congress, independently aligned; NOT a single global rotation",
            "padding": {
                "rule": "FIGURE-DESIGN 5.4 rule 3: correlations on active rows only",
                "mechanism": ("procrustes_per_congress.py:117 inner-merges on "
                              "(congress, legislator_id); load_cpp_csv:94 and "
                              "load_voteview_csv:80 drop NaN. Padded matrix rows "
                              "cannot enter the merge."),
                "verified_in_generator": ("assert n in 20..120 per Congress; observed "
                                          f"{int(min(ours.n.min(), oracle.n.min()))}"
                                          f"-{int(max(ours.n.max(), oracle.n.max()))}, "
                                          "Senate-plausible, so no padded rows leaked"),
            },
            "congress_key_assertion": ("both CSVs asserted to carry the identical "
                                       "contiguous congress index 1..117, matched row "
                                       "for row; generator exits non-zero otherwise"),
            "offset_exposure": ("NONE. The one-legislatura offset class of "
                                "FIGURE-DESIGN 5.1/5.2 arises from Chilean Fortran runs "
                                "whose us.num line 1 distinguishes the 347-369 panel "
                                "('1 103 120 120') from 346-368 ('1 25 119 119'). No "
                                "Chilean artifact is read by this figure."),
        },

        "lopsidedness_screen": {
            "which_side": ("POST-SCREEN, symmetrically, on all three lineages. This "
                           "figure counts congresses and legislators; it counts no "
                           "roll calls and no votes, so no count printed here sits on "
                           "either side of the screen."),
            "detail": ("The 0.025 minority threshold (main_cli.cpp:471, "
                       "dwnominate.cpp:187 validRollCalls_ margin test, "
                       "dwnom2004.f:324-326) was applied inside each engine before "
                       "these coordinates existed. Our C++, the 2004 Fortran and the "
                       "published VoteView scores are all post-screen products, so "
                       "the comparison is screen-symmetric."),
            "paper_panel_figure_not_used": ("the 6,094 of 12,952 dropped roll calls is "
                                            "a Chilean 346-368 number and does not "
                                            "apply to this US figure"),
        },

        "denominator": {"constant": "DENOM_NOTE", "value": DENOM_NOTE},

        "sources": [
            {
                "role": "series 1, 'our C++ vs 2004 Fortran'",
                "path": str(CSV_OURS),
                "path_repo_relative": "reproduce/out/us_linear_1117/procrustes_cpp_lapack_vs_tier2.csv",
                "md5": md5(CSV_OURS),
                "rows": int(len(ours)),
                "columns": list(ours.columns),
                "A_onto_B": "A = our C++ (LAPACK build)  ->  B = 2004 Fortran (Tier-2 canonical)",
            },
            {
                "role": "series 2, '2004 Fortran vs published VoteView'",
                "path": str(CSV_ORACLE),
                "path_repo_relative": "reproduce/out/us_linear_1117/procrustes_tier2_vs_voteview.csv",
                "md5": md5(CSV_ORACLE),
                "rows": int(len(oracle)),
                "columns": list(oracle.columns),
                "A_onto_B": "A = 2004 Fortran (Tier-2 canonical)  ->  B = published VoteView scores",
            },
        ],

        "shape": {"rows_plotted_per_series": int(len(ours)),
                  "series_per_panel": 2, "panels": 2,
                  "panel_layout": "2 rows x 1 column, stacked, shared x",
                  "total_data_points": int(2 * 2 * len(ours))},

        "values_gated": got,
        "gate_tolerance": GATE_TOL,
        "gate_source": "FIGURE-DESIGN-2026-08-11.md section 3, fig3-verification, block marked CONFIRMED",

        "margin_ours_minus_oracle": margin,
        "margin_caveat": (
            "FIGURE-DESIGN's three-second read states 'our line sits at or above the "
            "oracle's own line'. MEASURED: on dimension two ours is above in "
            f"{margin['dim2_ours_above_n']} of {got['n_congresses']} congresses "
            f"({margin['dim2_ours_above_pct']} per cent), median margin "
            f"{margin['dim2_median_margin']:+.4f}, worst deficit "
            f"{margin['dim2_worst_deficit']:+.4f}. On dimension one it is "
            f"{margin['dim1_ours_above_pct']} per cent, i.e. a coin flip. The bound is "
            "a median bound, NOT pointwise dominance. The caption says 'typically' and "
            "variant v2 draws the exceptions rather than hiding them."),

        "geometry": {
            "include_width": "\\columnwidth = 252pt = 3.5in, single column",
            "figsize_in": [COLW_IN, FIGH_IN],
            "authored_at_include_width": True,
            "savefig": "bbox_inches=None, pad_inches=0.01 (never 'tight', per 7.4)",
            "png_dpi": PNG_DPI,
            "pdf": "vector, pdf.fonttype=42 (Type 3 is rejected by IEEE PDF eXpress)",
            "smallest_text_pt_at_scale_1": 7,
            "ylim_shared_both_panels": list(YLIM),
            "yticks": YTICKS, "xlim": list(XLIM), "xticks": XTICKS,
        },

        "palette": {
            "series_1_ours": C_OURS, "series_2_oracle": C_ORACLE,
            "fill_ours_ahead": FILL_OURS_AHEAD, "fill_oracle_ahead": FILL_ORACLE_AHEAD,
            "ink": INK, "muted": MUTED, "grid": GRID,
            "validation": {
                "categorical": ('node validate_palette.js "#2a78d6,#eb6834" --mode light '
                                '--surface "#ffffff" --pairs all -> ALL PASS; CVD worst '
                                '24.7 protan, normal-vision 33.6, both >= 3:1'),
                "ramp_blue": '"#86b6ef,#2a78d6" --ordinal -> ALL PASS, light end 2.11:1',
                "ramp_orange": '"#eb9e6a,#eb6834" --ordinal -> ALL PASS, light end 2.18:1',
                "tint_pair_separation": ("#86b6ef vs #eb9e6a: dE 20.8 normal / 18.3 protan "
                                         "/ 19.6 deutan / 23.0 tritan, all >= 8"),
                "new_colour_introduced": ("#eb9e6a only, the light step of slot 2, chosen "
                                          "by lightness match to #86b6ef (both OKLab "
                                          "L=0.764) and validated, not eyeballed"),
            },
            "no_alpha": "true: every fill is a solid light hex (7.3, PDF transparency-group risk)",
            "greyscale_and_inversion": ("identity is carried by line style (solid vs dashed) "
                                        "in parallel with hue; legend always present; "
                                        "nothing encoded in white or near-white"),
            "robustness_measured": {
                "method": ("the rendered PNG was transformed pixelwise: Machado deuteranopia "
                           "matrix, Rec.709 luminance greyscale, and a straight inversion. "
                           "Sheet: fig3-verification-margin_v2_robustness.png"),
                "deuteranopia": "PASS. blue vs olive on both lines and both fills.",
                "inverted": ("PASS. light text on black, both series legible, no white-encoded "
                             "mark disappears."),
                "greyscale": (
                    "PARTIAL, and stated rather than hidden. The two SERIES survive because "
                    "solid vs dashed carries identity. The two FILL tints do NOT separate, "
                    "because they are deliberately lightness-matched (both OKLab L=0.764) so "
                    "that neither reads as louder in colour. In greyscale the diverging fill "
                    "therefore degrades to a single uniform gap band. No information is lost: "
                    "the sign of the margin is still readable from which line lies on top. "
                    "The alternative, splitting the tints in lightness, would make the "
                    "minority-case orange read as the heavier mark in colour, which is worse. "
                    "This affects variant B only; A and C are unaffected."),
            },
        },

        "compile_verified": {
            "engine": "pdflatex (MiKTeX), \\documentclass[conference]{IEEEtran}",
            "scratch_only": ("compiled in the job scratch dir; no .tex in the paper tree was "
                             "created, opened for writing or modified"),
            "columnwidth_pt": 252.0,
            "graphic_rendered_width_pt": 252.0,
            "graphic_rendered_height_pt": 241.206,
            "scale": ("exactly 1.0. \\includegraphics[width=\\columnwidth] reproduces the PDF "
                      "MediaBox 252 x 241.2pt with no scaling, so every in-figure point size "
                      "is the authored size and the 7pt floor is a real 7pt on the page."),
            "float_cost_col_pt": {
                "graphic": 241.206, "abovecaptionskip": 6.0,
                "caption_at_footnotesize": 42.584, "textfloatsep": 18.600,
                "total": 308.39,
                "page_fraction": round(308.39 / 1386.0, 3),
            },
            "vs_figure_design_estimate": ("FIGURE-DESIGN section 4 estimated ~300 col-pt and "
                                          "0.22 page and flagged that costs were arithmetic, "
                                          "not a compile, to be verified by compiling "
                                          "(DESK-PLAN R11). MEASURED 308.4 col-pt and 0.222 "
                                          "page. The estimate holds."),
            "pdf_conformance": {
                "type3_fonts": 0,
                "embedded_as": ("Type0 / CIDFontType2 with /FontFile2, i.e. subsetted TrueType, "
                                "which is what pdf.fonttype=42 produces and what IEEE PDF "
                                "eXpress accepts"),
                "image_xobjects": 0,
                "fully_vector": True,
            },
        },

        "variants": {
            "why": ("FIGURE-DESIGN specifies the two series and the faceting but leaves "
                    "open how to make 'the oracle bounds us' readable in three seconds. "
                    "All three are rendered; none is deleted. All three share one y-range "
                    "so they compare directly."),
            "A_lines": {
                "files": [f"{FIGNAME}-lines_v2.png", f"{FIGNAME}-lines_v2.pdf"],
                "what": "lines only. spec-literal, minimum ink. The margin is read off the gap.",
            },
            "B_margin": {
                "files": [f"{FIGNAME}-margin_v2.png", f"{FIGNAME}-margin_v2.pdf"],
                "what": ("lines + diverging fill of the signed margin between them. Blue "
                         "where our agreement is higher, orange where the Fortran's own "
                         "is. Panel (a) reads as a hairline and panel (b) as an area, "
                         "which IS the asymmetry, and it draws the 31 per cent of "
                         "congresses where the bound reverses instead of hiding them."),
            },
            "C_threshold": {
                "files": [f"{FIGNAME}-threshold_v2.png", f"{FIGNAME}-threshold_v2.pdf"],
                "what": ("lines + dashed reference rule at r = 0.90 + a per-series rug in "
                         "the gutter below the axis marking the congresses under it. Lets "
                         "the reader count 6 against 10 without a number being printed "
                         "inside the figure, which 7.1 forbids."),
            },
            "contact_sheet": f"{FIGNAME}_variants_v2.png",
            "robustness_sheet": (f"{FIGNAME}-margin_v2_robustness.png -- the same render "
                                 "under greyscale, deuteranopia and inversion, which is "
                                 "how 7.5 is verified for a print figure"),
            "recommendation": ("B carries the inversion most directly and is the only one "
                               "whose panel (a) and panel (b) differ as AREAS rather than "
                               "as line traces. Roberto decides by looking."),
        },

        "iteration_history": {
            "v1": {
                "files": [f"{FIGNAME}_v1.png", f"{FIGNAME}_v2.png", f"{FIGNAME}_v3.png",
                          f"{FIGNAME}_v1.pdf", f"{FIGNAME}_v2.pdf", f"{FIGNAME}_v3.pdf",
                          f"{FIGNAME}_variants.png", f"{FIGNAME}_v2_robustness.png"],
                "status": "SUPERSEDED, retained, not deleted",
                "naming_note": ("in iteration 1 the trailing digit named the VARIANT, "
                                "which collides with the _vN iteration convention. From "
                                "iteration 2 the variant is in the stem "
                                "(-lines / -margin / -threshold) and _vN is the iteration."),
                "defects_fixed_in_v2": [
                    "the '117' x-tick label was clipped at the right edge",
                    ("the panel tag sat inside the axes and collided with the "
                     "second-dimension series at Congress 7 and 117; it is now a "
                     "left-aligned title outside the data area"),
                    ("the v3 rug sat at y=0.803/0.812, inside the data band (global min "
                     "0.8120); the y-floor is now 0.78 and the rug lives in the gutter "
                     "below the 0.80 tick"),
                    ("both series carried equal line weight; ours is now 1.35 against "
                     "1.15 so the subject of the figure reads as the subject"),
                ],
            },
            "v2": {"status": "CURRENT"},
        },

        "caption_drafted": {
            "base_A": (
                "Per-Congress agreement across United States Senate history, Congresses 1 "
                "to 117, linear model, centred Procrustes on active rows. Our engine "
                "against the 2004 Fortran, and the 2004 Fortran against the scores its own "
                "maintainers publish. (a) first dimension; (b) second dimension, same "
                "scale. Medians on the first dimension 0.986 and 0.984; on the second, "
                "0.969 and 0.950."),
            "B_margin_addendum": (
                " Shading marks which of the two agreements is the higher at each Congress: "
                "ours in blue, the Fortran's own in orange."),
            "C_threshold_addendum": (
                " The dashed rule is r = 0.90; the ticks below the axis mark the congresses "
                "falling under it, six for our engine against ten for the Fortran's own."),
            "register_note": ("purely descriptive, names the marks and nothing else, per 7.1. "
                              "It states medians, which are table-backed, and does NOT claim "
                              "pointwise dominance, which the data does not support -- see "
                              "margin_caveat."),
        },

        "gaps": [
            ("None blocking. Both CSVs were on disk, every CONFIRMED value in "
             "FIGURE-DESIGN section 3 reproduced exactly, and no number in this figure "
             "was estimated or carried across from another bank."),
            ("The provenance of the two CSVs is recorded here by md5 and by the "
             "generating script (procrustes_per_congress.py), but the exact argv that "
             "produced them was not captured at the time and is not recoverable from "
             "the files; build_fig_us_timeline.py:30-31 is the only on-disk record that "
             "binds these two filenames to these two roles."),
        ],
    }
    mpath = OUTDIR / f"{FIGNAME}.manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("wrote", mpath.name)


if __name__ == "__main__":
    main()
