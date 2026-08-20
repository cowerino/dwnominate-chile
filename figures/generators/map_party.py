#!/usr/bin/env python3
r"""map_party -- per-party ideal-point maps, one small map per party.

WHAT THIS SHOWS
    For one (panel, engine) pair: a facet grid over political parties. Each
    facet draws the FULL cloud of that panel in light grey for context and
    that party's members in the party's own colour. The unit circle is drawn
    as a reference rule.

WHY THIS FORM
    Roberto, 2026-08-20: "we need to be able to see the points and identify
    them by party clearly with colors, that's all ... it doesn't matter if
    that generates a lot of maps, that's the point."

    One party per facet, so identity is carried by the FACET LABEL and the
    colour only reinforces it. That is also what the colour arithmetic forces:
    on a scatter (all-pairs CVD) only three categorical slots clear the
    separation gates, and a six-party single scatter FAILS outright
    (green<->orange dE 3.2 protan, magenta<->orange 12.9 normal-vision,
    measured with the palette validator). Faceting removes the problem instead
    of arguing with it: each panel contains exactly one coloured category.

RELATION TO ../CONVENTION.md N1 (monochrome, category by marker shape)
    N1 is suspended here by Roberto's instruction, for discussion maps only,
    NOT for paper floats. The reasoning behind N2 is untouched: N2 forbids
    encoding an ESTIMATED SIGNED POSITION as a ramp, because that asserts the
    identification the paper denies. Party is an EXTERNAL CATEGORICAL label,
    not an estimated coordinate, so colouring by it asserts nothing about the
    frame -- it is the independent attribute we judge the map's coherence
    against.

    Kept from the convention: no numeric annotation inside any figure, axis
    titles once for the grid, bare facet labels, white panel with light grey
    grid and a dark border on all four sides, no title inside the axes.

FRAME
    Static panels are single-period, so the export frame question does not
    arise. For the dynamic panel pass a fit produced by an engine at or after
    the 2026-08-20 exporter fix, or read through _coords.load_coords_local.

NO COMPUTE. Reads finished coordinate artifacts and legislator metadata.
"""
import sys, argparse
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DB = Path("C:/Users/cow/Documents/GitHub/quevotan-db/reproduce")
META = DB/"input/legislator_metadata.csv"

# Categorical slots, fixed order, from the validated reference palette.
# One slot per facet, so no within-panel pair is ever formed.
SLOTS = ["#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4",
         "#008300","#4a3aa7","#e34948"]
GREY_CTX = "#d8d8d6"
INK = "#1a1a19"

def load_meta():
    m = pd.read_csv(META)[["legislator_id","partido"]]
    m["partido"] = m["partido"].fillna("NOINFO").replace({"NOINFO":"sin dato"})
    return m

def load_fortran(path):
    rows=[]
    for line in open(path):
        if len(line.rstrip("\r\n"))<54: continue
        try: rows.append((int(line[0:4]),int(line[4:10]),float(line[40:47]),float(line[47:54])))
        except ValueError: continue
    d=pd.DataFrame(rows,columns=["period","legislator_id","d1","d2"])
    return d.drop_duplicates(["period","legislator_id"],keep="last").dropna()

def load_cpp(d, period=None):
    c=pd.read_csv(Path(d)/"cpp_coordinates_all_periods.csv").rename(
        columns={"coord1D":"d1","coord2D":"d2"})
    if period is not None: c=c[c["period"]==period]
    return c[["period","legislator_id","d1","d2"]]

def rotate_to(A, B):
    """Rotate A onto B about the ORIGIN. Preserves every radius, so the unit
    circle stays meaningful. No translation, no scaling."""
    U,_,Vt = np.linalg.svd(A.T@B)
    return A@(U@Vt)

def draw(df, title, outstem, ref=None, ncol=4, min_n=1):
    """df: legislator_id,d1,d2,partido. ref: optional reference frame to rotate onto."""
    if ref is not None:
        m = df.merge(ref, on="legislator_id", suffixes=("","_ref")).dropna()
        R = rotate_to(m[["d1","d2"]].to_numpy(float), m[["d1_ref","d2_ref"]].to_numpy(float))
        df = df.copy()
        idx = df.set_index("legislator_id").index
        rot = pd.DataFrame(R, columns=["d1","d2"]); rot["legislator_id"]=m["legislator_id"].values
        df = df.drop(columns=["d1","d2"]).merge(rot, on="legislator_id")
    counts = df["partido"].value_counts()
    parties = [p for p,n in counts.items() if n>=min_n]
    nrow = int(np.ceil(len(parties)/ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.05*ncol, 2.28*nrow),
                             squeeze=False, sharex=True, sharey=True)
    th = np.linspace(0,2*np.pi,400)
    ALL = df[["d1","d2"]].to_numpy(float)
    for k,ax in enumerate(axes.ravel()):
        if k >= len(parties):
            ax.axis("off"); continue
        p = parties[k]
        sub = df[df["partido"]==p]
        ax.scatter(ALL[:,0],ALL[:,1],s=5,color=GREY_CTX,linewidths=0,zorder=2)
        ax.scatter(sub["d1"],sub["d2"],s=15,color=SLOTS[k%len(SLOTS)],
                   linewidths=0.4,edgecolors="white",zorder=4)
        ax.plot(np.cos(th),np.sin(th),lw=0.7,color="#9a9a97",zorder=3)
        ax.set_aspect("equal"); ax.set_xlim(-1.25,1.25); ax.set_ylim(-1.25,1.25)
        ax.set_xticks([-1,0,1]); ax.set_yticks([-1,0,1])
        ax.grid(True,which="major",lw=0.4,color="#ececea",zorder=0)
        ax.tick_params(labelsize=6,length=2,color="#9a9a97")
        for sp in ax.spines.values(): sp.set_linewidth(0.7); sp.set_color("#4a4a47")
        # facet strip: light grey fill, dark rule beneath, BARE value
        ax.set_title(p, fontsize=7.5, color=INK, pad=4,
                     bbox=dict(facecolor="#ececea", edgecolor="none", pad=2.6))
        ax.annotate("", xy=(0,1.0), xytext=(1,1.0), xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="-", lw=0.9, color="#4a4a47"))
    fig.supxlabel("primera dimensión", fontsize=8, color=INK)
    fig.supylabel("segunda dimensión", fontsize=8, color=INK)
    fig.suptitle(title, fontsize=9, color=INK)
    fig.tight_layout(rect=[0.015,0.015,1,0.965])
    for ext in ("pdf","png"):
        fig.savefig(f"{outstem}.{ext}", dpi=200 if ext=="png" else None)
    plt.close(fig)
    return len(parties), len(df)
