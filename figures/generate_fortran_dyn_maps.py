#!/usr/bin/env python3
"""Rebuild the Fortran dynamic disk maps with the served-pair filter.

The canonical Fortran coordinate export is padded exactly as engine-modern's is:
7,820 rows on the Chilean dynamic panel against the 2,855 (legislator, period)
cells actually served. The previously published `cl-dyn-*-fortran` slots were
therefore drawn with 340 points per cross-section instead of 121 / 155 / 161, and
the career map averaged 23 periods per legislator instead of 8.45.

Style, naming and colour policy are inherited from generate_modern_maps.py so the
series stays consistent. Static Fortran slots are untouched: they were never padded.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from generate_modern_maps import (  # noqa: E402
    FIGDIR,
    RESDIR,
    draw_disk_map,
    filter_served,
    load_party_maps,
    mean_by_legislator,
    orient_dim1,
)

FORTRAN_CHILE_DYN = (
    RESDIR / "chile-dyn-m2" / "fortran" / "coordinates.csv"
)

PANEL = "chile-dyn-m2"


def load_fortran(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().strip('"') for c in df.columns]
    out = df[["legislator_id", "period", "coord1D", "coord2D"]].copy()
    out["legislator_id"] = out["legislator_id"].astype(int)
    out["period"] = out["period"].astype(int)
    return out


def dim2_gauge_report(df: pd.DataFrame, panel_dir: str) -> None:
    """Report, but do NOT act on, the dimension-2 polarity against engine-faithful.

    For the C++ arms this correlation is strong and the gauge is well determined.
    Against the Fortran export it is near zero on this panel, so flipping on its
    sign would be arbitrary. The number is printed so the ambiguity is on the
    record rather than silently resolved.
    """
    from generate_modern_maps import load_coords

    ref = load_coords(
        RESDIR / panel_dir / "faithful" / "cpp_coordinates_all_periods_corrected.csv"
    )
    j = df.merge(ref, on=["legislator_id", "period"], suffixes=("", "_ref"))
    r = np.corrcoef(j["coord2D"], j["coord2D_ref"])[0, 1]
    verdict = "well determined" if abs(r) >= 0.3 else "AMBIGUOUS, not pinned"
    print(f"    dim2 gauge vs faithful: r={r:+.4f} ({verdict})")


def main() -> None:
    chile_party, _ = load_party_maps()

    df = load_fortran(FORTRAN_CHILE_DYN)
    print(f"fortran chile dynamic: {len(df)} rows before filtering")
    df = filter_served(df, PANEL)
    dim2_gauge_report(df, PANEL)

    slots = {
        "cl-dyn-leg353": (8, "Chile · legislatura 353 · panel dinámico de 23"),
        "cl-dyn-leg366": (21, "Chile · legislatura 366 · panel dinámico de 23"),
        "cl-dyn-leg368": (23, "Chile · legislatura 368 · panel dinámico de 23"),
        "cl-dyn-carrera": ("career", "Chile · promedio de carrera · panel dinámico de 23"),
    }

    for base_name, (slice_spec, panel_title) in slots.items():
        if slice_spec == "career":
            dfp = mean_by_legislator(df)
            subtitle = "promedio sobre períodos servidos"
        else:
            dfp = df[df["period"] == int(slice_spec)].copy()
            subtitle = "corte transversal del ajuste de 23 períodos"

        dfp["party"] = dfp["legislator_id"].map(chile_party).fillna("IND")
        dfp = orient_dim1(dfp, "party", {"UDI", "RN", "EVOP", "PRep"})

        out_base = FIGDIR / f"{base_name}-fortran"
        draw_disk_map(
            dfp,
            f"{panel_title} · Fortran 2004",
            subtitle,
            out_base,
            is_us=False,
        )
        print(f"  {out_base.name}: {len(dfp)} points")

    print("Rebuilt 4 Fortran dynamic slots (PNG+PDF each)")


if __name__ == "__main__":
    main()
