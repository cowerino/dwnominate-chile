#!/usr/bin/env python3
"""Merge exact continuation segments into one publishable convergence state."""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


STATE_FILES = (
    "cpp_coordinates_all_periods.csv",
    "cpp_coordinates_all_periods_corrected.csv",
    "cpp_bill_parameters.csv",
)


def read_summary(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("segments", nargs="+", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    merged: list[dict[str, str]] = []
    offset = 0
    total_elapsed = 0.0
    for segment in args.segments:
        with (segment / "cpp_convergence_trace.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            row["iteration"] = str(int(row["iteration"]) + offset)
            merged.append(row)
        offset += len(rows)
        values = {row["parameter"]: row["value"] for row in read_summary(segment / "cpp_summary.csv")}
        total_elapsed += float(values["elapsed_seconds"])

    final = args.segments[-1]
    for name in STATE_FILES:
        shutil.copy2(final / name, args.output / name)

    with (args.output / "cpp_convergence_trace.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=merged[0].keys())
        writer.writeheader()
        writer.writerows(merged)

    summary_rows = read_summary(final / "cpp_summary.csv")
    replacements = {
        "iterations": str(offset),
        "elapsed_seconds": f"{total_elapsed:.2f}",
    }
    for row in summary_rows:
        if row["parameter"] in replacements:
            row["value"] = replacements[row["parameter"]]
    with (args.output / "cpp_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=("parameter", "value"))
        writer.writeheader()
        writer.writerows(summary_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
