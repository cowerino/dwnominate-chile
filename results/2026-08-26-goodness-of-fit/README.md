# Goodness of fit, measured on one common evaluator

**2026-08-26.** Two tables, both produced by the same evaluator, so a difference
between two rows is a difference between fits and not between scorers.

| file | what it covers |
| :--- | :--- |
| `three-engine-six-panels.csv` | 3 engines x 6 panels, 18 fits, 4 cycles |
| `expanding-windows-order1.csv` | 5 grids x 3 expanding windows, 15 fits, requested order 1 |

## Why a common evaluator

Each engine reports its own likelihood, and those numbers are not directly
comparable: the arms differ in classification rule (a continuous normal CDF
against a `legacy-nearest` lookup table), in build (LAPACK backend, thread count,
fast-math), and in what they count as a valid vote. Comparing self-reported
likelihoods measures the reporters as much as the fits.

So every fit here is re-scored from its own final state, under one probability
model, with the 2.5 per cent lopsidedness screen re-applied from the vote matrices
rather than trusted from a summary file. `native_minus_self_plog` is carried in
both tables and shows how far each engine's own number sits from the common one.

The evaluator is a port of the metric computation in Julio Rojas-Mora's
cross-country optimizer-isolation suite. The port is **validated numerically, not
asserted**: running it against his own fitted state reproduces his published row
on all 16 shared columns to machine precision (largest relative difference
1.5e-16). Reproduce that check with:

    python reproduce/scripts/gof_metrics.py \
        --panel-dir <his>/data/chile-static/leg353 --periods 1 --model 0 \
        --state-dir <his>/results/.../cycle-0004/chile-static-leg353/fortran-wmay \
        --panel chile-static-leg353 --engine fortran-wmay --cycles 4 \
        --validate-against <his-metrics>/state_fit_metrics.csv

His measurements corroborate; the fits scored here are ours.

## APRE

`apre` is the Average Proportional Reduction in Error, and it appeared in no
goodness-of-fit table on this project before this one:

    APRE = (sum_j minority_j - sum_j errors_j) / sum_j minority_j

over screened roll calls `j`, where `minority_j` is the size of the losing side,
which is exactly the error count of a null model that predicts the majority every
time. Both totals are carried beside it (`minority_votes_total`,
`classification_errors_common`), so the share is never quoted without its
denominator.

APRE earns its place because raw classification percentage is dominated by
lopsided roll calls that any model gets right. On `us-static-sen90` the three
engines sit within 0.01 points of each other at about 84.8 per cent classified,
and APRE puts them at 0.493 to 0.494: the panel is genuinely hard, and the
percentage hides it. On `chile-dynamic-23p` classification separates NLopt from
the Fortran by 1.24 points while APRE separates them by 4.0.

⚠ APRE here uses the **common evaluator's** decision rule (predict yea when the
continuous probability is at or above 0.5). `classification_pct_common` is printed
next to `classification_pct_native` so the two rules can be checked against each
other before APRE is read. They are close but **not identical**: the two rules
differ by at most **0.113** percentage points across the 18 fits, on
`chile-static-leg366` / C++ ad hoc (94.777 native against 94.890 common). Every
other panel's worst case is under 0.05. That residual is the `legacy-nearest`
lookup table against the continuous normal CDF, and it is smaller than every
engine difference APRE is used to read here, but it is not zero and should not be
described as agreement.

## GMP, both bases

`gmp_native` is `exp(native_plog / N)`, the engine's own likelihood per vote
exponentiated, which is the quantity the Fortran computes internally as `GMPA` /
`GMPB` and never exports. `gmp_continuous` is the same transform of the common
evaluator's continuous likelihood. The largest gap between them across the 18 fits
is **2.2e-05**, which is itself a check that the re-scoring reproduces each
engine's own state rather than re-optimising it.

## Reading the expanding-window table

Those 15 fits are one engine (`engine-modern`) at requested order 1, across five
time grids and three expanding windows. They are **not** a three-engine
comparison, and nothing in that file speaks to engine agreement. Figures for the
same fits are under `figures/dynamic/chile-expanding-*`.

## Regenerate

    python reproduce/scripts/make_gof_table.py --set all --tag m1i4

Cell discovery is mechanical: the script walks the run directories and reads each
run's own log for its input directory, model order and period count. It prints the
cells it could not cover rather than dropping them silently.
