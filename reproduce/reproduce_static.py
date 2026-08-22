#!/usr/bin/env python3
"""
Re-run the static three-engine comparison and check it against the committed
results, from a clean clone of this repository.

Everything needed is already here: the panels in `data/chile-static/` and
`data/us-sen90/`, the committed outputs in
`results/2026-08-20-three-engine/`, and the engine sources. This script closes
the loop, so the repository can be verified rather than only read.

    python reproduce/reproduce_static.py --faithful <path-to-dwnominate>

It runs each supplied engine over each panel, then compares the log-likelihood
it gets against the committed one and prints a per-arm verdict. Arms whose
engine is not supplied are SKIPPED and named, never quietly dropped.

BUILDING THE ENGINES

    cmake -S engine-faithful -B build-faithful -DCMAKE_BUILD_TYPE=Release
    cmake --build build-faithful -j 4

  engine-modern/ builds the same way. `modern-ltr` and `modern-audit` are two
  different builds of it; see results/2026-08-20-three-engine/README.md.

⚠ THE SVD BACKEND CHANGES THE ANSWER. Without reference LAPACK the build falls
back to Eigen's JacobiSVD and the likelihood moves by roughly 2 to 32 nats,
enough to change which engine wins on some panels. The build warns when this
happens, and every run records `svd_backend` in its cpp_summary.csv. The
committed results were produced with LAPACKE. If your numbers differ by a few
nats, check that line before looking for anything else. See
engine-faithful/external/README-DEPENDENCIES.md.

Solver settings below are the ones the committed run logs record.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMITTED = ROOT / "results" / "2026-08-20-three-engine"

# (result arm dir, panel input dir)
PANELS = [
    ("chile-static-p8",  ROOT / "data" / "chile-static" / "leg353"),
    ("chile-static-p21", ROOT / "data" / "chile-static" / "leg366"),
    ("chile-static-p23", ROOT / "data" / "chile-static" / "leg368"),
    ("us-sen90-static",  ROOT / "data" / "us-sen90"),
]

ARMS = {
    "faithful":            ("faithful",     []),
    "modern-ltr-local":    ("modern-ltr",   ["--scalar-search=local"]),
    "modern-ltr-global":   ("modern-ltr",   ["--scalar-search=global"]),
    "modern-audit-local":  ("modern-audit", ["--scalar-search=local"]),
    "modern-audit-global": ("modern-audit", ["--scalar-search=global"]),
}

SOLVER = ["--model=0", "--iterations=4", "--periods=1",
          "--dimensions=2", "--beta=5.9539", "--w2=0.3463"]

TOL = 1e-6   # relative; the engines are deterministic on a fixed backend


def summary_value(path: Path, key: str):
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split(",")
        if len(parts) >= 2 and parts[0].strip().lstrip("﻿") == key:
            return parts[1].strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("faithful", "modern-ltr", "modern-audit"):
        ap.add_argument(f"--{k}", default=None, help=f"path to the {k} executable")
    ap.add_argument("--out", default=None, help="scratch output dir (default: reproduce/_out)")
    ap.add_argument("--tolerance", type=float, default=TOL)
    args = ap.parse_args()

    engines = {k: (Path(getattr(args, k.replace("-", "_"))).resolve()
                   if getattr(args, k.replace("-", "_")) else None)
               for k in ("faithful", "modern-ltr", "modern-audit")}
    if not any(engines.values()):
        print("Supply at least one engine, e.g. --faithful build-faithful/dwnominate",
              file=sys.stderr)
        return 2

    out_root = Path(args.out).resolve() if args.out else (ROOT / "reproduce" / "_out")
    rows, skipped = [], []

    for arm_dir, panel in PANELS:
        if not panel.exists():
            skipped.append(f"{arm_dir}: panel missing at {panel}")
            continue
        seed = panel / "wnominate_coordinates.csv"
        for arm, (engine_key, extra) in ARMS.items():
            exe = engines[engine_key]
            ref = COMMITTED / arm_dir / arm / "cpp_summary.csv"
            if exe is None or not exe.exists():
                skipped.append(f"{arm_dir}/{arm}: no --{engine_key} supplied")
                continue
            if not ref.exists():
                skipped.append(f"{arm_dir}/{arm}: no committed result to compare against")
                continue
            dest = out_root / arm_dir / arm
            dest.mkdir(parents=True, exist_ok=True)
            cmd = [str(exe), f"--input-dir={panel}", f"--output-dir={dest}",
                   f"--wnominate={seed}", *SOLVER, *extra]
            with open(dest / "run.log", "w", encoding="utf-8") as f:
                f.write(f"command: {' '.join(cmd)}\n")
                f.flush()
                rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
            got = summary_value(dest / "cpp_summary.csv", "log_likelihood")
            want = summary_value(ref, "log_likelihood")
            backend = summary_value(dest / "cpp_summary.csv", "svd_backend") or "unrecorded"
            if rc != 0 or got is None:
                verdict, delta = "RUN FAILED", None
            else:
                delta = float(got) - float(want)
                verdict = "MATCH" if abs(delta) <= abs(float(want)) * args.tolerance else "DIFFERS"
            rows.append(dict(panel=arm_dir, arm=arm, verdict=verdict, got=got,
                             committed=want, delta=delta, svd_backend=backend))

    w = max([len(f"{r['panel']}/{r['arm']}") for r in rows], default=20)
    print(f"\n{'panel/arm'.ljust(w)}  {'verdict':<10} {'reproduced':>16} {'committed':>16} "
          f"{'delta':>12}  backend")
    for r in rows:
        d = "" if r["delta"] is None else f"{r['delta']:+.6f}"
        print(f"{(r['panel'] + '/' + r['arm']).ljust(w)}  {r['verdict']:<10} "
              f"{str(r['got']):>16} {str(r['committed']):>16} {d:>12}  {r['svd_backend']}")

    if skipped:
        print("\nSKIPPED (not silently dropped):")
        for s in skipped:
            print(f"  {s}")

    n_match = sum(1 for r in rows if r["verdict"] == "MATCH")
    print(f"\n{n_match}/{len(rows)} arm(s) reproduce within {args.tolerance:g} relative.")
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "REPRODUCTION-REPORT.json").write_text(
        json.dumps({"rows": rows, "skipped": skipped}, indent=2), encoding="utf-8")
    print(f"wrote {out_root / 'REPRODUCTION-REPORT.json'}")
    return 0 if rows and n_match == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
