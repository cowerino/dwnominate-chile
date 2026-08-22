#!/usr/bin/env python3
"""
Falsification demonstration: reintroduce the 2026-08-15 alignment defect and show
that the reproduction FAILS.

The paper's claim is that `engine-faithful/` reproduces the canonical Fortran. A
claim that cannot fail is not worth much, so this script makes it fail on
purpose, in a scratch tree that is deleted afterwards.

    python validation/run_falsification.py

What it does:

  1. copies engine-faithful/ into a scratch directory
  2. applies validation/defect-alignment.patch, restoring the misalignment
  3. builds BOTH the clean and the defective engine with the same toolchain
  4. runs both over the static panels in data/
  5. reports defective-vs-clean, and clean against results/
  6. deletes the scratch tree

BOTH ENGINES ARE BUILT HERE ON PURPOSE. The SVD backend moves the likelihood by
2 to 32 nats on its own (see reproduce/README.md), so comparing a defective build
against the committed numbers would confound the defect with the backend.
Building both the same way isolates the defect: the clean-vs-defective delta is
the defect and nothing else.

THE DEFECT. `prepareRollCallData` used to reorder `voteCodes` into projection
order while `coords` stayed in natural order, so `voteCodes[i]` belonged to
legislator `sortedIndices[i]` while `coords.row(i)` belonged to legislator `i`.
The NS>=2 CUTPLANE path consumes them together, so it classified a shuffled
pairing. Measured when found: 27.84 percent roll-call error against 5.58 percent
for the aligned optimum. The canonical Fortran passes XMAT and LDATA in natural
order and sorts internally (RSORT plus MVOTE(I)=MM(LLL(I)), CUTPLANE:4293-4296),
so natural order on both sides is the faithful arrangement.

Fixed in quevotan-api@01eff25; the NS==1 half followed in @77bfeea.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine-faithful"
PATCH = ROOT / "validation" / "defect-alignment.patch"
COMMITTED = ROOT / "results" / "2026-08-20-three-engine"

PANELS = [
    ("chile-static-p8", ROOT / "data" / "chile-static" / "leg353"),
    ("chile-static-p21", ROOT / "data" / "chile-static" / "leg366"),
    ("chile-static-p23", ROOT / "data" / "chile-static" / "leg368"),
    ("us-sen90-static", ROOT / "data" / "us-sen90"),
]
SOLVER = ["--model=0", "--iterations=4", "--periods=1",
          "--dimensions=2", "--beta=5.9539", "--w2=0.3463"]


def summary_value(path, key):
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split(",")
        if len(parts) >= 2 and parts[0].strip().lstrip("﻿") == key:
            return parts[1].strip()
    return None


def build(src, build_dir, log):
    with open(log, "w", encoding="utf-8") as f:
        cmds = [
            ["cmake", "-S", str(src), "-B", str(build_dir),
             "-G", "MinGW Makefiles", "-DCMAKE_BUILD_TYPE=Release"],
            ["cmake", "--build", str(build_dir), "-j", "4"],
        ]
        for cmd in cmds:
            f.write("\n$ " + " ".join(cmd) + "\n")
            f.flush()
            if subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode != 0:
                return None
    for name in ("dwnominate.exe", "dwnominate"):
        if (build_dir / name).exists():
            return build_dir / name
    return None


def run_panels(exe, out_root):
    got = {}
    for arm_dir, panel in PANELS:
        if not panel.exists():
            continue
        dest = out_root / arm_dir
        dest.mkdir(parents=True, exist_ok=True)
        cmd = [str(exe), "--input-dir=" + str(panel), "--output-dir=" + str(dest),
               "--wnominate=" + str(panel / "wnominate_coordinates.csv")] + SOLVER
        with open(dest / "run.log", "w", encoding="utf-8") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
        got[arm_dir] = (summary_value(dest / "cpp_summary.csv", "log_likelihood"),
                        summary_value(dest / "cpp_summary.csv", "svd_backend") or "unrecorded")
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", default=None,
                    help="scratch dir (default: validation/_scratch, deleted after)")
    ap.add_argument("--keep", action="store_true", help="do not delete the scratch tree")
    args = ap.parse_args()

    scratch = Path(args.scratch).resolve() if args.scratch else (ROOT / "validation" / "_scratch")
    if scratch.exists():
        shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    keep = args.keep

    try:
        clean_src = scratch / "clean"
        bad_src = scratch / "defective"
        shutil.copytree(ENGINE, clean_src, ignore=shutil.ignore_patterns("build*", "_*"))
        shutil.copytree(clean_src, bad_src)

        rc = subprocess.run(["git", "apply", "-p1", str(PATCH)], cwd=str(bad_src),
                            capture_output=True, text=True)
        if rc.returncode != 0:
            print("FAILED to apply the defect patch:\n" + rc.stderr, file=sys.stderr)
            keep = True
            return 2
        print("applied validation/defect-alignment.patch to the scratch copy")

        clean_exe = build(clean_src, scratch / "build-clean", scratch / "build-clean.log")
        bad_exe = build(bad_src, scratch / "build-defective", scratch / "build-defective.log")
        if not clean_exe or not bad_exe:
            print("build failed; see the build logs in the scratch tree", file=sys.stderr)
            keep = True
            return 2
        print("built clean and defective engines")

        clean = run_panels(clean_exe, scratch / "out-clean")
        bad = run_panels(bad_exe, scratch / "out-defective")

        rows = []
        for arm_dir, _ in PANELS:
            if arm_dir not in clean or arm_dir not in bad:
                continue
            c, backend = clean[arm_dir]
            b, _ = bad[arm_dir]
            ref = summary_value(COMMITTED / arm_dir / "faithful" / "cpp_summary.csv",
                                "log_likelihood")
            rows.append(dict(
                panel=arm_dir, clean=c, defective=b, committed=ref,
                defect_delta=(float(b) - float(c)) if (b and c) else None,
                clean_vs_committed=(float(c) - float(ref)) if (c and ref) else None,
                svd_backend=backend))

        w = max([len(r["panel"]) for r in rows]) if rows else 16
        print("\n" + "panel".ljust(w) + "  " + "clean".rjust(16) + " "
              + "defective".rjust(16) + " " + "defect delta".rjust(14) + "  backend")
        for r in rows:
            d = "" if r["defect_delta"] is None else "%+.4f" % r["defect_delta"]
            print(r["panel"].ljust(w) + "  " + str(r["clean"]).rjust(16) + " "
                  + str(r["defective"]).rjust(16) + " " + d.rjust(14) + "  " + r["svd_backend"])

        broke = [r for r in rows if r["defect_delta"] is not None and abs(r["defect_delta"]) > 1.0]
        print("\nThe defect changes the likelihood on %d/%d panel(s)." % (len(broke), len(rows)))
        print("Expected: the reproduction FAILS with the defect reintroduced. That is the point.")
        report = ROOT / "validation" / "FALSIFICATION-REPORT.json"
        report.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
        print("wrote " + str(report))
        return 0 if rows and len(broke) == len(rows) else 1
    finally:
        if not keep:
            shutil.rmtree(scratch, ignore_errors=True)
            print("scratch tree deleted")


if __name__ == "__main__":
    raise SystemExit(main())
