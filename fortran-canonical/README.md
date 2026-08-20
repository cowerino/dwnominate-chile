# fortran-canonical

The third engine, next to `engine-faithful/` and `engine-modern/`. Two Fortran sources, both
unmodified, plus the minimum needed to link them outside R.

| file | what |
|---|---|
| `DW-NOMINATE-2004.FOR` | Poole/Rosenthal's original, dated 1 October 2004, from `legacy.voteview.com/k7ftp/wf1/DW-NOMINATE.FOR`. 10,115 lines. Self-contained: bundles its own IMSL `LSVRR` (SVD) and EISPACK `RS`/`TRED1`, so it needs no external LAPACK/BLAS |
| `DW-NOMINATE-wmay.f` | `wmay/dwnominate` `src/DW-NOMINATE.f` @ `02d0876`. 3,680 lines. **This is the arm the paper's `*-fortran` numbers and figures come from** |
| `gettim_stub.f` | `gettim_` (MS-Fortran wall-clock intrinsic) reimplemented with `date_and_time`. The 2004 source's only unresolved external symbol; used for an elapsed-time printout, zero numerical effect |
| `r_compat.f90` | `intpr`, `realpr`, `dblepr`, `rexit`. The wmay source is built by R and calls these for logging and fatal exit; these replace R's `<R_ext/Print.h>` glue so it links standalone |
| `standalone_main.f90` | `program dwnominate_standalone`. Calls the unmodified `dwnom(...)` with the same argument list the R wrapper uses |
| `upstream.patch` | the entire delta of `DW-NOMINATE-wmay.f` against upstream: one trailing space removed from a comment at line 3021 |

## The two sources are the same estimation core

Verified by normalised diff of all 13 core estimation subroutines (`SIGMAS, WINT, JAN11PT, PLOG,
PROX, XINT, REGA, PROLLC2, RCINT2, RSORT, CUTPLANE, SEARCH, JAN1PT`). `JAN11PT`, `RSORT`,
`CUTPLANE` and `JAN1PT` are identical. The rest differ only by IMSL→LAPACK substitution,
single↔double casts for LAPACK, Fortran-90 `use`-modules in place of common blocks, R error
handling, and removed diagnostic writes. **No estimation-math change anywhere.** The 6,435-line
size gap is the ~34 IMSL/BLAS routines the 2004 file bundles and wmay drops in favour of R's
LAPACK/BLAS.

Two differences worth naming:

- **`SEARCH`** (the cutting-plane orientation finder, the dimension-2 mechanism) takes the
  cutting-plane normal from an SVD of the roll-call midpoint matrix. 2004 uses IMSL `LSVRR`,
  wmay uses LAPACK `DGESDD` with the correspondingly transposed right-singular-vector index
  (`vvv(ns,k)` against `vvv(k,ns)`).
- **`XINT`** carries a per-legislator 2-D fit-quality safeguard in the 2004 source that wmay
  drops: under `ns==2`, a legislator whose geometric mean probability falls below 0.50 has their
  coefficients reverted to the pre-update values rather than the update being accepted.

`GRID`, a 31-line search helper, exists only in the 2004 source and is not on wmay's path.

## Building

**2004** — no external linear algebra required:

```sh
gfortran -std=legacy -ffixed-line-length-none -fno-automatic -w -c DW-NOMINATE-2004.FOR -o dwnom2004.o
gfortran -std=legacy -ffixed-line-length-none -fno-automatic -w -c gettim_stub.f         -o gettim_stub.o
gfortran -std=legacy dwnom2004.o gettim_stub.o -o dwnom2004.exe
```

The `.FOR` extension triggers cpp preprocessing on some toolchains; rename to `.f` if yours does.
It is a file-based legacy program: it reads a control file `DW-NOMSTART.DAT` from the CWD naming
seven fixed-width data files. The formats are declared at `DW-NOMINATE-2004.FOR:96-138` and read
at `:40-360`.

**wmay** — `dsyev_` is unresolved at *link* time, not runtime, so LAPACK/BLAS must be passed to the
final link. Compile the model first; it defines the `xxcom_mod`, `mine_mod` and `zdf_mod` modules.

```sh
gfortran -O2 -c DW-NOMINATE-wmay.f  -o dwnominate_core.o
gfortran -O2 -c r_compat.f90        -o r_compat.o
gfortran -O2 -c standalone_main.f90 -o standalone_main.o
gfortran -O2 dwnominate_core.o r_compat.o standalone_main.o -llapack -lblas -o dwnominate_fortran.exe
```

The WinLibs UCRT toolchain ships no `liblapack`/`libblas`; `Rlapack.dll Rblas.dll` from any R
install (`R/bin/x64/`) can be passed to the linker instead, which is how the reference build was
produced. Both were built with gfortran 15.2.0, MinGW-W64 x86_64-ucrt-posix-seh.

**Scope of the standalone wmay driver.** `standalone_main.f90` is validated for single-period runs
only. A multi-period run aborts inside the engine with `FATAL: MISMATCH ON MISSING DATA`, an input
marshalling inconsistency in the driver's `RCVOTE1`/`RCVOTE9` construction, not in the model. The
paper's multi-period Fortran results were produced through the R package.

## Provenance of the published Fortran arm

The `*-fortran` figures and the Fortran column of the comparisons read a wmay run through the
R package at `dims=2, model=2, niter=4` on the 23-period Chilean panel in `data/chile-dynamic/`,
which returned `w1 = 1.0`, `w2 = 0.386339038610458`, `beta = 8.31815528869629`. Its coordinate
export carries 7,820 rows, 340 legislators × 23 periods, so it is padded across unserved cells;
`figures/generate_fortran_dyn_maps.py` filters it to the 2,855 served placements before plotting.
That export is not yet in `results/`.

## Attribution and licence

DW-NOMINATE is the work of Keith T. Poole and Howard Rosenthal, with Nolan McCarty. The 2004 source
is their original distribution from `legacy.voteview.com/dw-nominate.htm`, which carries no explicit
licence text; it is reproduced here unmodified for reproducibility. `DW-NOMINATE-wmay.f` is from
`github.com/wmay/dwnominate` (William May), reported MIT. `r_compat.f90` and `standalone_main.f90`
are ours and touch no model code. The repository-level licence file is still pending.
