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
cetz `content()` elements and fletcher nodes; raw cetz draw commands are the one exception,
and are refused at the tag site rather than silently ignored (see *Tags*).

The separation is deliberately *not* "all content in the body, all verbs in the animation".
Content that exists only from a certain subslide onwards (the replacement text of a bullet, the
second version of an equation) lives in the animation argument, next to the subslide that
introduces it. The rule is:

- the **body** declares the slide's skeleton: its static layout, the tag sites, and the
  areas where layout may change;
- the **animation** declares the timeline, including the time-dependent content and styling
  of the tag sites.

## Companion Documents

This document specifies the latest version of Animo:
what a slide declares, what a timeline may do to it,
and why each of those answers was chosen rather than another.
One companion document carries the material that would otherwise overwhelm it.

- [findings.md](findings.md), referred to throughout as *Findings*,
  records the verified behaviour of typst 0.15.1 and of the browsers Animo drives
  that this design rests on.
  Every entry there was expensive to establish and is easily lost again,
  and nearly every one is guarded by a probe under `probes/`.

Any other reference in italics, *Regions* or *Architecture* for instance,
is a section of this document.

Further development is tracked on GitHub as issues and pull requests,
not as a phase plan kept in this repository.

## Initial Design

The initial version has the following (non)features:

- Showing, hiding, moving and scaling elements, where a move is stated either as a position on
  the canvas, possibly relative to another tag, or as a shift from wherever the element is, and a
  scale is either isotropic or per axis
- Replacing, removing and restyling tagged content, with **real reflow** of the surrounding
  typst content inside a bounded area (a *region*)
- Separation between content and animation
  - Animations reference tagged content in the body of the slide.
  - Anything laid out as content can be tagged: parts of equations, cetz `content()` elements,
    fletcher nodes. Raw cetz draw commands are not content and are refused.
- Slipshow-like animations: a slide is a **viewport** onto a **canvas** that may be larger than
  it, and `pan` moves the viewport over the canvas
- No overflow of content to a next slide. Whatever falls outside the viewport is clipped, and it
  is the canvas that `pan` brings into view, not a next page.
- A **background** and an **overlay** per slide, each either a colour or arbitrary content, both
  belonging to the viewport, so a `pan` moves the slide under them
- **Timing**: every primitive may be delayed and given a duration of its own, and the gap before
  a subslide or a slide may run on a timer rather than on a presenter click, written as `wait:`
  on the subslide it brings up or as `hold:` on the subslide it keeps on screen,
  which a reader can stop and start again with `Space`
  and which carries the deck back over the same gaps when the reader steps back
- **Numbering**: a slide number the deck reads with `slide-number()` and `slide-count()`, and a
  number finer than a slide, which is content laid out once per subslide with `per-subslide`
  and chosen by the browser rather than a value baked into a frame
- A **crossfade or a hard cut between slides**, and nothing else between them
- Zero templating or styling features
- Zero HTML and CSS in a deck's source: every setting the runtime reads is an argument of
  the deck's show rule, so an author is never expected to call `html.elem`
- No footer or header support, just use `#place` and wrap `#slide` to implement recurring elements
- Handout pages chosen per subslide with `sub(handout: ..)` and `#slide(handout: ..)`,
  defaulting to the final state
- Output types, which are paged modes rather than file formats:
  - An HTML presentation for presenting in a browser, the only animated one.
  - A static presentation for presenting when a browser is not available at the venue.
  - Static handouts for printing and distributing to the audience.
  - Either static type exports to PDF, SVG or PNG, whichever suits the use.

Example usage:

```typst
#import "@preview/animo:0.1.1": *

#slide(
  background: blue,
  // The overlay is drawn over everything else and belongs to the viewport, so
  // a `pan` moves the slide under it. Same for the background, behind it.
  overlay: place(bottom + right, dx: -1cm, dy: -1cm)[#emph[A talk]],
  // `transition` says how this slide is entered: `auto` is the deck's own
  // strategy, `none` cuts, and a string names a strategy. It is `auto` by
  // default, and `"crossfade"` is the one strategy there is.
  transition: auto,
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
      // `dx`/`dy` shift an element from wherever it is, `x`/`y` put it at a
      // position, by itself on the canvas or with `relto` at another tag.
      move("line1", dx: 0.5cm, dy: 0.5cm),
      // `f` sets the scale factor rather than multiplying into it,
      // `delay` holds an operation back, here by a fifth of a second, and
      // `duration` says how long it then takes.
      scale("line3", f: 2, delay: 0.2, duration: 1.5),
      pan(x: 0.5cm, y: 0.5cm, relto: "line1"),
    )
    // `wait` brings this subslide up two seconds after the previous one came
    // up, instead of on a presenter click. `hold` on the subslide before it says the
    // same thing from the other side, and one gap takes only one of the two.
    sub(
      wait: 2,
      reveal("line2"),
    )
    /*
      Structural operations: these change what typst has to lay out, so the enclosing
      region is relaid out and redrawn as a whole. Everything outside the region
      is unaffected, down to the pixel.
    */
    sub(
      replace("claim")[Actually the opposite holds, and this replacement is long
        enough to wrap onto a second line, which pushes the rest of the region down.],
      apply("caveat", text.with(fill: red)),
    )
    /*
      `handout: true` asks for a handout page at this subslide. The default, `auto`,
      gives a page to the last subslide of the slide and to no other, which here
      would lose the caveat that this subslide removes.
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

  // `line2` and `line3` start out hidden, because the first thing the timeline
  // does to each of them is `reveal`. Both occupy their space from the start.
  #tag("line2")[Something the timeline reveals two seconds in, and that already
    occupies its space on the slide]

  #tag("line3")[Something else the timeline reveals]

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

```typst
slide(body, animation: (), canvas: auto, background: none, overlay: none,
      transition: auto, wait: none, hold: none, handout: auto, numbered: true, ..)
```

- `animation` is the timeline, a code block of `sub(..)` calls (see *Animation primitives*).
- `background` and `overlay` are the section after next.
- `transition` says how this slide is **entered**: `auto` is the deck's own strategy,
  `none` cuts, and a string names a strategy, of which `"crossfade"` is the one that exists and
  is what `auto` means.
  A boundary uses the setting of the slide being entered, in both directions, so
  stepping back over a boundary undoes exactly what stepping forward over it did. The duration
  is the deck's own, `transition-duration:` on the show rule, defaulting to `0.4`, so a deck makes
  every `auto` slide cut by setting it to zero and `prefers-reduced-motion: reduce` does the
  same. HTML only: the paged outputs put the two slides on two pages and there is nothing
  between them.
- `wait` and `hold` are each a number of seconds, or `none` for a presenter click. `wait` is the
  delay before this slide is entered, measured from the moment the previous slide's last state
  came up. `hold` is the delay before the state after this slide's initial one is entered,
  measured from the moment that initial state came up, which on a slide with no `sub` at all is
  the boundary into the next slide. Their subslide counterparts are `sub(wait: ..)` and
  `sub(hold: ..)`, and the rules are the same ones at both levels (see *Timing*). Both are
  written here for the reason `handout` is: a slide's initial state has no `sub` of its own.
- `handout` says whether the handout keeps this slide's **initial state**,
  and takes the same three values as its subslide counterpart `sub(handout: ..)`:
  `auto` keeps that state only when it is also the slide's last one,
  `true` asks for the page, and `false` gives it up.
  The initial state has no `sub` of its own, which is why its flag is written here
  (see *Animation primitives*).
- `numbered` decides only whether the slide is **counted** by the slide counter. A title or
  section slide is typically `numbered: false`. It does not decide whether or how a number is
  *shown*: there is no header or footer machinery, so displaying a number is the author's job,
  with `#place` and a wrapper around `#slide`, or with `overlay`.

A shown number is built from three body-level names, which are the whole of the numbering
surface.

```typst
slide-number()            // the slide's number, or `none` on a slide `numbered: false` left out
slide-count()             // how many slides of the deck carry a number
per-subslide(f, wrap: auto)  // content laid out once per subslide, one of them shown
```

`slide-number()` and `slide-count()` are counter reads and hand back integers, so a deck may
compute with them; both must be called in a context. `slide-number()` is `none` rather than the
number of the slide before it on a slide the counter passed over, so one footer can serve a
deck without special-casing every slide it lands on. Neither is the position that
addresses a slide in the URL, which counts every slide the presenter walks through.

`per-subslide` is a callback rather than a counter, and *States and epochs* says why: an HTML
frame covers a whole run of subslides, so a value chosen when the frame is rendered would be one
value for all of them. The callback is laid out **once per subslide** and receives the
**subslide numbers**, `(number, count, step, steps)`: the subslide's number within its slide and
how many that slide has, then the same pair over the whole deck, so a progress indicator may
span either. Both numbers count from one, where the URL fragment addresses state 0, because the
fragment is an address and the number is what the audience reads on the slide. *Resolved Design
Decisions* records why the deck-wide pair is named for the presenter's steps.
A callback may return `none`, which lays nothing out for that subslide,
and `wrap:` takes `auto`, `box` or `block`, deciding hugging versus
filling exactly as a tag site's does; a rendering that states a ratio needs `block`, since only
a filling container has a width for it to be a ratio of.

The renderings are stacked in a container with the footprint of the largest of them, which is
the rule an implicit region already follows, taken over the states rather than over the epochs.
Each carries a label of Animo's own, the paged outputs lay out the rendering of the page's own
state, and the browser shows the one belonging to the position it is on. So all three output
types agree, and a handout page carries the number of the state it kept rather than of the page
it is.

- `canvas` is the next section.

Beyond these, `#slide` has no templating or styling parameters by design. `background` and
`overlay` are not an exception to that, because neither is a style applied to the body: they are
two more pieces of content, at two fixed depths, and Animo neither positions nor decorates what
goes in them.

### Canvas and viewport

A slide has two rectangles, and `pan` is defined by the difference between them.

- The **viewport** is what the audience sees: one HTML slide container, one presentation-PDF
  page, one handout page. Its size is the deck's slide size.

- The **canvas** is what the body is laid out on. It is at least as large as the viewport and
  may be larger. Content that falls outside the *viewport* is clipped, not carried over to a
  next slide; `pan` is what brings the rest of the canvas into view.

- `canvas: auto` (the default) sizes the canvas to the content of a slide **whose timeline
  pans**: the union of the body's in-flow extent and the extent of each `#place`d element,
  clamped to at least the viewport.
  A slide that places nothing outside the viewport therefore has canvas = viewport, and
  nothing about the ordinary case changes.

- **A slide that never pans takes the viewport, clamped to its body box.** `pan` is the only
  reader of the canvas, and the viewport clips in both targets, so such a slide is drawn the
  same whatever canvas it gets. The union is what costs: it is computed from a `show place:`
  rule, which pays a `context`, a `measure` and a queried element for every `#place` in the
  body. A slide that places thousands of elements therefore pays nothing for a canvas nobody
  can observe. See *Resolved Design Decisions*.

- The body is laid out in a **box** as wide as the viewport's inner width and as tall,
  unless the body's own flow is taller, in which case the box is as tall as the flow.
  It has to be: a fixed-height container stacks the block-level content that does not fit at
  its own bottom edge rather than letting it flow past, measured under *Findings*,
  so a derivation that runs off the viewport would arrive as a pile of overlapping blocks
  instead of as the content a `pan` is meant to reach.
  A `#place` in the body resolves its alignment and its ratios against that box,
  so `place(bottom + right)` is the bottom right of the viewport on an ordinary slide
  and the bottom right of the flow on a slide that runs off it.
  A placement never changes the box, because it contributes nothing to the flow,
  so the automatic canvas still converges.

- `canvas: (width: .., height: ..)` states it explicitly, which is also the escape hatch when
  the automatic extent is wrong.

- The canvas origin is the body's origin. The viewport starts at `(0pt, 0pt)` in state 0, so a
  slide with no `pan` is indistinguishable from one with no canvas at all.

The automatic size cannot come from typst's own `auto` sizing, because `#place` is out of flow
and contributes nothing to it, as measured in *Findings*. It also cannot come from position
introspection, which is dead in the HTML target. What does work, and is what Animo uses, is a
`show place:` rule over the body: it fires for every placement and exposes `dx`, `dy`,
`alignment` and a measurable `body`, so the union can be computed from content alone and comes
out the same in both targets. Its known limit is that a `place` nested inside another container
resolves against that container, and the rule cannot tell the difference,
so the union is approximate and errs in both directions;
`canvas:` is the answer when it bites, and *Open Questions* says how far it is off.

The rule fires once per epoch rather than once per rendering. The states of one epoch share
their content, and a display state puts a `move`, a `scale` and a `hide` around a tag rather
than a `place`, so every rendering of an epoch records the same placements at the same
offsets and at the same size. The recording covers the epochs the output type renders, which
is every epoch in the HTML target and in the presentation, and the epochs a handout keeps a
page of. A rendering that is measured rather than laid out, which is what a region does to
size its footprint, records nothing at all, because a `metadata` element inside a `measure`
never reaches `query`.

### Background and overlay

A slide has three layers, and the author fills the outer two:

1. the **background**, behind everything;
1. the **canvas**, carrying the body, which is what `pan` moves;
1. the **overlay**, in front of everything.

`background` and `overlay` both take either a **colour** or **content**. A colour is emitted as
CSS in the HTML target and as a page fill in the paged ones, since `set page(..)` is unavailable
in HTML (see *Findings*); this is what `background: blue` has always done. Content is laid out in
a box the size of the **viewport**, against which `#place(bottom + right, ..)` resolves its
alignment, and an `image(width: 100%, height: 100%)` fills the slide. A background that wants
both a ground colour and content says so in the content, with a filled `rect` behind the rest.

A gradient and a tiling are refused rather than accepted as a third form, and the message says
to wrap one in a `rect` of the slide size. Typst resolves either against the element it fills,
while CSS would have to be handed an equivalent Animo would have to write itself, and a tiling
has no CSS equivalent at all, so the two targets would agree only by accident. The `rect` is
content, which both targets already draw the same way.

Four rules govern both of them, and they are the same four:

- **They belong to the viewport, not to the canvas.** A `pan` moves the slide under them and
  leaves them where they are, so a logo stays in the same place on screen instead of travelling
  with the canvas. They contribute nothing to the automatic canvas extent either,
  so putting a full-bleed image in the background cannot enlarge the canvas and make the body
  pannable by accident. A background that should pan with the canvas is left for a later
  release. It would be a different construct rather than a flag on this one, because a fill
  and a content background would otherwise behave differently under a `pan`.

- **They hold no `tag` and no `region`,** and Animo refuses either there. They are outside the
  body, so nothing in the timeline could address them, and a tag that resolved to nothing would
  be the silent no-op that *Tags* refuses raw cetz draw commands to avoid. A `per-subslide` is
  not one of those and is served rather than refused: it addresses nothing, the slide renders it
  for itself, and a layer is where it costs the least.

- **They are rendered once per slide in HTML**, not once per epoch, because nothing in them
  can depend on one. Each is one `html.frame` of its own beside the canvas element, so a slide
  with four epoch renderings still carries one background and one overlay. This keeps them
  off the epoch cost curve entirely, and it is why a layer is the cheapest place for a number:
  a `per-subslide` there is one stack of renderings per slide, where the same stack in the body
  is that stack once per epoch.

  What is rendered once is the *layer*, and not necessarily one value per slide. A stack holds
  one rendering per state and lets the browser choose between them, exactly as a tag's own
  display state does, so a layer may carry a subslide number after all. An earlier draft of this
  document concluded the opposite from the same rule, and the inference that does not follow is from
  "rendered once" to "one value".

  In the paged outputs each layer is laid out **once per page** of the slide, under and over the
  panned canvas, which is what a rendering chosen per state requires and what placing it on
  every page already amounted to.

- **They do not clip the body and the body does not clip them.** The viewport clips all three
  layers alike, at its own edge.

### Tags

`tag(name, body, wrap: auto)` marks content for animation.

- The same tag name may be used in **several places within one slide**. The animation
  primitives then address all of them together, as if they were one element.
- The same tag name may also be used in **different slides without interfering**: tags
  are scoped to the slide they appear in (see *Scoping* below).
