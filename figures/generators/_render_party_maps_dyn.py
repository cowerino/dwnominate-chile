#!/usr/bin/env python3
"""Dynamic-panel per-party maps: cross-sections of the 23-period fit at the
same three legislaturas that have static fits, so the two are comparable.

Uses a fit produced by the engine AT OR AFTER the 2026-08-20 exporter fix, so
the coordinates are already the fitted configuration (local t, served only).
"""
from pathlib import Path
import pandas as pd, map_party as M

OUT = Path("../renders/party-maps-2026-08-20")
DB, JOB = M.DB, Path("C:/Users/cow/.claude/jobs/b08a2d58/tmp")
meta = M.load_meta()

FORT_DYN = DB/"out/dwnom2004_chile_per_period/us_legout.dat"
ARM_DYN  = JOB/"expfix_dyn"          # exporter-fixed, 2855 served rows
PERIODS  = {8:"leg353", 21:"leg366", 23:"leg368"}

Fall = M.load_fortran(FORT_DYN)
Call = M.load_cpp(ARM_DYN)
# ONE global rotation on all served placements, then slice: a trajectory frame.
m = Fall.merge(Call, on=["period","legislator_id"], suffixes=("_r",""))
import numpy as np
R = np.linalg.svd(m[["d1","d2"]].to_numpy(float).T @ m[["d1_r","d2_r"]].to_numpy(float))
Rot = R[0] @ R[2]
rot = m[["d1","d2"]].to_numpy(float) @ Rot
m["d1x"], m["d2x"] = rot[:,0], rot[:,1]

for per,label in PERIODS.items():
    sub = m[m["period"]==per]
    f = sub[["legislator_id","d1_r","d2_r"]].rename(columns={"d1_r":"d1","d2_r":"d2"}).merge(meta,on="legislator_id")
    o = sub[["legislator_id","d1x","d2x"]].rename(columns={"d1x":"d1","d2x":"d2"}).merge(meta,on="legislator_id")
    for tag,df in (("fortran",f),("ours",o)):
        n,_ = M.draw(df, f"{label} (periodo {per}) dentro del ajuste dinámico de 23 periodos · "
                         f"{'Fortran 2004 (referencia)' if tag=='fortran' else 'C++ engine-faithful'}",
                     str(OUT/f"mapdyn-{label}-{tag}"), ref=None)
        print(f"dyn {label} {tag:8s} -> {n} partidos, {len(df)} placements")
