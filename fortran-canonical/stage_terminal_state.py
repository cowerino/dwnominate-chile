#!/usr/bin/env python3
"""Normalize a modern or Fortran terminal state for the native harness."""

from __future__ import annotations

import argparse
import csv
import pathlib


def first_existing(directory: pathlib.Path, names: tuple[str, ...]) -> pathlib.Path:
    for name in names:
        path = directory / name
        if path.is_file():
            return path
    raise FileNotFoundError(f"none of {names} exists below {directory}")


def read_summary(path: pathlib.Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["parameter"]: row["value"].strip() for row in csv.DictReader(handle)}


def stage_summary(source: pathlib.Path, destination: pathlib.Path) -> None:
    values = read_summary(source)
    required = ("w2", "beta")
    missing = [key for key in required if key not in values]
    if missing:
        raise ValueError(f"summary missing {missing}: {source}")
    ordered = ["log_likelihood", "w1", "w2", "beta", "iterations"]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("parameter", "value"))
        for key in ordered:
            if key in values:
                writer.writerow((key, values[key]))


def stage_coordinates(source: pathlib.Path, destination: pathlib.Path) -> int:
    count = 0
    with source.open(newline="", encoding="utf-8") as input_handle, destination.open(
        "w", newline="", encoding="utf-8"
    ) as output_handle:
        reader = csv.DictReader(input_handle)
        writer = csv.writer(output_handle)
        writer.writerow(("legislator_id", "period", "coord1D", "coord2D"))
        for row in reader:
            writer.writerow(
                (
                    row["legislator_id"],
                    row["period"],
                    row["coord1D"],
                    row["coord2D"],
                )
            )
            count += 1
    return count


def stage_bills(source: pathlib.Path, destination: pathlib.Path) -> int:
    count = 0
    with source.open(newline="", encoding="utf-8") as input_handle, destination.open(
        "w", newline="", encoding="utf-8"
    ) as output_handle:
        reader = csv.DictReader(input_handle)
        writer = csv.writer(output_handle)
        writer.writerow(
            ("rollcall_id", "midpoint1D", "midpoint2D", "spread1D", "spread2D")
        )
        for index, row in enumerate(reader):
            rollcall_id = row.get("rollcall_id", str(index))
            writer.writerow(
                (
                    rollcall_id,
                    row["midpoint1D"],
                    row["midpoint2D"],
                    row["spread1D"],
                    row["spread2D"],
                )
            )
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--expected-coordinates", type=int)
    parser.add_argument("--expected-bills", type=int)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)

    summary = first_existing(args.state_dir, ("summary.csv", "cpp_summary.csv"))
    coordinates = first_existing(
        args.state_dir, ("coordinates.csv", "cpp_coordinates_all_periods.csv")
    )
    bills = first_existing(
        args.state_dir,
        ("bill_parameters.csv", "cpp_bill_parameters.csv", "dwnominate_bill_parameters.csv"),
    )

    stage_summary(summary, args.output_dir / "summary.csv")
    coordinate_count = stage_coordinates(coordinates, args.output_dir / "coordinates.csv")
    bill_count = stage_bills(bills, args.output_dir / "bill_parameters.csv")

    if args.expected_coordinates is not None and coordinate_count != args.expected_coordinates:
        raise ValueError(
            f"coordinate count {coordinate_count} != {args.expected_coordinates}"
        )
    if args.expected_bills is not None and bill_count != args.expected_bills:
        raise ValueError(f"bill count {bill_count} != {args.expected_bills}")

    with (args.output_dir / "manifest.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(("item", "value"))
        writer.writerow(("source_state", args.state_dir.resolve()))
        writer.writerow(("source_summary", summary.resolve()))
        writer.writerow(("source_coordinates", coordinates.resolve()))
        writer.writerow(("source_bills", bills.resolve()))
        writer.writerow(("coordinates", coordinate_count))
        writer.writerow(("bills", bill_count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
