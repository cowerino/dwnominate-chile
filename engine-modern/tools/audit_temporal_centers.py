#!/usr/bin/env python3
"""Audit realised positions, arithmetic means, and constrained beta_0 centres."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def audit(path: Path, coefficients_output: Path | None = None) -> dict[str, object]:
    data = pd.read_csv(path)
    legislators: list[dict[str, float | int]] = []
    coefficient_rows: list[dict[str, float | int]] = []
    maximum_reconstruction_error = 0.0

    for legislator_id, group in data.groupby("legislator_id"):
        group = group.sort_values("period")
        served = len(group)
        order = int(group["effective_model"].iloc[0])
        t = np.linspace(-1.0, 1.0, served) if served > 1 else np.array([-1.0])
        full_basis = np.column_stack(
            (
                np.ones(served),
                t,
                (3.0 * t * t - 1.0) / 2.0,
                (5.0 * t * t * t - 3.0 * t) / 2.0,
            )
        )
        basis = full_basis[:, : order + 1]
        coordinates = group[["coord1D", "coord2D"]].to_numpy(dtype=float)
        beta = np.linalg.lstsq(basis, coordinates, rcond=None)[0]
        padded_beta = np.zeros((4, 2))
        padded_beta[: order + 1] = beta
        reconstructed = basis @ beta
        maximum_reconstruction_error = max(
            maximum_reconstruction_error,
            float(np.max(np.abs(reconstructed - coordinates))),
        )

        beta0 = beta[0]
        arithmetic_mean = coordinates.mean(axis=0)
        beta2 = beta[2] if order >= 2 else np.zeros(2)
        predicted_mean = beta0.copy()
        if order >= 2 and served > 1:
            predicted_mean += beta2 / (served - 1)

        legislators.append(
            {
                "legislator_id": int(legislator_id),
                "served_periods": served,
                "effective_model": order,
                "intercept_radius": float(np.linalg.norm(beta0)),
                "arithmetic_mean_radius": float(np.linalg.norm(arithmetic_mean)),
                "mean_minus_intercept": float(np.linalg.norm(arithmetic_mean - beta0)),
                "mean_identity_error": float(np.linalg.norm(arithmetic_mean - predicted_mean)),
            }
        )
        coefficient_rows.append(
            {
                "legislator_id": int(legislator_id),
                "served_periods": served,
                "effective_model": order,
                **{
                    f"beta{term}_dim{dimension + 1}": padded_beta[term, dimension]
                    for term in range(4)
                    for dimension in range(2)
                },
                "intercept_radius": float(np.linalg.norm(beta0)),
            }
        )

    if coefficients_output is not None:
        coefficients_output.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(coefficient_rows).to_csv(
            coefficients_output, index=False, float_format="%.15f"
        )

    intercept_radii = np.array([row["intercept_radius"] for row in legislators])
    mean_radii = np.array([row["arithmetic_mean_radius"] for row in legislators])
    realised_radii = np.sqrt(data["coord1D"] ** 2 + data["coord2D"] ** 2)
    return {
        "file": str(path),
        "coordinate_rows": int(len(data)),
        "legislators": len(legislators),
        "maximum_intercept_radius": float(intercept_radii.max()),
        "intercepts_outside_unit_circle": int(np.sum(intercept_radii > 1.0 + 1e-9)),
        "maximum_arithmetic_mean_radius": float(mean_radii.max()),
        "arithmetic_means_outside_unit_circle": int(np.sum(mean_radii > 1.0 + 1e-9)),
        "maximum_realised_radius": float(realised_radii.max()),
        "realised_positions_outside_unit_circle": int(np.sum(realised_radii > 1.0 + 1e-9)),
        "maximum_reconstruction_error": maximum_reconstruction_error,
        "maximum_mean_identity_error": max(
            row["mean_identity_error"] for row in legislators
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("coordinates", type=Path, nargs="+")
    parser.add_argument(
        "--coefficients-out",
        type=Path,
        help="write reconstructed coefficients (requires exactly one input)",
    )
    args = parser.parse_args()
    if args.coefficients_out is not None and len(args.coordinates) != 1:
        parser.error("--coefficients-out requires exactly one coordinate file")
    print(
        json.dumps(
            [
                audit(
                    path,
                    args.coefficients_out if len(args.coordinates) == 1 else None,
                )
                for path in args.coordinates
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
