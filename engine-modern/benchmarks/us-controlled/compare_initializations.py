#!/usr/bin/env python3
"""Compare two C++ runs that differ only in their initial legislator map."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, required=True)
    parser.add_argument("--common-dir", type=Path, required=True)
    parser.add_argument("--repo-dir", type=Path, required=True)
    parser.add_argument("--common-seed", type=Path, required=True)
    parser.add_argument("--repo-seed", type=Path, required=True)
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


def active_member_periods(benchmark_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, int]] = []
    for period in range(1, 6):
        votes = pd.read_csv(
            benchmark_dir / "cpp_input" / f"votes_matrix_p{period}.csv",
            index_col=0,
        )
        observed = ((votes == 1) | (votes == 6)).any(axis=1)
        rows.extend(
            {"period": period, "id": int(member_id)}
            for member_id in votes.index[observed]
        )
    return pd.DataFrame(rows)


def origin_fixed_procrustes(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Return the orthogonal transform source -> target, with no shift or scale."""
    u, _, vt = np.linalg.svd(source.T @ target)
    return u @ vt


def period_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period, group in frame.groupby("period", sort=True):
        rows.append(
            {
                "period": period,
                "congress": 110 + period,
                "n_active": len(group),
                "r_dimension_1": np.corrcoef(group["ra1"], group["c1"])[0, 1],
                "r_dimension_2": np.corrcoef(group["ra2"], group["c2"])[0, 1],
                "mean_displacement": group["distance"].mean(),
                "median_displacement": group["distance"].median(),
                "p90_displacement": group["distance"].quantile(0.90),
                "max_displacement": group["distance"].max(),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    common = pd.read_csv(args.common_dir / "cpp_coordinates_all_periods.csv").rename(
        columns={"legislator_id": "id", "coord1D": "c1", "coord2D": "c2"}
    )
    repo = pd.read_csv(args.repo_dir / "cpp_coordinates_all_periods.csv").rename(
        columns={"legislator_id": "id", "coord1D": "r1", "coord2D": "r2"}
    )
    active = active_member_periods(args.benchmark_dir)
    party = pd.read_csv(args.common_seed)[
        ["legislator_id", "legislator_name", "party"]
    ].rename(columns={"legislator_id": "id", "legislator_name": "name"})
    repo_seed = pd.read_csv(args.repo_seed)[
        ["legislator_id", "coord1D", "coord2D"]
    ].rename(columns={"legislator_id": "id"})
    repo_seed["repository_start_zero"] = np.hypot(
        repo_seed["coord1D"], repo_seed["coord2D"]
    ) < 1e-12

    merged = active.merge(
        common[["period", "id", "c1", "c2"]], on=["period", "id"], how="inner"
    ).merge(
        repo[["period", "id", "r1", "r2"]], on=["period", "id"], how="inner"
    ).merge(party, on="id", how="left").merge(
        repo_seed[["id", "repository_start_zero"]], on="id", how="left"
    )
    if len(merged) != len(active):
        raise ValueError(
            f"coordinate coverage mismatch: {len(merged)} matched of {len(active)} active rows"
        )

    rotation = origin_fixed_procrustes(
        merged[["r1", "r2"]].to_numpy(), merged[["c1", "c2"]].to_numpy()
    )
    merged[["ra1", "ra2"]] = merged[["r1", "r2"]].to_numpy() @ rotation
    merged["dx"] = merged["c1"] - merged["ra1"]
    merged["dy"] = merged["c2"] - merged["ra2"]
    merged["distance"] = np.hypot(merged["dx"], merged["dy"])

    metrics = period_metrics(merged)
    pooled = {
        "period": "pooled",
        "congress": "111-115",
        "n_active": len(merged),
        "r_dimension_1": np.corrcoef(merged["ra1"], merged["c1"])[0, 1],
        "r_dimension_2": np.corrcoef(merged["ra2"], merged["c2"])[0, 1],
        "mean_displacement": merged["distance"].mean(),
        "median_displacement": merged["distance"].median(),
        "p90_displacement": merged["distance"].quantile(0.90),
        "max_displacement": merged["distance"].max(),
    }
    metrics = pd.concat([metrics, pd.DataFrame([pooled])], ignore_index=True)
    zero_start_metrics = (
        merged.groupby(["period", "repository_start_zero"], as_index=False)
        .agg(
            n=("distance", "size"),
            mean_displacement=("distance", "mean"),
            median_displacement=("distance", "median"),
            max_displacement=("distance", "max"),
        )
        .sort_values(["period", "repository_start_zero"])
    )

    common_summary = read_summary(args.common_dir / "cpp_summary.csv")
    repo_summary = read_summary(args.repo_dir / "cpp_summary.csv")
    objective = pd.DataFrame(
        [
            {
                "initialization": "common_all_periods_svd",
                "log_likelihood": common_summary["log_likelihood"],
                "classification_pct": common_summary["classification_pct"],
                "w2": common_summary["w2"],
                "beta": common_summary["beta"],
            },
            {
                "initialization": "repository_congress_111_wnominate",
                "log_likelihood": repo_summary["log_likelihood"],
                "classification_pct": repo_summary["classification_pct"],
                "w2": repo_summary["w2"],
                "beta": repo_summary["beta"],
            },
        ]
    )
    objective["delta_from_common"] = (
        objective["log_likelihood"] - objective.loc[0, "log_likelihood"]
    )

    common_trace = pd.read_csv(args.common_dir / "cpp_convergence_trace.csv")
    common_trace["initialization"] = "common_all_periods_svd"
    repo_trace = pd.read_csv(args.repo_dir / "cpp_convergence_trace.csv")
    repo_trace["initialization"] = "repository_congress_111_wnominate"
    traces = pd.concat([common_trace, repo_trace], ignore_index=True)

    merged.to_csv(args.output_dir / "cpp_initialization_displacements.csv", index=False)
    metrics.to_csv(args.output_dir / "cpp_initialization_metrics.csv", index=False)
    zero_start_metrics.to_csv(
        args.output_dir / "cpp_initialization_zero_start_metrics.csv", index=False
    )
    objective.to_csv(args.output_dir / "cpp_initialization_objective.csv", index=False)
    traces.to_csv(args.output_dir / "cpp_initialization_traces.csv", index=False)
    np.savetxt(
        args.output_dir / "repo_to_common_origin_fixed_rotation.csv",
        rotation,
        delimiter=",",
        header="column_1,column_2",
        comments="",
    )

    colors = {"D": "#2878b5", "R": "#cf4f43", "I": "#7768ad"}
    fig, axes = plt.subplots(2, 3, figsize=(14, 9), dpi=180)
    for period, axis in zip(range(1, 6), axes.ravel()):
        group = merged[merged["period"] == period]
        axis.add_patch(
            plt.Circle((0, 0), 1, fill=False, linestyle="--", color="0.45", lw=0.8)
        )
        for item in group.itertuples():
            color = colors.get(str(item.party), "#777777")
            axis.annotate(
                "",
                xy=(item.c1, item.c2),
                xytext=(item.ra1, item.ra2),
                arrowprops={
                    "arrowstyle": "->",
                    "lw": 0.55,
                    "color": color,
                    "alpha": 0.48,
                    "shrinkA": 0,
                    "shrinkB": 0,
                },
            )
            axis.scatter(item.ra1, item.ra2, s=7, color=color, alpha=0.72, zorder=3)
        axis.axhline(0, linewidth=0.45, color="0.78")
        axis.axvline(0, linewidth=0.45, color="0.78")
        axis.set(
            xlim=(-1.3, 1.3),
            ylim=(-1.3, 1.3),
            aspect="equal",
            title=f"Congreso {110 + period} (n={len(group)})",
            xlabel="Dimensión 1",
            ylabel="Dimensión 2",
        )
        axis.grid(alpha=0.12)
    legend_axis = axes.ravel()[-1]
    legend_axis.axis("off")
    legend_axis.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=colors[key],
                   markeredgecolor="none", label=label, markersize=7)
            for key, label in (("D", "Demócrata"), ("R", "Republicano"),
                               ("I", "Independiente"))
        ],
        loc="center",
        frameon=False,
        title="Partido",
    )
    fig.suptitle(
        "Sensibilidad de C++ al inicio: mapa del repositorio → mapa común",
        fontsize=14,
    )
    fig.text(
        0.5,
        0.015,
        "Alineación ortogonal con origen fijo; sin traslación ni escala. Solo miembros activos.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(args.output_dir / "cpp_initialization_displacements.png")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8.5, 5.2), dpi=180)
    for label, group in traces.groupby("initialization", sort=False):
        friendly = (
            "Common all-period seed"
            if label == "common_all_periods_svd"
            else "Inicio del repositorio (Congreso 111)"
        )
        if label == "common_all_periods_svd":
            friendly = "Inicio común (cinco períodos)"
        axis.plot(
            group["iteration"], group["log_likelihood"], marker="o", label=friendly
        )
    axis.set(
        title="Convergencia de C++ según inicialización",
        xlabel="Ciclo efectivo WINT-SIGMAS-RC-LEG",
        ylabel="Log-verosimilitud",
        xticks=range(1, 6),
    )
    axis.grid(alpha=0.18)
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(args.output_dir / "cpp_initialization_convergence.png")
    plt.close(fig)

    print(metrics.to_string(index=False))
    print("\nObjective after five cycles")
    print(objective.to_string(index=False))


if __name__ == "__main__":
    main()
