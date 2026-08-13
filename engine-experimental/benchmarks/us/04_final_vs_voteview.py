"""Final confirmation (2026-05-24): do BOTH the C++ and the in-house Fortran
DW-NOMINATE reproduce VoteView's PUBLISHED DW-NOMINATE scores on the US Senate
island (Congresses 111-115)?

Gate for closing the Finding C fix: per-period dim1 correlation of each
implementation vs published VoteView should be high (~>=0.95) and FLAT across
periods, and the recovered ideological map (anchor-senator trajectories) should
look the same. Polarity/rotation is a free gauge, so we orthogonal-Procrustes
align (rotation+reflection, no scaling) before comparing.
"""
import numpy as np, pandas as pd


def pear(x, y):
    return float(np.corrcoef(x, y)[0, 1])


def spear(x, y):
    return float(np.corrcoef(pd.Series(x).rank(), pd.Series(y).rank())[0, 1])


def procrustes_align(A, B):
    """Best rotation+reflection of A onto B (both centered)."""
    Ac, Bc = A - A.mean(0), B - B.mean(0)
    U, _, Vt = np.linalg.svd(Ac.T @ Bc)
    return Ac @ (U @ Vt), Bc


vv = pd.read_csv("voteview_published.csv")
vv = vv[["period", "legislator_id", "vv_dim1", "vv_dim2", "party_code", "bioname"]].dropna(subset=["vv_dim1"])
vv = vv.rename(columns={"legislator_id": "id"})

fort = pd.read_csv("fortran_dwnom.csv").rename(columns={"ID": "id", "session": "period"})
fort = fort[["period", "id", "coord1D", "coord2D"]].rename(columns={"coord1D": "f1", "coord2D": "f2"})

cpp = pd.read_csv("cpp_out/cpp_coordinates_all_periods.csv").rename(columns={"legislator_id": "id"})
cpp = cpp[["period", "id", "coord1D", "coord2D"]].rename(columns={"coord1D": "c1", "coord2D": "c2"})

periods = sorted(vv.period.unique())

print("=" * 74)
print("PER-PERIOD dim1 correlation vs PUBLISHED VoteView DW-NOMINATE (Procrustes-aligned)")
print("=" * 74)
print(f"{'period':>6} {'congress':>8} | {'C++ vs VV':>18} | {'Fortran vs VV':>18} | {'n':>4}")
print(f"{'':>6} {'':>8} | {'r':>9} {'rho':>8} | {'r':>9} {'rho':>8} |")
for p in periods:
    cong = 110 + p
    cv = cpp[cpp.period == p].merge(vv[vv.period == p], on="id")
    A, B = procrustes_align(cv[["c1", "c2"]].to_numpy(), cv[["vv_dim1", "vv_dim2"]].to_numpy())
    r_cv, rho_cv = pear(A[:, 0], B[:, 0]), spear(A[:, 0], B[:, 0])
    fv = fort[fort.period == p].merge(vv[vv.period == p], on="id")
    A2, B2 = procrustes_align(fv[["f1", "f2"]].to_numpy(), fv[["vv_dim1", "vv_dim2"]].to_numpy())
    r_fv, rho_fv = pear(A2[:, 0], B2[:, 0]), spear(A2[:, 0], B2[:, 0])
    print(f"{p:>6} {cong:>8} | {r_cv:>9.3f} {rho_cv:>8.3f} | {r_fv:>9.3f} {rho_fv:>8.3f} | {len(cv):>4}")

# Pooled across all periods (single alignment over the full panel)
print("\n" + "=" * 74)
print("POOLED (all 5 periods stacked) dim1 correlation vs VoteView")
print("=" * 74)
cv = cpp.merge(vv, on=["period", "id"])
A, B = procrustes_align(cv[["c1", "c2"]].to_numpy(), cv[["vv_dim1", "vv_dim2"]].to_numpy())
print(f"  C++     vs VoteView:  r={pear(A[:,0],B[:,0]):.3f}  rho={spear(A[:,0],B[:,0]):.3f}  n={len(cv)}")
fv = fort.merge(vv, on=["period", "id"])
A2, B2 = procrustes_align(fv[["f1", "f2"]].to_numpy(), fv[["vv_dim1", "vv_dim2"]].to_numpy())
print(f"  Fortran vs VoteView:  r={pear(A2[:,0],B2[:,0]):.3f}  rho={spear(A2[:,0],B2[:,0]):.3f}  n={len(fv)}")

# Anchor-senator trajectories: align each implementation to VV with ONE pooled
# rotation, then show dim1 per period for a few recognizable senators present
# in all 5 periods (most extreme by mean VV dim1 on each side).
print("\n" + "=" * 74)
print("ANCHOR SENATORS: dim1 trajectory  [VoteView | Fortran | C++]  (aligned to VoteView)")
print("=" * 74)
cvf = cpp.merge(vv, on=["period", "id"]).merge(fort, on=["period", "id"])
# pooled rotations
Ac, _ = procrustes_align(cvf[["c1", "c2"]].to_numpy(), cvf[["vv_dim1", "vv_dim2"]].to_numpy())
Af, _ = procrustes_align(cvf[["f1", "f2"]].to_numpy(), cvf[["vv_dim1", "vv_dim2"]].to_numpy())
cvf = cvf.assign(c1a=Ac[:, 0], f1a=Af[:, 0])
allp = set.intersection(*[set(cvf[cvf.period == p].id) for p in periods])
cvf5 = cvf[cvf.id.isin(allp)]
mean_vv = cvf5.groupby("id").vv_dim1.mean().sort_values()
anchors = list(mean_vv.index[:3]) + list(mean_vv.index[-3:])
name = vv.drop_duplicates("id").set_index("id").bioname.to_dict()
pc = vv.drop_duplicates("id").set_index("id").party_code.to_dict()
for legid in anchors:
    g = cvf5[cvf5.id == legid].sort_values("period")
    pn = {100: "D", 200: "R", 328: "I"}.get(pc.get(legid), str(pc.get(legid)))
    vvt = [round(x, 2) for x in g.vv_dim1.tolist()]
    ft = [round(x, 2) for x in g.f1a.tolist()]
    ct = [round(x, 2) for x in g.c1a.tolist()]
    print(f"\n{name.get(legid,legid)} ({pn}, id={legid})")
    print(f"   VoteView: {vvt}")
    print(f"   Fortran : {ft}")
    print(f"   C++     : {ct}")