- **The initial state of a tag is not an argument of `tag`.** It follows from the timeline,
  as the paragraph below says.
- `wrap` decides what container the tag site becomes.

**A tag's initial state is inferred from the timeline.** A tag has two slots that are set
independently, its display state and its content state (see *Animation primitives*),
and each takes its initial value from the first operation that addresses it:

- a name whose first *display* operation is `reveal` **starts hidden**:
  invisible on the first subslide, but still occupying its space;
- a name whose first *content* operation is `reset` **starts removed**:
  not laid out at all on the first subslide, so it contributes nothing to the layout of that
  epoch. It differs from starting hidden only inside an *explicit* region:
  in an implicit one the footprint is the maximum over the tag's states either way,
  so the space is reserved regardless.

The order is the slide's own: over its states, and within one `sub` over the operations as
written, which is the order the resolver applies them in anyway.
A name that neither operation addresses first is visible and laid out as the body wrote it.
Adding a `reset` to a timeline therefore changes what the first subslide lays out,
inside the region that bounds the change; adding a `reveal` does not,
because content that starts hidden keeps its space.
The two slots stay independent, so a name the timeline resets and later reveals starts out
removed and hidden at once, and the `reset` and the `reveal` undo different things.
Every site of one name therefore starts in the same state by construction,
since the state is a property of the name in the timeline rather than of the site.

Two states are unreachable this way, and both have an answer that needs no argument.
Content that is hidden for the whole slide, with no `reveal` anywhere, is typst's own `#hide`
in the body, which the package's star import deliberately leaves unshadowed;
a tag is then needed only if the timeline moves or scales the hidden content.
Content that is removed for the whole slide, with no `reset` anywhere, is laid out in no epoch,
so it reserves no footprint and reaches no output, and deleting it says the same thing.

A tag **always** wraps, unless `wrap: none` says otherwise.
The decision is a property of the body alone and never of the timeline,
so that adding an animation operation cannot reflow a paragraph,
and so that the three output types and all of a slide's states lay out the same.

| `wrap`     | Wrapper                                                                     |
| ---------- | --------------------------------------------------------------------------- |
| `auto`     | `box` for an inline body, `block(width: 100%)` for a block-level one        |
| `box`      | `box`, the hugging wrapper                                                  |
| `block`    | `block(width: 100%)`, since a hugging block loses the container's alignment |
| `none`     | no wrapper and no label, the body is returned untouched                     |
| a function | the function builds the inner slot, Animo matches the outer one to it       |

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

`wrap: none` is the way to say "this tag is only ever addressed structurally":
with no label there is no group, so the continuous primitives have nothing to animate,
and Animo panics when the timeline asks for one anyway.
A `reveal` is one of those, so such a tag cannot start hidden either,
and the refusal that says so is the one already there.

The body is then returned exactly as it came in, and "exactly" is measured:
the marker and the show rule that carry the plan to a tag site contribute nothing to the
layout, not even where a wrapper would trim a heading's block spacing (see *Findings*).

**A body that is not content is refused**, whatever the `wrap`, and the message names the
cause and the two ways around it. Such a value carries no marker, and a `context` block
cannot return one either, so the tag reaches no view and no primitive could ever resolve it.
The case this exists for is a stream of raw cetz draw commands, which is an array of closures
built where it is written, before any show rule or `context` exists (measured; see
*Findings*). Handing it back untouched was the earlier behaviour, and it made every primitive
a silent no-op on it, which is a poor diagnosis: the symptom surfaces three tools away from its
cause. What to write instead is a cetz `content()` element with a tag of its
own, or a canvas written as a function of what it draws and tagged whole, so that the
timeline replaces it with the same function called differently.

Wrapping is not free, and the manual states this explicitly:
a tagged inline phrase can no longer break across lines, so its paragraph may reflow,
and a tagged heading shifts by a few points, because a heading's own block spacing is trimmed
at the wrapper's edge and replaced by the generic one (measured; see *Findings*).
Tagging the heading's text instead, `= #tag("t")[Head]`, avoids the shift exactly:
the wrapper is then inside the heading rather than around it, and the page is unchanged to
the pixel (measured; see *Findings*).

The wrapping is not cosmetic in the other direction either: only labelled `box` and `block`
elements become addressable groups in the SVG/HTML output (see *Findings*). That is what decides
which primitives a tag site supports, and it is worth stating as a table rather than leaving it
implied:

| Tag site                                    | Structural primitives | Continuous primitives |
| ------------------------------------------- | --------------------- | --------------------- |
| ordinary content                            | yes                   | yes                   |
| inside math                                 | yes                   | yes                   |
| a cetz `content()` element or fletcher node | yes                   | yes                   |
| content tagged with `wrap: none`            | yes                   | refused               |
| raw cetz draw commands                      | refused               | refused               |

The asymmetry in the fourth row has one cause. Structural primitives are resolved by typst
when the epoch is rendered, so they work wherever a tag can wrap something at all. Continuous
primitives are resolved by the browser and need a `<g data-typst-label>` to address, which
typst emits only for labelled boxes and blocks.

The last row is the boundary of the claim above, and it is a property of the value rather than
of Animo's mechanism. `sanor` does reach a tagged `draw.grid(..)`, in `test/draw.typ`, and it
reaches it by threading its `s` through the slide body: the body is a function, re-evaluated
once per subslide, so its `tag` applies draw-to-draw wrappers eagerly at call time. Animo
re-*lays out* one content value instead of re-*evaluating* a function, which is what
*Resolved Design Decisions* settles on other grounds, and a show rule reaches content where
re-evaluation reaches values. So the capability follows from that decision and not from an
unexplored corner. A canvas written as a function of what it draws and tagged whole recovers
the geometry change at the granularity of the canvas, which a structural change there redraws
anyway. A per-epoch canvas body would recover it per object, and that is left for a later
release.

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

`region(body, width: auto, height: auto, align: top, clip: auto, name: none)`

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
  the author wrote, an **implicit region** is the one a bare tag gets. Every tag that becomes
  a box is inside exactly one region, so "outside a region" never means "in no region" in this
  document, and the bullet below is the one exception.
  Structural changes to such a tag reflow within the tag's own box and nothing else: a replacement is laid out in the largest box any of its
  states needs, which is the closest thing to "just swap this element" that keeps the rest of
  the slide still.
- **A `wrap: none` tag has no box, so it gets no implicit region.** Inside an explicit region
  that region bounds it, as it bounds any tag it holds. Outside one, nothing bounds it: its
  content change reflows the flow it sits in, so the area redrawn is the whole rendering, and
  that is what the boundary hands over. The two renderings then cross as they are, since
  nothing outside the change is still.
- `name` makes the region itself addressable, so the *region* can be moved, scaled, hidden or
  revealed like any tag. An unnamed region is invisible to the animation.
- A region is **block-level**, and is always a `block(width: 100%, ..)`, so no detection is
  needed: unlike a tag, a region knows what container it has to be. It does **not** reuse a
  `box` or a `block` that its body happens to be already. Reuse would save nothing, since two
  nested `block(width: 100%)` render identically to one (measured), and it would cost the
  region control over `width`, `height`, `clip` and `align`, which it would then have to merge
  into the author's element by rebuilding it from `fields()`, losing whatever a `set` rule
  contributed.
- **Why block-level**, since the reason is not the one the word suggests.
  It is not that the surroundings have to stay still:
  a box whose footprint is fixed at the maximum over its epochs
  holds its paragraph as still as a block holds its flow,
  because constant size means constant line breaking.
  It is that a region at `width: auto` has to know its container's width,
  and `layout(size => ..)` is the only way to learn it, and `layout` is block-level:
  it breaks the line it is put in (measured).
  Inline, the best available is an unbounded `measure`,
  which reports the natural width of content that never got the chance to wrap.
  A box itself wraps correctly once it has a width,
  so what is missing inside a paragraph is the width, not the box.
  An explicitly sized region could therefore be a box.
  Animo does not offer one,
  because the inline case already exists as the implicit region around a bare tag.
- That implicit region inherits the same limit: its footprint can only come from unbounded
  measurements, so content replaced at an *inline* tag site cannot wrap, it can only run on.
  Inline tag sites are for short content, and the manual says so. A one-line paragraph measures
  as inline under `wrap: auto`, so a tag around one whose replacement should wrap needs
  `wrap: block`, which the manual says as well.
- The footprint of an inline implicit region is not the per-axis maximum of `measure`: a box
  takes its baseline from its content even at a fixed size, so a fixed box still moves its line
  (measured; see *Findings*). It is the widest width, and the tallest ascent plus the deepest
  descent over the epochs, with the content placed inside at the height that aligns its baseline
  and the box lowered by the deepest descent. A block-level implicit region is the filling block,
  as tall as its tallest epoch laid out at the container's width.
- A tag whose content state is the same in every epoch has no footprint and is not measured,
  since it lays out the same by itself. This keeps a slide without structural operations
  exactly as cheap as before epochs existed, and a tag nested in a changing tag needs nothing
  either, because the inner footprint is fixed.

Why a fixed footprint, rather than letting the slide reflow around a growing region? Three
reasons, in decreasing order of importance:

1. It keeps the continuous primitives composable with the structural ones. An element that
   has been moved 2 cm keeps its meaning across a content change, because its base position
   did not change. If the whole slide reflowed, every `move`, `scale` and `pan` in flight
   would jump at the same moment.
1. It keeps the HTML transition correct and cheap: the redrawn slide is pixel-identical
   outside the region, so the crossfade is invisible there (measured; see *Findings*).
1. It keeps the HTML and paged outputs laying out identically, which is the invariant that
   lets one source produce all three output types.

The cost is real: a region reserves room for its largest state,
so a slide whose first state is short and whose last state is tall shows a gap at the start.
The remedies are authorial (choose `align`, split into several regions, give explicit sizes).
The alternative semantics is a region that pushes its surroundings around.
That semantics is deferred rather than impossible.

**Where regions cannot go.** `region` needs ordinary content, so it does not work inside a
cetz canvas (which consumes draw commands, not content) and is awkward inside math. A region
beside a draw command is a type error there, exactly as any other content in a canvas body is
(measured; see *Findings*). In those places, use a bare tag: the
implicit-region rule above gives it a fixed footprint of its own, and `replace` on a tag inside
math or inside a cetz `content` element works there as it does anywhere else.

A region around the whole canvas, `#region[#cetz.canvas(..)]`, is the other half of the
answer, and the two differ in a way that is worth stating. Outside a region, a tagged
`content()` element reserves the room of its widest epoch, so cetz lays the figure out the same
in every epoch and nothing in it moves. Inside one, the tag reserves nothing, cetz lays the
figure out afresh per epoch, the canvas may change size, and the region absorbs that while
keeping everything outside its footprint still. Both were measured to the pixel in the paged
output. So a region around a canvas is what allows a figure to change size,
and without one a figure stays rigid.

### Animation primitives

All primitives return a plain description (a dictionary); they perform no action themselves.
`sub(..ops)` groups the operations that happen together in one subslide.
An empty `sub()` advances one step without changing anything.
It is allowed rather than refused because a timeline is code:
a `sub` whose operations come from a loop or an array may legitimately receive none,
and refusing the degenerate call would turn that into a compile error.
A call carrying only keyword arguments is legal for the same reason,
though `sub(wait: a)` in front of `sub(wait: b, ..ops)` is `sub(wait: a + b, ..ops)`
with one extra state, since a wait is measured from its predecessor's trigger (see *Timing*).

`sub` takes three keyword arguments of its own.
`wait:` and `hold:` are under *Timing*.
`handout:` says whether the handout shows that subslide, and is three-valued:

- `handout: auto`, the default, resolves to `true` for the **last** state of the slide and to
  `false` for every other one, which is the one page per slide the handout shows anyway.
- `handout: true` asks for an extra page at that subslide, which is how a state that a later
  subslide destroys is kept.
- `handout: false` takes a page away, including the final state, so a slide can be left out
  of the handout entirely.

Every state carries this flag, the initial state included.
That state has no `sub` of its own, so its flag is written as `#slide(handout: ..)`,
with the same three values and the same meaning (see *Slides*).
A slide with no `sub` at all has only state 0, which is therefore also its last state,
so `auto` keeps it and `#slide(handout: false)` leaves the slide out of the handout.

The resolver therefore resolves the flag to a boolean per state, and the handout renders the
states whose resolved flag is true. This makes `handout:` the only thing that says what a
handout holds, rather than a set of exceptions to a rule written elsewhere.

It is a keyword rather than a free-standing `handout()` call between `sub` calls, so that its
meaning does not depend on its position in the block, which is the same reasoning that puts
`wait:` and `hold:` on `sub`, and one fewer name at the top level.

The primitives are classified in two ways, and both classifications matter.

The first cut is **what they address**. *Element primitives* take a tag name and act on the
tagged content. *Slide primitives* take no tag and act on the slide as a whole.
Today that is `pan` alone, which moves the viewport over the canvas,
and a narration `audio` could join it later.
Slide primitives touch neither tags, regions, epochs nor footprints, which is why adding one
is cheap.

The second cut is **how they are realised**, and it runs through the whole implementation.

**Continuous primitives** change only how already-rendered content is *displayed*. In HTML
they are pure CSS on the existing frame, so they animate smoothly and cost nothing extra.

| Primitive                             | Meaning                                                            |
| ------------------------------------- | ------------------------------------------------------------------ |
| `reveal(tag)`                         | make the element visible (fades in, in HTML)                       |
| `hide(tag)`                           | make the element invisible, keeping its space (fades out, in HTML) |
| `move(tag, x:, y:, dx:, dy:, relto:)` | translate the element, optionally relative to another tag          |
| `scale(tag, f:, fx:, fy:)`            | scale the element about its own centre                             |
| `pan(x:, y:, dx:, dy:, relto:)`       | move the viewport over the canvas, optionally relative to a tag    |

The first four are element primitives; `pan` is the slide primitive, which is why it takes no
tag name and why `relto`, which means "pan so that this tag comes into view",
is optional rather than positional.
Every one of them also takes `delay:` and `duration:`, which are under *Timing*.

**Where `move` and `pan` put things.** They say where something goes in the same two ways, and
each axis takes one of them.
`x` and `y` put it at a distance from an **anchor**; `dx` and `dy` shift it from wherever it
already is. One call may mix the two across its axes, as in `pan(dx: -17cm, y: 1cm)`, and `x`
together with `dx` on one axis is refused, since the two are measured from different places.
An axis given neither form stays where it is, unless `relto` is given, in which case it goes to
the anchor: `pan(relto: "t")` brings a tag into view, `pan(dy: 3cm)` scrolls, and
`move("a", relto: "b")` puts `a` exactly where `b` is. `x`, `y`, `dx` and `dy` are lengths,
since a ratio has nothing here to be a ratio of.

The anchor is what the two differ about, and only that:

- for `pan` it is the canvas origin, or with `relto` the named tag, placed where the body of a
  fresh slide starts, at the deck's margin;
- for `move` it is the canvas origin, or with `relto` the named tag, and what is put there is
  the **moved tag's own anchor**, so `move("a", x: 2cm, y: 0pt)` puts `a`'s top-left corner
  2 cm from the left edge of the canvas.

The anchor of a tag is the top-left corner of the first site of its name in document order, as
the body laid it out, in the first rendering that lays that site out. Three consequences follow,
and all three are stated here explicitly:

1. **A tag's anchor excludes its own display state**, so it means the same in every state. A
   `move` is therefore idempotent in its absolute form: `move("a", x: 2cm)` twice leaves `a` in
   the same place, and `move("b", relto: "a", ..)` is unaffected by whatever moved `a`.
1. **A name with several sites moves as one.** The first site in document order lands on the
   target and every other site takes the same translation, exactly as `relto` already reads the
   first site. Two sites of one name cannot land on one point without moving independently,
   which the "several places, one tag" rule does not allow.
1. **An anchor is a layout corner, and a `scale` is about a centre.** An element that is both
   moved and scaled lands its *unscaled* anchor on the target, and its painted corner sits half
   the growth further out. Absolute placement of scaled content is therefore approximate by
   construction, and the exact form is a `dx`/`dy` shift.

