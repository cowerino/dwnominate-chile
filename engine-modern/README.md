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
| Roll-call midpoint and spread | NLopt COBYLA or SLSQP | `||midpoint|| <= 1` |
| Legislator coefficients | NLopt COBYLA or SLSQP | `||intercept|| <= 1` |
| `beta` and dimension weight | NLopt BOBYQA | positive bounds plus a re-centred local box |

COBYLA remains the reference block solver because it natively handles nonlinear
inequality constraints and follows the previously validated trajectory. SLSQP
is an optional faster solver. Its analytic gradients are obtained by converting
the historical `PROLLC2`/legislator directions to gradients of the declared
probit log-likelihood; central-difference regression tests independently check
that conversion. BOBYQA handles the two smooth scalar, bound-constrained
problems. CUTPLANE remains a deterministic initialization and polarity routine;
it is no longer the likelihood optimizer.

The local scalar box is essential to the alternating scheme. A globally exact
conditional solve in the first cycle sees crude bill and legislator states and
drives `beta` to its lower bound, which changes the basin of every later block.
The default `--scalar-search=local` re-centres BOBYQA at each cycle and retains
the effective 16-step reach of Fortran's `SIGMAS` (`1.6`) and `WINT` (`0.16`).
`--scalar-search=global` is retained as an explicit diagnostic, not the
scientific default.

This is model-faithful rather than iteration-faithful. Generic optimizers need
not visit the same grid points or reach the same local optimum as `RCINT2`,
`XINT`, `SIGMAS`, and `WINT`.

## Geometric invariants

Three checks from the Fortran caller are enforced explicitly:

1. a preloaded roll-call midpoint is made feasible before evaluation;
2. the midpoint returned by CUTPLANE is projected before optimization;
3. the nonlinear unit-ball constraint remains active throughout COBYLA.

CUTPLANE also preserves the original `XMAT`/`LDATA` row contract. Coordinates
and vote codes remain aligned until the routine sorts their projections, and
non-voters remain in the point cloud with a missing-vote code. They do not
contribute to the margin or classification counts, but they do participate in
the SVD geometry of `SEARCH`, as in the Fortran implementation. Equal
projections are resolved by original row index for deterministic C++ runs.

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

The optional reference-panel regression test additionally requires Python 3,
NumPy, and pandas.

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

OpenMP is disabled by default so the canonical build remains serial. When it is
enabled, only independent roll-call and legislator blocks run concurrently.
Global likelihood reductions used by `WINT` and `SIGMAS` deliberately remain
serial: changing their summation order can perturb `w2` or `beta` and send a
later constrained solve to a different local solution.

## Run

The CLI accepts the same directory layout as the other C++ engines:

```bash
build/engine-modern/dwnominate-modern \
  --input-dir=engine-faithful/benchmarks/sen90 \
  --output-dir=build/sen90-modern \
  --wnominate=engine-faithful/benchmarks/sen90/wnominate_coordinates.csv \
  --periods=1 --model=0 --iterations=4
```

To reproduce the three-decimal serialization of the original standalone
Fortran input files, add `--legacy-round-starts`. This quantizes only the
initial legislator coordinates to increments of `0.001`; all subsequent
optimization remains in double precision.

NLopt convergence can be examined with
`--optimizer-precision=relaxed|standard|strict|ultra`. The profiles jointly
control relative parameter and objective tolerances, nonlinear-constraint
tolerance, and the maximum number of objective evaluations for scalar,
roll-call, and legislator subproblems. Every run also exports
`cpp_convergence_trace.csv`, containing the global log-likelihood, `w2`, `beta`,
and the log-likelihood increment after each complete alternating cycle.

The scalar trajectory is selected independently:

```bash
dwnominate-modern ... --scalar-search=local   # default, Fortran-reach box
dwnominate-modern ... --scalar-search=global  # experimental full bounds
```

## Performance options

The solver, precision, scalar-trajectory, telemetry, and parallel controls are
independent and available from the CLI.

