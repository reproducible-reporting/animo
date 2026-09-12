<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 02: Test Harness and Probes

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Testing* and *Behaviour probes* under
*Development Infrastructure*, the *Testing strategy* entry under *Resolved Design Decisions*,
and the whole *Findings* section, which is the input to the probes.

## Goal

All three test tiers exist and are exercised, and every finding the design rests on
has a probe that asserts the finding itself.
When typst or chromium changes something underneath animo,
the failure should name the behaviour that broke, not the feature that broke.

Like phase 01, this phase builds machinery whose value only becomes visible later.
The probes are what make it worth doing now anyway:
they are the one thing in this phase that has real content from day one,
and writing them is also how the three tiers get validated against known answers.

## Prerequisites

Phase 01.

## Scope

### In Scope

- **Tier 1, plan resolution.**
  A pytest fixture that compiles a `.typ` document with no output
  and reports failure with the compiler's stderr attached.
  Documents are full of `#assert`; the test asserts that the compile succeeded.
  The inverse case matters as much: a helper for documents that *must* fail to compile,
  asserting on the message, which is how the `import *` footgun gets tested later.
- **Tier 2, paged outputs.**
  `typst compile -f png --ppi ..` straight to rasters, decoded with `Pillow`
  and compared with `numpy`, with `--input animo=presentation` selecting the mode
  exactly as an ordinary user would.
  Plus a `pypdfium2` path for the few assertions that are about the PDF writer
  rather than about the layout.
  Provide comparison helpers that report *where* two rasters differ, not only that they do:
  phases 08 and 09 assert "identical outside this band" repeatedly,
  and a bare boolean makes those failures unreadable.
- **Tier 3, HTML.**
  `playwright` with its bundled chromium.
  Geometry through `page.evaluate`, images through `locator.screenshot(animations="disabled")`.
  The fixtures should already assume what phase 05 will provide:
  a deck whose slide and subslide state is addressable in `location.hash`,
  so tests deep-link instead of clicking their way to a state.
- **The reference image policy, implemented rather than described.**
  Stored images are the exception.
  When one is unavoidable, it is captured as PNG, converted with `Pillow` to lossless WebP,
  and compared on decoded arrays.
  Provide the update path (an environment variable or a pytest flag) in the same commit,
  because a policy without a regeneration command decays into hand-edited binaries.
- **`probes/`, one probe per entry in *Findings*.**
  Each probe asserts the finding, names the finding in its docstring or comment,
  and is independent of any animo feature.
  The findings that need a browser are probes too, in tier 3.
  Findings that are about the typst source tree rather than about observable behaviour
  (for example the single `data-typst-label` emission site) become behavioural probes
  where possible, and are otherwise skipped with a note rather than faked.
- **Continuous integration**, as the design document's table has it,
  minus the release workflow:
  `pytest` on push and pull request against the pinned typst,
  `probes` on a schedule against the newest typst release, non-blocking,
  `zensical` building with `--strict`,
  and `lint` running the Universe package checker through
  `docker run -v .:/data ghcr.io/typst/package-check check`.
  Typst is installed with `typst-community/setup-typst@v5`, pinned to the manifest's `compiler`.
- Fonts: tests and examples compile with `--ignore-system-fonts` and use only embedded fonts,
  so a contributor's machine and CI rasterise identically.

### Out of Scope

- The release workflow and the publishable subtree: phase 13.
- Any animo feature.
- Benchmarks: phase 11.

## Open Questions in Focus

1. **Does the non-blocking newest-typst probe job produce signal or noise?**
   The design document leaves this open deliberately.
   It cannot be answered in one session, but this phase decides the shape that makes
   answering it possible: how a probe failure is reported so that it names the finding,
   whether the job is allowed to fail silently or must open something,
   and how a finding that legitimately changed gets retired.
   A job nobody reads is worse than no job.
1. **How much of the suite genuinely needs stored pixels?**
   The design argues that the two invariants the region design rests on are comparisons
   *within* one page load and need no reference images, and that stored images are brittle.
   Establish concretely, while building the tiers, which assertions can be expressed
   numerically and which cannot, and make the answer visible:
   a test that stores a reference image should have to say why.

No other open question from the design document is in scope for this phase.

## Tests

The probes are the tests of this phase.
They should all pass against the pinned typst 0.15.1, because every one of them
restates something the design document already measured.
A probe that fails is a finding that was wrong, and that is exactly the news worth having early.

Add in addition a small self-test of the harness itself:
a raster comparison that is known to differ and one that is known to be identical,
so that a broken comparison helper cannot pass everything silently.

## Documentation

- `docs/testing.md`: the three tiers, what belongs in each,
  how to run one tier or one test, and the reference image policy including regeneration.
- `docs/probes.md` or a section of the same page: what a probe is,
  why it is separate from a feature test, and how to add one when a new finding is measured.
  Phases 03 to 13 all end with a session log that may contain new findings,
  so this page is the instruction for turning those into probes.

## Definition of Done

- `pytest` runs all three tiers and is green, with the browser tier actually launching chromium.
- Every entry in the design document's *Findings* section has a probe,
  or a recorded reason why it cannot have one.
- The four workflows exist and pass on a pull request.
- `pre-commit run --all-files` and `zensical build --strict` are green.

## Hand-Off

Every later phase writes tests through these fixtures and adds probes for what it measures.
Phase 05 depends on the tier-3 fixture assuming hash-addressable state,
and phases 08 and 09 depend on the raster comparison reporting the location of differences.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