A `move` or `pan` relative to a tag the slide does not have is refused, because a misspelt name
is the likely cause and a silent fallback would hide it, and so is one relative to a `wrap: none`
tag, which has no box to have a corner. The same holds for the other continuous primitives: a
`move`, `scale`, `reveal` or `hide` on a name that became no group on its slide is refused, for
the reason under *Scoping*.

**An anchor read from inside a tag the timeline moves or scales is refused as well**, and this
one is a refusal about the body rather than about a name. A transform around a tag moves the
very corner its anchor is, so the anchor stops being the corner the body gave it, and no
rendering can recover the one the design promises: the static presentation and the browser still
read an untransformed layout, the first from its own first page and the second from the slide
before anything is written on it, while the handout reads whichever page it keeps. So a
`pan(relto: ..)` below a transform would put the viewport in two different places in two output
types, and a `move` whose `relto` names a tag inside the tag it moves would not even converge,
since its own translation moves the marker it reads. The rule covers the moved tag's own anchor
too, so `move("a", x: ..)` on a tag inside a moved one is refused for the same reason. What is
refused is reading the anchor, not the nesting: a tag inside a moved tag is the ordinary way to
move a group and light up a part of it, and a tag inside one that is only revealed or hidden
keeps its anchor, because typst's `hide` lays content out where it is. The remedy is to read the
anchor of the outer tag, or to take the inner one out of it.

What the anchor of a tag is exactly, and how the two targets read it, is under *Architecture*.

The resolver keeps each axis as a pair, an anchor name and an offset, rather than as a single
number: `x` sets both, `dx` adds to the offset and leaves the anchor alone, and the default pair
is the element's own anchor at offset zero. A target computes the translation as
`anchor(relto) + offset - anchor(self)`, which is the identity when nothing has been said. This
lets absolute and relative forms alternate along a timeline without either one having to
know the other's units, and it is the same shape the plan already carries for `pan`, whose
`anchor(self)` is the canvas origin.

**What `scale` does.** `scale` takes `f` for an isotropic factor and `fx`/`fy` for one axis
each, and **`f` cannot be combined with either**. The combination is refused rather than
resolved by a precedence rule, since a call that says both says two different things.
Each is a number or a ratio, so
`scale("a", f: 2)` and `scale("a", f: 200%)` are the same operation; a ratio is resolved to a
number when the operation is built, because that is the form the browser and the paged renderer
both take.

**A factor is set, not multiplied into what is already there.** `scale("a", f: 2)` in one subslide
and `scale("a", f: 2)` in the next leaves `a` at twice its size, not four times, and
`scale("a", f: 1)` restores it whatever came before. An axis the call does not mention keeps
its factor, so `scale("a", fx: 2)` after `scale("a", f: 3)` leaves `a` at 2 horizontally and 3
vertically. Successive growth is written as the product, so the author multiplies once
instead of tracking a history across every later subslide.

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
  in the style of `sanor`'s `case(fill: red)` are deliberately not supported: Animo does not
  inspect content, so it cannot know which `set` rule a bare property belongs to. Wrapping
  with `text.with(..)`, `box.with(..)` or a lambda says it explicitly.
- `apply` is structural even when the wrapper cannot possibly reflow (a colour change).
  The reason is not reflow but rendering: typst's styling is not expressible in CSS in
  general. The cheap CSS-only special case, a primitive that changes a colour and nothing
  else, is left for a later release.
- **`reveal` and `reset` also declare an initial state.** A name whose first display operation
  is `reveal` starts hidden, and one whose first content operation is `reset` starts removed
  (see *Tags*). Neither is a pure undo for that reason: a `reveal` written where nothing hid the
  tag used to change nothing and now makes the tag start hidden.
- **Inserting** content that is not in the body is `replace` on an empty tag:
  `#tag("slot")[]` in the body, `replace("slot")[..]` in the timeline. Content that *is* in
  the body but should start out absent is a plain `#tag` that the timeline resets, which is
  what makes it start removed.
- `remove` versus `hide`: `hide` keeps the space and is smooth; `remove` frees the space and
  reflows. This restores the "occupies no space" state that the first draft dropped, now that
  regions give it a bounded meaning.
  Outside a region there is nothing for `remove` to reflow,
  because the implicit region reserves the footprint of the element's largest state
  either way.
  There it costs an epoch without any benefit, and `hide` is the right primitive.
- Structural primitives work at every tag site, a `wrap: none` one included, because typst
  renders the epoch and needs no group to do it. What such a site redraws outside an explicit
  region is the whole rendering, since it has no box of its own; see *Regions*.
  Continuous primitives need a labelled group and so need a wrapped tag site. A tag site is
  content in either case: raw cetz draw commands are refused, and no primitive reaches them.
  See the table under *Tags*.
- **How they compose.** A tag's content state is two slots that are set independently: what is
  laid out (the body, a replacement or nothing) and the list of wrappers. `replace` and `remove`
  set the first and keep the second. `apply` appends to the second, so it wraps whatever is laid
  out then or later, a later replacement included. `reset` sets both, back to the body with no
  wrappers. So `apply` then `replace` is a restyled replacement, `reset` after `remove` is the
  body with no wrappers, and replacing twice keeps the second replacement. None of the four
  touches the display state: a moved tag that is replaced is a moved replacement, and `reset`
  does not undo a `move`. Several operations on one tag in one `sub` apply in the order written,
  as continuous operations do, so `apply("x", f, g)` in one subslide equals two subslides
  and lays out `g(f(content))`.
- Because `replace` and `apply` carry content and functions, plan descriptors are no longer
  pure data in the strict sense. Tier-1 tests should therefore assert on the *resolved
  structure* (tag names, per-state flags, epoch boundaries and counts) rather than on the
  payloads, which do not compare usefully.

### Timing

Four arguments decide *when* and *how long* rather than *what*, and keeping them apart by name is
the whole of their API. `wait:` and `hold:` time a **subslide**, the first naming the gap before
it and the second the gap after it; `delay:` times an **operation inside a subslide**; `duration:`
says
how long that operation then takes. All of them are plain numbers of seconds, because typst has
no time literal of its own and `2s` would not parse, and because one unit across the whole
surface is what keeps two numbers on one call comparable. All of them are HTML only: the paged
outputs are one page per state with nothing between them, so there is no clock for any of them
to be measured on. The stylesheet is the one place where a time carries a unit, because a custom
property read as a CSS `<time>` must: Animo writes its own values as `0.4s` rather than as
`400ms`, so that every number an author reads or writes is still a number of seconds, and the
runtime accepts either spelling.

**Three arguments of the deck's show rule say what motion costs when nothing else does.**
`primitive-duration:` is how long one animation primitive takes, `transition-duration:` how long
a transition between two slides takes, and `easing:` is the timing function both of them follow:

```typst
#show: animo.with(primitive-duration: 0.2, transition-duration: 0, easing: "ease-out")
```

The two durations are numbers of seconds like every other time an author writes, `0.4` each by
default, and a zero means that kind of motion is not animated, so the deck above cuts
between its slides while the steps inside them keep moving. `easing:` takes one of `"linear"`,
`"ease"`, `"ease-in"`, `"ease-out"` and `"ease-in-out"`, the last being the default, and a
name outside that list is refused at compile time, because a timing function the browser
rejects would throw in the middle of a talk. The three reach the runtime as the custom
properties `--animo-primitive-duration`, `--animo-transition-duration` and `--animo-easing`
on `:root`, which the deck writes into its own stylesheet beside its geometry
and the runtime reads at every step,
so restating one reaches every operation that asked for nothing of its own.
They are HTML only, like the four times above them, and the paged outputs ignore them.

**`wait:` is the delay before the subslide it is written on is entered, and `hold:` is the delay
before the subslide after it is.** Those are two rules for one quantity, and both hold at both
levels:

- `sub(wait: 2, ..ops)` brings that subslide up two seconds after the previous state came up,
  instead of on a presenter click; `sub(hold: 2, ..ops)` keeps it up for two seconds and then
  brings up whatever follows it, which on the last `sub` of a slide is the next slide;
- `#slide(wait: 2, ..)` enters that slide two seconds after the previous slide's last state came
  up; `#slide(hold: 2, ..)` holds its initial state for two seconds, which on a slide with no
  `sub` at all is again the boundary into the next slide.

`none`, the default of both, waits for the presenter. Two spellings of one gap is one keyword
more than the surface needs, and it is here because each of them is the natural one for a
different sentence. "This slide needs no click" is about the slide being entered and is
`#slide(wait: 0)`; "do not stop here, run straight on" is about the motion that is playing and is
`sub(hold: 0)` on the subslide that plays it, which is also where the author is looking. Neither
covers the whole surface alone. `wait:` has no reading on the first state of a deck, which has no
predecessor, and `hold:` has none on the last, which has no successor; neither of those cases
is a real loss. `wait:` cannot be written on a subslide a loop generated, so a slide boundary
after a generated timeline has to be timed from the slide that follows. And the two
survive editing in opposite directions: inserting a subslide hands its predecessor's `wait:` to
whatever now occupies the gap, where a `hold:` stays with the state it was written for, while
appending a subslide to a slide takes that slide's trailing `hold:` with it, where a `wait:` on the
next slide is unmoved.

**One gap takes one number.** A gap that both of its neighbours time is refused, naming both
sides. A gap elapses once, so there is nothing for a precedence rule to pick between, which is
the resolution two operations disagreeing about a `delay:` in one region already get. Summing the
two was the other way out and was rejected on what it would mean rather than on what it would
cost: no author means "hold three and wait one" as four, so the sum's only effect is to accept a
gap that got specified twice and hand back a length that neither number states. It also has no
reading for the `hold: auto` that a narrated clip would need later, which cannot be added to
anything. Refusing now is the choice that keeps the other one open, since widening a refusal
into a sum later would break no deck and narrowing a sum into a refusal would break several.

The refusal is a compile error in both of the places it can arise. Inside a slide the resolver
sees both sides of every gap. Across a slide boundary neither slide does, because the trailing
`hold:` and the leading `wait:` are resolved by two calls, so a slide hands its trailing `hold:`
to the next through a state, unconditionally, and the next checks the pair against its own
leading `wait:`. That is the mechanism the handout's own deck-wide refusal already uses.

Timing does not take the deck away from the presenter. **A forward step cancels the pending timer
and re-arms from the state it lands on**, so a presenter can always run ahead of the clock and a
deep link starts its own timer from where it lands.

**A backward step lands on the nearest earlier state the deck would rest at.** A gap of zero
is a join rather than a stop: the state it is measured from is left at the same moment it is
entered, so the audience never sees that state at rest, and the motion it began is redirected in
its first frame rather than arriving. Landing there would put a composition on the screen that
was never shown, and it would cost one press per join to walk back over a run the presenter got
through in one, since a join costs no press going forward either. A join is therefore crossed in
both directions, and a run of them is crossed whole, a slide the deck runs through included. It
is the timeline that says where a deck rests and not the clock, so the walk is the same while the
clock is stopped, and a state it walks over stays reachable both by a fragment and by stepping
forward through a stopped deck. Zero is the whole of the rule, and `hold: 0.001` states
that the state before it is a stop after all.

**A join that runs out of a slide is walked back into.** Such a step lands on a state below the
last one of the slide it enters, which is the one case where the slide being entered is not
already showing the state it is entered at, and it moves into that state rather than snapping
into it. Going forward the audience saw one motion, the step running inside the slide while the
boundary carried it away, so a backward step that snapped the slide into place would crossfade a
picture that was never shown. The two clocks stay their own: the slide moves on
`--animo-primitive-duration` and the boundary crosses on `--animo-transition-duration`,
started on one frame as the forward join started them.
A forward step is the asymmetry that makes this safe to state.
It snaps, because a slide keeps the state it was last shown in and may be entered at state 0
while showing a later one, and animating out of that state would play a step the audience never
saw, backwards, while the slide is coming up. A step that crosses more than one
slide boundary snaps whole, as it always did.

**A backward step also turns the clock around.** One gap times the step in both directions,
because a gap lies between two states rather than belonging to one of them. A state the deck
leaves on its own after a second going forward is a state it leaves on its own after a second
coming back, so a state inside a run is shown for as long in either direction. The travel ends at
the state whose gap waits for the presenter, which is the state the presenter last pressed a key
at, so a run of automatic gaps costs one press back as it costs one press forward. A backward key
pressed during the travel is one more step back, as a forward key pressed during autoplay is one
more step forward, and `Space` stops the deck where it is. A deck that times every one of its gaps
has no state to end the travel at and travels back to its first state.

**The first state of a deck is where backward travel stops rather than turns**, because there is
nothing earlier to travel to. The gap that state carries would arm forwards and undo the step that
just arrived, which would leave the state reachable for that gap's length and no longer, so the
clock is stopped there instead. A deck that runs itself out of its first slide from the first
paint is held there by that stop, and without it the slide would be reachable for no time at all,
since `Space` is the forward key where no timer is pending. A forward step puts that clock back
and so does `Space`. A backward step over a gap that was waiting for the presenter changes
nothing, which is what keeps every key of a deck with no number in it exactly as it was.

**`Space` stops and starts the deck**, which is what a reader watching a deck play itself asks
for, and it does so only while there is a clock to stop: on a deck with no clock it is
the forward key it has always been, which is what a presentation remote sends. The stop reaches
the motion as well as the clock. An animation in flight is paused where it is and picked up from
there, so the picture holds still rather than running on to the end of the step it was in.
Resuming puts back what is left of the wait rather than restarting it, and it puts the deck back
on the way it was going, so `Space` is the one key that says nothing about direction. A manual
step while the clock is stopped leaves it stopped. That last rule distinguishes the two stops: a
deck stopped on purpose stays stopped while its presenter steps through it, where a deck stopped
at the first state of the deck carries on when they step forward again.
Both publish the same `data-animo-paused` on the root element,
and a deck that wants to show the pause reads it there. The pause is **not in the fragment**,
which stays the position and nothing else, so a deck restored from a hash comes back running, the
reload of `typst watch` included.

A `wait` and a `hold` are measured from the moment the subslide they are timed against was
**triggered**, not from the moment its animations finished. A gap shorter than that subslide's
motion therefore interrupts it, which needs no rule of its own: an interrupted subslide continues
from where it is, by *Architecture*. A `hold: 0` is the limiting case and is the reason the
measurement is stated this way: it starts the next subslide at the same moment as the one it is
written on, so a
build that runs over two slides keeps its motion and the slide crossfade on one clock.

**`delay:` holds one operation back within its subslide**, and every primitive takes it,
continuous and structural alike, defaulting to zero. `scale("a", f: 2, delay: 0.2)` starts a
fifth of a second after the subslide it is in. The subslide still has exactly one clock: a delay
becomes the effect's delay in the Web Animations API, so all of a subslide's animations are still
created in one task and all of their delays are measured from the same instant.

**A backward step is the step it undoes, mirrored in time.** The step lasts as long as its last
operation runs, and every operation of it is turned around about that length: one that ran from
`delay` to `delay + duration` runs backwards from `step - delay - duration`, for exactly as long
as it took. So the last thing the audience saw arrive is the first thing they see leave, a step
of three staggered lines comes apart in the reverse of the order it was built up, and the step
ends where the earlier state began. Replaying the schedule as it stands was the first rule and
is the wrong one: it makes the operation that arrived first leave first, so the composition
passes through states the forward step never showed, and where one line is nested inside another
it takes the outer line away while the inner one is still on the screen. Only the delays are
mirrored, because a duration is how long an operation takes and not when it happens.
A backward step that walked back over a join runs between two states that are not neighbours,
and the schedules of the steps it walked over go with them: what the audience saw across a join
is one motion redirected before it arrived, which neither schedule replayed on its own
reproduces, so the way back is one motion too, mirrored about the length of the step that
began it. The epoch boundaries such a step
crosses are handed over together and on that one motion's clock, which *Architecture* rule 2
states.

On a structural operation a delay holds back the **crossfade of the region it changes**, and the
epoch boundary lasts until the last of them has finished, the outgoing frame staying visible in
the regions it hands over for that whole time. Staggering two structural changes therefore works
when they sit in two regions, which two bare tags always do, since each is its own implicit
region. Two operations that change *one* region at one boundary and disagree about `delay:` are
refused: a region crossfades once, so there is nothing for a precedence rule to pick between.

