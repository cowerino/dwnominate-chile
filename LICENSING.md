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

### `fortran-canonical/DW-NOMINATE-wmay.f` — MIT. **Resolved 2026-08-22.**

Taken unmodified from `wmay/dwnominate` `src/DW-NOMINATE.f` at commit `02d0876`
(2023-02-20, verified against the GitHub API). The upstream `DESCRIPTION`
declares `License: MIT + file LICENSE`, with `YEAR: 2023` and
`COPYRIGHT HOLDER: William May, Keith T. Poole`.

The notice now travels with the copy, at
`fortran-canonical/LICENSE-wmay-dwnominate`.

⚠ GitHub's licence detector reports that repository as **NOASSERTION / Other**,
not MIT. That is an artefact of R's convention, where `LICENSE` holds only the
two template fields and the body comes from R's `share/licenses/MIT`. The
`DESCRIPTION` declaration is authoritative. Anyone re-checking this will hit the
same false signal, which is why it is written down here.

Attribution: William May (author), Nolan McCarty (author, "Author of the original
Fortran code"), Keith T. Poole (copyright holder of the original Fortran code).

### `fortran-canonical/DW-NOMINATE-2004.FOR` — **no licence exists. Checked 2026-08-22.**

Poole and Rosenthal's original, dated 1 October 2004, from
`legacy.voteview.com/k7ftp/wf1/DW-NOMINATE.FOR`.

Checked directly rather than assumed. The DW-NOMINATE program page carries **no
licence, no copyright notice, and no terms of use**. The site's only relevant
statement is a policy, on `legacy.voteview.com/about_this_site.htm`:

> "Keith and Howard adhere to the policy that all of their datasets and software
> are made freely available to anyone who asks for them."

The only disclaimer on the site concerns access to the files, not their reuse:
"UCLA provides no warranty or guarantee of access to these files." The site is
maintained by Keith Poole (`ktpoole@uga.edu`), Department of Political Science,
University of Georgia.

**A policy of free availability on request is not a licence grant.** It does not
state redistribution terms, and this repository redistributes the file. So:

- It is included unmodified and attributed, as academic source of record.
- **We assert no licence over it. It is outside our MIT grant.**
- If you intend to redistribute it yourself, resolve its terms first.

**The stated policy names its own mechanism: asking.** `wmay/dwnominate` records
Keith T. Poole as "Copyright holder of the original Fortran code", so he is the
person to ask, and one email would convert this from an assumption into a
permission. Until then the honest options are to keep it with this statement, or
to drop the file and cite the upstream URL so a reader fetches it themselves.

### NLopt — fetched, not vendored.

`engine-modern/` fetches NLopt at configure time via CMake `FetchContent` from
`https://github.com/stevengj/nlopt.git`. Nothing from it is committed here, so
its licence (LGPL, with MIT-licensed subcomponents) applies to your build rather
than to this repository's contents.

## Open items

1. ~~Vendor `wmay/dwnominate`'s `LICENSE`~~ **done 2026-08-22.**
2. **Ask Keith T. Poole for explicit permission to redistribute
   `DW-NOMINATE-2004.FOR`**, or drop the file and cite the upstream URL instead.
   The site's stated policy is that the software is free "to anyone who asks",
   so asking is the mechanism it names.
3. Confirm the CC BY 4.0 / MIT split with all three authors before this file is
   treated as settled (D-E3 is recorded as a co-author decision).
