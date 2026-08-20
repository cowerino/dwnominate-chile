#!/usr/bin/env python3
"""The mechanical half of the figure acceptance test.  CONVENTION.md section 6.

Four of the ten acceptance tests are measurable and are implemented here.  The
other six need a human and are listed at the end of every report so that a pass
here is never mistaken for acceptance.

    A2  chromatic pixel count      zero chromatic pixels
    A3  print-size read            no type smaller than the 8 pt caption, at scale 1.0
    A4  font type                  no Type 3 font
    A8  vector                     PDF, and no raster image drawn inside it

CONVENTION.md: "a convention that is not checked will drift within two
sessions."  This is that check.  It reads finished files, renders nothing, and
decides nothing.

HOW EACH TEST IS MEASURED, since a check nobody understands gets ignored:

  A2  Two independent probes, because they fail differently.
      (i) every colour operator in the PDF content stream: `r g b rg` / `RG` /
          `sc` / `SCN`.  A greyscale figure sets only equal components (or uses
          the `g`/`G` operators).  This catches colour that is drawn but
          invisible at the sampled resolution, which a pixel count cannot.
      (ii) the companion PNG, if one exists, pixel by pixel.  This is how the
          reference figure was verified, so it is the comparable number.
  A3  every `/F<n> <size> Tf` in the content stream.  Matplotlib writes the
      point size directly, and the convention says author at final size and
      include at scale 1.0, so the number in the file is the number on paper.
      A figure included at a scale other than 1.0 defeats this test, which is
      why the convention forbids it.
  A4  `/Subtype /Type3` anywhere in the file.  IEEE PDF eXpress rejects Type 3.
  A8  `/Subtype /Image`.  A vector PDF with a raster image pasted inside it is
      a raster figure with extra steps.

Usage:
    python check_convention.py <file-or-directory> [...]
    python check_convention.py ../renders/2026-08-13
    python check_convention.py --json report.json ../renders/2026-08-13
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from pathlib import Path

CAPTION_PT = 8.0          # CONVENTION.md section 4: nothing smaller than the caption
BODY_PT = 9.0             # for reporting only; ticks and strip labels should reach ~9
CHROMATIC_SAMPLE = 150_000
GREY_TOL = 0             # exact equality of R, G, B. Monochrome means monochrome.

_STREAM = re.compile(rb"stream\r?\n(.*?)endstream", re.S)
_TF = re.compile(rb"/[A-Za-z0-9]+\s+([0-9.]+)\s+Tf")
_RG = re.compile(rb"([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+(rg|RG)\b")
_SC = re.compile(rb"([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+(sc|SC|scn|SCN)\b")


def _content(pdf: bytes) -> bytes:
    """Every stream in the file, inflated where it is deflated."""
    out = []
    for m in _STREAM.finditer(pdf):
        raw = m.group(1)
        try:
            out.append(zlib.decompress(raw))
        except zlib.error:
            out.append(raw)
    return b"\n".join(out)


def check_pdf(path: Path) -> dict:
    pdf = path.read_bytes()
    body = _content(pdf)

    # -- A4, A8 -----------------------------------------------------------
    type3 = pdf.count(b"/Type3")
    images = pdf.count(b"/Subtype /Image") + pdf.count(b"/Subtype/Image")

    # -- A3 ---------------------------------------------------------------
    sizes = sorted({round(float(s), 3) for s in _TF.findall(body)})
    smallest = min(sizes) if sizes else None

    # -- A2 (i) -----------------------------------------------------------
    chromatic_ops = []
    for r, g, b, op in _RG.findall(body) + _SC.findall(body):
        r, g, b = float(r), float(g), float(b)
        if not (r == g == b):
            chromatic_ops.append((r, g, b, op.decode()))
    uniq_ops = sorted({c[:3] for c in chromatic_ops})

    res = {
        "file": str(path),
        "kind": "pdf",
        "A4_type3_fonts": type3,
        "A4_pass": type3 == 0,
        "A8_vector": True,
        "A8_raster_images_inside": images,
        "A8_pass": images == 0,
        "A3_font_sizes_pt": sizes,
        "A3_smallest_pt": smallest,
        "A3_pass": bool(sizes) and smallest >= CAPTION_PT,
        "A2_chromatic_colour_ops": len(chromatic_ops),
        "A2_distinct_chromatic_colours": [list(c) for c in uniq_ops[:20]],
        "A2_ops_pass": len(chromatic_ops) == 0,
    }
    if not sizes:
        res["A3_note"] = ("no text operators found; either the figure has no "
                          "text or the type was converted to paths, which "
                          "defeats this test and is not permitted")
    return res


def check_png(path: Path) -> dict:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    step = max(1, (w * h) // CHROMATIC_SAMPLE)
    sampled = chromatic = 0
    worst = None
    i = 0
    for y in range(h):
        for x in range(w):
            i += 1
            if i % step:
                continue
            r, g, b = px[x, y]
            sampled += 1
            spread = max(r, g, b) - min(r, g, b)
            if spread > GREY_TOL:
                chromatic += 1
                if worst is None or spread > worst[0]:
                    worst = (spread, x, y, (r, g, b))
    return {
        "file": str(path),
        "kind": "png",
        "A2_pixels_sampled": sampled,
        "A2_chromatic_pixels": chromatic,
        "A2_pass": chromatic == 0,
        "A2_worst_pixel": (None if worst is None else
                           {"spread": worst[0], "xy": [worst[1], worst[2]],
                            "rgb": list(worst[3])}),
        "A8_pass": False,
        "A8_note": "raster. CONVENTION.md section 4: vector at every stage.",
    }


HUMAN_TESTS = [
    "A1  greyscale proof: every category still distinguishable, every ramp still in order",
    "A5  cover-the-caption: a reader who cannot see the caption can state the claim",
    "A6  illegal-comparison: the caption forbids no comparison the layout invites",
    "A7  one-sentence caption, and no plot title",
    "A9  frame declaration: the caption names the frame and the alignment operator",
    "A10 manifest exists and every depicted number is a row in the number registry",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    files = []
    for t in args.targets:
        p = Path(t)
        if p.is_dir():
            files += sorted(p.glob("*.pdf")) + sorted(p.glob("*.png"))
        elif p.exists():
            files.append(p)
        else:
            print(f"missing: {p}")
    if not files:
        print("nothing to check")
        return 2

    reports, failed = [], 0
    for f in files:
        r = check_pdf(f) if f.suffix.lower() == ".pdf" else check_png(f)
        reports.append(r)
        keys = [k for k in r if k.endswith("_pass")]
        bad = [k for k in keys if not r[k]]
        if bad:
            failed += 1
        mark = "PASS" if not bad else "FAIL"
        print(f"\n{mark}  {f.name}")
        if r["kind"] == "pdf":
            print(f"      A2 chromatic colour operators   {r['A2_chromatic_colour_ops']}")
            if r["A2_distinct_chromatic_colours"]:
                for c in r["A2_distinct_chromatic_colours"][:6]:
                    print(f"         rgb {c[0]:.3f} {c[1]:.3f} {c[2]:.3f}")
            print(f"      A3 smallest type                {r['A3_smallest_pt']} pt "
                  f"(floor {CAPTION_PT})")
            print(f"      A4 Type 3 fonts                 {r['A4_type3_fonts']}")
            print(f"      A8 raster images inside         {r['A8_raster_images_inside']}")
        else:
            print(f"      A2 chromatic pixels             {r['A2_chromatic_pixels']} "
                  f"of {r['A2_pixels_sampled']} sampled")
            print(f"      A8 raster, not vector")

    print(f"\n{len(files) - failed} of {len(files)} files pass the mechanical tests.")
    print("\nSTILL UNTESTED. These need a human and no script will ever do them:")
    for t in HUMAN_TESTS:
        print("  " + t)
    print("\nA figure is accepted only when all ten pass and the result is "
          "recorded in its manifest.")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(reports, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
