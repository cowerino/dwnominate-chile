#!/usr/bin/env python3
"""What the frame correction (M-2) does to the numbers fig1 draws.

Runs fig1's exact construction twice, once in the exported GLOBAL-t frame it
used until 2026-08-13 and once in the LOCAL-t frame the estimator actually used,
and reports the difference.  **Renders nothing and decides nothing.**  The
figure's gate constants come from `_joint_niter4.out` k=16, which was computed
in the global frame; this script produces the evidence the number registry needs
in order to decide what the corrected constants are.  Changing them is a
registry decision, not a generator's.

Three separate effects are separated on purpose, because they are three
different claims:

  (1) ROSTER.  The global frame's roster is built from a padded export, which
      writes a row for every (legislator, period) cell whether or not the
      legislator served that period.  The local frame emits served placements
      only, so the roster shrinks.  Placements that vanish are placements that
      never existed.  This is M-4.
  (2) COORDINATES.  Every partial-span legislator's coordinates move, because
      the curve is re-evaluated over their own span rather than the panel's.
  (3) The two together, which is what a corrected fig1 would show.

Run:  python frame_audit.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _paths
from _coords import load_coords_local, load_coords_raw, served_periods

_spec = importlib.util.spec_from_file_location("fig1", HERE / "fig1-asymmetry.py")
fig1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fig1)


def build(frame: str, p2leg, served):
    """fig1's join, under one frame. Returns (keys, fits, per_leg)."""
    fits = {}
    for name, d in fig1.FIT_DIRS.items():
        co = (load_coords_raw(d) if frame == "global"
              else load_coords_local(d, _paths.N_PERIODS, served))
        out = {}
        for (lid, per), (c1, c2) in co.items():
            leg = p2leg.get(per)
            if leg in fig1.FIG_LEGS:
                out[(leg, str(lid))] = (c1, c2)
        fits[name] = out
    return fits


def stats(keys, fits, ref, se):
    R = np.array([ref[k] for k in keys])
    S = np.stack([R] + [fig1.proc(np.array([fits[n][k] for k in keys]), R)
                        for n in fig1.FIT_DIRS])
    sd = np.std(S, axis=0)
    agree = (S > 0).all(0) | (S < 0).all(0)
    med_sd = [float(np.median(sd[:, d])) for d in (0, 1)]
    med_se = [float(np.median([se[k][d] for k in keys if k in se])) for d in (0, 1)]
    flip = [float(np.mean(~agree[:, d])) for d in (0, 1)]
    return {"n": len(keys), "med_sd": med_sd, "med_se": med_se, "flip": flip,
            "ratio": [med_sd[d] / med_se[d] for d in (0, 1)],
            "se_coverage": sum(1 for k in keys if k in se)}


