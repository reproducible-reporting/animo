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

The relevant parts of the design document are *Tags*, *Regions*, *Animation primitives*,
*States and epochs*, *Architecture* and *Scoping*,
plus the findings on `data-typst-label`, on block-scoped imports and on the `import *` footgun.

This file was rewritten after a review session that measured what the phase rests on.
*Ground Truth* records those measurements,
*The Model* states what is to be built and why it has the shape it has,
and *Decisions* closes the two questions this phase used to carry.
There are no open questions left in this phase.
Read those three sections before the scope list: the scope list only summarises them.

## Goal

The data model of the whole package: tags, a timeline of `sub` steps, and a resolver
that turns them into per-state display state.
Proven on paper first, where every state is simply a page,
so that the model can be tested exhaustively before any browser is involved.

## Prerequisites

Phases 01 to 03.

## Ground Truth

Measured on typst 0.15.1 during the review session that rewrote this file,
and recorded in the design document's *Findings*.
Each item has a probe under `probes/`, named under *Tests* below.

### Wrapping Is Never Free, and `box` Versus `block` Is the Wrong Axis

A page was rasterised at 144 ppi with and without a wrapper around one element,
and the rasters compared pixel by pixel.

| Tagged body                 | `box(box(x))` | `block(block(x))` | `block(width: 100%)`, twice |
| --------------------------- | ------------- | ----------------- | --------------------------- |
| markup list, grid, table    | identical     | identical         | identical                   |
| a paragraph that wraps      | identical     | identical         | identical                   |
| `figure`, `$ .. $`, `align` | left-aligned  | left-aligned      | identical                   |
| `= Heading`                 | shifts        | shifts            | shifts                      |

Three consequences, and they are the reason the wrapping question was hard to settle before:

1. For content that already sits between paragraph breaks,
   a `box` and a `block` render **identically**.
   The axis that matters is not inline versus block but **hugging versus filling**:
   a wrapper at `width: auto` hugs its content, which left-aligns anything
   the container was centring.
   `block(width: 100%)` reproduces the original rendering.
1. A `heading` shifts under *every* wrapper, by about 5 pt at 11 pt text.
   A heading carries its own block spacing (1.8em above and 0.75em below at level 1,
   in `typst-library/src/model/heading.rs`),
   that spacing sits at the wrapper's edge and is trimmed there,
   and the wrapper contributes the generic 1.2em instead.
   Neither `heading.above` nor `block.spacing` is readable from a `context` block
   (`text.size`, `par.spacing` and `heading.numbering` are),
   so animo cannot copy the value it would have to restore.
   The documentation says to tag the heading's text, `= #tag("t")[Head]`, when the shift matters.
1. A tagged inline phrase becomes unbreakable, so the paragraph around it can reflow.
   That one is inherent: a group that CSS can translate cannot be split across two lines.

### Inline Versus Block Is Decidable by Measurement

Put a zero-sized box on each side of the body and measure:

```typ
let nothing = box(width: 0pt, height: 0pt)
let is-block = measure([#nothing#body#nothing]).height > measure(body).height
```

Block-level content forces the two neighbours onto lines of their own,
inline content does not.
Over 31 constructs the separation was **exactly 0.0 pt** for every inline case
and **at least 12 pt** for every block-level one, so the comparison needs no tolerance.
It needs no available width either:
an unbounded `measure` resolves a `100%` width to zero rather than to infinity,
and every verdict was the same as with a width given.

It sees through what inspection cannot.
A `context` block reports the block-ness of whatever it produces;
`#layout(..)` reports block, which is what it is, whatever it returns.

It has one blind spot.
Content that is itself **several paragraphs** measures as inline,
because the neighbours merge into the first and the last paragraph instead of being pushed off.
A scan for a `parbreak` in the body's own sequence covers it.

Inspection was measured as well, and is recorded because it is what a reader expects to use:

- a markup list or enum is a **`sequence` of `item`**, not a `list`;
  `list.item`, `enum.item` and `terms.item` all report as `item`;
- `#text(red)[..]` and a `#set` block are both `styled`, with the real element at `.child`;
- `image`, `rect`, `circle`, `line`, `stack`, `grid`, `columns`, `place`,
  and also `move`, `scale` and `layout`, are block-level;
- `box`, `hide`, `footnote`, `metadata`, inline math and inline raw are inline;
- `context` has no fields at all, so inspection stops there.

The table is closed, because a package cannot define an element,
but it is only closed per typst release, and it does not cover `context`.
That is why this phase measures rather than classifies.

### A State Cannot Carry What Must Vary Inside `measure`; a Show Rule Can

