#!/usr/bin/env python3
r"""fig1-asymmetry -- "The dimensional asymmetry". THE CORE RESULT.

FIGURE-DESIGN-2026-08-11.md section 3, fig1-asymmetry (rank 1, essential).

WHAT THIS SHOWS
    Two stacked single-column panels on one shared y-scale.
      (a) first dimension, (b) second dimension.
    In each panel, the 470 legislator-period placements of legislaturas
    366-368 are ranked along x by their mean across the three admitted
    estimation frames, and drawn as a hairline point series at that mean.
    A point is INKED where all three frames agree on its sign and MUTED
    where they do not.
    Two bands, both centred on zero, both of CONSTANT half-width because
    both quantities are MEDIANS over placements, never per-placement
    intervals:
      pale band  = median cross-frame standard deviation
      dark band  = median within-fit parametric-bootstrap standard error

WHY IT IS THE PAPER
    Sign stability: 5 per cent of dim-1 placements are unstable across the
    admitted frames against 52 per cent on dim-2. The reader sees a nearly
    solid inked ribbon in (a) and a ribbon whose middle has gone pale in (b),
    and has the finding before reading a number.

NO COMPUTE. Reads four finished coordinate artifacts and 150 banked bootstrap
replicate .npy files. Procrustes + medians in numpy. No fits, no bootstrap
run, no engine invocation.

--------------------------------------------------------------------------
FOUR VARIANTS ARE RENDERED, NOT ONE.  FIGURE-DESIGN leaves two decisions open
and one of its stated expectations does not survive contact with the data.

  A  zero-centred band fills, EACH PANEL SORTED BY ITS OWN DIMENSION
     ("identical construction" read; a true caterpillar in both panels)
  B  zero-centred band fills, BOTH PANELS ON THE DIM-1 RANKING
     ("on the same sorted x" read; item i is the same placement in both
      panels, at the cost of panel (b) becoming a cloud)
  C  bands moved OUT of the plotting area into a right-hand scale key,
     per-panel sort.  Fixes a measured contrast defect in A/B: muted ink
     #898781 on the pale band #86b6ef is 1.70:1 and on the dark band
     #1c5cab is 1.84:1, and in panel (b) the muted points sit exactly on
     top of the bands.  Nothing is drawn behind the point series here.
  D  bands as a constant-half-width RIBBON around the sorted mean curve,
     per-panel sort.  Rendered so the rejection is visible: this is the
     construction FIGURE-DESIGN calls "the one dishonest move available
     here", because a median band drawn around each point reads as a
     per-placement interval.

--------------------------------------------------------------------------
HONESTY NOTE 1, and it changes the caption.
    FIGURE-DESIGN's three-second read for panel (a) says "the two bands
    nearly coincide". They do not. Measured here from the artifacts, in the
    corrected local-t frame over the 470 served placements:
        dim 1   median cross-frame SD 0.1430   median bootstrap SE 0.0327
        dim 2   median cross-frame SD 0.1915   median bootstrap SE 0.0705
    So the band NESTING RATIO is 4.38x on dimension one and 2.72x on
    dimension two -- larger on dim 1, the opposite of the intended
    perception. What is true, and what the shared absolute y-scale does
    show correctly, is that BOTH dim-2 bands are absolutely wider than
    their dim-1 counterparts (1.34x and 2.16x).
    Neither ratio is publishable as it stands: the numerator is now
    frame-corrected and the denominator bank is not. See GATE_RATIO2.
    DESK-PLAN R5 forbids printing a dim-1 ratio at all (it swings 1.17x to
    4.29x across cells). The drafted caption therefore does not claim the
    bands coincide and does not license any dim-1 ratio; the dimensional
    contrast is carried by the ink/mute encoding, which is the quantity
    R5 says is robust.

HONESTY NOTE 2.
    The dim-1 median bootstrap SE is recorded in no prior document
    (FIGURE-DESIGN section 8). It is read here directly from the
    route2_bigB bank: 0.033034. It happens to round to the 0.0330 that
    _tb_series_out.txt reports for a DIFFERENT bank. That agreement is a
    coincidence of the medians, not a carry-across; the value used here is
    computed in this file from the 150 banked .npy replicates.

Run:  python figgen-2026-08-11/fig1-asymmetry.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths
from _coords import (assert_panel_matches_fit, frame_displacement,
                     load_coords_local, load_coords_raw, padding_report,
                     served_periods)

# ---------------------------------------------------------------------------
# 0. PATHS
# ---------------------------------------------------------------------------
REPO = _paths.REPO
PAPER = _paths.PAPER
CH = REPO / "reproduce/out/chile"
PANEL_DIR = _paths.PANEL_DIR
N_PERIODS = _paths.N_PERIODS

MAP_CSV = REPO / "output/legislatura_map.csv"

# The admitted frame set at the recommended screen k in [11,102]
# (_joint_niter4.out, DESK-PLAN 1.1). F = 3: two C++ fits plus the external
# QueVotan reference, which is an independent ESTIMATOR on the same vote
# record (DESK-PLAN 5.3), not an independent curation.
REF_CSV = CH / "julio_reference_periodo9_by_leg.csv"          # frame 3, the alignment target
FIT_DIRS = {
    "canary_fseed_i4": CH / "canary_fseed_i4",                # 0 tolerance steps
    "cpp_run_chile_constseed": CH / "cpp_run_chile_constseed",  # 10 tolerance steps
}

OUTDIR = _paths.render_dir()
FIGNAME = "fig1-asymmetry"

# ---------------------------------------------------------------------------
# 1. NAMED CONSTANTS.  Non-negotiable 3: the denominator is never inlined.
#
#    pablo-10 (PABLO-HANDOFF-2026-08-11 D1) may replace the bootstrap base
#    fit with canary_fseed_i4. That is a ONE-LINE edit of DENOM_BANK below;
#    the two DENOM_MED_SE_* values are gate targets and are re-derived from
#    the bank on every run, so a swapped bank fails the gate loudly instead
#    of silently redrawing at the old height.
# ---------------------------------------------------------------------------
DENOM_BANK = CH / "julio_test/route2_bigB"   # <-- pablo-10 swaps this one line
DENOM_LABEL = "route2_bigB B=150, base fit cpp_run_chile, pooled w0/w1/w2"
DENOM_B_EXPECTED = 150
DENOM_MED_SE_DIM1 = 0.033034   # route2_bigB B=150, base cpp_run_chile, legs 366-368, n=482 roster
DENOM_MED_SE_DIM2 = 0.070614   # idem; DESK-PLAN 1.1 prints this as 0.0706
DENOM_GATE_TOL = 5e-4

# Numerator + sign-stability gates.
#
# REBASED 2026-08-13, when the export-frame correction (M-2) landed in the data
# path. The previous targets came from the _joint_niter4.out k=16 row, which was
# computed in the exported GLOBAL-t frame over a roster of 482 placements built
# from a padded export. Both of those inputs were wrong, so the gates below are
# recomputed in the LOCAL-t frame over the 470 served placements, by
# `frame_audit.py`, whose JSON output decomposes the move into a roster effect
# and a frame effect. The legacy values are kept so the rebase is auditable and
# so nobody re-derives them from a stale document.
#
#   quantity          legacy (global, 482)   now (local, 470)   moved by
#   median SD dim1          0.1416               0.1430          frame
#   median SD dim2          0.1944               0.1915          frame
#   sign-unstable dim1       4.6 %                4.9 %          frame
#   sign-unstable dim2      53.3 %               51.7 %          frame
#   placements               482                  470            roster
#
# The roster effect alone leaves sign instability at 53.4 %; the whole of the
# 53.3 -> 51.7 move is the frame. The two corrected sign-instability values
# reproduce, from these artifacts and without the engine, the 51.7 % and 4.9 %
# recorded independently in reference/NUMBERS-2026-08-13.md. That agreement is
# the acceptance test for the port.
LEGACY_GATE_GLOBAL_FRAME = {"sd1": 0.1416, "sd2": 0.1944, "ratio2": 2.75,
                            "flip1": 0.05, "flip2": 0.53, "n_keys": 482,
                            "source": "_joint_niter4.out k=16, global-t frame"}
GATE_SD1 = 0.1430
GATE_SD2 = 0.1915
GATE_RATIO2 = 2.72
GATE_FLIP1 = 0.049
GATE_FLIP2 = 0.517
GATE_N_KEYS = 470
GATE_F = 3
GATE_TOL_SD = 5e-4
GATE_TOL_RATIO = 0.02
GATE_TOL_FLIP = 0.01
# GATE_RATIO2 is a REGRESSION gate on this generator's own arithmetic, not a
# publishable quantity: its numerator is now frame-corrected while its
# denominator bank was banked in the global frame. A ratio that mixes frames
# does not go in the paper. The publishable ratio is settled by quevotan-db#3
# (B=75, corrected reader), and not before it lands.
GATE_RATIO2_MIXES_FRAMES = True
# DENOM_MED_SE_* are unchanged by the rebase: the roster shrink moves the
# median bootstrap SE by 3.8e-4 on dim 1 and 1.3e-4 on dim 2, both inside
# DENOM_GATE_TOL = 5e-4. Checked 2026-08-13, not assumed.

# ---------------------------------------------------------------------------
# 2. PANEL AND ALIGNMENT, asserted rather than assumed.
#    Non-negotiables 1 and 2. DATA-CONTRACT-2026-08-05 section 8 is binding.
# ---------------------------------------------------------------------------
PANEL_NAME = "reproduce/out/chile/cpp_input"
PANEL_LEGS = (346, 368)          # 23 periods
PANEL_VALID_VOTES = 692_839      # POST lopsidedness screen -- verified below
PANEL_ROLLCALLS_TOTAL = 12_952
PANEL_ROLLCALLS_KEPT = 6_858     # 6,094 dropped at the 0.025 minority threshold
FIG_LEGS = [366, 367, 368]
# 470 served placements. Was {366: 161, 367: 161, 368: 160} = 482 while the
# roster was built from the padded export. The twelve that left are six
# legislators (ids 1088-1093) who served period 23 only, i.e. legislatura 368,
# and were being drawn into legislaturas 366 and 367 where they had not yet
# arrived. This is M-4, settled: they are not phantoms in the sense of missing
# data, they are placements the export invented for legislators who were not
# there. See frame_audit.py.
FIG_LEG_COUNTS = {366: 155, 367: 155, 368: 160}   # 470 placements

# Non-negotiable 1: `dwnom2004_chile` (legs 347-369) is a DATA-CONTRACT
# section 4 panel violator and must never enter a comparison figure. This
# figure has no Fortran arm at all, but the guard is kept so the file cannot
# silently acquire one.
FORBIDDEN_PATH_TOKEN = "dwnom2004_chile"
ALLOWED_FORTRAN_RUN = "dwnom2004_chile_per_period"   # legs 346-368, us.num "1 25 119 119"

ALIGNMENT = (
    "uncentred orthogonal Procrustes; each C++ frame rotated onto the QueVotan "
    "reference by a SINGLE GLOBAL rotation over the stacked (legislatura, "
    "legislator) set of all 470 served placements; R = U V^T from svd(A^T B); no "
    "centring, no scaling, no translation, determinant unconstrained so "
    "reflections are admitted; the reference is left unrotated and is itself "
    "one of the three frames"
)

# ---------------------------------------------------------------------------
# 3. PALETTE.  FIGURE-DESIGN 7.3, already validated:
#      node scripts/validate_palette.js "#86b6ef,#1c5cab" --ordinal  -> PASS
#        (monotone lightness, adjacent gap, light end 2.11:1, single hue)
#    No alpha anywhere (7.3): every band is a solid hex, every scatter is
#    edgecolor="none".  No white halos (7.5).
# ---------------------------------------------------------------------------
BAND_WIDE = "#86b6ef"    # uncertainty band, wide  -> cross-frame spread
BAND_NARROW = "#1c5cab"  # uncertainty band, narrow -> bootstrap SE
INK = "#0b0b0b"          # primary ink   -> sign-stable placements, axis text
MUTED = "#898781"        # muted ink     -> sign-unstable placements, ticks
GRID = "#e1e0d9"         # solid hairline, never dashed

# Variant E only. Measured contrast of the spec's muted ink against the two
# bands it is drawn on top of: #898781 vs #86b6ef = 1.70:1 and vs #1c5cab =
# 1.84:1, i.e. the sign-unstable points -- which ARE the finding in panel (b)
# -- recede into the very bands they must be read against. Categorical slot 2
# is the palette's own answer: "#2a78d6,#eb6834" is validated at dE 24.7
# (protan) / 33.6 (normal), and #eb6834 against #86b6ef is a large hue
# separation with a luminance gap that survives greyscale (L 0.278 vs 0.448).
UNSTABLE_ALT = "#eb6834"  # categorical slot 2

LBL_WIDE = "cross-frame spread (median)"
LBL_NARROW = "bootstrap SE (median)"
LBL_INK = "sign stable"
LBL_MUTE = "sign unstable"

# ---------------------------------------------------------------------------
# 4. TYPOGRAPHY AND OUTPUT GEOMETRY.  FIGURE-DESIGN 7.4.
#    Single column: \columnwidth = 252pt = 3.5in. Author at exactly that width
#    and never scale; never bbox_inches='tight'.
# ---------------------------------------------------------------------------
COLW_IN = 3.5
FIGH_IN = 3.35
PNG_DPI = 400

matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,     # floor: never below 7pt at scale 1.0
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "pdf.fonttype": 42,       # IEEE PDF eXpress rejects Type 3
    "ps.fonttype": 42,
    "savefig.transparent": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

YLIM = (-1.0, 1.0)
YTICKS = [-1.0, -0.5, 0.0, 0.5, 1.0]
MARKER_S = 2.0            # ~1.4pt diameter; at 0.45pt spacing this reads as a ribbon


# ---------------------------------------------------------------------------
# 5. HELPERS
# ---------------------------------------------------------------------------
def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def die(msg: str) -> None:
    print("\n" + "!" * 74, file=sys.stderr)
    print("FAILED ALIGNMENT / GATE ASSERTION -- nothing was written", file=sys.stderr)
    print(msg, file=sys.stderr)
    print("!" * 74 + "\n", file=sys.stderr)
    raise SystemExit(2)


def guard_paths(paths) -> None:
    """Non-negotiable 1. Refuse the 347-369 Fortran panel outright."""
    for p in paths:
        s = str(p).replace("\\", "/")
        if FORBIDDEN_PATH_TOKEN in s and ALLOWED_FORTRAN_RUN not in s:
            die(f"input path names the 347-369 panel violator: {s}\n"
                f"Only {ALLOWED_FORTRAN_RUN} (legs 346-368) may be compared against.")


def proc(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Uncentred orthogonal Procrustes: rotate A onto B."""
    U, _, Vt = np.linalg.svd(A.T @ B)
    return A @ (U @ Vt)


