# Building engine-faithful: the two dependencies, and why the backend matters

This file exists because the published reproduction package could not be built by a
third party. Two things were missing, and one of them failed **silently**.

## 1. Eigen 3.4.0 — MANDATORY

Header-only. The build expects `nominate_cmodule/Eigen/Dense` to resolve.

    curl -L -o eigen-3.4.0.tar.gz https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz
    tar xf eigen-3.4.0.tar.gz
    cp -r eigen-3.4.0/Eigen nominate_cmodule/Eigen

Without it the build previously died in a wall of `Eigen/Dense: No such file or
directory`. It now stops with one actionable line.

## 2. Reference netlib LAPACK 3.12.1 — OPTIONAL, but it changes the numbers

`USE_REF_LAPACK` defaults **ON** and routes Eigen's SVD through `LAPACKE_dgesvd`
via `EIGEN_USE_LAPACKE`. This is the configuration every published likelihood was
produced with.

If the library is absent, the build falls back to Eigen's own `JacobiSVD`. **That
fallback used to be silent.** It now emits a prominent warning, because the choice
is not cosmetic:

| panel | LAPACKE | Eigen JacobiSVD | difference |
|---|---:|---:|---:|
| Chile 353 | −1,132.370 | −1,138.778 | 6.41 |
| Chile 366 | −6,276.201 | −6,278.608 | 2.41 |
| Chile 368 | −13,296.522 | −13,264.718 | **−31.80** |
| US sen90 | −15,457.167 | −15,435.597 | **−21.57** |

The sign is not constant. On Chile 353/366 LAPACKE reaches the higher likelihood;
on Chile 368 and US sen90 Jacobi does. On sen90 the backend decides whether
engine-faithful beats the canonical Fortran (−15,452.25) or loses to it.

**Rule this establishes:** `r2` and other scale-invariant statistics may be quoted
without naming the backend. **A likelihood may not.**

To build the published configuration:

    cd external && tar xf lapack-3.12.1.tar.gz && cd lapack-3.12.1
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DLAPACKE=ON -DBUILD_SHARED_LIBS=OFF
    cmake --build build -j 4

Then configure the engine normally. To build deliberately without it:

    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DUSE_REF_LAPACK=OFF

## 3. Check what you actually got

Every run writes its own provenance into `cpp_summary.csv`:

    svd_backend,lapacke          # or eigen_jacobi
    cutplane_absence,retained    # or filtered (DWNOM_CUTPLANE_FILTER_ABSENT=1)
    export_frame,local_t         # or global_t (DWNOM_EXPORT_GLOBAL_T=1)

Read those three lines before comparing any likelihood to any table.
