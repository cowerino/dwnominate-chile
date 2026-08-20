#!/usr/bin/env python3
"""One unit-disk map per figure: Chile static, US static, and the dynamic panels."""
from pathlib import Path
import numpy as np, pandas as pd
import map_disk as M

DB  = Path("C:/Users/cow/Documents/GitHub/quevotan-db/reproduce")
BM  = Path("C:/Users/cow/Documents/GitHub/quevotan-api/nominate_cmodule/benchmarks")
JOB = Path("C:/Users/cow/.claude/jobs/b08a2d58/tmp")
OUT = Path("../renders/disk-maps-2026-08-20"); OUT.mkdir(parents=True, exist_ok=True)

def legout(p):
    rows=[]
    for line in open(p):
        if len(line.rstrip("\r\n"))<54: continue
        try: rows.append((int(line[0:4]),int(line[4:10]),float(line[40:47]),float(line[47:54])))
        except ValueError: continue
    d=pd.DataFrame(rows,columns=["period","legislator_id","d1","d2"])
    return d.drop_duplicates(["period","legislator_id"],keep="last").dropna()

def cpp(d):
    return pd.read_csv(Path(d)/"cpp_coordinates_all_periods.csv").rename(
        columns={"coord1D":"d1","coord2D":"d2"})[["period","legislator_id","d1","d2"]]

meta_cl = pd.read_csv(DB/"input/legislator_metadata.csv")[["legislator_id","partido"]]
meta_cl = meta_cl.rename(columns={"partido":"party"}); meta_cl["party"]=meta_cl.party.fillna("IND")
def meta_us(p):
    m=pd.read_csv(p)[["legislator_id","party"]]; m["party"]=m.party.fillna("I"); return m

n=0
def emit(df, meta, title, stem, lr, right, sub=None):
    global n
    d = df.merge(meta, on="legislator_id", how="left")
    d["party"] = d["party"].fillna("IND" if lr is M.PARTY_LR_CL else "I")
    cnt = M.disk_map(d[["legislator_id","d1","d2","party"]], title, str(OUT/stem), lr, right, sub)
    n += 1; print(f"  [{n:2d}] {stem:44s} {cnt:5d} pts")

# ---------------------------------------------------------------- Chile static
print("CHILE STATIC (ajuste por legislatura)")
for leg,pdir in (("353","p8"),("366","p21"),("368","p23")):
    F = legout(DB/f"fortran/build_2004/run_static_chile_{pdir}/us_legout.dat")
    emit(F, meta_cl, f"Chile · legislatura {leg} · Fortran 2004 (referencia)",
         f"cl-static-leg{leg}-fortran", M.PARTY_LR_CL, M.RIGHT_CL, "ajuste estático de un período")
    emit(cpp(JOB/f"final_{pdir}"), meta_cl, f"Chile · legislatura {leg} · C++ engine-faithful",
         f"cl-static-leg{leg}-ours", M.PARTY_LR_CL, M.RIGHT_CL, "ajuste estático de un período")

# ------------------------------------------------------------------- US static
print("US STATIC (motor corregido)")
mus = meta_us(BM/"sen90/legislator_metadata.csv")
F = legout(DB/"fortran/build_2004/run_static_sen90/us_legout.dat")
emit(F, mus, "US Senate 90 · Fortran 2004 (referencia)", "us-static-sen90-fortran",
     M.PARTY_LR_US, M.RIGHT_US, "ajuste estático de un período")
emit(cpp(JOB/"final_sen90"), mus, "US Senate 90 · C++ engine-faithful", "us-static-sen90-ours",
     M.PARTY_LR_US, M.RIGHT_US, "ajuste estático de un período")

# ------------------------------------------------------------ Chile dynamic 23
print("CHILE DINÁMICO (panel de 23 períodos, marco local-t del exportador corregido)")
Fd = legout(DB/"out/dwnom2004_chile_per_period/us_legout.dat")
Cd = cpp(JOB/"expfix_dyn")
for leg,per in (("353",8),("366",21),("368",23)):
    emit(Fd[Fd.period==per], meta_cl, f"Chile · legislatura {leg} dentro del panel dinámico · Fortran 2004",
         f"cl-dyn-leg{leg}-fortran", M.PARTY_LR_CL, M.RIGHT_CL, "corte transversal del ajuste de 23 períodos")
    emit(Cd[Cd.period==per], meta_cl, f"Chile · legislatura {leg} dentro del panel dinámico · C++ engine-faithful",
         f"cl-dyn-leg{leg}-ours", M.PARTY_LR_CL, M.RIGHT_CL, "corte transversal del ajuste de 23 períodos")
for tag,df in (("fortran",Fd),("ours",Cd)):
    mp = df.groupby("legislator_id")[["d1","d2"]].mean().reset_index()
    emit(mp, meta_cl, f"Chile · promedio de carrera 2002–2021 · {'Fortran 2004' if tag=='fortran' else 'C++ engine-faithful'}",
         f"cl-dyn-carrera-{tag}", M.PARTY_LR_CL, M.RIGHT_CL, "media sobre los períodos servidos")

# --------------------------------------------------------------- US dynamic 5p
print("US DINÁMICO (5 períodos, motor corregido)")
mus5 = meta_us(BM/"us/cpp_input/legislator_metadata.csv")
Fu = legout(DB/"fortran/build_2004/run_us/us_legout.dat")
Cu = cpp(JOB/"final_us5")
for tag,df in (("fortran",Fu),("ours",Cu)):
    lab = "Fortran 2004" if tag=="fortran" else "C++ engine-faithful"
    emit(df[df.period==5], mus5, f"US Senate · último período del panel de 5 · {lab}",
         f"us-dyn-p5-{tag}", M.PARTY_LR_US, M.RIGHT_US, "corte transversal del ajuste de 5 períodos")
    mp = df.groupby("legislator_id")[["d1","d2"]].mean().reset_index()
    emit(mp, mus5, f"US Senate · promedio de carrera (5 períodos) · {lab}",
         f"us-dyn-carrera-{tag}", M.PARTY_LR_US, M.RIGHT_US, "media sobre los períodos servidos")
print(f"\n{n} figuras, una proyección de disco unitario cada una -> {OUT}")