**`duration:` says how long one operation takes**, and every primitive takes it beside `delay:`,
defaulting to `auto`. `auto` is the deck's own `primitive-duration:`, so a timeline that asks for
nothing reads as one deck and a change of the deck's tempo still reaches every operation that
did not ask for something else. A number is a number of seconds, so
`reveal("a", delay: 0.5, duration: 2)` fades in over two of them. It becomes the Web Animations
API effect's duration, exactly where `delay:` becomes that effect's delay, so the subslide still
has one clock, an interrupted subslide is unchanged, and a backward step keeps every operation's own
duration while mirroring the moment it starts at.

**A reader who asked for less motion gets none, whatever the deck or the timeline says.** Every
duration before `duration:` is a custom property on `:root`, and that is the only reason
`prefers-reduced-motion: reduce` works at all: it is one media query over two custom
properties, and a number written in a typst source is invisible to it. The deck writes its own
`primitive-duration:` and `transition-duration:` into the same `:root`,
after the stylesheet that holds the query,
so both declarations in the query are `!important`
and the guard wins by cascade weight rather than by source order.
That covers a stylesheet an author adds to the page as well, which source order alone did not,
as chromium 151 and firefox 153 both showed.
An explicit `duration:` is therefore zeroed when `--animo-primitive-duration` is zero,
by the runtime rather than by the stylesheet, and takes the same snapping path a deep link takes.
Making `duration:` a multiple of `--animo-primitive-duration` instead of a number of seconds
would get the same property arithmetically, and it was rejected for its unit:
`delay: 0.2, duration: 5` would then be two numbers on one call meaning seconds and multiples of
something else.

A `delay:` goes the same way, and neither of the two gap numbers does. A step whose duration is
zero has no motion for one operation to arrive late inside, so the runtime drops the delays of a
snapping step along with its duration, which makes one reading of the media query serve all three
numbers and keeps it in one line. A `wait:` and a `hold:` are left alone, because they are pacing
rather than motion: zeroing them would run an autoplaying deck through itself at once, which is
worse for a reader who asked for less motion than the motion they asked to be rid of.

**A duration may run past the subslide it is in**, and an operation that outlives its subslide is
overtaken rather than clamped or refused. For a continuous operation that is the rule
*Architecture* already states, an interrupted animation continuing from where it is. For a
structural one it means the epoch boundary stretches with the duration, so two boundaries
may be in flight at once and three frames may paint one region together. That state is not
particular to a duration: a gap shorter than a subslide reaches it, and so does a presenter
clicking twice, which is why clamping a structural duration to its subslide or refusing one that
outlives it would remove a way in rather than the state. What the boundary does with it is
under *Architecture*: every frame that is not the one being entered hands the region over on
the new boundary's clock, so the region's ink stays at one throughout.

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
  word *state* is reserved for the S+1 subslides.)

**How a region measures one epoch.** Not by substitution: a region receives its body as opaque
content and cannot rewrite the tags nested inside it. Instead the current epoch is an entry of
the view provided to the body (see *Scoping*), and the region measures by laying its own body
out once per epoch under a copy of the view with that entry set accordingly, each tag resolving
its own content for the epoch as it is laid out. Verified in both targets, inside `layout` and
`measure`, with nested `context` reads and no convergence warning (see *Findings*).

This is stated explicitly, because it matters in two ways. It is what makes reflow
inside a region possible without turning the body into a function of the epoch,
which is the `s => ([body], s)` threading that *Resolved Design Decisions* rejects.
And it is **indifferent to where time-dependent content is written**:
a tag could resolve its content for the epoch from the plan or from its own arguments
equally well. So the question of where `replace`'s content belongs
is not a feasibility question, and is settled on other grounds below.

Renderings required per slide:

| Output type         | Renderings                                    |
| ------------------- | --------------------------------------------- |
| HTML presentation   | one per epoch                                 |
| Static presentation | one per state (S+1)                           |
| Static handouts     | one per state with `handout` resolved to true |

A `background` or `overlay` that is content is rendered **once** beside these in HTML, whatever
its epochs, because neither layer can depend on one; in the paged outputs each is laid out once
per page of the slide (see *Background and overlay*).

A `per-subslide` is the one construct whose cost is counted in **states** rather than in epochs:
it is one rendering per state of its slide, wherever it sits. In a layer that is one stack per
slide, and in the body it is one stack per epoch rendering, which is why *Slides* says to put a
number in a layer. Nothing about it travels in the plan, since the runtime finds the renderings
by the label each of them carries.

### Architecture

The same tagged content feeds three output types:

**HTML presentation.** A slide is rendered as *one* `html.frame`, i.e. one inline SVG, laid
out on the canvas, holding one rendering per epoch. The epoch renderings are `#place`d on top
of each other at the origin of that frame, in epoch order, each a labelled `box` so that it
becomes a `<g data-typst-label="animo-epoch-N">` the runtime can address. One frame and not one
per epoch, because typst's deduplicator has the frame for its scope: the renderings of a slide
then define each glyph they share once between them rather than once each, which is the only
part of that duplication a package can reach (see *Findings*). The canvas element sits inside
the viewport element, which is the slide's visible box and clips it (`overflow: hidden`),
between the background frame and the overlay frame, which are frames of the slide rather than
renderings inside the canvas's frame and are not moved by a `pan`.
Each tagged element appears in every epoch rendering as a `<g data-typst-label="...">` group.
Animations are then performed in the browser:

- `reveal`/`hide` animate `opacity` on the tag's inner group
- `move` animates the CSS `translate` property, computed from the measured anchors as
  *anchor(relto) + offset - anchor(self)*, which is the identity for a tag the timeline has not
  moved
- `scale` animates the CSS `scale` property, about the element's own centre, with one value for
  `f` and two for `fx`/`fy`
- `pan` animates `translate` on the canvas element inside the clipping viewport, as a
  percentage of the canvas, which follows the window without being measured
- a `per-subslide` stack shows the rendering of the state being entered and hides the others,
  by writing `opacity` on the labelled group of each. It snaps, in a step that animates as much
  as in one that does not, since two numbers crossfading into each other are two numbers neither
  of which can be read. `opacity` and not `visibility`, which is what hides an epoch rendering
  nobody is watching: a descendant may take its visibility back, so a stacked rendering that did
  would paint out of an epoch the slide is not showing, where one at `opacity: 1` inside a
  hidden epoch stays hidden (see *Findings*)
- structural steps crossfade the changed **region**: the region's labelled group fades out in
  the outgoing epoch rendering and in in the incoming one, with `mix-blend-mode: plus-lighter`
  on the epoch renderings inside the canvas, which isolates, and `visibility` scoping the
  outgoing rendering down to the regions it hands over
- a slide boundary crossfades the two **slide containers** by the same means: `plus-lighter` on
  the containers inside an isolated stacking context, the outgoing one kept laid out until the
  two have crossed, and `--animo-transition-duration` rather than `--animo-primitive-duration`
  for its length.
  Nothing is scoped here, because the two slides share nothing to hold still, which is why
  the whole container is the unit. `transition: none` and a duration of zero take the same
  path, which is no animation at all and one container shown in place of the other.
  Two things differ from the epoch crossfade, and both are measured rather than chosen.
  A slide outside a boundary is hidden with `display` where a frame is hidden with `visibility`,
  because a frame nobody is watching has to keep the geometry the morph will read while a slide
  outside a boundary is wanted neither for its ink nor for its geometry, and laying every slide
  of a long deck out costs seconds of first paint. And the deck's surround is a colour on the
  page rather than on the element that isolates the blend, whose own ground would otherwise be
  summed into both slides (see *Findings* for both)

Five rules make this work:

1. Continuous state is applied to **all** epoch renderings of the slide at once, not only the
   active one. Entering an epoch therefore never needs re-initialisation, and a subslide that
   is both structural and continuous (a `replace` together with a `move`) animates in lockstep
   in the outgoing and the incoming rendering, so the composite reads correctly. Operations on
   a tag that is absent from an epoch are no-ops in that rendering.

1. **The crossfade is scoped to the regions whose content state changed**, not to the whole
   frame. Only the changed regions' labelled groups are animated, one fading out and one in,
   and nothing else in either frame takes part. Two mechanisms together make that true, and
   which does which matters:

   - **`visibility` scopes the epoch renderings a boundary is not entering.** One rendering is
     shown at a time, and the others are `visibility: hidden`. A boundary gives their carried
     regions their visibility back, and nothing else, so such a rendering paints in those
     regions and nowhere else. Outside them the reader sees the incoming rendering
     alone, which is what makes the containment exact *by construction* rather than by the
     weaker argument that a typst rendering paints nothing where it has no ink. `visibility`
     and not `opacity` or `display`: a descendant can take `visibility` back, while the
     rendering stays laid out, so the geometry of a rendering nobody is watching stays readable,
     which is what the morph will need.
     Every rendering that is not the one being entered takes part, and not only the one the
     step is leaving, because a boundary crossed while an earlier one is still running finds
     more than one of them painting the region. They then all leave on the new boundary's
     clock, under one easing, while the incoming rendering arrives under its complement, so the
     sum stays at one whatever each of them was showing when it began (see *Timing*).
     A step may also cross more than one boundary at once, which is what a backward step that
     walked back over a join does, and it names the regions of all of them. That is the same
     picture reached from the other side, and it takes the same clock: the boundaries it
     crossed are steps the deck ran through, so the only clock left is the step's own, and the
     timings their operations stated go with the schedules of the steps that stated them.
     The boundaries such a step crosses are in the slide it is standing on, or in the slide it
     is entering when the join it walked back over ran out of a slide, and the handover is the
     same one either way.
   - **`plus-lighter` on the epoch renderings makes the two halves of a region add.** They are
     the outermost groups of the slide's one frame, so each of them adds to ink beside it,
     which is what a blend needs and what is measured (see *Findings*): the outgoing region at
     `1 - t` and the incoming at `t` come to exactly one opaque region, and nothing dips. A
     single visible rendering added to a transparent backdrop is that rendering, so the blend
     changes nothing outside a transition.
     It sits on the rendering rather than on the region's own group so that one element carries
     both halves of the mechanism, the blend and the `visibility` the boundary scopes with.
     That was once forced rather than chosen: when the renderings were frames of their own, a
     blend on a region's group was measured not to reach the frame below at all and degraded to
     a plain opacity crossfade.
     How far a group's blend reaches *past* its own frame is not the same in every engine,
     which is why the canvas isolates rather than leaving the containment to the root of the
     inline SVG (see *Findings*).

   The measured cost is 1/255 rounding inside the region against 62/255 for a plain opacity
   crossfade, and nothing at all outside it; see *Findings*.

1. Animo must emit **only** the individual transform properties (`translate`, `scale`) and
   never the `transform` shorthand, which would clobber typst's own positioning (see
   *Findings*). `transform-box: fill-box` and `transform-origin: center`, which are what make
   a `scale` grow the element in place, fall under the same prohibition one step further out:
   they re-anchor the element's own `transform` attribute as well, so on a group typst
   positioned they move its content (see *Findings*). Both are therefore written by the
   runtime, on the slot it is about to transform, and never as a rule in the stylesheet,
   which cannot tell a slot from a region's content.

1. Continuous state and boundary state get **separate nested slots**. `tag` wraps its body
   twice, in two wrappers of the same kind, so every tag site emits a labelled outer group with
   an unlabelled inner group inside it (see *Findings*). Continuous primitives address the
   inner group (`[data-typst-label="x"] > g`); anything belonging to an epoch *boundary*,
   the region crossfade today and the morph later, addresses the labelled outer group.
   CSS gives each element only one `translate` and one `scale`,
   so the split is what keeps the two classes from clobbering each other.
   The order follows from how a boundary effect is measured:
   it is measured in the frame's own coordinates
   and must sit *above* the continuous transforms rather than inside them,
   or a tag that is being scaled or (later) rotated while its region reflows
   moves by the wrong amount in the wrong direction.
   A morph added later works this out.
   Opacity is exempt from the ordering argument, since the two slots simply multiply,
   but it follows the same convention.

1. **`pan` belongs to the canvas element, not to what is inside it.** It is a slide primitive,
   so it must not be applied per epoch: the renderings sit in the frame the canvas holds, and
   moving the canvas moves all of them together and keeps the crossfade registered. This is also the one place
   Animo touches a transform outside an SVG group, where rule 3's prohibition does not apply,
   although `translate` is used there too,
   for consistency and to leave `scale` free for a future zoom.
   A background or overlay that is content belongs to the viewport rather than to the canvas,
   so in HTML each is a frame of its own beside the canvas element, not ink in the
   canvas's frame, and a pan moves the canvas between them; on paper they are placed on the
   page before and after the panned canvas. One frame each per slide covers every state and
   every epoch, since neither may hold a tag or a region and so neither can depend on one.

**How the plan reaches the browser.** The resolved display state of every state of a slide
travels as compact JSON in a `data-animo-plan` attribute on the slide container, keyed by tag
name, beside the `data-animo-slide` and `data-animo-states` attributes the runtime already
reads. An attribute rather than a `<script>` element, because the HTML parser escapes and
unescapes an attribute value while typst writes script content raw, so a tag name can never
break the page; and because a browser's element inspector shows it beside the slide it belongs
to, which is what makes a step that misbehaves a question about one value rather than about the
whole runtime. Every state holds every addressed tag, even the ones it leaves at the identity:
the browser keeps a display state as inline style until something overwrites it, so a state
that said nothing about a tag would leave the previous state's style in place and stepping
backwards would not undo what stepping forwards did. State 0 is resolved from the timeline like
every other state, out of which operation addresses a name first, so the runtime applies what it
is given and resolves nothing, and no tag site reports a display state of its own.
The one exception is the anchor of a `relto`. Each state
carries its pan, and each moved tag its position, as an anchor and an offset per axis,
`(relto:, offset:)` with the offset in points, and the slide's margin and canvas size travel
beside the states: a tag's position is dead in HTML, so the resolver keeps the anchor a name and
the runtime adds the position it measures, which is the next paragraph but one. Beside the
display state, each state carries the `wait:` and the `hold:` it was given and each operation the
`delay:` and `duration:` it was given, all in seconds, because none of them can be resolved
anywhere but at the moment the step runs. Beside those, a state carries how long the step that
enters it lasts, which is what a backward step mirrors its operations about, and it carries it as
two numbers rather than one: the resolver can add up only the operations that stated a duration,
because the duration the others take is the deck's own and lives in the stylesheet, so it hands
over the largest end it could compute and the largest delay of the operations it could not, and
the runtime adds `--animo-primitive-duration` to the second. A step that states no timing at all
carries neither, and lasts exactly one `primitive-duration:` of the deck.
Both gap numbers travel rather than one resolved number per gap,
because the gap across a slide boundary is timed by two slides and emitted by two calls,
so the runtime is the first place that sees both sides of it.

**Motion is driven by the Web Animations API**, not by CSS transitions. A step writes the new
display state as inline style and animates from what the element was showing to that, so the
style is the state and the animation is only how it got there. An interrupted step therefore
continues from where it is, a backward step lands on exactly the geometry the earlier state had,
and a restore needs no transition to suppress. A backward step differs from a
forward one in two things and no more: every effect of it is mirrored about the length of the
step it undoes, by *Timing*, and it is the direction that may rewind the slide it enters, which
it does when a join ran out of that slide. Every animation of a step is
created in one task and none of them is told when it began, so the browser starts them all at
the same frame: the step has one clock, which is the clock an epoch crossfade joins. Reading
that clock off `document.timeline` instead would be wrong, because the timeline stands still
while the page does (see *Findings*). A step animates only the properties it changes, and not
the ones it leaves alone, because a property that holds still in the keyframes stops chromium
from drawing the ones beside it (see *Findings*). A primitive takes `0.4s` and eases in and
out; both are custom properties on `:root`,
written there by the deck from its `primitive-duration:` and `easing:` arguments,
so the values are in the stylesheet rather than in the runtime
and `prefers-reduced-motion: reduce` sets the duration to zero,
which is also what a deep link and the first paint get. A slide boundary has a third such
property, `--animo-transition-duration`, also `0.4s`, so a deck of hard cuts states one argument;
`prefers-reduced-motion` zeroes that one too. An operation that states a
`duration:` of its own overrides the first of the three for itself, and a zeroed
`--animo-primitive-duration` still zeroes it, so reduced motion is decided in one place
(see *Timing*).

