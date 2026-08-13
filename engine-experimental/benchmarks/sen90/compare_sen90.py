"""Tier 1 fidelity comparison: C++ DW-NOMINATE (single-period, sen90) vs the
published W-NOMINATE reference (sen90wnom). Polarity/rotation is a free gauge,
so we align with orthogonal Procrustes (rotation + reflection, no scaling)
before correlating."""
import numpy as np, pandas as pd

def pearsonr(x, y):
    return (np.corrcoef(x, y)[0, 1],)

def spearmanr(x, y):
    rx = pd.Series(x).rank().to_numpy(); ry = pd.Series(y).rank().to_numpy()
    return (np.corrcoef(rx, ry)[0, 1],)

def orthogonal_procrustes(A, B):
    # best R (rotation+reflection) minimizing ||A R - B||, via SVD of A^T B
    U, _, Vt = np.linalg.svd(A.T @ B)
    return (U @ Vt, None)

ref = pd.read_csv("wnom_reference.csv")[["legislator_id", "coord1D", "coord2D", "party"]]

def load_cpp(path):
    d = pd.read_csv(path)
    d = d[d["period"] == 1][["legislator_id", "coord1D", "coord2D"]]
    return d.rename(columns={"coord1D": "c1", "coord2D": "c2"})

def align_and_score(cpp, label):
    m = ref.merge(cpp, on="legislator_id", how="inner").dropna()
    A = m[["c1", "c2"]].to_numpy()             # C++
    B = m[["coord1D", "coord2D"]].to_numpy()   # reference (W-NOM)
    # center
    Ac, Bc = A - A.mean(0), B - B.mean(0)
    R, _ = orthogonal_procrustes(Ac, Bc)       # best rotation+reflection of A onto B
    Aa = Ac @ R
    r1 = pearsonr(Aa[:, 0], Bc[:, 0])[0]
    r2 = pearsonr(Aa[:, 1], Bc[:, 1])[0]
    rho1 = spearmanr(Aa[:, 0], Bc[:, 0])[0]
    rmse = np.sqrt(((Aa - Bc) ** 2).sum(1)).mean()
    print(f"[{label}] n={len(m)}  dim1 Pearson r={r1:.3f}  dim1 Spearman={rho1:.3f}  "
          f"dim2 Pearson r={r2:.3f}  mean 2D dist after Procrustes={rmse:.3f}")
    return m, Aa, Bc

print("== C++ (W-NOM seed) vs published W-NOMINATE ==")
mA, AaA, B = align_and_score(load_cpp("out_seedA/cpp_coordinates_all_periods.csv"), "seedA")
print("== C++ (perturbed seed) vs published W-NOMINATE ==")
mB, AaB, _ = align_and_score(load_cpp("out_seedB/cpp_coordinates_all_periods.csv"), "seedB")

# Initialization stability: seedA vs seedB C++ outputs directly
sA = load_cpp("out_seedA/cpp_coordinates_all_periods.csv").rename(columns={"c1":"a1","c2":"a2"})
sB = load_cpp("out_seedB/cpp_coordinates_all_periods.csv").rename(columns={"c1":"b1","c2":"b2"})
s = sA.merge(sB, on="legislator_id")
print(f"\n== Initialization stability (seedA vs seedB C++ dim1) ==\n"
      f"Pearson r={pearsonr(s.a1, s.b1)[0]:.4f}")

# Party ordering sanity (D should sit on one side of R)
mA["aligned1"] = AaA[:, 0]
means = mA.groupby("party")["aligned1"].mean()
print("\n== Party means on aligned dim1 (US: D vs R should separate) ==")
print(means.round(3).to_string())
