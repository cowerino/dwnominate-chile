#!/usr/bin/env python3
r"""map_disk -- ONE unit-disk ideological map per figure. Nothing else in it.

Follows the convention established in quevotan-db/maps_2026-05-24/make_maps.py:
party colour from a left-right score through a coolwarm ramp, dim 1 oriented so
the right-wing bloc is positive, a party legend below the plot, dotted axes
through the origin. Added here: the unit circle drawn as a reference rule.

Roberto, 2026-08-20: "ONE UNIT DISK MAP PROJECTION PER FIGURE. ONE. With a
proper colored legend, coloring the points."
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

CMAP = plt.get_cmap("coolwarm")

# Chile: left-right score in [-1 left, +1 right] (verbatim from make_maps.py)
PARTY_LR_CL = {
 "PRep":1.0,"UDI":0.9,"RN":0.75,"EVOP":0.6,"AMPL":0.45,"PRI":0.35,
 "IND":0.0,"NOINFO":0.0,
 "DC":-0.2,"PRad":-0.4,"PL":-0.45,"FRVS":-0.5,"PPD":-0.55,"PS":-0.6,
 "IC":-0.7,"PEV":-0.7,"RD":-0.8,"PH":-0.8,"PC":-0.9,"CS":-0.9,"COM":-0.9,
}
PARTY_LR_US = {"R":0.9,"D":-0.9,"I":0.0}
RIGHT_CL = ["UDI","RN","EVOP","PRep"]
RIGHT_US = ["R"]

def party_color(p, lr): return CMAP((lr.get(str(p),0.0)+1)/2)

def orient(df, right_parties):
    """Flip dim1 so the right-wing bloc mean is positive. Polarity is a free gauge."""
    df = df.copy()
    m = df[df.party.isin(right_parties)]["d1"].mean()
    if pd.notna(m) and m < 0:
        df["d1"] = -df["d1"]
        df["d2"] = -df["d2"]      # a reflection would change chirality; use a rotation by pi
    return df

def disk_map(df, title, outstem, lr, right_parties, subtitle=None):
    """df: legislator_id, d1, d2, party.  ONE axes, ONE unit disk."""
    df = orient(df, right_parties)
    fig, ax = plt.subplots(figsize=(6.6, 6.6))
    th = np.linspace(0, 2*np.pi, 512)
    ax.plot(np.cos(th), np.sin(th), lw=1.0, color="0.45", zorder=2)
    ax.axhline(0, color="grey", lw=0.5, ls=":", zorder=1)
    ax.axvline(0, color="grey", lw=0.5, ls=":", zorder=1)
    ax.scatter(df["d1"], df["d2"], c=[party_color(p, lr) for p in df.party],
               s=42, edgecolors="black", linewidths=0.35, alpha=0.9, zorder=3)
    lim = max(1.05, float(np.abs(df[["d1","d2"]].to_numpy()).max())*1.04)
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
    ax.set_xlabel("Dimensión 1 (izquierda – derecha)", fontsize=10)
    ax.set_ylabel("Dimensión 2", fontsize=10)
    if subtitle:
        ax.set_title(title + chr(10), fontsize=11, pad=16)
        ax.text(0.5, 1.012, subtitle, transform=ax.transAxes, ha="center",
                fontsize=8.5, color="0.35")
    else:
        ax.set_title(title, fontsize=11, pad=8)
    present = [p for p in sorted(lr, key=lambda k: -lr[k]) if p in set(df.party) and p != "NOINFO"]
    handles = [Line2D([0],[0], marker="o", color="w", markerfacecolor=party_color(p, lr),
                      markeredgecolor="black", markersize=8, label=p) for p in present]
    ncol = min(11, max(4, int(np.ceil(len(handles)/2))))
    fig.legend(handles=handles, loc="lower center", ncol=ncol, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=[0, 0.075, 1, 1])
    for ext in ("pdf","png"):
        fig.savefig(f"{outstem}.{ext}", dpi=180 if ext=="png" else None, bbox_inches="tight")
    plt.close(fig)
    return len(df)
