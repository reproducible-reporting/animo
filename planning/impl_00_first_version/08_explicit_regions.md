<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 08: Explicit Regions

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Regions*,
the *Should the whole slide body be a region* and *How are group-like containers and tags
related* entries under *Resolved Design Decisions*,
the finding on region footprints across epochs,
and *Consequences of confining reflow to regions*.

## Goal

Real reflow in a bounded area: a region whose interior is laid out afresh for each epoch
while its footprint on the slide never changes,
so that a replacement can push the paragraph below it down
without a single pixel moving outside the region.

## Prerequisites

Phases 01 to 07.

## Scope

### In Scope

- `region(body, width: auto, height: auto, align: top + left, clip: auto, name: none)`.
- **The fixed footprint**: by default the smallest box that fits every state the region
  actually takes on along the timeline, measured per epoch, never per state.
  Explicit `width`/`height` override it.
  `clip` defaults to on when a size is given.
- **Reflow inside the footprint**: line breaks change, following paragraphs shift,
  and `align` decides where a state smaller than the footprint sits.
- **Nesting**: an inner region is itself a fixed footprint,
  so an outer region's layout does not depend on an inner region's state.
  Footprints compose and states do not multiply, which is the cost claim to test.
- **`name:`** makes the region itself addressable,
  so a region can be moved, scaled, hidden or revealed like any tag.
  An unnamed region is invisible to the animation.
- **Block-level semantics**: the footprint is computed against the width of the container,
  which is what makes a region usable inside grids, columns and placed boxes,
  and unusable inside a paragraph.
  Fail clearly in the cases that cannot work.
- The implicit region from phase 07 becomes a special case of this machinery,
  not a parallel implementation.

### Out of Scope

- `region(spill: true)`, the propagating variant: a future feature,
  explicitly deferred because it needs the morph to look right.
- HTML rendering of multiple epochs: phase 09.
- Regions inside cetz canvases and math, where regions do not go and bare tags are the answer:
  phase 10.

## Open Questions in Focus

1. **Does `layout(size => ..)` give a region the right measuring width in every container?**
   The design document's open question, and the one that decides whether regions work
   in real slides.
   The containers that matter are grid cells, `#place`d boxes and columns,
   and possibly a region nested in another region.
   Measure each of them, and where the answer is wrong,
   decide between a documented restriction and an explicit `width:`.
   A region whose footprint is measured against the wrong width fails silently,
   by reserving the wrong amount of space, so a diagnostic is worth more than usual here.
1. **Is the max-footprint rule tolerable in practice?**
   Also the design document's open question.
   A region reserves room for its largest state,
   so a slide whose first state is short and whose last state is tall shows a gap at the start.
   The remedies are meant to be authorial: choose `align`, split into several regions,
   give explicit sizes.
   Build a slide that makes the problem as bad as it gets, look at it,
   and decide whether the authorial remedies are enough
   or whether a per-region "pin the footprint to state *i*" option is needed in 0.1.0.
   Adding it later is additive; shipping it unnecessarily is not.

No other open question from the design document is in scope for this phase.

## Tests

Tier 1:

- the footprint chosen for a region, per axis, as an actual length,
  for a region with several epochs;
- the footprint of a region containing a nested region is independent of the inner region's
  content state, which is the composition claim;
- the number of measurements is linear in epochs, not combinatorial in tags;
- explicit `width`/`height` override the measurement, and `clip` behaves as specified;
- a region used where it cannot work fails with a clear message.

Tier 2, which is the real evidence:

- the y position of content *after* a region is identical in every state,
  which the design document has already measured for two epochs;
- the raster is pixel-identical outside the region's band between two epochs,
  and the comparison reports the band, so a failure is readable;
- a replacement long enough to wrap genuinely reflows within the footprint.

## Documentation

- `docs/regions.md`: what a region is, the fixed footprint and why it is fixed,
  nesting, `name:`, where regions cannot go, and the price of the max-footprint rule
  stated honestly with its remedies.
  The three reasons for the fixed footprint are in the design document and belong here too,
  because an author who does not know them will file the gap as a bug.

## Definition of Done

- A deck with explicit regions, including a nested one, reflows correctly on paper.
- Everything outside a region is provably unchanged between epochs.
- The two open questions are answered with measurements, not impressions.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 09 crossfades exactly these regions,
and its containment claim is true *by construction* only if this phase's footprint
invariant holds exactly.
The resolver must expose, per epoch boundary, which regions changed.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