1. **SLSQP with analytic gradients**

   ```bash
   dwnominate-modern ... --block-solver=slsqp
   ```

   If SLSQP fails, returns a non-finite value, or decreases the block
   log-likelihood, the default behavior is to retry that block with COBYLA.
   Add `--no-solver-fallback` only for diagnostics.

2. **Adaptive tolerances and evaluation budgets**

   ```bash
   dwnominate-modern ... --block-solver=slsqp --adaptive-tolerances
   ```

   Early outer cycles use relaxed tolerances and reduced budgets; the final
   cycle always uses the complete selected precision profile.

3. **Explicit budgets and telemetry**

   ```bash
   dwnominate-modern ... --block-solver=slsqp \
     --scalar-maxeval=60 --rollcall-maxeval=80 \
     --legislator-maxeval=100
   ```

   `cpp_optimizer_trace.csv` records, for every block, the algorithm, status,
   evaluation count, elapsed time, initial/final likelihood, improvement, and
   whether the fallback was used. This permits selecting budgets from observed
   saturation instead of guessing them globally.

4. **Parallel independent blocks**

   ```bash
   cmake --preset release-openmp
   cmake --build --preset release-openmp
   build/release-openmp/dwnominate-modern ... --threads=4
   ```

   Static scheduling and serial global reductions preserve the parameter state
   on the Senate 90 regression fixture; timing fields necessarily differ.

5. **Faithful trajectory followed by validated NLopt polishing**

   ```bash
   engine-modern/tools/run_hybrid.py \
     --faithful-binary=build/engine-faithful/dwnominate \
     --modern-binary=build/engine-modern/dwnominate-modern \
     --input-dir=engine-faithful/benchmarks/sen90 \
     --wnominate=engine-faithful/benchmarks/sen90/wnominate_coordinates.csv \
     --output-dir=build/sen90-hybrid --periods=1 --model=0 \
     --faithful-iterations=4 --polish-iterations=1 \
     --scalar-search=local \
     --legacy-round-starts
   ```

   The script transfers the faithful engine's coordinates, bill parameters,
   `w2`, and `beta` into a common SLSQP start. It rounds only the initial
   W-NOMINATE serialization when requested; the fitted faithful state is not
   rounded before polishing. This option must be evaluated against both the
   faithful terminal likelihood and held-out/regression diagnostics.

An internal trajectory switch is also available with
`--block-solver=hybrid`: it uses COBYLA before the final outer cycle and SLSQP
in the final cycle. It is experimental and is not equivalent to the external
faithful-engine polishing pipeline above.

### Chile static validation

The default local scalar trajectory was checked on all three committed Chile
panels with SLSQP, standard precision, four cycles, and one serial thread:

| legislature | log-likelihood | classification | `w2` | `beta` |
|---|---:|---:|---:|---:|
| 353 | -1081.939253 | 94.1206 % | 0.541958 | 6.671786 |
| 366 | -5827.995216 | 95.4473 % | 0.498612 | 6.554631 |
| 368 | -12804.639527 | 94.3698 % | 0.506305 | 5.906222 |

After orthogonal Procrustes without scaling and a predeclared minimum of 25
votes, correlations against `engine-faithful` are `(r1, r2) = (0.9978,
0.9893)`, `(0.9969, 0.9624)`, and `(0.9978, 0.9839)`. Second-dimension scale
ratios are `1.021`, `1.063`, and `1.013`, respectively. The global first-cycle
scalar solve previously compressed this dimension; increasing NLopt precision
did not repair the trajectory.

### Dynamic five-period validation

US Congresses 111--115 provide five periods, a linear temporal model, 523
Fortran-observed member-periods, and 2,940 roll calls. Under the same local
SLSQP configuration the engine reaches log-likelihood `-36404.397549`,
classification `93.4959 %`, `w2=0.552126`, and `beta=5.963518`.

Against the committed Fortran coordinates, aligned correlations by period are:

| period | `r1` | `r2` | dimension-2 scale |
|---:|---:|---:|---:|
| 1 | 0.9963 | 0.8740 | 0.9673 |
| 2 | 0.9965 | 0.7932 | 0.8724 |
| 3 | 0.9954 | 0.6938 | 0.8339 |
| 4 | 0.9956 | 0.6589 | 0.7702 |
| 5 | 0.9933 | 0.6061 | 0.7723 |