`state.get()` inside `measure(..)` resolves at the location of the **enclosing** context block,
not at some position inside the measured content.
So a caller cannot set a state, measure, set it again and measure again:
both measurements see the same value.
That is fatal for the region of phase 08, which has to measure its body once per epoch,
and it is what decides this phase's first question.

Passing the value down a show rule does work.
The child emits a marker carrying a function, an ancestor installs the rule that calls it:

```typ
#let ask(f) = context [#metadata(f)<animo-ask>]
#let provide(value, body) = {
  show <animo-ask>: it => (it.value)(value)
  body
}
```

Measured: two `measure` calls in one context block, with different values provided,
give different results.
Providers nest and the innermost wins.
The rule fires on a marker that a `context` block produced,
and on a marker inside the content another marker produced, so tags may be nested.
The marker's own label does not leak: a tag built this way emits exactly one
`data-typst-label`, the tag's own.

One thing does not work.
A marker that no provider replaced is **not** distinguishable afterwards:
`query(<animo-ask>)` returns replaced and unreplaced markers alike.
So "a tag outside any slide" cannot be diagnosed after the fact and is diagnosed at the tag site,
from a state that `slide` sets around its body.

### Transforms Inside the Tag's Box Are Layout-Neutral

`box(move(dx: .., dy: .., ..))`, `box(scale(.., reflow: false, ..))` and `box(hide(..))`
measure identically to `box(..)`, in width, in height and in their effect on the line around them,
even though `move` and `scale` are block-level elements.
The same holds for `block(width: 100%, move(..))` against `block(width: 100%, ..)`.

This is what lets the presentation PDF apply a state's display state with typst's own elements
without disturbing the layout,
and it is what makes "nothing moves between states except what the timeline moves" an invariant
rather than a hope.
The structure a tag emits is therefore the same in every state and in both targets;
only the parameters inside it change.

## The Model

### Where the Container Requirement Belongs

A `box` or a `block` is needed for two unrelated reasons, and separating them settles the API:

- **To be addressable in the browser.**
  Only a labelled box or block becomes a `<g data-typst-label>`,
  so a tag that a continuous primitive addresses has to be one.
  No region and no redraw can supply this: `move("x")` moves `x`, not the area around it.
- **To bound a redraw.**
  A structural change is rendered by typst and has to be contained,
  which is what a region is: a fixed footprint that is laid out afresh per epoch.

The second requirement lands on the **region**, not on the tag,
and a tag that is inside an explicit region needs no container of its own for it.
A bare tag is its own implicit region and needs one.
This is the answer for cetz and anything else that is not content:
put the `region` around the whole canvas, outside the drawing,
and tag inside it without wrapping.
The price is that a structural change redraws the whole figure, which is the right compromise.

A region therefore needs no detection at all.
A region is block-level, so it is always a `block(width: 100%, ..)`,
which is also the width its footprint is measured against.

The reason it is block-level is worth stating, because it is not the one the wording suggests.
It is not that the surroundings have to stay still:
a box whose footprint is fixed at the maximum over its epochs holds its paragraph as still
as a block holds its flow, since constant size means constant line breaking.
It is that **a region with `width: auto` has to know its container's width**.
Sizing means measuring every epoch at that width and taking the per-axis maximum,
and `layout(size => ..)` is the only way to learn it, and `layout` is block-level:
it breaks the line it is put in (measured).
Inline, the best available is an unbounded `measure`, which reports the natural width of content
that was never given the chance to wrap.
A box does wrap correctly once a width is given
(a box at 6 cm measures 154.95 pt by 19.66 pt for a text that measures the same bare),
so what is missing inline is the width, not the box.
An explicitly sized region could therefore be a box, and 0.1.0 still does not offer one:
the inline case already exists as the implicit region around a bare tag.

That implicit region inherits the same limit, which phase 08 has to face:
its footprint can only come from unbounded measurements,
so content that is replaced at an inline tag site cannot wrap.
Inline tag sites hold short content, and the documentation should say so.
It should **not** reuse a `box` or `block` that its body happens to already be:
the region has to own `width`, `height`, `clip` and `align`,
merging those into an author's element means rebuilding it from `fields()`
and losing whatever a `set` rule or a show rule contributed,
and the extra nesting it would save costs nothing
(two nested `block(width: 100%)` render identically to one, measured above).
The only thing a region cannot do is wrap something that is not content, and there it panics.
None of this is built in this phase; it is here because it is what `tag` has to leave room for.

### What `tag` Emits

```typ
tag(name, body, hidden: false, removed: false, wrap: auto)
```

A tag **always** wraps unless it is told not to.
The wrapping is a property of the slide body alone and never of the timeline,
so that adding an animation step cannot reflow a paragraph,
and so that the four outputs and the S+1 states all lay out the same.

The emitted structure is the two nested slots the architecture asks for,
with the label on the outer one, the transforms on the inner one,
and the same shape in every state and both targets:

