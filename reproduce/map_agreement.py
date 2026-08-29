#!/usr/bin/env python3
"""
Map agreement between two DW-NOMINATE fits, including the amplitude ratio.

This reproduces the map-agreement columns of the paper's reproduction table:
the two Pearson correlations after rotation, the mean 2-D distance, and the
amplitude ratio.

    python reproduce/map_agreement.py --reference REF.csv --engine ENG.csv

Both files are coordinate exports with the columns

    legislator_id, period, coord1D, coord2D

which is what both C++ engines write (`cpp_coordinates_all_periods.csv`) and
what the Fortran arm's `coordinates.csv` carries. Rows are matched on
(legislator_id, period); unmatched rows are dropped and counted.

WHY THE AMPLITUDE RATIO EXISTS
------------------------------
Maps are compared after the best rigid rotation of one onto the other:
orthogonal Procrustes, WITHOUT scaling. Orthogonal means the fit absorbs a
rotation and a reflection -- the latter matters, because the two engines differ
on polarity by convention -- but it does NOT absorb a difference in size. That
asymmetry is deliberate.

It has to be, because both headline statistics are blind to size. Pearson r is
invariant to any positive rescaling of either map, and a no-scaling Procrustes
fit reports the residual of the best rotation, not the size mismatch itself. So
a map with exactly the right shape at the wrong size scores a near-perfect r and
a clean Procrustes fit. Nothing in those two numbers can see it.

The amplitude ratio is the statistic that can. Define, on the centred and
rotated configurations,

    rms(X) = sqrt( mean_i ( x_i1^2 + x_i2^2 ) )

the root-mean-square radius of a configuration about its own centroid. Then

    amplitude ratio = rms(engine) / rms(reference)

so 1.0 is the same size, above 1.0 means the engine's map is inflated relative
to the reference, and below 1.0 means it is compressed. It is reported beside
the correlations for every comparison in the paper.

This is not a hypothetical safeguard. During development a defect left the
engine reproducing first-dimension maps at r = 0.9915 while its amplitude ratio
sat at 0.87. Repairing it moved the amplitude to 0.96 and moved the correlation
the WRONG way, to 0.9907. A check built on the correlation alone would have
passed the defective build and failed the repaired one; the amplitude ratio is
what saw the repair.

FRAMES
------
`--frame global` (default) fits ONE rotation to all (legislator, period) rows
stacked together. This is the frame a trajectory claim lives in, and it is the
frame the paper's dynamic rows are reported in.

`--frame period` fits one rotation per period and aggregates. Per-period
rotation hides cross-period disagreement, so it answers a cross-sectional
question, not a trajectory one. The two are reported separately on purpose.

For a single-period (static) panel the two frames are identical by construction.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = {"legislator_id", "period", "coord1D", "coord2D"} - set(frame.columns)
    if missing:
        sys.exit(f"{path}: missing column(s) {sorted(missing)}")
    frame = frame.rename(columns={"coord1D": "d1", "coord2D": "d2"})
    return frame[["legislator_id", "period", "d1", "d2"]].dropna()


def procrustes_noscale(reference: np.ndarray, engine: np.ndarray):
    """Rotate/reflect `engine` onto `reference`. Orthogonal only, no scaling.

    Returns the centred reference and the centred, rotated engine, so that a
    size difference between them survives the alignment and can be measured.
    """
    ref_c = reference - reference.mean(axis=0)
    eng_c = engine - engine.mean(axis=0)
    u, _, vt = np.linalg.svd(eng_c.T @ ref_c)
    return ref_c, eng_c @ (u @ vt)


def agreement(reference: np.ndarray, engine: np.ndarray) -> dict:
    ref_c, eng_r = procrustes_noscale(reference, engine)
    rms_ref = float(np.sqrt((ref_c ** 2).sum(axis=1).mean()))
    rms_eng = float(np.sqrt((eng_r ** 2).sum(axis=1).mean()))
    return {
        "n": int(len(ref_c)),
        "r1": float(np.corrcoef(ref_c[:, 0], eng_r[:, 0])[0, 1]),
        "r2": float(np.corrcoef(ref_c[:, 1], eng_r[:, 1])[0, 1]),
        "mean_2d_distance": float(np.mean(np.sqrt(((ref_c - eng_r) ** 2).sum(axis=1)))),
        "amplitude_ratio": rms_eng / rms_ref if rms_ref > 0 else float("nan"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--frame", choices=("global", "period"), default="global")
    parser.add_argument("--csv-out", type=Path, default=None)
    args = parser.parse_args()

    ref, eng = load(args.reference), load(args.engine)
    merged = ref.merge(eng, on=["legislator_id", "period"], suffixes=("_ref", "_eng"))
    dropped = max(len(ref), len(eng)) - len(merged)
    if merged.empty:
        sys.exit("no (legislator_id, period) rows in common")

    ref_xy = merged[["d1_ref", "d2_ref"]].to_numpy()
    eng_xy = merged[["d1_eng", "d2_eng"]].to_numpy()

    rows = []
    if args.frame == "global":
        rows.append({"period": "all", **agreement(ref_xy, eng_xy)})
    else:
        for period, block in merged.groupby("period", sort=True):
            if len(block) < 3:
                print(f"period {period}: skipped, only {len(block)} matched rows")
                continue
            rows.append({"period": period,
                         **agreement(block[["d1_ref", "d2_ref"]].to_numpy(),
                                     block[["d1_eng", "d2_eng"]].to_numpy())})

    out = pd.DataFrame(rows)
    print(f"frame={args.frame}  matched rows={len(merged)}  dropped={dropped}")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(out.to_string(index=False,
                            float_format=lambda v: f"{v:.4f}"))

    if args.csv_out:
        args.csv_out.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(args.csv_out, index=False)
        print(f"\nwrote {args.csv_out}")


if __name__ == "__main__":
    main()
