#!/usr/bin/env python3
"""Frame-correct coordinate reader for the figure path.  Closes M-2.

WHY THIS EXISTS
---------------
The C++ export evaluates each legislator's Legendre polynomial at a GLOBAL t
spanning all `n_periods` periods of the panel (`getCoordinatesAtPeriod`,
`include/dwnominate.hpp:291`):

    t = -1 + 2*(period-1)/(numPeriods-1),   numPeriods = 23 for this panel

while the optimizer and the final likelihood evaluate it at a LOCAL t spanning
only the periods that legislator actually served (`reconstructLegislatorCoords`,
`src/dwnominate.cpp:1516-1531`):

    xinc = 2/(kk-1),  kk = servedPeriods.size(),  t = -1 + r*xinc

The two agree only for a legislator who served the whole panel: 14 of 338 here.
For the other 324 the exported coordinate is that legislator's own curve
evaluated at the wrong point.  **The raw export is therefore not the fitted
configuration**, and any figure drawn from it is drawn in a frame the estimator
never used.

Provenance: `findings/FINDING-export-frame-2026-08-12.md` (supersedes
`FINDING-coordinate-frame-2026-08-11.md`).  Found by Pablo on another machine,
quevotan-db#3, 2026-08-11.

The numerics of `load_coords_local` are lifted verbatim from
`tools/analysis/_pablo_issue3_attachments/julio_route2_bootstrap.py:120`, which
is the version the pooled bootstrap bank was computed with.  Do not "improve"
the arithmetic: it mirrors the C++ source, not a mathematical ideal.  In
particular the least-squares refit of the Legendre coefficients from the
exported points is exact to ~1e-15 (the export is a polynomial evaluation, so
recovering its coefficients is inversion, not estimation) and that is what
`self_test` checks.

WHAT THIS ALSO FIXES, INCIDENTALLY
----------------------------------
The export pads: it writes a row for every (legislator, period) cell of the
panel, not for served placements only.  7,774 rows against 2,855 served on this
panel.  `load_coords_local` only ever emits served placements, so a generator
that reads through it cannot compute a statistic over padded rows.  That is the
figure-path half of M-3.  It does not fix any number already computed elsewhere
over the padded set; use `padding_report()` to state the counts in a manifest.

USAGE
-----
    from _coords import served_periods, load_coords_local, padding_report

    served = served_periods(PANEL_DIR, 23)                 # cached
    co     = load_coords_local(FIT_DIR, 23, served)         # (leg_id, period) -> (c1, c2)

Self-check from the command line:

    python _coords.py <fit_dir> [<panel_dir>]
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

YES, NAY, MISS = 1, 6, 9

# The panel and the fits this module is used against.  Both are asserted, never
# assumed: see `assert_panel_matches_fit`.
DEFAULT_N_PERIODS = 23

# The panel the Chilean fits were actually run on.  NOT `reproduce/input`, which
# is a different, larger matrix (1,345,546 cast votes against this one's
# 1,266,034) and does not reproduce any fit's vote count.  Established
# 2026-08-13 by the screened-count match; the guard exists because the two
# directories are one path segment apart and the wrong one fails silently.
DEFAULT_PANEL = Path(
    "C:/Users/cow/Documents/GitHub/quevotan-db/reproduce/out/chile/cpp_input")

_CACHE = Path(__file__).resolve().parent / ".cache"


# ---------------------------------------------------------------------------
# 1.  SERVED PERIODS
# ---------------------------------------------------------------------------
def _panel_fingerprint(votes_dir: Path, n_periods: int) -> str:
    """Identity of the panel on disk: name, size and mtime of every matrix."""
    h = hashlib.md5()
    for p in range(1, n_periods + 1):
        f = votes_dir / f"votes_matrix_p{p}.csv"
        if f.exists():
            st = f.stat()
            h.update(f"{f.name}|{st.st_size}|{int(st.st_mtime)}".encode())
    return h.hexdigest()[:16]


def served_periods(votes_dir, n_periods: int = DEFAULT_N_PERIODS,
                   use_cache: bool = True) -> dict[str, list[int]]:
    """legislator_id -> sorted periods in which they cast at least one YES or NAY.

    Mirrors `src/dwnominate.cpp:225-244` (`loadLegislators`): `congressToDataIndex`
    is filled from periods where the legislator has a non-missing vote, not from
    every row of the matrix.  A legislator present in the matrix but never voting
    therefore serves zero periods and holds no fitted placement at all.

    ON THE UNSCREENED MATRIX, DELIBERATELY.  The engine computes the 2.5 %
    lopsidedness screen into `validRollCalls_` (`dwnominate.cpp:145-187`) but
    `loadLegislators` never consults it: the presence scan tests
    `votes_.isMissing(i, j)` alone, over all roll calls.  So the span that sets
    local t is the *unscreened* span, and this function must match that, not the
    likelihood's vote set.  Verified against the source 2026-08-13.

    The two differ for 5 of 338 legislators here (ids 151, 170, 173, 202, 211),
    who cast votes in a period where every roll call they voted on was later
    dropped by the screen.  Their Legendre curve is therefore stretched over a
    span that includes a period contributing no likelihood term.  That is the
    engine's behaviour, reproduced here on purpose.  Whether the Fortran does
    the same is unchecked.
    """
    votes_dir = Path(votes_dir)
    key = _panel_fingerprint(votes_dir, n_periods)
    cache = _CACHE / f"served-{key}.json"
    if use_cache and cache.exists():
        return {k: v for k, v in json.loads(cache.read_text()).items()}

    served: dict[str, set] = {}
    for p in range(1, n_periods + 1):
        path = votes_dir / f"votes_matrix_p{p}.csv"
        if not path.exists():
            continue
        with open(path, newline="") as f:
            r = csv.reader(f)
            next(r)                                   # header: roll-call ids
            for row in r:
                leg = str(row[0])
                for v in row[1:]:
                    try:
                        code = int(float(v))
                    except ValueError:
                        code = MISS
                    if code in (YES, NAY):
                        # a legislator serves period p on their first cast vote;
                        # scanning the rest of the row cannot change that.
                        served.setdefault(leg, set()).add(p)
                        break
    out = {leg: sorted(v) for leg, v in served.items()}
    if use_cache:
        _CACHE.mkdir(exist_ok=True)
        cache.write_text(json.dumps(out, sort_keys=True))
    return out


MARGIN_THRESHOLD = 0.025          # dwnominate.hpp:61, main_cli.cpp:471


def count_valid_votes(votes_dir, n_periods: int = DEFAULT_N_PERIODS,
                      margin_threshold: float = MARGIN_THRESHOLD) -> tuple[int, int]:
    """(votes, roll calls) surviving the engine's lopsidedness screen.

    `isRollCallValid` (`dwnominate.cpp:1371-1381`) keeps a roll call when
    min(yes, nay) / (yes + nay) >= 0.025.  Verified 2026-08-13: on this panel
    the screen takes 12,952 roll calls and 1,266,034 cast votes down to
    **6,858 roll calls and 692,839 votes**, which are exactly the counts the
    fits and the paper report.  That agreement is what proves a given panel
    directory is the one a given fit was run on.

    The engine also requires a non-zero roll-call spread, which cannot be
    evaluated from the panel alone; it does not bind here, since the vote count
    matches on the margin criterion alone.
    """
    votes_dir = Path(votes_dir)
    votes = 0
    kept = 0
    for p in range(1, n_periods + 1):
        path = votes_dir / f"votes_matrix_p{p}.csv"
        if not path.exists():
            continue
        with open(path, newline="") as f:
            r = csv.reader(f)
            ncol = len(next(r)) - 1
            yes = [0] * ncol
            nay = [0] * ncol
            for row in r:
                for j, v in enumerate(row[1:]):
                    try:
                        code = int(float(v))
                    except ValueError:
                        continue
                    if code == YES:
                        yes[j] += 1
                    elif code == NAY:
                        nay[j] += 1
        for j in range(ncol):
            tot = yes[j] + nay[j]
            if tot and min(yes[j], nay[j]) / tot >= margin_threshold:
                kept += 1
                votes += tot
    return votes, kept


def assert_panel_matches_fit(votes_dir, fit_dir, n_periods: int = DEFAULT_N_PERIODS,
                             die=None) -> int:
    """Fail loudly unless the panel's valid-vote count equals the fit's.

    A frame correction computed against the wrong panel is worse than no
    correction, because it is silent.
    """
    fail = die or (lambda m: (_ for _ in ()).throw(SystemExit(f"[_coords] {m}")))
    summary = {}
    with open(Path(fit_dir) / "cpp_summary.csv", newline="") as f:
        for row in csv.reader(f):
            if len(row) == 2 and row[0] != "parameter":
                try:
                    summary[row[0]] = float(row[1])
                except ValueError:
                    pass
    want = int(summary.get("valid_votes", -1))
    got, kept = count_valid_votes(votes_dir, n_periods)
    if want != got:
        fail(f"panel {votes_dir} yields {got:,} screened votes; fit {fit_dir} was "
             f"run on {want:,}. Wrong panel for this fit, or a different screen.")
    if int(summary.get("periods", -1)) != n_periods:
        fail(f"fit {fit_dir} has periods={summary.get('periods')}, expected {n_periods}")
    return got, kept


# ---------------------------------------------------------------------------
# 2.  COORDINATES
# ---------------------------------------------------------------------------
def _legendre(t: float, deg: int):
    return [1.0, t, (3.0 * t * t - 1.0) / 2.0, (5.0 * t ** 3 - 3.0 * t) / 2.0][:deg + 1]


def _parse_coords_full(run_dir):
    """Raw exported coords plus per-legislator effective_model, in one pass."""
    run_dir = Path(run_dir)
    for name in ("cpp_coordinates_all_periods.csv",
                 "dwnominate_coordinates_all_periods.csv"):
        path = run_dir / name
        if path.exists():
            co, mod = {}, {}
            with open(path, newline="") as f:
                for d in csv.DictReader(f):
                    leg = str(d["legislator_id"])
                    co[(leg, int(d["period"]))] = (float(d["coord1D"]), float(d["coord2D"]))
                    mod[leg] = int(d.get("effective_model", 2))
            return co, mod
    raise FileNotFoundError(f"no coordinates_all_periods.csv in {run_dir}")


def load_coords_raw(run_dir) -> dict:
    """(legislator_id, period) -> (c1, c2) exactly as exported: GLOBAL t, padded.

    Present so a generator can quantify the defect it is correcting.  Do not
    draw from this.
    """
    co, _ = _parse_coords_full(run_dir)
    return co


def load_coords_local(run_dir, n_periods: int, served: dict) -> dict:
    """(legislator_id, period) -> (c1, c2) in the frame the estimator used.

    Refit each legislator's Legendre coefficients from the exported points, then
    re-evaluate at local t over their own served span, mirroring
    `reconstructLegislatorCoords`.  Only served placements are emitted.
    """
    co, mod = _parse_coords_full(run_dir)
    out = {}
    leg_periods: dict[str, list] = {}
    for (leg, p) in co:
        leg_periods.setdefault(leg, []).append(p)
    for leg, srv in served.items():
        if leg not in mod:
            continue
        ps = sorted(leg_periods.get(leg, []))
        if not ps:
            continue
        deg = mod[leg]
        T = np.array([_legendre(-1.0 + 2.0 * (p - 1) / (n_periods - 1), deg) for p in ps])
        y1 = np.array([co[(leg, p)][0] for p in ps])
        y2 = np.array([co[(leg, p)][1] for p in ps])
        A = np.linalg.lstsq(T, y1, rcond=None)[0]
        B = np.linalg.lstsq(T, y2, rcond=None)[0]
        kk = len(srv)
        if kk > 1:
            xinc = 2.0 / (kk - 1.0)
            for r, p in enumerate(srv):
                pl = _legendre(-1.0 + r * xinc, deg)
                out[(leg, p)] = (sum(A[d] * pl[d] for d in range(deg + 1)),
                                 sum(B[d] * pl[d] for d in range(deg + 1)))
        else:
            pl = _legendre(-1.0, deg)
            for p in srv:
                out[(leg, p)] = (sum(A[d] * pl[d] for d in range(deg + 1)),
                                 sum(B[d] * pl[d] for d in range(deg + 1)))
    return out


# ---------------------------------------------------------------------------
# 3.  REPORTING, FOR MANIFESTS
# ---------------------------------------------------------------------------
def padding_report(run_dir, served: dict, n_periods: int = DEFAULT_N_PERIODS) -> dict:
    """Row counts for a figure manifest: exported, served, padded."""
    co, _ = _parse_coords_full(run_dir)
    served_cells = {(leg, p) for leg, ps in served.items() for p in ps}
    exported = set(co)
    return {
        "rows_exported": len(exported),
        "rows_served": len(served_cells),
        "rows_padded": len(exported - served_cells),
        "served_without_export": len(served_cells - exported),
        "legislators_exported": len({k[0] for k in exported}),
        "legislators_served": len(served),
    }


def frame_displacement(run_dir, served: dict, n_periods: int = DEFAULT_N_PERIODS) -> dict:
    """How far the correction moves each placement, and the invariant that
    proves it is the right correction: **a full-span legislator must not move at
    all**, because global t and local t coincide for them by construction."""
    raw = load_coords_raw(run_dir)
    loc = load_coords_local(run_dir, n_periods, served)
    full = {leg for leg, ps in served.items() if len(ps) == n_periods}
    d_full, d_part = [], []
    for (leg, p), (c1, c2) in loc.items():
        if (leg, p) not in raw:
            continue
        r1, r2 = raw[(leg, p)]
        d = float(np.hypot(c1 - r1, c2 - r2))
        (d_full if leg in full else d_part).append(d)
    return {
        "n_full_span_legislators": len(full),
        "n_partial_span_legislators": len(served) - len(full),
        "max_displacement_full_span": max(d_full) if d_full else 0.0,
        "max_displacement_partial_span": max(d_part) if d_part else 0.0,
        "mean_displacement_partial_span": float(np.mean(d_part)) if d_part else 0.0,
        "median_displacement_partial_span": float(np.median(d_part)) if d_part else 0.0,
    }


def self_test(run_dir, votes_dir, n_periods: int = DEFAULT_N_PERIODS,
              tol: float = 1e-12) -> dict:
    """The invariant, checked. Full-span legislators must displace by 0.

    `FINDING-export-frame-2026-08-12.md` states this as "full-span legislators
    displace by exactly 0.0000", verified independently of the engine.  A
    tolerance is carried anyway, per the standing rule that every float clause
    in a gate states one; the observed value is at machine epsilon.
    """
    served = served_periods(votes_dir, n_periods)
    disp = frame_displacement(run_dir, served, n_periods)
    pad = padding_report(run_dir, served, n_periods)
    ok = disp["max_displacement_full_span"] <= tol
    return {"pass": bool(ok), "tolerance": tol, **disp, **pad}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    fit = Path(sys.argv[1])
    panel = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PANEL
    n, kept = count_valid_votes(panel)
    print(f"panel           {panel}")
    print(f"screened votes  {n:,} over {kept:,} roll calls")
    assert_panel_matches_fit(panel, fit)
    print("panel/fit pair  OK (screened vote count matches the fit summary)")
    r = self_test(fit, panel)
    for k in ("rows_exported", "rows_served", "rows_padded", "served_without_export",
              "legislators_exported", "legislators_served",
              "n_full_span_legislators", "n_partial_span_legislators",
              "max_displacement_full_span", "max_displacement_partial_span",
              "mean_displacement_partial_span", "median_displacement_partial_span"):
        v = r[k]
        print(f"{k:34s} {v:,.6g}" if isinstance(v, float) else f"{k:34s} {v:,}")
    print("SELF TEST", "PASS" if r["pass"] else "FAIL")
    raise SystemExit(0 if r["pass"] else 1)
