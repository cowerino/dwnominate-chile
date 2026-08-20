#!/usr/bin/env python3
"""A dynamic export must reload to the exact likelihood that produced it."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def read_summary(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["parameter"]: row["value"] for row in csv.DictReader(handle)}


def bill_counts(input_dir: Path, periods: int) -> list[int]:
    counts: list[int] = []
    for period in range(1, periods + 1):
        with (input_dir / f"votes_matrix_p{period}.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            counts.append(len(next(csv.reader(handle))) - 1)
    return counts


def stage_bills(source: Path, destination: Path, counts: list[int]) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != sum(counts):
        raise AssertionError("bill count mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        fields = ["session", "ID", "midpoint1D", "midpoint2D", "spread1D", "spread2D"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        offset = 0
        for session, count in enumerate(counts, start=1):
            for local_id, row in enumerate(rows[offset : offset + count], start=1):
                writer.writerow(
                    {
                        "session": session,
                        "ID": local_id,
                        "midpoint1D": row["midpoint1D"],
                        "midpoint2D": row["midpoint2D"],
                        "spread1D": row["spread1D"],
                        "spread2D": row["spread2D"],
                    }
                )
            offset += count


def main() -> int:
    binary, input_dir, work = map(Path, sys.argv[1:4])
    fitted = work / "fitted"
    reloaded = work / "reloaded"
    common = [
        str(binary),
        f"--input-dir={input_dir}",
        f"--wnominate={input_dir / 'wnominate_coordinates.csv'}",
        "--model=1",
        "--periods=5",
        "--dimensions=2",
    ]
    subprocess.run(
        common
        + [
            f"--output-dir={fitted}",
            "--iterations=2",
            "--block-solver=slsqp",
            "--scalar-search=local",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    fitted_summary = read_summary(fitted / "cpp_summary.csv")
    staged = work / "staging" / "dwnominate_bill_parameters.csv"
    stage_bills(fitted / "cpp_bill_parameters.csv", staged, bill_counts(input_dir, 5))
    subprocess.run(
        common
        + [
            f"--output-dir={reloaded}",
            f"--seed-per-period={fitted / 'cpp_coordinates_all_periods.csv'}",
            f"--bill-params={staged}",
            f"--beta={fitted_summary['beta']}",
            f"--w2={fitted_summary['w2']}",
            "--iterations=1",
            "--evaluate-only",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    reloaded_summary = read_summary(reloaded / "cpp_summary.csv")
    difference = abs(
        float(fitted_summary["log_likelihood"])
        - float(reloaded_summary["log_likelihood"])
    )
    if difference > 1e-8:
        raise AssertionError(f"dynamic state reload changed LL by {difference}")
    with (fitted / "cpp_coordinates_all_periods_corrected.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        if len(list(csv.DictReader(handle))) != 523:
            raise AssertionError("US served-period export must contain 523 rows")
    with (fitted / "cpp_temporal_coefficients.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        coefficients = list(csv.DictReader(handle))
    if len(coefficients) != 168:
        raise AssertionError("US coefficient export must contain 168 legislators")
    if any(float(row["intercept_radius"]) > 1.0 + 1e-9 for row in coefficients):
        raise AssertionError("dynamic coefficient export contains an infeasible intercept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
