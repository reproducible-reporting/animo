<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Animo Design Document

Animo is a proof-of-concept presentation package for typst (0.15.1 or newer),
drawing inspiration from `slipst` and `sanor`.

Its distinguishing idea: **content and animation are separated**.
The slide body declares *what* is on the slide, tags the interesting parts, and marks the
areas that are allowed to be relaid out.
The animation argument declares *when and how* those parts move, appear, disappear, change
style and change content.
Anything that typst can lay out as content can be tagged, including parts of equations,
cetz `content()` elements and fletcher nodes; raw cetz draw commands can be tagged too, but
only for the structural primitives (see *Tags*).

The separation is deliberately *not* "all content in the body, all verbs in the animation".
Content that exists only from a certain step onwards (the replacement text of a bullet, the
second version of an equation) lives in the animation argument, next to the step that
introduces it. The rule is:

- the **body** declares the slide's skeleton: its static layout, the tag sites, and the
  areas where layout may change;
- the **animation** declares the timeline, including the time-dependent content and styling
  of the tag sites.

## Initial Design

The initial version has the following (non)features:

- Showing, hiding, moving and scaling elements
- Replacing, removing and restyling tagged content, with **real reflow** of the surrounding
  typst content inside a bounded area (a *region*)
- Separation between content and animation
  - Animations reference tagged content in the body of the slide.
  - Anything laid out as content can be tagged: parts of equations, cetz `content()` elements,
    fletcher nodes; raw cetz draw commands for structural primitives only.
- Slipshow-like animations: a slide is a **viewport** onto a **canvas** that may be larger than
  it, and `pan` moves the viewport over the canvas
- No overflow of content to a next slide. Whatever falls outside the viewport is clipped, and it
  is the canvas that `pan` brings into view, not a next page.
- Background color and background image support
- Zero templating or styling features
- No footer or header support, just use `#place` and wrap `#slide` to implement recurring elements
- Extra handout snapshots with `sub(handout: true)`
- Output formats:
  - HTML presentation export suitable for presenting in a browser, with animation features
  - Presentation PDF export suitable for presenting when HTML presentation is not supported at the venue.
  - Handout PDF export suitable for printing and distributing to the audience.
  - SVG export of handouts for later embedding in other documents.

Example usage:

```typst
#import "@preview/animo:0.1.0": *

#slide(
  background: blue,
  // `numbered` decides whether this slide is counted by the slide counter.
  // It says nothing about whether or how a number is shown; that is the
  // author's job, with `#place` and a wrapper around `#slide`.
  numbered: true,
  animation: {
    /*
      Animation logic:
      - The primitives are imported *inside* this block, so they do not shadow
        the typst built-ins `move`, `scale` and `hide` in the slide body.
      - Each call to `sub` creates a subslide; the block joins them into a list.
      - The state before the first `sub` is a subslide of its own: it is the
        slide exactly as the body declares it.
    */
    import anim: *
    sub(
      hide("line1"),
      reveal("line3"),
    )
    sub(
      move("line1", x: 0.5cm, y: 0.5cm),
      scale("line3", 2),
      pan(x: 0.5cm, y: 0.5cm, relto: "line1"),
    )
    sub(
      reveal("line2"),
    )
    /*
      Structural steps: these change what typst has to lay out, so the enclosing
      region is relaid out and redrawn as a whole. Everything outside the region
      is unaffected, down to the pixel.
    */
    sub(
      replace("claim")[Actually the opposite holds, and this replacement is long
        enough to wrap onto a second line, which pushes the rest of the region down.],
      apply("caveat", text.with(fill: red)),
    )
    /*
      `handout: true` asks for an extra handout page at this step. The handout
      otherwise shows only the final state of the slide, which would lose the
      caveat that the next step removes.
    */
    sub(
      handout: true,
      remove("caveat"),
    )
  },
)[
  /*
    Slide content:
    - Anything laid out as content can be tagged, including parts of figures,
      equations, etc.
    - Tags are referenced in the animation logic.
  */
  = Headings are optional

  #tag("line1")[Something that starts out visible]

  #tag("line2", hidden: true)[Something that is initially hidden, but already
    occupies its space on the slide]

  #tag("line3", hidden: true)[Something else that is initially hidden]

  #region[
    #tag("claim")[A short claim.]
    #tag("caveat")[With a caveat.]

    This paragraph moves down when the claim above it grows, and moves back up
    when the caveat is removed. The region as a whole keeps the same footprint
    on the slide, so nothing outside it ever shifts.
  ]
]
```

### Slides

`slide(body, animation: (), canvas: auto, background: none, numbered: true, ..)`

- `animation` is the timeline, a code block of `sub(..)` calls (see *Animation primitives*).
- `background` takes a colour or an image, emitted as CSS in the HTML target and as a page fill
  in the paged ones, since `set page(..)` is unavailable in HTML (see *Findings*).
- `numbered` decides only whether the slide is **counted** by the slide counter — a title or
  section slide is typically `numbered: false`. It does not decide whether or how a number is
  *shown*: there is no header or footer machinery, so displaying a number is the author's job,
  with `#place` and a wrapper around `#slide`. How a shown number is obtained at all is an
  *Open Question*.
- `canvas` is the next section.

Beyond these, `#slide` has no templating or styling parameters by design.

### Canvas and viewport

A slide has two rectangles, and keeping them apart is what makes panning mean anything.

- The **viewport** is what the audience sees: one HTML slide container, one presentation-PDF
  page, one handout page. Its size is the deck's slide size.

- The **canvas** is what the body is laid out on. It is at least as large as the viewport and
  may be larger. Content that falls outside the *viewport* is clipped, not carried over to a
  next slide; `pan` is what brings the rest of the canvas into view.

- `canvas: auto` (the default) sizes the canvas to the content: the union of the body's
  in-flow extent and the extent of each `#place`d element, clamped to at least the viewport.
  A slide that places nothing outside the viewport therefore has canvas = viewport, and
  nothing about the ordinary case changes.

- `canvas: (width: .., height: ..)` states it explicitly, which is also the escape hatch when
  the automatic extent is wrong.

- The canvas origin is the body's origin. The viewport starts at `(0pt, 0pt)` in state 0, so a
  slide with no `pan` is indistinguishable from one with no canvas at all.

The automatic size cannot come from typst's own `auto` sizing, because `#place` is out of flow
and contributes nothing to it — measured, see *Findings*. It also cannot come from position
introspection, which is dead in the HTML target. What does work, and is what animo uses, is a
`show place:` rule over the body: it fires for every placement and exposes `dx`, `dy`,
`alignment` and a measurable `body`, so the union can be computed from content alone and comes
out the same in both targets. Its known limit — a `place` nested inside another container
resolves against that container, and the rule cannot tell the difference — is an *Open
Question*, and `canvas:` is the answer when it bites.

### Tags

`tag(name, body, hidden: false, removed: false, wrap: auto)` marks content for
animation.

- The same tag name may be used in **several places within one slide**. The animation
  primitives then address all of them together, as if they were one element.
- The same tag name may also be used in **different slides without interfering**: tags
  are scoped to the slide they appear in (see *Scoping* below).
- `hidden: true` means the element is invisible on the first subslide, but **still occupies
  its space**. It is the initial-state counterpart of `hide`.
- `removed: true` means the element is not laid out at all on the first subslide, so it
  contributes nothing to the layout of the epoch. It is the initial-state counterpart of
  `remove`, and only differs from `hidden` inside an *explicit* region: in an implicit one the
  footprint is the maximum over the tag's states either way, so the space is reserved
  regardless. `reset(name)` brings it in, with reflow.
- `wrap` decides what container the tag site becomes.

A tag **always** wraps, unless `wrap: none` says otherwise.
The decision is a property of the body alone and never of the timeline,
so that adding an animation step cannot reflow a paragraph,
and so that the four outputs and all of a slide's states lay out the same.

| `wrap`     | Wrapper                                                                     |
| ---------- | --------------------------------------------------------------------------- |
| `auto`     | `box` for an inline body, `block(width: 100%)` for a block-level one        |
| `box`      | `box`, the hugging wrapper                                                  |
| `block`    | `block(width: 100%)`, since a hugging block loses the container's alignment |
| `none`     | no wrapper and no label, the body is returned untouched                     |
| a function | the function builds the inner slot, animo matches the outer one to it       |

`auto` decides by **measuring** whether the body breaks the line it is put in,
not by inspecting what kind of element it is:
inspection cannot see into a `context` block, and the measurement can (see *Findings*).
The axis it decides is hugging versus filling rather than inline versus block,
because a `box` and a `block` render identically for content that already sits between
paragraph breaks, while a wrapper at `width: auto` left-aligns anything the container was
centring, such as a `figure` or a block equation (measured; see *Findings*).

A function is accepted so that the inner slot can carry ink of its own,
`box.with(inset: 4pt, stroke: red)` for instance, which then moves and scales with the element.
Animo requires the result to be a `box` or a `block` and panics naming the tag otherwise,
because nothing else becomes an addressable group.

`wrap: none` is for a body that is not content at all,
such as a stream of raw cetz draw commands, which a box would destroy.
It is also the way to say "this tag is only ever addressed structurally":
with no label there is no group, so the continuous primitives have nothing to animate,
and animo panics when the timeline asks for one anyway.

Wrapping is not free, and the manual has to say so rather than let an author find out:
a tagged inline phrase can no longer break across lines, so its paragraph may reflow,
and a tagged heading shifts by a few points, because a heading's own block spacing is trimmed
at the wrapper's edge and replaced by the generic one (measured; see *Findings*).
Tagging the heading's text instead, `= #tag("t")[Head]`, avoids the shift.

The wrapping is not cosmetic in the other direction either: only labelled `box` and `block`
elements become addressable groups in the SVG/HTML output (see *Findings*). That is what decides
which primitives a tag site supports, and it is worth stating as a table rather than leaving it
implied:

| Tag site                                    | Structural primitives | Continuous primitives |
| ------------------------------------------- | --------------------- | --------------------- |
| ordinary content                            | yes                   | yes                   |
| inside math                                 | yes                   | yes                   |
| a cetz `content()` element or fletcher node | yes                   | yes                   |
| raw cetz draw commands (`wrap: none`)       | unverified            | no                    |

The asymmetry has one cause. Structural primitives are resolved by typst when the epoch is
rendered, so they work wherever a tag can wrap something at all — which is the parity with
`sanor`, whose `test/draw.typ` applies wrappers to a tagged `draw.grid(..)` in exactly this way.
Continuous primitives are resolved by the browser and need a `<g data-typst-label>` to address,
which typst emits only for labelled boxes and blocks. So `apply`, `replace`, `remove` and
`reset` reach a cetz `grid`; `move`, `scale`, `reveal` and `hide` do not.

The last row says *unverified* rather than *yes* because that parity is doubtful:
a cetz draw-command stream is built eagerly, before any show rule or `context` can act on it,
so a tag inside one cannot resolve its content for the current epoch the way a content tag does.
`sanor` reaches it by threading its `s` through the slide body, which this design rejects
elsewhere. Phase 10 settles what is possible there.

### Regions

A region is a **bounded area of the slide whose interior may be relaid out between
subslides**. It is the unit of reflow and the unit of redrawing.

```typst
#region[
  Some content
  #tag("name")[tagged content]
  Some more content
]
```

`region(body, width: auto, height: auto, align: top + left, clip: auto, name: none)`

- **Fixed footprint.** The region occupies the same rectangle on the slide in *every*
  subslide: by default the smallest box that fits every state the region actually takes on
  along the timeline. Explicit `width`/`height` override this; `clip` (default: on when a
  size is given) clips states that do not fit.
- **Reflow is contained.** Inside the footprint, typst lays the content out afresh for each
  state, so replaced, removed and restyled content genuinely reflows: line breaks change,
  following paragraphs shift. Outside the footprint, nothing moves.
- **Regions nest.** An inner region is itself a fixed footprint, so an outer region's layout
  does not depend on the inner region's state. Footprints compose; states do not multiply
  (see *States and epochs* for why this matters to the cost).
- **A tag that is not inside an explicit region is its own region**, i.e. `#tag("x")[c]`
  behaves as `#region[#tag("x")[c]]`, with an anonymous region so that the tag name stays
  unambiguous. Two words are used throughout for the two cases: an **explicit region** is one
  the author wrote, an **implicit region** is the one a bare tag gets. Every tag is inside
  exactly one region, so "outside a region" never means "in no region" in this document.
  Structural changes to such a tag reflow within the tag's own box and nothing else: a replacement is laid out in the largest box any of its
  states needs, which is the closest thing to "just swap this element" that keeps the rest of
  the slide still.