An operation's `delay:` and `duration:` become the effect's own delay and duration rather than a
timer of its own, which keeps the step's one clock intact, and a gap's `wait:` or `hold:`
is the only timer the runtime sets. That timer is armed when a step is entered and cleared
whenever another one is, whatever entered it, so a presenter stepping by hand is never racing a
clock that is still counting. A backward step arms it the other way, by *Timing*, so the deck
travels back over the gaps it travelled forward over, and it is also the one step that may land
further back than one state, since it walks back over the joins it finds on the way.

**How `relto` finds its tag, and `move` its target.** The anchor of a tag is the top-left corner
of the first site of its name in document order, as the body laid it out, which is the corner of
the tag's outer wrapper. The tag's own display state sits inside that wrapper and does not enter
the anchor, so `relto` means the same in every state, and an absolute `move` is idempotent. One
mechanism serves both primitives: `pan` reads the anchor of its `relto`, and `move` reads the
anchor of its `relto` and of the tag it moves. The two targets read the corner by different
means,
because positions are dead in HTML. The browser reads the origin of the labelled group, mapped
into the user space of its frame, when the slide is first shown and before anything is written
on it. Typst cannot use the wrapper's own position, which for a box on a line is the line's
baseline (see *Findings*), so on paper every tag site carries a zero-size marker placed at the
corner of its outer slot, and every page one at the canvas origin, which turns a position on a
panned page back into a position on the canvas. Only the paged target emits these markers, so
the groups the browser addresses are untouched. Over every kind of tag site measured the two
resolutions differ by at most 0.0005 pt, and a pan read back off the rendered page by at most
0.005 pt (see *Resolved Design Decisions*).

"The first site" needs one clause more, because a tag whose content changes is not laid out in
every rendering of its slide. It is the first site in document order **in the first rendering
that lays that site out**: the first epoch rendering holding a group of the name in HTML, since
the renderings are placed in epoch order, and the first page that carries the marker on paper. The two
coincide in the static presentation, whose pages are the states in order, so its first page
holding the tag is the first state of that same epoch. The handout renders a subset of the
states and so reads the first page it *keeps*, which is the one place the rule is a property of
the mode rather than of the mechanism, and the refusal below is what keeps that from meaning
anything: an anchor can only differ between two renderings of a slide if a transform sits above
it.

Anchors are resolved once per slide rather than once per state. On paper that is one
introspection pass over the slide's pages, and in the browser one measurement when the slide is
first shown; only the tags the plan actually names are read, which for a position whose anchor
is the tag's own name is none at all, since the two terms cancel whatever that anchor is.

Two refusals hang off this, and neither can be decided before the body is laid out: a pan
or a move relative to a tag the slide does not have, and an anchor read from inside a tag the
timeline moves or scales. Both can only
be detected from `query`, and a panic raised there may be swallowed.
They are kept reported by where they run: in a context block of its own after the
slide, emitting nothing, checked against the tag sites the slide's rendering reported, which
are the site reports in HTML and the anchor markers on paper, each carrying the tags whose
display state encloses it. A failing check then empties only itself, a site
reported a pass late is
forgotten with the errors of that pass, and a tag that is really missing fails the pass typst
ends on (see *Findings*).

The second of them is what the view's `within` entry exists for. Which tags enclose a site is a
fact about the body, and the body is opaque to the resolver, so a site learns it the way it
learns everything else about its slide: from the view it is handed, extended by every enclosing
site that carries a display state of its own, which is a wrapped tag or a named region. Only a
name the timeline addresses with a continuous primitive extends it, so a deck with no continuous
primitive threads nothing.

Because one rendering covers all subslides of its epoch, stepping within an epoch needs no
re-rendering and motion is genuinely smooth. The cost of structural operations is paid in compile
time and page weight, not in interaction.

**Static presentation.** One page per state: a snapshot of the *viewport* at that state, clipped
out of the canvas, with the background under it and the overlay over it.
Nothing moves.
The `move`, `scale` and `pan` primitives become discrete jumps between pages,
and `replace`, `remove` and `apply` are simply rendered in place.
A panned subslide is therefore a page showing a different part of the canvas,
so panning survives into the paged output.
Everything under *Timing* is absent rather than approximated.
A page has no clock, so `wait:`, `hold:`, `delay:` and `duration:` say nothing here.
Neither does `transition:`, which describes what happens between two pages
that are simply consecutive.

**Static handouts.** One page per state whose `handout` flag resolves to true, which by default is
the **final state of the slide** and no other: the viewport at its final position, like the
static presentation. Extra pages are asked for with `sub(handout: true, ..)`, and with
`#slide(handout: true)` for the slide's initial state. Pages are given up with
`sub(handout: false, ..)` and `#slide(handout: false)`, so an ordinary slide contributes one page
and an author who says so contributes any number, the empty one included.
This is lossy by construction for slides that
overwrite content: a `replace` destroys what it replaces, and only an explicit `handout: true`
keeps it. Animo cannot warn about this, because typst offers packages no way to emit a warning;
the manual must. A panned slide is no exception: a handout page is the viewport of its state and
not the canvas, so `handout: true` is also how a view that a later pan leaves is kept.

**The file format is not an output type.** Both static types are paged modes, and typst exports
either of them to PDF, SVG or PNG. SVG embeds a page in another document and PNG serves a
consumer that needs a raster image, and neither says anything about which pages exist.
A multi-page export to SVG or PNG requires a page-number template in the output path.

### Scoping

Tags live in the scope of their slide, with no per-slide context object threaded through
the body:

- In the **HTML** output, CSS/JS selection is scoped to the current slide's container, so
  `[data-typst-label="line1"]` in slide 3 cannot affect slide 7. Matching *all* elements
  with the same tag inside one slide is the natural behaviour of such a selector, which is
  exactly the "several places, one tag" requirement, and it is also what applies continuous
  state to every epoch rendering of the slide at once.
- In the **paged** outputs, `#slide` resolves its own animation plan before rendering its
  subslides and hands the result to the body, so each tag site sees the plan of the slide it
  sits in.

Names share one namespace with the labels Animo emits for itself, since both end up as a
`data-typst-label` in the same output and the runtime addresses what it finds there. The prefix
`animo-` is reserved for Animo's own labels, and `tag` and `region` refuse a name that starts
with it. An unnamed region needs a label of its own, because a boundary crossfades it and only
a labelled box becomes a group at all, so it gets `animo-region-<n>` with the region's own
number, which is stable across the epoch renderings of its slide. The epoch renderings
themselves take `animo-epoch-<n>` out of the same reserved prefix.

The namespace is shared with **the document's own labels** too, and that half Animo cannot
reserve: `#box[..]<x>` emits the same attribute a tag of that name does, and nothing in the
output tells the two apart. The consequence is asymmetric. Typst resolves a timeline through
the tag, so on paper a label of the document's own is never addressed, while the runtime
resolves it through the attribute, so in the browser it is. A continuous primitive on a name
that became no group on its slide is therefore refused, in every target, beside the refusal of
a `pan(relto:)` to a missing tag: a misspelt name is the likely cause, the refusal costs a deck
nothing it could have wanted, and the alternative is an operation that does nothing on paper and
something unintended on screen. What is left is a name a slide both tags and labels, which is
a collision inside one namespace and is documented rather than refused, since refusing it would
mean Animo policing the labels of the document around it.

The plan must be readable in the **HTML** output as well, because regions and implicit regions
need to measure their states while the body is laid out. There is no cycle: the plan is an
argument of `#slide` and does not depend on the body.

The plan is **provided**, not published.
`#slide` installs a show rule over its body,
and every tag emits a marker that the rule replaces with the tag's rendering for the view it is
given. A view has nine entries:

- the **position of the slide in the deck**. A tag needs it to report anything back out of the
  frame it sits in, because `query` is document-wide while a tag name means nothing outside its
  own slide. The site reports and the anchor markers a slide checks after itself are written
  this way (see *Architecture*);
- the **state index**, which is `none` in the HTML target, where a frame covers a whole run of
  states and the browser is what applies their display state;
- the **number of states** of the slide, which is how many renderings a `per-subslide` stack
  builds. It is a property of the slide rather than of the rendering, so it is the same in every
  view of one slide, the HTML one included;
- the **epoch** to lay out;
- the **content state of every epoch**, and not only of the one laid out, because a tag whose
  content changes reserves room for the largest of them, and a region measures another epoch by
  providing a copy of the view with only the epoch changed;
- the **resolved display state** of that state, keyed by tag name, holding only the tags the
  timeline addressed, so that a tag it never touched is absent from the entry and rests where
  the body put it. Every position in it is resolved to two lengths rather than kept as the
  anchor and the offset the resolver holds, because an anchor is a tag's corner and only the
  rendering knows where that is. A tag site puts on its content what it is handed and resolves
  nothing itself, which is what keeps the anchors read once per slide;
- the **names a continuous primitive addresses anywhere in the slide**. A tag site that cannot
  be animated at all has to say so in state 0 rather than in the state that moves it, and a
  `wrap: none` tag only learns that it is being animated from this entry. The target of a
  `pan(relto:)` counts, since the browser reads its anchor off the tag's group;
- the **region** the content sits in: the key of the nearest region whose footprint is the same
  in every epoch, whether an explicit region bounds it, and whether the content itself is laid out
  in every epoch. A tag inside an explicit region reserves no footprint of its own, and every
  site reports its key, which is how the regions a boundary redraws are found, since only layout
  knows which tags a region holds;
- the **tags whose display state encloses the content**, outermost first. Every site reports
  them, which is how an anchor read from inside a transformed tag is refused (see
  *Architecture*). Only a wrapped tag site and a named region extend the entry, since nothing
  else carries a display state, and only a name a continuous primitive addresses does, since a
  name the timeline never addresses can transform nothing. A deck with no continuous primitive
  therefore threads nothing and pays nothing.

A **second** marker travels beside that one, and a `per-subslide` asks through it. Two markers
rather than one, because the two are answered in different places: a tag is answered by the
body's view and refused anywhere else, where a stack is answered wherever a slide lays content
out, the background and the overlay included. What the second marker is handed is the **stack
view**, which is the part of a view that content outside the body may have: the number of states
and which of them is being laid out.

A state variable cannot do this,
because `state.get()` inside `measure(..)` resolves at the enclosing context's location,
so a caller cannot set a state, measure, set it again and measure again,
which is exactly what a region has to do to size its footprint over its epochs.
A show rule does reach inside `measure`, providers nest with the innermost winning,
and the marker's own label does not reach the output (measured; see *Findings*).
A view being an argument rather than a document position also means
that a deck wrapping `#slide` in its own function changes nothing.

Three things about a slide are published rather than provided, and none of them is the plan.
The slide counter and the flag that says whether this slide is counted are published because
`slide-number()` is an ordinary counter read that an author writes anywhere, in the body or in
a layer, and because both are constant over the slide, so nothing about them has to vary inside
a `measure`. The deck-wide step counter is published for the same reason and is read from
inside a stack. The third is the one a diagnosis needs:
`#slide` marks with a state that a body is being laid out, so that a tag outside any slide can
be diagnosed at the tag site. That diagnosis cannot come afterwards, because a marker nobody
replaced is indistinguishable from one that was (measured; see *Findings*), and a tag whose
marker is never replaced would simply drop its content.

Duplicate labels across a document are permitted by typst and cause no error.

### Output mode selection

One source file, one compile per output type. The HTML target is detected automatically via
`target()`; the two static modes are selected explicitly, defaulting to `handout`:

```bash
# HTML presentation
typst compile --format html --features html talk.typ talk.html

# Static presentation (one page per subslide)
typst compile --input animo=presentation talk.typ talk-presentation.pdf

# Static handouts (final state per slide), the default for paged output
typst compile talk.typ talk-handout.pdf

# Live preview while authoring: typst serves the HTML and reloads the browser itself
typst watch --format html --features html --open talk.typ talk.html
```

The mode and the file format are independent, so either static type exports to SVG or PNG as
well. Multi-page export to those formats needs a page-number template in the output path:

```bash
typst compile -f svg talk.typ 'talk-handout-{p}.svg'
typst compile -f svg --input animo=presentation talk.typ 'talk-presentation-{p}.svg'
```

### Consequences of confining reflow to regions

With reflow bounded by regions rather than either forbidden or global:

1. A slide with no structural operations needs exactly **one** `html.frame`, as in the first
   draft. Nothing about the simple case became more expensive.
1. The HTML and paged outputs lay out **identically**, because both reserve space for hidden
   elements and both reserve the same region footprints, measured the same way.
1. Smooth animation remains available for every continuous primitive, since within an epoch
   the frame geometry is frozen exactly as before.
1. The "occupies no space" state that the first draft dropped comes back, in bounded form, as
   `remove`, and as the initial state a `reset` declares.
   It was dropped because it reflowed the whole slide; inside a region
   that is precisely what it is supposed to do.
1. What is *not* achieved is animated reflow: content that moves because of reflow jumps to its
   new place behind a crossfade. A morph primitive is the way out, and nothing in this design
   precludes adding one later.

## Resolved Design Decisions

These were the open questions of the earlier drafts. They are settled; the evidence is in
*Findings*.

- **Is this feasible in typst?** Yes, for all three output types. The enabling mechanism is the
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

- **Why are two of the subslide numbers called `step` and `steps`?** Because a progress
  indicator is read as how far through the talk the presenter is, and that is what those two
  numbers are written for. Everywhere else in Animo a **step** is the transition from one
  subslide to the next, so the *n*-th subslide of a deck is reached by *n-1* steps, and `steps`
  counts subslides rather than transitions. These two keys are the one place where the word for
  the presenter's action names what the presenter arrives at. The alternative was `subslide` and
  `subslides`, which says the same thing and reads worse in the expression a progress bar is
  written as.

- **What does a boundary crossfade when no region bounds the change?** The whole rendering.
  A `wrap: none` tag outside an explicit region has no box, so there is no smaller area to
  hand over. The alternative is a cut, which would make one tag site change abruptly where
  every other one dissolves, and the manual says a structural step is a dissolve. The plan
  names the rendering by carrying no group for that boundary, and the runtime fades the two
  renderings into each other through the `plus-lighter` that a region crossfade already uses.
  The sum is exact in chromium 151, firefox 153 and webkit 26.5, measured on the epoch
  renderings of one frame, which is the structure the entry below rests on as well.

- **Where does the crossfade's blend go?** On the epoch renderings, not on the regions' own
  groups, with `visibility` scoping the outgoing rendering down to the regions it hands over.
  The group-level blend was the design's first answer and it could not work when it was asked:
  a slide was several frames then, and `plus-lighter` on a region's group was measured not to
  reach the frame below (see *Findings*). The epoch renderings are the outermost groups of the
  slide's one frame, which is what puts them within reach of each other, and keeping the blend
  there keeps it on the same element the boundary scopes with `visibility`. Scoping by
  `visibility` is the more important half of the pair anyway, because the containment
  outside the region does not rest on the blend at all. *Architecture* rule 2 spells the pair
  out.

- **How does a crossfade read when the region's content really reflows?** It depends on the
  change, and the split is sharp enough to be an authoring rule rather than a caveat.
  A **replacement** reads as a dissolve and is fine: one text fades out where another fades
  in, and the eye reads it as a transition. Its one flaw is repeated content, since text that
  is the same in both epochs but sits at two heights ghosts against itself and reads as
  doubled rather than as moving.
  A **small edit inside a large paragraph** reads badly. Everything after the edit shifts by a
  few pixels, and two copies of the same words a few pixels apart are an illegible smear for
  the rest of the paragraph, where the part *before* the edit stays crisp because it did not
  move. This is the case a morph would exist for, and it is why the transition strategy is a
  named, swappable one from the first release of Animo.
  Until a morph exists, the authoring advice is to put a region around what is replaced
  wholesale and to keep what merely shifts out of it.

