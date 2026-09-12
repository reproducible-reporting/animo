<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 13: Documentation, Examples and Release Readiness

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Documentation*, *Version numbers*,
*Continuous integration* and *Repository layout and manifest*
under *Development Infrastructure*.

## Goal

Turn a working package into a publishable one:
a manual that shows animo doing the thing it exists to do,
example decks that are compiled and tested rather than transcribed,
and a release path that stops exactly where a human decision is required.

## Prerequisites

Phases 01 to 12. The API is closed after phase 12 and must not change here.

## Scope

### In Scope

- **The manual**, as a Zensical site built with `--strict`, so a broken link fails CI.
  Markdown, not `tidy`: `tidy` renders a typst document, which does not compose with a
  markdown site, and a static manual cannot show the one thing animo exists to demonstrate.
  Phases 03 to 12 each added pages; this phase makes them one coherent document,
  with a reading order, an introduction and a reference.
- **Examples included from real files** with `pymdownx.snippets` and `check_paths = true`,
  so a documented example cannot drift from the file that CI compiles and tests.
- **Every example published beside the site** as an HTML deck and embedded in an `<iframe>`,
  with its presentation and handout PDFs linked next to it,
  so the reader clicks through a real animation instead of looking at a screenshot of one.
  This is the point of choosing a markdown site over `tidy`, so it is not optional.
- **Universe compliance**:
  - every example, including the ones in `README.md`, imports `@preview/animo:X.Y.Z`
    rather than a relative path, so a reader can copy any file and compile it;
  - `snipwise` keeps every one of those strings equal to the manifest version,
    with `snipwise fix` as a pre-commit hook and `snipwise check` in CI;
  - documentation files are committed to `typst/packages` but excluded from the archive
    through `exclude`;
  - tests, probes, benchmarks and build scripts are not committed there at all.
- **The release workflow**, on tag `v*`:
  build the directory that would be copied into `typst/packages`, honouring `exclude`,
  run the package linter over exactly that directory,
  extract the release notes from `CHANGELOG.md`, and attach everything to the GitHub release.
  It stops at the artefact.
  Copying it into a sparse checkout of `typst/packages` and opening the pull request
  stays manual, because the submission cannot be taken back.
- **An assertion, not a copy, where the relationship is a mapping**:
  `snipwise` copies the version into the strings that repeat it,
  but the agreement between the git tag and the manifest version is checked in the workflow.
- `README.md`, `CHANGELOG.md` for 0.1.0, `CITATION.cff` and `.zenodo.json` finalised.

### Out of Scope

- Actually publishing to Universe. The last step is the author's, by hand.
- Any feature or API change. If one seems necessary, ask; do not slip it in here.

## Open Questions in Focus

1. **Does compiling the documentation examples need a Zensical module,
   or is a StepUp step before the site build enough?**
   The design document leaves this open.
   The examples have to be compiled to four outputs each and their HTML decks published beside
   the site, which is ordinary StepUp work,
   but the site build has to know the artefacts exist and where they are.
   Decide it, and prefer the answer that keeps `zensical build --strict`
   and `stepup build` independently runnable,
   because a contributor who only wants to read the docs should not need the whole build graph.
1. **Is the 0.1.0 API what should be permanent?**
   Publishing commits to the name and, in practice, to the API,
   and a submission cannot be taken back.
   This phase is the last point at which that can be reconsidered.
   Do a deliberate pass over the public surface, which by then is
   `slide`, `tag`, `region`, `sub`, the `anim` module and the deck entry point,
   against the design document's own reasoning,
   and list anything that the phases decided differently from the design,
   anything that is still provisional, and anything a session log flagged and nobody resolved.
   Present that list; the decision is the author's.

## Tests

- Every example under `examples/` compiles to all four outputs in CI.
- Every documented snippet resolves to a real file, enforced by `check_paths = true`.
- `snipwise check` passes, so no stale version string survives.
- The package linter passes over the built subtree, not over the working tree,
  because those are not the same directory.
- The release workflow is exercised on a test tag, or its steps are exercised individually,
  so that the first real tag is not the first run.

## Documentation

This phase is the documentation, so the deliverable is the site itself.
Two contributor-facing pages carry over from earlier phases and should be finished here:
`docs/architecture.md`, which maps the modules and says where a change belongs,
and `docs/environment.md` from phase 01, now describing the full loop.

## Definition of Done

- The site builds with `--strict`, embeds working example decks, and reads as one document.
- A tagged build produces a publishable artefact that passes the Universe linter.
- The API review has been presented to the author and its outcome recorded.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

The first version is complete.
What remains is the manual submission, and the open questions that the phases deferred,
which by then are recorded in the session logs of this directory
and can be folded back into [planning/design.md](../design.md)
as the starting point for the next planning round.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