Seven matched reconstructed member-period coordinates exceed radius one
(maximum `1.227683`). This is expected: the constraint applies to the temporal
intercept, while time-specific coordinates add unconstrained Legendre terms.
The canonical Fortran output also contains such points.

The complete machine-readable snapshot is
`benchmarks/reference_panels_local_trust.json`. Run it with:

```bash
python engine-modern/tools/validate_reference_panels.py \
  --binary=build/engine-modern/dwnominate-modern \
  --repo-root=. --work-dir=build/reference-panels
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

## Historical global-box validation snapshot

This snapshot predates the local scalar trust region and corresponds to
`--scalar-search=global`; it is retained for provenance, not as the current
default regression target. The serial Release build was checked after repairing
the CUTPLANE caller on the committed Senate 90 one-period fixture (102
legislators and 596 roll calls), using `--legacy-round-starts`. With four
alternating cycles and the `standard` profile, the fitted log-likelihood is
`-15528.130488`. After orthogonal
Procrustes alignment without scaling, the coordinates have `r1 = 0.992835`,
`r2 = 0.991086`, and mean two-dimensional distance `0.097827` against the
published W-NOMINATE fixture.

The maximum legislator and roll-call midpoint radii are one to floating-point
precision, with no observation above `1 + 1e-9`. A repeated serial `standard`
run produced byte-identical coordinate, corrected-coordinate, bill-parameter,
and convergence-trace CSV files. This establishes deterministic behavior for
the tested configuration, not bitwise equivalence with a different compiler,
BLAS/LAPACK SVD, or the historical Fortran search.

Before the CUTPLANE repair, the corresponding `standard` four-cycle result was
`-15609.376994`. The corrected coordinate/vote alignment and inclusion of
missing-vote points therefore changed the initialization basin and improved the
fitted likelihood by `81.246506` on this fixture. Earlier benchmark rows from
the misaligned caller are not retained as validation anchors.

## Historical global-box NLopt precision experiment

Before the local trust-region default and the observed-voter callback
optimization above, the corrected fixture was evaluated serially with
`--scalar-search=global`, legacy-rounded starts, and four NLopt precision
profiles. The likelihood comparisons remain informative about tolerance
sensitivity within that historical trajectory, but they do not describe the
current default. The elapsed times are also superseded by the
performance-options table. At four alternating cycles the results were:

| Profile | Log-likelihood | Elapsed | Relative to `standard` |
|---|---:|---:|---:|
| `relaxed` | -15555.089269 | 5.73 s | -26.958781 |
| `standard` | -15528.130488 | 11.30 s | 0 |
| `strict` | -15522.488708 | 19.71 s | +5.641780 |
| `ultra` | -15520.618745 | 26.54 s | +7.511743 |

Thus `ultra` takes 2.35 times as long as `standard` for a gain of 7.51
log-likelihood units. Their coordinate estimates remain very close
(`r = 0.999979` and `0.999832` by dimension). At eight cycles, `standard`
reaches `-15176.834546` in 24.26 seconds and `ultra` reaches `-15169.329100`
in 61.31 seconds: again a 7.51-unit gain, now at 2.53 times the elapsed time.

Increasing complete alternating cycles has a much larger effect than tightening
the local solver. For `standard`, moving from four to eight cycles improves the
log-likelihood by `351.295942`. The last eight-cycle increment is still
`40.303529`, so this is not a converged outer solution. All tested legislator
and roll-call midpoint estimates remain inside the unit ball. The full summary
is stored in `benchmarks/nlopt_precision_sen90.csv`.

This experiment does not rank NLopt against the historical Fortran optimizer:
the benchmark reference is published W-NOMINATE coordinates, not a final
Fortran parameter vector evaluated by a common likelihood implementation. It
does show that `standard` is the practical default for this fixture and that a
fixed four-cycle run is not a converged maximum-likelihood fit for the modern
alternating implementation.
