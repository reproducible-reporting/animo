<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 10: Tag Sites in Math, cetz and fletcher

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are the tag site table under *Tags*,
the *Where regions cannot go* paragraph under *Regions*,
the finding that `data-typst-label` works inside math and inside cetz canvases,
the finding about labels inside math needing `#box(body)#label(name)` rather than a space,
and the comparison with `sanor`'s `test/draw.typ`.

## Goal

The claim that makes animo worth building: *anything typst can lay out as content can be tagged*.
This phase makes that true for the places it is hardest,
and makes the exceptions explicit rather than accidental.

## Prerequisites

Phases 01 to 09.

## Scope

### In Scope

- **Tags inside math.**
  Both structural and continuous primitives must work at a tag site inside an equation,
  including replacing part of an equation.
  Mind the parsing trap: `#box[b] <bb>` with a space is literal math content,
  whereas `#box(body)#label(name)` attaches correctly.
- **Tags on cetz `content()` elements and on fletcher nodes.**
  Both are content, so both support the full set of primitives.
- **`tag(.., draw: true)`**: no wrapping at all, for raw cetz draw commands,
  which are a draw-command stream rather than content and would be destroyed by a box.
  Structural primitives reach these because typst renders the epoch;
  continuous primitives do not, because they need a labelled group the browser can address.
- **The support matrix from the design document, enforced.**
  A continuous primitive applied to a `draw: true` tag should fail with a message that
  says why, not silently do nothing.
  A silent no-op in the browser is the worst possible diagnostic,
  because it appears three tools away from its cause.
- **Implicit regions in these contexts.**
  A `draw: true` tag has no box to bound,
  so its implicit region is the enclosing cetz canvas, which is a region-sized unit already:
  a structural change there redraws the canvas.
- A test deck exercising all of it, which also becomes an example in phase 13,
  because this is what an author will want to copy.

### Out of Scope

- Making `region` work inside a cetz canvas or inside math.
  The design document is explicit that it does not, and that bare tags are the answer.
  Document the boundary, do not try to move it.
- Any new primitive.

## Open Questions in Focus

1. **Does a `draw: true` tag survive every cetz construct,
   and what should it do when it wraps draw-*state* commands?**
   The design document's open question.
   `stroke` and `set-style` change the draw state rather than emitting geometry,
   so a tag wrapping them has nothing to show and possibly something to break.
   `sanor`'s `test/draw.typ` is the reference case:
   it tags a `draw.grid(..)` and applies wrappers to it, which is exactly the parity to match.
   Decide what happens for the state-changing case:
   support it, refuse it with a message, or document it as undefined.
   The sibling checkout `../sanor` is available and is worth reading before deciding.
1. **Do implicit regions around bare tags behave acceptably inside cetz canvases and math?**
   Also the design document's open question.
   The surrounding layout is not a flow in either place,
   so the max-footprint rule that phase 08 validated for block content may read very differently
   here: reserving the largest state's space inside an equation can shift the whole equation,
   and inside a cetz canvas the notion of reserved space may not apply at all.
   Measure it, and if the behaviour is surprising, document it with the workaround
   rather than special-casing it.

No other open question from the design document is in scope for this phase.

## Tests

- Tier 1: a tag inside math, on a cetz `content()`, on a fletcher node and on raw draw commands
  all resolve; the footprint of each implicit region is as expected;
  a continuous primitive on a `draw: true` tag fails to compile with the expected message.
- Tier 2: replacing part of an equation reflows only that equation;
  restyling a tagged `draw.grid(..)` redraws the canvas and nothing else on the slide.
- Tier 3: a tag inside math and a tag on a cetz `content()` element
  emit `<g data-typst-label>` groups and animate under the continuous primitives;
  a `draw: true` tag emits no such group, which is the reason for the restriction
  and is worth asserting directly so that a future typst change is noticed.
- Add probes for whatever new typst behaviour this phase measures,
  following phase 02's rule that a finding gets a probe.

## Documentation

- `docs/tags.md` gains the tag site table, with the asymmetry explained:
  structural primitives are resolved by typst when the epoch is rendered,
  so they work wherever a tag can wrap anything at all;
  continuous primitives are resolved by the browser and need a labelled group.
- A worked example for each site: math, cetz `content()`, fletcher, raw draw commands.
- The boundary: where `region` cannot go and why a bare tag is the answer there.

## Definition of Done

- A deck tagging content in math, in cetz and in fletcher animates and reflows correctly
  in every output that supports it.
- Unsupported combinations fail with messages that name the cause.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 11 benchmarks a realistic deck, which should include the constructs from this phase,
because a cetz canvas redrawn per epoch is the most expensive thing animo can be asked to do.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
