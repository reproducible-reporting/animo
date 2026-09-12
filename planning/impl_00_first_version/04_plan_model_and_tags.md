<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 04: The Plan Model and Tags

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Tags*, *Animation primitives*,
*States and epochs*, *Scoping*, and the findings on block-scoped imports
and on the `import *` footgun.

## Goal

The data model of the whole package: tags, a timeline of `sub` steps, and a resolver
that turns them into per-state display state.
Proven on paper first, where every state is simply a page,
so that the model can be tested exhaustively before any browser is involved.

## Prerequisites

Phases 01 to 03.

## Scope

### In Scope

- `tag(name, body, hidden: false, block: false, draw: false)`.
  `removed:` belongs to phase 07 with the rest of the content state.
  A tag emits a labelled outer box wrapping an unlabelled inner box,
  which is the two-slot structure phases 05 and 09 depend on.
  Build it now even though nothing uses the outer slot yet.
- The same tag name used several times in one slide addresses all of them together.
  The same tag name in different slides does not interfere.
- `sub(..ops)` and the `anim` module with the four continuous element primitives:
  `reveal`, `hide`, `move`, `scale`.
  `pan` is phase 06.
  Primitives return plain descriptors and perform no action.
- **Resolution**: a slide with *S* `sub` calls has *S+1* states.
  State 0 is the body as declared, state *i* is state *i-1* with the *i*-th step applied.
  Continuous operations accumulate.
- **`sub` validates its own arguments.**
  This is the `import *` footgun from the findings:
  a star import silently falls through to the standard library,
  so `rotate("b", 45deg)` inside the animation block quietly calls `std.rotate`
  and returns content.
  `sub` must panic with a message that names the offending argument
  and says what went wrong, not "does not have field".
- **Per-slide plan publishing**, which is the first open question below.
- **Presentation PDF**: one page per state.
  `hidden:` and `hide` use typst's own `hide()` here, which is correct in the paged target
  and forbidden in HTML.
  `move` and `scale` use the typst built-ins.
- **Handout PDF and SVG**: the final state of each slide, unchanged from phase 03.
- Block-scoped import: `{ import anim: * ... }` inside the animation argument,
  with `move`, `scale` and `hide` remaining the typst built-ins everywhere else,
  including in the slide body.

### Out of Scope

- The HTML runtime: phase 05. In this phase the HTML output may still render state 0 only,
  or the final state, as long as it compiles and the choice is documented as temporary.
- Structural primitives, epochs, regions: phases 07 and 08.
- `pan`: phase 06.

## Open Questions in Focus

1. **Is the per-slide plan better published as a state or passed down through a show rule?**
   The design document's open question, and this is the phase that creates the mechanism.
   `#slide` must publish its plan before the body is laid out,
   in *both* targets, because tags read it in a `context` block
   and phases 07 and 08 will have regions measuring against it.
   A state is the obvious mechanism and is what the design document assumes,
   but the question is explicitly about what happens once real decks wrap `#slide`
   in their own functions, which is the documented way to get recurring elements.
   Try that case deliberately in this phase rather than waiting for it to break in phase 13.
1. **Should `tag` default to `box`, with `block: true` as the escape hatch,
   or detect block-level bodies automatically?**
   Also the design document's open question.
   It matters here because the wrapping decides which elements become addressable groups
   in the SVG output, and a wrong default is a confusing failure much later,
   in the browser, with no diagnostic.
   Detection is attractive and may be unreliable;
   if it is, an explicit default with a good error message beats a clever guess.

No other open question from the design document is in scope for this phase.

## Tests

Tier 1 carries most of the weight here, and this is the phase that proves the tier was worth
building:

- resolved per-state display state for a timeline exercising all four primitives,
  including accumulation across steps and operations on a tag that appears several times;
- state count equals *S+1*, and an empty `sub()` advances a step without changing anything;
- assertions target the *resolved structure*, tag names and per-state flags,
  never the payloads, which do not compare usefully;
- the footgun: a document passing a non-animo value to `sub` must fail to compile,
  with the explanation on stderr;
- tag scoping: the same name in two slides resolves independently.

Tier 2: the presentation PDF has one page per state,
and the pages show the expected reveal, hide, move and scale results.
Nothing moves between states except what the timeline says moves.

## Documentation

- `docs/tags.md`: `tag`, its arguments, several sites sharing a name, and the scoping rule.
- `docs/animation.md`: `sub`, the block-scoped import and why it exists,
  the continuous primitives, and the state model.
  Be explicit that the timeline is read before the body is laid out,
  because that is the reason the animation is an argument rather than a trailing marker.

## Definition of Done

- A deck with tags and a timeline produces a correct presentation PDF, one page per state.
- Tier-1 assertions cover the resolver, including the failure case.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 05 consumes exactly this resolved display state in the browser
and needs the two nested slots this phase emits.
Phase 07 extends the resolver with content state and epochs,
so leave the resolver's structure open to that rather than hard-coding a display-only model.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
