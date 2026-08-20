#!/usr/bin/env python3
"""Disk maps for the converged engine-modern runs (convergence-fix build).

Source: results/2026-08-20-converged-modern/, the run-to-convergence build that
also fixes two export defects — the Legendre basis is now built on each
legislator's compact served-period sequence rather than the whole-panel index,
and the dynamic CSVs contain only observed (legislator_id, period) pairs.

These runs stopped on a likelihood-improvement criterion (238 cycles in Chile,
62 in the US) rather than at a fixed 4, so they are NOT comparable to the
iteration-4 arms in results/2026-08-20-three-engine/. Kept in their own slots.

Style and colour policy inherited from generate_modern_maps.py.
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
    load_coords,
    load_party_maps,
    mean_by_legislator,
    orient_dim1,
    orient_dim2_to_reference,
)

CONV = RESDIR.parent / "2026-08-20-converged-modern"

PANELS = {
    "chile-dyn-m2": dict(
        is_us=False,
        slots={
            "cl-dyn-leg353": (8, "Chile · legislatura 353 · panel dinámico de 23"),
            "cl-dyn-leg366": (21, "Chile · legislatura 366 · panel dinámico de 23"),
            "cl-dyn-leg368": (23, "Chile · legislatura 368 · panel dinámico de 23"),
            "cl-dyn-carrera": ("career", "Chile · promedio de carrera · panel dinámico de 23"),
        },
    ),
    "us-dyn-5p": dict(
        is_us=True,
        slots={
            "us-dyn-p5": (5, "US Senate · último período del panel de 5"),
            "us-dyn-carrera": ("career", "US Senate · promedio de carrera · panel dinámico de 5"),
        },
    ),
}


def main() -> None:
    chile_party, us_party = load_party_maps()
    made = 0

    for panel, cfg in PANELS.items():
        src = CONV / panel / "modern-global" / "cpp_coordinates_all_periods_corrected.csv"
        if not src.exists():
            print(f"  SKIP {panel}: {src} missing")
            continue
        df = load_coords(src)
        print(f"{panel}: {len(df)} rows from the converged build")
        df = filter_served(df, panel)
        df = orient_dim2_to_reference(df, panel)

        for base_name, (slice_spec, panel_title) in cfg["slots"].items():
            if slice_spec == "career":
                dfp = mean_by_legislator(df)
                subtitle = "promedio sobre períodos servidos · corrida convergida"
            else:
                dfp = df[df["period"] == int(slice_spec)].copy()
                subtitle = "corte transversal · corrida convergida"

            if cfg["is_us"]:
                dfp["party"] = dfp["legislator_id"].map(us_party).fillna("I")
                dfp = orient_dim1(dfp, "party", {"R"})
            else:
                dfp["party"] = dfp["legislator_id"].map(chile_party).fillna("IND")
                dfp = orient_dim1(dfp, "party", {"UDI", "RN", "EVOP", "PRep"})

            out_base = FIGDIR / f"{base_name}-modern-converged"
            draw_disk_map(
                dfp,
                f"{panel_title} · C++ engine-modern (convergido, global)",
                subtitle,
                out_base,
                is_us=cfg["is_us"],
            )
            r = np.hypot(dfp["coord1D"], dfp["coord2D"])
            print(f"  {out_base.name}: {len(dfp)} pts, max r={r.max():.4f}, "
                  f"outside={int((r > 1 + 1e-9).sum())}")
            made += 1

    print(f"Generated {made} converged map slots (PNG+PDF each)")


if __name__ == "__main__":
    main()
