# Reproducing the static three-engine comparison

Everything this needs is already in the repository: the panels in `data/`, the
committed outputs in `results/2026-08-20-three-engine/`, and the engine sources.
`reproduce_static.py` closes the loop, so you can **verify** the numbers rather
than compare them by eye.

## Quick start

    cmake -S engine-faithful -B build-faithful -DCMAKE_BUILD_TYPE=Release
    cmake --build build-faithful -j 4
    python reproduce/reproduce_static.py --faithful build-faithful/dwnominate

It runs each panel, compares the log-likelihood against the committed result, and
prints a verdict per arm. Arms whose engine you did not supply are listed as
skipped rather than quietly dropped.

## Read the `backend` column before anything else

The SVD backend changes the answer. Both outcomes below were measured on
2026-08-22, same source, same panels, same flags. **The only difference is
whether reference LAPACK was present at build time.**

With LAPACKE, which is what the committed results were produced with:

    panel/arm                  verdict          reproduced        committed        delta  backend
    chile-static-p8/faithful   MATCH          -1132.370286     -1132.370286    +0.000000  lapacke
    chile-static-p21/faithful  MATCH          -6276.201346     -6276.201346    +0.000000  lapacke
    chile-static-p23/faithful  MATCH         -13296.521959    -13296.521959    +0.000000  lapacke
    us-sen90-static/faithful   MATCH         -15457.166891    -15457.166891    +0.000000  lapacke

Without it, falling back to Eigen's own JacobiSVD:

    chile-static-p8/faithful   DIFFERS        -1138.778239     -1132.370286    -6.407953  eigen_jacobi
    us-sen90-static/faithful   DIFFERS       -15435.597141    -15457.166891   +21.569750  eigen_jacobi

Six to twenty-two nats, from the linear-algebra backend alone. If your run says
`DIFFERS` and the backend is `eigen_jacobi`, you have not found a discrepancy in
the model; you have built a different numerical configuration. The build warns
about this at configure time, and every run records the backend it used in its
own `cpp_summary.csv`.

To build the published configuration, see
`engine-faithful/external/README-DEPENDENCIES.md`.

## The modern arms

`modern-ltr` and `modern-audit` are two builds of `engine-modern/`; `-local` and
`-global` select `--scalar-search`. Pass them with `--modern-ltr` and
`--modern-audit`. See `results/2026-08-20-three-engine/README.md`.

## What is not here

This covers the **static** comparison end to end. The dynamic panels and the
figure pipeline are reproduced from the committed inputs and results in `data/`
and `results/`, but without a single-command runner of this kind yet.