- **Does every slide compute the union of its placements?** No. Only a slide whose timeline
  pans does. The union is the one part of laying out a slide whose cost grows with the number
  of `#place` calls in the body, and a deck that draws data as thousands of small placed marks
  is where that is felt: measured on typst 0.15.1, a slide with 10 000 placements over 20
  states took 63.9 s and 4.9 GB with the recording and 3.6 s and 1.1 GB without it. Nothing
  reads the canvas but `pan`: the viewport clips in both targets, and an offset is refused as
  a ratio, so no length in a timeline is a fraction of the canvas either. A slide with no
  `pan` in its timeline is therefore drawn identically whatever canvas it is given, which is
  what makes the saving free rather than a trade. An author who does pan and wants the cost
  gone states `canvas:`, which skips the recording as well.

- **Should the whole slide body be a region?** No. The body stays a plain layout in which
  nothing reflows, and regions are opt-in. If the body were a region, every structural operation
  would relay out the whole slide, which would break continuous animations in flight (their
  base geometry would move under them) and make the crossfade visible everywhere. Opting in
  per region also documents the author's intent about where the reflow is allowed to happen.

- **How are group-like containers and tags related?** They are orthogonal and both are kept.
  A region is the *unit of reflow and redrawing*; a tag is the *addressable handle*. A tag
  not inside an explicit region gets an implicit region of its own, so the simple case needs no extra
  syntax, and `region(name: ..)` covers the case where the container itself must be animated.

- **Is the name `group` right for the container?** No; it is called `region`. `group` collides
  with two neighbouring meanings, which are cetz's `draw.group`
  and the SVG `<g>` groups that Animo itself emits.
  The point of the construct is that it is a *bounded area* of the slide.

- **How much structure does `apply` need?** `apply(tag, ..fns)` with content-to-content
  functions only. `sanor`'s richer `case()`/`object()` machinery exists to cache object state
  across subslides, which Animo does not have: its plan is resolved to per-epoch content states in
  one pass. Named style properties would also require guessing which `set` rule a property
  belongs to, which Animo cannot do without inspecting content.

- **Where does time-dependent content live: the timeline or the body?** In the timeline, as
  `replace(tag, body)`.
  The alternative declares several content values at the tag site
  and selects among them from the timeline, in the style of `sanor`'s named cases.
  It is expressible under the measuring mechanism above, so feasibility does not decide it.
  What decides it is the interaction with duplicate tags,
  and it is sharpest in the case of the future morph:

  - Because every site sharing a tag name receives the **same** replacement content, the sub-tags
    inside it, their multiplicities and their document order match automatically between the
    outgoing and the incoming epoch rendering. That is exactly the precondition the morph's
    pairing rule needs. Per-site variants break it: two sites named `eq` could sit at different
    variants in the same epoch, so the two renderings could hold structurally different sub-tag
    sets, and the pairing becomes ambiguous in precisely the case morphing exists for.
  - Variants impose an **arity agreement** across same-named sites: every site named `x` must
    offer the variant the timeline asks for. `sanor` enforces its equivalent by panicking in
    `resolve-case`. `replace` has no such failure mode, because it hands the same content to all
    sites by construction.
  - The timeline stays a complete account of every content state. `switch("eq", 2)` says nothing
    without chasing the body.
  - `apply`, `remove` and `reset` cannot move into the body anyway, so variants would split
    time-dependent content across two places rather than unify it.

  The argument for the other side, recorded because it is real: with the content in the
  timeline, reading the body alone does not tell you how tall a region will be, since the content
  that determines its footprint is declared elsewhere. That is a legibility cost rather than a
  correctness one, and it is outweighed by the pairing property above.

  If per-site content is ever genuinely wanted, the answer is distinct tag names, not variants.

- **Does the handout show intermediate content?** Only where the timeline says so. The flag
  defaults to `auto`, which gives a page to the final state of each slide and to no other, and
  `sub(handout: true, ..)` and `sub(handout: false, ..)` override it in either direction. One
  page per epoch was considered and rejected: it makes the page count of a handout depend on an
  implementation concept (epochs) rather than on an authorial decision, and it silently inflates
  handouts for slides that merely restyle something. The manual must instead be explicit that
  `replace` and `remove` destroy content and that `handout: true` is how it is kept.

  Why a three-valued flag rather than a boolean that defaults to `false`, with the final state
  added on top: because then the final state is a rule written somewhere else, and there is no
  way to say that a slide's last state is a punchline the audience should not read ahead. With
  `auto` the flag is the whole answer, the default costs nothing, and every page of the handout
  is one a subslide asked for.

  It is a **keyword argument on `sub`**, not a free-standing `handout()` between `sub` calls.
  The same argument settles it as settles `wait:` and `hold:` under *Timing*: a marker
  whose meaning depends on its position in the block is harder to read and to validate than a
  keyword on the subslide it belongs to. It also keeps one more name out of the top-level namespace,
  and it means `sub` remains the only thing a timeline block contains, which is what lets `sub`
  validate its own arguments (see the `import *` footgun under *Findings*).

- **Can the handout keep a slide's initial state?** Yes, with `#slide(handout: ..)`.
  The flag belongs to a state, and the initial state has no `sub` of its own,
  so it is written on the slide, with the three values `sub(handout: ..)` takes.
  This matters as soon as a timeline restores what the body hides,
  since the handout then keeps the completed slide rather than the state the timeline filled in.
  The alternative was a leading `sub` carrying the flag and nothing else,
  which keeps every handout page chosen in one place.
  It does not name the initial state, though:
  it is a second state with the same pixels, which shifts every subslide index by one,
  and it has to be written `sub(wait: 0, handout: true)` to avoid a presenter click
  that changes nothing.
  The two gap numbers read the same way.
  `#slide(wait: ..)` times the entry into the initial state and `#slide(hold: ..)` the exit
  from it, so `#slide(handout: ..)` says whether that state is kept,
  and a slide's own arguments are where its initial state is spoken about at every level.
  The shorter form is also the one that is easier to explain.
  The choice also fills a gap that existed before:
  a slide with no `sub` at all could not be left out of the handout, and now it can.

- **Must the syntax become heavier (body as a function)?** No. `sanor` threads a mutable
  context through the body (`s => ([body], s)`) only because it accumulates actions while
  the body is evaluated. Animo passes the plan as an argument instead, so the body stays an
  ordinary content block, even though tags and regions now *read* that plan
  while the body is laid out.
  That read is a `context` read rather than a threaded accumulator.

- **Is a context object `c` needed?** No. It provided two things, both obtainable
  otherwise: scoping (handled by the slide container in HTML and by per-slide state in
  paged output) and a namespace for the primitives (handled by the cetz-style
  block-scoped import). Dropping it also keeps `tag` usable in any context, including
  inside `context` blocks and third-party packages.

- **How are primitives named without shadowing the built-ins?** Following cetz, the
  primitives are imported *inside* the animation block (`import anim: *`). The
  import is scoped to that block, so `move`, `scale` and `hide` keep their natural names
  there while remaining the typst built-ins everywhere else,
  including in the slide body, where authors legitimately use `#move`, `#scale` and `#hide`.
  Note that `region`, `tag` and `slide` are body-level names
  and are imported at the top level as usual.

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

- **Is the max-footprint rule tolerable?** Yes, with the authorial remedies, and there is no
  "pin the footprint to state *i*" option. On a region that grows from one line to a five-item
  list, `align: bottom` turns the gap into spacing above the line, and a given `height` clips the
  larger states without any sign, which is all a pin option would do. `align` defaults to `top`
  rather than `top + left`, because a horizontal component overrides an inherited alignment
  (see *Findings*).

- **Does `layout(size => ..)` give a region the right width?** In a container with a width of
  its own, yes; in one that takes the width of its content, it hands over the whole body width,
  and nothing at the region can tell. That is a documented restriction with `width:` as the
  remedy (see *Findings*). Regions are numbered in document order within a rendering, a region
  inside changing content borrowing the key around it, so the numbers agree across epochs.

- **Is the name appropriate?** `animo` is unused on Typst Universe.
  The name refers to its Latin interpretation.
  *Animo* is at once the first person singular of *animare*, "I bring to life", and the
  ablative of *animus*, "with mind, with intent",
  which states the package's position in a single word:
  an animation earns its place on a slide when it is put there deliberately,
  and so does everything else on that slide.
  Anything added without a reason competes with the speaker for the audience's attention.

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

- **Is the Web Animations API the right driver, and what are the easing and duration
  defaults?** Yes, and 400 ms with `ease-in-out`. A step writes the state's display state as
  inline style on the tag's inner group and animates from what the element was showing to that,
  so the style is the state and the animation is only the route. Reversible stepping, an
  interrupted step that continues from where it is, and a deep link that needs no transition to
  suppress all fall out of that rather than being arranged; CSS transitions handle none of the
  three well. It is also what makes a mid-flight assertion reproducible, because a test pauses
  the animation and states a `currentTime` instead of racing it, and it is where an operation's
  own `duration:` and the epoch crossfade's shared clock belong. The two values live in CSS,
  as `--animo-primitive-duration` and `--animo-easing` on `:root`, which is what lets
  `prefers-reduced-motion: reduce` set the duration to zero; the deck writes them there from
  its show rule arguments, so an author states them in typst and not in a `#slide` argument.
  A duration of zero is a step that snaps, which is the same path a deep link takes.

- **How does an author state the deck's tempo?** As three arguments of the deck's show rule,
  `primitive-duration:`, `transition-duration:` and `easing:`,
  which the deck writes into the `:root` block of its own stylesheet beside its geometry.
  The values have to end up in CSS, because
  that is the only form `prefers-reduced-motion: reduce` can reach and because the runtime
  reads them at every step, so restating one costs no second pass over the timeline. Leaving
  the author to write that CSS was the first answer, and it was wrong on two counts. Writing a
  `<style>` element from typst means calling `html.elem`, guarded by a `target()` test because
  the paged outputs have no `html` module, which is markup in a deck's source and a guard an
  author has to know about. Such a stylesheet also lands after animo's own, where it outranked
  the reduced-motion query in chromium 151 and firefox 153, so a deck that restated its tempo
  quietly took the guarantee away from the reader. Making the query's two declarations
  `!important` settles both that stylesheet and the deck's own block, because the guard then
  wins by cascade weight rather than by source order. An easing is checked against a list of
  five names in typst rather than passed through, because a timing function the browser
  rejects throws where the audience can see it, and because the list is what a reference page
  can state. The principle is narrow: every setting animo's own runtime reads is stated in
  typst, which is not a promise to expose the page's styling, and `html.elem` stays available
  for what animo does not cover.

- **Where are `transform-box` and `transform-origin` written?** By the runtime, on the slot it
  is about to transform, and never as a rule in the stylesheet. The first answer was a single
  rule, `.animo-canvas [data-typst-label] > g`, which is the selector the continuous properties
  themselves are written through, and it was wrong for a reason that took a deck to notice: the
  two declarations re-anchor the element's own `transform` attribute as much as the properties
  beside them (see *Findings*), and a labelled group is not always a tag site. A region's
  footprint carries a label too, because the crossfade addresses it, and its children are the
  author's content rather than a slot, so the rule reached typst's glyph runs and moved each of
  them by its own fill box. Every candidate selector that excludes a region's children is a
  guess about the shape of content Animo does not build: `:only-child` fails on a region holding
  one group, and `:not([transform])` would exclude a real slot the moment an inline footprint
  offsets one. Writing the two declarations where the transform is written needs no such guess,
  because the element is the one the runtime already holds. They are not tunable the way the
  duration and the easing are, so nothing is lost by taking them out of the stylesheet.

- **How do CSS-animated typst SVG groups look in motion?** Well enough that nothing about the
  defaults changes. Measured in chromium 151 and firefox 153 (see *Findings*): a scaled glyph
  is drawn afresh at the scale it ends up at rather than stretched, so text stays as sharp at
  200% as at its own size, and strokes scale geometrically with it, which is what a figure
  wants and what makes `scale` usable on text after all. A value under a running animation
  rasterises bit for bit as the same value in a style declaration, so the hand-off at the end of
  a step is invisible and there is no antialiasing seam at a subslide boundary. What a `scale`
  does still has to be understood rather than merely accepted: it is about the element's own
  centre and nothing reflows, so a doubled paragraph overlaps its neighbours.

- **What does a handout page of a panned slide show?** The viewport of its state, exactly as the
  presentation shows it, with no `#slide` argument. A page showing the whole canvas scaled to fit
  was the alternative: right for a deck that pans, and wrong for every slide whose canvas is merely
  a little larger than its viewport. `sub(handout: true)` already keeps any view a later pan
  leaves, and the manual says plainly that the handout does not show the canvas.

- **Do the two resolutions of `pan(relto:)` agree?** Yes, to within the rounding of the
  measurement, once both read the same point. Over ten kinds of tag site (placed, inline phrase,
  inline box, block, centred figure, math, heading text, grid cell, list item, a tag inside a
  tag), at windows 1280 and 640 pixels wide, the browser's pan differs from typst's by at most
  0.001 pt in chromium 151 and 0.005 pt in firefox 153. Reading typst's own position of the tag
  did not agree: it was a box height too low for every tag on a line. So the answer is neither a
  tolerance nor an authoritative target. `relto` promises the corner of the tag's wrapper, and
  each target is built to read exactly that (see *Architecture*).

  **And do they agree about a `move`, which reads two anchors and subtracts them?** Yes, and an
  order of magnitude closer: at most 0.0005 pt over the same ten kinds of site, at the same two
  window widths, in both engines. The disagreement does enter twice, and one of the two anchors
  is that of the tag being transformed, which is the case an inline site makes awkward; neither
  costs anything measurable. The figure is smaller than the one above because it is a different
  measurement rather than a better mechanism: the runtime's own `translate` is read here, in the
  user units of the frame, where a pan is read off two boxes on the page. So 0.005 pt is what
  reading a rendered pan costs, and 0.0005 pt is what the two resolutions themselves differ by.

- **Can a tag over raw cetz draw commands be made to work?** No, and Animo refuses it rather
  than ignoring it. A draw command is an array of closures built where it is written, a canvas
  body cannot hold content at all, and a tag reaches its plan through a marker element and a
  show rule, so there is nothing in the stream for the mechanism to attach to (measured; see
  *Findings*). No other channel exists either: `state` cannot vary inside `measure`, which is
  the same finding that made the plan provided rather than published, so varying the array per
  epoch would mean re-evaluating the block that built it. That is precisely the threading
  this document rejects elsewhere, `s => ([body], s)`, and it is how `sanor` reaches the
  same case.
  Handing the body back untouched was the earlier behaviour and made every primitive a silent
  no-op, which is a poor diagnosis: the symptom surfaces three tools away from its cause.
  The question of what a tag should do around a *state-changing* command (`stroke`,
  `set-style`) lapses with it, since neither kind is reachable. What remains for the author is
  a canvas written as a function of what it draws and tagged whole, which changes the geometry
  at the granularity of the canvas, and a `content()` element for anything that has to animate.
  A per-epoch canvas body would recover the per-object granularity, and that is left for a
  later release.

- **Do implicit regions behave acceptably inside cetz canvases and math?** Yes, and better
  than expected, because the surrounding layout not being a flow is what makes it
  work rather than what breaks it. Inside math, a tag reserves the width of its widest epoch,
  so the equation has the same width in every epoch and does not shift: measured on a centred
  display equation whose tagged term grew from `b` to `beta + gamma + delta`, where the `= c`
  after it did not move by a pixel. Inside a cetz canvas the same reservation keeps the figure
  rigid, since cetz measures the tag's box and that box is the same in every epoch: measured on
  a centred canvas whose label grew by a factor of five, where the circle and the line stayed
  put and the canvas kept its extent. The cost is the one the max-footprint rule imposes
  everywhere, a gap while a smaller epoch shows, and the remedy inside a canvas is the anchor
  that decides which way the label grows. Nothing here needed a special case, so none was
  added; the manual states both, together with the region around the canvas as the way to let
  a figure change size after all.

- **Is `sub` the right structure?** Yes. A code block of `sub(...)` calls joins into a
  list of subslides. It already carries `handout:` and took `wait:` and `hold:` in the same way.
  Dropping `c` makes the primitives free functions returning plain data, which is easier to
  inspect, test and extend than methods on a context object.