def read_summary(d: Path) -> dict:
    return {r["parameter"]: r["value"] for r in csv.DictReader(open(d / "cpp_summary.csv"))}


# ---------------------------------------------------------------------------
# 6. LOAD, WITH THE PANEL ASSERTED
# ---------------------------------------------------------------------------
def load() -> dict:
    guard_paths([MAP_CSV, REF_CSV, DENOM_BANK] + list(FIT_DIRS.values()))

    p2leg = {int(d["period_index"]): int(d["legislatura"])
             for d in csv.DictReader(open(MAP_CSV))}

    # -- panel assertion: period 1 must be leg 346 and period 23 leg 368.
    if p2leg.get(1) != PANEL_LEGS[0] or p2leg.get(23) != PANEL_LEGS[1]:
        die(f"legislatura_map period 1 -> {p2leg.get(1)}, period 23 -> {p2leg.get(23)}; "
            f"expected {PANEL_LEGS[0]} and {PANEL_LEGS[1]}. This is the "
            f"one-legislatura offset class (FIGURE-DESIGN 5.1/5.2).")
    for per, leg in ((21, 366), (22, 367), (23, 368)):
        if p2leg.get(per) != leg:
            die(f"period {per} maps to legislatura {p2leg.get(per)}, expected {leg}")

    # -- panel assertion: both C++ fits are 23-period runs on 692,839 valid votes.
    summaries = {}
    for name, d in FIT_DIRS.items():
        s = read_summary(d)
        summaries[name] = s
        if int(s["periods"]) != 23:
            die(f"{name}: periods={s['periods']}, expected 23 (legs 346-368)")
        if int(s["valid_votes"]) != PANEL_VALID_VOTES:
            die(f"{name}: valid_votes={s['valid_votes']}, expected {PANEL_VALID_VOTES}")
        if int(s["dimensions"]) != 2:
            die(f"{name}: dimensions={s['dimensions']}, expected 2")
        if int(s["iterations"]) != 4:
            die(f"{name}: iterations={s['iterations']}, expected the prescribed NITER=4")

    # -- FRAME (M-2, 2026-08-13). The export evaluates each legislator's Legendre
    #    polynomial at a GLOBAL t over all 23 periods; the optimizer and the final
    #    likelihood use a LOCAL t over that legislator's own served span. They
    #    coincide for 14 of 338 here, so the raw export is NOT the fitted
    #    configuration and this figure used to be drawn in a frame the estimator
    #    never used. `_coords.load_coords_local` reconstructs the fitted frame.
    #    Provenance: findings/FINDING-export-frame-2026-08-12.md, quevotan-db#3.
    served = served_periods(PANEL_DIR, N_PERIODS)
    for name, d in FIT_DIRS.items():
        assert_panel_matches_fit(PANEL_DIR, d, N_PERIODS, die=die)

    def load_fit(d: Path):
        raw = load_coords_raw(d)                       # exported, global t, padded
        loc = load_coords_local(d, N_PERIODS, served)   # fitted, local t, served only
        co = {}
        for (lid, per), (c1, c2) in loc.items():
            leg = p2leg.get(per)
            if leg in FIG_LEGS:
                co[(leg, str(lid))] = (c1, c2)
        return co, len(raw)

    fits, fit_rows = {}, {}
    for name, d in FIT_DIRS.items():
        fits[name], fit_rows[name] = load_fit(d)
    frame_audit = {name: {**padding_report(d, served, N_PERIODS),
                          **frame_displacement(d, served, N_PERIODS)}
                   for name, d in FIT_DIRS.items()}

    ref, ref_rows = {}, 0
    for d in csv.DictReader(open(REF_CSV)):
        ref_rows += 1
        try:
            leg = int(float(d["legislatura"]))
        except ValueError:
            continue
        if leg in FIG_LEGS:
            ref[(leg, str(d["legislator_id"]))] = (float(d["x"]), float(d["y"]))

    keys = sorted(k for k in ref if all(k in f for f in fits.values()))

    # -- roster assertion. Fail loudly if the 470-key served roster moved.
    if len(keys) != GATE_N_KEYS:
        die(f"roster is {len(keys)} placements, expected {GATE_N_KEYS}")
    per_leg = {leg: sum(1 for k in keys if k[0] == leg) for leg in FIG_LEGS}
    if per_leg != FIG_LEG_COUNTS:
        die(f"per-legislatura roster {per_leg}, expected {FIG_LEG_COUNTS}")
    roster_md5 = hashlib.md5(
        "\n".join(f"{a}|{b}" for a, b in keys).encode()).hexdigest()

    # -- bootstrap bank, pooled across the three disjoint-seed shards.
    bank_keys = np.load(DENOM_BANK / "keys.npy")
    xref = np.load(DENOM_BANK / "Xref.npy")
    shards, files = {}, []
    for w in (0, 1, 2):
        fs = sorted((DENOM_BANK / f"w{w}").glob("t*.npy"))
        shards[f"w{w}"] = {"n": len(fs), "files": {f.name: md5(f) for f in fs}}
        files.extend(fs)
    if len(files) != DENOM_B_EXPECTED:
        die(f"bootstrap bank holds B={len(files)} replicates, expected "
            f"{DENOM_B_EXPECTED}. Update DENOM_B_EXPECTED and the two "
            f"DENOM_MED_SE_* constants together, never one of them.")
    A = np.stack([np.load(f) for f in files])
    if A.shape[1:] != xref.shape or A.shape[1] != bank_keys.shape[0]:
        die(f"bank geometry mismatch: A{A.shape} Xref{xref.shape} keys{bank_keys.shape}")
    D = A - xref[None, :, :]
    seb = np.sqrt(np.nansum(D * D, axis=0) / (A.shape[0] - 1))
    se = {}
    for i, s in enumerate(bank_keys):
        lid, per = str(s).split("|")
        leg = p2leg.get(int(per))
        if leg in FIG_LEGS:
            se[(leg, lid)] = (float(seb[i, 0]), float(seb[i, 1]))
    missing = [k for k in keys if k not in se]
    if missing:
        die(f"{len(missing)} of {len(keys)} placements absent from the bootstrap bank")

    return dict(p2leg=p2leg, fits=fits, ref=ref, keys=keys, se=se,
                summaries=summaries, fit_rows=fit_rows, ref_rows=ref_rows,
                roster_md5=roster_md5, shards=shards, frame_audit=frame_audit,
                bank_shape=list(A.shape), bank_nkeys=int(bank_keys.shape[0]))


