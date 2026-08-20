#!/usr/bin/env python3
"""End-to-end check for early stopping and served-period export semantics."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def summary(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["parameter"]: row["value"] for row in csv.DictReader(handle)}


def main() -> int:
    binary, input_dir, output_dir = map(Path, sys.argv[1:4])
    command = [
        str(binary),
        f"--input-dir={input_dir}",
        f"--output-dir={output_dir}",
        f"--wnominate={input_dir / 'wnominate_coordinates.csv'}",
        "--model=0",
        "--periods=1",
        "--dimensions=2",
        "--iterations=6",
        "--min-iterations=2",
        "--convergence-abs=1e100",
        "--convergence-patience=2",
        "--block-solver=slsqp",
        "--scalar-search=local",
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)

    values = summary(output_dir / "cpp_summary.csv")
    if values["converged"] != "1" or int(values["iterations"]) != 3:
        raise AssertionError(f"unexpected stopping state: {values}")

    with (output_dir / "cpp_coordinates_all_periods_corrected.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        corrected = list(csv.DictReader(handle))
    keys = {(row["legislator_id"], row["period"]) for row in corrected}
    if len(keys) != len(corrected):
        raise AssertionError("corrected export contains duplicate served keys")
    if any(row["period"] != "1" for row in corrected):
        raise AssertionError("static export contains an impossible period")

    with (output_dir / "cpp_temporal_coefficients.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        coefficients = list(csv.DictReader(handle))
    if not coefficients:
        raise AssertionError("temporal coefficient export is empty")
    for row in coefficients:
        if float(row["intercept_radius"]) > 1.0 + 1e-9:
            raise AssertionError("exported legislator intercept is infeasible")
        for term in ("beta1", "beta2", "beta3"):
            if abs(float(row[f"{term}_dim1"])) > 1e-12 or abs(
                float(row[f"{term}_dim2"])
            ) > 1e-12:
                raise AssertionError("static model exported an active temporal term")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
