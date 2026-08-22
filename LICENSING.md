# Licensing

Two licences, split by what the material is, plus third-party components that
keep their own terms.

| what | licence | file |
|---|---|---|
| source code: `engine-faithful/` (except `Eigen/`), `engine-modern/`, `experimental/`, scripts, build files | **MIT** | `LICENSE` |
| data and reproduction outputs: `data/`, `results/`, `figures/`, measured tables, logs, receipts | **CC BY 4.0** | `LICENSE-DATA` |

Proposed by the authors and recorded as decision **D-E3**. If you are reusing
anything here and the split is ambiguous for your case, open an issue and we
will state it explicitly rather than leave you guessing.

## Third-party components, which keep their own licences

### Eigen 3.4.0 — MPL 2.0. Vendored.

`engine-faithful/Eigen/`, header-only, redistributed unmodified with its own
`COPYING.MPL2` and `COPYING.README` retained. It is vendored rather than fetched
so this repository builds from a clean clone; MPL 2.0 permits redistribution in
this form. Not covered by our MIT grant.

### `fortran-canonical/DW-NOMINATE-wmay.f` — upstream MIT. **Licence file not yet included.**

Taken unmodified from `wmay/dwnominate` `src/DW-NOMINATE.f` at commit `02d0876`.
The upstream project is MIT-licensed, which is compatible with redistribution
here, but **its `LICENSE` file is not yet vendored alongside the source, and MIT
requires the notice to travel with the copy.** That is an outstanding item, not a
claim that it is handled. Attribution owed to William May, and to Keith Poole,
Howard Rosenthal and Nolan McCarty for the method and the original code.

### `fortran-canonical/DW-NOMINATE-2004.FOR` — status unresolved.

Poole and Rosenthal's original, dated 1 October 2004, obtained from
`legacy.voteview.com/k7ftp/wf1/DW-NOMINATE.FOR`. It was published without an
explicit licence. It is included here unmodified and attributed, as academic
source of record. **We do not assert a licence over it and it is not covered by
our MIT grant.** If you intend to redistribute it yourself, resolve its terms
first.

### NLopt — fetched, not vendored.

`engine-modern/` fetches NLopt at configure time via CMake `FetchContent` from
`https://github.com/stevengj/nlopt.git`. Nothing from it is committed here, so
its licence (LGPL, with MIT-licensed subcomponents) applies to your build rather
than to this repository's contents.

## Open items

1. Vendor `wmay/dwnominate`'s `LICENSE` next to `DW-NOMINATE-wmay.f`.
2. Confirm the CC BY 4.0 / MIT split with all three authors before this file is
   treated as settled (D-E3 is recorded as a co-author decision).
