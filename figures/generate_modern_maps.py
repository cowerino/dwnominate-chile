#!/usr/bin/env python3
"""Generate modern-local/global disk maps in the existing public figure style.

Outputs 40 files in figures/:
- 20 PNG + 20 PDF
- one map per figure
- naming convention mirrors current fortran/ours files
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "figures"
RESDIR = ROOT / "results" / "2026-08-20-three-engine"

# Metadata from quevotan-db (same machine), because dwnominate-chile metadata is skeletonized.
QDB = Path("C:/Users/cow/Documents/GitHub/quevotan-db")
CHILE_META = QDB / "reproduce" / "input" / "legislator_metadata.csv"
US90_META = QDB / "benchmark_sen90" / "legislator_metadata.csv"
USDYN_META = QDB / "benchmark_us" / "cpp_input" / "legislator_metadata.csv"

PARTY_LR = {
    "PRep": 1.0,
    "UDI": 0.9,
    "RN": 0.75,
    "EVOP": 0.6,
    "AMPL": 0.45,
    "PRI": 0.35,
    "IND": 0.0,
    "NOINFO": 0.0,
    "DC": -0.2,
    "PRad": -0.4,
    "PL": -0.45,
    "FRVS": -0.5,
    "PPD": -0.55,
    "PS": -0.6,
    "IC": -0.7,
    "PEV": -0.7,
    "RD": -0.8,
    "PH": -0.8,
    "PC": -0.9,
    "CS": -0.9,
    "COM": -0.9,
}

CHILE_PARTY_ORDER = [
    "PRep", "UDI", "RN", "EVOP", "IND", "DC", "PRad", "PL", "FRVS", "PPD", "PS", "PEV", "RD", "PH", "PC", "CS", "COM",
]

US_PARTY_ORDER = ["R", "I", "D"]
US_COLORS = {"R": "#d34747", "D": "#4f67d3", "I": "#dcdcdc"}

CMAP = plt.get_cmap("coolwarm")


def load_party_maps() -> tuple[dict[int, str], dict[int, str]]:
    chile = pd.read_csv(CHILE_META)
    chile_map = (
        chile[["legislator_id", "partido"]]
        .dropna(subset=["legislator_id"])
        .assign(legislator_id=lambda d: d["legislator_id"].astype(int))
        .set_index("legislator_id")["partido"]
        .fillna("IND")
        .to_dict()
    )

    us90 = pd.read_csv(US90_META)
    usdyn = pd.read_csv(USDYN_META)
    us = pd.concat([us90[["legislator_id", "party"]], usdyn[["legislator_id", "party"]]], ignore_index=True)
    us_map = (
        us.dropna(subset=["legislator_id"])
        .assign(legislator_id=lambda d: d["legislator_id"].astype(int))
        .drop_duplicates(subset=["legislator_id"], keep="last")
        .set_index("legislator_id")["party"]
        .fillna("I")
        .to_dict()
    )
    return chile_map, us_map


def load_coords(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = df[["legislator_id", "period", "coord1D", "coord2D"]].copy()
    out["legislator_id"] = out["legislator_id"].astype(int)
    out["period"] = out["period"].astype(int)
    return out


def orient_dim1(df: pd.DataFrame, party_col: str, right_parties: set[str]) -> pd.DataFrame:
    out = df.copy()
    m = out[out[party_col].isin(right_parties)]["coord1D"].mean()
    if pd.notna(m) and m < 0:
        out["coord1D"] = -out["coord1D"]
    return out


def chile_color(p: str):
    s = PARTY_LR.get(str(p), 0.0)
    return CMAP((s + 1.0) / 2.0)


def draw_disk_map(df: pd.DataFrame, title: str, subtitle: str, out_base: Path, *, is_us: bool) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 8.5), dpi=150)

    if is_us:
        colors = [US_COLORS.get(str(p), US_COLORS["I"]) for p in df["party"]]
        legend_order = [p for p in US_PARTY_ORDER if p in set(df["party"].astype(str))]
    else:
        colors = [chile_color(p) for p in df["party"]]
        present = set(df["party"].astype(str))
        legend_order = [p for p in CHILE_PARTY_ORDER if p in present]

    ax.scatter(
        df["coord1D"],
        df["coord2D"],
        c=colors,
        s=55,
        edgecolors="#1a1a1a",
        linewidths=0.4,
        alpha=0.95,
    )

    circle = plt.Circle((0, 0), 1.0, fill=False, color="#7b7b7b", lw=1.1)
    ax.add_patch(circle)
    ax.axhline(0, color="#7f7f7f", lw=0.55, ls=":")
    ax.axvline(0, color="#7f7f7f", lw=0.55, ls=":")

    lim = 1.05
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal", "box")

    ax.set_xlabel("Dimensión 1  (izquierda – derecha)", fontsize=13)
    ax.set_ylabel("Dimensión 2", fontsize=13)
    ax.tick_params(labelsize=12)

    fig.suptitle(title, fontsize=17, y=0.98)
    ax.set_title(subtitle, fontsize=13, color="#575757", pad=6)

    handles = []
    for p in legend_order:
        if is_us:
            fc = US_COLORS.get(p, US_COLORS["I"])
        else:
            fc = chile_color(p)
        handles.append(
            Line2D([0], [0], marker="o", linestyle="", markerfacecolor=fc, markeredgecolor="#1a1a1a", markeredgewidth=1.2, markersize=10, label=p)
        )

    if handles:
        fig.legend(
            handles=handles,
            loc="lower center",
            ncol=min(len(handles), 9 if not is_us else 3),
            frameon=False,
            fontsize=12,
            bbox_to_anchor=(0.5, -0.01),
        )

    fig.tight_layout(rect=[0, 0.08, 1, 0.95])
    fig.savefig(out_base.with_suffix(".png"), dpi=150, bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def served_keys(panel_dir: str) -> set:
    """Roster of (legislator_id, period) pairs the member actually served.

    engine-faithful carries the export-frame fix and emits only served cells;
    engine-modern does not and pads every legislator to every period. Keying off
    the faithful export is therefore the roster of record.
    """
    src = RESDIR / panel_dir / "faithful" / "cpp_coordinates_all_periods_corrected.csv"
    f = load_coords(src)
    return set(zip(f["legislator_id"], f["period"]))


def filter_served(df: pd.DataFrame, panel_dir: str) -> pd.DataFrame:
    """Drop padded phantom placements. Inert on an already-served export."""
    keys = served_keys(panel_dir)
    idx = pd.MultiIndex.from_frame(df[["legislator_id", "period"]])
    kept = df[idx.isin(keys)].copy()
    if len(kept) != len(df):
        print(f"    filtered {panel_dir}: {len(df)} -> {len(kept)} rows "
              f"({len(df) - len(kept)} phantom)")
    return kept


def orient_dim2_to_reference(df: pd.DataFrame, panel_dir: str) -> pd.DataFrame:
    """Pin dimension-2 polarity to the engine-faithful arm.

    Dimension-2 orientation is a free gauge: nothing in the model fixes its sign, and
    orient_dim1() normalises dimension 1 only. An arm read from a differently signed
    export therefore renders as a mirror across the x axis while dimension 1 still
    agrees perfectly, which is how the interim rerun set differed from this one
    (dim1 r = +1.000000, dim2 r = -1.000000 on the same underlying run).

    This is a declared comparison gauge so the series is readable side by side. It is
    NOT a claim that dimension 2 has an intrinsic direction; the paper's position is
    that its orientation is analyst-supplied.
    """
    ref = load_coords(RESDIR / panel_dir / "faithful" / "cpp_coordinates_all_periods_corrected.csv")
    j = df.merge(ref, on=["legislator_id", "period"], suffixes=("", "_ref"))
    if len(j) < 3:
        return df
    r = np.corrcoef(j["coord2D"], j["coord2D_ref"])[0, 1]
    if np.isfinite(r) and r < 0:
        out = df.copy()
        out["coord2D"] = -out["coord2D"]
        print(f"    dim2 polarity flipped to match faithful ({panel_dir}, r={r:+.4f})")
        return out
    return df


def mean_by_legislator(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("legislator_id", as_index=False)[["coord1D", "coord2D"]]
        .mean()
        .assign(period=1)
    )


def main() -> None:
    chile_party, us_party = load_party_maps()

    mapping = {
        # static
        "cl-static-leg353": ("chile-static-p8", None, False, "Chile · legislatura 353"),
        "cl-static-leg366": ("chile-static-p21", None, False, "Chile · legislatura 366"),
        "cl-static-leg368": ("chile-static-p23", None, False, "Chile · legislatura 368"),
        "us-static-sen90": ("us-sen90-static", None, True, "US Senate 90"),
        # dynamic slices
        "cl-dyn-leg353": ("chile-dyn-m2", 8, False, "Chile · legislatura 353 · panel dinámico de 23"),
        "cl-dyn-leg366": ("chile-dyn-m2", 21, False, "Chile · legislatura 366 · panel dinámico de 23"),
        "cl-dyn-leg368": ("chile-dyn-m2", 23, False, "Chile · legislatura 368 · panel dinámico de 23"),
        "cl-dyn-carrera": ("chile-dyn-m2", "career", False, "Chile · promedio de carrera · panel dinámico de 23"),
        "us-dyn-p5": ("us-dyn-5p", 5, True, "US Senate · último período del panel de 5"),
        "us-dyn-carrera": ("us-dyn-5p", "career", True, "US Senate · promedio de carrera · panel dinámico de 5"),
    }

    modes = {
        "modern-local": "modern-ltr-local",
        "modern-global": "modern-ltr-global",
    }

    generated = []

    for base_name, (panel_dir, slice_spec, is_us, panel_title) in mapping.items():
        for mode_short, arm in modes.items():
            src = RESDIR / panel_dir / arm / "cpp_coordinates_all_periods_corrected.csv"
            df = load_coords(src)
            df = filter_served(df, panel_dir)
            df = orient_dim2_to_reference(df, panel_dir)

            if slice_spec == "career":
                dfp = mean_by_legislator(df)
            elif slice_spec is None:
                dfp = df.copy()
            else:
                dfp = df[df["period"] == int(slice_spec)].copy()

            if is_us:
                dfp["party"] = dfp["legislator_id"].map(us_party).fillna("I")
                dfp = orient_dim1(dfp, "party", {"R"})
                subtitle = (
                    "ajuste estático de un período" if "static" in base_name
                    else "corte transversal del ajuste de 5 períodos" if base_name == "us-dyn-p5"
                    else "promedio sobre períodos servidos"
                )
            else:
                dfp["party"] = dfp["legislator_id"].map(chile_party).fillna("IND")
                dfp = orient_dim1(dfp, "party", {"UDI", "RN", "EVOP", "PRep"})
                subtitle = (
                    "ajuste estático de un período" if "static" in base_name
                    else "corte transversal del ajuste de 23 períodos" if "leg" in base_name
                    else "promedio sobre períodos servidos"
                )

            title = f"{panel_title} · C++ engine-modern ({'local' if mode_short == 'modern-local' else 'global'})"
            out_base = FIGDIR / f"{base_name}-{mode_short}"
            draw_disk_map(dfp, title, subtitle, out_base, is_us=is_us)
            generated.append(out_base.name)

    print(f"Generated {len(generated)} modern map slots (PNG+PDF each) in {FIGDIR}")


if __name__ == "__main__":
    main()
