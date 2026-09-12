<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 12: Slide and Subslide Numbering

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant part of the design document is the first entry under *Open Questions*,
together with the `numbered:` paragraph under *Slides*
and the overlay entry under *Potential Future Features*.

## Goal

Answer the one open question that was deliberately left until the epoch machinery existed,
and implement whatever the answer is.

This is a small phase on purpose.
It is separate because the decision is genuinely hard and has a shape that only becomes visible
after phase 09, and because it is the last thing that can still change the public API
before the manual is written.

## Prerequisites

Phases 01 to 11. Phase 09 in particular: the problem is caused by epochs.

## Scope

### In Scope

- The decision and its implementation.
- `numbered:` on `#slide`, which already counts slides from phase 03,
  now connected to whatever displays a number.
- The documented pattern for showing a number at all:
  there is no header or footer machinery by design,
  so it is `#place` plus a wrapper around `#slide`, and the manual has to show it working.

### Out of Scope

- A header or footer system, permanently.
- The overlay argument, which is a future feature,
  though the decision below has to remain compatible with it.

## Open Question in Focus

**Slide and subslide numbering.**
The design document states the problem precisely.
`#subslidenum()` cannot work as written, because the HTML output renders one frame per *epoch*,
so a frame covering states 3 to 5 has one baked-in subslide number.
Making it correct would force every `sub` to be its own epoch,
which destroys the cost model the whole design rests on.
`#slidenum()` has no such problem, because it is a plain counter,
but shipping half of the pair is arguably worse than shipping neither.

The three ways out, none chosen:

1. leave both out of 0.1.0;
1. ship `#slidenum()` only;
1. find a form in which the subslide number is a runtime value the browser substitutes
   rather than rendered ink.

Two constraints apply to whatever is chosen.
It must also work for the `numbered:` counter,
and it must work for the overlay under *Potential Future Features*,
which is redrawn per epoch and therefore has the identical limitation.
Option 3 is the interesting one:
the runtime already knows the current slide and subslide, because they are in `location.hash`,
so substituting text into a labelled group is not obviously hard.
Whether it is worth the asymmetry with the paged outputs, where the number is simply ink,
is the real question.

This is a lasting API decision on a package whose first publication is permanent.
Ask, with the options and their consequences laid out, before implementing.

## Tests

Whatever is shipped:

- tier 1: the counter advances only on `numbered: true` slides;
- tier 2: the number rendered on a presentation page matches the page,
  and on a handout page matches the handout's own numbering,
  which is not the same sequence and is a place to be careful;
- tier 3, if option 3 is chosen: the substituted value is correct on every subslide,
  after a deep link, and after stepping backwards.

If option 1 is chosen, the test is that neither name exists
and that the documented `#place` pattern works.

## Documentation

- `docs/numbering.md`, or a section of `docs/slides.md`:
  what `numbered:` does, what is available for displaying a number,
  and, if something was left out, a plain statement of why.
  An author who expects `#subslidenum()` deserves the reason rather than silence.

## Definition of Done

- The decision is made by the author, recorded in the session log with its reasoning,
  and implemented.
- The documented pattern for showing a slide number compiles and is tested.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 13 writes the manual against the final API, so this phase closes it.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
