#!/usr/bin/env python3
"""Render the per-party maps: one figure per (panel, engine)."""
from pathlib import Path
import pandas as pd, map_party as M

OUT = Path("../renders/party-maps-2026-08-20")
DB  = M.DB
JOB = Path("C:/Users/cow/.claude/jobs/b08a2d58/tmp")
meta = M.load_meta()

PANELS = {
 "leg353": dict(fort=DB/"fortran/build_2004/run_static_chile_p8/us_legout.dat",
   engines={"fortran":None,"ours":JOB/"expfix_p8",
            "modern-global":DB/"out/chile/static_panels/p8/out_modern",
            "modern-local":DB/"out/chile/scaletest/_l_p8"}),
 "leg366": dict(fort=DB/"fortran/build_2004/run_static_chile_p21/us_legout.dat",
   engines={"fortran":None,"ours":JOB/"expfix_p21",
            "modern-global":DB/"out/chile/static_panels/p21/out_modern",
            "modern-local":DB/"out/chile/scaletest/_l_p21"}),
 "leg368": dict(fort=DB/"fortran/build_2004/run_static_chile_p23/us_legout.dat",
   engines={"fortran":None,"ours":JOB/"expfix_p23",
            "modern-global":DB/"out/chile/static_panels/p23/out_modern",
            "modern-local":DB/"out/chile/scaletest/_l_p23"}),
}
LABEL={"fortran":"Fortran 2004 (referencia)","ours":"C++ engine-faithful",
       "modern-global":"engine-modern, búsqueda global","modern-local":"engine-modern, región de confianza local"}

for pname,cfg in PANELS.items():
    F = M.load_fortran(cfg["fort"])[["legislator_id","d1","d2"]]
    ref = F.rename(columns={"d1":"d1_ref","d2":"d2_ref"}) if False else F.copy()
    for ename,edir in cfg["engines"].items():
        if ename=="fortran":
            df = F.merge(meta,on="legislator_id"); refarg=None
        else:
            c = M.load_cpp(edir)[["legislator_id","d1","d2"]]
            df = c.merge(meta,on="legislator_id"); refarg=ref
        stem = OUT/f"map-{pname}-{ename}"
        npar,n = M.draw(df, f"{pname} · {LABEL[ename]}", str(stem), ref=refarg)
        print(f"{pname:8s} {ename:14s} -> {npar} partidos, {n} legisladores")