- `name` makes the region itself addressable, so the *region* can be moved, scaled, hidden or
  revealed like any tag. An unnamed region is invisible to the animation.
- A region is **block-level**, and is always a `block(width: 100%, ..)`, so no detection is
  needed: unlike a tag, a region knows what container it has to be. It does **not** reuse a
  `box` or a `block` that its body happens to be already. Reuse would save nothing, since two
  nested `block(width: 100%)` render identically to one (measured), and it would cost the
  region control over `width`, `height`, `clip` and `align`, which it would then have to merge
  into the author's element by rebuilding it from `fields()`, losing whatever a `set` rule
  contributed.
- **Why block-level**, since the reason is not the one the word suggests. It is not that the
  surroundings have to stay still: a box whose footprint is fixed at the maximum over its
  epochs holds its paragraph as still as a block holds its flow, because constant size means
  constant line breaking. It is that a region at `width: auto` has to know its container's
  width, and `layout(size => ..)` is the only way to learn it, and `layout` is block-level: it
  breaks the line it is put in (measured). Inline, the best available is an unbounded
  `measure`, which reports the natural width of content that never got the chance to wrap. A
  box itself wraps correctly once it has a width, so what is missing inside a paragraph is the
  width, not the box. An explicitly sized region could therefore be a box; 0.1.0 does not offer
  one, because the inline case already exists as the implicit region around a bare tag.
- That implicit region inherits the same limit: its footprint can only come from unbounded
  measurements, so content replaced at an *inline* tag site cannot wrap, it can only run on.
  Inline tag sites are for short content, and the manual says so.

Why a fixed footprint, rather than letting the slide reflow around a growing region? Three
reasons, in decreasing order of importance:

1. It keeps the continuous primitives composable with the structural ones. An element that
   has been moved 2 cm keeps its meaning across a content change, because its base position
   did not change. If the whole slide reflowed, every `move`, `scale` and `pan` in flight
   would jump at the same moment.
1. It makes the HTML transition honest and cheap: the redrawn slide is pixel-identical
   outside the region, so the crossfade is invisible there (measured; see *Findings*).
1. It keeps the HTML and paged outputs laying out identically, which is the invariant that
   lets one source produce all four outputs.

The price is real and should be stated plainly: a region reserves room for its largest state,
so a slide whose first state is short and whose last state is tall shows a gap at the start.
The remedies are authorial (choose `align`, split into several regions, give explicit sizes),
and the alternative semantics — a region that pushes its surroundings around — is deferred,
not impossible (see *Potential Future Features*).

**Where regions cannot go.** `region` needs ordinary content, so it does not work inside a
cetz canvas (which consumes draw commands, not content) and is awkward inside math. In those
places, use a bare tag: the implicit-region rule above gives it a fixed footprint of its own,
and `replace` on a tag inside math or inside a cetz `content` element still works. A
`wrap: none` tag has no box to bound, so the region that bounds it is the one *around* the cetz
canvas: `#region[#cetz.canvas(..)]`, with unwrapped tags inside it. A structural change then
redraws the whole figure, which is the price of a construct that is not content.

### Animation primitives

All primitives return a plain description (a dictionary); they perform no action themselves.
`sub(..ops)` groups the operations that happen together in one subslide step. An empty `sub()`
advances one step without changing anything.

`sub` takes one keyword argument of its own: `sub(handout: true, ..ops)` asks for an extra
handout page at that step, on top of the final state that every slide contributes. It is a
keyword rather than a free-standing `handout()` call between `sub` calls, so that its meaning
does not depend on its position in the block — the same reasoning that puts the future `wait:`
on `sub`, and one fewer name at the top level.

The primitives are cut two ways, and both cuts matter.

The first cut is **what they address**. *Element primitives* take a tag name and act on the
tagged content. *Slide primitives* take no tag and act on the slide as a whole — today only
`pan`, which moves the viewport over the canvas; later also `audio` (see *Potential Future
Features*). Slide primitives touch neither tags, regions, epochs nor footprints, which is why
adding one is cheap.

The second cut is **how they are realised**, and it runs through the whole implementation.

**Continuous primitives** change only how already-rendered content is *displayed*. In HTML
they are pure CSS on the existing frame, so they animate smoothly and cost nothing extra.

| Primitive             | Meaning                                                            |
| --------------------- | ------------------------------------------------------------------ |
| `reveal(tag)`         | make the element visible (fades in, in HTML)                       |
| `hide(tag)`           | make the element invisible, keeping its space (fades out, in HTML) |
| `move(tag, x:, y:)`   | translate the element                                              |
| `scale(tag, factor)`  | scale the element about its own centre                             |
| `pan(x:, y:, relto:)` | move the viewport over the canvas, optionally relative to a tag    |

The first four are element primitives; `pan` is the slide primitive, which is why it takes no
tag name and why `relto` — "pan so that this tag comes into view" — is optional rather than
positional.

**Structural primitives** change what typst has to lay out or paint. Only typst can render
the result, so each of them forces a fresh rendering of the slide (an *epoch*, below) and is
transitioned by a crossfade rather than by motion.

| Primitive            | Meaning                                                                 |
| -------------------- | ----------------------------------------------------------------------- |
| `replace(tag, body)` | substitute new content at the tag site, with reflow inside the region   |
| `remove(tag)`        | drop the content and free its space, with reflow inside the region      |
| `apply(tag, ..fns)`  | wrap the content in the given content-to-content functions; accumulates |
| `reset(tag)`         | back to the body's own content, with all applied wrappers dropped       |

Notes and consequences:

- `apply` takes **functions only**, e.g. `apply("x", text.with(fill: red))` or
  `apply("x", emph, text.with(size: 1.2em))`, applied outermost-last. Named style properties
  in the style of `sanor`'s `case(fill: red)` are deliberately not supported: animo does not
  inspect content, so it cannot know which `set` rule a bare property belongs to. Wrapping
  with `text.with(..)`, `box.with(..)` or a lambda says it explicitly.
- `apply` is structural even when the wrapper cannot possibly reflow (a colour change).
  The reason is not reflow but rendering: typst's styling is not expressible in CSS in
  general. The cheap CSS-only special case is recorded under *Potential Future Features* as
  `recolor`.
- **Inserting** content that is not in the body is `replace` on an empty tag:
  `#tag("slot")[]` in the body, `replace("slot")[..]` in the timeline. Content that *is* in
  the body but should start out absent uses `#tag(.., removed: true)` plus `reset`.
- `remove` versus `hide`: `hide` keeps the space and is smooth; `remove` frees the space and
  reflows. This restores the "occupies no space" state that the first draft dropped, now that
  regions give it a bounded meaning. Outside a region there is nothing for `remove` to reflow —
  the implicit region reserves the footprint of the element's largest state either way — so
  there it costs an epoch and buys nothing, and `hide` is the right primitive.
- Structural primitives work at any tag site, including a `draw: true` tag over raw cetz draw
  commands, because typst renders the epoch. Continuous primitives need a labelled group and so
  need a boxed tag site. See the table under *Tags*.
- Because `replace` and `apply` carry content and functions, plan descriptors are no longer
  pure data in the strict sense. Tier-1 tests should therefore assert on the *resolved
  structure* (tag names, per-state flags, epoch boundaries and counts) rather than on the
  payloads, which do not compare usefully.

### States and epochs

This is the execution model that ties the two classes together.

- A slide with *S* `sub` calls has **S+1 states**, numbered 0 to S. State 0 is the slide
  exactly as the body declares it; state *i* is state *i-1* with the operations of the *i*-th
  `sub` applied. Continuous operations accumulate as display state; structural operations
  accumulate as content state.
- An **epoch** is a maximal run of consecutive states with the same *content* state. A new
  epoch starts at every state whose `sub` contains at least one structural operation. A slide
  with no structural operations has exactly one epoch, which is the design of the first draft
  unchanged.
- The content state of an epoch fixes, for every tag: its content (body, replacement, or
  nothing) and its accumulated wrappers. That is all typst needs to render the epoch.
- A region's content depends only on the *content* state, so its unit of measurement is the
  **epoch**, not the state. Each region measures **only the epochs the slide actually has**,
  not the cartesian product of its tags' possibilities, and consecutive states within one epoch
  cost it nothing. Because nested regions have fixed footprints, the measurements of an outer
  region are independent of its inner regions' content. Cost is therefore linear in the number
  of epochs, per region. (This document says *per epoch* everywhere for this measurement; the
  word *state* is reserved for the S+1 subslide steps.)

**How a region measures one epoch.** Not by substitution: a region receives its body as opaque
content and cannot rewrite the tags nested inside it. Instead the current epoch is itself a
state variable, and the region measures by laying its own body out once per epoch with that
variable set accordingly, each tag resolving its own content for the epoch as it is laid out.

This is worth stating explicitly, because it is load-bearing twice over. It is what makes reflow
inside a region possible at all without turning the body into a function of the epoch — the
`s => ([body], s)` threading that *Resolved Design Decisions* rejects. And it is **indifferent to
where time-dependent content is written**: a tag could resolve its content for the epoch from the
plan or from its own arguments equally well. So the question of where `replace`'s content belongs
is not a feasibility question, and is settled on other grounds below.

Renderings required per slide:

| Output            | Renderings                             |
| ----------------- | -------------------------------------- |
| HTML presentation | one per epoch                          |
| Presentation PDF  | one per state (S+1)                    |
| Handout PDF/SVG   | one, plus one per `sub(handout: true)` |

### Architecture

The same tagged content feeds four outputs:

**HTML presentation.** Each epoch of a slide is rendered as *one* `html.frame`, i.e. one
inline SVG, laid out on the canvas. The epoch frames of a slide are stacked on top of each
other in a single grid cell of the canvas element, in document order. The canvas element sits
inside the viewport element, which is the slide's visible box and clips it (`overflow: hidden`).
Each tagged element appears in every frame as a `<g data-typst-label="...">` group. Animations
are then performed in the browser:

- `reveal`/`hide` animate `opacity` on the tag's inner group
- `move` animates the CSS `translate` property
- `scale` animates the CSS `scale` property, with `transform-box: fill-box`
- `pan` animates `translate` on the canvas element inside the clipping viewport
- structural steps crossfade the changed **region**: the region's labelled group fades out in
  the outgoing frame and in in the incoming one, with `mix-blend-mode: plus-lighter` on an
  isolated stacking context

Five rules make this work:

1. Continuous state is applied to **all** epoch frames of the slide at once, not only the
   active one. Entering an epoch therefore never needs re-initialisation, and a subslide that
   is both structural and continuous (a `replace` together with a `move`) animates in lockstep
   in the outgoing and the incoming frame, so the composite reads correctly. Operations on a
   tag that is absent from an epoch are no-ops in that frame.
1. **The crossfade is scoped to the regions whose content state changed**, not to the whole
   frame. Outside those regions the two frames are pixel-identical by the fixed-footprint
   invariant, and a typst frame paints nothing where it has no ink, so the incoming frame can
   simply sit opaque on top of the outgoing one there. Only the changed regions' labelled groups
   are animated, and `plus-lighter` between them makes the sum exact, so nothing dips during the
   transition. This makes the containment claim true *by construction* rather than to within a
   measured tolerance. The whole-frame crossfade — the two frames stacked and cross-faded with
   `plus-lighter`, measured at 1/255 deviation outside the region versus 62/255 for a plain
   opacity crossfade — is the verified fallback if the group-level blend does not behave; see
   *Findings*.
1. Animo must emit **only** the individual transform properties (`translate`, `scale`) and
   never the `transform` shorthand, which would clobber typst's own positioning (see
   *Findings*).
1. Continuous state and boundary state get **separate nested slots**. `tag` wraps its body
   twice, in two wrappers of the same kind, so every tag site emits a labelled outer group with
   an unlabelled inner group inside it (see *Findings*). Continuous primitives address the
   inner group (`[data-typst-label="x"] > g`); anything belonging to an epoch *boundary*,
   the region crossfade today and the morph later, addresses the labelled outer group.
   CSS gives each element only one `translate` and one `scale`,
   so the split is what keeps the two classes from clobbering each other.
   The order is not arbitrary: a boundary effect is measured in the frame's own coordinates
   and must sit *above* the continuous transforms rather than inside them,
   or a tag that is being scaled or (later) rotated while its region reflows
   moves by the wrong amount in the wrong direction.
   The morph under *Potential Future Features* works this out.
   Opacity is exempt from the ordering argument, since the two slots simply multiply,
   but it follows the same convention.