# ---------------------------------------------------------------------------
# 7. COMPUTE
# ---------------------------------------------------------------------------
def compute(dat: dict) -> dict:
    keys = dat["keys"]
    R = np.array([dat["ref"][k] for k in keys])
    S = np.stack([R] + [proc(np.array([dat["fits"][n][k] for k in keys]), R)
                        for n in FIT_DIRS])
    if S.shape[0] != GATE_F:
        die(f"F={S.shape[0]} frames, expected {GATE_F}")

    mean = S.mean(0)
    sd = np.std(S, axis=0)                     # population sd across frames, ddof=0
    agree = (S > 0).all(0) | (S < 0).all(0)    # per placement, per dimension

    med_sd = [float(np.median(sd[:, d])) for d in (0, 1)]
    med_se = [float(np.median([dat["se"][k][d] for k in keys])) for d in (0, 1)]
    flip = [float(np.mean(~agree[:, d])) for d in (0, 1)]

    print(f"\n  n placements       {len(keys)}   (legs 366/367/368 = "
          f"{FIG_LEG_COUNTS[366]}/{FIG_LEG_COUNTS[367]}/{FIG_LEG_COUNTS[368]})")
    print(f"  frames F           {S.shape[0]}  "
          f"({', '.join(list(FIT_DIRS) + ['julio_reference_periodo9_by_leg'])})")
    print(f"  median cross-frame SD   dim1 {med_sd[0]:.4f}   dim2 {med_sd[1]:.4f}")
    print(f"  median bootstrap SE     dim1 {med_se[0]:.6f}   dim2 {med_se[1]:.6f}"
          f"   [{DENOM_LABEL}]")
    print(f"  ratio                   dim1 {med_sd[0]/med_se[0]:.2f}x  (NEVER PRINTED, "
          f"DESK-PLAN R5)   dim2 {med_sd[1]/med_se[1]:.2f}x")
    print(f"  sign-unstable           dim1 {100*flip[0]:.1f}%   dim2 {100*flip[1]:.1f}%")

    # ---- gates ------------------------------------------------------------
    bad = []
    if abs(med_sd[0] - GATE_SD1) > GATE_TOL_SD:
        bad.append(f"sd1 {med_sd[0]:.4f} != {GATE_SD1}")
    if abs(med_sd[1] - GATE_SD2) > GATE_TOL_SD:
        bad.append(f"sd2 {med_sd[1]:.4f} != {GATE_SD2}")
    if abs(med_sd[1] / med_se[1] - GATE_RATIO2) > GATE_TOL_RATIO:
        bad.append(f"dim-2 ratio {med_sd[1]/med_se[1]:.3f} != {GATE_RATIO2}")
    if abs(flip[0] - GATE_FLIP1) > GATE_TOL_FLIP:
        bad.append(f"flip1 {flip[0]:.3f} != {GATE_FLIP1}")
    if abs(flip[1] - GATE_FLIP2) > GATE_TOL_FLIP:
        bad.append(f"flip2 {flip[1]:.3f} != {GATE_FLIP2}")
    if abs(med_se[0] - DENOM_MED_SE_DIM1) > DENOM_GATE_TOL:
        bad.append(f"median SE dim1 {med_se[0]:.6f} != DENOM_MED_SE_DIM1 "
                   f"{DENOM_MED_SE_DIM1}")
    if abs(med_se[1] - DENOM_MED_SE_DIM2) > DENOM_GATE_TOL:
        bad.append(f"median SE dim2 {med_se[1]:.6f} != DENOM_MED_SE_DIM2 "
                   f"{DENOM_MED_SE_DIM2}")
    if bad:
        die("gate failures against the 2026-08-13 local-t rebase and the named "
            "denominator constants. Run frame_audit.py before changing any "
            "target: it separates a roster effect from a frame effect, and only "
            "one of those is ever a legitimate reason to move a gate.\n  "
            + "\n  ".join(bad))
    print("  GATES PASS against the 2026-08-13 local-t rebase "
          "(sd1 .1430 / sd2 .1915 / 4.9% / 51.7%, n=470). Legacy global-t "
          "targets were sd1 .1416 / sd2 .1944 / 4.6% / 53.3%, n=482.\n")

    # The drawn half-widths are the NAMED CONSTANTS, not the recomputed values,
    # so what the figure shows is exactly what the manifest and the prose say.
    return dict(S=S, mean=mean, agree=agree,
                med_sd=med_sd, med_se=med_se, flip=flip,
                half_sd=[GATE_SD1, GATE_SD2],
                half_se=[DENOM_MED_SE_DIM1, DENOM_MED_SE_DIM2])


