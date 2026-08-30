#!/usr/bin/env python3
"""Score each engine's recovery of a KNOWN two-dimensional truth.

Unlike every comparison against real data, here there is a right answer, so
"collapse" of the second dimension is measurable against truth rather than
against another engine.

Reports, per engine and per dimension: Procrustes correlation with truth,
amplitude (recovered sd / true sd, after optimal rotation), and roll-call
spread-sign agreement.

Runs out of the box on the panels and arms committed to this repository:

    python reproduce/score_synthetic_recovery.py strong
    python reproduce/score_synthetic_recovery.py moderate
    python reproduce/score_synthetic_recovery.py weak

and reprints the committed result beside the recomputed one, so you verify the
numbers rather than compare them by eye. Point it at your own run with the
SYN_DIR and ARMS_DIR environment variables.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Portable: this file lives in <repo>/reproduce/, so the repository root is its
# parent. Do NOT hardcode a machine path here.
REPO = Path(__file__).resolve().parent.parent
RUNGS = ("strong", "moderate", "weak")
PUBLISHED = REPO / "results" / "2026-08-21-synthetic-dim2-ladder"

rung = sys.argv[1] if len(sys.argv) > 1 else "strong"
if rung not in RUNGS:
    raise SystemExit(f"rung must be one of {RUNGS}, got {rung!r}")

SYN = Path(os.environ.get("SYN_DIR", REPO / "data" / "synthetic-2d" / rung))
ARMS = Path(os.environ.get("ARMS_DIR", PUBLISHED / "arms" / rung))
OUT = Path(os.environ.get("OUT_DIR", REPO / "reproduce" / "_out"))


def procrustes(A, B):
    """Rotate A onto B (single global rotation, no scaling). Returns aligned A."""
    Ac = A - A.mean(0)
    Bc = B - B.mean(0)
    U, _, Vt = np.linalg.svd(Ac.T @ Bc)
    R = U @ Vt
    return Ac @ R, Bc


def main():
    truth = pd.read_csv(SYN / "truth_coordinates.csv")
    tb = pd.read_csv(SYN / "truth_bill_parameters.csv")
    T = truth[["true_d1", "true_d2"]].to_numpy(float)

    seed = pd.read_csv(SYN / "wnominate_coordinates.csv")
    arms = {"SEED (votes-only start)": seed.rename(
        columns={"coord1D": "d1", "coord2D": "d2"})[["legislator_id", "d1", "d2"]]}
    for tag in ("faithful", "modern-local", "modern-global", "fortran"):
        f = ARMS / tag / "cpp_coordinates_all_periods.csv"
        if f.exists():
            arms[tag] = pd.read_csv(f).rename(
                columns={"coord1D": "d1", "coord2D": "d2"})[["legislator_id", "d1", "d2"]]

    print(f"rung: {rung}")
    print(f"panel: {SYN}")
    print(f"arms:  {ARMS}\n")
    print(f"truth: sd dim1 {T[:,0].std():.4f}  dim2 {T[:,1].std():.4f}   "
          f"{len(T)} legislators, {len(tb)} roll calls, "
          f"{int(tb.dim2_oriented.sum())} dim-2 oriented\n")
    print(f"{'arm':26s} {'r dim1':>8s} {'r dim2':>8s} {'amp dim1':>9s} {'amp dim2':>9s} "
          f"{'rc d2 signflip':>15s}")

    rows = []
    for tag, df in arms.items():
        m = truth.merge(df, on="legislator_id")
        A = m[["d1", "d2"]].to_numpy(float)
        B = m[["true_d1", "true_d2"]].to_numpy(float)
        Aal, Bc = procrustes(A, B)
        r1 = float(np.corrcoef(Aal[:, 0], Bc[:, 0])[0, 1])
        r2 = float(np.corrcoef(Aal[:, 1], Bc[:, 1])[0, 1])
        a1 = float(Aal[:, 0].std() / Bc[:, 0].std())
        a2 = float(Aal[:, 1].std() / Bc[:, 1].std())

        flip = np.nan
        bf = ARMS / tag / "cpp_bill_parameters.csv"
        if bf.exists():
            b = pd.read_csv(bf).set_index("rollcall_id").reindex(range(len(tb)))
            fitted = ~((b[["midpoint1D", "midpoint2D", "spread1D", "spread2D"]]
                        .abs() < 1e-12).all(axis=1))
            s_est = b.loc[fitted, "spread2D"].to_numpy(float)
            s_true = tb.loc[fitted.to_numpy(), "true_spread2D"].to_numpy(float)
            # polarity is a free global gauge; take the better of the two
            f1 = float(np.mean(np.sign(s_est) != np.sign(s_true)))
            flip = min(f1, 1.0 - f1)

        print(f"{tag:26s} {r1:8.4f} {r2:8.4f} {a1:9.4f} {a2:9.4f} "
              f"{'' if np.isnan(flip) else f'{100*flip:13.1f} %'}")
        rows.append(dict(arm=tag, r_dim1=r1, r_dim2=r2, amp_dim1=a1, amp_dim2=a2,
                         rc_dim2_signflip_pct=(None if np.isnan(flip) else 100 * flip)))

    got = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"recovery-{rung}.csv"
    got.to_csv(dest, index=False)
    print(f"\nwrote {dest}")

    # verify against the committed result rather than eyeballing it
    ref_path = PUBLISHED / f"recovery-{rung}.csv"
    if not ref_path.exists():
        print(f"no committed result at {ref_path}; nothing to verify against")
        return 0
    ref = pd.read_csv(ref_path)
    cols = ["r_dim1", "r_dim2", "amp_dim1", "amp_dim2", "rc_dim2_signflip_pct"]
    j = ref.merge(got, on="arm", suffixes=("_ref", "_got"))
    worst, where = 0.0, ""
    for c in cols:
        d = (j[f"{c}_ref"] - j[f"{c}_got"]).abs().max()
        if pd.notna(d) and d > worst:
            worst, where = float(d), c
    verdict = "MATCHES" if worst < 1e-9 else "DIFFERS"
    print(f"vs committed {ref_path.name}: {verdict} "
          f"(max |diff| {worst:.2e} on {where or 'n/a'}, {len(j)} arms compared)")
    return 0 if worst < 1e-9 else 1


if __name__ == "__main__":
    raise SystemExit(main())