def main():
    p2leg = {int(d["period_index"]): int(d["legislatura"])
             for d in csv.DictReader(open(fig1.MAP_CSV))}
    leg2p = {v: k for k, v in p2leg.items()}
    served = served_periods(_paths.PANEL_DIR, _paths.N_PERIODS)

    ref = {}
    for d in csv.DictReader(open(fig1.REF_CSV)):
        try:
            leg = int(float(d["legislatura"]))
        except ValueError:
            continue
        if leg in fig1.FIG_LEGS:
            ref[(leg, str(d["legislator_id"]))] = (float(d["x"]), float(d["y"]))

    # bootstrap bank, exactly as fig1 reads it
    bank_keys = np.load(fig1.DENOM_BANK / "keys.npy")
    xref = np.load(fig1.DENOM_BANK / "Xref.npy")
    files = [f for w in (0, 1, 2) for f in sorted((fig1.DENOM_BANK / f"w{w}").glob("t*.npy"))]
    A = np.stack([np.load(f) for f in files])
    D = A - xref[None, :, :]
    seb = np.sqrt(np.nansum(D * D, axis=0) / (A.shape[0] - 1))
    se = {}
    for i, s in enumerate(bank_keys):
        lid, per = str(s).split("|")
        leg = p2leg.get(int(per))
        if leg in fig1.FIG_LEGS:
            se[(leg, lid)] = (float(seb[i, 0]), float(seb[i, 1]))

    fits_g = build("global", p2leg, served)
    fits_l = build("local", p2leg, served)
    keys_g = sorted(k for k in ref if all(k in f for f in fits_g.values()))
    keys_l = sorted(k for k in ref if all(k in f for f in fits_l.values()))
    dropped = sorted(set(keys_g) - set(keys_l))
    gained = sorted(set(keys_l) - set(keys_g))

    print(f"\nfig1 roster under each frame")
    print(f"  global (exported, padded)   {len(keys_g)} placements")
    print(f"  local  (fitted, served)     {len(keys_l)} placements")
    print(f"  dropped by the correction   {len(dropped)}")
    print(f"  gained                      {len(gained)}")

    print(f"\nthe dropped placements: legislator, legislatura, period, served span")
    for leg, lid in dropped:
        per = leg2p.get(leg)
        srv = served.get(lid, [])
        print(f"  leg {lid:>6}  legislatura {leg}  period {per}  "
              f"served kk={len(srv)}  {srv}")

    b_g = stats(keys_g, fits_g, ref, se)
    b_l = stats(keys_l, fits_l, ref, se)
    b_gc = stats(keys_l, fits_g, ref, se)     # global coords, corrected roster

    rows = [("global frame, global roster (what fig1 drew)", b_g),
            ("global frame, corrected roster (roster effect alone)", b_gc),
            ("local frame,  corrected roster (corrected fig1)", b_l)]
    print(f"\n{'':54s} {'n':>4} {'medSD1':>8} {'medSD2':>8} "
          f"{'flip1':>7} {'flip2':>7} {'ratio2':>7}")
    for label, b in rows:
        print(f"  {label:52s} {b['n']:>4} {b['med_sd'][0]:>8.4f} {b['med_sd'][1]:>8.4f} "
              f"{100*b['flip'][0]:>6.1f}% {100*b['flip'][1]:>6.1f}% {b['ratio'][1]:>7.2f}")

    print(f"\ngate constants fig1 currently asserts (global frame, k=16 row):")
    print(f"  sd1 {fig1.GATE_SD1}  sd2 {fig1.GATE_SD2}  ratio2 {fig1.GATE_RATIO2}  "
          f"flip1 {fig1.GATE_FLIP1}  flip2 {fig1.GATE_FLIP2}  n {fig1.GATE_N_KEYS}")

    print(f"\nCAVEAT, and it is not small. The denominator bank "
          f"({fig1.DENOM_LABEL}) was banked in the global frame. The ratio "
          f"column above therefore mixes a corrected numerator with an "
          f"uncorrected denominator and is NOT a publishable number. Pablo's "
          f"quevotan-db#3 run banks with the corrected reader; the ratio is "
          f"settled there, not here.")

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "roster": {"global": len(keys_g), "local": len(keys_l),
                   "dropped": [{"legislatura": leg, "legislator_id": lid,
                                "period": leg2p.get(leg),
                                "served_kk": len(served.get(lid, [])),
                                "served": served.get(lid, [])}
                               for leg, lid in dropped],
                   "gained": [{"legislatura": leg, "legislator_id": lid}
                              for leg, lid in gained]},
        "statistics": {label: b for label, b in rows},
        "current_gates": {"sd1": fig1.GATE_SD1, "sd2": fig1.GATE_SD2,
                          "ratio2": fig1.GATE_RATIO2, "flip1": fig1.GATE_FLIP1,
                          "flip2": fig1.GATE_FLIP2, "n_keys": fig1.GATE_N_KEYS},
        "denominator_caveat": ("bank banked in the global frame; ratio column "
                               "mixes frames and is not publishable"),
    }
    dest = _paths.render_dir() / "frame-audit.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
