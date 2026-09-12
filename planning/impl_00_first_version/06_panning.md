<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 06: Panning

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Canvas and viewport*,
the `pan` entry under *Animation primitives*, rule 5 of *Architecture*,
*Presentation PDF* and *Handout PDF*, and the finding that positions are dead in HTML output
but available on paper.

## Goal

The slipshow-like half of the design: a slide is a viewport onto a larger canvas,
and `pan` moves the viewport over it, in the browser and on paper alike.

## Prerequisites

Phases 01 to 05.

## Scope

### In Scope

- `pan(x:, y:, relto:)`, the first and for 0.1.0 the only **slide primitive**.
  It takes no tag name, acts on the slide as a whole,
  and touches neither tags nor regions nor footprints.
  The resolver must therefore keep slide state separate from element state,
  which is a small refactor of phase 04's model and is the point of doing `pan` before epochs.
- **In HTML, `pan` animates `translate` on the canvas element**, never on the frames.
  The frames are stacked inside the canvas, so moving the canvas moves all of them together
  and keeps them registered, which is what phase 09 needs.
  This is the one place animo touches a transform outside an SVG group,
  and `translate` is used there too, leaving `scale` free for a future zoom.
- **In the paged outputs, a panned step is a page showing a different part of the canvas.**
  The viewport is clipped out of the canvas at the panned position.
  This is what makes panning survive into the paged outputs at all.
- **`relto:`**, "pan so that this tag comes into view", resolved differently per target:
  from the group's bounding box in the browser,
  and from `query` plus `location().position()` in the paged outputs,
  where positions are available, including for content inside math.
- Interaction with `canvas: auto` and `canvas: (width:, height:)` from phase 03,
  now that there is a reason for a canvas larger than the viewport.

### Out of Scope

- Zooming. `scale` on the canvas is deliberately left unused.
- Structural primitives and epochs: phase 07 onwards.

## Open Questions in Focus

1. **Do the two resolutions of `pan(relto:)` agree closely enough?**
   The design document's open question.
   The browser resolves it from a rendered bounding box, typst resolves it from element
   positions, and the two have to produce presentations that look the same.
   Measure the disagreement rather than assuming it is small,
   and decide what to do when it is not:
   a documented tolerance, a rule that makes one target authoritative,
   or a restriction on what `relto:` promises.
   Record the numbers in the session log, because phase 11 and phase 13 both care.
1. **What does a handout page of a panned slide show?**
   Also the design document's open question, and it becomes concrete here.
   Today the handout shows the viewport at the final position,
   so a slide that pans across a large canvas loses everything outside that final viewport
   unless the author asks for snapshots.
   The alternative, a handout page showing the whole canvas scaled to fit,
   is right for panned decks and wrong for ordinary ones,
   because it would shrink every slide whose canvas is a little larger than its viewport.
   A `#slide` argument is the obvious shape but is not decided.
   Note that `sub(handout: true)` does not exist until phase 07,
   so if the answer depends on it, say so and settle the part that does not.

No other open question from the design document is in scope for this phase.

## Tests

- Tier 1: the resolved slide state per step, including `relto:` resolved in the paged target,
  and the canvas extent for a body that places content outside the viewport.
- Tier 2: a panned step produces a presentation page showing a different part of the canvas,
  content outside the viewport is clipped and never spills to another page,
  and the handout behaves as the decision above says it does.
- Tier 3: the canvas element's `translate` changes on a panned step while the frames
  keep their own transforms; the viewport clips; deep-linking to a panned state snaps correctly.
- **Cross-target**: a panned state rendered on paper and screenshotted in the browser
  show the same part of the canvas, within the tolerance established above.

## Documentation

- `docs/canvas.md`: the viewport and the canvas as two rectangles,
  why content does not overflow to a next slide, `pan`, `relto:`,
  and what panning means in each of the four outputs.
- Be explicit about the handout consequence, whichever way the second question is decided.
  An author who pans across a large canvas and prints a handout should not be surprised.

## Definition of Done

- A deck with a canvas larger than the viewport pans smoothly in the browser
  and produces correct presentation pages.
- The `relto:` agreement between the targets is measured and recorded.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 09 stacks several frames inside the canvas element this phase animates,
so the pan transform and the frame transforms must remain independent.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
