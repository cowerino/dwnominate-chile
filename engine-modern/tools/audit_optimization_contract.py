#!/usr/bin/env python3
"""Audit optimizer feasibility, common-objective fit, and reference equivalence.

The framework deliberately separates questions that correlations often blur:

1. Did the optimizer return a point satisfying every declared constraint?
2. Did it evaluate the likelihood at infeasible internal trial points?
3. Does a terminal state improve one common likelihood evaluator?
4. Is the modern state numerically the same as the reference state?
5. Are Chilean displacements concentrated among members with few votes?

The default reference runner is engine-faithful, which is a reproducible C++
proxy for the Fortran trajectory. An actual Fortran export can be supplied as a
standardized output root containing one ``legNNN`` directory per panel with
``cpp_coordinates_all_periods.csv``, ``cpp_bill_parameters.csv``, and
``cpp_summary.csv``. The report always records which reference was used.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PANELS = (353, 366, 368)
VOTE_BINS = (-1, 24, 49, 99, 199, math.inf)
VOTE_LABELS = ("1-24", "25-49", "50-99", "100-199", "200+")
BILL_PARAMETER_COLUMNS = (
    "midpoint1D",
    "midpoint2D",
    "spread1D",
    "spread2D",
)


def read_summary(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["parameter"]: row["value"] for row in csv.DictReader(handle)}


def run_checked(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def run_engine(
    binary: Path,
    input_dir: Path,
    output_dir: Path,
    iterations: int,
    modern: bool,
) -> None:
    command = [
        str(binary),
        f"--input-dir={input_dir}",
        f"--output-dir={output_dir}",
        f"--wnominate={input_dir / 'wnominate_coordinates.csv'}",
        "--periods=1",
        "--model=0",
        "--dimensions=2",
        f"--iterations={iterations}",
    ]
    if modern:
        command.extend(
            [
                "--threads=1",
                "--optimizer-precision=standard",
                "--block-solver=slsqp",
                "--scalar-search=local",
            ]
        )
    run_checked(command)


def vote_files(input_dir: Path, periods: int) -> list[Path]:
    paths = []
    for period in range(1, periods + 1):
        path = input_dir / f"votes_matrix_p{period}.csv"
        if periods == 1 and period == 1 and not path.exists():
            path = input_dir / "votes_matrix.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        paths.append(path)
    return paths


def bill_counts(input_dir: Path, periods: int) -> list[int]:
    counts = []
    for path in vote_files(input_dir, periods):
        with path.open(newline="", encoding="utf-8") as handle:
            counts.append(len(next(csv.reader(handle))) - 1)
    return counts


def stage_bill_parameters(
    source: Path, destination: Path, counts: list[int]
) -> None:
    rows = pd.read_csv(source)
    if len(rows) != sum(counts):
        raise AssertionError(
            f"bill count mismatch for {source}: {len(rows)} != {sum(counts)}"
        )
    required = set(BILL_PARAMETER_COLUMNS)
    if not required.issubset(rows.columns):
        raise AssertionError(f"missing bill columns in {source}")
    # The R wrapper serializes an unestimated all-zero roll call as NA. The C++
    # engines use the equivalent explicit zero row.
    columns = list(BILL_PARAMETER_COLUMNS)
    rows[columns] = rows[columns].apply(
        pd.to_numeric, errors="coerce"
    ).fillna(0.0)

    staged: list[dict[str, Any]] = []
    offset = 0
    for period, count in enumerate(counts, start=1):
        for local_id, (_, row) in enumerate(
            rows.iloc[offset : offset + count].iterrows(), start=1
        ):
            staged.append(
                {
                    "session": period,
                    "ID": local_id,
                    "midpoint1D": row.midpoint1D,
                    "midpoint2D": row.midpoint2D,
                    "spread1D": row.spread1D,
                    "spread2D": row.spread2D,
                }
            )
        offset += count
    destination.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(staged).to_csv(destination, index=False, float_format="%.15g")


def evaluate_terminal_state(
    modern_binary: Path,
    input_dir: Path,
    state_dir: Path,
    output_dir: Path,
    staging_dir: Path,
    periods: int,
    model: int,
) -> dict[str, str]:
    summary = read_summary(state_dir / "cpp_summary.csv")
    staged_bills = staging_dir / "dwnominate_bill_parameters.csv"
    stage_bill_parameters(
        state_dir / "cpp_bill_parameters.csv",
        staged_bills,
        bill_counts(input_dir, periods),
    )
    command = [
        str(modern_binary),
        f"--input-dir={input_dir}",
        f"--output-dir={output_dir}",
        f"--wnominate={input_dir / 'wnominate_coordinates.csv'}",
        f"--seed-per-period={state_dir / 'cpp_coordinates_all_periods.csv'}",
        f"--bill-params={staged_bills}",
        f"--beta={summary['beta']}",
        f"--w2={summary['w2']}",
        f"--periods={periods}",
        f"--model={model}",
        "--iterations=1",
        "--threads=1",
        "--evaluate-only",
    ]
    run_checked(command)
    return read_summary(output_dir / "cpp_summary.csv")


def coordinate_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = ("legislator_id", "period", "coord1D", "coord2D")
    if not set(columns).issubset(frame.columns):
        raise AssertionError(f"missing coordinate columns in {path}")
    return frame[list(columns)].copy()


def compare_terminal_parameters(
    modern_dir: Path,
    reference_dir: Path,
) -> dict[str, float]:
    modern_coordinates = coordinate_frame(
        modern_dir / "cpp_coordinates_all_periods.csv"
    )
    reference_coordinates = coordinate_frame(
        reference_dir / "cpp_coordinates_all_periods.csv"
    )
    coordinates = modern_coordinates.merge(
        reference_coordinates,
        on=["legislator_id", "period"],
        suffixes=("_modern", "_reference"),
        validate="one_to_one",
    )
    if len(coordinates) != len(modern_coordinates) or len(coordinates) != len(
        reference_coordinates
    ):
        raise AssertionError("coordinate states do not contain identical keys")
    coordinate_delta = coordinates[
        ["coord1D_modern", "coord2D_modern"]
    ].to_numpy() - coordinates[
        ["coord1D_reference", "coord2D_reference"]
    ].to_numpy()

    modern_bills = pd.read_csv(modern_dir / "cpp_bill_parameters.csv")
    reference_bills = pd.read_csv(reference_dir / "cpp_bill_parameters.csv")
    required_bills = {"rollcall_id", *BILL_PARAMETER_COLUMNS}
    modern_has_bills = required_bills.issubset(modern_bills.columns)
    reference_has_bills = required_bills.issubset(reference_bills.columns)
    if not modern_has_bills or not reference_has_bills:
        raise AssertionError("bill-parameter state lacks required columns")
    bill_columns = list(BILL_PARAMETER_COLUMNS)
    modern_bills[bill_columns] = modern_bills[bill_columns].apply(
        pd.to_numeric, errors="coerce"
    ).fillna(0.0)
    reference_bills[bill_columns] = reference_bills[bill_columns].apply(
        pd.to_numeric, errors="coerce"
    ).fillna(0.0)
    bills = modern_bills.merge(
        reference_bills,
        on="rollcall_id",
        suffixes=("_modern", "_reference"),
        validate="one_to_one",
    )
    if len(bills) != len(modern_bills) or len(bills) != len(reference_bills):
        raise AssertionError("bill states do not contain identical keys")
    bill_differences = np.column_stack(
        [
            (bills[f"{column}_modern"] - bills[f"{column}_reference"]).to_numpy()
            for column in BILL_PARAMETER_COLUMNS
        ]
    )

    modern_summary = read_summary(modern_dir / "cpp_summary.csv")
    reference_summary = read_summary(reference_dir / "cpp_summary.csv")
    return {
        "max_raw_coordinate_component_difference": float(
            np.abs(coordinate_delta).max()
        ),
        "max_raw_coordinate_distance": float(
            np.linalg.norm(coordinate_delta, axis=1).max()
        ),
        "max_raw_bill_parameter_difference": float(
            np.abs(bill_differences).max()
        ),
        "beta_difference": abs(
            float(modern_summary["beta"])
            - float(reference_summary["beta"])
        ),
        "w2_difference": abs(
            float(modern_summary["w2"])
            - float(reference_summary["w2"])
        ),
    }


def align_coordinates(
    modern: pd.DataFrame, reference: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, float]]:
    merged = modern.merge(
        reference,
        on=["legislator_id", "period"],
        suffixes=("_modern", "_reference"),
    )
    if merged.empty:
        raise AssertionError("modern/reference coordinate merge is empty")

    modern_values = merged[["coord1D_modern", "coord2D_modern"]].to_numpy()
    reference_values = merged[
        ["coord1D_reference", "coord2D_reference"]
    ].to_numpy()
    modern_center = modern_values.mean(axis=0)
    reference_center = reference_values.mean(axis=0)
    centered_modern = modern_values - modern_center
    centered_reference = reference_values - reference_center
    u, _, vt = np.linalg.svd(centered_modern.T @ centered_reference)
    rotation = u @ vt
    aligned = centered_modern @ rotation + reference_center
    displacement = np.linalg.norm(aligned - reference_values, axis=1)
    raw_displacement = np.linalg.norm(modern_values - reference_values, axis=1)

    merged["alignedCoord1D"] = aligned[:, 0]
    merged["alignedCoord2D"] = aligned[:, 1]
    merged["displacement"] = displacement
    merged["rawDisplacement"] = raw_displacement
    r1 = float(np.corrcoef(aligned[:, 0], reference_values[:, 0])[0, 1])
    r2 = float(np.corrcoef(aligned[:, 1], reference_values[:, 1])[0, 1])
    scale1 = float(aligned[:, 0].std() / reference_values[:, 0].std())
    scale2 = float(aligned[:, 1].std() / reference_values[:, 1].std())
    metrics = {
        "matched_coordinates": int(len(merged)),
        "raw_max_distance": float(raw_displacement.max()),
        "aligned_mean_distance": float(displacement.mean()),
        "aligned_median_distance": float(np.median(displacement)),
        "aligned_max_distance": float(displacement.max()),
        "r1": r1,
        "r2": r2,
        "scale1": scale1,
        "scale2": scale2,
    }
    return merged, metrics


def parse_vote(value: object) -> bool:
    if pd.isna(value):
        return False
    try:
        numeric = float(str(value).strip())
    except ValueError:
        return False
    return 1.0 <= numeric <= 6.0


def member_vote_counts(input_dir: Path) -> pd.DataFrame:
    votes = pd.read_csv(vote_files(input_dir, 1)[0])
    id_column = votes.columns[0]
    observed = votes.iloc[:, 1:].apply(lambda column: column.map(parse_vote))
    counts = observed.sum(axis=1).astype(int)
    return pd.DataFrame(
        {
            "legislator_id": pd.to_numeric(votes[id_column], errors="coerce"),
            "vote_count": counts,
        }
    ).dropna(subset=["legislator_id"])


def vote_bin_rows(
    legislature: int,
    aligned: pd.DataFrame,
    counts: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    merged = aligned.merge(counts, on="legislator_id", how="left")
    merged["vote_bin"] = pd.cut(
        merged.vote_count,
        bins=VOTE_BINS,
        labels=VOTE_LABELS,
    )
    rows: list[dict[str, Any]] = []
    for label in VOTE_LABELS:
        subset = merged[merged.vote_bin == label]
        if subset.empty:
            continue
        rows.append(
            {
                "legislature": legislature,
                "vote_bin": label,
                "members": int(len(subset)),
                "mean_votes": float(subset.vote_count.mean()),
                "mean_displacement": float(subset.displacement.mean()),
                "median_displacement": float(subset.displacement.median()),
                "max_displacement": float(subset.displacement.max()),
            }
        )

    rank_votes = merged.vote_count.rank(method="average").to_numpy()
    rank_distance = merged.displacement.rank(method="average").to_numpy()
    spearman = (
        float(np.corrcoef(rank_votes, rank_distance)[0, 1])
        if len(merged) > 1
        else math.nan
    )
    profile = {
        "active_members": int((counts.vote_count > 0).sum()),
        "members_below_25_votes": int((counts.vote_count.between(1, 24)).sum()),
        "share_below_25_votes": float(
            (counts.vote_count.between(1, 24)).sum()
            / max(1, (counts.vote_count > 0).sum())
        ),
        "median_votes_per_active_member": float(
            counts.loc[counts.vote_count > 0, "vote_count"].median()
        ),
        "spearman_votes_vs_displacement": spearman,
    }
    return rows, profile


def input_profile(path: Path) -> dict[str, Any]:
    votes = pd.read_csv(path)
    observed = votes.iloc[:, 1:].apply(lambda column: column.map(parse_vote))
    counts = observed.sum(axis=1)
    active = counts[counts > 0]
    return {
        "active_members": int(len(active)),
        "roll_calls": int(observed.shape[1]),
        "median_votes_per_active_member": float(active.median()),
        "members_below_25_votes": int((active < 25).sum()),
        "share_below_25_votes": float((active < 25).mean()),
    }


def audit_trace(path: Path, acceptance_tolerance: float) -> dict[str, Any]:
    trace = pd.read_csv(path)
    required = {
        "attempted",
        "accepted",
        "raw_return_feasible",
        "constraint_tolerance",
        "raw_constraint_violation",
        "improvement",
        "infeasible_objective_evaluations",
        "max_objective_constraint_violation",
    }
    if not required.issubset(trace.columns):
        raise AssertionError(f"optimizer trace lacks feasibility columns: {path}")

    skipped = trace[trace.attempted == 0]
    trace = trace[trace.attempted == 1].copy()
    accepted = trace[trace.accepted == 1]
    accepted_infeasible = accepted[accepted.raw_return_feasible != 1]
    accepted_over_tolerance = accepted[
        accepted.raw_constraint_violation > accepted.constraint_tolerance + 1e-18
    ]
    accepted_decreases = accepted[accepted.improvement < -acceptance_tolerance]
    if not accepted_infeasible.empty or not accepted_over_tolerance.empty:
        raise AssertionError("an infeasible optimizer return was accepted")
    if not accepted_decreases.empty:
        raise AssertionError("an accepted block decreased post-correction likelihood")

    internal_infeasible_evaluations = int(
        trace.infeasible_objective_evaluations.sum()
    )
    return {
        "attempted_blocks": int(len(trace)),
        "skipped_blocks": int(len(skipped)),
        "accepted_blocks": int((trace.accepted == 1).sum()),
        "rejected_blocks": int((trace.accepted == 0).sum()),
        "raw_returns_outside_tolerance": int(
            (trace.raw_return_feasible == 0).sum()
        ),
        "internal_infeasible_evaluations": internal_infeasible_evaluations,
        "internal_feasible_objective_path": internal_infeasible_evaluations == 0,
        "max_internal_constraint_violation": float(
            trace.max_objective_constraint_violation.max()
        ),
        "max_raw_return_constraint_violation": float(
            trace.raw_constraint_violation.max()
        ),
        "numerical_corrections": int(
            (trace.numerical_correction_applied == 1).sum()
        ),
    }


def audit_output_geometry(state_dir: Path, tolerance: float = 1e-12) -> dict[str, float]:
    coordinates = pd.read_csv(state_dir / "cpp_coordinates_all_periods.csv")
    bills = pd.read_csv(state_dir / "cpp_bill_parameters.csv")
    coordinate_radius = np.hypot(coordinates.coord1D, coordinates.coord2D)
    midpoint1 = pd.to_numeric(bills.midpoint1D, errors="coerce").fillna(0.0)
    midpoint2 = pd.to_numeric(bills.midpoint2D, errors="coerce").fillna(0.0)
    midpoint_radius = np.hypot(midpoint1, midpoint2)
    if coordinate_radius.max() > 1.0 + tolerance:
        raise AssertionError("stored static legislator coordinate is infeasible")
    if midpoint_radius.max() > 1.0 + tolerance:
        raise AssertionError("stored roll-call midpoint is infeasible")
    return {
        "max_coordinate_radius": float(coordinate_radius.max()),
        "max_midpoint_radius": float(midpoint_radius.max()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modern-binary", type=Path, required=True)
    reference = parser.add_mutually_exclusive_group(required=True)
    reference.add_argument("--reference-binary", type=Path)
    reference.add_argument("--reference-output-root", type=Path)
    parser.add_argument("--reference-label", default="faithful_cpp")
    parser.add_argument("--reference-is-actual-fortran", action="store_true")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--coordinate-tolerance", type=float, default=1e-6)
    parser.add_argument("--likelihood-tolerance", type=float, default=1e-6)
    parser.add_argument("--acceptance-tolerance", type=float, default=1e-8)
    parser.add_argument("--require-numerical-equivalence", action="store_true")
    parser.add_argument(
        "--require-feasible-objective-evaluations", action="store_true"
    )
    args = parser.parse_args()

    root = args.repo_root.resolve()
    work = args.work_dir.resolve()
    modern_binary = args.modern_binary.resolve()
    work.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "contract": {
            "coordinate_tolerance": args.coordinate_tolerance,
            "likelihood_tolerance": args.likelihood_tolerance,
            "acceptance_tolerance": args.acceptance_tolerance,
            "reference_label": args.reference_label,
            "reference_is_actual_fortran": args.reference_is_actual_fortran,
        },
        "panels": {},
        "input_profiles": {"chile": {}, "us": {}},
    }
    panel_rows: list[dict[str, Any]] = []
    bin_rows: list[dict[str, Any]] = []
    any_equivalence_failure = False
    any_infeasible_objective_evaluation = False

    for legislature in PANELS:
        input_dir = root / "data" / "chile-static" / f"leg{legislature}"
        modern_dir = work / f"leg{legislature}" / "modern"
        reference_dir = work / f"leg{legislature}" / "reference"
        run_engine(
            modern_binary,
            input_dir,
            modern_dir,
            iterations=args.iterations,
            modern=True,
        )
        if args.reference_binary is not None:
            run_engine(
                args.reference_binary.resolve(),
                input_dir,
                reference_dir,
                iterations=args.iterations,
                modern=False,
            )
        else:
            reference_dir = (
                args.reference_output_root.resolve() / f"leg{legislature}"
            )
            if not reference_dir.is_dir():
                raise FileNotFoundError(reference_dir)

        modern_summary = read_summary(modern_dir / "cpp_summary.csv")
        reference_summary = read_summary(reference_dir / "cpp_summary.csv")
        common_modern = evaluate_terminal_state(
            modern_binary,
            input_dir,
            modern_dir,
            work / f"leg{legislature}" / "evaluate-modern",
            work / f"leg{legislature}" / "staging-modern",
            periods=1,
            model=0,
        )
        common_reference = evaluate_terminal_state(
            modern_binary,
            input_dir,
            reference_dir,
            work / f"leg{legislature}" / "evaluate-reference",
            work / f"leg{legislature}" / "staging-reference",
            periods=1,
            model=0,
        )

        aligned, geometry = align_coordinates(
            coordinate_frame(modern_dir / "cpp_coordinates_all_periods.csv"),
            coordinate_frame(reference_dir / "cpp_coordinates_all_periods.csv"),
        )
        parameter_differences = compare_terminal_parameters(
            modern_dir, reference_dir
        )
        counts = member_vote_counts(input_dir)
        panel_bin_rows, coverage = vote_bin_rows(legislature, aligned, counts)
        bin_rows.extend(panel_bin_rows)
        report["input_profiles"]["chile"][str(legislature)] = input_profile(
            vote_files(input_dir, 1)[0]
        )

        common_modern_ll = float(common_modern["log_likelihood"])
        common_reference_ll = float(common_reference["log_likelihood"])
        modern_native_ll = float(modern_summary["log_likelihood"])
        reference_native_ll = float(reference_summary["log_likelihood"])
        modern_roundtrip_difference = abs(common_modern_ll - modern_native_ll)
        reference_roundtrip_difference = abs(
            common_reference_ll - reference_native_ll
        )
        if modern_roundtrip_difference > args.likelihood_tolerance:
            raise AssertionError(
                "modern state did not survive common-evaluator reload"
            )
        if reference_roundtrip_difference > args.likelihood_tolerance:
            raise AssertionError(
                "reference state did not survive common-evaluator reload"
            )
        ll_difference = common_modern_ll - common_reference_ll
        objective_equivalent = abs(ll_difference) <= args.likelihood_tolerance
        parameter_equivalent = all(
            difference <= args.coordinate_tolerance
            for difference in parameter_differences.values()
        )
        numerically_equivalent = objective_equivalent and parameter_equivalent
        any_equivalence_failure |= not numerically_equivalent

        trace_audit = audit_trace(
            modern_dir / "cpp_optimizer_trace.csv",
            args.acceptance_tolerance,
        )
        any_infeasible_objective_evaluation |= not trace_audit[
            "internal_feasible_objective_path"
        ]
        modern_feasibility = audit_output_geometry(modern_dir)
        reference_feasibility = audit_output_geometry(reference_dir)
        panel_report = {
            "modern_native_log_likelihood": modern_native_ll,
            "reference_native_log_likelihood": reference_native_ll,
            "modern_common_log_likelihood": common_modern_ll,
            "reference_common_log_likelihood": common_reference_ll,
            "modern_common_reload_difference": modern_roundtrip_difference,
            "reference_common_reload_difference": (
                reference_roundtrip_difference
            ),
            "common_log_likelihood_difference": ll_difference,
            "modern_is_better_feasible_endpoint": ll_difference
            > args.likelihood_tolerance,
            "objective_equivalent": objective_equivalent,
            "parameter_equivalent_in_common_starting_frame": parameter_equivalent,
            "numerically_equivalent": numerically_equivalent,
            "geometry": geometry,
            "parameter_differences": parameter_differences,
            "vote_coverage": coverage,
            "optimizer_contract": trace_audit,
            "modern_stored_geometry": modern_feasibility,
            "reference_stored_geometry": reference_feasibility,
        }
        report["panels"][str(legislature)] = panel_report
        panel_rows.append(
            {
                "legislature": legislature,
                "modern_common_ll": common_modern_ll,
                "reference_common_ll": common_reference_ll,
                "modern_common_reload_difference": modern_roundtrip_difference,
                "reference_common_reload_difference": (
                    reference_roundtrip_difference
                ),
                "common_ll_difference": ll_difference,
                "objective_equivalent": int(objective_equivalent),
                "parameter_equivalent": int(parameter_equivalent),
                "numerically_equivalent": int(numerically_equivalent),
                **geometry,
                **parameter_differences,
                **coverage,
                **trace_audit,
            }
        )

    us_input = root / "engine-faithful" / "benchmarks" / "us" / "cpp_input"
    for period, path in enumerate(vote_files(us_input, 5), start=1):
        report["input_profiles"]["us"][str(period)] = input_profile(path)

    report["verdicts"] = {
        "all_accepted_solver_returns_feasible": all(
            panel["optimizer_contract"]["raw_returns_outside_tolerance"] == 0
            for panel in report["panels"].values()
        ),
        "all_objective_evaluations_feasible": (
            not any_infeasible_objective_evaluation
        ),
        "all_panels_numerically_equivalent": not any_equivalence_failure,
        "modern_has_higher_common_in_sample_likelihood_on_all_panels": all(
            panel["modern_is_better_feasible_endpoint"]
            for panel in report["panels"].values()
        ),
    }

    report_path = work / "optimization_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    pd.DataFrame(panel_rows).to_csv(
        work / "optimization_audit_panels.csv", index=False
    )
    pd.DataFrame(bin_rows).to_csv(
        work / "optimization_audit_vote_bins.csv", index=False
    )
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.require_numerical_equivalence and any_equivalence_failure:
        return 2
    if (
        args.require_feasible_objective_evaluations
        and any_infeasible_objective_evaluation
    ):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
