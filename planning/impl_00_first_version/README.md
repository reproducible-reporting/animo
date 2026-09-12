<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Implementation Plan: Animo 0.1.0

This directory turns [planning/design.md](../design.md) into an ordered series of phases.
Each phase is implemented in its own Opus 5 session and leaves the repository in a state that
compiles, tests and documents itself.

Read [planning/design.md](../design.md) in full before starting any phase.
This plan does not restate the design, it only says in which order to build it,
and which of the design's open questions each phase is expected to answer.

## How to Use This Plan

- **One session per phase.**
  Start a fresh session, read the design document and the phase file, and implement that phase.
- **Phases are ordered by dependency**, so the numbering is also the implementation order.
  Later phases assume everything earlier is in place.
- **Each phase ends in a testable version.**
  Tests and documentation are part of the phase, not a later cleanup.

## Rules for Every Phase Session

These apply to all phases and are repeated at the top of each phase file.

1. **Ask when a significant decision comes up.**
   The open questions listed in a phase file are known in advance
   and are the reason the phase is cut the way it is,
   but decisions with lasting consequences for the API, the file layout or the output format
   are the author's to make.
   Ask instead of guessing, and ask early rather than after building on the guess.
   Prefer one question with concrete alternatives over a long discussion.
1. **End the phase with a session log.**
   Append a `## Session Log` section to the phase file itself, covering:
   what was built, what was decided and why, which open questions were answered and how,
   which new findings about typst, chromium or the tooling were collected,
   and what a follow-up phase should know.
   Findings are the point of the log:
   the design document's *Findings* section exists because such observations are expensive
   to rediscover, and a phase that measures something new should record it in the same spirit.
   If a finding contradicts the design document, say so in the log and ask
   whether [planning/design.md](../design.md) should be updated.
   Do not silently edit the design document.
1. **Do not commit.**
   Leave all work in the working tree.
   The author reviews and commits after the session is closed.
   Running `pre-commit run --all-files` at the end is expected,
   because it formats files and catches hygiene problems, but `git commit` is not.
1. **Stay inside the phase.**
   Open questions that are not in the phase's focus list belong to another phase.
   When one surfaces, note it in the session log and leave it alone.
   Scope creep is what makes a phase unreviewable.

## Repository Conventions

- Every new file carries a REUSE header (`Apache-2.0`), as the existing files do.
- English prose is wrapped with [semantic line breaks](https://sembr.org/),
  with a hard cap of 100 characters, and avoids en and em dashes.
- Markdown headings use Title Case.
- `.editorconfig` sets the indentation: two spaces for `.typ`, `.md`, `.yaml` and `.json`,
  four spaces for Python.
- `pre-commit run --all-files` and the test suite must be green before a phase is considered done.

## The Phases

| Phase                                                                         | Delivers                                                          |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [01 Repository and toolchain](01_repository_and_toolchain.md)                 | manifest, package resolution, environment, task layer, docs shell |
| [02 Test harness and probes](02_test_harness_and_probes.md)                   | the three test tiers, one probe per finding, CI                   |
| [03 Static slides and the four outputs](03_static_slides_and_outputs.md)      | `slide`, viewport, canvas, backgrounds, deck navigation           |
| [04 The plan model and tags](04_plan_model_and_tags.md)                       | `tag`, `sub`, `anim`, states, continuous primitives on paper      |
| [05 HTML continuous animation](05_html_continuous_animation.md)               | the browser runtime, subslide stepping, smooth motion             |
| [06 Panning](06_panning.md)                                                   | `pan`, canvas motion, `relto` in both targets                     |
| [07 Epochs and structural primitives](07_epochs_and_structural_primitives.md) | `replace`, `remove`, `apply`, `reset`, implicit regions           |
| [08 Explicit regions](08_explicit_regions.md)                                 | `region`, footprints, nesting, sizing, clipping                   |
| [09 Epoch frames and transitions](09_epoch_frames_and_transitions.md)         | stacked frames, region-scoped crossfade, the two invariants       |
| [10 Tag sites in math, cetz and fletcher](10_math_cetz_and_fletcher.md)       | `draw: true`, the tag site support matrix                         |
| [11 Benchmarks and page weight](11_benchmarks_and_page_weight.md)             | compile time and output size, measured and tracked                |
| [12 Slide and subslide numbering](12_numbering.md)                            | the numbering decision, implemented                               |
| [13 Documentation, examples and release](13_documentation_and_release.md)     | the manual, the example decks, the release path                   |

Phases 01 and 02 build the development environment.
Their output is deliberately hard to validate on its own:
a test harness with almost nothing to test and a task layer with almost nothing to build
only prove themselves from phase 03 onwards, when real features start using them.
That is expected, and it is why they come first rather than being grown ad hoc later.
Build them thin enough to be revised, and expect later phases to revise them.

## Where the Design's Open Questions Are Answered

Every phase is deliberately exposed to at most two of the design document's open questions,
so that the hard part of the phase is small enough to think about properly.

| Open question (design document)                      | Phase |
| ---------------------------------------------------- | ----- |
| Slide and subslide numbering                         | 12    |
| Handout page of a panned slide                       | 06    |
| Exactness of the automatic canvas                    | 03    |
| Region-scoped `plus-lighter` crossfade               | 09    |
| `draw: true` over raw cetz draw commands             | 10    |
| How CSS-animated typst SVG groups look in motion     | 05    |
| How a reflow crossfade reads                         | 09    |
| Compile-time cost for a realistic deck               | 11    |
| Page weight with several epochs per slide            | 11    |
| Whether the max-footprint rule is tolerable          | 08    |
| `layout(size => ..)` measuring width in containers   | 08    |
| Implicit regions inside cetz canvases and math       | 10    |
| Agreement of `pan(relto:)` between browser and typst | 06    |
| Easing, durations and the Web Animations API         | 05    |
| `tag` defaulting to `box` versus `block`             | 04    |
| Plan published as a state versus through a show rule | 04    |
| Whether a FLIP morph should ever scale               | none  |

The last one belongs to the morph under *Potential Future Features* and is out of scope here.
Phases 01, 02, 07 and 13 carry questions of their own that the design document does not list,
stated in their phase files.

## Out of Scope for 0.1.0

Everything under *Potential Future Features* in the design document, in particular:
`time:` and `wait:`, narrated audio, `recolor`, `once`, morphing transitions,
`region(spill: true)`, hoisted glyph defs, the overlay argument, speaker notes,
and slide-to-slide transitions.

Phases 05, 08 and 09 must nevertheless leave the seams the design document asks for:
the two nested transform slots per tag site, and a swappable transition strategy.
Those are cheap now and expensive to retrofit.