# ---------------------------------------------------------------------------
# 8. RENDER
# ---------------------------------------------------------------------------
def _style_axes(ax, n, show_x):
    ax.set_ylim(*YLIM)
    ax.set_yticks(YTICKS)
    ax.set_yticklabels(["-1", "", "0", "", "1"])
    ax.set_xlim(-6, n + 5)
    ax.set_xticks([1, (n + 1) // 2, n])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=MUTED)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, linewidth=0.4, linestyle="-")
    if not show_x:
        ax.tick_params(labelbottom=False)


def _series(ax, x, y, agree):
    ax.scatter(x[agree], y[agree], s=MARKER_S, c=INK, edgecolors="none",
               linewidths=0, zorder=5, marker="o")
    ax.scatter(x[~agree], y[~agree], s=MARKER_S, c=MUTED, edgecolors="none",
               linewidths=0, zorder=4, marker="o")


def _legend(fig, ribbon=False):
    wide = LBL_WIDE + (" about the mean" if ribbon else "")
    handles = [
        Patch(facecolor=BAND_WIDE, edgecolor="none", label=wide),
        Patch(facecolor=BAND_NARROW, edgecolor="none", label=LBL_NARROW),
        Line2D([], [], marker="o", linestyle="none", markersize=2.6,
               markerfacecolor=INK, markeredgecolor="none", label=LBL_INK),
        Line2D([], [], marker="o", linestyle="none", markersize=2.6,
               markerfacecolor=MUTED, markeredgecolor="none", label=LBL_MUTE),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, -0.012), handlelength=1.25,
               handletextpad=0.5, columnspacing=1.0, labelspacing=0.32,
               borderaxespad=0.0, fontsize=7, labelcolor=INK)


def render(res: dict, variant: str, out_stem: Path) -> dict:
    """variant in {A, B, C, D}."""
    mean, agree = res["mean"], res["agree"]
    n = mean.shape[0]
    order1 = np.argsort(mean[:, 0])

    if variant == "C":
        fig = plt.figure(figsize=(COLW_IN, FIGH_IN))
        gs = GridSpec(2, 2, figure=fig, width_ratios=[1.0, 0.075],
                      left=0.145, right=0.985, top=0.985, bottom=0.185,
                      hspace=0.16, wspace=0.045)
        axes = [fig.add_subplot(gs[r, 0]) for r in (0, 1)]
        keys_ax = [fig.add_subplot(gs[r, 1]) for r in (0, 1)]
    else:
        fig = plt.figure(figsize=(COLW_IN, FIGH_IN))
        gs = GridSpec(2, 1, figure=fig, left=0.145, right=0.985,
                      top=0.985, bottom=0.185, hspace=0.16)
        axes = [fig.add_subplot(gs[r, 0]) for r in (0, 1)]
        keys_ax = [None, None]

    for d, ax in enumerate(axes):
        o = order1 if variant == "B" else np.argsort(mean[:, d])
        y = mean[o, d]
        a = agree[o, d]
        x = np.arange(1, n + 1, dtype=float)
        hs, he = res["half_sd"][d], res["half_se"][d]

        _style_axes(ax, n, show_x=(d == 1))

        if variant in ("A", "B"):
            ax.axhspan(-hs, hs, facecolor=BAND_WIDE, edgecolor="none", zorder=1)
            ax.axhspan(-he, he, facecolor=BAND_NARROW, edgecolor="none", zorder=2)
        elif variant == "D":
            ax.fill_between(x, y - hs, y + hs, facecolor=BAND_WIDE,
                            edgecolor="none", zorder=1)
            ax.fill_between(x, y - he, y + he, facecolor=BAND_NARROW,
                            edgecolor="none", zorder=2)

        ax.axhline(0.0, color=MUTED, linewidth=0.5, zorder=3)
        _series(ax, x, y, a)

        ax.set_ylabel("first dimension" if d == 0 else "second dimension",
                      color=INK, labelpad=2)
        ax.text(0.012, 0.955, "(a)" if d == 0 else "(b)", transform=ax.transAxes,
                ha="left", va="top", fontsize=7, color=INK)

        if variant == "C":
            kax = keys_ax[d]
            kax.set_ylim(*YLIM)
            kax.set_xlim(0, 1)
            kax.add_patch(Rectangle((0.06, -hs), 0.88, 2 * hs,
                                    facecolor=BAND_WIDE, edgecolor="none"))
            kax.add_patch(Rectangle((0.28, -he), 0.44, 2 * he,
                                    facecolor=BAND_NARROW, edgecolor="none"))
            kax.axhline(0.0, color=MUTED, linewidth=0.5)
            for s in ("top", "right", "bottom", "left"):
                kax.spines[s].set_visible(False)
            kax.set_xticks([])
            kax.set_yticks([])

    axes[1].set_xlabel("legislator-period placement, ranked by cross-frame mean"
                       + (" on dim. 1" if variant == "B" else ""),
                       color=INK, labelpad=2)
    _legend(fig, ribbon=(variant == "D"))

    out_png = out_stem.with_suffix(".png")
    out_pdf = out_stem.with_suffix(".pdf")
    fig.savefig(out_png, dpi=PNG_DPI, bbox_inches=None, pad_inches=0.01)
    fig.savefig(out_pdf, bbox_inches=None, pad_inches=0.01)
    plt.close(fig)
    print(f"  wrote {out_png.name} / {out_pdf.name}")
    return {"png": str(out_png), "pdf": str(out_pdf),
            "png_md5": md5(out_png), "pdf_md5": md5(out_pdf)}


# ---------------------------------------------------------------------------
# 9. CONTACT SHEET + ROBUSTNESS SHEET (review aids, never included in the .tex)
# ---------------------------------------------------------------------------
DESCR = {
    "A": "A  spec-literal: zero-centred fills, per-panel sort",
    "B": "B  zero-centred fills, both panels on the dim-1 rank",
    "C": "C  bands moved to a right-hand scale key (contrast fix)",
    "D": "D  bands as a ribbon around the mean (rejected reading)",
}


def contact_sheet(pngs, out_png: Path):
    fig, axes = plt.subplots(1, len(pngs), figsize=(3.9 * len(pngs), 4.5))
    for ax, (v, p) in zip(np.atleast_1d(axes), pngs):
        ax.imshow(plt.imread(p))
        ax.set_title(DESCR[v], fontsize=10, color=INK)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_png, dpi=110, bbox_inches=None, pad_inches=0.02)
    plt.close(fig)
    print(f"  wrote {out_png.name}")


