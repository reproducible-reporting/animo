<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 11: Benchmarks and Page Weight

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Benchmarks* under
*Development Infrastructure*, the renderings-per-slide table under *States and epochs*,
the finding that `<defs>` ids are content hashes,
and the shared-defs hoisting entry under *Potential Future Features*.

## Goal

Turn the design's two numeric open questions into measured numbers,
and put them under a regression watch.

Animo exists partly because the existing packages are slow.
This is the phase that says whether animo is,
and it is the last phase that can still change the design if the answer is bad.

## Prerequisites

Phases 01 to 10.

## Scope

### In Scope

- **A realistic benchmark deck** under `benchmarks/`.
  Realistic means the kind of deck the design is aimed at,
  not a synthetic worst case: a talk-sized number of slides,
  several regions with several epochs each, some cetz and some math,
  a panned slide, and a slide with many continuous steps in one epoch.
  The sibling decks listed under *Related directories* in the design document
  are the reference for what a real deck looks like,
  in particular `../2026-talk-thermodynamics` and `../2026-talk-fml-stacie/2_talk`.
- **Compile time**, per output, broken down enough to be actionable:
  how much is the base rendering, how much is the per-epoch re-rendering,
  and how much is the per-epoch region measurement.
  A single total number tells you that it is slow, not what to fix.
- **Page weight** of the HTML output, uncompressed and gzipped,
  with the per-epoch growth isolated,
  since every frame carries its own glyph `<defs>`.
- **Recording the numbers**, in the style of `../stepup-benchmark`,
  so that a later regression is visible when it happens rather than at the next release.
- Driven by StepUp, as a step in `plan.py`, not as a script a contributor has to remember.

### Out of Scope

- Optimisation work that changes the design.
  If the numbers say something must change, that is a finding and a question,
  not a silent redesign.
- Implementing shared-defs hoisting, unless the second question below says it is required
  for 0.1.0 and the author agrees.

## Open Questions in Focus

1. **What does a realistic deck cost to compile?**
   The design document's open question.
   Renderings scale with epochs for HTML and with states for the presentation PDF,
   and each region measures once per epoch on top of that.
   This is the expensive part, and it is what makes existing packages slow.
   Measure it, compare it against compiling the same content as plain typst slides,
   and state the overhead as a factor, which is the number an author will care about.
   Watch in particular whether the live preview loop stays usable,
   because a deck that takes ten seconds to recompile is not authorable
   even if a release build is fine.
1. **Is gzip enough for the page weight, or is shared-defs hoisting needed?**
   Also the design document's open question.
   The duplication across epoch frames is pure redundancy,
   because typst's def ids are content hashes, so equal ids always mean equal content
   and hoisting them into one document-level `<svg>` would be sound.
   Measure the uncompressed and gzipped sizes and the per-epoch growth,
   and decide whether 0.1.0 needs the hoisting or can defer it.
   Note that a deck is usually served from disk or over HTTP with compression,
   so the honest number is the transferred one, and the uncompressed one matters
   mainly for memory in the browser.

No other open question from the design document is in scope for this phase.

## Tests

Benchmarks are not assertions, and turning them into pass/fail tests in CI
makes the suite flaky on shared runners.
So:

- the benchmark deck itself is compiled by the test suite, to catch breakage,
  without asserting on timings;
- the recorded numbers live in the repository as data, with the machine they were measured on
  written next to them, because a number without a machine is not a measurement;
- a cheap structural assertion is worth having and is stable:
  the *number of renderings* animo asks typst for, for a given deck,
  which is the cost model itself and does not depend on the hardware.

## Documentation

- `docs/performance.md`: what a slide costs in each output,
  which authoring choices are expensive (a structural step, a region with many epochs,
  a cetz canvas redrawn per epoch), and what the measured numbers are.
  An author who knows that a `replace` costs a whole rendering will use `hide` where it fits,
  which is exactly the guidance the design document's own remarks imply.

## Definition of Done

- The benchmark deck exists, is built by `plan.py`, and its numbers are recorded.
- Both open questions are answered with numbers and a decision.
- Any finding that changes an earlier phase's conclusion is raised as a question,
  not acted on silently.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 13 quotes these numbers in the manual and in the README.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