```typ
[#W(W(move(dx: .., dy: .., scale(.., reflow: false, body))))#label(name)]
```

`move` is outside `scale` because CSS composes its individual properties that way,
and `hide(body)` replaces `body` when the resolved display state says hidden.
In the HTML target the parameters are the identity and nothing is hidden;
phase 05 puts the display state on the groups as CSS.

`wrap` takes:

| Value      | Wrapper `W`                                                               |
| ---------- | ------------------------------------------------------------------------- |
| `auto`     | `box` or `block(width: 100%)`, decided by the measurement above           |
| `box`      | `box`                                                                     |
| `block`    | `block(width: 100%)`, because a hugging block loses the container's align |
| `none`     | no wrapper, no label, the body is returned untouched                      |
| a function | the function builds the inner slot, animo matches the outer one to it     |

`wrap: none` is the design document's `draw: true`, generalised:
it is the tag site that supports structural primitives and not continuous ones.
A function is accepted so that the inner slot can carry ink of its own
(`box.with(inset: 4pt, stroke: red)`), which then moves and scales with the element.
Animo digs through a `styled` result and requires what is left to be a `box` or a `block`,
panicking with the name of the tag otherwise, because nothing else becomes an addressable group.
The outer slot is then a plain wrapper of the same kind.

`hidden: true` is the initial-state counterpart of `hide` and keeps the element's space.
`removed: true` belongs to phase 07 with the rest of the content state and panics here.

Panics, all naming the tag:

- the body is not content and `wrap` is not `none`
  (this is the cetz case, and the message says to use `wrap: none` inside a `region`);
- a continuous primitive addresses a tag whose `wrap` is `none`,
  which is the failure that would otherwise be a silent no-op in the browser much later;
- `wrap` is a function whose result is neither a box nor a block;
- the tag is not inside a `#slide`.

### Why the Plan Is Provided Rather Than Published

`#slide` resolves its timeline once and **provides** the result to its body
through the marker and show rule measured above,
rather than publishing it to a state that tags read.
The paged target renders S+1 pages and provides a different state to each.
The reasons, in order:

- A state cannot vary inside `measure`, and phase 08's region has to do exactly that.
  Choosing the state now would mean rewriting `tag` in phase 08
  and invalidating the tests of phases 04 to 07.
- A provider is lexically scoped to the body, so a deck that wraps `#slide`
  in its own function changes nothing, which is what the question asked about.
- The tag receives its display state as an argument instead of reading it from
  a document position, so the canvas measurement in `slide` cannot read the wrong slide's plan
  by resolving at the wrong location.

What is provided is a small dictionary, the **view**:
the state index (`none` in HTML), the epoch (always 0 in this phase),
the resolved display state of that state keyed by tag name,
and the names the timeline addresses with a continuous primitive anywhere in the slide.
The last entry is there for the diagnostics below,
which have to fire in state 0 as well and cannot wait for the state in which the tag moves.
Phase 07 adds the content state to the same dictionary, which is why it is a dictionary.

One state remains, and it is not the plan:
`slide` marks that a body is being laid out, so that `tag` can panic when it is used outside one.

### The Resolver

A slide with *S* `sub` calls has *S+1* states.
State 0 is the body as declared, state *i* is state *i-1* with the *i*-th step applied,
and continuous operations accumulate:
`move` adds, `scale` multiplies, `reveal` and `hide` overwrite.

The display state of a tag is `(hidden: none, x: 0pt, y: 0pt, scale: 1.0)` before anything
addresses it.
`hidden: none` means "no `reveal` or `hide` has happened yet",
which is what lets the tag fall back to its own `hidden:` argument:
the resolver never sees that argument, because it is written in the body and not in the timeline.

The resolved plan is
`(states: ((display: (:), epoch: 0, handout: false), ..), epochs: ((:),))`.
The epoch fields are placeholders that phase 07 fills in;
they are in the shape from the start so that phase 07 extends the resolver instead of replacing it.

`sub` validates its own arguments, which is the `import *` footgun from the findings:
a star import falls through to the standard library, so `rotate("b", 45deg)` inside the
animation block quietly calls `std.rotate` and returns content.
`sub` panics naming the offending argument and saying what it got,
not "does not have field".
`sub` returns a **one-element array**, never a bare dictionary:
a code block joins arrays, and it *merges* dictionaries,
so two `sub(..)` calls returning dictionaries would silently become one step.

## Scope

### In Scope