def _deutan(rgb: np.ndarray) -> np.ndarray:
    """Vienot 1999 deuteranopia simulation on linear RGB."""
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.31399, 0.63951, 0.04649],
                  [0.15537, 0.75789, 0.08670],
                  [0.01775, 0.10945, 0.87259]])
    Mi = np.linalg.inv(M)
    lms = lin @ M.T
    lms[..., 1] = 0.9513092 * lms[..., 0] + 0.04264323 * lms[..., 2]
    out = np.clip(lms @ Mi.T, 0, 1)
    return np.where(out <= 0.0031308, out * 12.92, 1.055 * out ** (1 / 2.4) - 0.055)


def robustness_sheet(png: Path, out_png: Path):
    im = plt.imread(png)[..., :3]
    grey = im @ np.array([0.2126, 0.7152, 0.0722])
    views = [(im, "as rendered"),
             (np.dstack([grey] * 3), "greyscale (luminance)"),
             (_deutan(im), "deuteranopia (Vienot)"),
             (1.0 - im, "inverted (dark reader)")]
    fig, axes = plt.subplots(1, 4, figsize=(15.0, 4.5))
    for ax, (a, t) in zip(axes, views):
        ax.imshow(np.clip(a, 0, 1))
        ax.set_title(t, fontsize=10, color=INK)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_png, dpi=110, bbox_inches=None, pad_inches=0.02)
    plt.close(fig)
    print(f"  wrote {out_png.name}")


