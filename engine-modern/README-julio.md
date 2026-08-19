# DW-NOMINATE Modern C++

Modern C++20 implementation of the statistical model in the original
`DW-NOMINATE.f`. It retains the existing CSV interface and alternating model
phases, but delegates numerical likelihood maximization to established NLopt
algorithms.

## Design

The engine preserves the original probit spatial likelihood:

\[
\Pr(y_{ij}) = \Phi\left(\beta\left[e^{U_{ij}^{\text{chosen}}}
-e^{U_{ij}^{\text{other}}}\right]\right),
\qquad
U=-\sum_k w_k^2 d_k^2.
\]

The following blocks are estimated:

| Block | Solver | Declared domain |
|---|---|---|
| Roll-call midpoint and spread | NLopt COBYLA | `||midpoint|| <= 1` |
| Legislator coefficients | NLopt COBYLA | `||intercept|| <= 1` |
| `beta` and dimension weight | NLopt BOBYQA | positive identifying bounds |

COBYLA is used because each block has few variables and it natively handles
nonlinear inequality constraints without requiring the approximate, scaled
derivatives used by the historical Fortran search. BOBYQA handles the two
smooth scalar, bound-constrained problems. CUTPLANE remains as a deterministic
initialization and polarity routine; it is no longer the likelihood optimizer.

This is model-faithful rather than iteration-faithful. Generic optimizers need
not visit the same grid points or reach the same local optimum as `RCINT2`,
`XINT`, `SIGMAS`, and `WINT`.

## Geometric invariants

Three checks from the Fortran caller are enforced explicitly:

1. a preloaded roll-call midpoint is made feasible before evaluation;
2. the midpoint returned by CUTPLANE is projected before optimization;
3. the nonlinear unit-ball constraint remains active throughout COBYLA.

With one period, temporal terms are disabled and a legislator's reported
coordinate is exactly its constrained intercept. In dynamic models, as in the
original formulation, the intercept is constrained but the temporal
coefficients are not; a reconstructed time-specific coordinate can therefore
leave the unit ball.

## Dependencies

- CMake 3.24 or newer;
- a C++20 compiler;
- Eigen 3.4 or newer;
- NLopt 2.10 or newer;
- OpenMP, optionally.

If Eigen or NLopt is absent, CMake fetches pinned upstream releases (Eigen
5.0.0 and NLopt 2.11.0). Disable this with
`-DDWNOMINATE_FETCH_DEPENDENCIES=OFF` for fully offline builds.

## Build and test

```bash
cmake -S engine-modern -B build/engine-modern \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=ON
cmake --build build/engine-modern --parallel
ctest --test-dir build/engine-modern --output-on-failure
```

Equivalently, from `engine-modern/`: `cmake --preset release`,
`cmake --build --preset release`, and `ctest --preset release`.

`-ffast-math` is intentionally not used. Tail probabilities and active
constraints should retain standard IEEE floating-point semantics.

OpenMP is disabled by default because the inherited CUTPLANE path is not yet
bitwise reproducible under concurrent roll-call initialization. Enable it only
for performance experiments with `-DDWNOMINATE_ENABLE_OPENMP=ON`; scientific
regression runs should retain the default serial configuration.

## Run

The CLI accepts the same directory layout as the other C++ engines:

```bash
build/engine-modern/dwnominate-modern \
  --input-dir=engine-experimental/benchmarks/sen90 \
  --output-dir=build/sen90-modern \
  --wnominate=engine-experimental/benchmarks/sen90/wnominate_coordinates.csv \
  --periods=1 --model=0 --iterations=4
```

The most important regression checks are not correlations alone. For a static
run, also verify

```text
max hypot(coord1D, coord2D)       <= 1 + tolerance
max hypot(midpoint1D, midpoint2D) <= 1 + tolerance
```

and compare the radial distribution, log-likelihood, classification, and
coordinate distances against the Fortran output.

## Current scope

The implementation reuses the audited data loader, likelihood evaluator,
Legendre temporal basis, polarity conventions, and output layer of the prior
C++ port. The principal modernization is the replacement of all hand-written
likelihood searches. Before treating it as a drop-in scientific replacement,
the Chilean one-legislature panels and the multi-period US benchmark should be
run as numerical regression suites against the exact Fortran inputs.

## Validation snapshot

The serial Release build was checked on the committed Senate 90 one-period
fixture with four alternating iterations. After orthogonal Procrustes alignment
without scaling, the baseline initialization produced `r1 = 0.993014`,
`r2 = 0.988759`, and mean two-dimensional distance `0.103374` against the
published W-NOMINATE fixture. The perturbed initialization produced
`r1 = 0.993298` and `r2 = 0.989266`; its estimates correlate with the baseline
run at `0.999467` and `0.993709` by dimension.

In both runs, the maximum legislator radius was one to floating-point precision.
The baseline maximum roll-call midpoint radius was also one, with no observation
above `1 + 1e-9`. Two repeated serial executions produced byte-identical
coordinate and roll-call CSV files. These results are useful regression anchors,
but they are not evidence that every local optimum or dynamic trajectory is
numerically identical to the Fortran search.
