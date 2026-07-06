# dwnominate-chile

Reproduction package for:

**A Verified C++ DW-NOMINATE and the Identification Floor of Its Second Dimension: The Chilean Chamber through the *Estallido Social***
Roberto Nieves Tocornal, Pablo Antivil Morales, Julio Rojas-Mora.
45th International Conference of the Chilean Computer Science Society (SCCC / JCC 2026).

This repository accompanies the paper: an open, from-scratch, parallel C++
reimplementation of DW-NOMINATE, verified component by component against the canonical
2004 Fortran, and applied to the Chilean Chamber of Deputies across the *estallido
social* (2018–2022).

## Contents

- `engine/` — the verified parallel C++ DW-NOMINATE engine: sources, build files, and
  the exact compiler flags used in the paper.
- `reproduce/` — data-extraction scripts, per-figure and per-table receipts, and both
  engines' build configurations, sufficient to regenerate every figure and table in
  the paper.

## Status

**Placeholder.** The full engine and reproduction package will be published here by
the camera-ready deadline (2026-08-10), ahead of the conference (2026-11-10). A
BibTeX citation will be added on acceptance.