# ---------------------------------------------------------------------------
# 10. MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    print(f"\n{FIGNAME}  --  panel {PANEL_LEGS[0]}-{PANEL_LEGS[1]}, "
          f"figure legs {FIG_LEGS[0]}-{FIG_LEGS[-1]}")

    dat = load()
    res = compute(dat)

    variants = {}
    for v in ("A", "B", "C", "D"):
        variants[v] = render(res, v, OUTDIR / f"{FIGNAME}-{v}_v1")

    # The recommended build is also written under the plain figure name so the
    # .tex has one stable target. C is recommended: see the manifest note.
    recommended = "C"
    variants["recommended"] = render(res, recommended, OUTDIR / f"{FIGNAME}_v1")

    contact_sheet([(v, variants[v]["png"]) for v in ("A", "B", "C", "D")],
                  OUTDIR / f"{FIGNAME}-variants_v1.png")
    robustness_sheet(Path(variants["recommended"]["png"]),
                     OUTDIR / f"{FIGNAME}-robustness_v1.png")

    # -- manifest ----------------------------------------------------------
    man = {
        "figure": FIGNAME,
        "version": "v1",
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec": "FIGURE-DESIGN-2026-08-11.md section 3, fig1-asymmetry (rank 1)",
        "generating_command": {
            "cwd": str(PAPER),
            "command": "python figgen-2026-08-11/fig1-asymmetry.py",
            "argv": sys.argv,
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },

        "panel": {
            "name": PANEL_NAME,
            "legislaturas": f"{PANEL_LEGS[0]}-{PANEL_LEGS[1]}",
            "periods": 23,
            "valid_votes": PANEL_VALID_VOTES,
            "valid_votes_side_of_screen": (
                "POST-screen. Verified in this session by recounting "
                "reproduce/out/chile/cpp_input/votes_matrix_p1..p23.csv: 12,952 "
                "roll calls carry 1,266,034 valid (yea|nay) votes; applying the "
                "0.025 minority lopsidedness screen (main_cli.cpp:471, "
                "dwnominate.cpp:187, dwnom2004.f:324-326) keeps 6,858 roll calls "
                "and exactly 692,839 valid votes, which is the number both "
                "cpp_summary.csv files report. 6,094 roll calls are dropped."),
            "rollcalls_total": PANEL_ROLLCALLS_TOTAL,
            "rollcalls_kept_after_lopsidedness_screen": PANEL_ROLLCALLS_KEPT,
            "rollcalls_dropped": PANEL_ROLLCALLS_TOTAL - PANEL_ROLLCALLS_KEPT,
            "figure_counts_rollcalls_or_votes": False,
            "figure_counts": "legislator-period placements, not roll calls or votes",
        },

        "legislatura_span_drawn": {
            "legs": FIG_LEGS,
            "placements_per_leg": FIG_LEG_COUNTS,
            "rows_drawn": GATE_N_KEYS,
            "columns_frames": GATE_F,
            "roster_md5": dat["roster_md5"],
        },

        "alignment": {
            "operator": ALIGNMENT,
            "target": str(REF_CSV),
            "fortran_arm": "none -- this figure has no Fortran arm",
            "panel_offset_guard": (
                f"dwnom2004_chile (legs 347-369, us.num '1 103 120 120') is "
                f"refused by guard_paths(); only {ALLOWED_FORTRAN_RUN} "
                f"(us.num '1 25 119 119', legs 346-368) would be admitted. "
                f"period->legislatura asserted: 1->346, 21->366, 22->367, 23->368."),
            "padding": ("structurally impossible since 2026-08-13: coordinates "
                        "enter through _coords.load_coords_local, which emits a "
                        "placement only for a (legislator, period) the legislator "
                        "actually served. The join can no longer admit a padded "
                        "row even if the roster asked for one. See frame.padding "
                        "for the counts."),
        },

        "frame": {
            "reader": "_coords.load_coords_local",
            "declared": ("LOCAL t, the frame the optimizer and the final "
                         "likelihood used (reconstructLegislatorCoords, "
                         "src/dwnominate.cpp:1516-1531). NOT the exported global-t "
                         "frame (getCoordinatesAtPeriod, dwnominate.hpp:291)."),
            "why": ("The export evaluates each legislator's Legendre polynomial "
                    "over the whole 23-period panel; the estimator evaluated it "
                    "over that legislator's own served span. They coincide only "
                    "for a legislator who served every period: 14 of 338 here. "
                    "Before 2026-08-13 this figure was drawn in the global-t "
                    "frame, which is not the fitted configuration."),
            "provenance": ("findings/FINDING-export-frame-2026-08-12.md; found by "
                           "Pablo on an independent machine, quevotan-db#3, "
                           "2026-08-11; M-2 in decide/DECISIONS.md"),
            "panel": {"path": str(PANEL_DIR), "n_periods": N_PERIODS,
                      "served_span_basis": ("unscreened matrix, matching "
                                            "loadLegislators, which does not "
                                            "consult validRollCalls_")},
            "audit": dat["frame_audit"],
        },

        "frames": {
            "admitted_set": "k in [11,102] (DESK-PLAN 1.1); F=3",
            "members": [
                {"name": "canary_fseed_i4", "role": "C++ frame, 0 tolerance steps",
                 "path": str(FIT_DIRS["canary_fseed_i4"] /
                             "cpp_coordinates_all_periods.csv"),
                 "md5": md5(FIT_DIRS["canary_fseed_i4"] /
                            "cpp_coordinates_all_periods.csv"),
                 "rows": dat["fit_rows"]["canary_fseed_i4"],
                 "summary": dat["summaries"]["canary_fseed_i4"]},
                {"name": "cpp_run_chile_constseed",
                 "role": "C++ frame, 10 tolerance steps",
                 "path": str(FIT_DIRS["cpp_run_chile_constseed"] /
                             "cpp_coordinates_all_periods.csv"),
                 "md5": md5(FIT_DIRS["cpp_run_chile_constseed"] /
                            "cpp_coordinates_all_periods.csv"),
                 "rows": dat["fit_rows"]["cpp_run_chile_constseed"],
                 "summary": dat["summaries"]["cpp_run_chile_constseed"]},
                {"name": "julio_reference_periodo9_by_leg",
                 "role": ("external QueVotan reference; an independent ESTIMATOR "
                          "on the same MongoDB vote record (DESK-PLAN 5.3), not "
                          "an independent curation. Unscreenable, included as a "
                          "lineage (DESK-PLAN R7). It is the alignment target."),
                 "path": str(REF_CSV), "md5": md5(REF_CSV),
                 "rows": dat["ref_rows"]},
            ],
            "legislatura_map": {"path": str(MAP_CSV), "md5": md5(MAP_CSV)},
        },

        "denominator": {
            "named_constants": {
                "DENOM_BANK": str(DENOM_BANK),
                "DENOM_LABEL": DENOM_LABEL,
                "DENOM_MED_SE_DIM1": DENOM_MED_SE_DIM1,
                "DENOM_MED_SE_DIM2": DENOM_MED_SE_DIM2,
            },
            "recomputed_this_run": {"dim1": res["med_se"][0], "dim2": res["med_se"][1]},
            "how_dim1_was_obtained": (
                "FIGURE-DESIGN section 8 records that the dim-1 median bootstrap "
                "SE exists in no document: _joint_niter4.out prints only the "
                "dim-1 RATIO and _tb_series_out.txt's 0.0330 is a different "
                "bank. It is computed here from route2_bigB directly: pool the "
                "150 .npy replicates across shards w0/w1/w2, take "
                "SE = sqrt(nansum((A - Xref)^2, axis=0)/(B-1)) per (key, dim) "
                "exactly as _joint_niter4.py:88-100 does, restrict to the 470 "
                "placements on legs 366-368, take the median. Result 0.033034. "
                "It happens to round to the 0.0330 of the other bank; that is a "
                "coincidence of medians, not a carry-across."),
            "bank": {
                "root": str(DENOM_BANK),
                "B": DENOM_B_EXPECTED,
                "replicate_array_shape": dat["bank_shape"],
                "keys_npy": {"path": str(DENOM_BANK / "keys.npy"),
                             "md5": md5(DENOM_BANK / "keys.npy"),
                             "n": dat["bank_nkeys"]},
                "Xref_npy": {"path": str(DENOM_BANK / "Xref.npy"),
                             "md5": md5(DENOM_BANK / "Xref.npy")},
                "shards": dat["shards"],
            },
            "swap_note": ("pablo-10 / PABLO-HANDOFF D1 moves the base fit to "
                          "canary_fseed_i4. That is a one-line edit of "
                          "DENOM_BANK; the two DENOM_MED_SE_* gate values must "
                          "be updated in the same edit or the run aborts."),
        },

        "quantities_drawn": {
            "median_cross_frame_sd": {"dim1": res["med_sd"][0], "dim2": res["med_sd"][1]},
            "median_bootstrap_se": {"dim1": res["med_se"][0], "dim2": res["med_se"][1]},
            "band_half_widths_drawn": {
                "pale_dim1": res["half_sd"][0], "pale_dim2": res["half_sd"][1],
                "dark_dim1": res["half_se"][0], "dark_dim2": res["half_se"][1]},
            "sign_unstable_fraction": {"dim1": res["flip"][0], "dim2": res["flip"][1]},
            "dim2_ratio": res["med_sd"][1] / res["med_se"][1],
            "dim1_ratio_NOT_FOR_PUBLICATION": {
                "value": res["med_sd"][0] / res["med_se"][0],
                "why": ("DESK-PLAN R5: the dim-1 ratio swings 1.17x to 4.29x "
                        "across cells and is not a stable quantity. Recorded "
                        "here only so a reader of this manifest knows what the "
                        "panel (a) band geometry implies. Never print it."),
            },
        },

        "gates": {
            "source": "_joint_niter4.out k=16 row "
                      "(C:/Users/cow/.claude/jobs/b43b64d6/tmp/_joint_niter4.out)",
            "targets": {"sd1": GATE_SD1, "sd2": GATE_SD2, "ratio2": GATE_RATIO2,
                        "flip1": GATE_FLIP1, "flip2": GATE_FLIP2,
                        "n_keys": GATE_N_KEYS, "F": GATE_F},
            "result": "PASS",
        },

        "variants": {
            "A": {"desc": DESCR["A"], **variants["A"]},
            "B": {"desc": DESCR["B"], **variants["B"]},
            "C": {"desc": DESCR["C"], **variants["C"]},
            "D": {"desc": DESCR["D"], **variants["D"]},
            "recommended": {"variant": recommended, **variants["recommended"]},
        },

        "open_decisions": [
            ("SORT. FIGURE-DESIGN says panel (b) is 'identical construction' "
             "AND 'on the same sorted x'. Those disagree. A/C/D sort each panel "
             "by its own dimension (a caterpillar in both); B puts both panels "
             "on the dim-1 rank so item i is the same placement in both, at the "
             "cost of panel (b) becoming a cloud. Roberto picks."),
            ("BAND GEOMETRY. A/B/C draw the bands centred on zero, as a scale "
             "reference. D draws them as a ribbon around each point. D is "
             "rendered only so the rejection is visible: FIGURE-DESIGN calls a "
             "median band presented as a per-placement interval 'the one "
             "dishonest move available here', and the ribbon is exactly that."),
            ("BAND PLACEMENT. C moves the two bands into a right-hand scale key "
             "because muted ink #898781 measures 1.70:1 against the pale band "
             "#86b6ef and 1.84:1 against the dark band #1c5cab, and in panel "
             "(b) the muted points sit on top of both. In C nothing is drawn "
             "behind the point series. Recommended for that reason."),
        ],

        "departures_from_spec": [
            ("FIGURE-DESIGN's three-second read for panel (a), 'the two bands "
             "nearly coincide', is FALSE on the measured numbers. dim-1 nesting "
             "is 4.29x against dim-2's 2.75x, i.e. relatively WIDER on dim 1. "
             "What is true on the shared absolute scale is that both dim-2 "
             "bands are absolutely wider (1.37x pale, 2.14x dark). The drafted "
             "caption makes no coincidence claim and licenses no dim-1 ratio."),
            ("The design note anticipated 'the middle two thirds of the point "
             "series is muted' on dim 2. Measured by decile of the dim-2 rank, "
             "the muted fraction runs 4, 8, 35, 67, 88, 100, 96, 62, 48, 24 per "
             "cent, so the muting is concentrated in the middle as expected but "
             "reaches the tails: exactly one placement with |mean| > 0.4 is "
             "sign-unstable, and the extreme-positive decile is still 24 per "
             "cent unstable. The figure shows this rather than smoothing it."),
        ],

        "caption_draft": (
            "Identification spread against sampling error, legislaturas 366 to "
            "368 on the 23-period panel (346-368, 692,839 valid votes after the "
            "lopsidedness screen), 470 served legislator-period placements ranked by "
            "their cross-frame mean. Pale band: the median spread across the "
            "three admitted frames. Dark band: the median within-fit bootstrap "
            "standard error. Both are medians over placements and are drawn at "
            "constant width; neither is a per-placement interval. Points are "
            "inked where all three frames agree on the sign. (a) first "
            "dimension; (b) second dimension, same scale."),

        "not_established": [
            "No fit, bootstrap or engine call was run. Every number is read "
            "from artifacts already on disk.",
            "_joint_niter4.out lives only in a session scratch directory "
            "(C:/Users/cow/.claude/jobs/b43b64d6/tmp/) and not in quevotan-db, "
            "so the gate source is not in the reproduction package. This "
            "generator reproduces its k=16 row from first principles, which is "
            "the mitigation, but the .out file itself should be moved into "
            "reproduce/scripts/ before the package ships.",
            "route2_bigB is PAUSED at B=150 of a targeted 360 "
            "(PAUSED-2026-08-06.md). The dark band moves if it is resumed.",
        ],
    }
    mpath = OUTDIR / f"{FIGNAME}.manifest.json"
    mpath.write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(f"  wrote {mpath.name}\n")


if __name__ == "__main__":
    main()
