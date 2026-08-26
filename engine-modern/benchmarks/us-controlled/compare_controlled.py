#!/usr/bin/env python3
"""Compare controlled Fortran/C++ outputs and cross-evaluate their likelihood."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.special import log_ndtr


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, required=True)
    parser.add_argument("--fortran-dir", type=Path, required=True)
    parser.add_argument("--cpp-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def read_summary(path: Path) -> dict[str, float]:
    frame = pd.read_csv(path)
    result: dict[str, float] = {}
    for key, value in zip(frame["parameter"], frame["value"]):
        try:
            result[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def procrustes(cpp: np.ndarray, fortran: np.ndarray) -> np.ndarray:
    cpp_mean = cpp.mean(axis=0)
    fortran_mean = fortran.mean(axis=0)
    u, _, vt = np.linalg.svd((cpp - cpp_mean).T @ (fortran - fortran_mean))
    return (cpp - cpp_mean) @ (u @ vt) + fortran_mean


def likelihood(
    benchmark_dir: Path,
    coordinates: pd.DataFrame,
    bills: pd.DataFrame,
    w2: float,
    beta: float,
) -> tuple[float, int, float]:
    total_ll = 0.0
    total_votes = 0
    total_correct = 0
    weight_squared = np.array([1.0, w2 * w2])

    for period in range(1, 6):
        votes = pd.read_csv(
            benchmark_dir / "cpp_input" / f"votes_matrix_p{period}.csv",
            index_col=0,
        )
        votes.index = votes.index.astype(int)
        period_coords = coordinates[coordinates["period"] == period].set_index("id")
        common_ids = votes.index.intersection(period_coords.index)
        votes = votes.loc[common_ids]
        x = period_coords.loc[common_ids, ["x1", "x2"]].to_numpy(dtype=float)
        period_bills = bills[bills["period"] == period].sort_values("bill")
        if len(period_bills) != votes.shape[1]:
            raise ValueError(f"bill count mismatch in period {period}")

        for column, bill in enumerate(period_bills.itertuples(index=False)):
            codes = votes.iloc[:, column].to_numpy(dtype=int)
            observed = (codes == 1) | (codes == 6)
            yes = int((codes == 1).sum())
            no = int((codes == 6).sum())
            if yes + no == 0 or min(yes, no) / (yes + no) < 0.025:
                continue

            midpoint = np.array([bill.m1, bill.m2], dtype=float)
            spread = np.array([bill.s1, bill.s2], dtype=float)
            dist_yes = (x - midpoint + spread) ** 2
            dist_no = (x - midpoint - spread) ** 2
            utility_yes = -(dist_yes * weight_squared).sum(axis=1)
            utility_no = -(dist_no * weight_squared).sum(axis=1)
            z_yes = beta * (np.exp(utility_yes) - np.exp(utility_no))
            signed_z = np.where(codes == 1, z_yes, -z_yes)
            signed_z = signed_z[observed]
            total_ll += float(log_ndtr(signed_z).sum())
            total_votes += int(observed.sum())
            total_correct += int((signed_z > 0.0).sum())

    return total_ll, total_votes, total_correct / total_votes


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    fort = pd.read_csv(args.fortran_dir / "fortran_coordinates_controlled.csv")
    fort = fort.rename(
        columns={"session": "period", "ID": "id", "coord1D": "f1", "coord2D": "f2"}
    )
    cpp = pd.read_csv(args.cpp_dir / "cpp_coordinates_all_periods.csv")
    cpp = cpp.rename(
        columns={"legislator_id": "id", "coord1D": "c1", "coord2D": "c2"}
    )
    merged = fort[["period", "id", "party", "name", "f1", "f2"]].merge(
        cpp[["period", "id", "c1", "c2"]], on=["period", "id"], how="inner"
    )
    aligned = procrustes(
        merged[["c1", "c2"]].to_numpy(), merged[["f1", "f2"]].to_numpy()
    )
    merged[["ca1", "ca2"]] = aligned
    merged["dx"] = merged["ca1"] - merged["f1"]
    merged["dy"] = merged["ca2"] - merged["f2"]
    merged["distance"] = np.hypot(merged["dx"], merged["dy"])

    rows = []
    for period, group in merged.groupby("period"):
        rows.append(
            {
                "period": period,
                "congress": 110 + period,
                "n": len(group),
                "r1": np.corrcoef(group["ca1"], group["f1"])[0, 1],
                "r2": np.corrcoef(group["ca2"], group["f2"])[0, 1],
                "mean_distance": group["distance"].mean(),
                "median_distance": group["distance"].median(),
                "p90_distance": group["distance"].quantile(0.9),
                "max_distance": group["distance"].max(),
            }
        )
    comparison = pd.DataFrame(rows)

    fort_bills = pd.read_csv(
        args.fortran_dir / "fortran_bill_parameters_controlled.csv"
    ).rename(
        columns={
            "session": "period",
            "ID": "bill",
            "midpoint1D": "m1",
            "midpoint2D": "m2",
            "spread1D": "s1",
            "spread2D": "s2",
        }
    )
    cpp_bills_raw = pd.read_csv(args.cpp_dir / "cpp_bill_parameters.csv")
    bill_counts = [
        pd.read_csv(
            args.benchmark_dir / "cpp_input" / f"votes_matrix_p{period}.csv",
            nrows=0,
        ).shape[1]
        - 1
        for period in range(1, 6)
    ]
    cpp_bill_rows = []
    offset = 0
    for period, count in enumerate(bill_counts, start=1):
        block = cpp_bills_raw.iloc[offset : offset + count].copy()
        block["period"] = period
        block["bill"] = np.arange(1, count + 1)
        cpp_bill_rows.append(block)
        offset += count
    cpp_bills = pd.concat(cpp_bill_rows, ignore_index=True).rename(
        columns={
            "midpoint1D": "m1",
            "midpoint2D": "m2",
            "spread1D": "s1",
            "spread2D": "s2",
        }
    )

    fort_coords = fort.rename(columns={"f1": "x1", "f2": "x2"})
    cpp_coords = cpp.rename(columns={"c1": "x1", "c2": "x2"})
    fort_summary = read_summary(args.fortran_dir / "fortran_summary_controlled.csv")
    cpp_summary = read_summary(args.cpp_dir / "cpp_summary.csv")
    fort_ll, fort_votes, fort_accuracy = likelihood(
        args.benchmark_dir,
        fort_coords,
        fort_bills[["period", "bill", "m1", "m2", "s1", "s2"]],
        fort_summary["w2"],
        fort_summary["beta"],
    )
    cpp_ll, cpp_votes, cpp_accuracy = likelihood(
        args.benchmark_dir,
        cpp_coords,
        cpp_bills[["period", "bill", "m1", "m2", "s1", "s2"]],
        cpp_summary["w2"],
        cpp_summary["beta"],
    )
    objective = pd.DataFrame(
        [
            {"implementation": "Fortran", "common_log_likelihood": fort_ll,
             "votes": fort_votes, "accuracy": fort_accuracy,
             "w2": fort_summary["w2"], "beta": fort_summary["beta"]},
            {"implementation": "C++", "common_log_likelihood": cpp_ll,
             "votes": cpp_votes, "accuracy": cpp_accuracy,
             "w2": cpp_summary["w2"], "beta": cpp_summary["beta"]},
        ]
    )

    comparison.to_csv(args.output_dir / "controlled_coordinate_metrics.csv", index=False)
    objective.to_csv(args.output_dir / "controlled_common_objective.csv", index=False)
    merged.to_csv(args.output_dir / "controlled_displacements.csv", index=False)

    colors = {"D": "#2878b5", "R": "#cf4f43", "I": "#7768ad"}
    fig, axes = plt.subplots(2, 3, figsize=(14, 9), dpi=160)
    for period, axis in zip(range(1, 6), axes.ravel()):
        group = merged[merged["period"] == period]
        axis.add_patch(plt.Circle((0, 0), 1, fill=False, linestyle="--", color="0.5"))
        for item in group.itertuples():
            color = colors.get(str(item.party), "#777777")
            axis.annotate(
                "", xy=(item.ca1, item.ca2), xytext=(item.f1, item.f2),
                arrowprops={"arrowstyle": "->", "lw": 0.55, "color": color, "alpha": 0.5}
            )
            axis.scatter(item.f1, item.f2, s=8, color=color, zorder=3)
        axis.axhline(0, linewidth=0.5, color="0.75")
        axis.axvline(0, linewidth=0.5, color="0.75")
        axis.set(xlim=(-1.3, 1.3), ylim=(-1.3, 1.3), aspect="equal",
                 title=f"Congress {110 + period}", xlabel="Dimension 1", ylabel="Dimension 2")
        axis.grid(alpha=0.15)
    axes.ravel()[-1].axis("off")
    fig.tight_layout()
    fig.savefig(args.output_dir / "controlled_displacements.png")

    print(comparison.to_string(index=False))
    print("\nCommon objective evaluation")
    print(objective.to_string(index=False))


if __name__ == "__main__":
    main()