- **What does a realistic deck cost to compile?** About twice a plain typst deck, and the
  live preview loop costs a tenth of a cold compile, so Animo is not slow.
  Measured on `examples/tour.typ`, 13 slides with 41 states and 17 epoch frames,
  on an i7-1260P with typst 0.15.1: 0.29 s for the HTML presentation,
  0.29 s for the static presentation, 0.25 s for the handout, and **34 ms** to
  recompile after an edit to one slide under `typst watch`, which memoises across recompiles.

  The overhead over the same content laid out as plain typst pages is **2.0** for a deck with
  no structural subslides, **2.2 to 2.6** for two to eight epochs a slide, and **5.4** for a deck
  with regions, epochs and continuous subslides throughout. The terms behind it, each measured as
  the difference between two decks that differ in one knob: one more epoch on one slide costs
  5 ms in HTML, and one region measuring one epoch costs 1.3 ms of prose.

  The one expensive construct is a **cetz canvas inside a region**, at 8.8 ms per epoch
  measured, seven times the prose figure, which took a twelve-slide deck over four epochs to
  5.0 s against 0.08 s for the same drawings as plain typst. That is the cost of letting a
  figure change size, it is the cost the region design predicts, and both remedies are
  authorial: leave the canvas outside a region to keep it rigid, or give the region a `height`,
  which skips the measuring and took the same deck to 1.2 s. Nothing here asks for a change to
  the design; `docs/performance.md` says it to authors instead.

- **Is gzip enough for the page weight, or is the shared-defs hoisting needed?** Gzip is enough,
  and what was to follow it turned out to be two things rather than one. Hoisting the
  shared definitions into a document-level `<svg>` is sound in the browser and **unreachable
  from inside typst 0.15.1**, because a package never holds the markup a frame became; what is
  reachable is one frame per slide holding a rendering per epoch, which makes typst's own
  deduplicator share the definitions of a slide's epochs. *Findings* measures both, and the
  reachable half is specified under *Architecture*, since it changes what an epoch frame is
  rather than only how many bytes one weighs. The tour is 1.08 MB, which gzip takes to
  **222 KiB**, a factor of five, and every extra epoch on a slide adds 73 KiB raw or 14 KiB
  compressed. A deck that transfers 222 KiB is a small web page, so nothing here is urgent.

  What is worth recording is that gzip does **not** recover the duplication, which the question
  as posed left open. Definitions are 59% of the tour's page and 37% of it is definitions that
  appeared in an earlier frame, and dropping those repeats saves **44% of the gzipped page**.
  The reason is that deflate's window is 32 KiB while an epoch frame
  carrying a heading and one sentence is already 45 KiB, so a definition repeated in the next
  frame is out of reach whatever sits between (measured; see *Findings*). The two facts are
  therefore independent: compression is worth a factor of five on a deck, and hoisting is worth
  a further factor of two on top of it.

- **Can `hide` and `remove` be one primitive, with the reflow inferred?** No, and the obstacle
  is the order in which a slide is built rather than a judgement about the API. The two differ
  only inside an explicit region, so the inference would have to read whether the tag
  sits in one.
  Where a tag sits is a *layout-time* fact,
  while the plan is resolved *before* the body is laid out,
  because the body's layout depends on its epochs. Nothing in the timeline can stand in for
  it: the resolver never sees the body. The two escapes are both worse than the problem. Making
  the merged primitive always structural puts a fresh epoch behind the most common animation in
  a deck, which roughly doubles the frames and the page weight of an ordinary slide. Making it
  always continuous deletes `remove`, which regions were what made meaningful in the first place.

  There is a second reason, independent of the first, and it survives even if the ordering ever
  changes. The two write to **different slots**: `hide` sets display state, `remove` sets content
  state, and *Animation primitives* has them composing independently by design, so a tag may be
  hidden and removed at once and `reveal` and `reset` undo different things. One name covering
  both would make `hide(reflow: true)` followed by `reveal()` a near-no-op that reads like an
  undo. So `hide`/`reveal` and `remove`/`reset` stay four names, and the guidance stays the one
  already under *Animation primitives*: outside an explicit region, `hide` is the right
  primitive, because `remove` there costs an epoch and buys nothing.

- **Where does a tag's initial state live: the body or the timeline?** The timeline, inferred
  from the first operation that addresses each of the two slots. A name whose first display
  operation is `reveal` starts hidden, and one whose first content operation is `reset` starts
  removed. An earlier draft declared both at the tag site, as `hidden:` and `removed:` arguments
  of `tag`, and those arguments are gone.

  What decides it is that the site arguments made an author keep two places in sync for one
  fact. Nothing can usefully start hidden without a `reveal` somewhere, and nothing can usefully
  start removed without a `reset`, so the timeline already carried the information and the
  argument repeated it, once per site of the name. The repetition was the common case rather
  than an edge one: of the 55 `tag` calls in `examples/`, 37 carried `hidden: true` and 5
  carried `removed: true`. The inference was checked against every tag site in `examples/`,
  `docs/`, `tests/documents/` and `probes/documents/`, and it reproduces the state each argument
  declared, with no site needing an escape hatch. A `reset` that undoes an `apply` or a
  `replace` rather than a `remove` is unaffected, because the first content operation on such a
  name is the `apply` or the `replace`.

  Four things go with the arguments. The agreement check between the sites of one name
  disappears, because sites cannot disagree about something no site states. The refusal of
  `hidden: true` on a `wrap: none` site disappears, because a `reveal` on a name that became no
  group is refused already. The `hidden:` field on the site reports and the anchor markers
  disappears. And the resolver resolves state 0 like every other state, so the tri-state that
  meant "no `reveal` and no `hide` has happened yet" becomes a plain boolean, and no display
  state is read at a tag site at all.

  The cost is accepted rather than mitigated. `reveal` and `reset` stop being pure undos, so a
  `reveal` on a name that nothing hid changes the first subslide where it used to change
  nothing, and Animo cannot diagnose it, because every timeline yields an answer. Such a mistake
  surfaces as an element missing from the first subslide rather than as a refusal. This is the
  one place where Animo guesses instead of refusing, and it is accepted because the refusals
  elsewhere are about what an author cannot have meant, while here every reading is meant by
  somebody.

  The alternative considered was keeping the arguments and shortening them with exported `htag`
  and `rtag` partials. It was rejected twice over: it leaves the two places to keep in sync, and
  `tag.with(hidden: true)` gives an author the same shorthand in one line, the way
  `box.with(..)` and `text.with(..)` already serve `wrap` and `apply`.

- **Should there be a `once` primitive?** No, and it is dropped rather than deferred. The idea
  was `sanor`'s: make something true for exactly one subslide, revealing and hiding it again, or
  applying a wrapper and dropping it.
  It is not hard to resolve, because the resolver is a forward pass
  and could perfectly well write the undo into the next state. What rules it out is that there is
  no single thing it could mean. Reveal-then-hide and reset-then-remove are both "once", and by the
  entry above nothing can choose between them without an argument; an `apply`-then-drop form is a
  third meaning, needs identity in the wrapper list so that only its own wrapper is dropped, and
  costs two epochs where the display form costs none; and each of them needs a rule for a `once`
  in the last `sub`, which has no next state to undo it in. That is a cluster of optional
  arguments standing in for two lines an author can already write, `sub(reveal("x"))` and
  `sub(hide("x"))`, which say exactly which of the meanings was wanted.

- **How does `move` say where something goes?** The same two ways `pan` does, and for the same
  reason: `x`/`y` place, `dx`/`dy` shift, `relto` names another tag to place against. The earlier
  `move(tag, x:, y:)` was a shift only, so "put this label where that node is" had to be computed
  by hand from a layout the author cannot see, and it stopped being right the moment the slide was
  edited. Sharing the vocabulary with `pan` costs nothing, because the resolver already keeps a
  pan as an anchor and a per-axis offset and the runtime already measures a tag's anchor for
  `relto`; `move` differs in one term only, subtracting the moved tag's own anchor. The price is
  in *Animation primitives* and is stated there: a name with several sites lands its first site
  on the target, and an element that is also scaled lands its unscaled corner, because a scale is
  about a centre.

- **Does a scale factor multiply into what is there, or set it?** It sets it. Multiplying was the
  earlier answer and it makes a factor unreadable in isolation: `scale("a", 2)` at subslide 7 means
  nothing until every earlier `scale` on `a` has been found and multiplied, and returning an
  element to its own size means writing a reciprocal that changes whenever an earlier subslide does.
  Setting makes `scale("a", f: 1)` the restore, whatever came before, and it is what makes the
  primitive agree with `move`, whose absolute form is likewise idempotent. Successive growth is
  the case multiplication served, and it is a product an author writes once. `f` is the isotropic
  factor and `fx`/`fy` the per-axis ones; combining `f` with either is refused rather than
  resolved by precedence, since a call that gives both says two different things, while an axis
  the call omits keeps whatever factor it had.

- **What may a background hold, and where does an overlay go?** Either may be a colour or
  arbitrary content, and both belong to the **viewport**. Extending `background` from a colour or
  an image to content costs nothing,
  because *Architecture* rule 5 already had a content background as a
  frame of its own beside the canvas, and `overlay` is that same construct one layer up. Making
  them viewport-bound rather than canvas-bound keeps a logo in the same place on screen instead
  of letting it travel with the canvas, keeps a full-bleed image from silently enlarging the
  automatic canvas, and keeps
  a colour and a content background behaving identically under a `pan`. Rendering them **once per
  slide** rather than per epoch is the other half: neither may hold a tag or a region, so neither
  can depend on an epoch, and drawing them once keeps them off the epoch cost curve. It does not
  keep them to one value per slide, which an earlier draft of this document concluded from it:
  see the numbering entry below, which makes a layer the cheapest place for a subslide number
  rather than a place one cannot go. Tags and regions are refused there rather than ignored, for
  the reason *Tags* gives for raw cetz draw commands: a silent no-op is a poor diagnosis.

- **What happens between two slides?** A crossfade, or nothing. `#slide(transition: auto)` is the
  default and crossfades; `transition: none` cuts. The boundary takes the setting of the slide
  being **entered**, in both directions, so stepping back over a boundary undoes exactly what
  stepping forward over it did, and the setting is written on the slide it is about, not on the
  slide that happens to precede it in the file. The mechanism is the one the epoch crossfade
  already proves, `plus-lighter` on the two containers inside an isolated stacking context, which
  is what keeps two opaque backgrounds from dipping halfway through. Two slides are laid out
  while they cross and no more, because laying every slide of a long deck out for the whole
  session costs it seconds of first paint (see *Findings*). The length is the deck's
  `transition-duration:`, 0.4 seconds, beside `primitive-duration:` and `easing:`:
  a deck with nothing but hard cuts sets it to zero, `prefers-reduced-motion: reduce` does
  the same, and `transition: none` and a zero duration take one code path. Richer transitions
  (a wipe, a push) are left for later, and the argument is already open to them: beside the
  typst literals `auto` and `none` it takes the name of a strategy, so a second
  one is a value added to a list rather than a change of what the argument takes. The list of
  names lives in typst rather than only in the runtime, because a misspelling has to be refused
  at compile time: a name the runtime did not recognise would be a slide that quietly took the
  default.

- **Where does the timing of an automatic step go, and can one operation start late?** On either
  side of the gap it times, and yes. The three knobs are `wait:`, `hold:` and `delay:`, and
  *Timing* states them. `wait:` names the gap before the subslide it is written on and `hold:`
  the gap after it, both at both levels, and a slide's initial state is timed by
  `#slide(wait: ..)` and `#slide(hold: ..)` because it has no `sub` of its own.

  Only `wait:` was in the first draft, which stated the rule as the delay before a subslide on the
  grounds that a "hold this state for *n* seconds" keyword would need two slide-level names to
  cover a slide's first and last states, and recorded as a real cost that the other form
  survives editing better. Using the package is what reopened it. Two of the three grounds did
  not survive. The two-keyword claim is wrong: `#slide(hold: ..)` times state 0, every later
  state is a `sub` that carries its own, and the last state of a slide with no `sub` at all *is*
  state 0, so one slide-level keyword covers it either way. And the coverage `wait:` alone was
  supposed to buy is not there: `#slide(wait: ..)` on the first slide of a deck does nothing,
  because a gap is read when its state is entered from a predecessor and state 0 of slide 1 has
  none. What is left is that the two forms are natural for different sentences and fail in
  opposite directions when a timeline is edited, which is why both are implemented.

  **One gap takes one number**, and a gap that both of its neighbours time is refused rather than
  summed. *Timing* states why, and the part that belongs here is the order of the two decisions:
  a refusal can be widened into a sum in a later version without breaking a deck, where a sum
  cannot be narrowed into a refusal without breaking several. Nothing about the runtime changes
  with the second keyword, which is what made this cheap: the plan carries both numbers per state
  and the runtime reads whichever of the two was written.

  **A backward step turns the clock around**, which is the other thing using the package turned
  up: a deck that played itself forward over a run of gaps has to come back over the same run, and
  the state a backward step lands on arms the gap that step just came over. The clock therefore
  steps the deck whichever way it is travelling, and the travel ends where the presenter would
  have had to press a key. The first state of a deck is the one place the clock is stopped
  instead, because nothing earlier is there to travel to. A forward step and `Space` both put that
  clock back.
  A pending timer is cleared by any manual step, so autoplay never races the presenter, and the
  pause never enters the fragment: it is the one piece of runtime state the URL does not carry.

  `delay:` is a separate name because it times an operation rather than a subslide,
  it becomes the Web Animations API effect's delay so the subslide keeps its one clock,
  and on a structural operation it holds back the crossfade of the region it changes,
  which is why two operations changing one region at one boundary may not disagree about it.

  **A backward step mirrors that schedule rather than replaying it**, which is the third thing
  using the package turned up. The first rule was the replay, on the reading that an operation
  which arrived late should leave late, and presenting a slide of three lines staggered by
  `delay:` showed what it does: the line that arrived first leaves first, so the build comes
  apart in the order it was built up and takes the composition through pictures the forward step
  never showed. Mirroring each operation about the length of its step is what makes the two
  directions one motion seen from two ends, and it costs the plan one number per timed step,
  because the length of a step cannot be computed in the browser out of the operations that
  reached it: an operation that states nothing carries nothing. *Timing* states the rule and
  *Architecture* what travels.
  All of them are plain numbers of seconds, since typst has no time literal and `2s` does not
  parse.

- **Does an operation get a duration of its own, and in what unit?** Yes, `duration:`, beside
  `delay:` on every primitive, defaulting to `auto`, and in seconds like everything else an
  author writes. It was queued as `time:` and moved into Animo once `delay:` had built its
  plumbing, because the plan carries per-operation timing to the browser either way and the Web Animations API takes a duration exactly where it takes a delay.
  The name is `duration:` rather than `time:` because it sits beside `delay:`, where `time:`
  reads as a moment rather than as a length, and because it is the quantity
  `--animo-primitive-duration` already names.
  Three things decided with it are the reason this is an entry rather than a line.
  **The unit is seconds**, not a multiple of `--animo-primitive-duration`,
  so that two numbers on one call mean the same thing by the same number;
  the multiple was the tempting form, because it makes the next point arithmetic instead of a
  rule. **Reduced motion still takes precedence**: a zero
  `--animo-primitive-duration` zeroes every explicit duration, in the runtime, because a media query
  cannot reach a number written in a typst source, and a reader who asked for no motion should
  not have to ask a second time. `auto` rather than a number as the default is what keeps
  "unset" and "as long as the deck's own step" distinguishable,
  which is what a deck-wide restyle needs in order to reach the operations that said nothing
  and leave the ones that did alone.