1. **`pan` belongs to the canvas element, not to the frames.** It is a slide primitive, so it
   must not be applied per frame: the frames are stacked in the canvas, and moving the canvas
   moves all of them together and keeps the crossfade registered. This is also the one place
   animo touches a transform outside an SVG group, where rule 3's prohibition does not apply —
   though `translate` is used there too, for consistency and to leave `scale` free for a future
   zoom.

Because a frame covers all subslides of its epoch, stepping within an epoch needs no
re-rendering and motion is genuinely smooth. The cost of structural steps is paid in compile
time and page weight, not in interaction.

**Presentation PDF.** One page per state: a snapshot of the *viewport* at that step, clipped
out of the canvas. No motion — `move`, `scale` and `pan` become discrete jumps between pages,
and `replace`, `remove` and `apply` are simply rendered in place. A panned step is therefore a
page showing a different part of the canvas, which is what makes panning survive into the paged
output at all.

**Handout PDF.** One page per slide, showing the **final state of the slide** — the viewport at
its final position, like the presentation PDF. Additional snapshots are requested with
`sub(handout: true, ..)`. This is lossy by construction for slides
that overwrite content: a `replace` destroys what it replaces, and only an explicit
`handout: true` keeps it. Animo cannot warn about this, because typst offers packages no way to
emit a warning; the manual must.

**Handout SVG.** The handout pages, exported as SVG for embedding elsewhere. Multi-page
SVG export requires a page-number template in the output path.

### Scoping

Tags live in the scope of their slide, with no per-slide context object threaded through
the body:

- In the **HTML** output, CSS/JS selection is scoped to the current slide's container, so
  `[data-typst-label="line1"]` in slide 3 cannot affect slide 7. Matching *all* elements
  with the same tag inside one slide is the natural behaviour of such a selector, which is
  exactly the "several places, one tag" requirement, and it is also what applies continuous
  state to every epoch frame of the slide at once.
- In the **paged** outputs, `#slide` resolves its own animation plan before rendering its
  subslides and hands the result to the body, so each tag site sees the plan of the slide it
  sits in.

The plan must be readable in the **HTML** output as well, because regions and implicit regions
need to measure their states while the body is laid out. There is no cycle: the plan is an
argument of `#slide` and does not depend on the body.

The plan is **provided**, not published.
`#slide` installs a show rule over its body,
and every tag emits a marker that the rule replaces with the tag's rendering for the view it is
given: the state index, the epoch, and the resolved display state of that state.
A state variable cannot do this,
because `state.get()` inside `measure(..)` resolves at the enclosing context's location,
so a caller cannot set a state, measure, set it again and measure again,
which is exactly what a region has to do to size its footprint over its epochs.
A show rule does reach inside `measure`, providers nest with the innermost winning,
and the marker's own label does not reach the output (measured; see *Findings*).
A view being an argument rather than a document position also means
that a deck wrapping `#slide` in its own function changes nothing.

Duplicate labels across a document are permitted by typst and cause no error.

### Output mode selection

One source file, one compile per output. The HTML target is detected automatically via
`target()`; the paged modes are selected explicitly, defaulting to `handout`:

```bash
# HTML presentation
typst compile --format html --features html talk.typ talk.html

# Presentation PDF (one page per subslide)
typst compile --input animo=presentation talk.typ talk-presentation.pdf

# Handout PDF (final state per slide) — the default for paged output
typst compile talk.typ talk-handout.pdf

# Handout SVG (one file per page)
typst compile -f svg talk.typ 'talk-{p}.svg'

# Live preview while authoring: typst serves the HTML and reloads the browser itself
typst watch --format html --features html --open talk.typ talk.html
```

## Resolved Design Decisions

These were the open questions of the earlier drafts. They are settled; the evidence is in
*Findings*.

- **Is this feasible in typst?** Yes, for all four outputs. The enabling mechanism is the
  `data-typst-label` attribute, which makes tagged content individually addressable in the
  SVG that `html.frame` produces. Smooth per-element animation in the browser has been
  verified on real typst output.

- **Can content and style change, with reflow?** Yes, but only within a bounded area, and
  only by re-rendering that area. Typst cannot relay out a fragment of an existing SVG, and
  the browser cannot lay out typst content, so the *only* mechanism available is: render the
  slide again for the new content state, and swap the rendering. The region concept exists to
  keep the cost and the visual consequences of that swap bounded. Verified end to end:
  measuring each epoch of a region and forcing the maximum footprint keeps everything outside
  the region pixel-identical between epochs, in the browser as well as on paper.

- **Should the whole slide body be a region?** No. The body stays a plain layout in which
  nothing reflows, and regions are opt-in. If the body were a region, every structural step
  would relay out the whole slide, which would break continuous animations in flight (their
  base geometry would move under them) and make the crossfade visible everywhere. Opting in
  per region also documents the author's intent, which is where the reflow is allowed to
  happen.

- **How are group-like containers and tags related?** They are orthogonal and both are kept.
  A region is the *unit of reflow and redrawing*; a tag is the *addressable handle*. A tag
  not inside an explicit region gets an implicit region of its own, so the simple case needs no extra
  syntax, and `region(name: ..)` covers the case where the container itself must be animated.

- **Is the name `group` right for the container?** No; it is called `region`. `group` collides
  with two neighbouring meanings — cetz's `draw.group` and the SVG `<g>` groups that animo
  itself emits — while the point of the construct is that it is a *bounded area* of the slide.

- **How much structure does `apply` need?** `apply(tag, ..fns)` with content-to-content
  functions only. `sanor`'s richer `case()`/`object()` machinery exists to cache object state
  across steps, which animo does not have: its plan is resolved to per-epoch content states in
  one pass. Named style properties would also require guessing which `set` rule a property
  belongs to, which animo cannot do without inspecting content.

- **Where does time-dependent content live: the timeline or the body?** In the timeline, as
  `replace(tag, body)`. The alternative — declaring several content values at the tag site and
  selecting among them from the timeline, in the style of `sanor`'s named cases — is expressible
  under the measuring mechanism above, so feasibility does not decide it. What decides it is the
  interaction with duplicate tags, and it is sharpest in the case of the future morph:

  - Because every site sharing a tag name receives the **same** replacement content, the sub-tags
    inside it, their multiplicities and their document order match automatically between the
    outgoing and the incoming epoch frame. That is exactly the precondition the morph's pairing
    rule needs. Per-site variants break it: two sites named `eq` could sit at different variants
    in the same epoch, so the two frames could hold structurally different sub-tag sets, and the
    pairing becomes ambiguous in precisely the case morphing exists for.
  - Variants impose an **arity agreement** across same-named sites: every site named `x` must
    offer the variant the timeline asks for. `sanor` enforces its equivalent by panicking in
    `resolve-case`. `replace` has no such failure mode, because it hands the same content to all
    sites by construction.
  - The timeline stays a complete account of every content state. `switch("eq", 2)` says nothing
    without chasing the body.
  - `apply`, `remove` and `reset` cannot move into the body anyway, so variants would split
    time-dependent content across two places rather than unify it.

  The honest argument for the other side, recorded because it is real: with the content in the
  timeline, reading the body alone does not tell you how tall a region will be, since the content
  that determines its footprint is declared elsewhere. That is a legibility cost rather than a
  correctness one, and it is outweighed by the pairing property above.

  If per-site content is ever genuinely wanted, the answer is distinct tag names, not variants.

- **Does the handout show intermediate content?** No, the handout keeps showing the final state
  of each slide, and `sub(handout: true, ..)` opts into extra pages. One page per epoch was
  considered and rejected: it makes the page count of a handout depend on an implementation
  concept (epochs) rather than on an authorial decision, and it silently inflates handouts for
  slides that merely restyle something. The manual must instead be explicit that `replace` and
  `remove` destroy content and that `handout: true` is how it is kept.

  It is a **keyword argument on `sub`**, not a free-standing `handout()` between `sub` calls.
  The same argument settles it as settles `wait:` under *Potential Future Features*: a marker
  whose meaning depends on its position in the block is harder to read and to validate than a
  keyword on the step it belongs to. It also keeps one more name out of the top-level namespace,
  and it means `sub` remains the only thing a timeline block contains, which is what lets `sub`
  validate its own arguments (see the `import *` footgun under *Findings*).

- **Must the syntax become heavier (body as a function)?** No. `sanor` threads a mutable
  context through the body (`s => ([body], s)`) only because it accumulates actions while
  the body is evaluated. Animo passes the plan as an argument instead, so the body stays an
  ordinary content block — even though tags and regions now *read* that plan while the body is
  laid out, which is a `context` read, not a threaded accumulator.

- **Is a context object `c` needed?** No. It provided two things, both obtainable
  otherwise: scoping (handled by the slide container in HTML and by per-slide state in
  paged output) and a namespace for the primitives (handled by the cetz-style
  block-scoped import). Dropping it also keeps `tag` usable in any context, including
  inside `context` blocks and third-party packages.

- **How are primitives named without shadowing the built-ins?** Following cetz, the
  primitives are imported *inside* the animation block (`import anim: *`). The
  import is scoped to that block, so `move`, `scale` and `hide` keep their natural names
  there while remaining the typst built-ins everywhere else — including in the slide body,
  where authors legitimately use `#move`, `#scale` and `#hide`. Note that `region`, `tag` and
  `slide` are body-level names and are imported at the top level as usual.

- **Can the animation logic be placed after the body?** Technically yes (a marker at the
  end of the body, collected by `query`, works), but it costs extra introspection passes
  and makes the plan discovered rather than passed. The animation stays a named argument.
  With regions this is no longer merely a preference: the body's *layout* depends on the plan,
  so the plan must be known before the body is laid out.

- **HTML export: `reveal.js` or custom?** Custom. Animo animates `<g>` nodes inside an
  inline SVG, so reveal.js's DOM-fragment machinery contributes almost nothing while
  imposing its own slide model, CSS cascade and scaling. Panning is not reveal's model
  either; `touying-exporter` reached for impress.js for that reason. `slipst`'s complete
  custom runtime is ~214 lines of TypeScript plus ~68 lines of CSS, so the cost is small.
  Animo should use plain JavaScript, inlined with `read()`, to avoid requiring a node
  toolchain for a package installed from Universe.

- **How large is a slide, and what does `pan` move?** A slide is a viewport onto a canvas that
  is at least as large as it. `pan` moves the viewport; content outside the viewport is clipped
  and never flows to a next slide. The canvas is sized automatically from the content by default
  (`canvas: auto`) and can be stated explicitly. Automatic sizing cannot use typst's own `auto`
  page or block sizing, because `#place` is out of flow and contributes nothing to it, nor
  position introspection, which is dead in HTML; it uses a `show place:` rule over the body,
  which is available in both targets. See *Canvas and viewport* and *Findings*.

- **Is the name appropriate?** `animo` is unused on Typst Universe. The original rationale
  ("a play on animation and typst") does not hold — there is no *typst* in *animo*, unlike
  `kino` or `tanim` — so the name is kept simply because it is short and free, not because
  it encodes anything.

- **Does `tag` default to `box`, or detect block-level bodies?** It detects, and the axis it
  detects on is not the expected one. A `box` and a `block` render identically for content that
  already sits between paragraph breaks; what differs is hugging versus filling, so `wrap: auto`
  chooses between `box` and `block(width: 100%)`. The detection is a measurement, not an
  inspection of element kinds: a zero-sized box on each side of the body, and a comparison of
  heights. Over 31 constructs the separation was exactly 0 pt for every inline case and at least
  12 pt for every block-level one, and it sees through a `context` block, which inspection
  cannot. `wrap:` overrides it and replaces the earlier `block:` and `draw:` arguments.

- **Is the per-slide plan published as a state or passed down through a show rule?** Passed
  down, as a view, through a marker element and a show rule over the slide body. A state cannot
  carry anything that has to vary inside `measure`, which is what a region's footprint
  measurement needs, and no amount of care with document order fixes that. See *Scoping* and
  *Findings*.

- **Is `sub` the right structure?** Yes. A code block of `sub(...)` calls joins into a
  list of steps. It already carries `handout:` and extends cleanly to the future `time:` and
  `wait:` keywords in the same way.
  Dropping `c` makes the primitives free functions returning plain data, which is easier to
  inspect, test and extend than methods on a context object.

