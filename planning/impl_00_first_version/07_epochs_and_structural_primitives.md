<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 07: Epochs and Structural Primitives

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *States and epochs*,
the structural half of *Animation primitives*, the implicit-region rule under *Regions*,
the *Where does time-dependent content live* entry under *Resolved Design Decisions*,
and the finding on region footprints across epochs.

## Goal

Content that changes: `replace`, `remove`, `apply` and `reset`,
with the epoch model that makes them affordable,
proven in the paged outputs where every state is simply a fresh rendering.

Regions are present in this phase only in their implicit form,
one per bare tag, which is the simplest possible container to get the measuring right in.
Explicit regions are phase 08.

## Prerequisites

Phases 01 to 06.

## Scope

### In Scope

- **The four structural primitives**:
  - `replace(tag, body)`, substituting new content at the tag site;
  - `remove(tag)`, dropping the content and freeing its space;
  - `apply(tag, ..fns)`, wrapping in content-to-content functions, applied outermost-last,
    accumulating across steps;
  - `reset(tag)`, back to the body's own content with all wrappers dropped.
    `apply` takes functions only. Named style properties are deliberately not supported,
    because animo does not inspect content and cannot know which `set` rule a property belongs to.
- **`tag(.., removed: true)`**, the initial-state counterpart of `remove`,
  completing the tag signature from phase 04.
- **Epoch resolution.**
  An epoch is a maximal run of consecutive states with the same content state.
  A new epoch starts at every state whose `sub` contains at least one structural operation.
  A slide with no structural operations has exactly one epoch,
  which must remain exactly as cheap as it was in phase 04.
  The content state of an epoch fixes, for every tag, its content and its accumulated wrappers.
- **The implicit region**: a tag not inside an explicit region is its own region.
  Its footprint is the per-axis maximum over the epochs the slide actually has,
  measured with `measure` inside `layout(size => ..)`.
  Cost is linear in epochs, never combinatorial in tags.
  Note that `removed:` and `hidden:` are indistinguishable inside an implicit region,
  because the footprint reserves the maximum either way.
  Say so in the documentation rather than letting an author discover it.
- **`sub(handout: true, ..ops)`**, requesting an extra handout page at that step,
  on top of the final state every slide contributes.
  It is a keyword on `sub`, not a free-standing call between `sub` calls.
- The paged outputs render this correctly:
  the presentation PDF still has one page per state, now with content changes in place;
  the handout has one page per slide plus one per `handout: true`.

### Out of Scope

- Explicit `region`: phase 08.
- HTML epoch frames and crossfades: phase 09.
  The HTML output in this phase may render one frame per slide at a fixed epoch,
  as long as it compiles and the limitation is recorded, not documented as a feature.
- `once`, morphing, `recolor`: future features.

## Open Questions in Focus

1. **Does the epoch-as-a-state-variable mechanism hold in practice?**
   The design document is precise about this and it is load-bearing:
   a region cannot rewrite the tags nested inside it, because it receives its body as opaque
   content.
   So the current epoch is itself a state variable,
   and a region measures by laying its own body out once per epoch with that variable set,
   each tag resolving its own content for that epoch as it is laid out.
   Verify that this works in both targets, inside `measure` and inside `layout`,
   with nested `context` reads, and that it produces no introspection cycle and no
   convergence warning.
   If it does not hold, everything downstream changes, so test it before building on it.
1. **What exactly do the structural primitives compose to?**
   The design document defines each primitive alone but leaves their interaction open,
   and this phase cannot avoid deciding it.
   At least these cases need an answer, a test and a documented rule:
   - `apply` then `replace`: does the replacement inherit the accumulated wrappers?
   - `replace` then `apply`: does the wrapper apply to the replacement, or to the body?
   - `reset` after `remove`: does the content come back, and with which wrappers?
   - `replace` twice, and `apply` of two functions in one step versus in two steps;
   - a structural and a continuous operation on the same tag in the same `sub`,
     which must animate in lockstep once phase 09 exists.
     These are lasting semantics that the manual will state, so ask rather than decide alone.

No other open question from the design document is in scope for this phase.

## Tests

Tier 1 is where this phase is really tested, and it should be thorough,
because the epoch model is the part of the design most likely to be subtly wrong:

- epoch boundaries and epoch counts for timelines mixing continuous and structural steps,
  including a timeline with no structural steps, which must resolve to exactly one epoch;
- the resolved content state per epoch, asserted on structure, never on payloads;
- the footprint chosen for each implicit region, per axis, as an actual length;
- the composition cases listed above, one assertion each;
- the number of renderings the model asks for, which is the cost claim of the design.

Tier 2:

- everything outside an implicit region is pixel-identical between two states
  that differ only by a structural operation;
- a `replace` with content long enough to wrap reflows inside the footprint and nowhere else;
- `handout: true` adds exactly one page in the expected place;
- the presentation PDF still has one page per state.

## Documentation

- `docs/structural.md`: the four primitives, the epoch model in author-facing terms,
  and the composition rules decided above.
- The lossy handout, stated plainly:
  `replace` and `remove` destroy content, the handout shows the final state,
  and `handout: true` is the only way to keep an intermediate one.
  Typst gives packages no way to emit a warning, so the manual is the only place this can be said.
- The implicit region, and why `remove` outside an explicit region costs an epoch
  and buys nothing, so that `hide` is the right primitive there.

## Definition of Done

- A deck with content changes produces correct presentation and handout PDFs.
- Epoch counts and footprints are asserted in tier 1 and match the design's cost model.
- The composition rules are decided, tested and documented.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 08 generalises the implicit region into the explicit one,
so keep the footprint machinery separate from the tag.
Phase 09 renders one frame per epoch and crossfades the regions whose content state changed,
so the resolver must already be able to say *which* regions changed at a given boundary.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