- **How is a slide numbered, and can a subslide be?** Both, with `slide-number()`,
  `slide-count()` and `per-subslide(f)`, and the subslide half works by rendering every value
  rather than by substituting one. *Slides* states the surface; this entry is why it has that
  shape.

  The obstacle was stated correctly and the way around it was not. An HTML frame covers a whole
  run of subslides, so a number chosen when the frame is rendered is one number for all of them,
  and rendering one frame per subslide would destroy the cost model. The earlier draft's three
  ways out were to ship neither name, to ship the slide number alone, or to find a form in which
  the number is "a runtime value the browser substitutes rather than rendered ink". Substituting
  a value is the bad half of that third option: typst emits glyphs as `<use>` references into
  per-frame `<defs>`, so a runtime that wrote a number would be rewriting glyph references by
  their hashed identifiers, which is the markup the shared-`<defs>` hoisting rewrites.

  What works needs no new mechanism. Typst renders **every** value and the browser chooses which
  one is shown, which is exactly what `reveal` and `hide` already do. So a number is
  a stack of renderings with a label each, and the runtime shows the one belonging to the
  position it is on, while a page of a paged output lays out the rendering of its own state.
  The three output types then agree by construction rather than by arrangement, and nothing
  about a number travels in the plan.

  **An overlay is the cheapest place for it, not an impossible one.** A layer is one rendering
  per slide where the body is one per epoch, so a stack costs once in a layer and once per epoch
  in the body. Measured on the controlled deck at its realistic point, a slide number and a
  subslide number in an overlay cost 3% of the raw page, 4% of the compressed page and 5% of the
  compile time, with the plan attributes byte-identical. The same stack built by hand out of
  tags and `reveal`/`hide`, which an author could already write, doubled both the plan and the
  compile time, which is what settled on a reserved label over a generic display state.

  **Why a callback rather than a `subslidenum()`.** The machinery is the same either way, and
  the callback is what makes a progress indicator possible at all: in HTML there is no integer
  at layout time to compute a bar's width from, only a rendering per state. One name in the
  manual therefore covers a number, a "3 of 6", a row of dots and a bar. It also puts the
  deck-wide pair, `step` and `steps`, where a bar spanning the talk can reach them.

  **Numbering epochs instead was rejected.** It is free, because a frame knows its own epoch,
  and it fails what a number is for: it does not advance on a continuous subslide, so it is constant
  on the ordinary slide that only reveals things; it makes `hide` versus `remove` visible to the
  audience, which is the objection that keeps epochs out of the handout under *Does the handout
  show intermediate content?*; and it would stand beside the `slide.state` of the fragment as a
  second numbering system. Nothing named `epoch` is in the public surface.

  The purpose is worth stating, since it decides the trade-offs above: a number is there so that
  someone in the audience can ask about a particular moment of a talk, and so that the speaker
  can find that moment again. An exactly correct subslide number is a means to that and not the
  end. It turned out to be affordable, so the question of an approximate one lapsed.

- **Testing strategy.** Three tiers, with the weight on the cheapest, under one runner:

  1. typst-level `#assert` on plan resolution (compile only, no export): per-state content and
     display state, epoch boundaries, epoch counts, and the footprint chosen for each region.
     These documents are compiled, so footprints come from real `layout` and `measure` calls.
     Nothing is written out and no raster or PDF is produced.
     `slipst` does this inline in `utils.typ`. Because `replace`/`apply` payloads are content
     and functions, assertions target the resolved structure, not the payloads.
  1. Rasterised comparisons of the presentation and handout outputs.
  1. Headless-browser checks of the HTML output. Subslide state must be addressable by URL
     (as in `slipst`'s `#slip-alter` hash) so tests can deep-link, and numeric assertions on
     geometry are more robust than pixel comparison.

  Two invariants are cheap to test in the browser and worth testing directly, because the
  region design rests on them:

  - the bounding box of every label *outside* a region is identical in all epoch renderings of
    a slide, read per rendering with `getBBox` mapped through `getScreenCTM` and not with
    `getBoundingClientRect`, which the engines disagree about on a group (see *Findings*).
    The region's own group is not one of these: a group's box is its ink, and the ink inside
    a region is exactly what an epoch changes, so what a region promises is its corner;
  - the rendering is pixel-identical outside the region between epochs, and stays so
    mid-crossfade, with every raster of the mid-crossfade comparison taken while the step is
    in flight (see *Findings*).

  Both are comparisons *within* one page load, so they need no stored reference images and are
  unaffected by glyph rasterisation changes. Stored image snapshots are brittle across typst
  versions and stay the exception. The runner, the tools and the reference-image policy are
  settled in [docs/testing.md](../docs/testing.md); `tytanic` is the ecosystem convention there
  and was rejected only because it cannot see the HTML target at all.

## Open Questions

These need the prototype to answer.

- **How exact is the automatic canvas?** Settled: the approximation stays, and its error is
  documented in both directions rather than reduced. The `show place:` rule fires for *every*
  placement, including one nested inside a `box` or a grid cell, where `dx`/`dy` resolve
  against that container rather than against the canvas, and the rule cannot tell the two
  apart (measured; see *Findings*). Counting only the placements Animo can attribute to the
  slide body was the alternative, and it has no mechanism behind it: `layout(size => ..)`
  inside the rule reports the container exactly and breaks the paragraph the placement sits
  in, and a nesting depth kept in a state reads zero for a placement inside another
  placement, which is the shape real decks are written in, and would read every placement
  inside a tag as nested, since a tag site is a box (measured; see *Findings*). What the
  approximation costs is therefore stated instead: a nested offset is counted short by
  wherever its container sits, a nested alignment is counted *long* from the body box, and a
  ratio-sized body contributes nothing at all, which is the one inexactness that bites at the
  top level too. An explicit `canvas: (width: .., height: ..)` is the escape hatch for all
  three.

- **Does autoplay want a pause key?** Settled: yes, on `Space`, and the pause does not survive a
  reload. A gap advances on a timer, and a manual step clears the pending timer and re-arms from
  the state it lands on, which is enough for a presenter who wants to run ahead and not for one
  who wants to stop and take a question, nor for the reader this is really for: someone watching a
  deck that plays itself, who wants to stop it the way they stop a video. `Space` toggles the
  clock while a timer is pending or the deck is already stopped, and steps forward otherwise, so
  the forward key that every presentation remote sends is unchanged on a deck with no number in
  it. Resuming puts back what is left of the wait. The other two ways out were rejected on what
  each would cost: leaving it out serves the presenter and not the reader, and putting the pause
  in the hash would make the fragment something other than a position, and a shared link say that
  a deck is stopped. So the pause stays the one piece of runtime state the URL does not carry, and
  the runtime publishes it as `data-animo-paused` on the root element for whatever wants to show
  it. *Timing* states the rule.

  A second way into the same stop was added after the package was used: **a backward step stopped
  the clock**, because arming the gap it just came over would carry the deck forward again, and
  that gap can be zero. A gap of zero then needed a second answer beside the stop. The stop made
  such a gap walkable and left the presenter resting on a state the audience had only ever seen in
  passing, one press per join. So **a backward step walks back to the nearest earlier state the
  deck would rest at**, which *Timing* states.

  Presenting a deck with a short gap across a slide boundary reopened the stop. The walk crosses a
  gap of zero and nothing else, so a gap of a third of a second left the presenter one press back
  on a state the audience had seen for a third of a second, and a second press was needed to reach
  the state they had left. A floor under the walk was rejected when the stop was written, and is
  rejected still. A floor is a magic number, and zero is what an author types to say that a state
  is not a stop, where a tiny number beside it says the opposite just as deliberately. What
  replaced the stop needs no number. **The clock steps the deck whichever way it is travelling**,
  so a run of automatic gaps is crossed back the way it was crossed forward and the travel ends
  where the presenter would have had to press a key. The cost is that a deck which times every gap
  travels back to its first state. That is accepted, because such a deck plays itself forward to
  its last state as readily, and `Space` stops it either way. The stop keeps the one case the travel cannot
  answer, the first state of a deck. The two stops publish the same attribute and are told apart
  only by what puts them back, a forward step resuming the one and leaving the other stopped.
  *Timing* states those rules too.

  **The pause stops the motion as well as the clock**, which the same use of the package turned
  up: a pause that let the step in flight run on to its end moved the picture after the key was
  pressed, where a reader who presses a pause key means the picture they are looking at.
  Every animation the key finds in flight is paused where it is and picked up from there, which
  the Web Animations API does on its own, and a step the presenter makes by hand while the deck is
  paused is left alone.

  What the walk left behind, and what presenting turned up after it, is that a join running out
  of a slide leaves the slide it walks back into below its own last state. The way back now
  moves that slide into the state it lands on while the boundary crosses it, rather than
  snapping it into place under the crossfade, and only a backward step does so. *Timing* states
  that rule as well.

- **May an operation's duration run past the subslide it is in?** Settled: it may, and the
  boundary stretches with it. For a continuous operation nothing was in question: an
  interrupted animation continues from where it is, by *Architecture*, which is already what a
  gap shorter than a subslide's motion does. The structural case was the open one, because an
  epoch boundary lasts until the last of its crossfades has finished, so a long duration holds
  two frames laid out for as long as it runs and two boundaries can be in flight at once, which
  is a state the epoch model had never had to represent. What decided it is that the state is
  reachable without a duration at all: a deck that staggers a long `replace` against a fast
  timeline reaches it, and so does a presenter clicking twice, with numerically the same result
  (measured). Clamping a structural duration to its subslide and refusing one that outlives it were
  the other two ways out, and both can only be written against the gap that follows the subslide,
  since a click has no length, so each would remove one way in and leave the state. What the
  overlap needed instead was an answer in the runtime, which *Architecture* rule 2 now states:
  every frame that is not the one being entered hands its carried regions over on the new
  boundary's clock, so the region's ink stays at one rather than dipping to the fraction the
  interrupted crossfade had reached. The same answer repairs the dip that a short gap
  already produced.

- Whether a FLIP morph should ever scale. Non-uniform `scale` distorts glyph strokes, so text
  morphs probably want translate-only, with the size change carried by the crossfade, leaving
  scaling for figures. This has to be seen in motion before it is decided; the extra nested box
  under *Findings* is needed either way, since the two slots are separated by coordinate space
  and not merely by how many properties each one uses.

## Development Infrastructure

Not part of the feature design, but recorded here because much of it is constrained by the design,
and because two parts of it impose requirements back on the package: the live preview needs the
runtime's state to be addressable in the URL, and Universe needs the version number to be correct
in every example.

Most of it is no longer a plan but a working repository, described where a contributor meets it.
This section keeps only what the design decides.

| Subject                                             | Where it is written up                                                |
| --------------------------------------------------- | --------------------------------------------------------------------- |
| Environment, the two import paths, version numbers  | [docs/environment.md](../docs/environment.md), `snipwise.md`          |
| The three test tiers, the engines, reference images | [docs/testing.md](../docs/testing.md)                                 |
| Continuous integration                              | [docs/testing.md](../docs/testing.md)                                 |
| Probes, and what to do when one fails               | [docs/probes.md](../docs/probes.md)                                   |
| The live preview loop                               | [docs/presenting.md](../docs/presenting.md)                           |
| What a deck costs, and where the numbers come from  | [docs/performance.md](../docs/performance.md), `benchmarks/README.md` |
| The public surface, name by name                    | [docs/reference.md](../docs/reference.md)                             |
| Where the specification lives, for a contributor    | [docs/development.md](../docs/development.md)                         |

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
└── tools/        the build and release scripts
```

One rule of the Universe submission guidelines shapes the package itself rather than the release
path: every example, including the ones in the README, imports `@preview/animo:X.Y.Z` rather than
a relative path, so that a reader can copy any file and compile it. Keeping those strings correct
is `snipwise`'s job.

A submission cannot be withdrawn: publishing a first version commits to the name and to that version
number for good. It does not commit to the API. Animo is not API-stable before 1.0, and
saying so plainly is better than a promise that real use would break anyway, because nobody
knows yet what real use turns up. What the intention means is that a break has a real cost:
it rewrites decks that already exist. That, and the irreversibility of the
submission itself, is why the last step of the release path stays manual.

### The state the runtime has to expose

`typst watch` serves the HTML and reloads the browser itself (see *Findings*), so Animo ships
nothing for live preview. What it does require is that the runtime keep the current slide and
subslide in `location.hash` and restore from it on load, which the testing strategy wants anyway,
for deep-linking. Two consequences:

- the restore must *snap* to the state rather than animate into it, which is one more argument for
  driving animations through the Web Animations API;
- the hash must be written with `history.replaceState`, or every subslide leaves a browser
  history entry behind.

Narration audio, should it ever be added, is silent on a restore.
The reload is what makes that rule an everyday case rather than an edge case.

### Task layer

Everything is a command a contributor can type, and there is no build tool between them.
`pytest`, `pre-commit`, `zensical` and `typst watch` are invoked directly,
and what takes more than one command is a script under `tools/`:

- `tools/build_examples.py` compiles every deck under `examples/` to all three output types and
  writes them into `docs/examples/`, which the site build publishes. This is where "one compile
  per output type" is expressed rather than asserted: the design requires that the claim be a set
  of commands, and a deck that fails one of them fails the documentation build.
- `tools/build_package.py` writes the subtree that is submitted to `typst/packages`, which is the
  tracked files minus the `exclude` list of the manifest. The Universe package checker reads that
  subtree and not the working tree, so it has to exist as a directory of its own.
- `tools/release_notes.py` reads one version's section out of `CHANGELOG.md`, so a GitHub release
  does not restate it.

The benchmarks are a script for a reason of their own, stated in
[docs/environment.md](../docs/environment.md): a measurement is only meaningful when it is
requested explicitly, on an idle machine, and a target that ran by default would record numbers
taken while something else had the processor.

An earlier version of this section put all of it in StepUp, as deliberate dogfooding.
That was dropped once the documentation was in place.
The dependency graph was not worth its cost here, because what it drove is a glob compiled by one
command and a site built by another, and a contributor who only wants to read the documentation
should not need a build tool to get it.

### What is left open

One thing is deliberately left open: whether the non-blocking newest-typst job yields useful
signal or only noise.

## Comparison with the packages that inspired this

- **`sanor`** separates declaration from animation, as Animo does, and its `apply`/`case`
  mechanism is the direct ancestor of Animo's `apply`. It also tags raw cetz draw commands
  (`test/draw.typ` tags a `draw.grid(..)` with `hider: draw.hide`), which Animo does not and
  cannot: `sanor`'s body is a function of `s`, re-evaluated once per subslide, so its `tag`
  applies draw-to-draw wrappers eagerly at call time, while Animo lays one content value out per
  epoch and reaches it with a show rule, which reaches content and not values. The capability
  difference is that one decision and nothing else. It is PDF-only, which is what lets it
  restyle and reflow freely: every step is a fresh page anyway. It pays for the separation with
  the `s => ([body], s)` threading, because it accumulates actions while the body is evaluated.
  It also supports what Animo decided against: `tag(s, name, body, ..defined-cases)` takes named
  cases at the tag site, and since `make-case` turns a bare content value into a replacing
  wrapper, those cases can carry *content*, selected from the timeline by name
  (`once("gtext", "alert")`). The threading and `object` being a function of the case are what
  pay for it.
- **`slipst`** has HTML export with panning, implemented with a custom runtime (whole-slip
  opacity crossfades with `plus-lighter` plus a `container.style.top` offset for panning). Its
  animation model is coarse, because it re-renders a whole frame per "alter"
  rather than animating elements.
  That per-alter re-render is exactly the mechanism Animo needs for structural steps.
  Animo's contribution is to confine it to a region
  and to keep per-element animation inside each frame.
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
| `../2026-talk-fml-stacie/2_talk`        | manim + manim-slides deck that assembles typst snippets: the workflow Animo aims to replace, and the best source of realistic animation requirements |
| `../2026-talk-thermodynamics`           | plain typst slides (`workflow/slides.typ`) built with StepUp; realistic input for both static output types                                           |
| `../2026-talk-publication-workflows`    | idem, a second deck with a different structure                                                                                                       |
| `../2025-poster-mlp-si-al-distribution` | typst poster; exercises the SVG-embedding output path                                                                                                |

Tooling Animo has to fit into:

| Directory                            | Relevance                                                                                                               |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `../stepup-core`, `../stepup-reprep` | the build tool driving those decks; Animo itself no longer uses it                                                      |
| `../templates`, `../bootstrap`       | repository templates where an Animo-based talk template would eventually land                                           |
| `../snipwise`                        | keeps text snippets in sync across files; copies the version from `typst.toml` into every `@preview/animo:X.Y.Z` string |
| `../stepup-benchmark`                | precedent for tracking compile time and output size across releases                                                     |
