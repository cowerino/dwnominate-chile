#!/usr/bin/env python3
"""Run the committed Chile static and US five-period regression panels.

The checks deliberately combine likelihood, classification, parameter scale,
geometry, unit-ball invariants, and repeatability. Correlation alone is not a
sufficient regression oracle for a non-convex NOMINATE fit.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


STATIC_LIMITS = {
    353: {"ll_min": -1150.0, "classification_min": 93.7},
    366: {"ll_min": -6100.0, "classification_min": 94.5},
    368: {"ll_min": -13300.0, "classification_min": 94.0},
}


def read_summary(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row[0]: row[1] for row in list(csv.reader(handle))[1:]}


def run_engine(binary: Path, input_dir: Path, output_dir: Path, periods: int | None,
               model: int) -> dict[str, str]:
    command = [
        str(binary),
        f"--input-dir={input_dir}",
        f"--output-dir={output_dir}",
        f"--wnominate={input_dir / 'wnominate_coordinates.csv'}",
        "--dimensions=2",
        "--iterations=4",
        f"--model={model}",
        "--threads=1",
        "--optimizer-precision=standard",
        "--block-solver=slsqp",
        "--scalar-search=local",
    ]
    if periods is not None:
        command.append(f"--periods={periods}")
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"engine failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return read_summary(output_dir / "cpp_summary.csv")


def assert_static_geometry(output_dir: Path) -> None:
    coordinates = pd.read_csv(output_dir / "cpp_coordinates_all_periods.csv")
    bills = pd.read_csv(output_dir / "cpp_bill_parameters.csv")
    coordinate_radius = np.hypot(coordinates.coord1D, coordinates.coord2D)
    midpoint_radius = np.hypot(bills.midpoint1D, bills.midpoint2D)
    if coordinate_radius.max() > 1.0 + 1e-9:
        raise AssertionError(f"static coordinate escaped unit ball: {coordinate_radius.max()}")
    if midpoint_radius.max() > 1.0 + 1e-9:
        raise AssertionError(f"bill midpoint escaped unit ball: {midpoint_radius.max()}")


def procrustes_score(cpp: pd.DataFrame, reference: pd.DataFrame) -> tuple[float, float, float, float]:
    merged = cpp.merge(reference, on=["id", "period"], suffixes=("_c", "_f"))
    a = merged[["coord1D_c", "coord2D_c"]].to_numpy()
    b = merged[["coord1D_f", "coord2D_f"]].to_numpy()
    ac = a - a.mean(axis=0)
    bc = b - b.mean(axis=0)
    u, _, vt = np.linalg.svd(ac.T @ bc)
    aligned = ac @ (u @ vt)
    r1 = float(np.corrcoef(aligned[:, 0], bc[:, 0])[0, 1])
    r2 = float(np.corrcoef(aligned[:, 1], bc[:, 1])[0, 1])
    scale2 = float(aligned[:, 1].std() / bc[:, 1].std())
    distance = float(np.linalg.norm(aligned - bc, axis=1).mean())
    return r1, r2, scale2, distance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()

    binary = args.binary.resolve()
    root = args.repo_root.resolve()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"static": {}, "dynamic": {}}

    for legislature, limits in STATIC_LIMITS.items():
        input_dir = root / "data" / "chile-static" / f"leg{legislature}"
        output_dir = work / f"chile-{legislature}"
        # periods=None intentionally tests votes_matrix.csv auto-detection.
        summary = run_engine(binary, input_dir, output_dir, periods=None, model=0)
        ll = float(summary["log_likelihood"])
        classification = float(summary["classification_pct"])
        beta = float(summary["beta"])
        w2 = float(summary["w2"])
        if ll < limits["ll_min"]:
            raise AssertionError(f"leg{legislature}: LL regression {ll}")
        if classification < limits["classification_min"]:
            raise AssertionError(f"leg{legislature}: classification regression {classification}")
        if not (5.0 <= beta <= 8.0 and 0.4 <= w2 <= 0.7):
            raise AssertionError(f"leg{legislature}: scale drift beta={beta}, w2={w2}")
        assert_static_geometry(output_dir)
        report["static"][str(legislature)] = {
            "log_likelihood": ll,
            "classification_pct": classification,
            "beta": beta,
            "w2": w2,
        }

    # A second serial run must reproduce all scientific outputs. Timing
    # telemetry is intentionally excluded from the byte comparison.
    repeat_dir = work / "chile-353-repeat"
    run_engine(
        binary,
        root / "data" / "chile-static" / "leg353",
        repeat_dir,
        periods=None,
        model=0,
    )
    for filename in (
        "cpp_coordinates_all_periods.csv",
        "cpp_coordinates_all_periods_corrected.csv",
        "cpp_bill_parameters.csv",
        "cpp_convergence_trace.csv",
    ):
        if (work / "chile-353" / filename).read_bytes() != (repeat_dir / filename).read_bytes():
            raise AssertionError(f"non-deterministic scientific output: {filename}")

    us_dir = root / "engine-faithful" / "benchmarks" / "us"
    dynamic_out = work / "us5"
    dynamic_summary = run_engine(
        binary, us_dir / "cpp_input", dynamic_out, periods=5, model=1
    )
    ll = float(dynamic_summary["log_likelihood"])
    classification = float(dynamic_summary["classification_pct"])
    beta = float(dynamic_summary["beta"])
    w2 = float(dynamic_summary["w2"])
    if ll < -37500.0 or classification < 93.3:
        raise AssertionError(f"US5 fit regression: LL={ll}, classification={classification}")
    if not (5.0 <= beta <= 7.0 and 0.4 <= w2 <= 0.7):
        raise AssertionError(f"US5 scale drift: beta={beta}, w2={w2}")

    cpp = pd.read_csv(dynamic_out / "cpp_coordinates_all_periods.csv").rename(
        columns={"legislator_id": "id"}
    )
    reference = pd.read_csv(us_dir / "fortran_dwnom.csv").rename(
        columns={"ID": "id", "session": "period"}
    )
    thresholds_r2 = [0.84, 0.75, 0.65, 0.60, 0.55]
    period_scores = []
    for period, minimum_r2 in enumerate(thresholds_r2, start=1):
        score = procrustes_score(
            cpp[cpp.period == period], reference[reference.period == period]
        )
        if score[0] < 0.99 or score[1] < minimum_r2 or score[2] < 0.70:
            raise AssertionError(f"US5 period {period} geometry regression: {score}")
        period_scores.append(
            {"period": period, "r1": score[0], "r2": score[1],
             "scale2": score[2], "mean_distance": score[3]}
        )

    matched = reference[["id", "period"]].merge(cpp, on=["id", "period"])
    radius = np.hypot(matched.coord1D, matched.coord2D)
    if radius.max() > 1.30:
        raise AssertionError(f"dynamic reconstructed radius unexpectedly large: {radius.max()}")
    report["dynamic"] = {
        "log_likelihood": ll,
        "classification_pct": classification,
        "beta": beta,
        "w2": w2,
        "outside_unit_ball": int((radius > 1.0 + 1e-12).sum()),
        "max_radius": float(radius.max()),
        "period_scores": period_scores,
    }

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
