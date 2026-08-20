#!/usr/bin/env python3
"""Run the faithful C++ estimator, then polish its state with NLopt/SLSQP.

The faithful stage supplies per-period legislator coordinates, bill parameters,
and global weights. The modern stage therefore starts from the completed fast
trajectory instead of recomputing CUTPLANE or W-NOMINATE initialization.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import time
from pathlib import Path


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--faithful-binary", type=Path, required=True)
    parser.add_argument("--modern-binary", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--wnominate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--periods", type=int, required=True)
    parser.add_argument("--model", type=int, default=1)
    parser.add_argument("--faithful-iterations", type=int, default=4)
    parser.add_argument("--polish-iterations", type=int, default=1)
    parser.add_argument("--optimizer-precision", default="standard")
    parser.add_argument(
        "--scalar-search", choices=("local", "global"), default="local"
    )
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--legacy-round-starts", action="store_true")
    return parser.parse_args()


def run(command: list[str]) -> float:
    print("+", " ".join(command), flush=True)
    started = time.perf_counter()
    subprocess.run(command, check=True)
    return time.perf_counter() - started


def read_summary(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["parameter"]: row["value"] for row in csv.DictReader(handle)}


def stage_rounded_wnominate(source: Path, destination: Path) -> None:
    """Reproduce the historical three-decimal input serialization."""
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"missing CSV header: {source}")
        rows = list(reader)
        fieldnames = reader.fieldnames

    required = {"coord1D", "coord2D"}
    if not required.issubset(fieldnames):
        raise ValueError(
            f"{source} must contain coord1D and coord2D columns"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            for column in required:
                # Python's decimal formatter uses round-to-nearest/even, as
                # does the nearbyint boundary used by engine-modern.
                row[column] = format(float(row[column]), ".3f")
            writer.writerow(row)


def bill_counts(input_dir: Path, periods: int) -> list[int]:
    counts: list[int] = []
    for period in range(1, periods + 1):
        path = input_dir / f"votes_matrix_p{period}.csv"
        if period == 1 and periods == 1 and not path.exists():
            path = input_dir / "votes_matrix.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        counts.append(len(header) - 1)
    return counts


def stage_bill_parameters(
    faithful_csv: Path,
    destination: Path,
    counts: list[int],
) -> None:
    with faithful_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != sum(counts):
        raise ValueError(
            f"bill count mismatch: faithful={len(rows)}, input={sum(counts)}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "session",
                "ID",
                "midpoint1D",
                "midpoint2D",
                "spread1D",
                "spread2D",
            ]
        )
        offset = 0
        for period, count in enumerate(counts, start=1):
            for local_bill, row in enumerate(rows[offset : offset + count], start=1):
                writer.writerow(
                    [
                        period,
                        local_bill,
                        row["midpoint1D"],
                        row["midpoint2D"],
                        row["spread1D"],
                        row["spread2D"],
                    ]
                )
            offset += count


def write_hybrid_summary(
    path: Path,
    args: argparse.Namespace,
    faithful: dict[str, str],
    polished: dict[str, str],
    faithful_wall_seconds: float,
    polish_wall_seconds: float,
) -> None:
    faithful_ll = float(faithful["log_likelihood"])
    polished_ll = float(polished["log_likelihood"])
    rows = [
        ("faithful_log_likelihood", f"{faithful_ll:.12f}"),
        ("polished_log_likelihood", f"{polished_ll:.12f}"),
        ("polish_improvement", f"{polished_ll - faithful_ll:.12f}"),
        ("faithful_iterations", str(args.faithful_iterations)),
        ("polish_iterations", str(args.polish_iterations)),
        ("scalar_search", args.scalar_search),
        ("faithful_wall_seconds", f"{faithful_wall_seconds:.6f}"),
        ("polish_wall_seconds", f"{polish_wall_seconds:.6f}"),
        (
            "pipeline_wall_seconds",
            f"{faithful_wall_seconds + polish_wall_seconds:.6f}",
        ),
        ("final_w2", polished["w2"]),
        ("final_beta", polished["beta"]),
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["parameter", "value"])
        writer.writerows(rows)


def main() -> None:
    args = arguments()
    if args.output_dir.exists():
        raise FileExistsError(f"output directory already exists: {args.output_dir}")
    if args.threads < 1:
        raise ValueError("threads must be >= 1")
    for executable in (args.faithful_binary, args.modern_binary):
        if not executable.is_file():
            raise FileNotFoundError(executable)

    faithful_dir = args.output_dir / "faithful_stage"
    staging_dir = args.output_dir / "staging"
    polish_dir = args.output_dir / "nlopt_polish"
    args.output_dir.mkdir(parents=True)

    faithful_start = args.wnominate
    if args.legacy_round_starts:
        faithful_start = staging_dir / "wnominate_coordinates_rounded.csv"
        stage_rounded_wnominate(args.wnominate, faithful_start)

    faithful_command = [
        str(args.faithful_binary),
        f"--input-dir={args.input_dir}",
        f"--output-dir={faithful_dir}",
        f"--wnominate={faithful_start}",
        f"--periods={args.periods}",
        f"--model={args.model}",
        f"--iterations={args.faithful_iterations}",
    ]
    faithful_wall_seconds = run(faithful_command)

    summary = read_summary(faithful_dir / "cpp_summary.csv")
    staged_bills = staging_dir / "dwnominate_bill_parameters.csv"
    stage_bill_parameters(
        faithful_dir / "cpp_bill_parameters.csv",
        staged_bills,
        bill_counts(args.input_dir, args.periods),
    )

    # The modern loader expects this exact R-compatible basename in the parent
    # directory supplied through --bill-params.
    if not staged_bills.exists():
        raise FileNotFoundError(staged_bills)

    modern_command = [
        str(args.modern_binary),
        f"--input-dir={args.input_dir}",
        f"--output-dir={polish_dir}",
        f"--wnominate={args.wnominate}",
        f"--seed-per-period={faithful_dir / 'cpp_coordinates_all_periods.csv'}",
        f"--bill-params={staged_bills}",
        f"--periods={args.periods}",
        f"--model={args.model}",
        f"--iterations={args.polish_iterations}",
        f"--beta={summary['beta']}",
        f"--w2={summary['w2']}",
        f"--optimizer-precision={args.optimizer_precision}",
        f"--scalar-search={args.scalar_search}",
        "--block-solver=slsqp",
        f"--threads={args.threads}",
    ]
    polish_wall_seconds = run(modern_command)
    polished_summary = read_summary(polish_dir / "cpp_summary.csv")
    write_hybrid_summary(
        args.output_dir / "hybrid_summary.csv",
        args,
        summary,
        polished_summary,
        faithful_wall_seconds,
        polish_wall_seconds,
    )
    print(f"Hybrid result: {polish_dir}")


if __name__ == "__main__":
    main()