- `src/plan.typ`: the resolver, the view, the provider and the marker, and the tag label.
- `src/wrap.typ`: the `auto` decision, the `wrap` argument's other forms, and their panics.
- `src/tag.typ`: `tag` as described above; `region` stays the phase-08 placeholder.
- `src/anim.typ`: `sub` with validation, and `reveal`, `hide`, `move`, `scale`.
  `pan` is phase 06 and the structural primitives are phase 07: they stay placeholders
  that panic when used, rather than being silently accepted by the resolver.
- `src/slide.typ`: resolve the timeline, provide the view, emit one page per state
  in the presentation PDF, and keep the handout at the final state.
  `data-animo-states` carries S+1 from now on.
- The same tag name used several times in one slide addresses all of them together;
  the same name in different slides does not interfere.
- Block-scoped import: `{ import anim: * .. }` inside the animation argument,
  with `move`, `scale` and `hide` remaining the typst built-ins everywhere else.

### Out of Scope

- The HTML runtime: phase 05.
  This phase emits the two slots and the labels in HTML and applies **no** display state,
  so a `hidden: true` tag is visible there.
  Say so in `docs/animation.md`, as a temporary state of affairs.
- Structural primitives, epochs, regions: phases 07 and 08.
- `pan`: phase 06.
- Caching the `wrap: auto` measurement.
  It costs two `measure` calls per tag site per rendering, which is a benchmark item for
  phase 11, and `wrap: box` is the escape hatch in the meantime.

## Decisions

Both of the design document's open questions that this phase carried are answered above:

1. **Published as a state or passed through a show rule?**
   Passed down, as a view, through a marker and a show rule.
   The measurement that decides it is that a state cannot vary inside `measure`.
1. **Does `tag` default to `box`, or detect block-level bodies?**
   It detects, by measuring whether the body breaks the line, which is exact,
   and it chooses between `box` and `block(width: 100%)` rather than between `box` and `block`.
   `wrap:` overrides it, and replaces both `block:` and `draw:` from the design document.

## Tests

Tier 1 carries most of the weight here, and this is the phase that proves the tier was worth
building.
The wrapper a tag chose is visible to an assertion as `query(<name>).first().func()`.

- resolved per-state display state for a timeline exercising all four primitives,
  including accumulation across steps and operations on a tag that appears several times;
- state count equals *S+1*, and an empty `sub()` advances a step without changing anything;
- assertions target the *resolved structure*, tag names and per-state flags,
  never the payloads, which do not compare usefully;
- the footgun: a document passing a non-animo value to `sub` must fail to compile,
  with the explanation on stderr;
- tag scoping: the same name in two slides resolves independently;
- `wrap: auto` picks a `box` for a phrase, a heading's text and inline math,
  and a `block` for a list, a grid, a figure and a body of several paragraphs;
- each panic listed under *What `tag` Emits*, by its message;
- `#slide` wrapped in a deck's own function still reaches its tags,
  which is the case the show-rule question was really about.

Tier 2: the presentation PDF has one page per state,
the pages show the expected reveal, hide, move and scale results,
and `assert_identical_outside` proves that nothing moves between two states
except inside the box of the tag the timeline moved.
One more: a slide whose tags are never addressed renders identically
whether or not it carries a timeline.

The probes for *Ground Truth* are already in the tree,
written by the review session that measured them:
`probes/test_wrapping.py`, `probes/test_levels.py`, `probes/test_providing.py`
and `probes/test_paged_transforms.py`.
They import nothing from `src/`, so a failure there names the typst behaviour
rather than an animo bug, and this phase only has to keep them green.

## Documentation

- `docs/tags.md`: `tag`, its arguments, `wrap:` and what each value is for,
  several sites sharing a name, the scoping rule,
  and an honest paragraph on what tagging costs:
  an inline phrase stops breaking across lines, and a heading shifts.
- `docs/animation.md`: `sub`, the block-scoped import and why it exists,
  the continuous primitives, the state model,
  and the note that the HTML output does not animate yet.
  Be explicit that the timeline is read before the body is laid out,
  because that is the reason the animation is an argument rather than a trailing marker.

## Definition of Done

- A deck with tags and a timeline produces a correct presentation PDF, one page per state.
- Tier-1 assertions cover the resolver, the wrapping decision and every failure case.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 05 consumes the view in the browser and needs the two nested slots this phase emits.
Phase 06 adds `pan` to the view as a slide-level entry rather than a tag entry.
Phase 07 extends the view with content state and a real epoch number,
and phase 08's region provides a view of its own while it measures footprints,
which is the reason the view is provided rather than published.
Phase 10 inherits the cetz question in its new form:
`wrap: none` plus an enclosing `region`, and whether a tag inside a draw-command stream
can reach a view at all, given that the stream is built before any provider can act.

## Session Log

To be written at the end of the implementation session, per the rules in [README.md](README.md).

A review session preceded it.
It measured what is in *Ground Truth*, rewrote this file,
and left the implementation untouched.
