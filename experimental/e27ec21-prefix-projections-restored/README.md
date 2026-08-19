# engine-experimental

The most recent state of the module, including work that was never merged to trunk.
`../engine/` is the trunk build (`f01e747`, 2026-06-13) and is what the paper's
reported runs use. Prefer it unless you specifically want what is below.

This tree is `e27ec21` (2026-08-06), the newest commit in the module. It differs from
trunk in exactly one place: **the REQ-004 roll-call midpoint unit-sphere projection is
restored** in `src/rollcall_optimizer.cpp:473`.

That restoration is a **measured negative result and is deliberately not merged.**
It is kept because the reasoning is worth more than the outcome: REQ-004 removed the
projection after reading the reference's likelihood evaluator and finding no constraint
there, but the constraint is real and lives one level up, in the grid search that calls
the evaluator (`dwnom2004.f:3299`). The supporting observation was also a column
misread: the reference writes `(DYN(I,K),ZMID(I,K),K=1,NS)`, so the row cited as a
midpoint of norm 1.69 is actually (spread, midpoint) interleaved, and the real midpoint
is inside the ball. The change was right; the argument for it was wrong. Restoring the
projection costs classification 93.49% to 93.13% and about 9,478 nats.

`unmerged-patches/` holds work that is on neither tree:

- `req004-clamp-restore.patch` and `.commit.txt` — the above, as a patch against trunk.
- `req006-rc-ninc25-normal_cdf.patch` — an unmerged `normal_cdf.cpp` divergence from
  branch `experiment/req006-rc-ninc25` (`dce51b4`). Never evaluated to a verdict.

Note `EXPERIMENTS.md` in both trees still records REQ-004 as a clean faithfulness fix
and predates the correction above.
