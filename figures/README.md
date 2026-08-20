# figures

Working figure tree for the JCC / SCCC 2026 paper: the generators, the renders they produce, and
the design rules both answer to. Published here so the three of us are testing against the same
images rather than against screenshots.

| path | what |
|---|---|
| `CONVENTION.md` | the figure convention. Ten acceptance tests; a figure is not accepted until all ten pass |
| `INTENT.md` | per-figure intent: what claim each figure carries and what form it should take |
| `generators/` | one script per figure, matplotlib, emitting vector PDF. `check_convention.py` runs the tests |
| `renders/` | output, in dated directories. The newest date is the live one |
| `reference-renders/` | earlier accepted renders kept for comparison, with `.manifest.json` receipts |

## Manifests

Renders carry a `.manifest.json` recording the generating command, every input path with its MD5,
the alignment operator, and the screens applied. Read the manifest before quoting a number off an
image. The manifests record absolute paths from the machine that produced them; treat those as
provenance, not as a path you can follow.

## Status of the modern-engine arm, 2026-08-20

**Every `modern` series in this tree was produced by a pre-fix `dwnominate-modern` build.** No
output on disk carries the `scalar_search` row that the current engine writes unconditionally, and
the `[UC5TRACE]` lines in the run logs show the scalar search running on global bounds
(`w2 [0, 1.5]`, `beta [0.05, 25]`) rather than the re-centred local box the current engine defaults
to. The runs are dated 2026-08-17; the fixed binary was built 2026-08-19 and has not been re-run.

This matters most in `renders/2026-08-19-engine-comparison/`, which attributes modern's dim-2
collapse on legislatura 366 to COBYLA linearising the ball constraint. That attribution is not
settled: see the correction note in that directory. Do not quote the modern arm as a property of
the modern engine until it has been re-run.
