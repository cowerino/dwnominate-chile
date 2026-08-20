#!/usr/bin/env python3
"""Shared paths for the figure generators.

Exists because all seven generators hard-coded `PAPER / "figs/v2026-08-11"`, an
output directory the 2026-08-13 reorganization retired.  Every generator wrote
there; the directory no longer exists in the schema, so every generator was one
run away from recreating a retired path at the paper root.

RULES THIS ENCODES
------------------
1. Generators render into `figures/renders/<UTC date>/`, a fresh dated directory
   per rendering day.  Renders are working artifacts, not decisions.
2. `figures/reference-renders/` is a **frozen record of what we tried** and is
   never written to.  `2026-07/` and `2026-08-11/` are read-only history.
3. A survivor is copied by hand into `../draft/figures/` when it is chosen.
   Nothing copies itself: the copy is the decision, and a decision is Roberto's.

Panel and period constants live here too, so a generator cannot disagree with
`_coords` about which panel it is reading.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

REPO = Path("C:/Users/cow/Documents/GitHub/quevotan-db")
PAPER = Path("C:/Users/cow/Documents/thesis-quevotan/papers/jcc-2026")

FIGURES = PAPER / "figures"
RENDERS = FIGURES / "renders"                 # writable, dated, disposable
REFERENCE_RENDERS = FIGURES / "reference-renders"   # frozen, never written
DRAFT_FIGURES = PAPER / "draft" / "figures"   # survivors only, copied by hand

# The Chilean panel the fits were run on, and its period count.  See
# `_coords.DEFAULT_PANEL` for why it is this directory and not `reproduce/input`.
PANEL_DIR = REPO / "reproduce/out/chile/cpp_input"
N_PERIODS = 23


def render_dir(create: bool = True) -> Path:
    """`figures/renders/<UTC date>/`.  One directory per rendering day."""
    d = RENDERS / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d
