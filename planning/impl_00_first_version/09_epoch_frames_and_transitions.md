<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 09: Epoch Frames and Transitions

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Architecture* in full, especially rules 1 to 5,
the findings on crossfading epoch frames, on SVG `<defs>` ids being content hashes,
and on cross-frame geometry being readable.

## Goal

Structural steps in the browser.
Each epoch of a slide is one `html.frame`, the frames are stacked,
and a structural step crossfades the regions whose content changed
while everything else stays pixel-identical.

With this phase, all four outputs support the full 0.1.0 feature set.

## Prerequisites

Phases 01 to 08.

## Scope

### In Scope

- **One `html.frame` per epoch**, stacked in a single grid cell of the canvas element
  in document order, with `isolation: isolate` on the parent.
  The shell for this was built in phase 03 and the canvas motion in phase 06;
  this phase fills it with more than one frame.
- **Rule 1: continuous state is applied to all epoch frames at once**, not only the active one.
  Entering an epoch then needs no re-initialisation,
  and a `sub` carrying both a `replace` and a `move` animates in lockstep in the outgoing
  and the incoming frame.
  An operation on a tag absent from a frame is a no-op in that frame.
- **Rule 2: the crossfade is scoped to the regions whose content state changed**,
  with `mix-blend-mode: plus-lighter` between the two regions' labelled groups.
  Outside those regions the frames are pixel-identical by phase 08's invariant,
  so the incoming frame sits opaque on top.
  The whole-frame crossfade, already measured at 1/255 deviation outside the region
  against 62/255 for a plain opacity crossfade, is the verified fallback.
- **Rule 4: the labelled outer group is the boundary slot, the inner group the continuous one.**
  Phase 04 emits both and phase 05 uses only the inner one,
  so this phase writes to the outer slot for the first time.
  The ordering is not a matter of taste:
  a boundary effect is measured in the frame's own coordinates
  and must sit above the continuous transforms.
- **A swappable transition strategy.**
  The design document asks for this explicitly, because the answer to the second open question
  below may be that a crossfade is the wrong transition for some content,
  and because the morph is the intended successor.
  One named strategy, selected in one place, with the crossfade as the only implementation
  in 0.1.0.
- **A shared clock.** Epoch crossfades run on the same driver as the continuous animations
  from phase 05, which is what makes a mid-transition assertion reproducible.
- Stacked frames put duplicate `<defs>` ids in one DOM.
  This is harmless, because typst's def ids are content hashes,
  so equal ids mean equal content.
  Confirm it rather than assume it: it is cheap to check and expensive to be wrong about.

### Out of Scope

- Morphing: a future feature. Leave the seam, build nothing.
- Hoisting shared glyph defs: a future feature, and phase 11 decides whether it is needed.
- Page weight measurement: phase 11.

## Open Questions in Focus

1. **Does the region-scoped `plus-lighter` crossfade blend correctly?**
   The design document's open question, and the one this phase exists to answer.
   The measured result is for the whole-frame crossfade;
   the same blend between two labelled `<g>` elements in two *different* inline SVGs
   within one isolated stacking context is not measured.
   Measure it the same way: both frames at the midpoint, compared against a single frame,
   and report the maximum deviation outside the region.
   If it does not behave, fall back to the whole-frame crossfade,
   which is verified, and record why.
   The fallback changes the containment claim from exact to 1/255,
   which is worth stating in the documentation if it is what ships.
1. **How does a crossfade read when the region's content really reflows?**
   Also the design document's open question, and it is answered by watching, not by measuring.
   Ghosting of two text layouts at once is acceptable for a replacement
   but may look wrong for a small edit in a large paragraph.
   Build both cases, watch them, and record the judgement in the session log.
   If it reads badly, that is the evidence that the morph is needed,
   and the swappable strategy above is what makes adding it later cheap.

No other open question from the design document is in scope for this phase.

## Tests

Tier 3, and the two invariants the region design rests on come first,
because both are comparisons within one page load and need no stored images:

- the bounding box of every label *outside* a region is identical in all epoch frames
  of a slide;
- the rendering is pixel-identical outside the region between epochs,
  **and stays so mid-crossfade**, sampled by setting the clock rather than racing a transition.

Then:

- a slide with *E* epochs emits exactly *E* frames, and a slide with no structural steps
  emits exactly one, which is the cost claim;
- a step carrying both a structural and a continuous operation on the same tag
  moves identically in both frames;
- a deep link into a state inside an epoch shows the right frame and snaps without animating;
- stepping backwards across an epoch boundary returns to the earlier rendering exactly.

Tier 2 must keep passing unchanged.

## Documentation

- `docs/structural.md` gains the browser half: what a structural step looks like,
  why it is a crossfade and not motion, and what that means for the author's choices.
- `docs/architecture.md` for contributors: the five rules, the two transform slots,
  and where the transition strategy is selected.
  This is the page the morph will be added against.

## Definition of Done

- A deck with structural steps animates correctly in chromium,
  with continuous and structural steps composing in one `sub`.
- The containment invariants hold, mid-transition included.
- The crossfade question is answered with a number and the reflow question with a judgement.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 10 puts tags in places where frames and regions behave differently.
Phase 11 measures what this phase costs in page weight, which is the known price of stacking
frames that each carry their own glyph defs.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
