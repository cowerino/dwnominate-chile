#!/usr/bin/env python3
"""Build one estimator-independent starting map from all five vote matrices.

The construction uses only observed votes. It obtains a two-dimensional SVD
subspace, rotates that subspace so dimension 1 maximally separates the two
major parties, fixes the sign of dimension 2 with a named anchor, projects the
map inside radius 0.95, and serializes the coordinates as IEEE float32. Both
Fortran and C++ must consume the resulting CSV without further rounding.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dimension-2-anchor", type=int, default=40915)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = pd.read_csv(args.input_dir / "legislator_metadata.csv")
    metadata["legislator_id"] = metadata["legislator_id"].astype(int)
    metadata = metadata.drop_duplicates("legislator_id").set_index("legislator_id")

    matrices: list[np.ndarray] = []
    ids: np.ndarray | None = None
    observed_votes = 0
    for period in range(1, 6):
        frame = pd.read_csv(
            args.input_dir / f"votes_matrix_p{period}.csv", index_col=0
        )
        frame.index = frame.index.astype(int)
        if ids is None:
            ids = frame.index.to_numpy()
        elif not np.array_equal(ids, frame.index.to_numpy()):
            raise ValueError("The five vote matrices do not share the same roster order")

        codes = frame.to_numpy(dtype=np.int16)
        observed = (codes == 1) | (codes == 6)
        observed_votes += int(observed.sum())
        signed = np.where(codes == 1, 1.0, np.where(codes == 6, -1.0, np.nan))
        column_means = np.nanmean(signed, axis=0)
        centered = np.where(observed, signed - column_means, 0.0)
        matrices.append(centered)

    if ids is None:
        raise ValueError("No vote matrices were loaded")

    vote_panel = np.concatenate(matrices, axis=1)
    u, singular_values, _ = np.linalg.svd(vote_panel, full_matrices=False)
    scores = u[:, :2] * singular_values[:2]

    parties = metadata.reindex(ids)["party"].fillna("I").astype(str).to_numpy()
    party_target = np.where(parties == "D", 1.0, np.where(parties == "R", -1.0, 0.0))
    party_target -= party_target.mean()
    direction = scores.T @ party_target
    direction /= np.linalg.norm(direction)
    orthogonal = np.array([-direction[1], direction[0]])
    coordinates = np.column_stack((scores @ direction, scores @ orthogonal))

    if coordinates[parties == "D", 0].mean() < coordinates[parties == "R", 0].mean():
        coordinates[:, 0] *= -1.0

    anchor_matches = np.flatnonzero(ids == args.dimension_2_anchor)
    if anchor_matches.size != 1:
        raise ValueError("Dimension-2 anchor is not present exactly once")
    if coordinates[anchor_matches[0], 1] < 0.0:
        coordinates[:, 1] *= -1.0

    maximum_radius = np.linalg.norm(coordinates, axis=1).max()
    coordinates *= 0.95 / maximum_radius
    coordinates = coordinates.astype(np.float32)

    output = pd.DataFrame(
        {
            "coord1D": coordinates[:, 0],
            "coord2D": coordinates[:, 1],
            "legislator_id": ids,
            "legislator_name": metadata.reindex(ids)["name"].fillna("").to_numpy(),
            "party": parties,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, float_format="%.9g")

    diagnostics = {
        "legislators": int(len(ids)),
        "roll_calls": int(vote_panel.shape[1]),
        "observed_votes": observed_votes,
        "dimension_2_anchor": args.dimension_2_anchor,
        "singular_values": [float(x) for x in singular_values[:2]],
        "maximum_serialized_radius": float(
            np.linalg.norm(coordinates.astype(np.float64), axis=1).max()
        ),
        "zero_coordinate_rows": int(np.all(coordinates == 0.0, axis=1).sum()),
    }
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
