# Controlled Fortran/C++ initialization experiment

This experiment removes the starting-map asymmetry in the older US benchmark.
Neither implementation is initialized with estimated coordinates committed by
the repository. `make_common_seed.py` derives one map from all 2,940 roll calls,
quantizes it once to IEEE float32, and writes the exact CSV consumed by both
estimators.

The controlled settings are two dimensions, a linear temporal model, initial
`beta=5.9539`, initial `w2=0.3463`, zero bill parameters, and five effective
WINT-SIGMAS-RC-LEG cycles. The R wrapper uses `niter=4`, which maps to Fortran
`IHAPPY=1..5`; C++ therefore uses `--iterations=5`. C++ must not use
`--legacy-round-starts`, because the shared seed is already quantized.

From the repository root:

```bash
python3 engine-modern/benchmarks/us-controlled/make_common_seed.py \
  --input-dir=engine-experimental/benchmarks/us/cpp_input \
  --output=engine-modern/benchmarks/us-controlled/common_start_float32.csv

engine-modern/benchmarks/us-controlled/run_cpp_controlled.sh \
  engine-modern/build/release/dwnominate-modern \
  engine-experimental/benchmarks/us/cpp_input \
  engine-modern/benchmarks/us-controlled/common_start_float32.csv \
  engine-modern/benchmarks/us-controlled/cpp_out

Rscript engine-modern/benchmarks/us-controlled/run_fortran_controlled.R \
  engine-experimental/benchmarks/us \
  engine-modern/benchmarks/us-controlled/common_start_float32.csv \
  engine-modern/benchmarks/us-controlled/fortran_out

python3 engine-modern/benchmarks/us-controlled/compare_controlled.py \
  --benchmark-dir=engine-experimental/benchmarks/us \
  --fortran-dir=engine-modern/benchmarks/us-controlled/fortran_out \
  --cpp-dir=engine-modern/benchmarks/us-controlled/cpp_out \
  --output-dir=engine-modern/benchmarks/us-controlled/comparison
```

The comparison applies one pooled orthogonal Procrustes transformation without
scaling, reports coordinate displacement by Congress, and evaluates both fitted
parameter sets with the same double-precision probit likelihood implementation.

## Initialization-sensitivity control

The retained `cpp_out` and `cpp_repo_seed_out` runs use identical data,
precision and five-cycle settings. They differ only in their initial legislator
map. Reproduce their comparison with:

```bash
python3 engine-modern/benchmarks/us-controlled/compare_initializations.py \
  --benchmark-dir=engine-experimental/benchmarks/us \
  --common-dir=engine-modern/benchmarks/us-controlled/cpp_out \
  --repo-dir=engine-modern/benchmarks/us-controlled/cpp_repo_seed_out \
  --common-seed=engine-modern/benchmarks/us-controlled/common_start_float32.csv \
  --repo-seed=engine-experimental/benchmarks/us/cpp_input/wnominate_coordinates.csv \
  --output-dir=engine-modern/benchmarks/us-controlled/initialization-comparison
```

For coordinate diagnostics, only the 523 member-period rows with at least one
observed vote are retained. The repository-start solution is aligned to the
common-start solution with an origin-fixed orthogonal transform: reflection and
rotation are allowed, while translation and scaling are not. The unit circle
therefore remains invariant.

In the recorded runs, the common seed ends at log-likelihood -37123.688755,
versus -37384.549912 for the repository Congress-111 seed after five cycles.
The 260.861157-unit gap is an initialization effect, not a comparison between
optimizers. A literal repetition of the common-seed run produced byte-identical
bill parameters, coordinates and convergence trace; only elapsed time differed.
