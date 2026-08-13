"""Tier 2 comparison on the 5-congress US Senate island (111-115).
Per period: orthogonal-Procrustes-align (rotation+reflection) and correlate.
  2a  C++ vs canonical Fortran dwnominate  (oracle test, same estimation task)
  2b  each vs VoteView published nominate_dim1 (validity; island != full-history)
  2c  Finding C diagnostic (does C++ degrade in periods 2+ / beta collapse)
"""
import numpy as np, pandas as pd

def pear(x, y): return np.corrcoef(x, y)[0, 1]
def spear(x, y):
    return np.corrcoef(pd.Series(x).rank(), pd.Series(y).rank())[0, 1]
def procrustes_align(A, B):
    Ac, Bc = A - A.mean(0), B - B.mean(0)
    U, _, Vt = np.linalg.svd(Ac.T @ Bc)
    return Ac @ (U @ Vt), Bc

fort = pd.read_csv("fortran_dwnom.csv").rename(columns={"ID": "id", "session": "period"})
fort = fort[["period", "id", "coord1D", "coord2D"]].rename(columns={"coord1D": "f1", "coord2D": "f2"})
cpp = pd.read_csv("cpp_out/cpp_coordinates_all_periods.csv").rename(columns={"legislator_id": "id"})
cpp = cpp[["period", "id", "coord1D", "coord2D"]].rename(columns={"coord1D": "c1", "coord2D": "c2"})
vv = pd.read_csv("voteview_published.csv")[["period", "legislator_id", "vv_dim1", "vv_dim2"]]
vv = vv.rename(columns={"legislator_id": "id"}).dropna(subset=["vv_dim1"])

def align_score(m, ax, ay, bx, by, label):
    A = m[[ax, ay]].to_numpy(); B = m[[bx, by]].to_numpy()
    Aa, Bc = procrustes_align(A, B)
    return pear(Aa[:, 0], Bc[:, 0]), spear(Aa[:, 0], Bc[:, 0]), pear(Aa[:, 1], Bc[:, 1]), len(m)

print(f"{'period':>6} {'congress':>8} | {'C++vsFort r1':>12} {'sp1':>5} | {'C++vsVV r1':>10} | {'FortvsVV r1':>11} | n")
rows = []
for p in sorted(fort.period.unique()):
    cong = 110 + p
    # present set this period = legislators the Fortran actually estimated
    fp, cp, vp = fort[fort.period == p], cpp[cpp.period == p], vv[vv.period == p]
    cf = fp.merge(cp, on="id")                         # C++ vs Fortran (full per-period roster)
    r_cf1, sp_cf1, r_cf2, n_cf = align_score(cf, "c1", "c2", "f1", "f2", "cf")
    cv = cp.merge(vp, on="id")                         # C++ vs VoteView
    r_cv1, _, _, n_cv = align_score(cv, "c1", "c2", "vv_dim1", "vv_dim2", "cv")
    fv = fp.merge(vp, on="id")                         # Fortran vs VoteView (oracle fork)
    r_fv1, _, _, n_fv = align_score(fv, "f1", "f2", "vv_dim1", "vv_dim2", "fv")
    print(f"{p:>6} {cong:>8} | {r_cf1:>12.3f} {sp_cf1:>5.2f} | {r_cv1:>10.3f} | {r_fv1:>11.3f} | {n_cf}")
    rows.append((p, r_cf1, r_cv1, r_fv1))

print("\n== Finding C diagnostic: C++ trajectory stability ==")
# A member present in all 5 periods, check coord1D swing in C++ vs Fortran
common = set.intersection(*[set(cpp[cpp.period == p].id) & set(fort[fort.period == p].id)
                            for p in sorted(fort.period.unique())])
def swing(df, idcol, vcol):
    s = df[df.id.isin(common)].pivot_table(index="id", columns="period", values=vcol)
    return (s.max(1) - s.min(1))
cpp_sw = swing(cpp, "id", "c1"); fort_sw = swing(fort, "id", "f1")
print(f"members present all 5 periods: {len(common)}")
print(f"mean coord1D range across periods  C++={cpp_sw.mean():.3f}  Fortran={fort_sw.mean():.3f}")
print(f"  (large C++ swing vs small Fortran swing => Finding C corruption)")
print("\nC++ final beta=1.75 (init 5.95), W2=0.99  <- collapse signature")