- **Testing strategy.** Three tiers, with the weight on the cheapest, under one runner:

  1. typst-level `#assert` on plan resolution (compile only, no export): per-state content and
     display state, epoch boundaries, epoch counts, and the footprint chosen for each region.
     These documents are compiled — footprints come from real `layout` and `measure` calls — but
     nothing is written out and no raster or PDF is produced.
     `slipst` does this inline in `utils.typ`. Because `replace`/`apply` payloads are content
     and functions, assertions target the resolved structure, not the payloads.
  1. Rasterised comparisons of the presentation and handout outputs.
  1. Headless-browser checks of the HTML output. Subslide state must be addressable by URL
     (as in `slipst`'s `#slip-alter` hash) so tests can deep-link, and numeric assertions on
     geometry are more robust than pixel comparison.

  Two invariants are cheap to test in the browser and worth testing directly, because they are
  what the region design rests on:

  - the bounding box of every label *outside* a region is identical in all epoch frames of a
    slide (`getBoundingClientRect` per frame);
  - the rendering is pixel-identical outside the region between epochs, and stays so
    mid-crossfade.

  Both are comparisons *within* one page load, so they need no stored reference images and are
  unaffected by glyph rasterisation changes. Stored image snapshots are brittle across typst
  versions and stay the exception. The runner, the tools and the reference-image policy are
  settled under *Development Infrastructure*; `tytanic` is the ecosystem convention there and
  was rejected only because it cannot see the HTML target at all.

## Open Questions

These need the prototype to answer.

- **Slide and subslide numbering.** The earlier draft offered `#slidenum()` and
  `#subslidenum()` in the body; both have been taken out, because `#subslidenum()` cannot work
  as written. HTML renders one frame per *epoch*, so a frame covering states 3 to 5 has one
  baked-in subslide number, and making it correct would force every `sub` to be its own epoch,
  which destroys the cost model the whole design rests on. `#slidenum()` has no such problem —
  it is a plain counter — but shipping half of the pair is worse than shipping neither, so the
  question is open as a pair. Three ways out, none chosen: leave both out of 0.1.0; ship
  `#slidenum()` only; or find a form in which the subslide number is a runtime value the
  browser substitutes rather than rendered ink. Whatever is chosen must also work for the
  `numbered:` counter and for the overlay under *Potential Future Features*, which is redrawn
  per epoch and therefore has the identical limitation.

- **What does a handout page of a panned slide show?** Today: the viewport at that step, which
  means a slide that pans across a large canvas loses everything the final viewport does not
  cover, unless the author asks for snapshots with `handout: true`. The alternative — a handout
  page that shows the whole canvas, scaled to fit — is attractive for panned decks and wrong for
  ordinary ones, since it would shrink every slide whose canvas happens to be a little larger
  than its viewport. Possibly a `#slide` argument; not decided.

- **How exact is the automatic canvas?** The `show place:` rule fires for *every* placement,
  including one nested inside a `box` or a grid cell, where `dx`/`dy` resolve against that
  container rather than against the canvas — and the rule cannot tell the two apart (measured;
  see *Findings*). So the automatic union is exact for top-level placements and approximate
  below that. Whether that is good enough in real decks, or whether animo should count only
  placements it can attribute to the slide body, is for the prototype. An explicit
  `canvas: (width: .., height: ..)` is the escape hatch either way.

- Whether the region-scoped crossfade blends correctly: `mix-blend-mode: plus-lighter` on two
  labelled `<g>` elements in two different inline SVGs, inside one isolated stacking context,
  is not yet measured. The whole-frame crossfade is measured and is the fallback.

- Whether a `wrap: none` tag over raw cetz draw commands can be made to work at all, and how it
  should behave when it wraps commands that change the draw *state* (`stroke`, `set-style`)
  rather than emitting geometry. `sanor`'s `test/draw.typ` is the reference case, and it reaches
  the result by threading `s`, which this design rejects. A draw-command stream is built before
  any show rule or `context` can act on it, so a tag inside one may have no way to resolve its
  content for the current epoch. This is why the tag-site table says *unverified* for that row.

- How do CSS-animated typst SVG groups actually *look* in motion: stroke scaling under
  `scale`, text rendering during transforms, and antialiasing seams at subslide boundaries.

- How a crossfade between two epoch frames *reads* when the region's content really reflows.
  Ghosting of two text layouts at once is acceptable for a replacement but may look wrong for
  a small edit in a large paragraph. If it does, the answer is the morph in
  *Potential Future Features*, and the prototype should be built so that the transition
  strategy is swappable.

- Compile-time cost for a realistic deck. Renderings now scale with epochs (HTML) and states
  (presentation PDF), and each region measures once per epoch on top of that. This is the
  expensive part, and it is what makes existing packages slow.

- Page weight of the HTML output with several epochs per slide: every frame carries its own
  glyph `<defs>`. Whether gzip is enough, or whether the shared-defs hoisting under
  *Potential Future Features* is needed.

- Whether the max-footprint rule is tolerable in practice, or whether authors reach for
  explicit sizes so often that a per-region "pin the footprint to state *i*" option is needed.

- Whether `layout(size => ..)` gives regions the right measuring width in every container
  animo cares about (grid cells, `#place`d boxes, columns).

- Whether implicit regions around bare tags behave acceptably inside cetz canvases and math,
  where the surrounding layout is not a flow.

- Whether `pan(relto:)` resolved in the browser (from the group's bounding box) and resolved
  in typst (from element positions, available in paged output) agree closely enough that
  the HTML and PDF presentations look the same.

- Easing and duration defaults, and whether the Web Animations API (paused animations with
  an explicit `currentTime`) is the right driver. It would give reversible stepping and
  correct snap-to-state on deep links, which CSS transitions handle poorly, and it is the
  natural home for the future `time:` parameter. Epoch crossfades must share that clock.
  It is also what makes a mid-crossfade assertion reproducible, because a test can set
  `currentTime` instead of racing a transition.

- Whether a FLIP morph should ever scale. Non-uniform `scale` distorts glyph strokes, so text
  morphs probably want translate-only, with the size change carried by the crossfade, leaving
  scaling for figures. This has to be seen in motion before it is decided; the extra nested box
  under *Findings* is needed either way, since the two slots are separated by coordinate space
  and not merely by how many properties each one uses.

## Potential Future Features

Some ideas:

- Add `time` parameter to animation primitives to control the duration of animations.

- Add a `wait` keyword argument to `sub` for fixed timing between subslides: `sub(wait: 2, ..ops)`
  brings up that subslide 2 seconds after the previous one, instead of on a presenter click.
  Without `wait`, the subslide waits for the presenter, as it does today. Because the argument
  times the *preceding* display, a first `sub(wait: 2)` also times the initial body state, which
  has no `sub` of its own. Keeping this a keyword argument rather than a free-standing `wait()`
  call between `sub` calls avoids a marker whose meaning depends on its position in the block —
  the same reasoning that already put `handout:` on `sub`.
  See the narration entry below for `wait: auto`, which takes its timing from a clip's length
  rather than from a number in the source.

- **Narrated audio, and `wait: auto`.** `audio(path, delay: 0s)` inside a `sub` plays a recorded
  fragment when that subslide is entered. It is HTML-only, and a no-op in all three paged outputs
  — not "ignored with care", but genuinely zero new code there. Like `pan` it is a *slide
  primitive* (see *Animation primitives*), so it touches neither tags, regions, epochs nor
  footprints.

  The `<audio>` element cannot live inside `html.frame`, since `html.elem` is dropped there
  (see *Findings*). `#slide` therefore emits it as a **sibling of the epoch frames**, out of the
  plan it already receives as an argument. That is the same mechanism that puts `replace`'s
  content in the timeline rather than in the body, and it is why `audio` has no body-level form.

  It is written here together with `wait:` because neither alone reaches the goal, which is a deck
  that plays itself with a spoken narrative — so that it reads as a video, and can be recorded as
  one with OBS. That needs `wait:`, and specifically `wait: auto`, "advance when this subslide's
  clip ends". A hand-maintained `wait: 7.3` does not survive re-recording the narration. The clip's
  length is known only to the browser, because typst cannot decode an audio file: measured, a
  data-URI Opus clip reports `duration = 8.0065s` and `readyState = 4` in chromium. So `wait: auto`
  is driven by the `ended` event and is HTML-only, which costs nothing, as `wait:` is HTML-only
  anyway.

  **Audio is the one place where the state model does not hold, and it is better stated than
  discovered.** Everywhere else, state *i* is a pure function of the operations applied up to *i*,
  which is what makes deep links, backward stepping and the paged snapshots fall out for free.
  Playing a sound is an event with a wall-clock extent, and it is not idempotent. The rule that
  contains this: **a clip fires only on a forward transition that is actually triggered**, and any
  playing clip stops on every transition, in either direction. Restoring a state — a deep link, a
  backward step, a reload — is silent. Audio thus sits explicitly outside the state model instead
  of awkwardly inside it. Whether a presenter who steps back wants an explicit "play it again" key
  is left to the prototype; it is additive either way.

  `delay` is **positive only** in a first version, shifting the clip later relative to its subslide.
  A negative delay would have to start a sound before an event whose time is not yet known, which
  is unrealisable under manual clicking, and the effect is available anyway by splitting the step
  in two.

  Embedding is the default, so the HTML stays one self-contained file. That costs a base64 encoder
  written in typst, because typst exposes no base64 to scripts (see *Findings*), at roughly
  **2 s per MB** on a cold compile — about 8 s for twenty minutes of Opus at 24 kbit/s. It is paid
  once rather than per edit, because typst memoises the encoding across recompiles. Referencing
  external files instead of embedding them is a later option, not a requirement.

  `--input animo-audio=off` drops the narration at compile time, so one source serves both an
  autoplaying self-contained deck and a live talk. Dropping rather than muting is what makes the
  live build the cheap one: no encoding, no page weight. And because `<audio>` sits outside the
  frames and has no layout, the switch cannot change a single pixel of the rendered slides.

  Two costs are real but authorial rather than technical: a narrated deck tends to carry less text
  on its slides, which makes its handout lossier; and the base64 stays resident in the DOM, so
  clips want `preload="none"` with prefetch-ahead rather than eager decoding of the whole deck.

- `recolor(tag, color)` as a *continuous* colour change. Verified feasible: a CSS rule on the
  descendants of a labelled group overrides the `fill` presentation attributes that typst emits
  on glyphs and shapes, without `!important`, and `fill` interpolates smoothly under the Web
  Animations API. It would make the most common styling animation free, at the cost of a
  primitive whose semantics are SVG's rather than typst's (fill only, not strokes, not images).

- `once(tag, ..fns)` in the style of `sanor`, applying a wrapper for a single step. Cheap to
  resolve, but it costs two epochs, so it is worth adding only once the epoch machinery is
  proven.

- **Morphing instead of crossfading structural steps.** Both epoch frames are in the DOM and
  laid out, so the runtime can read the bounding box of every label in the outgoing *and* the
  incoming frame and FLIP-animate the ones that exist in both, while crossfading the rest.
  That turns "reflow" from a crossfade into genuine motion, which is the one thing this design
  cannot do today. Measured feasible: a label inside a region reports different, readable
  bounding boxes in the two frames.

  Nothing in the present design precludes it, and it is purely additive — but it is *not* a
  generalisation of `replace` in the sense of carrying content. It is a generalisation of the
  **transition**, and five rules follow from that:

  1. **It must stay purely presentational.** The presentation PDF is one page per state with no
     transitions at all, so the paged outputs have to be able to ignore a morph hint entirely. A
     separate content-carrying `morph(tag, body)` primitive would force every output to
     understand it, for no gain: the author expresses the correspondence by reusing tag names
     inside the replacement, which `replace` already allows.
  1. **Its scope is the region, not the slide.** The fixed-footprint invariant guarantees that
     everything outside the changed region is pixel-identical between epochs, so nothing out there can have
     moved and there is nothing to FLIP. The pairing namespace is therefore *(region, tag name)*
     rather than slide-global, which bounds the runtime cost to the regions whose content state
     actually changed and dissolves the collision between a sub-tag inside a replacement and a
     same-named body tag elsewhere on the slide. A bare tag counts as its own implicit region, so
     a tag whose ink shifts within its fixed footprint still morphs.
  1. **Duplicate tags need a pairing rule.** With *n* groups named `x` in the outgoing frame and
     *m* in the incoming one, pair the first *min(n,m)* in document order within the region and
     crossfade the remainder. Document order is stable and directly available in the DOM. Authors
     who want control use distinct names.
  1. **It needs a transform slot of its own, above the continuous one.** `move` and `scale`
     already own `translate` and `scale` on every epoch frame at once, so the FLIP needs a
     second slot — but *which* of the two nested groups it gets is not a free choice. A FLIP
     delta is read off rendered geometry, i.e. in the frame's coordinates, whereas the inner
     group's coordinates are those of whatever `move` and `scale` have already applied there.
     Put the FLIP inside and a tag under `scale("x", 2)` travels twice the measured delta, which
     is itself twice the layout displacement; a future `rotate` would send it off at the wrong
     angle entirely. So the labelled outer group is the boundary slot and the inner group the
     continuous slot, as *Architecture* rule 4 has it — which is also why that nesting is worth
     doing in the prototype long before the morph exists.
  1. **It pairs on centres, and measures both frames under the same continuous state.** Two
     consequences of the previous rule, both easy to get wrong. Pair on the centre of each
     label's box plus an explicit size ratio, not on `getBoundingClientRect`'s corner and
     extents: `scale` and a future `rotate` act about the element's own centre
     (`transform-box: fill-box`, `transform-origin: center`), so centres are invariant under
     them and cancel between the two frames, while corners and extents are not — a rotated
     element's client rect is the axis-aligned box of the rotated shape and no longer describes
     the element at all. And because one `sub` may carry `replace("eq")` together with
     `move("eq")`, the outgoing and incoming frames must be measured with *identical* continuous
     state applied; measuring the incoming frame after the new `move` and the outgoing one
     before it folds that move into the FLIP delta, and the element then travels it twice.

  The surface is a keyword argument on the structural operation itself:

  ```typst
  sub(replace("eq", transition: morph)[ .. ])
  ```

  A transition is a property of an epoch boundary *within a region*, and the operation's tag is
  what identifies the region, so this is the only placement that says exactly what it means. The
  two alternatives are both worse. On `sub` it would be slide-wide for that boundary, even though
  one `sub` can carry structural operations in several regions, and there would be no answer for
  a step that replaces in one region and removes in another. On `region` it would put a purely
  presentational, HTML-only parameter in the slide body, which the separation rule at the top of
  this document reserves for the slide's skeleton — and a body-level default that three of the
  four outputs ignore is exactly the kind of blurred line a first version should not start with.
  Should two operations on the same region at the same boundary ever disagree, the resolution is
  a panic rather than a precedence rule: it is an authoring mistake, not a composition.

  A slide- or document-level default (`#slide(transition: morph, ..)`) is the natural home for
  "morph everywhere in this deck" and is purely additive to the per-operation form. One API
  choice is deliberately left open: whether `transition:` takes a value from the `anim` module or
  a plain string. Inside the animation block `anim` is star-imported, so a bare `morph` reads
  cleanly there, which is a further small argument for keeping the parameter on the operation.

- **Region reflow that propagates** (`region(spill: true)`), letting a growing region push the
  content below it down. Technically free — the slide is re-rendered per epoch anyway — but it
  invalidates in-flight continuous animations and makes the crossfade visible across the whole
  slide, so it needs the morph above to look right.

- **Hoisting shared glyph `<defs>`** out of the per-slide frames into a single document-level
  `<svg>`. Safe in principle because typst's def ids are content hashes, so equal ids always
  mean equal content and `<use>` resolves document-wide. This would cut the page weight cost of
  multiple epoch frames substantially.

- Add optional overlay content argument to `#slide` that contains no animations but is redrawn
  on every epoch frame. It is intended for content that is not part of the slide body but must
  be present in every epoch frame, e.g. a watermark, a logo, or a slide number. Users should use
  typst's `#place` command for absolute positioning, even if the whole overlay is already
  implemented as a `#place`d box. No `#tag` or `#region` is allowed in the overlay. The overlay
  belongs to the **viewport**, not to the canvas, so it stays put while `pan` moves the slide
  under it — and it does not enter the automatic canvas extent. Being redrawn per epoch rather
  than per state, it inherits the subslide-numbering limitation recorded under *Open Questions*.

- Speaker notes as an optional `notes:` argument to `#slide`. This is orthogonal to the
  rest of the design: for paged output the notes become pdfpc metadata (as in `sanor`'s
  `pdfpc` module), and for HTML they feed a presenter view.

- More complex custom animations, e.g. tagging something with a `time` parameter (floating point number) to render snapshots to be compiled into a single animation. The time axis is still controlled by the `sub` function, but the animation is more complex than just showing, hiding, moving and scaling.

- Add `#slide` options for transitions between top-level slides, e.g. fade, slide, etc.

## Development Infrastructure

Not part of the feature design, but recorded here because much of it is constrained by the design,
and because two parts of it impose requirements back on the package: the live preview needs the
runtime's state to be addressable in the URL, and Universe needs the version number to be correct
in every example.

### Repository layout and manifest

`typst.toml` is the root of everything downstream: the entrypoint, the version,
`compiler = "0.15.1"`, and the `exclude` list that keeps documentation out of the published
archive.

```text
animo/
├── src/          the package itself, entrypoint `src/lib.typ`
├── tests/        pytest: plan assertions, paged rasters, browser checks
├── probes/       one probe per entry in *Findings*
├── examples/     the decks the documentation embeds
├── benchmarks/   compile time and page weight
├── docs/         the Zensical site
├── planning/     design documents, including this one
├── tools/        helper scripts
└── plan.py       the StepUp plan
```

Three rules of the Universe submission guidelines shape this:

- Every example, including the ones in the README, imports `@preview/animo:X.Y.Z` rather than a
  relative path, so that a reader can copy any file and compile it. Keeping those strings correct
  is `snipwise`'s job, below.
- Documentation files are committed to `typst/packages` but excluded from the archive through
  `exclude`. Tests, probes, benchmarks and build scripts are not committed there at all.
- A submission is permanent: publishing `0.1.0` commits to the name and, in practice, to the API.
  That is why the last step of the release path stays manual.

Still to be added before a first release: `.gitignore`, `CHANGELOG.md`, `CONTRIBUTING.md`,
`CITATION.cff` and `.zenodo.json`.

### The working tree as `@preview/animo`

Those Universe-style imports must resolve to the working tree while developing, which a
repository-local package directory arranges without rewriting a single file:

```bash
# once, in the repository
mkdir -p .typst-packages/preview/animo
ln -s ../../.. .typst-packages/preview/animo/0.1.0

# in .envrc
export TYPST_PACKAGE_PATH=.typst-packages
```

Verified: `#import "@preview/animo:0.1.0"` then resolves to the symlinked working tree and picks up
edits immediately. Both alternatives are worse. `slipst` rewrites the imports of its examples with
`sed` in CI, so the file that is tested is not the file that is shipped; and installing into the
user-wide package directory shadows the published `animo` for every other project on the machine.
Tests do not need any of this: they run with the repository as the typst root and import
`/src/lib.typ` by absolute path.

### Live preview

`typst watch` serves the HTML and reloads the browser itself (see *Findings*), so animo ships
nothing for live preview. What it does require is that the runtime keep the current slide and
subslide in `location.hash` and restore from it on load — which the testing strategy wants anyway,
for deep-linking. Two consequences:

- the restore must *snap* to the state rather than animate into it, which is one more argument for
  driving animations through the Web Animations API;
- the hash must be written with `history.replaceState`, or every subslide step leaves a browser
  history entry behind.

Narration audio is silent on a restore by the rule already stated under *Potential Future
Features*. The reload is what makes that rule an everyday case rather than an edge case.

### Testing

One runner, `pytest`, for all three tiers of *Resolved Design Decisions*. `tytanic` is the
ecosystem convention and a good tool: it embeds typst 0.15.1 exactly, its *ephemeral* tests compare
against a reference document compiled in the same run rather than against stored pixels, it sets
`sys.inputs` per test, and its augmented standard library has `assert-panic` and `catch`. But it
compares rasterised pages and has no notion of the HTML target, so it could cover at most the paged
half of the matrix, and two test frameworks side by side cost more than they save.

1. **Plan resolution.** Compile-only documents full of `#assert`, run as subprocesses. The same
   shape covers the `import *` footgun: a document that hands `sub()` something that is not an
   animo operation must fail to compile, with the explanation on stderr.

1. **Paged outputs.** `typst compile -f png --ppi` rasterises the presentation and handout
   directly, so no PDF has to be rendered for a layout assertion, and `--input animo=presentation`
   selects the mode exactly as in ordinary use. Comparison is `numpy` and `Pillow` on decoded
   arrays. The few checks that are about the PDF writer rather than the layout do need the real
   PDF rendered, and use `pypdfium2`: permissively licensed, self-contained wheels, and the same
   engine chromium renders PDFs with. (`stepup.reprep`'s `raster_pdf` is not that tool; it
   rasterises PDF to PDF for flattening, not to arrays.)

1. **HTML.** `playwright` with the browsers it bundles, which keep the pixels identical on every
   machine. Every test of this tier runs in **chromium, firefox and webkit**, parametrised on the
   engine so that a failure names it, because the CSS animo emits has to be the CSS all of them
   agree on and one of them accepting it proves nothing.

   The three are not equally available, so the tier splits them. Chromium and firefox run
   wherever playwright runs and are **required**: a launch failure is a broken bootstrap and an
   error. Playwright builds webkit for ubuntu only, against libraries other distributions do not
   carry, so elsewhere it runs only in a container. Requiring a container of every contributor is
   too much and dropping an engine is too little, so webkit is **best effort locally and required
   in continuous integration**, which is ubuntu. Naming an engine with `--browser` makes it
   required, which is how the workflows ask for all three, so the engine can never be skipped
   everywhere at once and leave the suite green.

   Geometry comes from `page.evaluate`, through `getBBox` and `getScreenCTM` rather than
   `getBoundingClientRect` (see *Findings*), and images from
   `locator.screenshot(animations="disabled")`.

Stored reference images stay the exception, for the cases where a picture is the only statement
that can be made, and are kept as lossless WebP. WebP defaults to lossy, including in
`playwright`'s own `type="webp"`, so a screenshot is taken as PNG and converted with `Pillow`
(`lossless=True`). Comparison always happens on decoded arrays, so the storage format never enters
an assertion.

### Behaviour probes

*Findings* is the load-bearing section of this document: some twenty verified behaviours of typst
0.15.1, any of which could change under the package. Each one becomes a probe under `probes/` — a
small document or browser check that asserts the behaviour itself, rather than a feature test that
merely depends on it. When typst 0.16 lands, the failures then name the finding that broke instead
of the feature that broke. The probes run with the rest of the suite against the pinned typst, and
in a separate non-blocking job against the newest release, which is what turns them into an early
warning rather than a post-mortem.

### Task layer

StepUp drives everything that takes more than one step: the local package symlink, the example
decks to all four outputs, the documentation artefacts, the reference rasters and the benchmarks.
This is deliberate dogfooding. The design requires that "one compile per output" be expressible as
StepUp steps, and building the examples that way tests the claim continuously instead of asserting
it. Verified that it holds today: `stepup.reprep`'s `compile_typst` takes `sysinp` for
`--input animo=presentation`, `resolution` for PNG, a `{p}` destination template for multi-page
SVG, and appends `--features=html` by itself when the destination ends in `.html`.

`pytest`, `pre-commit` and `typst watch` stay directly invocable, so a contributor who only wants
to run the tests or preview a deck never has to learn StepUp.

### Documentation

Zensical, as in the sibling repositories, with the version pinned: it is a `0.0.x` on a near-daily
release cadence, so an unpinned install can break a documentation build with no change in the
repository. The site is built with `--strict`, so a broken link between pages fails CI.

The manual is markdown, not `tidy`. `tidy` is the ecosystem convention — `kino` and `cetz` both use
it — but it renders a typst document, which does not compose with a markdown site, and a static
manual cannot show the one thing animo exists to demonstrate. Instead:

- examples are included from the real `.typ` files with `pymdownx.snippets` and
  `check_paths = true`, so a documented example cannot drift from the file that CI compiles and
  tests;
- every example is published beside the site as an HTML deck and embedded in an `<iframe>`, with
  its presentation and handout PDFs linked next to it, so the reader clicks through a real
  animation instead of looking at a screenshot of one.

### Version numbers

`typst.toml` holds the version and `snipwise` copies it into every place that repeats it: the
`@preview/animo:X.Y.Z` strings in the README, the documentation, the design documents under
`planning/` (including this one) and the examples, and the typst version pin in the workflows, which comes from the manifest's `compiler`
field. A source rule makes the manifest authoritative, and a `regex` target rule rewrites the
version inside an import string with no marker in the file, so the examples stay copy-pasteable:

```toml
[[sources]]
patterns = ["typst.toml"]
scanner = "regex"
regex = '(?m)^version = "(?P<content>[^"]*)"'
snippets = ["version"]

[[targets]]
patterns = ["README.md", "planning/*.md", "docs/**/*.md", "examples/**/*.typ"]
scanner = "regex"
regex = '@preview/animo:(?P<content>[0-9]+\.[0-9]+\.[0-9]+)'
snippets = ["version"]
render = "{{ content | unwrap }}"
```

`snipwise fix` runs as a pre-commit hook and `snipwise check` in CI, so a stale version is a failed
build rather than a review comment on an irreversible pull request. Bumping a release is then:
edit `typst.toml`, run pre-commit. Two limits are worth knowing in advance. The `regex` scanner has
no end marker, so the expression must be anchored and `snipwise check --diff` is worth a look
before the first `fix`. And it copies rather than derives, so anything that is a mapping — the
agreement between the git tag and the manifest version — stays an assertion in the release
workflow.

### Formatting and hygiene

`pre-commit` already carries the generic hooks, `mdformat` and `reuse`. Three more belong here:
`typstyle` (through `typstyle-rs/pre-commit-typstyle`, whose tags track the formatter version;
the hook builds it with cargo), `check-toml` for the manifest, and `check-github-workflows`.

Rendering must be reproducible between a contributor's machine and CI, so tests and examples use
only the fonts typst embeds and compile with `--ignore-system-fonts`. No font files are vendored:
they would collide with the 1 MB limit of `check-added-large-files` for no gain.

### Continuous integration

| Workflow   | Trigger          | Does                                                           |
| ---------- | ---------------- | -------------------------------------------------------------- |
| `pytest`   | push to main, PR | the three tiers and the probes, against the pinned typst       |
| `probes`   | schedule         | the probes against the newest typst release, non-blocking      |
| `zensical` | push to main, PR | builds the site with `--strict`, deploys to Pages on main only |
| `lint`     | push to main, PR | runs the Universe package linter over the package              |
| `release`  | tag `v*`         | builds the publishable subtree, extracts notes, uploads them   |

Typst is installed with `typst-community/setup-typst@v5`, pinned to the version in the manifest.
The package linter runs as `docker run -v .:/data ghcr.io/typst/package-check check`, because its
GitHub Action expects credentials for a GitHub App that a personal repository does not have.

The release workflow stops at the artefact. It builds the directory that would be copied into
`typst/packages` (honouring `exclude`), runs the linter over exactly that, extracts the release
notes from `CHANGELOG.md` and attaches everything to the GitHub release. Copying it into a sparse
checkout of `typst/packages` and opening the pull request stays manual, because the submission
cannot be taken back.

Two things are deliberately left open: whether the non-blocking newest-typst job yields useful
signal or only noise, and whether compiling the documentation examples ever needs a Zensical
module rather than a StepUp step that runs before the site build.

### Benchmarks

Three of the *Open Questions* are numeric: compile time for a realistic deck, page weight with
several epochs per slide, and whether gzip is enough. `benchmarks/` holds a deck that exercises
them and records the numbers, so that the answers are measured rather than guessed, and so that the
regression which would make animo as slow as the packages it means to replace is visible when it
happens.

## Findings

Verified behaviour of typst 0.15.1 that this design relies on. Recorded here so it does not
have to be rediscovered. Checked against the installed `typst 0.15.1` binary and the
v0.15.1 source checkout (`../typst`, commit `9dfd3a085`), with chromium 151, firefox 153 and
playwright's webkit 26.5 for the browser measurements. Where the engines differ, the entry
says so, because a deck that only works in one of them is not a presentation format.
Webkit is measured in a container, for the reason under *Testing*.

### Element identity in the output: `data-typst-label`

This is the keystone of the whole design.

- Labelled content appears in SVG output as `<g data-typst-label="name">`. In all of
  0.15.1 there is exactly **one** emission site, `crates/typst-svg/src/lib.rs:348`, and it
  fires only for `group.label` — that is, only for **labelled `box` and `block`
  elements**. A label on a bare `rect`, or on a text span, emits nothing.
- It works **inside `html.frame`**, which is what makes browser animation possible.
- It works for content inside **math** and inside **cetz** canvases.
- **Duplicate labels are permitted** and each occurrence gets its own group, which is what
  makes "one tag, several elements" work — and what makes one CSS rule reach the same tag in
  every epoch frame of a slide.

Stability: the attribute was added by PR
[#4822 "Animation-friendly export"](https://github.com/typst/typst/pull/4822) (merged
2024-09-03), resolving issue
[#4384](https://github.com/typst/typst/issues/4384), whose stated purpose was
"exposing some way to generate groups with well-known identifiers in SVG export, **which
external tools can pick up**" — precisely this use case. It shipped in **v0.12.0** and is
documented in the 0.12.0 changelog ("Exported SVGs now contain the `data-typst-label`
attribute on groups resulting from labelled boxes and blocks"). It has survived 0.12 →
0.13 → 0.14 → 0.15.1 unchanged, and no open issue proposes changing or removing it. It is
not mentioned in the reference documentation, only in that changelog entry.

The residual risk is not the attribute but its HTML wrapper: HTML export remains behind
`--features html`, warns that "behaviour may change at any time", and its tracking issue
[#5512](https://github.com/typst/typst/issues/5512) gives no stabilisation timeline.
"Frame API for embedded layout-as-SVG" and "Linking to a label, with derived ID" are
already ticked there, but "Share printing code between SVG and HTML export" is not, so the
SVG-inside-HTML emission path may still be refactored.

### The frame is the smallest unit of DOM addressability

This is what forces "re-render the slide, not the region" and therefore the whole epoch model.

- `html.elem` **inside** `html.frame` is dropped, with the warning "elem may not occur inside
  of a paragraph and was ignored". There is no way to give a sub-area of a frame its own DOM
  node, so a region cannot be its own HTML element inside a slide frame.
- `html.frame` inside `html.frame` compiles without error but contributes no second `<svg>`;
  nesting frames is not a route to independently swappable sub-frames either.
- `set page(..)` inside `html.frame` is an error ("page configuration is not allowed inside of
  containers"), so a slide is a sized `block`, not a page, in the HTML target.
- Positions are dead in HTML output (below), so animo cannot place per-region frames itself
  either: it does not know where the region is.

Hence the only mechanism available: render the whole slide once per content state, stack the
frames, and swap them. That is also why the vertical-flow alternative — cutting the slide into
a stack of separate frames the way `slipst` cuts a document into slips — is not usable here:
it only supports content that flows top to bottom, whereas an animo slide is a fixed-size 2D
canvas with `#place`.

### Regions: fixed footprints across epochs

Measured on a region with two epochs, i.e. two content states (a short line and a version long
enough to wrap), with the footprint taken as the per-axis maximum of
`measure(epoch, width: avail)` inside `layout(size => ..)`:

| Check                                                      | Result                                          |
| ---------------------------------------------------------- | ----------------------------------------------- |
| footprint chosen for both epochs (paged)                   | `w=233.88pt h=21.63pt` — identical              |
| y position of the content after the region (paged)         | identical in both epochs                        |
| `data-typst-label` transform after the region (HTML)       | `translate(41.613 40.876)` in both epochs       |
| `getBoundingClientRect` of a label after the region (HTML) | `{x:0.05, y:58.81, w:100.61, h:14.98}` in both  |
| pixel diff between the two epoch frames, full window       | 2958 px, all inside the region's band (y 29–43) |
| pixel diff below the region                                | none                                            |

`measure` internally sets `Target::Paged`
(`crates/typst-library/src/layout/measure.rs`, "let style = TargetElem::target.set(Target::Paged)"),
so a footprint measured in the HTML target is the footprint `html.frame` will produce. This is
what makes one footprint rule serve both targets.

Consequences: `layout` + `measure` per epoch is a sufficient and verified mechanism for
footprints; the region only needs the epochs the slide actually has, so the cost is linear in
epochs rather than combinatorial in tags.

### Crossfading epoch frames

Stacked in one grid cell (`display: grid`, both children in `grid-row: 1 / grid-column: 1`,
`isolation: isolate` on the parent), at the midpoint of a transition with both frames at
`opacity: 0.5`, compared against the single frame at `opacity: 1`:

| Mid-transition blending        | Max deviation outside the region |
| ------------------------------ | -------------------------------- |
| plain `opacity` crossfade      | 62/255 (text visibly washes out) |
| `mix-blend-mode: plus-lighter` | 1/255 (rounding only)            |

So `plus-lighter` is not a nicety, it is what makes the containment claim true *during* the
transition and not only at its endpoints. `slipst` uses the same blend mode for its
whole-slip crossfades.

**The sum is exact in two of the three engines.** Chromium 151 and firefox 153 add the two
half-opacity layers back to one opaque layer bit for bit. Playwright's webkit 26.5 does
not: ten pixels on antialiased glyph edges drift by up to 42/255, measured in a container.
That does not change the choice, because the plain crossfade is worse in kind rather than
in degree: it moves every pixel outside the region, where webkit moves ten of roughly a
million. It does mean the exactness claim is engine-dependent, which the region-scoped
variant below would settle by not relying on a blend at all.

**What is measured here is the whole-frame crossfade.** *Architecture* scopes the crossfade to
the changed regions instead: both frames stay opaque, and only the regions' labelled groups
animate, which makes the containment exact rather than 1/255. That variant needs the same blend
between two `<g>` elements in two different inline SVGs within one isolated stacking context,
and is not yet measured — it is an *Open Question*, with the whole-frame form above as the
verified fallback. The stacking, the grid cell and the isolation are common to both.

### Automatic canvas sizing: `#place` is invisible to `auto`, but visible to a show rule

Measured on 0.15.1, for the canvas rule under *Canvas and viewport*.

- **`#place` contributes nothing to automatic sizing.** With `#set page(width: auto, height: auto, margin: 0pt)` and a body of `#place(dx: 8cm, dy: 4cm)[OUT] in-flow`, the page comes out
  `32.285 x 7.238 pt` — the size of the in-flow text alone. `measure()` agrees: a block with and
  without the same placement measures `32.29pt x 7.24pt` both times. So typst's own `auto`
  machinery cannot size an animo canvas, because an animo slide is a 2D canvas built with
  `#place`.

- **`place` is not locatable**: `query(selector(place))` is a compile error ("place is not
  locatable"), so the placements cannot be discovered by query either.

- **But `show place:` does fire, and exposes everything needed.** A rule
  `#show place: it => { ..; it }` sees every placement and can read `it.dx`, `it.dy`,
  `it.alignment` and `it.body`. Measured on three placements:

  | Source                                  | `dx`            | `dy`           | `alignment`      | `measure(body)`   |
  | --------------------------------------- | --------------- | -------------- | ---------------- | ----------------- |
  | `place(dx: 5cm, dy: 3cm)[OUT]`          | `0% + 141.73pt` | `0% + 85.04pt` | `start`          | `21.97 x 7.24 pt` |
  | `place(bottom + right, dx: 50%)[BR]`    | `50% + 0pt`     | `0% + 0pt`     | `right + bottom` | `12.93 x 7.24 pt` |
  | `place(dx: 1cm)` inside a 4cm x 2cm box | `0% + 28.35pt`  | `0% + 0pt`     | `start`          | `29.21 x 7.24 pt` |

  Ratios stay unresolved (`50% + 0pt`), so they must be resolved against the container inside
  `layout(size => ..)`. This needs neither position introspection nor the paged target, so the
  canvas comes out the same in HTML and on paper — which is the invariant the whole design rests
  on.

- **The limit is the third row.** A placement nested inside another container is reported
  exactly like a top-level one, with offsets relative to *that* container. The rule cannot
  distinguish them, so the automatic union is exact for top-level placements and approximate
  below that. Recorded under *Open Questions*; `canvas:` is the explicit override.

### Recording placements: what a `show place:` rule may and may not do

Measured on 0.15.1 while building the automatic canvas, which needs the placements as
*data* and not merely as content the rule passes through.

- **A show rule cannot return a value, so the numbers travel as introspection.** The rule
  emits a `metadata` element carrying a label beside the placement it sees, and the union
  is taken from `query`. This works **inside `html.frame`** as well: `query` sees into a
  frame even though positions do not exist there, which is what lets one canvas rule serve
  both targets.
- **A block sized from its own `query` converges.** The canvas depends on the layout of
  the very block it sizes: the first pass records nothing and the block comes out at its
  floor, and typst's introspection loop then runs the document again with the placements
  in reach. It terminates because the body is laid out at a width that does not depend on
  the answer. Measured: a block whose width is the maximum of `200pt` and a placement at
  `dx: 400pt` comes out at 419.4pt in the emitted frame.
- **The recording may not disturb the layout it is watching.** A `context` block holding
  nothing but `metadata` is inline and changes no measurement. `layout(size => ..)` is
  block-level and breaks the paragraph the placement sits in: the same body measures
  `76.89pt` tall without it and `103.29pt` with it.
- **That last point closes the one route to telling a nested placement apart.**
  `layout(size => ..)` inside the rule does report the placement's own containing block
  (`400 x 300pt` at top level, `113.39 x 56.69pt` inside a 4 cm box, `200 x 300pt` in a
  grid column), which would make the automatic union exact. It cannot be used, because
  the price is a body that lays out differently from the one the author wrote. So the
  union stays approximate below the top level, as *Open Questions* has it, and the reason
  is not that typst hides the container but that asking for it costs the layout.

### `html.frame` sizes its SVG in `em`, as an inline style

Measured on 0.15.1. `html.frame` writes `width` and `height` on the `<svg>` as an inline
style in `em`, dividing the frame's size in points by the text size in effect: a 200pt
block is `18.181818182em` at the default 11pt text and `9.090909091em` at 22pt.

Two consequences for the HTML shell. An inline style outranks a stylesheet rule, so a deck
that sizes its frames from CSS renders them at the ratio between the page's font size and
typst's text size, which is 16/11 by default and looks like an 8% scaling bug. And the
frame's own size is not a reliable unit for anything, since it moves with a `set text` the
author is free to write. Animo therefore sizes the canvas element itself and overrides the
frame with `width: 100% !important`.

The SVG also carries `overflow: visible`, so ink outside the frame's viewBox is painted
rather than clipped. The viewport element is what clips a slide.

### Fitting the slide to the browser window

Measured in playwright's chromium 151 and firefox 153.

- **`calc()` does not divide a length by a length in firefox.** `calc(100px / 40px)`
  computes to `2.5` in chromium 151 and in playwright's webkit 26.5, which is what CSS
  Values 4 type checking asks for, so firefox is the outlier rather than chromium the
  exception. Firefox 153 does not parse it: `CSS.supports("scale", "calc(100px / 40px)")`
  is false,
  and the declaration it appears in is dropped whole, with nothing on the console.
  A deck whose fit was written that way rendered unscaled in the top-left corner of the
  window in firefox, at roughly half size, with the content beyond the viewport visible
  because the element that clips had nothing left to clip.
  So the fit may not be expressed as one length over another.
- **A length over a number is portable**, and that is what animo emits.
  `--animo-unit` is `calc(var(--animo-viewport) / <slide width in points>)`: one typst
  point, as a CSS length, at whatever size the window currently has.
  Every length animo writes is then that unit times a number computed at compile time,
  and the runtime still never has to measure the window or listen for a resize.
- **Sizing the canvas, rather than scaling it,** is what makes a typst point the unit of
  everything inside it at any window size. This is a change from the first version, which
  scaled the canvas element as a whole, and it is an improvement beyond portability: the
  canvas keeps both its `translate` and its `scale` free, which is what *Architecture*
  rule 5 asks for when it reserves `scale` on that element for a future zoom.
- The two targets then agree to **0.0017 of the slide** on every edge of a placed square,
  comparing a 454-pixel handout raster with a 908-pixel browser screenshot. That is one
  pixel of the coarser raster, which is the floor of the measurement rather than a layout
  difference. Chromium and firefox agree with each other to **0.01 CSS pixel** on the
  canvas box at a 1280 by 720 window.

### SVG `<defs>` ids are content hashes

Relevant because stacking several frames in one document puts duplicate ids in one DOM.

- All deduplicated defs (glyphs, clip paths, gradients, patterns) get ids of the form
  *kind char* + hex of `hash128(key)`, from the `Deduplicator` in
  `crates/typst-svg/src/lib.rs` (`DedupId(char, u128)`).
- Equal ids therefore always mean equal content. Browsers resolve `<use xlink:href="#g..">`
  to the first matching id in the document, which is harmless here, and it is why stacking
  frames does not corrupt glyph rendering.
- It also means the duplication is pure redundancy: hoisting shared defs into one
  document-level `<svg>` would be sound (see *Potential Future Features*).

### CSS animation of typst SVG groups

Measured in chromium on real typst output, on a labelled group that carries typst's own
`transform="translate(0 28.346456693)"`:

| Applied CSS                                                         | Result                                                                          |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `opacity: 0.35`                                                     | works; typst emits no group-level opacity or style, so opacity is entirely free |
| `translate: 50px 0`                                                 | composes — element moves, typst's `transform` attribute stays intact            |
| `transform: translate(50px,0)`                                      | **clobbers** typst's translate (y jumped 49.2 → 8.0, losing the offset)         |
| `scale: 2` (default `transform-box: view-box`)                      | scales about the SVG viewBox origin, displacing the element (y 49.2 → 90.5)     |
| `scale: 2` + `transform-box: fill-box` + `transform-origin: center` | scales about the element's own centre, in place                                 |
| all three together                                                  | compose correctly                                                               |

Mid-flight interpolation, sampled deterministically through the Web Animations API,
confirms genuine smoothness and that typst's own transform survives the animation:

```
t=0.00  x=8.0   w=82.5   opacity=0
t=0.50  x=23.8  w=123.7  opacity=0.5
t=1.00  x=39.5  w=164.9  opacity=1
typst transform attr survived animation: translate(0 28.346456693)
```

Consequences: use the individual `translate`/`scale` properties, never the `transform`
shorthand; set `transform-box: fill-box` for scaling. A stray `transform` in user CSS will
silently break positioning.

Firefox 153 agrees on every row of the table, including that `fill-box` is what makes a
scale happen in place. It resolves the fill box itself slightly differently: the centre it
scales about sits about **0.7 CSS pixels** from the centre `getBBox` reports, so doubling
an 11-pixel line moves it by that much where chromium moves it by under a tenth of a
pixel. That is invisible in a transition, and it is why the probe for this row allows a
pixel rather than half of one.

Units: CSS lengths inside a group are **user units (pt), scaled by the SVG's rendered
size** — 50 user units measured as 72.7 px at the test slide scale. A move expressed in
typst lengths therefore stays the same fraction of the slide at any screen size, for free.

### Styling from CSS: what is and is not reachable

Measured on a labelled group whose glyphs carry typst's `fill="#000000"` presentation
attributes:

- A rule on the group's **descendants** wins without `!important`:
  `[data-typst-label="x"] use { fill: rgb(0,128,0) }` gives a computed fill of
  `rgb(0, 128, 0)`. Any CSS declaration outranks a presentation attribute.
- A rule on the **group itself** does not reach the glyphs: the computed fill stays
  `rgb(0, 0, 0)`, because the glyphs' own presentation attribute beats an inherited value.
- `fill` interpolates smoothly: driving it with a paused Web Animations API animation gives
  `rgb(128, 0, 0)` at the midpoint of a black-to-red transition.

So a colour-only primitive is possible and must target descendants explicitly, but anything
beyond fill (weight, size, spacing, strokes, images) is out of CSS's reach and therefore has
to go through a re-rendered epoch. This is what puts `apply` in the structural class and
`recolor` in the future-features list.

### Cross-frame geometry is readable, so morphing is possible

With two epoch frames in the DOM and both laid out, a label that moves because of reflow
*inside* a region reports both of its geometries to JavaScript: `x=39.49` in the outgoing
frame and `x=523.87` in the incoming one, at identical size. A FLIP-style morph between epochs
is therefore implementable without any help from typst.

Two transform slots are therefore needed, since CSS gives each element only one `translate` and
one `scale`, and nesting supplies the second. `#box(box[Hello world])#label("outer")` emits
`<g transform="translate(..)" data-typst-label="outer"><g>`: the inner group carries **no**
transform of its own. A single `#box[..]` instead emits `<g label><g transform="matrix(..)">`,
whose child is content-dependent and therefore not a slot to rely on. So `tag` wraps its body in
a nested box, which makes `[data-typst-label="x"] > g` a reliable second slot.

**How that geometry is read is not free.** `getBoundingClientRect()` on a labelled group
gives the tight box in chromium 151 and a box inflated to roughly the width of the whole
frame in firefox 153, which paints its ink outside the viewBox because typst writes
`overflow: visible` on the `<svg>`. On the same group chromium reported `19.57 x 13.86`
and firefox `358 x 13.90`. What both engines agree on exactly is `getBBox()`, in the
group's own user units, which are typst points; mapping its corners through
`getScreenCTM()` puts it back in CSS pixels and the two then agree to **0.02 CSS pixels**
on an untransformed group and to **0.7** on one under a CSS scale. So a FLIP morph, and
every test that reads a tag's geometry, uses `getBBox` and the CTM, never
`getBoundingClientRect`.

Which slot takes which class of animation is fixed by the measurement, not by taste: a FLIP delta
is read in the frame's coordinates, so it must be applied above anything that already transforms
the element. The labelled outer group is the boundary slot, the inner group the continuous one
(*Architecture* rule 4). The alternative — leaving both classes on the labelled group and
composing them numerically — also works, but it obliges the runtime to know the current value of
every continuous property in both frames before it can write a FLIP transform, which is state the
stacked-frame design otherwise never has to keep.

### `hide()` cannot be undone in the browser

Typst's `hide()` lays content out but emits **nothing** to draw: the labelled group is
present but empty (0 glyphs versus 9 for the visible equivalent). So CSS can never reveal
it. In the HTML output, initially-hidden elements must be rendered normally and hidden with
CSS `opacity: 0`; only the paged outputs may use `hide()`.

Note the asymmetry with `remove`/`removed:`, which is a *content state*: it is resolved by
typst when the epoch is rendered, so it needs no browser support and cannot be undone within
an epoch — by construction, undoing it starts a new one.

### Introspection: positions

- In **paged** output, positions are available and useful: `query(<tag>)` plus
  `location().position()` returns real coordinates, including for tagged content **inside
  math**. This is how `pan(relto:)` and element geometry are resolved for the PDF outputs.
- In **HTML** output, positions are dead: `here().position()` and
  `location().position()` return `(page: 1, x: 0pt, y: 0pt)` — *even inside `html.frame`*.
  Verified geometrically, by driving a rectangle's width from `here().position().y`: it
  came out zero-width against a 1 cm control. `query` itself does see inside frames.
- `measure()` **does** work in HTML output and returns real sizes, in paged layout (above).

So the HTML output cannot rely on typst coordinates at all; it relies on the browser's own
layout of the frame SVG, which is why per-element animation is done with CSS rather than
with typst-computed offsets, and why regions are sized by `measure` rather than placed by
coordinates.

### Media elements in the HTML output

Measured in chromium on real typst HTML output, for the narration entry under *Potential Future
Features*.

- `html.elem("audio", ..)` works as a **sibling of `html.frame`** inside the slide container. It
  must be wrapped in a block-level element — a `div` with `display: contents` suffices — because
  `audio` is phrasing content and typst otherwise wraps it in a `<p>`.
- A clip embedded as a `data:` URI decodes fully: `readyState = 4` and `duration = 8.0065s` for an
  8 s Opus file, matching the source exactly. So the browser can supply the timing that typst
  cannot.
- **Autoplay of audible media is blocked until a user gesture**: `play()` rejects with
  `NotAllowedError: play() failed because the user didn't interact with the document`. A
  self-playing deck therefore needs one click to start, which a presentation has anyway.
- **Typst exposes no base64 to scripts.** `to_base64_url` exists only on the Rust side, for images
  (`crates/typst-svg/src/image.rs`), so embedding requires an encoder written in typst. Two traps
  in writing one:
  - `while` is capped at 10 000 iterations (`MAX_ITERATIONS`, `crates/typst-eval/src/flow.rs`), so
    the loop must be a `for` over a `range`.
  - The natural implementation, one array element per output character, costs about 119 MB of RSS
    per MB of input. Joining in blocks of a few thousand characters keeps memory flat: 4 MB encoded
    in 8.37 s at 46 MB RSS, i.e. **~2.1 s/MB, linear in size and constant in memory**.
- **The encoding is memoised across recompiles.** Under `typst watch`, a 4 MB payload cost 8.11 s
  on the first compile and 6.6 / 11.2 / 18.8 ms on the next three — including edits that shift
  every span in the file. The cost is per watch session and per cold compile, not per edit, which
  is what makes embedding-by-default tolerable while authoring.

### Live preview: typst serves and reloads the HTML itself

`typst watch` with HTML output starts a small HTTP server and injects a live-reload script into
the response it serves. Verified against the 0.15.1 binary and the checkout
(`crates/typst-kit/src/server.rs`):

- the flags are `--port` (default: the first free port in the range 3000-3005), `--no-serve` and
  `--no-reload`;

- the injected script is a single line, placed before `</body>` of the *served* response only, so
  the file written to disk never contains it:

  ```js
  new EventSource("/__events").addEventListener("reload", () => location.reload())
  ```

- the document is served from memory, and every successful recompile pushes a `reload` event to
  all connected browsers.

Because the reload is a plain `location.reload()`, the URL survives it, fragment included. A deck
whose subslide state lives in `location.hash` therefore comes back on the same subslide after
every recompile. This is what makes the built-in server sufficient for authoring, and it is why
animo ships no reload machinery of its own (see *Development Infrastructure*).

### Wrapping a tag site: what it changes and what it does not

A page was rasterised at 144 ppi with and without a wrapper around one element, at 11 pt text,
and the rasters compared pixel by pixel.

| Tagged body                 | `box(box(x))` | `block(block(x))` | `block(width: 100%)`, twice |
| --------------------------- | ------------- | ----------------- | --------------------------- |
| markup list, grid, table    | identical     | identical         | identical                   |
| a paragraph that wraps      | identical     | identical         | identical                   |
| `figure`, `$ .. $`, `align` | left-aligned  | left-aligned      | identical                   |
| `= Heading`                 | shifts        | shifts            | shifts                      |

For content that already sits between paragraph breaks, a `box` and a `block` render
**identically**. The axis that decides the rendering is not inline versus block but hugging
versus filling: a wrapper at `width: auto` hugs, which left-aligns anything the container was
centring, and `block(width: 100%)` reproduces the original.

A `heading` shifts under *every* wrapper, by about 5 pt. A heading carries its own block spacing
(1.8em above and 0.75em below at level 1, `typst-library/src/model/heading.rs`), that spacing
sits at the wrapper's edge and is trimmed there, and the wrapper contributes the generic 1.2em
instead. Neither `heading.above` nor `block.spacing` is readable from a `context` block, while
`text.size`, `par.spacing` and `heading.numbering` are, so animo cannot copy the value it would
have to restore. Tagging the heading's text rather than the heading is the way around it.

A tagged inline phrase stops breaking across lines, so its paragraph can reflow. That one is
inherent: a group that CSS can translate cannot be split over two lines.

### Inline versus block, decided by measurement

```typ
let nothing = box(width: 0pt, height: 0pt)
let is-block = measure([#nothing#body#nothing]).height > measure(body).height
```

Block-level content pushes the two neighbours onto lines of their own, inline content does not.
Over 31 constructs the separation was **exactly 0.0 pt** for every inline case and **at least
12 pt** for every block-level one, so the comparison needs no tolerance. It needs no available
width either: an unbounded `measure` resolves a `100%` width to zero rather than to infinity, and
every verdict was the same as with a width given.

It sees what inspection cannot. A `context` block reports the block-ness of whatever it
produces. Its one blind spot is content that is itself several paragraphs, which measures as
inline because the neighbours merge into the first and the last paragraph instead of being pushed
off; a scan for a `parbreak` in the body's own sequence covers it.

Inspection was recorded as well, because it is what a reader expects to reach for first:

- a markup list or enum is a **`sequence` of `item`**, not a `list`; `list.item`, `enum.item` and
  `terms.item` all report as `item`;
- `#text(red)[..]` and a `#set` block are both `styled`, with the real element at `.child`;
- `image`, `rect`, `circle`, `line`, `stack`, `grid`, `columns`, `place`, and also `move`, `scale`
  and `layout`, are block-level;
- `box`, `hide`, `footnote`, `metadata`, inline math and inline raw are inline;
- `context` has no fields at all, so inspection stops there.

The set of element functions is closed, because a package cannot define one, but it is only
closed per typst release and it does not cover `context`. That is why animo measures.

### Providing a value down the tree: a show rule reaches into `measure`, a state does not

`state.get()` inside `measure(..)` resolves at the location of the **enclosing** context block,
not at a position inside the measured content. A caller therefore cannot set a state, measure,
set it again and measure again: both measurements see the same value. That rules the state out as
the channel for anything a region varies while it sizes its footprint.

A marker plus a show rule does work:

```typ
#let ask(f) = context [#metadata(f)<animo-ask>]
#let provide(value, body) = {
  show <animo-ask>: it => (it.value)(value)
  body
}
```

Measured: two `measure` calls in one context block, with different values provided, give
different results. Providers nest and the innermost wins. The rule fires on a marker produced
inside a `context` block, and on a marker inside the content that another marker produced, so
tags may be nested. The marker's own label does not leak: a tag built this way emits exactly one
`data-typst-label`, its own.

One thing does not work. A marker that no provider replaced is **not** distinguishable
afterwards: `query(<animo-ask>)` returns replaced and unreplaced markers alike. So "this tag is
outside any slide" has to be diagnosed at the tag site, from a state that `slide` sets around its
body, and not by a sweep at the end of the document.

### Transforms inside a tag's wrappers are layout-neutral

`box(move(dx: .., dy: .., ..))`, `box(scale(.., reflow: false, ..))` and `box(hide(..))` measure
identically to `box(..)`, in width, in height and in their effect on the line around them, even
though `move` and `scale` are themselves block-level elements. The same holds for
`block(width: 100%, move(..))` against `block(width: 100%, ..)`.

This is what lets the presentation PDF apply a state's display state with typst's own elements
without disturbing the layout, and it is what makes "nothing moves between states except what the
timeline moves" an invariant rather than a hope. A tag site emits the same structure in every
state and in both targets; only the parameters inside it change.

### Other verified behaviour

- `target()` returns `"html"` or `"paged"`, which is the clean way to branch. The
  `dictionary(std).at("html", default: none)` idiom in `slipst` is a compatibility hack for
  older typst versions and is not needed here.
- `set page(...)` is **ignored** in HTML export at document level (typst warns) and is an
  error inside `html.frame`. Slide size, background colour and background image must be
  emitted as CSS for the HTML target, and the slide itself is a sized `block`.
- HTML export still requires `--features html` in 0.15.1 and prints an
  "under active development and incomplete" warning.
- `html.elem` takes its attributes as a dictionary in the `attrs:` argument; `html.div(..)`
  and friends do not accept `attrs:`, so animo should use `html.elem` for anything with
  data attributes.
- Multi-page SVG export fails without a page-number template (`{p}`/`{0p}`) in the output
  path.
- A code block joins array-returning calls, so `animation: { sub(..) sub(..) }` yields a
  list of steps with no side effects and no accumulator. An empty `sub()` yields an empty
  step.
- The cetz-style block-scoped import works exactly as hoped: inside
  `{ import anim: * ... }` the primitives win, while `move`, `scale` and `hide`
  outside the block remain the typst built-ins.
- A star import re-exports submodule bindings, so a single
  `#import "@preview/animo:0.1.0": *` provides `slide`, `tag`, `region`, `sub` *and* the
  `anim` module (`anim` reports as a `module`). Three usage forms all work: `import anim: *`
  inside the animation block, a named import (`#import "@preview/animo:0.1.0": sub, tag, anim`), and fully-qualified calls (`anim.reveal("a")`) with no inner import at all.
  Verified with a local two-file module, which resolves identically to a package
  entrypoint.
- **Footgun:** because `import ...: *` silently falls through to the standard library for
  any name the module does not define, a mistyped or unsupported primitive does not error.
  `rotate("b", 45deg)` inside the animation block quietly calls `std.rotate` and returns
  *content*, surfacing later as a confusing "does not have field" error. `sub()` must
  therefore validate that every operation it receives is an animo operation descriptor and
  panic with a clear message otherwise.
- Labels inside math need care: `#box[b] <bb>` with a space is parsed as literal math
  content (it renders as `<bb>`), whereas `#box(body)#label(name)` attaches correctly.
- SVG paints in document order, and `z-index` does not apply to SVG children in shipping
  browsers. Stacking order is therefore fixed at compile time. This is accepted: z-order
  changing animations are out of scope and can be simulated without reordering. Note that
  epoch frames are stacked as *HTML* elements, where the grid and `opacity` do apply.
- `animo` is unused on Typst Universe (`packages/preview/animo` returns 404).

### Consequences of confining reflow to regions

With reflow bounded by regions rather than either forbidden or global:

1. A slide with no structural operations needs exactly **one** `html.frame`, as in the first
   draft. Nothing about the simple case became more expensive.
1. The HTML and paged outputs lay out **identically**, because both reserve space for hidden
   elements and both reserve the same region footprints, measured the same way.
1. Smooth animation remains available for every continuous primitive, since within an epoch
   the frame geometry is frozen exactly as before.
1. The "occupies no space" state that the first draft dropped comes back, in bounded form, as
   `remove` and `removed:`. It was dropped because it reflowed the whole slide; inside a region
   that is precisely what it is supposed to do.
1. What is *not* achieved is animated reflow: content that moves because of reflow jumps to its
   new place behind a crossfade. The morph idea in *Potential Future Features* is the way out,
   and nothing in this design precludes it.

## Comparison with the packages that inspired this

- **`sanor`** separates declaration from animation, as animo does, and its `apply`/`case`
  mechanism is the direct ancestor of animo's `apply`. It also tags raw cetz draw commands
  (`test/draw.typ` tags a `draw.grid(..)` with `hider: draw.hide`), which animo matches with
  `tag(.., draw: true)` for the structural primitives; being PDF-only, `sanor` has no continuous
  class for which the limitation would bite. It is PDF-only, which is what lets it
  restyle and reflow freely: every step is a fresh page anyway. It pays for the separation with
  the `s => ([body], s)` threading, because it accumulates actions while the body is evaluated.
  It also supports what animo decided against: `tag(s, name, body, ..defined-cases)` takes named
  cases at the tag site, and since `make-case` turns a bare content value into a replacing
  wrapper, those cases can carry *content*, selected from the timeline by name
  (`once("gtext", "alert")`). The threading and `object` being a function of the case are what
  pay for it.
- **`slipst`** has HTML export with panning, implemented with a custom runtime (whole-slip
  opacity crossfades with `plus-lighter` plus a `container.style.top` offset for panning). Its
  animation model is coarse — it re-renders a whole frame per "alter" rather than animating
  elements — but that per-alter re-render is exactly the mechanism animo needs for structural
  steps. Animo's contribution is to confine it to a region and to keep per-element animation
  inside each frame.
- **`kino`** targets frame-by-frame animation with an external python driver, which is a
  different goal: it interpolates a timeline into video or reveal.js rather than driving a
  presentation.
- **`touying-exporter`** reaches HTML by packaging per-slide SVGs with impress.js.

Animo's per-element `data-typst-label` approach is what none of them use, and it is what
allows one tagging mechanism to serve smooth HTML animation and paged snapshots alike. The
region concept is what lets it also serve content changes, which per-element animation alone
cannot express.

## Related directories

Siblings of this directory (`..`) that bear on this design.

Reference implementations and prior art:

| Directory   | Relevance                                                                              |
| ----------- | -------------------------------------------------------------------------------------- |
| `../sanor`  | tag/`apply` separation, cases, objects, pdfpc notes; PDF-only                          |
| `../slipst` | HTML export, custom runtime, stacked frames with `plus-lighter`, URL-addressable steps |
| `../kino`   | frame-by-frame animation in pure typst with an external python driver                  |

Upstream sources consulted for the findings:

| Directory             | Relevance                                                                                                                  |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `../typst`            | v0.15.1 checkout; `crates/typst-svg` (label emission, def id hashing) and `crates/typst-library` (`measure`, `html.frame`) |
| `../typst-dev-assets` | assets used by typst's own test suite, handy for rendering tests                                                           |
| `../krilla`           | the PDF writer typst builds on; relevant only if PDF-level features (pdfpc metadata, layers) are ever needed               |

Real decks that constitute the test corpus and the motivation:

| Directory                               | Relevance                                                                                                                                            |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `../2026-talk-fml-stacie/2_talk`        | manim + manim-slides deck that assembles typst snippets: the workflow animo aims to replace, and the best source of realistic animation requirements |
| `../2026-talk-thermodynamics`           | plain typst slides (`workflow/slides.typ`) built with StepUp; realistic input for handout and presentation PDF                                       |
| `../2026-talk-publication-workflows`    | idem, a second deck with a different structure                                                                                                       |
| `../2025-poster-mlp-si-al-distribution` | typst poster; exercises the SVG-embedding output path                                                                                                |

Tooling animo has to fit into:

| Directory                            | Relevance                                                                                                               |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `../stepup-core`, `../stepup-reprep` | the build tool driving those decks and animo's own task layer; `compile_typst` already covers all four outputs          |
| `../templates`, `../bootstrap`       | repository templates where an animo-based talk template would eventually land                                           |
| `../snipwise`                        | keeps text snippets in sync across files; copies the version from `typst.toml` into every `@preview/animo:X.Y.Z` string |
| `../stepup-benchmark`                | precedent for tracking compile time and output size across releases                                                     |
