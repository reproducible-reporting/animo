<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Animo Design Document

Animo is a proof-of-concept presentation package for typst (0.15.0 or newer),
drawing inspiration from `slipst` and `sanor`.

The distinguishing idea of Animo is that **content and animation are separated**.
The slide body declares *what* is on the slide, tags the interesting parts, and marks the
areas that are allowed to be relaid out.
The animation argument declares *when and how* those parts move, appear, disappear, change
style and change content.
Anything that typst can lay out as content can be tagged, including parts of equations,
cetz `content()` elements and fletcher nodes.
Raw cetz draw commands are the one exception,
and are refused at the tag site rather than silently ignored (see *Tags*).

The separation deliberately does not put all content in the body and all verbs in the animation.
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
One companion document carries the material that would otherwise overwhelm this document.

- [findings.md](findings.md), referred to throughout as *Findings*,
  records the verified behaviour of typst 0.15.0 and of the browsers Animo drives
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
  the viewport, and `pan` moves the viewport over the canvas
- No overflow of content to a next slide.
  Whatever falls outside the viewport is clipped, and `pan` brings the rest of the canvas into view.
- A **background** and an **overlay** per slide, each either a colour or arbitrary content, both
  belonging to the viewport, so a `pan` moves the slide under them
- **Timing**: every primitive may be delayed and given a separate duration.
  The gap before a subslide or a slide may run on a timer rather than wait for a presenter click.
  The timer is written as `wait:` on the subslide that comes up after the gap,
  or as `hold:` on the subslide that stays on screen during the gap.
  A reader can stop and start the timers again with `Space`,
  and a backward step plays the deck back over the same timed gaps.
- **Numbering**: a slide number, which the deck reads with `slide-number()` and `slide-count()`,
  and a subslide number, which is content laid out once per subslide with `per-subslide`.
  The browser shows the rendering of the current subslide,
  so the subslide number is not a value baked into a frame.
- A **transition between slides**, which is a crossfade, a push, a cover or a wipe, or a hard
  cut when it takes no time
- Zero templating or styling features
- Zero HTML and CSS in a deck's source.
  Every setting the runtime reads is an argument of the deck's show rule,
  so an author is never expected to call `html.elem`.
- No footer or header support, just use `#place` and wrap `#slide` to implement recurring elements
- Handout pages chosen per subslide with `init(handout: ..)` and `sub(handout: ..)`,
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
  // a `pan` moves the slide under it. The background, behind the slide, does the same.
  overlay: place(bottom + right, dx: -1cm, dy: -1cm)[#emph[A talk]],
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
      - The state before the first `sub` is a subslide too, which shows
        the slide exactly as the body declares it.
      - `init` describes that initial state. An `init` call is optional, and
        comes before the first `sub`. It says how the slide is entered, here with
        a push upwards over one second instead of the default transition of the deck.
        It also takes `wait`, `hold` and `handout`, as `sub` does.
    */
    import anim: *
    init(push(direction: btt), duration: 1)
    sub(
      hide("line1"),
      reveal("line3"),
    )
    sub(
      // `dx`/`dy` shift an element from wherever it is. `x`/`y` put it at a
      // position on the canvas, or relative to another tag with `relto`.
      move("line1", dx: 0.5cm, dy: 0.5cm),
      // `f` sets the scale factor rather than multiplying into it,
      // `delay` holds an operation back, here by a fifth of a second, and
      // `duration` says how long it then takes.
      scale("line3", f: 2, delay: 0.2, duration: 1.5),
      pan(x: 0.5cm, y: 0.5cm, relto: "line1"),
    )
    // `wait` brings this subslide up two seconds after the previous one came
    // up, instead of on a presenter click. `hold` on the previous subslide says
    // the same thing from the other side. A gap takes one of the two, not both.
    sub(
      wait: 2,
      reveal("line2"),
    )
    /*
      Structural operations change what typst has to lay out, so the enclosing
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
slide(body, animation: (), canvas: auto, background: none, overlay: none, numbered: true, ..)
```

The arguments of `slide` say what the slide is.
The `animation` argument says when anything happens to the slide,
including how the slide is entered.

- `animation` is the timeline, a code block of an optional `init(..)` call followed by
  `sub(..)` calls (see *Animation primitives*).
  The transition into the slide, the gaps on either side of its initial state and the handout
  flag of that state are arguments of `init`.
- `background` and `overlay` are described in *Background and overlay*.
- `numbered` decides only whether the slide is **counted** by the slide counter.
  A title or section slide is typically `numbered: false`.
  Whether and how a number is *shown* is the author's job,
  because there is no header or footer machinery.
  The author shows a number with `#place` and a wrapper around `#slide`, or with `overlay`.

A number that is shown is built from three functions,
and Animo has no other functions for numbering.

```typst
slide-number()            // the slide's number, or `none` on a slide `numbered: false` left out
slide-count()             // how many slides of the deck carry a number
per-subslide(f, wrap: auto)  // content laid out once per subslide, one of them shown
```

The `slide-number()` and `slide-count()` functions read the slide counter and return integers,
so a deck may compute with them.
Both must be called in a context.
On a slide that the counter passes over,
`slide-number()` is `none` rather than the number of the slide before it,
so one footer can serve a deck without special-casing every slide it lands on.
Neither number is the position that addresses a slide in the URL,
which counts every slide the presenter walks through.

`per-subslide` takes a callback rather than reading a counter.
An HTML frame covers a whole run of subslides (see *States and epochs*),
so a value chosen when the frame is rendered would be the same for all of them.
The callback is laid out **once per subslide**
and receives the **subslide info**, which is the dictionary `(number, count, step, steps, handout)`.
The `number` and `count` keys are the subslide's number within its slide
and how many subslides that slide has.
The `step` and `steps` keys are the same pair over the whole deck,
so a progress indicator may span either the slide or the deck.
The `handout` key is the subslide's resolved `handout:` flag.
The flag is the same in every output type,
so a presentation can mark the subslides that the handout keeps.
A handout also lays out the renderings of the subslides it leaves out.
The `number` and `step` keys count from one, while the URL fragment addresses state 0,
because the fragment is an address and the number is what the audience reads on the slide.
See *Resolved Design Decisions* for why the deck-wide pair is named after the presenter's steps.
A callback may return `none`, which lays nothing out for that subslide.
The `wrap:` argument takes `auto`, `box` or `block`,
and chooses between a hugging and a filling container exactly as the `wrap` of a tag does.
A rendering that states a ratio needs `block`,
because only a filling container has a width that the ratio can refer to.

The renderings are stacked in a container with the footprint of the largest rendering.
An implicit region follows the same rule, but takes the maximum over its epochs
rather than over the states.
Each rendering carries a label with the reserved `animo-` prefix.
A paged output lays out only the rendering of the state on the page,
and the browser shows the rendering that belongs to the current position.
All three output types therefore agree,
and a handout page carries the number of the state it kept rather than the number of the page.

- `canvas` is described in *Canvas and viewport*.

Beyond these, `#slide` has no templating or styling parameters by design.
The `background` and `overlay` arguments are not styles applied to the body.
They are two more pieces of content at two fixed depths,
and Animo neither positions nor decorates what goes in them.

### Canvas and viewport

A slide has two rectangles, and `pan` is defined by the difference between them.

- The **viewport** is what the audience sees: one HTML stage, one presentation-PDF
  page, one handout page. Its size is the deck's slide size.

- The **canvas** is what the body is laid out on. It is at least as large as the viewport and
  may be larger.
  Content that falls outside the *viewport* is clipped, not carried over to a next slide.
  A `pan` brings the rest of the canvas into view.

- `canvas: auto` (the default) sizes the canvas to the content of a slide **whose timeline
  pans**.
  That size is the union of the body's in-flow extent and the extent of each `#place`d element,
  clamped to at least the viewport.
  A slide that places nothing outside the viewport therefore has canvas = viewport, and
  nothing about the ordinary case changes.

- **A slide that never pans takes the viewport, clamped to its body box.** `pan` is the only
  reader of the canvas, and the viewport clips in both targets, so such a slide is drawn the
  same whatever canvas it gets.
  Computing the union is what costs time.
  The union is computed from a `show place:` rule,
  which pays a `context`, a `measure` and a queried element for every `#place` in the body.
  A slide that never pans therefore pays nothing for a canvas nobody can observe,
  even when it places thousands of elements.
  See *Resolved Design Decisions*.

- The body is laid out in a **box** as wide and as tall as the inner area of the viewport,
  unless the flow of the body is taller, in which case the box is as tall as the flow.
  The box has to grow, because a fixed-height container stacks the block-level content
  that does not fit at the bottom edge of the container rather than letting it flow past
  (measured under *Findings*).
  In a fixed-height box, a derivation that runs off the viewport would arrive
  as a pile of overlapping blocks instead of as the content a `pan` is meant to reach.
  A `#place` in the body resolves its alignment and its ratios against that box,
  so `place(bottom + right)` is the bottom right of the viewport on an ordinary slide
  and the bottom right of the flow on a slide whose flow runs off the viewport.
  A placement never changes the box, because a placement contributes nothing to the flow.
  The automatic canvas therefore still converges.

- `canvas: (width: .., height: ..)` states the canvas size explicitly,
  which is also the escape hatch when the automatic extent is wrong.

- The canvas origin is the body's origin. The viewport starts at `(0pt, 0pt)` in state 0, so a
  slide with no `pan` is indistinguishable from one with no canvas at all.

The automatic size cannot come from typst's own `auto` sizing, because `#place` is out of flow
and contributes nothing to it, as measured in *Findings*.
It also cannot come from position introspection, which does not work in the HTML target.
Animo uses a `show place:` rule over the body instead.
The rule fires for every placement and exposes `dx`, `dy`, `alignment` and a measurable `body`,
so the union can be computed from content alone and comes out the same in both targets.
The known limit of the rule is that a `place` nested inside another container
resolves against that container, which the rule cannot detect.
The union is therefore approximate and errs in both directions.
The `canvas:` argument is the remedy when the error matters,
and *Open Questions* says how large the error can be.

The rule fires once per epoch rather than once per rendering. The states of one epoch share
their content, and a display state puts a `move`, a `scale` and a `hide` around a tag rather
than a `place`, so every rendering of an epoch records the same placements at the same
offsets and at the same size.
The rule records the epochs that the output type renders.
These are all epochs in the HTML target and in the presentation,
and only the epochs that have a page in the handout.
A rendering that is measured rather than laid out, which is what a region does to
size its footprint, records nothing at all, because a `metadata` element inside a `measure`
never reaches `query`.

### Background and overlay

A slide has three layers, and the author fills the outer two:

1. the **background**, behind everything;
1. the **canvas**, carrying the body, which is what `pan` moves;
1. the **overlay**, in front of everything.

`background` and `overlay` both take either a **colour** or **content**.
A colour is emitted as CSS in the HTML target and as a page fill in the paged ones,
because `set page(..)` is unavailable in HTML (see *Findings*).
Content is laid out in a box the size of the **viewport**.
A `#place(bottom + right, ..)` in that content resolves its alignment against this box,
and an `image(width: 100%, height: 100%)` fills the slide.
A background that needs both a ground colour and content puts a filled `rect` behind the rest
of the content.

A gradient and a tiling are refused rather than accepted as a third form,
and the error message says to wrap the gradient or tiling in a `rect` of the slide size.
Typst resolves a gradient or a tiling against the element it fills.
For CSS, Animo would have to write an equivalent itself,
and a tiling has no CSS equivalent at all,
so the two targets would agree only by accident.
A `rect` is content, which both targets already draw the same way.

Four rules govern both layers alike:

- **They belong to the viewport, not to the canvas.** A `pan` moves the slide under them and
  leaves them where they are, so a logo stays in the same place on screen instead of travelling
  with the canvas. They contribute nothing to the automatic canvas extent either,
  so putting a full-bleed image in the background cannot enlarge the canvas and make the body
  pannable by accident. A background that should pan with the canvas is left for a later
  release. It would be a different construct rather than a flag on this one, because a fill
  and a content background would otherwise behave differently under a `pan`.

- **They hold no `tag` and no `region`,** and Animo refuses either there. They are outside the
  body, so nothing in the timeline could address them.
  A tag that resolved to nothing would be a silent no-op,
  which is what the refusal of raw cetz draw commands in *Tags* avoids.
  A `per-subslide` in a layer is accepted rather than refused.
  A `per-subslide` addresses nothing, the slide renders it without the timeline,
  and a layer is where a `per-subslide` costs the least.

- **They are rendered once per slide in HTML**, not once per epoch,
  because nothing in a layer can depend on an epoch.
  Each layer is a separate `html.frame` beside the canvas element,
  so a slide with four epoch renderings still carries one background and one overlay.
  The cost of a layer therefore does not grow with the number of epochs,
  which makes a layer the cheapest place for a number.
  A `per-subslide` in a layer is one stack of renderings per slide,
  while the same `per-subslide` in the body is one stack per epoch.

  Rendering a layer once does not limit the layer to one value per slide.
  A stack holds one rendering per state and lets the browser choose between them,
  exactly as a tag's display state does, so a layer may carry a subslide number.
  An earlier draft of this document wrongly inferred "one value" from "rendered once".

  In the paged outputs, each layer is laid out **once per page** of the slide,
  under or over the panned canvas.
  A rendering chosen per state requires this,
  and placing a layer on every page amounted to the same cost anyway.

- **The viewport clips all three layers alike,** at the edge of the viewport,
  and no layer clips another.

### Tags

`tag(name, body, wrap: auto)` marks content for animation.

- The same tag name may be used in **several places within one slide**. The animation
  primitives then address all of them together, as if they were one element.
- The same tag name may also be used in **different slides without interfering**: tags
  are scoped to the slide they appear in (see *Scoping* below).
- **The initial state of a tag follows from the timeline** rather than from an argument of
  `tag`, as the paragraph below says.
- The `wrap` argument decides what container the tag site becomes.

**A tag's initial state is inferred from the timeline.** A tag has two slots that are set
independently, its display state and its content state (see *Animation primitives*),
and each takes its initial value from the first operation that addresses it:

- a name whose first *display* operation is `reveal` **starts hidden**:
  invisible on the first subslide, but still occupying its space;
- a name whose first *content* operation is `reset` **starts removed**:
  not laid out at all on the first subslide, so it contributes nothing to the layout of that
  epoch.
  Starting removed differs from starting hidden only inside an *explicit* region.
  In an implicit region, the footprint is the maximum over the tag's states either way,
  so the space is reserved regardless.

The first operation is found in the order of the slide, which is first over its states,
and within one `sub` over the operations as written.
The resolver applies the operations in that same order.
A name that neither operation addresses first is visible and laid out as the body wrote it.
Adding a `reset` to a timeline therefore changes what the first subslide lays out,
inside the region that bounds the change.
Adding a `reveal` does not, because content that starts hidden keeps its space.
The two slots stay independent, so a name the timeline resets and later reveals starts out
removed and hidden at once, and the `reset` and the `reveal` undo different things.
Every site of one name therefore starts in the same state by construction,
since the state is a property of the name in the timeline rather than of the site.

Two states are unreachable this way, and both have an answer that needs no argument.
Content that is hidden for the whole slide, with no `reveal` anywhere, is typst's own `#hide`
in the body, which the package's star import deliberately leaves unshadowed;
a tag is then needed only if the timeline moves or scales the hidden content.
Content that is removed for the whole slide, with no `reset` anywhere, is laid out in no epoch,
so it reserves no footprint and reaches no output.
Deleting such content from the body has the same effect.

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

`wrap: auto` decides by **measuring** whether the body breaks the line it is put in.
Inspecting what kind of element the body is would not work,
because inspection cannot see into a `context` block, while the measurement can
(see *Findings*).
The choice is between a hugging and a filling wrapper rather than between inline and block.
A `box` and a `block` render identically for content that already sits between
paragraph breaks, while a wrapper at `width: auto` left-aligns anything the container was
centring, such as a `figure` or a block equation (measured; see *Findings*).

A function is accepted so that the inner slot can draw additional ink,
`box.with(inset: 4pt, stroke: red)` for instance, which then moves and scales with the element.
Animo requires the result to be a `box` or a `block`,
and otherwise panics with a message that names the tag,
because nothing else becomes an addressable group.

`wrap: none` says that a tag is only ever addressed by structural primitives.
Without a label there is no group for the continuous primitives to animate,
so Animo panics when the timeline applies one of them to such a tag.
A `reveal` is a continuous primitive, so a tag with `wrap: none` cannot start hidden either,
and the same panic reports it.

With `wrap: none`, the body is returned exactly as it came in, as measured.
The marker and the show rule that carry the plan to a tag site contribute nothing to the
layout, not even where a wrapper would trim a heading's block spacing (see *Findings*).

**A body that is not content is refused**, whatever the `wrap`, and the message names the
cause and the two ways around it. Such a value carries no marker, and a `context` block
cannot return one either, so the tag reaches no view and no primitive could ever resolve it.
The refusal exists for a stream of raw cetz draw commands,
which is an array of closures built where it is written,
before any show rule or `context` exists (measured; see *Findings*).
An earlier version handed such a body back untouched,
which made every primitive a silent no-op on it.
The symptom then surfaced three tools away from its cause.
The author writes a cetz `content()` element with a separate tag instead,
or a canvas written as a function of what it draws and tagged as a whole.
The timeline then replaces the canvas with the same function called with other arguments.

**A body a container would have resolved is refused** as well, and the refusal covers `region`
for the same reason. A grid, a table, a list, an enum and a terms list read their direct children
and keep the ones that are `cell` or `item` elements, and every other child becomes the body of a
cell or an item with default settings (measured; see *Findings*).
A tag site is a `context` block that stands between the container and the element,
so the container no longer sees a cell or an item.
`tag("s", grid.cell(fill: c)[..])` therefore lays out a cell with no fill,
and a tagged `list.item` becomes a nested list.
Typst neither panics nor warns, so the author would find the mistake only in the rendered deck.

The alternative was to rebuild the cell around the site,
which was rejected because of what it leaves behind.
A grid paints the fill of a cell in a separate frame, outside every group a site produces
(measured; see *Findings*), so the rebuild restores the fill in the rendering and leaves `move`,
`scale`, `pan`, `reveal` and `hide` reaching only the cell's content.
Those primitives would then be the silent no-op that the cetz refusal above prevents,
for half the primitives instead of all of them.
The error message names two ways out.
The site goes inside the element to keep its settings.
When the timeline has to move the filled box,
the fill goes on a `block` that the site holds.

The refusal fires only where something is lost.
A cell that sets nothing beside its body lays out the same either way and is left alone.
An item is refused whatever it carries,
because the list then takes the whole tag site as the body of a new item,
so the tagged item turns into a nested list.

Wrapping has a cost, which the manual states explicitly:
a tagged inline phrase can no longer break across lines, so its paragraph may reflow,
and a tagged heading shifts by a few points, because the block spacing of a heading is trimmed
at the wrapper's edge and replaced by the generic one (measured; see *Findings*).
Tagging the heading's text instead, `= #tag("t")[Head]`, avoids the shift exactly:
the wrapper is then inside the heading rather than around it, and the page is unchanged to
the pixel (measured; see *Findings*).

Wrapping also matters for addressing,
because only labelled `box` and `block` elements become addressable groups
in the SVG/HTML output (see *Findings*).
Whether a tag site has such a wrapper decides which primitives the site supports:

| Tag site                                                     | Structural primitives | Continuous primitives |
| ------------------------------------------------------------ | --------------------- | --------------------- |
| ordinary content                                             | yes                   | yes                   |
| inside math                                                  | yes                   | yes                   |
| a cetz `content()` element or fletcher node                  | yes                   | yes                   |
| content tagged with `wrap: none`                             | yes                   | refused               |
| a `grid.cell` or a `table.cell` that sets more than its body | refused               | refused               |
| an item of a list, an enum or a terms list                   | refused               | refused               |
| raw cetz draw commands                                       | refused               | refused               |

The asymmetry in the `wrap: none` row has one cause. Structural primitives are resolved by typst
when the epoch is rendered, so they work wherever a tag can wrap something at all. Continuous
primitives are resolved by the browser and need a `<g data-typst-label>` to address, which
typst emits only for labelled boxes and blocks.

The row for raw cetz draw commands is where the claim that anything laid out as content can be
tagged stops, and it follows from what such a value is rather than from Animo's mechanism.
`sanor` does reach a tagged `draw.grid(..)`, in `test/draw.typ`,
by threading its `s` through the slide body.
The body of a `sanor` slide is a function that is re-evaluated once per subslide,
so its `tag` applies draw-to-draw wrappers eagerly at call time.
Animo re-*lays out* one content value instead of re-*evaluating* a function,
for reasons that *Resolved Design Decisions* gives,
and a show rule reaches content where re-evaluation reaches values.
The refusal is therefore a consequence of that decision rather than an unexplored corner.
A canvas written as a function of what it draws and tagged as a whole
recovers the geometry change at the granularity of the canvas,
which a structural change there redraws anyway.
A canvas body evaluated per epoch would recover the change per object,
which is left for a later release.

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
  subslide.
  By default, that rectangle is the smallest box that fits every state the region actually
  takes on along the timeline.
  Explicit `width`/`height` override this default.
  The `clip` argument, which is on by default when a size is given, clips states that do not
  fit.
- **Reflow is contained.** Inside the footprint, typst lays the content out afresh for each
  state, so replaced, removed and restyled content genuinely reflows: line breaks change,
  following paragraphs shift. Outside the footprint, nothing moves.
- **Regions nest.** An inner region is itself a fixed footprint, so an outer region's layout
  does not depend on the inner region's state. Footprints compose, and states do not multiply
  (see *States and epochs* for why this matters to the cost).
- **A tag that is not inside an explicit region forms an implicit region**, i.e. `#tag("x")[c]`
  behaves as `#region[#tag("x")[c]]`, with an anonymous region so that the tag name stays
  unambiguous.
  This document uses two words for the two cases.
  An **explicit region** is one the author wrote,
  and an **implicit region** is the one a bare tag gets.
  Every tag that becomes a box is inside exactly one region,
  so in this document "outside a region" means outside an explicit region,
  and never "in no region".
  A tag with `wrap: none` is the one exception, as the next bullet says.
  Structural changes to a tag in an implicit region reflow only within the box that the tag
  reserves.
  A replacement is laid out in the largest box that any of the tag's states needs,
  which is the closest thing to "just swap this element" that keeps the rest of the slide still.
- **A `wrap: none` tag has no box, so it gets no implicit region.**
  Inside an explicit region, the region bounds such a tag as it bounds any other tag it holds.
  Outside an explicit region, nothing would bound the tag,
  so a structural primitive on it is refused in every output type.
  A tag whose content changes needs a box that the change stays inside,
  which is either a wrapper or a region around the tag.
- The `name` argument makes the region itself addressable,
  so the *region* can be moved, scaled, hidden or revealed like any tag.
  An unnamed region is invisible to the animation.
- A region is **block-level**, and is always a `block(width: 100%, ..)`.
  Unlike a tag, a region therefore needs no detection to choose its container.
  A region does **not** reuse a `box` or a `block` that its body happens to be already.
  Reuse would save nothing, since two nested `block(width: 100%)` render identically to one
  (measured).
  Reuse would also cost the region its control over `width`, `height`, `clip` and `align`.
  The region would have to merge those into the author's element
  by rebuilding the element from `fields()`, which loses whatever a `set` rule contributed.
- **A region is block-level because it needs the width of its container.**
  A region at `width: auto` has to know its container's width,
  and `layout(size => ..)` is the only way to learn it.
  The `layout` function is block-level, which means that it breaks the line it is put in
  (measured).
  Inline, the best available measurement is an unbounded `measure`,
  which reports the natural width of content that never got the chance to wrap.
  Keeping the surroundings still does not require a block.
  A box whose footprint is fixed at the maximum over its epochs
  holds its paragraph as still as a block holds its flow,
  because a constant size means constant line breaking.
  A box also wraps its content correctly once it has a width,
  so inside a paragraph only the width is missing.
  An explicitly sized region could therefore be a box.
  Animo does not offer one,
  because the inline case already exists as the implicit region around a bare tag.
- The implicit region around an inline tag has the same limit.
  Its footprint can only come from unbounded measurements,
  so content replaced at an *inline* tag site cannot wrap and runs on in one line instead.
  Inline tag sites are for short content, and the manual says so.
  A one-line paragraph measures as inline under `wrap: auto`.
  A tag around a one-line paragraph whose replacement should wrap therefore needs `wrap: block`,
  which the manual also says.
- The footprint of an inline implicit region is the widest width over the epochs,
  and the tallest ascent plus the deepest descent over the epochs.
  The content is placed inside at the height that aligns its baseline,
  and the box is lowered by the deepest descent.
  The per-axis maximum of `measure` would not do,
  because a box takes its baseline from its content even at a fixed size,
  so a fixed box still moves its line (measured; see *Findings*).
  A block-level implicit region is the filling block,
  as tall as its tallest epoch laid out at the container's width.
- A tag whose content state is the same in every epoch has no footprint and is not measured,
  since it lays out the same by itself.
  A slide without structural operations therefore pays nothing for epochs,
  and a tag nested in a changing tag needs no footprint either,
  because the inner footprint is fixed.

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

The cost is that a region reserves room for its largest state,
so a slide whose first state is short and whose last state is tall shows a gap at the start.
The remedies are authorial (choose `align`, split into several regions, give explicit sizes).
The alternative semantics is a region that pushes its surroundings around.
That semantics is deferred rather than impossible.

**Where regions cannot go.** `region` needs ordinary content,
so it does not work inside a cetz canvas (which consumes draw commands, not content)
and is awkward inside math.
A region beside a draw command in a canvas body is a type error,
exactly as any other content in a canvas body is (measured; see *Findings*).
In those places, a bare tag works instead.
The implicit-region rule above gives a bare tag a fixed footprint,
so `replace` on a tag inside math or inside a cetz `content` element works there
as it does anywhere else.

A region around the whole canvas, `#region[#cetz.canvas(..)]`, is the other option,
and it behaves differently.
Outside a region, a tagged `content()` element reserves the room of its widest epoch,
so cetz lays the figure out the same in every epoch and nothing in the figure moves.
Inside a region, the tag reserves nothing.
Cetz then lays the figure out afresh per epoch, and the canvas may change size,
which the region absorbs while keeping everything outside its footprint still.
Both behaviours were measured to the pixel in the paged output.
A region around a canvas is therefore what allows a figure to change size,
and without one a figure stays rigid.

### Animation primitives

All primitives return a plain description (a dictionary) and perform no action themselves.
`sub(..ops)` groups the operations that happen together in one subslide.
An empty `sub()` advances one step without changing anything.
It is allowed rather than refused because a timeline is code:
a `sub` whose operations come from a loop or an array may legitimately receive none,
and refusing the degenerate call would turn that into a compile error.
A call carrying only keyword arguments is legal for the same reason,
though `sub(wait: a)` in front of `sub(wait: b, ..ops)` is `sub(wait: a + b, ..ops)`
with one extra state, since a wait is measured from its predecessor's trigger (see *Timing*).

```typst
init(transition, duration: auto, wait: none, hold: none, handout: auto)
```

`init(..)` describes the slide's **initial state**, which is state 0.
The initial state is the slide as the body declares it, and has no `sub`.
The `init` call adds no state, so the subslides after it keep their numbers.
A timeline holds at most one `init`, before its first `sub`.
A second `init`, or one after a `sub`, is refused,
so that what `init` says never depends on where it was written.
A timeline without `init` behaves as one whose `init` states nothing.

- `transition` is how the slide is **entered**, one of the transition functions of
  *Transitions*. It is optional, and a slide without it takes the default transition of the deck.
- `duration:` is how long the transition into the slide takes, in seconds.
  `auto` is the deck's `transition-duration:`, and zero is a hard cut, whatever `transition`
  names.
- `wait:` and `hold:` time the gaps on either side of state 0,
  and `handout:` says whether the handout keeps state 0.
  Each takes the values and has the meaning of its counterpart on `sub`, described below and
  under *Timing*.

The boundary into a slide uses the `init` of that slide in both directions,
so stepping back over a boundary undoes exactly what stepping forward over it did.
That `init` belongs to the slide with the higher number, which is the slide a forward step
enters.
The setting is therefore written on the slide it is about,
rather than on the slide that happens to precede it in the file.
The `init` of the first slide of a deck has no boundary to time, so its `transition`,
`duration:` and `wait:` say nothing.
Every argument of `init` except `handout:` is HTML only,
because the paged outputs put two slides on two pages with nothing between them.

`sub` takes three keyword arguments.
`wait:` and `hold:` are under *Timing*.
`handout:` says whether the handout shows that subslide, and is three-valued:

- `handout: auto`, the default, resolves to `true` for the **last** state of the slide and to
  `false` for every other one, which gives the usual handout of one page per slide.
- `handout: true` asks for an extra page at that subslide, which is how a state that a later
  subslide destroys is kept.
- `handout: false` takes a page away, including the final state, so a slide can be left out
  of the handout entirely.

Every state carries this flag, the initial state included.
The initial state has no `sub`, so its flag is written as `init(handout: ..)`,
with the same three values and the same meaning.
A slide with no `sub` at all has only state 0, which is therefore also its last state,
so `auto` keeps it and `init(handout: false)` leaves the slide out of the handout.

The resolver therefore resolves the flag to a boolean per state, and the handout renders the
states whose resolved flag is true. This makes `handout:` the only thing that says what a
handout holds, rather than a set of exceptions to a rule written elsewhere.

The `handout:` flag is a keyword rather than a free-standing `handout()` call between `sub`
calls, so that its meaning does not depend on its position in the block.
The same reasoning puts `wait:` and `hold:` on `sub`.
A keyword also adds no name at the top level.

The primitives are classified in two ways, and both classifications matter.

The first cut is **what they address**. *Element primitives* take a tag name and act on the
tagged content. *Slide primitives* take no tag and act on the slide as a whole.
The only slide primitive is `pan`, which moves the viewport over the canvas,
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
| `scale(tag, f:, fx:, fy:)`            | scale the element about its centre                                 |
| `pan(x:, y:, dx:, dy:, relto:)`       | move the viewport over the canvas, optionally relative to a tag    |

The first four are element primitives.
`pan` is the slide primitive, so `pan` takes no tag name,
and its `relto`, which means "pan so that this tag comes into view",
is optional rather than positional.
Every primitive in the table also takes `delay:` and `duration:`, which *Timing* describes.

**Where `move` and `pan` put things.**
`move` and `pan` state a target position in the same two ways,
and each axis takes one of the two.
`x` and `y` put the element or the viewport at a distance from an **anchor**.
`dx` and `dy` shift it from wherever it already is.
One call may mix the two forms across its axes, as in `pan(dx: -17cm, y: 1cm)`.
`x` together with `dx` on one axis is refused, since the two are measured from different places.
An axis given neither form stays where it is, unless `relto` is given,
in which case that axis goes to the anchor.
For example, `pan(relto: "t")` brings a tag into view, `pan(dy: 3cm)` scrolls,
and `move("a", relto: "b")` puts `a` exactly where `b` is.
`x`, `y`, `dx` and `dy` are lengths, because there is no length that a ratio could refer to here.

The two primitives differ only in their anchor:

- for `pan` it is the canvas origin, or with `relto` the named tag, placed where the body of a
  fresh slide starts, at the deck's margin;
- for `move` it is the canvas origin, or with `relto` the named tag, and what is put there is
  the **anchor of the moved tag**, so `move("a", x: 2cm, y: 0pt)` puts `a`'s top-left corner
  2 cm from the left edge of the canvas.

The anchor of a tag is the top-left corner of the first site of its name in document order, as
the body laid it out, in the first rendering that lays that site out.
This definition has the following consequences:

1. **A tag's anchor excludes the display state of that tag**, so it means the same in every state. A
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

A `move` or `pan` relative to a tag the slide does not have is refused,
because a misspelt name is the likely cause and a silent fallback would hide it.
A `move` or `pan` relative to a `wrap: none` tag is refused as well,
because such a tag has no box and therefore no corner.
The other continuous primitives follow the same rule.
A `move`, `scale`, `reveal` or `hide` on a name that became no group on its slide is refused,
for the reason given under *Scoping*.

**An anchor read from inside a tag that the timeline moves or scales is refused as well.**
This refusal is about the body rather than about a name.
A transform around a tag moves the corners of that tag and of every tag inside it,
so their anchors stop being the corners that the body gave them.
No rendering can then recover the anchor that the design promises.
The static presentation and the browser read an untransformed layout,
the static presentation from the first page of the slide,
and the browser from the slide before anything is written on it.
The handout reads whichever page it keeps, which may show the transform.
A `pan(relto: ..)` that names a tag below a transform would therefore put the viewport
in two different places in two output types.
A `move` whose `relto` names a tag inside the tag it moves would not even converge,
because the translation of the move shifts the marker it reads.
The rule also covers the anchor of the moved tag,
so `move("a", x: ..)` on a tag inside a moved tag is refused for the same reason.
Only reading the anchor is refused, and nesting itself is allowed.
A tag inside a moved tag is the ordinary way to move a group and light up a part of it.
A tag inside a tag that is only revealed or hidden keeps its anchor,
because typst's `hide` lays content out where it is.
The remedy is to read the anchor of the outer tag,
or to take the inner tag out of the outer one.

What the anchor of a tag is exactly, and how the two targets read it, is under *Architecture*.

The resolver keeps each axis as a pair of an anchor name and an offset,
rather than as a single number.
`x` sets both, `dx` adds to the offset and leaves the anchor alone,
and the default pair is the anchor of the moved tag at offset zero.
A target computes the translation as `anchor(relto) + offset - anchor(self)`,
which is the identity when nothing has been said.
This lets absolute and relative forms alternate along a timeline
without either one having to know the other's units.
The plan carries the same pair for `pan`, whose `anchor(self)` is the canvas origin.

**What `scale` does.** `scale` takes `f` for an isotropic factor and `fx`/`fy` for one axis
each, and **`f` cannot be combined with either**. The combination is refused rather than
resolved by a precedence rule, since a call that says both says two different things.
Each factor is a number or a ratio,
so `scale("a", f: 2)` and `scale("a", f: 200%)` are the same operation.
A ratio is resolved to a number when the operation is built,
because the browser and the paged renderer both take a number.

**A factor is set, not multiplied into what is already there.** `scale("a", f: 2)` in one subslide
and `scale("a", f: 2)` in the next leaves `a` at twice its size, not four times, and
`scale("a", f: 1)` restores it whatever came before. An axis the call does not mention keeps
its factor, so `scale("a", fx: 2)` after `scale("a", f: 3)` leaves `a` at 2 horizontally and 3
vertically. Successive growth is written as the product, so the author multiplies once
instead of tracking a history across every later subslide.

**Structural primitives** change what typst has to lay out or paint.
Only typst can render the result,
so each of them forces a fresh rendering of the slide (an *epoch*, below).
The change is shown with the transition that the operation names,
which is the crossfade by default, rather than with motion.

| Primitive            | Meaning                                                                 |
| -------------------- | ----------------------------------------------------------------------- |
| `replace(tag, body)` | substitute new content at the tag site, with reflow inside the region   |
| `remove(tag)`        | drop the content and free its space, with reflow inside the region      |
| `apply(tag, ..fns)`  | wrap the content in the given content-to-content functions; accumulates |
| `reset(tag)`         | back to the content in the body, with all applied wrappers dropped      |

Notes and consequences:

- `apply` takes **functions only**, e.g. `apply("x", text.with(fill: red))` or
  `apply("x", emph, text.with(size: 1.2em))`, applied outermost-last. Named style properties
  in the style of `sanor`'s `case(fill: red)` are deliberately not supported.
  Animo does not inspect content,
  so Animo cannot know which `set` rule a bare property belongs to.
  Wrapping with `text.with(..)`, `box.with(..)` or a lambda says it explicitly.
- `apply` is structural even when the wrapper cannot possibly reflow, as with a colour change.
  The reason is rendering rather than reflow,
  because typst's styling cannot be expressed in CSS in general.
  The cheap CSS-only special case, a primitive that changes a colour and nothing
  else, is left for a later release.
- **`reveal` and `reset` also declare an initial state.** A name whose first display operation
  is `reveal` starts hidden, and one whose first content operation is `reset` starts removed
  (see *Tags*).
  Neither is therefore a pure undo.
  A `reveal` written where nothing hid the tag makes the tag start hidden.
- **Inserting** content that is not in the body is `replace` on an empty tag:
  `#tag("slot")[]` in the body, `replace("slot")[..]` in the timeline. Content that *is* in
  the body but should start out absent is a plain `#tag` that the timeline resets, which is
  what makes it start removed.
- `remove` versus `hide`: `hide` keeps the space and is smooth,
  while `remove` frees the space and reflows.
  Regions give the "occupies no space" state a bounded meaning.
  Outside a region there is nothing for `remove` to reflow,
  because the implicit region reserves the footprint of the element's largest state
  either way.
  Outside a region, `remove` therefore costs an epoch without any benefit,
  and `hide` is the right primitive.
- Structural primitives work at every tag site inside a region, a `wrap: none` one included,
  because typst renders the epoch and needs no group to do it. Outside an explicit region a
  `wrap: none` site has no box that a change could stay inside, so a structural
  primitive on it is refused; see *Regions*.
  Continuous primitives need a labelled group and so need a wrapped tag site. A tag site is
  content in either case: raw cetz draw commands are refused, and no primitive reaches them.
  See the table under *Tags*.
- **How they compose.** A tag's content state is two slots that are set independently: what is
  laid out (the body, a replacement or nothing) and the list of wrappers. `replace` and `remove`
  set the first and keep the second. `apply` appends to the second, so it wraps whatever is laid
  out then or later, a later replacement included. `reset` sets both, back to the body with no
  wrappers.
  Consequently, `apply` followed by `replace` gives a restyled replacement,
  `reset` after `remove` gives the body with no wrappers,
  and replacing twice keeps the second replacement. None of the four
  touches the display state: a moved tag that is replaced is a moved replacement, and `reset`
  does not undo a `move`. Several operations on one tag in one `sub` apply in the order written,
  as continuous operations do, so `apply("x", f, g)` in one subslide equals two subslides
  and lays out `g(f(content))`.
- **How a region crosses its boundary.**
  All four structural primitives take `transition:`,
  which is one of the transition functions of *Transitions*
  and says how the region they change crosses the epoch boundary.
  `auto`, the default, is the crossfade, whatever the deck's `transition:` says,
  because the deck's argument is about slide boundaries.
  The `delay:` and `duration:` of the operation time the transition,
  and a `duration:` of zero is a hard cut of the region.
  The `transition:` argument belongs to the operation rather than to `sub`,
  so that one subslide can carry one region with one transition and another region with
  another. Two operations that change one region at one boundary and
  name two transitions are refused, as two that disagree about `delay:` are. The argument is
  HTML only, because two pages have nothing between them.
- Because `replace` and `apply` carry content and functions, plan descriptors are no longer
  pure data in the strict sense. Tier-1 tests should therefore assert on the *resolved
  structure* (tag names, per-state flags, epoch boundaries and counts) rather than on the
  payloads, which do not compare usefully.

### Transitions

A **transition** is the way a boundary is crossed, and it is named by a function of the `anim`
module, so that it is written where the timeline is written and an editor can show the
parameters each one takes.

| Transition              | What it does                                         | Slide | Region |
| ----------------------- | ---------------------------------------------------- | ----- | ------ |
| `crossfade()`           | fades the outgoing content out and the incoming in   | yes   | yes    |
| `morph()`               | moves the shared content and fades the rest          | no    | yes    |
| `push(direction: rtl)`  | moves the incoming slide in and the outgoing one out | yes   | no     |
| `cover(direction: rtl)` | moves the incoming slide in over the outgoing one    | yes   | no     |
| `wipe(direction: ltr)`  | uncovers the incoming slide behind a moving edge     | yes   | no     |

A transition is written in three places:

- as the positional argument of `init`, for the boundary into the slide;
- as `transition:` on a structural primitive, for the region it changes;
- as `transition:` on the deck's show rule, for every slide whose `init` names none.

A transition says what the crossing looks like and nothing about time.
The time is stated by the call that causes the change, which is the structural primitive for a
region and `init` for a slide, so one `sub` states the timing of all its operations in one way,
and a transition never receives a number it would have to refuse.
A **hard cut** is a crossing that takes no time, so it is written as `duration: 0` rather than
as a separate transition, and every transition with a duration of zero is the same cut.

A `direction` is the direction of travel on a forward step, one of `ltr`, `rtl`, `ttb` and
`btt`, which are the directions that typst defines.
A backward step plays the same transition from the other end, so it travels the other way.
A transition a region cannot take, such as a push, is refused on a structural primitive at
compile time, and a transition a slide cannot take, which is the morph, is refused in `init`
and on the deck.
The names, the parameters and their values are checked in typst rather than only in the
runtime, because a transition the runtime did not recognise would be a boundary that quietly
took a default.

### Timing

Four arguments decide *when* and *how long* rather than *what*.
`wait:` and `hold:` time a **subslide**:
`wait:` names the gap before the subslide and `hold:` the gap after it.
`delay:` times an **operation inside a subslide**.
`duration:` says how long that operation then takes,
and on `init` how long the transition into the slide takes.
All four are plain numbers of seconds,
because typst has no time literal and `2s` would not parse,
and because one unit across the whole API keeps two numbers on one call comparable.
All four are HTML only.
The paged outputs are one page per state with nothing between them,
so there is no clock to measure any of them on.
The stylesheet is the one place where a time carries a unit,
because a custom property read as a CSS `<time>` must carry one.
Animo writes the values it generates as `0.4s` rather than as `400ms`,
so that every number an author reads or writes is still a number of seconds,
and the runtime accepts either spelling.

**Three arguments of the deck's show rule say what motion costs when nothing else does.**
`primitive-duration:` is how long one animation primitive takes, `transition-duration:` how long
a transition between two slides takes, and `easing:` is the timing function both of them follow.
A fourth argument, `transition:`, is the transition of every slide whose `init` names none,
which is the crossfade by default, as in `transition: anim.push(direction: btt)`.
The `transition:` argument reaches the runtime in the deck's configuration, `data-animo-config`,
rather than as a custom property, because it is structured and no media query has to reach it:

```typst
#show: animo.with(primitive-duration: 0.2, transition-duration: 0, easing: "ease-out")
```

The two durations are numbers of seconds like every other time an author writes,
and each is `0.4` by default.
They are only defaults, so a call that states a `duration:` takes that duration.
A deck that sets one of them to zero does not animate motion of that kind
unless a call asks for it.
The deck above therefore cuts between its slides while the steps inside them keep moving.
A slide of that deck that is to be pushed in states the duration as well as the transition,
as in `init(push(), duration: 0.4)`.
The shorter `init(push())` takes the deck's `transition-duration:`, which is zero in that deck,
so the slide is entered with a cut.
The manual has to say so where it teaches `init`,
because a transition that is named and not seen is the mistake this rule invites.
`easing:` takes one of `"linear"`, `"ease"`, `"ease-in"`, `"ease-out"` and `"ease-in-out"`,
the last being the default.
A name outside that list is refused at compile time,
because a timing function the browser rejects would throw in the middle of a talk.
The three arguments reach the runtime as the custom properties `--animo-primitive-duration`,
`--animo-transition-duration` and `--animo-easing` on `:root`.
The deck writes these properties into the deck stylesheet beside its geometry,
and the runtime reads them at every step,
so restating one of them reaches every operation that asked for nothing.
They are HTML only, like the four times above, and the paged outputs ignore them.

**`wait:` is the delay before the subslide it is written on is entered, and `hold:` is the delay
before the next subslide is entered.**
The two arguments are two ways to state one quantity, and both apply to `sub` and to `init`:

- `sub(wait: 2, ..ops)` brings that subslide up two seconds after the previous state came up,
  instead of on a presenter click; `sub(hold: 2, ..ops)` keeps it up for two seconds and then
  brings up whatever follows it, which on the last `sub` of a slide is the next slide;
- `init(wait: 2)` enters that slide two seconds after the previous slide's last state came
  up; `init(hold: 2)` holds its initial state for two seconds, which on a slide with no
  `sub` at all is again the boundary into the next slide.

`none`, the default of both, waits for the presenter.
Two spellings of one gap are one keyword more than strictly needed.
Both exist because each is the natural spelling for a different intent.
"This slide needs no click" is about the slide being entered, and is written `init(wait: 0)`.
"Do not stop here, run straight on" is about the motion that is playing,
and is written `sub(hold: 0)` on the subslide that plays it,
which is also where the author is looking.
Neither spelling covers every case alone.
`wait:` means nothing on the first state of a deck, which has no predecessor,
and `hold:` means nothing on the last state, which has no successor.
Neither of those cases is a real loss.
`wait:` cannot be written on a subslide that a loop generated,
so a slide boundary after a generated timeline has to be timed from the slide that follows.
The two spellings also behave in opposite ways when a timeline is edited.
Take a subslide *A* followed by a subslide *B*, and insert a new subslide between them.
A `wait:` written on *B* still times the gap in front of *B*,
which now runs from the new subslide to *B*.
A `hold:` written on *A* still times the gap after *A*,
which now runs from *A* to the new subslide.
Appending a subslide to the end of a slide works the same way.
The slide's trailing `hold:` then times the gap into the appended subslide,
and the slide boundary is no longer timed,
while a `wait:` on the `init` of the next slide still times the boundary.

**One gap takes one number.**
A gap that both of its neighbours time is refused, and the error names both sides.
A gap elapses once, so there is nothing for a precedence rule to pick between.
Two operations that disagree about a `delay:` in one region are refused for the same reason.
Summing the two numbers was the alternative,
and it was rejected because of what it would mean rather than what it would cost.
No author means four seconds by "hold three and wait one",
so a sum would only accept a gap that was specified twice
and turn it into a length that neither number states.
A sum would also have no meaning for the `hold: auto` that a narrated clip would need later,
because `auto` cannot be added to a number.
Refusing now keeps the sum open as a later option,
because widening a refusal into a sum later would break no deck,
while narrowing a sum into a refusal would break several.

The refusal is a compile error in both of the places it can arise.
Inside a slide, the resolver sees both sides of every gap.
Across a slide boundary, neither slide's resolver sees both sides,
because the trailing `hold:` and the leading `wait:` are resolved by two calls.
A slide therefore always hands its trailing `hold:` to the next slide through a typst `state`,
and the next slide checks that `hold:` against its leading `wait:`.
The deck-wide refusal of the handout uses the same mechanism.

Timing does not take the deck away from the presenter. **A forward step cancels the pending timer
and re-arms from the state it lands on**, so a presenter can always run ahead of the clock and a
deep link starts a new timer from where it lands.

**A backward step lands on the nearest earlier state the deck would rest at.**
A gap of zero is a join rather than a stop.
The state that the gap is measured from is left at the same moment it is entered,
so the audience never sees that state at rest,
and the motion that the state began is redirected in its first frame rather than arriving.
A backward step that landed on such a state would put a composition on the screen that was
never shown.
It would also cost one press per join to walk back over a run
that the presenter got through with one press, because a join costs no press going forward.
A join is therefore crossed in both directions,
and a run of joins is crossed as a whole, including a slide that the deck runs through.
The timeline decides where a deck rests, and the clock does not,
so a backward step walks the same way while the clock is stopped.
A state that a backward step walks over stays reachable by a fragment,
and by stepping forward through a stopped deck.
Only a gap of exactly zero is a join, so `hold: 0.001` makes the state it is written on a stop
after all.

**A join that runs out of a slide is walked back into.**
A backward step over such a join lands on a state before the last state of the slide it enters.
This is the one case where the slide being entered is not already showing the state it is
entered at, and the slide moves into that state rather than snapping into it.
Going forward, the audience saw one motion,
in which the step ran inside the slide while the boundary carried the slide away.
A backward step that snapped the slide into place would therefore crossfade a picture that was
never shown.
The two clocks stay separate.
The slide moves on `--animo-primitive-duration`,
and the boundary crosses on the duration of the slide's `init`,
which is `--animo-transition-duration` unless the `init` states one.
Both clocks start on the same frame, as they did in the forward join.
A forward step into a slide snaps instead.
A slide keeps the state it was last shown in,
so a slide may be entered at state 0 while showing a later state.
Animating out of that later state would play, backwards, a step the audience never saw,
while the slide is coming up.
A step that crosses more than one slide boundary snaps as a whole.

**A backward step also turns the clock around.** One gap times the step in both directions,
because a gap lies between two states rather than belonging to one of them. A state the deck
leaves on its own after a second going forward is a state it leaves on its own after a second
coming back, so a state inside a run is shown for as long in either direction. The travel ends at
the state whose gap waits for the presenter, which is the state the presenter last pressed a key
at, so a run of automatic gaps costs one press back as it costs one press forward. A backward key
pressed during the travel is one more step back, as a forward key pressed during autoplay is one
more step forward, and `Space` stops the deck where it is. A deck that times every one of its gaps
has no state to end the travel at and travels back to its first state.

**The first state of a deck is where backward travel stops rather than turns**,
because there is nothing earlier to travel to.
The timer of the gap after the first state would start forwards and undo the step that just
arrived, so the first state would stay on screen only for the length of that gap.
The clock is stopped there instead.
This stop also holds a deck that runs itself out of its first slide from the first paint.
Without the stop, that slide would be on screen for no time at all,
since `Space` is the forward key where no timer is pending.
A forward step restarts that clock, and so does `Space`.
A backward step over a gap that was waiting for the presenter does not touch the clock,
so every key behaves as before in a deck that times none of its gaps.

**`Space` stops and starts the deck**, which is what a reader watching a deck play itself
expects.
`Space` does so only while there is a clock to stop.
On a deck with no clock, `Space` is a forward key, which is what a presentation remote sends.
The stop reaches the motion as well as the clock.
An animation in flight is paused where it is and picked up from
there, so the picture holds still rather than running on to the end of the step it was in.
Resuming continues what is left of the wait rather than restarting it,
and the deck continues in the direction it was going,
so `Space` is the one key that says nothing about direction.
A manual step while the clock is stopped leaves the clock stopped.
This rule distinguishes the two kinds of stop.
A deck stopped with `Space` stays stopped while its presenter steps through it,
while a deck stopped at its first state starts its clock again when the presenter steps forward.
Both kinds of stop set the same `data-animo-paused` attribute on the root element,
where a deck that wants to show the pause can read it.
The pause is **not in the fragment**, which holds only the position,
so a deck restored from a fragment comes back running, also after a reload by `typst watch`.

A `wait` and a `hold` are measured from the moment the subslide they are timed against was
**triggered**, not from the moment its animations finished.
A gap shorter than that subslide's motion therefore interrupts the motion.
This needs no separate rule,
because an interrupted subslide continues from where it is (see *Architecture*).
A `hold: 0` is the limiting case, and the reason the measurement is defined this way.
A `hold: 0` starts the next subslide at the same moment as the subslide it is written on,
so a build that runs over two slides keeps its motion and the slide crossfade on one clock.

**`delay:` holds one operation back within its subslide**, and every primitive takes it,
continuous and structural alike, defaulting to zero. `scale("a", f: 2, delay: 0.2)` starts a
fifth of a second after the subslide it is in.
The subslide still has exactly one clock.
A delay becomes the effect's delay in the Web Animations API,
so all of a subslide's animations are still created in one task
and all of their delays are measured from the same instant.

**A backward step is the step it undoes, mirrored in time.**
The length of a step is the time until its last operation ends,
and every operation is mirrored about that length.
An operation that ran from `delay` to `delay + duration`
runs backwards from `step - delay - duration`, for exactly as long as it took.
The last thing the audience saw arrive is therefore the first thing they see leave,
a step of three staggered lines comes apart in the reverse of the order it was built up,
and the step ends where the earlier state began.
Replaying the forward schedule unchanged would make the operation that arrived first leave first.
The composition would then pass through states that the forward step never showed,
and where one line is nested inside another,
the outer line would leave while the inner one is still on the screen.
Only the delays are mirrored, because a duration is how long an operation takes and not when it
happens.
A backward step that walks back over a join runs between two states that are not neighbours,
and the schedules of the steps it walks over are not replayed one by one.
Across a join, the audience saw one motion that was redirected before it arrived,
and neither schedule replayed on its own reproduces that motion.
The way back is therefore one motion too, mirrored about the length of the step that began it.
The epoch boundaries that such a step crosses are handed over together,
on the clock of that one motion, as rule 2 of *Architecture* states.

On a structural operation, a delay holds back the **crossfade of the region it changes**.
The epoch boundary lasts until the last of these crossfades has finished,
and the outgoing frame stays visible in the regions it hands over for that whole time.
Staggering two structural changes therefore works
when they sit in two regions, which two bare tags always do, since each forms an implicit
region.
Two operations that change *one* region at one boundary and disagree about `delay:` are refused.
A region crossfades once, so there is nothing for a precedence rule to pick between.

**`duration:` says how long one operation takes**, and every primitive takes it beside `delay:`,
defaulting to `auto`.
`auto` is the `primitive-duration:` of the deck,
so a timeline that asks for nothing follows the tempo of the deck,
and a change of the deck's tempo still reaches every operation that did not ask for something
else.
A number is a number of seconds,
so `reveal("a", delay: 0.5, duration: 2)` fades in over two seconds.
A `duration:` becomes the duration of the Web Animations API effect,
just as `delay:` becomes the delay of that effect.
The subslide therefore still has one clock, an interrupted subslide behaves as before,
and a backward step keeps the duration of every operation while mirroring the moment it starts
at.

**A reader who asked for less motion gets none, whatever the deck or the timeline says.**
A number written in a typst source is invisible to a media query, so the reader's preference
reaches the runtime as a separate custom property on `:root`, `--animo-motion`, which is
`auto` unless `prefers-reduced-motion: reduce` sets it to `none`.
The runtime reads `--animo-motion` at every step.
While it is `none`, every step snaps, whatever duration the deck or a call states,
and takes the same path that a deep link takes.
The preference is a separate property rather than a zero written over the deck's durations.
A deck duration is only a default that the `duration:` of a call overrides,
so a zeroed default would leave every stated duration animating.
The deck writes its `:root` block after the stylesheet that holds the query,
so the declaration in the query is `!important`
and the guard wins by cascade weight rather than by source order.
The `!important` declaration also wins over a stylesheet that an author adds to the page,
which source order alone did not, as chromium 151 and firefox 153 both showed.

Reduced motion drops every `delay:` as well, but neither of the two gap numbers.
A step whose duration is zero has no motion for one operation to arrive late inside,
so the runtime drops the delays of a snapping step along with its duration.
One reading of the media query thus serves all three numbers, and keeps the check in one line.
A `wait:` and a `hold:` are left alone, because they are pacing rather than motion.
Zeroing them would run an autoplaying deck to its end at once,
and a reader who asked for less motion could then not follow the deck at all.

**A duration may run past the subslide it is in**,
and an operation that outlives its subslide is overtaken rather than clamped or refused.
For a continuous operation, this is the rule that *Architecture* already states,
which is that an interrupted animation continues from where it is.
For a structural operation, the epoch boundary stretches with the duration,
so two boundaries may be in flight at once and three frames may paint one region together.
A long duration is not the only way to reach that situation.
A gap shorter than a subslide reaches it, and so does a presenter who clicks twice.
Clamping a structural duration to its subslide, or refusing one that outlives it,
would therefore remove one way into the situation rather than the situation itself.
*Architecture* describes how the boundary handles it.
Every frame other than the one being entered hands the region over on the new boundary's clock,
so the opacities in the region still add up to one throughout.

### States and epochs

States and epochs form the execution model that ties the two classes of primitives together.

- A slide with *S* `sub` calls has **S+1 states**, numbered 0 to S.
  State 0 is the slide exactly as the body declares it.
  State *i* is state *i-1* with the operations of the *i*-th `sub` applied.
  Continuous operations accumulate as display state,
  and structural operations accumulate as content state.
- An **epoch** is a maximal run of consecutive states with the same *content* state.
  A new epoch starts at every state whose `sub` contains at least one structural operation.
  A slide with no structural operations has exactly one epoch.
- The content state of an epoch fixes the content of every tag (body, replacement, or nothing)
  and its accumulated wrappers.
  That is all typst needs to render the epoch.
- A region's content depends only on the *content* state, so its unit of measurement is the
  **epoch**, not the state. Each region measures **only the epochs the slide actually has**,
  not the cartesian product of its tags' possibilities, and consecutive states within one epoch
  cost it nothing. Because nested regions have fixed footprints, the measurements of an outer
  region are independent of its inner regions' content. Cost is therefore linear in the number
  of epochs, per region. (This document says *per epoch* everywhere for this measurement; the
  word *state* is reserved for the S+1 subslides.)

**How a region measures one epoch.**
A region cannot substitute the content of an epoch into its body,
because it receives its body as opaque content and cannot rewrite the tags nested inside it.
Instead, the current epoch is an entry of the view provided to the body (see *Scoping*).
The region measures by laying its body out once per epoch,
under a copy of the view with that entry set to the epoch,
and each tag resolves its content for the epoch as it is laid out.
This was verified in both targets, inside `layout` and `measure`,
with nested `context` reads and no convergence warning (see *Findings*).

This mechanism matters in two ways.
It makes reflow inside a region possible without turning the body into a function of the epoch,
which is the `s => ([body], s)` threading that *Resolved Design Decisions* rejects.
It is also **indifferent to where time-dependent content is written**,
because a tag could resolve its content for the epoch from the plan or from its arguments
equally well.
Where `replace`'s content belongs is therefore not a question of feasibility,
and is settled on other grounds below.

Renderings required per slide:

| Output type         | Renderings                                    |
| ------------------- | --------------------------------------------- |
| HTML presentation   | one, with one per epoch in every region       |
| Static presentation | one per state (S+1)                           |
| Static handouts     | one per state with `handout` resolved to true |

A `background` or `overlay` that is content is rendered **once** beside these in HTML,
whatever its epochs, because neither layer can depend on an epoch.
In the paged outputs, each layer is laid out once per page of the slide
(see *Background and overlay*).

In HTML the body of a slide is laid out once, and every region that sits in no other region
lays its body out once per epoch, as an epoch stack in its footprint (see *Architecture*).
A slide with one epoch is one rendering and nothing more.

A `per-subslide` is the one construct whose cost is counted in **states** rather than in epochs,
because it is one rendering per state of its slide, wherever it sits.
In a layer, or in the body outside every region, a `per-subslide` is one stack per slide.
Inside a region, it is one stack per rendering of the region's epoch stack,
which is why *Slides* says to put a number in a layer.
The plan carries nothing about a `per-subslide`,
because the runtime finds the renderings by the label each of them carries.

### Architecture

The same tagged content feeds three output types:

**HTML presentation.** A slide is rendered as *one* `html.frame`, i.e. one inline SVG, laid
out on the canvas, holding one rendering of the body. Everything outside the regions is the
same in every epoch, so it is laid out once.
Every region that sits in no other region,
whether explicit or the implicit region of a tag, lays its body out once per epoch.
The region places these renderings on top of each other at the corner of its footprint,
in epoch order.
Each rendering is a labelled block,
so that it becomes a `<g data-typst-label="animo-epoch-N">` that the runtime can address.
Together the renderings are the region's epoch **stack**.
A stack is a set of renderings placed at one point, of which the
runtime shows one at a time. Each rendering of a stack is labelled `animo-<kind>-<index>`, and
the kind says what the index counts and how the runtime chooses the rendering it shows. The
renderings of a `per-subslide` are a stack of the other kind, `subslide`, with one rendering
per state of the slide.
Stacks do not nest.
A region inside a rendering of an epoch stack is already laid out once per rendering,
so the inner region lays out the epoch of that rendering.
A region on paper lays out the epoch of its page, so an epoch stack exists only in HTML.
The slide is one frame rather than one frame per stack,
because typst's deduplicator works within one frame.
The renderings of a slide then define each glyph they share once between them
rather than once each,
which is the only part of that duplication a package can reach (see *Findings*).
The canvas element sits inside the slide container,
which is the slide's visible box and clips the canvas (`overflow: hidden`).
Inside the slide container, the canvas element sits between the background frame and the overlay
frame.
These two are frames of the slide rather than renderings inside the canvas's frame,
so a `pan` does not move them.
The slide containers are the children of the **stage**,
which is an element with the deck's aspect ratio and the viewport of the HTML output.
The stage clips its content and isolates the blend between two slides,
and the deck centres the stage on the page's surround.
Each tagged element appears as a `<g data-typst-label="...">` group, once outside every
region and once in every rendering of the stack it sits in.
Animations are then performed in the browser:

- `reveal`/`hide` animate `opacity` on the tag's inner group
- `move` animates the CSS `translate` property, computed from the measured anchors as
  *anchor(relto) + offset - anchor(self)*, which is the identity for a tag the timeline has not
  moved
- `scale` animates the CSS `scale` property, about the centre of the element, with one value for
  `f` and two for `fx`/`fy`
- `pan` animates `translate` on the canvas element inside the clipping viewport, as a
  percentage of the canvas, which follows the window without being measured
- a `per-subslide` stack shows the rendering of the state being entered and hides the others,
  by writing `opacity` on the labelled group of each.
  The switch snaps, also in a step that animates,
  since two numbers that crossfade into each other are both unreadable.
  The stack uses `opacity` rather than `visibility`,
  although `visibility` is what hides an epoch rendering nobody is watching.
  A descendant may take its visibility back,
  so a stacked rendering that did so would paint out of an epoch that the slide is not showing.
  A rendering at `opacity: 1` inside a hidden epoch stays hidden (see *Findings*)
- structural steps crossfade the changed **region**: the outgoing rendering of its epoch stack
  fades out and the incoming one fades in, with `mix-blend-mode: plus-lighter` on the
  renderings and `isolation: isolate` on the container of the stack, and every other stack
  shows the rendering of the epoch being entered without animating
- a structural step whose primitive names `morph()` crossfades the region in the same way and
  also animates `translate` on the **matches** inside it.
  A match is a pair of elements, one in the outgoing region and one in the incoming one,
  that show the same ink.
  The outgoing element travels from its place to the place of the incoming one,
  and the incoming element travels from the place of the outgoing one to its place,
  so the two are at one position at every moment.
  Their opacities are those of the crossfade, `1 - t` and `t`, which `plus-lighter` adds to
  one, so the pair reads as one opaque element on the path and a pair whose colours differ
  reads as the interpolation of the two colours.
  Nothing is cloned and no opacity is touched other than the one the crossfade animates.
  Unmatched content fades out or in where it is.
  The translations are animation effects and never inline style, so a slide at rest carries no
  morph translation, and the outgoing element jumps back to its place when its animation
  ends, at which point its opacity is zero.
  See *Resolved Design Decisions* for what counts as a match
- a slide boundary crossfades the two **slide containers** by the same means.
  The containers inside the stage, which isolates, take `plus-lighter`,
  and the outgoing container stays laid out until the two have crossed.
  The crossfade lasts for the duration of the slide's `init`,
  which is `--animo-transition-duration` unless the `init` states one,
  rather than `--animo-primitive-duration`.
  The crossfade is not scoped to regions, because two slides share nothing that has to hold
  still, so the whole container is the unit.
  A duration of zero is a hard cut whatever the transition,
  and takes the path with no animation at all, which shows one container in place of the other.
  The slide crossfade differs from the epoch crossfade in two ways,
  and both follow from measurements rather than from choice.
  A slide that takes no part in a boundary is hidden with `display`,
  while a frame is hidden with `visibility`.
  A frame nobody is watching has to keep the geometry that the morph reads,
  while such a slide is needed neither for its ink nor for its geometry,
  and laying out every slide of a long deck costs seconds of first paint.
  The deck's surround is also a colour on the page rather than on the stage,
  because the stage isolates the blend,
  and the background of the stage would otherwise be added into both slides
  (see *Findings* for both)
- a slide boundary that pushes, covers or wipes animates `translate` or a `clip-path` inset on
  the two containers instead.
  A transition is a function of the boundary's owner, which is the slide with the higher number,
  and of a progress `p` that runs from 0, where the owner has not arrived, to 1, where it has.
  A forward step animates each container from what it shows to the state at 1,
  and a backward step to the state at 0, which is the mirror that *Timing* prescribes.
  A slide that had no layout before the step starts at the far end.
  The owner comes later in the document, so the owner is in front in both directions.
  These transitions overlap two opaque slides, which `plus-lighter` would add together.
  Both containers therefore take `mix-blend-mode: normal` until the deck moves again,
  which is as long as the slide being left keeps its layout.
  A single slide renders the same under either blend (see *Findings*).
  The stage clips a slide that is pushed out of it

The HTML presentation rests on the following rules:

1. Continuous state is applied to **every** occurrence of a tag in every rendering of every
   stack at once, not only in the rendering being shown. Entering an epoch therefore never
   needs re-initialisation, and a subslide that is both structural and continuous (a `replace`
   together with a `move`) animates in lockstep
   in the outgoing and the incoming rendering, so the composite reads correctly. Operations on
   a tag that is absent from an epoch are no-ops in that rendering.

1. **The crossfade is scoped to the regions whose content state changed**, not to the whole
   frame. Only the epoch stacks of the changed regions are animated, one rendering fading out
   and one in, and nothing else on the slide takes part. Two mechanisms together make that
   true:

   - **The stack holds nothing but its region.** The renderings of a stack are the region's
     body laid out once per epoch and nothing else, so the outgoing rendering has no ink
     outside the region's footprint, and the containment outside the region is exact *by
     construction*.
     A rendering that is not being shown is hidden with `visibility: hidden`
     rather than `display: none`, because `visibility` keeps the rendering laid out,
     so the morph can still read its geometry.
     Every rendering of the stack that is still painting takes part in a crossfade,
     not only the one the step is leaving.
     A boundary crossed while an earlier boundary is still running
     finds more than one rendering painting the region.
     Those renderings then all leave on the new boundary's clock, under one easing,
     while the incoming rendering arrives under the complement of that easing.
     Their opacities therefore still add up to one,
     whatever each rendering was showing when the boundary began (see *Timing*).
     A step may also cross more than one boundary at once, as a backward step over a join does.
     Such a step carries the stacks of all the boundaries it crosses, each stack once.
     This is the same situation reached from the other side, and it uses the same clock.
     The boundaries it crosses belong to steps that the deck ran through without stopping,
     so the only clock left is the clock of the step itself,
     and the timings that the operations of those steps stated are dropped with their schedules.
     The boundaries that such a step crosses lie in the slide it stands on,
     or in the slide it enters when the join it walks back over ran out of a slide.
     The handover is the same in both cases.
   - **`plus-lighter` on the renderings makes the two halves add, inside a container that
     isolates.** The renderings of a stack are siblings in one group, which carries
     `isolation: isolate`, so the outgoing rendering at `1 - t` and the incoming at `t` come to
     exactly one opaque region, and nothing dips.
     Without the isolation, chromium 151 and webkit 26.5 also add the two halves to the ink
     under the region, as measured with the stack a few groups deep,
     while firefox 153 needs no isolation.
     A single visible
     rendering added to a transparent backdrop is that rendering, so the blend changes nothing
     outside a transition.

   The measured cost is a rounding error of 1/255 inside the region,
   against 62/255 for a plain opacity crossfade, and nothing at all outside the region
   (see *Findings*).

1. Animo must emit **only** the individual transform properties (`translate`, `scale`) and
   never the `transform` shorthand, which would clobber typst's own positioning (see
   *Findings*).
   `transform-box: fill-box` and `transform-origin: center` make a `scale` grow the element in
   place, and they fall under a similar prohibition.
   They also re-anchor the `transform` attribute of the element,
   so on a group that typst positioned they move the group's content (see *Findings*).
   The runtime therefore writes both properties on the slot it is about to transform,
   and never as a rule in the stylesheet, which cannot tell a slot from a region's content.
   A resize and a shape morph also animate `d` and `stroke-width` on the two paths they pair.
   Neither property is a transform, and neither is ever written as inline style,
   so a path at rest shows its attributes.

1. Continuous state and boundary state get **separate nested slots**. `tag` wraps its body
   twice, in two wrappers of the same kind, so every tag site emits a labelled outer group with
   an unlabelled inner group inside it (see *Findings*).
   Continuous primitives address the inner group (`[data-typst-label="x"] > g`).
   Everything that belongs to an epoch *boundary*, which is the region crossfade and the morph,
   addresses the labelled outer group.
   CSS gives each element only one `translate` and one `scale`,
   so the split is what keeps the two classes from clobbering each other.
   The order follows from how a boundary effect is measured:
   it is measured in the coordinates of the frame
   and must sit *above* the continuous transforms rather than inside them,
   or a tag that is being scaled or (later) rotated while its region reflows
   moves by the wrong amount in the wrong direction.
   The morph measures a match on the screen and maps the difference into the user space of
   the parent of the element it translates, through the inverse of that parent's
   `getScreenCTM()`, which holds every transform above the element, typst's own included.
   Opacity is exempt from the ordering argument, since the two slots simply multiply,
   but it follows the same convention.

1. **`pan` belongs to the canvas element, not to what is inside it.**
   `pan` is a slide primitive, so it must not be applied per epoch.
   The body and its stacks sit in the frame that the canvas holds,
   so moving the canvas moves all of them together and keeps the crossfade registered.
   The canvas element is also the one place where Animo applies a transform outside an SVG
   group.
   The prohibition of rule 3 does not apply there,
   but `translate` is used there too, for consistency and to leave `scale` free for a future
   zoom.
   A background or overlay that is content belongs to the viewport rather than to the canvas.
   In HTML, each layer is therefore a separate frame beside the canvas element,
   rather than ink in the canvas's frame, and a pan moves the canvas between them.
   On paper, the layers are placed on the page before and after the panned canvas.
   One frame per layer and per slide covers every state and every epoch,
   because neither layer may hold a tag or a region, so neither can depend on an epoch.

**How the plan reaches the browser.**
The resolved display state of every state of a slide travels as compact JSON, keyed by tag name,
in a `data-animo-plan` attribute on the slide container.
It sits beside the `data-animo-slide` and `data-animo-states` attributes that the runtime also
reads.
The plan is an attribute rather than a `<script>` element for two reasons.
The HTML parser escapes and unescapes an attribute value while typst writes script content raw,
so a tag name can never break the page.
A browser's element inspector also shows the attribute beside the slide it belongs to,
so a step that misbehaves becomes a question about one value rather than about the whole
runtime.
Every state holds every addressed tag, even the tags it leaves at the identity.
The browser keeps a display state as inline style until something overwrites it,
so a state that said nothing about a tag would leave the previous state's style in place,
and stepping backwards would not undo what stepping forwards did.
State 0 is resolved from the timeline like every other state,
from which operation addresses a name first.
The runtime therefore applies what it is given and resolves nothing,
and no tag site reports a display state.
The one exception is the anchor of a `relto`.
Each state carries its pan, and each moved tag its position,
as an anchor and an offset per axis, `(relto:, offset:)`, with the offset in points.
The slide's margin and canvas size travel beside the states.
A tag's position cannot be read in HTML,
so the resolver keeps the anchor as a name and the runtime adds the position it measures,
as the paragraph on how `relto` finds its tag explains below.
Beside the display state, each state carries the `wait:` and the `hold:` it was given,
and each operation the `delay:` and `duration:` it was given, all in seconds,
because none of them can be resolved anywhere but at the moment the step runs.
A state also carries how long the step that enters it lasts,
which is the length that a backward step mirrors its operations about.
That length travels as two numbers rather than one.
The resolver can add up only the operations that stated a duration,
because the other operations take the `primitive-duration:` of the deck,
which lives in the stylesheet.
The resolver therefore hands over the largest end it could compute
and the largest delay of the operations it could not,
and the runtime adds `--animo-primitive-duration` to the second number.
A step that states no timing at all carries neither number,
and lasts exactly one `primitive-duration:` of the deck.
Both gap numbers travel rather than one resolved number per gap,
because the gap across a slide boundary is timed by two slides and emitted by two calls,
so the runtime is the first place that sees both sides of it.
Each state also carries its resolved `handout:` flag,
so that a view of the deck that shows one state per slide can show the state the handout shows.
Each boundary carries the names of the tags it changes,
each with the timing and the `transition:` of the operations that changed it,
and nothing for `auto`.
The runtime finds the stacks that a boundary crosses by those names,
because a stack holds the groups of the tags laid out in it,
and by comparing the renderings of each stack on the two sides of the boundary.
A `wrap: none` tag becomes no group,
so the boundary also names the tag whose timing and transition a stack takes,
keyed by the group of the region that holds the stack.
Only the membership reports know that tag.

**Motion is driven by the Web Animations API**, not by CSS transitions.
A step writes the new display state as inline style,
and animates from what the element was showing to that new state.
The inline style is therefore the state, and the animation is only how the element got there.
An interrupted step therefore continues from where it is,
a backward step lands on exactly the geometry the earlier state had,
and a restore needs no transition to suppress.
A backward step differs from a forward one in only two ways.
Every effect of a backward step is mirrored about the length of the step it undoes
(see *Timing*).
A backward step may also rewind the slide it enters,
which happens when a join ran out of that slide.
Every animation of a step is created in one task, and none of them is given a start time,
so the browser starts them all on the same frame.
The step therefore has one clock, and an epoch crossfade joins that clock.
Reading that clock off `document.timeline` instead would be wrong,
because the timeline does not advance while the page draws nothing (see *Findings*).
A step animates only the properties it changes,
because a property that holds still in the keyframes stops chromium from drawing the properties
beside it (see *Findings*).
By default, a primitive takes `0.4s` and eases in and out.
The duration and the easing are custom properties on `:root`,
which the deck writes from its `primitive-duration:` and `easing:` arguments,
so the values live in the stylesheet rather than in the runtime.
A slide boundary has a third such property, `--animo-transition-duration`,
which is also `0.4s` by default, so a deck of hard cuts states only one argument.
An operation that states a `duration:` overrides `--animo-primitive-duration` for
itself, and an `init` that states one overrides `--animo-transition-duration`,
also where the `transition-duration:` of the deck is zero.
Reduced motion is decided in one place, the custom property `--animo-motion`.
The media query `prefers-reduced-motion: reduce` sets it to `none`,
and every step then snaps, as a deep link and the first paint do (see *Timing*).

An operation's `delay:` and `duration:` become the delay and the duration of the effect
rather than separate timers, which keeps the step's one clock intact.
A gap's `wait:` or `hold:` is the only timer the runtime sets.
That timer is armed when a step is entered,
and cleared whenever another step is entered, whatever entered it,
so a presenter stepping by hand is never racing a clock that is still counting.
A backward step arms the timer in the other direction (see *Timing*),
so the deck travels back over the gaps it travelled forward over.
A backward step is also the one step that may land more than one state back,
since it walks back over the joins it finds on the way.

**How `relto` finds its tag, and `move` its target.** The anchor of a tag is the top-left corner
of the first site of its name in document order, as the body laid it out, which is the corner of
the tag's outer wrapper.
The display state of the tag sits inside that wrapper and does not enter the anchor,
so `relto` means the same in every state, and an absolute `move` is idempotent.
One mechanism serves both primitives:
`pan` reads the anchor of its `relto`, and `move` reads the anchor of its `relto` and of the
tag it moves.
The two targets read the corner by different means, because positions cannot be read in HTML.
The browser reads the origin of the labelled group, mapped into the user space of its frame,
when the slide is first shown and before anything is written on it.
On paper, typst cannot use the position of the wrapper,
which for a box on a line is the line's baseline (see *Findings*).
Every tag site therefore carries a zero-size marker at the corner of its outer slot.
Every page also carries a marker at the canvas origin,
which turns a position on a panned page back into a position on the canvas.
Only the paged target emits these markers, so the groups the browser addresses are untouched.
Over every kind of tag site measured, the anchors that the two targets resolve differ by at most
0.0005 pt, and a pan read back off the rendered page differs by at most 0.005 pt
(see *Resolved Design Decisions*).

"The first site" needs a qualification,
because a tag whose content changes is not laid out in every rendering of its slide.
The anchor is the first site in document order **in the first rendering that lays that site
out**.
In HTML, this is the first site in document order among the sites of the lowest epoch.
A site outside every stack counts as epoch 0,
because the body around the stacks is laid out for every epoch.
On paper, it is the site on the first page that carries the marker.
Document order alone would disagree with paper,
because a site that only a later epoch lays out may come earlier in the body
than one that every epoch lays out.
The HTML rule and the paper rule coincide in the static presentation,
whose pages are the states in order,
so its first page that holds the tag shows the first state of that same epoch.
The handout renders a subset of the states, so it reads the first page it *keeps*.
This is the one place where the rule depends on the mode rather than on the mechanism.
The refusal below keeps that difference harmless,
because an anchor can only differ between two renderings of a slide if a transform sits above
it.

Anchors are resolved once per slide rather than once per state.
On paper, that is one introspection pass over the slide's pages,
and in the browser, one measurement when the slide is first shown.
Only the tags that the plan actually names are read.
A position whose `relto` names the moved tag needs no reading at all,
since the two terms cancel whatever that anchor is.

Two refusals depend on anchors, and neither can be decided before the body is laid out.
They are a pan or a move relative to a tag the slide does not have,
and an anchor read from inside a tag that the timeline moves or scales.
Both can only be detected from `query`, and a panic raised there may be swallowed.
Both checks are reported reliably because of where they run.
Each runs in a separate context block after the slide, which emits nothing.
The checks compare the timeline against the tag sites that the slide's rendering reported,
which are the site reports in HTML and the anchor markers on paper.
Each report carries the tags whose display state encloses the site.
A failing check then empties only the context block it runs in.
A site that is reported one layout pass late is forgotten together with the errors of that pass,
and a tag that is really missing fails the pass that typst ends on (see *Findings*).

The view's `within` entry exists for the second refusal.
Which tags enclose a site is a fact about the body, and the body is opaque to the resolver.
A site therefore learns which tags enclose it from the view it is handed,
as it learns everything else about its slide.
Every enclosing site that carries a display state,
which is a wrapped tag or a named region, extends that entry.
Only a name the timeline addresses with a continuous primitive extends it,
so a deck with no continuous primitive threads nothing.

Because one rendering covers all subslides of its epoch, stepping within an epoch needs no
re-rendering and motion is genuinely smooth. The cost of structural operations is paid in compile
time and page weight, not in interaction.

**Static presentation.** The static presentation has one page per state.
Each page is a snapshot of the *viewport* at that state, clipped out of the canvas,
with the background under it and the overlay over it.
Nothing moves.
The `move`, `scale` and `pan` primitives become discrete jumps between pages,
and `replace`, `remove` and `apply` are simply rendered in place.
A panned subslide is therefore a page showing a different part of the canvas,
so panning survives into the paged output.
Everything under *Timing* is absent rather than approximated.
A page has no clock, so `wait:`, `hold:`, `delay:` and `duration:` say nothing here.
Neither does a transition, which describes what happens between two pages
that are simply consecutive.

**Static handouts.** The static handouts have one page per state whose `handout` flag resolves
to true.
By default, that is only the **final state of the slide**,
which shows the viewport at its final position, as in the static presentation.
Extra pages are asked for with `sub(handout: true, ..)`, and with
`init(handout: true)` for the slide's initial state. Pages are given up with
`sub(handout: false, ..)` and `init(handout: false)`, so an ordinary slide contributes one page
and an author who says so contributes any number, the empty one included.
A handout therefore loses content on a slide that overwrites it.
A `replace` destroys what it replaces, and only an explicit `handout: true` keeps it.
Animo cannot warn about this, because typst offers packages no way to emit a warning,
so the manual has to.
A panned slide loses content in the same way.
A handout page shows the viewport of its state rather than the whole canvas,
so `handout: true` is also how a view that a later pan leaves is kept.

**The file format is not an output type.** Both static types are paged modes, and typst exports
either of them to PDF, SVG or PNG.
SVG is suited to embedding a page in another document,
and PNG serves a consumer that needs a raster image.
Neither format says anything about which pages exist.
A multi-page export to SVG or PNG requires a page-number template in the output path.

### Scoping

Tags live in the scope of their slide, with no per-slide context object threaded through
the body:

- In the **HTML** output, CSS/JS selection is scoped to the current slide's container, so
  `[data-typst-label="line1"]` in slide 3 cannot affect slide 7.
  Such a selector naturally matches *all* elements with the same tag inside one slide.
  This is exactly the "several places, one tag" requirement,
  and it also applies continuous state to every rendering of every stack of the slide at once.
- In the **paged** outputs, `#slide` resolves its animation plan before rendering its
  subslides and hands the result to the body, so each tag site sees the plan of the slide it
  sits in.

Names share one namespace with the labels Animo emits for itself, since both end up as a
`data-typst-label` in the same output and the runtime addresses what it finds there. The prefix
`animo-` is reserved for Animo's own labels, and `tag` and `region` refuse a name that starts
with it.
An unnamed region needs a label,
because a boundary crossfades it and only a labelled box becomes a group at all.
An unnamed region therefore gets the label `animo-region-<n>`,
where `n` is the number of the region, which is the same in every output type.
A region inside an epoch stack counts once,
not once per rendering. The renderings of an epoch stack themselves take `animo-epoch-<n>` out
of the same reserved prefix.

The namespace is also shared with **the labels that the document defines**, which Animo cannot
reserve.
`#box[..]<x>` emits the same attribute as a tag of that name,
and nothing in the output tells the two apart.
The consequence is asymmetric.
Typst resolves a timeline through the tag,
so on paper a label that the document defines is never addressed.
The runtime resolves a timeline through the attribute,
so in the browser a label that the document defines is addressed.
A continuous primitive on a name that became no group on its slide is therefore refused
in every target, just like a `pan(relto:)` to a missing tag.
A misspelt name is the likely cause, the refusal costs a deck nothing it could have wanted,
and the alternative is an operation that does nothing on paper and something unintended on
screen.
The remaining case is a name that a slide uses both as a tag and as a label.
This is a collision inside one namespace, which is documented rather than refused,
because refusing it would mean that Animo polices the labels of the document around it.

The plan must be readable in the **HTML** output as well, because regions and implicit regions
need to measure their states while the body is laid out. There is no cycle: the plan is an
argument of `#slide` and does not depend on the body.

The plan is **provided**, not published.
`#slide` installs a show rule over its body,
and every tag emits a marker that the rule replaces with the tag's rendering for the view it is
given. A view has the following entries:

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
  rendering knows where that is.
  A tag site applies to its content what it is handed and resolves nothing itself,
  so the anchors are still read only once per slide;
- the **names a continuous primitive addresses anywhere in the slide**. A tag site that cannot
  be animated at all has to say so in state 0 rather than in the state that moves it, and a
  `wrap: none` tag only learns that it is being animated from this entry. The target of a
  `pan(relto:)` counts, since the browser reads its anchor off the tag's group;
- the **region** the content sits in, which consists of the key of the nearest region whose
  footprint is the same in every epoch, whether an explicit region bounds the content,
  and whether the content itself is laid out in every epoch.
  A tag inside an explicit region reserves no separate footprint.
  Every site reports the key of its region, which is how the regions that a boundary redraws
  are found, since only layout knows which tags a region holds;
- the **tags whose display state encloses the content**, outermost first. Every site reports
  them, which is how an anchor read from inside a transformed tag is refused (see
  *Architecture*).
  Only a wrapped tag site and a named region extend the entry,
  since nothing else carries a display state.
  They extend it only when a continuous primitive addresses their name,
  since a name the timeline never addresses can transform nothing.
  A deck with no continuous primitive therefore threads nothing and pays nothing.

A `per-subslide` uses a **second** kind of marker.
The two kinds of marker are answered in different places.
A tag marker is answered by the body's view and refused anywhere else,
while a stack marker is answered wherever a slide lays content out,
including the background and the overlay.
The second marker is handed the **stack view**,
which is the part of a view that content outside the body may have:
the number of states, and which of them is being laid out.

A state variable cannot do this,
because `state.get()` inside `measure(..)` resolves at the enclosing context's location,
so a caller cannot set a state, measure, set it again and measure again,
which is exactly what a region has to do to size its footprint over its epochs.
A show rule does reach inside `measure`, providers nest with the innermost winning,
and the label of the marker does not reach the output (measured; see *Findings*).
Because a view is an argument rather than a document position,
a deck that wraps `#slide` in a custom function changes nothing.

A few things about a slide are published rather than provided, and none of them is the plan.
The slide counter and the flag that says whether this slide is counted are published because
`slide-number()` is an ordinary counter read that an author writes anywhere, in the body or in
a layer, and because both are constant over the slide, so nothing about them has to vary inside
a `measure`. The deck-wide step counter is published for the same reason and is read from
inside a stack.
The last one is needed for a diagnosis.
`#slide` marks with a state that a body is being laid out, so that a tag outside any slide can
be diagnosed at the tag site. That diagnosis cannot come afterwards, because a marker nobody
replaced is indistinguishable from one that was (measured; see *Findings*), and a tag whose
marker is never replaced would simply drop its content.

Duplicate labels across a document are permitted by typst and cause no error.

### Output mode selection

One source file is compiled once per output type.
The HTML target is detected automatically with `target()`.
The two static modes are selected explicitly, and the default is `handout`:

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

A deck reads which output type it is compiled to with `output-type()`, a context function that
returns `"html"`, `"presentation"` or `"handout"`.
These are the strings the command lines above already use: `target()` returns `"html"`, and the
two paged modes are the values of `--input animo=`.
`target()` alone cannot answer inside a slide, because it returns `"paged"` inside an
`html.frame` (see *Findings*), so every slide publishes whether the document is compiled to
HTML before it lays anything out.

The mode and the file format are independent, so either static type exports to SVG or PNG as
well. Multi-page export to those formats needs a page-number template in the output path:

```bash
typst compile -f svg talk.typ 'talk-handout-{p}.svg'
typst compile -f svg --input animo=presentation talk.typ 'talk-presentation-{p}.svg'
```

### Consequences of confining reflow to regions

Bounding reflow by regions, rather than forbidding it or letting it reach the whole slide,
has the following consequences:

1. A slide with no structural operations needs exactly **one** `html.frame`,
   so the simple case costs nothing extra.
1. The HTML and paged outputs lay out **identically**, because both reserve space for hidden
   elements and both reserve the same region footprints, measured the same way.
1. Smooth animation remains available for every continuous primitive,
   since the frame geometry does not change within an epoch.
1. The "occupies no space" state is available in bounded form,
   as `remove` and as the initial state that a `reset` declares.
   Without regions, this state would reflow the whole slide,
   while inside a region reflow is exactly what it is supposed to do.
1. Content that moves because of reflow jumps to its new place behind a crossfade, unless the
   primitive that causes the reflow names `morph()`, which carries the content that both
   renderings share to its new place.

## Resolved Design Decisions

These were the open questions of the earlier drafts.
They are settled, and the evidence is in *Findings*.

- **Is this feasible in typst?** Yes, for all three output types. The enabling mechanism is the
  `data-typst-label` attribute, which makes tagged content individually addressable in the
  SVG that `html.frame` produces. Smooth per-element animation in the browser has been
  verified on real typst output.

- **Can content and style change, with reflow?** Yes, but only within a bounded area, and
  only by re-rendering that area. Typst cannot relay out a fragment of an existing SVG, and
  the browser cannot lay out typst content,
  so the *only* available mechanism is to render the slide again for the new content state
  and swap the rendering.
  The region concept exists to keep the cost and the visual consequences of that swap bounded.
  This was verified end to end.
  Measuring each epoch of a region and forcing the maximum footprint keeps everything outside
  the region pixel-identical between epochs, in the browser as well as on paper.

- **Why are two of the keys of the subslide info called `step` and `steps`?** Because a progress
  indicator is read as how far through the talk the presenter is, and that is what those two
  numbers are written for. Everywhere else in Animo a **step** is the transition from one
  subslide to the next, so the *n*-th subslide of a deck is reached by *n-1* steps, and `steps`
  counts subslides rather than transitions. These two keys are the one place where the word for
  the presenter's action names what the presenter arrives at. The alternative was `subslide` and
  `subslides`, which says the same thing and reads worse in the expression a progress bar is
  written as.

- **Why is a subslide's `handout:` flag a key of the subslide info rather than a function
  like `slide-number()`?** Because the flag differs between the subslides of one slide,
  it has the problem that *Slides* solves with `per-subslide`: an HTML frame covers a run of
  subslides, and a value read when the frame is rendered would be one value for all of them.
  The dictionary is called the *subslide info* rather than the *subslide numbers*, because it
  holds the flag beside the numbers.

- **What does `output-type()` return?** One of `"html"`, `"presentation"` and `"handout"`.
  These are the strings a deck is already compiled with: `target()` returns `"html"`, and the
  two paged modes are the values of `--input animo=`. The function is named after the *output
  types* that this document and the guide already describe. It is a context function, as
  `slide-number()` is, because it reads `target()` and a state.

- **What does a boundary crossfade when no region bounds the change?** Nothing, because such a
  change is refused. A `wrap: none` tag outside an explicit region has no box, so there is no
  area that could hold its change, and Animo refuses a structural primitive on it in every
  output type rather than only in the one that could not show it. The refusal names the two
  ways out, a wrapper or a region around the tag, which is the advice this document already
  gives for a change that should read well.
  An earlier answer crossfaded the whole rendering of the slide, which was possible while HTML
  laid out the whole slide once per epoch. With the epoch stacks in the regions there is no
  whole rendering to fade. Keeping one for this case would take a second structure chosen from
  the layout reports, and a structure that depends on the reports it produces did not converge
  when it was tried.

- **Which regions hold an epoch stack?** Every region that sits in no other region, and no
  other. A region inside the rendering of a stack is laid out once per rendering already, so a
  stack there would multiply the renderings by the epochs again. The outermost region is
  therefore the one that crosses a boundary, with everything inside it, and two operations that
  change two regions inside one region at one boundary have to agree about their timing and
  their transition, as two operations inside one region do.

- **Where does the crossfade's blend go?** On the renderings of an epoch stack, with
  `isolation: isolate` on the group that holds them. A stack holds nothing but its region, so
  the outgoing rendering paints nowhere outside the region, and no `visibility` scoping is
  needed for the containment.
  The isolation keeps the sum of the two halves off the ink under the region
  in chromium 151 and webkit 26.5, as measured.
  It is written as `isolation` because it changes nothing at rest,
  while `opacity: 0.999` changes pixel values and `filter: opacity(1)` does not isolate in
  webkit.
  An earlier answer put the blend on whole-slide renderings, which were the outermost groups of
  the slide's one frame, with `visibility` scoping the outgoing one down to the regions it
  handed over.
  The stacks make the scoping unnecessary and the slide lighter,
  because the page weight and the node count now follow the regions rather than the whole slide.

- **How does a crossfade read when the region's content really reflows?** It depends on the
  change, and the split is sharp enough to be an authoring rule rather than a caveat.
  A **replacement** reads as a dissolve and works well.
  One text fades out where another fades in, and the eye reads it as a transition.
  Its one flaw is repeated content.
  Text that is the same in both epochs but sits at two heights ghosts against itself,
  and reads as doubled rather than as moving.
  A **small edit inside a large paragraph** reads badly.
  Everything after the edit shifts by a few pixels,
  so the rest of the paragraph shows two copies of the same words a few pixels apart,
  which cannot be read.
  The part *before* the edit stays crisp because it did not move.
  This is the case the morph exists for, and it is why the transition of an epoch
  boundary is a named, swappable one from the first release of Animo.
  The authoring advice is to name `morph()` on the primitive when content shifts,
  and otherwise to put a region around what is replaced wholesale
  and to keep what merely shifts out of it.

- **Does every slide compute the union of its placements?** No. Only a slide whose timeline
  pans does.
  The union is the one part of laying out a slide whose cost grows with the number of `#place`
  calls in the body.
  The cost becomes noticeable in a deck that draws data as thousands of small placed marks.
  Measured with typst 0.15.0 linked against musl, a slide with 10 000
  placements over 20 states took 3.59 s and 972 MB with the recording and 2.93 s and 812 MB
  without it.
  Only `pan` reads the canvas.
  The viewport clips in both targets, and an offset given as a ratio is refused,
  so no length in a timeline is a fraction of the canvas either.
  A slide with no `pan` in its timeline is therefore drawn identically whatever canvas it is
  given, so skipping the union saves time without changing any output. An author who does pan and
  wants the cost gone states `canvas:`, which skips the recording as well.

- **Should the whole slide body be a region?** No. The body stays a plain layout in which
  nothing reflows, and regions are opt-in. If the body were a region, every structural operation
  would relay out the whole slide, which would break continuous animations in flight (their
  base geometry would move under them) and make the crossfade visible everywhere. Opting in
  per region also documents the author's intent about where the reflow is allowed to happen.

- **How are group-like containers and tags related?** They are orthogonal and both are kept.
  A region is the *unit of reflow and redrawing*, and a tag is the *addressable handle*.
  A tag not inside an explicit region gets a separate implicit region,
  so the simple case needs no extra syntax,
  and `region(name: ..)` covers the case where the container itself must be animated.

- **Is the name `group` right for the container?** No, it is called `region`. `group` collides
  with two neighbouring meanings, which are cetz's `draw.group`
  and the SVG `<g>` groups that Animo itself emits.
  The point of the construct is that it is a *bounded area* of the slide.

- **How much structure does `apply` need?** `apply(tag, ..fns)` with content-to-content
  functions only. `sanor`'s richer `case()`/`object()` machinery exists to cache object state
  across subslides.
  Animo has no such state, because its plan is resolved to per-epoch content states in one pass.
  Named style properties would also require guessing which `set` rule a property
  belongs to, which Animo cannot do without inspecting content.

- **Where does time-dependent content live: the timeline or the body?** In the timeline, as
  `replace(tag, body)`.
  The alternative declares several content values at the tag site
  and selects among them from the timeline, in the style of `sanor`'s named cases.
  It is expressible under the measuring mechanism above, so feasibility does not decide it.
  The interaction with duplicate tags decides it,
  and that interaction matters most for the morph:

  - Because every site sharing a tag name receives the **same** replacement content, the sub-tags
    inside it, their multiplicities and their document order match automatically between the
    outgoing and the incoming epoch rendering.
    That is exactly the precondition that the morph's pairing rule needs.
    Per-site variants break this precondition.
    Two sites named `eq` could sit at different variants in the same epoch,
    so the two renderings could hold structurally different sub-tag sets,
    and the pairing becomes ambiguous in precisely the case that morphing exists for.
  - Variants impose an **arity agreement** across same-named sites: every site named `x` must
    offer the variant the timeline asks for. `sanor` enforces its equivalent by panicking in
    `resolve-case`. `replace` has no such failure mode, because it hands the same content to all
    sites by construction.
  - With `replace`, the timeline stays a complete account of every content state,
    while a call such as `switch("eq", 2)` means nothing without looking up the body.
  - `apply`, `remove` and `reset` cannot move into the body anyway, so variants would split
    time-dependent content across two places rather than unify it.

  The argument for the other side is real, and is recorded here.
  With the content in the timeline, reading the body alone does not tell how tall a region will
  be, since the content that determines its footprint is declared elsewhere.
  That is a legibility cost rather than a
  correctness one, and it is outweighed by the pairing property above.

  If per-site content is ever genuinely wanted, the answer is distinct tag names, not variants.

- **Does the handout show intermediate content?** Only where the timeline says so. The flag
  defaults to `auto`, which gives a page to the final state of each slide and to no other, and
  `sub(handout: true, ..)` and `sub(handout: false, ..)` override it in either direction.
  One page per epoch was considered and rejected,
  because it makes the page count of a handout depend on an implementation concept (epochs)
  rather than on an authorial decision,
  and it silently inflates handouts for slides that merely restyle something.
  The manual must instead be explicit that
  `replace` and `remove` destroy content and that `handout: true` is how it is kept.

  A three-valued flag is used rather than a boolean that defaults to `false`
  with the final state added on top.
  With such a boolean, the final state would be a rule written somewhere else,
  and there would be no way to say that a slide's last state is a punchline
  the audience should not read ahead. With
  `auto` the flag is the whole answer, the default costs nothing, and every page of the handout
  is one a subslide asked for.

  The flag is a **keyword argument on `sub`**, not a free-standing `handout()` between `sub`
  calls.
  The same argument applies as for `wait:` and `hold:` under *Timing*.
  A marker whose meaning depends on its position in the block is harder to read and to validate
  than a keyword on the subslide it belongs to.
  A keyword also keeps one more name out of the top-level namespace,
  and it keeps a timeline block down to `sub` calls and at most one `init` before them,
  which is what lets the timeline refuse anything else
  (see the `import *` footgun under *Findings*).

- **Can the handout keep a slide's initial state?** Yes, with `init(handout: ..)`.
  The flag belongs to a state, and the initial state has no `sub`,
  so it is written on `init`, which is the call that describes that state,
  with the three values that `sub(handout: ..)` takes.
  This matters as soon as a timeline restores what the body hides,
  since the handout then keeps the completed slide rather than the state the timeline filled in.
  With `init(handout: false)`, a slide with no `sub` at all can also be left out of the handout.
  See the next entry for why the flag is on `init` rather than on the slide or on a leading `sub`.

- **Where does a slide say what happens to its initial state?** In `init(..)`, the first call
  of its timeline, which takes the transition into the slide, its `duration:`, the `wait:` and
  `hold:` around state 0 and its `handout:` flag.
  The arguments of `slide` then say what the slide is,
  namely its canvas, its layers and whether it is counted.
  The timeline says when anything happens to the slide,
  which is the separation the package is built on.
  The first answer was a leading `sub` that carried the flags and nothing else.
  Such a `sub` does not describe the initial state, but adds a second state with the same pixels.
  That shifts every subslide index by one,
  and the leading `sub` has to be written `sub(wait: 0, handout: true)`
  to avoid a presenter click that changes nothing.
  The second answer was a set of slide arguments, `transition:`, `wait:`, `hold:` and
  `handout:`, beside the ones that describe the slide.
  Those arguments mixed what and when in the slide's signature,
  and put the transition of the slide in a different call from the transitions of its regions.
  `init` adds no state, so it keeps every subslide index,
  and it takes the keywords of `sub` with the meaning they have there,
  so the initial state is described in the same way as every other state.
  `init` is a separate call rather than a keyword of the first `sub`,
  because a slide without `sub` has an initial state too.
  A timeline holds `init` at most once and before its first `sub`,
  so its position carries no meaning,
  which satisfies the condition that the previous entry puts on a call between `sub` calls.

- **Where is the timing of a transition stated, and what is a hard cut?** On the call that
  causes the change, and a hard cut is a duration of zero.
  A structural primitive states the `delay:` and `duration:` of the transition of its region,
  just as a continuous primitive states the `delay:` and `duration:` of its operation,
  so one `sub` times all its operations in the same way.
  `init` states the `duration:` of the transition into the slide, because no primitive
  causes that change, and `wait:` takes the place of a delay there.
  A transition is then only what the crossing looks like.
  A cut is the crossing that takes no time, so `duration: 0` with any transition is a cut,
  which the runtime handles as one code path.
  A transition named `cut` would have been a transition that refused a duration.
  It follows that a deck's durations are defaults that a stated `duration:` overrides, also
  when the default is zero, since otherwise a deck of hard cuts could not push one slide in.
  The cost is that `init(push())` in such a deck is a cut, so the manual says that a named
  transition in a deck of cuts needs its duration too.
  Reduced motion then needs a separate property, `--animo-motion`, because zeroing a
  default no longer stops a stated duration.
  A per-slide `easing` was dropped together with the dictionary form of a transition,
  because a primitive states no easing.
  An easing on every call is left for when a deck needs it.

- **Must the syntax become heavier (body as a function)?** No. `sanor` threads a mutable
  context through the body (`s => ([body], s)`) only because it accumulates actions while
  the body is evaluated. Animo passes the plan as an argument instead, so the body stays an
  ordinary content block, even though tags and regions now *read* that plan
  while the body is laid out.
  That read is a `context` read rather than a threaded accumulator.

- **Is a context object `c` needed?** No.
  In `sanor`, `c` provides two things, and Animo obtains both otherwise.
  Scoping is handled by the slide container in HTML and by per-slide state in paged output,
  and a namespace for the primitives is handled by the cetz-style block-scoped import.
  Without `c`, `tag` is also usable in any context,
  including inside `context` blocks and third-party packages.

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
  With regions, this is more than a preference, because the body's *layout* depends on the plan,
  so the plan must be known before the body is laid out.

- **HTML export: `reveal.js` or custom?** Custom. Animo animates `<g>` nodes inside an
  inline SVG, so reveal.js's DOM-fragment machinery contributes almost nothing while
  imposing a separate slide model, CSS cascade and scaling.
  Panning is not part of reveal's model either,
  which is why `touying-exporter` turned to impress.js for it. `slipst`'s complete
  custom runtime is ~214 lines of TypeScript plus ~68 lines of CSS, so the cost is small.
  Animo should use plain JavaScript, inlined with `read()`, to avoid requiring a node
  toolchain for a package installed from Universe.

- **How large is a slide, and what does `pan` move?** A slide is a viewport onto a canvas that
  is at least as large as the viewport.
  `pan` moves the viewport, and content outside the viewport is clipped
  and never flows to a next slide.
  The canvas is sized automatically from the content by default (`canvas: auto`)
  and can be stated explicitly.
  Automatic sizing cannot use typst's own `auto` page or block sizing,
  because `#place` is out of flow and contributes nothing to it.
  It cannot use position introspection either, which does not work in HTML.
  It uses a `show place:` rule over the body instead, which is available in both targets.
  See *Canvas and viewport* and *Findings*.

- **Is the max-footprint rule tolerable?** Yes, with the authorial remedies, and there is no
  "pin the footprint to state *i*" option. On a region that grows from one line to a five-item
  list, `align: bottom` turns the gap into spacing above the line, and a given `height` clips the
  larger states without any sign, which is all a pin option would do. `align` defaults to `top`
  rather than `top + left`, because a horizontal component overrides an inherited alignment
  (see *Findings*).

- **Does `layout(size => ..)` give a region the right width?** In a container whose width does
  not depend on its content, yes.
  In a container that takes the width of its content, `layout` hands over the whole body width,
  and the region cannot detect this.
  That is a documented restriction with `width:` as the remedy (see *Findings*).
  Regions are numbered in document order within a rendering,
  and a region inside changing content borrows the key of the region around it,
  so the numbers agree across epochs.

- **Is the name appropriate?** `animo` is unused on Typst Universe.
  The name refers to its Latin interpretation.
  *Animo* is at once the first person singular of *animare*, "I bring to life", and the
  ablative of *animus*, "with mind, with intent",
  which states the package's position in a single word:
  an animation earns its place on a slide when it is put there deliberately,
  and so does everything else on that slide.
  Anything added without a reason competes with the speaker for the audience's attention.

- **Does `tag` default to `box`, or detect block-level bodies?** It detects,
  but it decides between hugging and filling rather than between inline and block.
  A `box` and a `block` render identically for content that already sits between paragraph
  breaks.
  What differs is hugging versus filling, so `wrap: auto` chooses between `box` and
  `block(width: 100%)`.
  The detection is a measurement rather than an inspection of element kinds.
  It puts a zero-sized box on each side of the body and compares heights.
  Over 31 constructs the separation was exactly 0 pt for every inline case and at least
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
  so the inline style is the state and the animation is only how the element gets there.
  Reversible stepping, an interrupted step that continues from where it is,
  and a deep link that needs no transition to suppress all follow from that without extra code.
  CSS transitions handle none of the three well.
  The Web Animations API also makes a mid-flight assertion reproducible,
  because a test pauses the animation and sets a `currentTime` instead of racing it.
  It is also where the `duration:` of an operation and the shared clock of the epoch crossfade
  belong.
  The default duration and easing live in CSS,
  as `--animo-primitive-duration` and `--animo-easing` on `:root`,
  beside the `--animo-motion` that `prefers-reduced-motion: reduce` sets to `none`.
  The deck writes them there from its show rule arguments,
  so an author states them in typst rather than in a `#slide` argument.
  A duration of zero is a step that snaps, which is the same path a deep link takes.

- **How does an author state the deck's tempo?** As three arguments of the deck's show rule,
  `primitive-duration:`, `transition-duration:` and `easing:`,
  which the deck writes into the `:root` block of the deck stylesheet beside its geometry.
  The values end up in CSS, beside the `--animo-motion` that `prefers-reduced-motion: reduce`
  sets, and the runtime reads them at every step, so restating one costs no second pass over
  the timeline. Leaving
  the author to write that CSS was the first answer, and it was wrong on two counts. Writing a
  `<style>` element from typst means calling `html.elem`, guarded by a `target()` test because
  the paged outputs have no `html` module, which is markup in a deck's source and a guard an
  author has to know about.
  Such a stylesheet also lands after the stylesheet of Animo,
  where it outranked the reduced-motion query in chromium 151 and firefox 153,
  so a deck that restated its tempo quietly took the guarantee away from the reader.
  Making the query's declaration
  `!important` settles both that stylesheet and the `:root` block of the deck,
  because the guard then wins by cascade weight rather than by source order.
  An easing is checked against a list of
  five names in typst rather than passed through, because a timing function the browser
  rejects throws where the audience can see it, and because the list is what a reference page
  can state.
  The principle is narrow.
  Every setting that the runtime of Animo reads is stated in typst,
  which is not a promise to expose the page's styling,
  and `html.elem` stays available for what animo does not cover.

- **Where are `transform-box` and `transform-origin` written?** By the runtime, on the slot it
  is about to transform, and never as a rule in the stylesheet.
  The first answer was a single rule, `.animo-canvas [data-typst-label] > g`,
  which is the selector through which the continuous properties themselves are written.
  That rule was wrong for a reason that only showed up in a real deck.
  The two declarations re-anchor the `transform` attribute of the element
  as much as the properties beside them (see *Findings*),
  and a labelled group is not always a tag site. A region's
  footprint carries a label too, because the crossfade addresses it, and its children are the
  author's content rather than a slot, so the rule reached typst's glyph runs and moved each of
  them by its fill box. Every candidate selector that excludes a region's children is a
  guess about the shape of content Animo does not build: `:only-child` fails on a region holding
  one group, and `:not([transform])` would exclude a real slot the moment an inline footprint
  offsets one. Writing the two declarations where the transform is written needs no such guess,
  because the element is the one the runtime already holds. They are not tunable the way the
  duration and the easing are, so nothing is lost by taking them out of the stylesheet.

- **How do CSS-animated typst SVG groups look in motion?** Well enough that nothing about the
  defaults changes.
  Measurements in chromium 151 and firefox 153 (see *Findings*) show the following.
  A scaled glyph is drawn afresh at the scale it ends up at rather than stretched,
  so text stays as sharp at 200% as at its unscaled size,
  and strokes scale geometrically with it.
  That is what a figure needs, and it makes `scale` usable on text.
  A value under a running animation
  rasterises bit for bit as the same value in a style declaration, so the hand-off at the end of
  a step is invisible and there is no antialiasing seam at a subslide boundary.
  An author still has to know what a `scale` does.
  It scales about the centre of the element and nothing reflows,
  so a doubled paragraph overlaps its neighbours.

- **What does a handout page of a panned slide show?** The viewport of its state, exactly as the
  presentation shows it, with no `#slide` argument.
  The alternative was a page that shows the whole canvas scaled to fit.
  That suits a deck that pans,
  but not a slide whose canvas is merely a little larger than its viewport.
  `sub(handout: true)` already keeps any view a later pan
  leaves, and the manual says plainly that the handout does not show the canvas.

- **Do the two resolutions of `pan(relto:)` agree?** Yes, to within the rounding of the
  measurement, once both read the same point. Over ten kinds of tag site (placed, inline phrase,
  inline box, block, centred figure, math, heading text, grid cell, list item, a tag inside a
  tag), at windows 1280 and 640 pixels wide, the browser's pan differs from typst's by at most
  0.001 pt in chromium 151 and 0.005 pt in firefox 153.
  Reading the position that typst reports for the tag did not agree,
  because that position was a box height too low for every tag on a line.
  The agreement therefore comes neither from a tolerance nor from making one target
  authoritative. `relto` promises the corner of the tag's wrapper, and
  each target is built to read exactly that (see *Architecture*).

  **And do they agree about a `move`, which reads two anchors and subtracts them?** Yes, and an
  order of magnitude closer: at most 0.0005 pt over the same ten kinds of site, at the same two
  window widths, in both engines.
  The disagreement enters twice, once per anchor,
  and one of the two anchors is that of the tag being transformed,
  which is the case that an inline site makes awkward.
  Neither costs anything measurable.
  The figure is smaller than the one above because it is a different measurement,
  not because the mechanism is better.
  Here the `translate` that the runtime writes is read in the user units of the frame,
  while a pan is read off two boxes on the page.
  The 0.005 pt is therefore the error of reading a rendered pan,
  and 0.0005 pt is the difference between the two resolutions themselves.

- **Can a tag over raw cetz draw commands be made to work?** No, and Animo refuses it rather
  than ignoring it. A draw command is an array of closures built where it is written, a canvas
  body cannot hold content at all, and a tag reaches its plan through a marker element and a
  show rule, so there is nothing in the stream for the mechanism to attach to (measured; see
  *Findings*).
  No other channel exists either.
  A `state` cannot vary inside `measure`,
  which is the same finding that made the plan provided rather than published,
  so varying the array per epoch would mean re-evaluating the block that built it.
  That is precisely the threading
  this document rejects elsewhere, `s => ([body], s)`, and it is how `sanor` reaches the
  same case.
  An earlier version handed the body back untouched,
  which made every primitive a silent no-op.
  The symptom then surfaced three tools away from its cause.
  The question of what a tag should do around a *state-changing* command
  (`stroke`, `set-style`) no longer arises, since neither kind of command is reachable.
  What remains for the author is a canvas written as a function of what it draws and tagged as a
  whole, which changes the geometry at the granularity of the canvas,
  and a `content()` element for anything that has to animate.
  A canvas body evaluated per epoch would recover the per-object granularity,
  which is left for a later release.

- **Do implicit regions behave acceptably inside cetz canvases and math?** Yes,
  and better than expected.
  The surrounding layout is not a flow, and that helps rather than hurts.
  Inside math, a tag reserves the width of its widest epoch,
  so the equation has the same width in every epoch and does not shift.
  This was measured on a centred display equation whose tagged term grew from `b` to
  `beta + gamma + delta`, and the `= c` after it did not move by a pixel.
  Inside a cetz canvas, the same reservation keeps the figure rigid,
  since cetz measures the tag's box and that box is the same in every epoch.
  This was measured on a centred canvas whose label grew by a factor of five,
  and the circle and the line stayed put and the canvas kept its extent.
  The cost is the one that the max-footprint rule imposes everywhere,
  which is a gap while a smaller epoch shows.
  Inside a canvas, the remedy is the anchor that decides which way the label grows.
  Nothing here needed a special case, so none was added.
  The manual describes both cases,
  together with the region around the canvas as the way to let a figure change size.

- **Is `sub` the right structure?** Yes. A code block of `sub(...)` calls joins into a
  list of subslides. It already carries `handout:` and took `wait:` and `hold:` in the same way.
  Dropping `c` makes the primitives free functions returning plain data, which is easier to
  inspect, test and extend than methods on a context object.

- **What does a realistic deck cost to compile?** About twice a plain typst deck, and the
  live preview loop costs a tenth of a cold compile, so Animo is not slow.
  Measured on `examples/tour.typ`, 16 slides with 48 states and 20 epoch frames,
  on an i7-1260P with typst 0.15.0 linked against musl: 0.47 s for the HTML presentation,
  1.09 s for the static presentation, 0.60 s for the handout, and **51 ms** to
  recompile after an edit to one slide under `typst watch`, which memoises across recompiles.

  The overhead over the same content laid out as plain typst pages is **2.0** for a deck with
  no structural subslides, **2.5 to 3.0** for two to eight epochs a slide, and **6.6** for a deck
  with regions, epochs and continuous subslides throughout.
  Each term behind the overhead was measured as the difference between two decks
  that differ in one setting.
  One more epoch on one slide costs 6 ms in HTML,
  and one region measuring one epoch of prose costs 2.1 ms.

  The one expensive construct is a **cetz canvas inside a region**,
  measured at 14.9 ms per epoch, which is seven times the figure for prose.
  A twelve-slide deck with four epochs per slide took 5.2 s,
  against 0.13 s for the same drawings as plain typst.
  That is the cost of letting a figure change size, as the region design predicts.
  Both remedies are up to the author.
  The canvas can stay outside a region to keep it rigid,
  or the region can be given a `height`,
  which skips the measuring and brought the same deck down to 1.4 s.
  Nothing here asks for a change to the design,
  and `docs/performance.md` explains the cost to authors instead.

- **Is gzip enough for the page weight, or is the shared-defs hoisting needed?** Gzip is enough,
  and the hoisting that was to follow it turned out to be two separate things.
  Hoisting the shared definitions into a document-level `<svg>` is sound in the browser
  and **unreachable from inside typst 0.15.0**,
  because a package never holds the markup that a frame became.
  What is reachable is one frame per slide that holds every rendering of the slide,
  which makes the deduplicator of typst share the definitions of a slide's epochs.
  *Findings* has measurements of both.
  The reachable half is specified under *Architecture*,
  since it changes what an epoch frame is rather than only how many bytes one weighs.
  The tour is 1.08 MB, which gzip compresses to **222 KiB**, a factor of five.
  Every extra epoch on a slide adds 73 KiB raw or 14 KiB compressed.
  A deck that transfers 222 KiB is a small web page, so nothing here is urgent.

  Gzip does **not** recover the duplication, which the question as posed left open.
  Definitions make up 59% of the tour's page,
  and 37% of the page is definitions that already appeared in an earlier frame.
  Dropping those repeats saves **44% of the gzipped page**.
  The reason is that deflate's window is 32 KiB while an epoch frame
  carrying a heading and one sentence is already 45 KiB, so a definition repeated in the next
  frame is out of reach whatever sits between (measured; see *Findings*).
  Compression and hoisting are therefore independent.
  Compression is worth a factor of five on a deck,
  and hoisting would be worth a further factor of two on top of it.

- **Can `hide` and `remove` be one primitive, with the reflow inferred?** No, and the obstacle
  is the order in which a slide is built rather than a judgement about the API. The two differ
  only inside an explicit region, so the inference would have to read whether the tag
  sits in one.
  Where a tag sits is a *layout-time* fact,
  while the plan is resolved *before* the body is laid out,
  because the body's layout depends on its epochs.
  Nothing in the timeline can stand in for that fact, because the resolver never sees the body.
  Both ways around this cost more than the problem.
  Making the merged primitive always structural puts a fresh epoch behind the most common
  animation in a deck, which roughly doubles the frames and the page weight of an ordinary slide.
  Making it always continuous drops `remove`, which is the primitive that regions made
  meaningful.

  There is a second reason, independent of the first, and it holds even if the ordering ever
  changes.
  The two write to **different slots**.
  `hide` sets display state and `remove` sets content state,
  and the two compose independently by design (see *Animation primitives*),
  so a tag may be hidden and removed at once, and `reveal` and `reset` undo different things.
  One name covering both would make `hide(reflow: true)` followed by `reveal()` a near-no-op
  that reads like an undo.
  `hide`/`reveal` and `remove`/`reset` therefore stay four names.
  The guidance under *Animation primitives* still holds:
  outside an explicit region, `hide` is the right primitive,
  because `remove` there costs an epoch without any benefit.

- **Where does a tag's initial state live: the body or the timeline?** The timeline, inferred
  from the first operation that addresses each of the two slots. A name whose first display
  operation is `reveal` starts hidden, and one whose first content operation is `reset` starts
  removed. An earlier draft declared both at the tag site, as `hidden:` and `removed:` arguments
  of `tag`, and those arguments are gone.

  The deciding argument is that the site arguments made an author keep two places in sync for
  one fact. Nothing can usefully start hidden without a `reveal` somewhere, and nothing can usefully
  start removed without a `reset`, so the timeline already carried the information and the
  argument repeated it, once per site of the name. The repetition was the common case rather
  than an edge one: of the 55 `tag` calls in `examples/`, 37 carried `hidden: true` and 5
  carried `removed: true`. The inference was checked against every tag site in `examples/`,
  `docs/`, `tests/documents/` and `probes/documents/`, and it reproduces the state each argument
  declared, with no site needing an escape hatch. A `reset` that undoes an `apply` or a
  `replace` rather than a `remove` is unaffected, because the first content operation on such a
  name is the `apply` or the `replace`.

  Removing the arguments had four further effects. The agreement check between the sites of one name
  disappears, because sites cannot disagree about something no site states. The refusal of
  `hidden: true` on a `wrap: none` site disappears, because a `reveal` on a name that became no
  group is refused already. The `hidden:` field on the site reports and the anchor markers
  disappears. And the resolver resolves state 0 like every other state, so the tri-state that
  meant "no `reveal` and no `hide` has happened yet" becomes a plain boolean, and no display
  state is read at a tag site at all.

  The cost is accepted rather than mitigated.
  `reveal` and `reset` are no longer pure undos,
  so a `reveal` on a name that nothing hid now changes the first subslide.
  Animo cannot diagnose this mistake, because every timeline yields a valid answer. Such a mistake
  surfaces as an element missing from the first subslide rather than as a refusal. This is the
  one place where Animo guesses instead of refusing, and it is accepted because the refusals
  elsewhere are about what an author cannot have meant, while here every reading is meant by
  somebody.

  The alternative considered was keeping the arguments and shortening them with exported `htag`
  and `rtag` partials.
  It was rejected for two reasons.
  It leaves the two places to keep in sync,
  and `tag.with(hidden: true)` gives an author the same shorthand in one line,
  the way `box.with(..)` and `text.with(..)` already serve `wrap` and `apply`.

- **Should there be a `once` primitive?** No, and it is dropped rather than deferred.
  The idea came from `sanor`, and was to make something true for exactly one subslide,
  by revealing and hiding it again, or by applying a wrapper and dropping it.
  It is not hard to resolve, because the resolver is a forward pass
  and could write the undo into the next state.
  It is ruled out because there is no single thing it could mean.
  Reveal-then-hide and reset-then-remove are both "once",
  and by the entry above nothing can choose between them without an argument.
  An `apply`-then-drop form is a third meaning.
  It needs identity in the wrapper list so that only the wrapper it added is dropped,
  and it costs two epochs where the display form costs none.
  Each of these forms also needs a rule for a `once` in the last `sub`,
  which has no next state to undo it in.
  All this would take a cluster of optional arguments,
  standing in for two lines that an author can already write,
  `sub(reveal("x"))` and `sub(hide("x"))`, which say exactly which meaning was wanted.

- **How does `move` say where something goes?** The same two ways `pan` does, and for the same
  reason: `x`/`y` place, `dx`/`dy` shift, `relto` names another tag to place against. The earlier
  `move(tag, x:, y:)` was a shift only, so "put this label where that node is" had to be computed
  by hand from a layout the author cannot see, and it stopped being right the moment the slide was
  edited.
  Sharing the vocabulary with `pan` costs nothing,
  because the resolver already keeps a pan as an anchor and a per-axis offset,
  and the runtime already measures a tag's anchor for `relto`.
  `move` differs in only one term, which subtracts the anchor of the moved tag.
  The price is stated in *Animation primitives*.
  A name with several sites lands its first site on the target,
  and an element that is also scaled lands its unscaled corner, because a scale is about a
  centre.

- **Does a scale factor multiply into what is there, or set it?** It sets it.
  Multiplying was the earlier answer, and it makes a factor unreadable in isolation.
  `scale("a", 2)` at subslide 7 means nothing until every earlier `scale` on `a` has been found
  and multiplied, and returning an element to its unscaled size means writing a reciprocal
  that changes whenever an earlier subslide does.
  Setting makes `scale("a", f: 1)` restore the element whatever came before,
  and makes the primitive agree with `move`, whose absolute form is likewise idempotent.
  Multiplication served successive growth, which is a product an author can write once.
  `f` is the isotropic factor and `fx`/`fy` are the per-axis ones.
  Combining `f` with either is refused rather than resolved by precedence,
  since a call that gives both says two different things,
  while an axis the call omits keeps whatever factor it had.

- **What may a background hold, and where does an overlay go?** Either may be a colour or
  arbitrary content, and both belong to the **viewport**. Extending `background` from a colour or
  an image to content costs nothing,
  because *Architecture* rule 5 already had a content background as a
  separate frame beside the canvas, and `overlay` is that same construct one layer up. Making
  them viewport-bound rather than canvas-bound keeps a logo in the same place on screen instead
  of letting it travel with the canvas, keeps a full-bleed image from silently enlarging the
  automatic canvas, and keeps
  a colour and a content background behaving identically under a `pan`.
  The layers are also rendered **once per slide** rather than per epoch.
  Neither may hold a tag or a region, so neither can depend on an epoch,
  and drawing them once keeps their cost from growing with the epochs.
  Rendering a layer once does not limit it to one value per slide,
  although an earlier draft of this document concluded so.
  The numbering entry below makes a layer the cheapest place for a subslide number.
  Tags and regions are refused in a layer rather than ignored,
  for the reason *Tags* gives for raw cetz draw commands,
  which is that a silent no-op hides the cause of a mistake.

- **What happens between two slides?** A transition, which may take no time.
  A slide that states no transition takes the deck's transition,
  which is the crossfade unless the show rule's `transition:` names another,
  and `init(duration: 0)` cuts.
  In both directions, the boundary takes the `init` of the slide with the higher number,
  which is the slide a forward step **enters**.
  Stepping back over a boundary therefore undoes exactly what stepping forward over it did,
  and the setting is written on the slide it is about,
  rather than on the slide that happens to precede it in the file.
  The crossfade uses the mechanism that the epoch crossfade already proved,
  which is `plus-lighter` on the two containers inside an isolated stacking context.
  That keeps two opaque backgrounds from dipping halfway through.
  A push, a cover and a wipe move or clip the containers instead,
  and blend them normally while they overlap.
  Two slides are laid out only while they cross,
  because laying out every slide of a long deck for the whole session costs seconds of first
  paint (see *Findings*).
  The length is the deck's `transition-duration:`, which is 0.4 seconds by default
  and sits beside `primitive-duration:` and `easing:`, unless the slide's `init` states one.
  A transition is a function of the `anim` module, as in `push(direction: ttb)`, rather than a
  name per variant or a dictionary. A parameter is then a named argument, so a misspelt one is
  refused by typst at the call that wrote it, a misspelt transition is an unknown variable, and
  an editor shows each transition's parameters and their defaults. The functions live in the
  `anim` module, where new transitions add no names to the namespace of the slide body.
  A direction is a typst direction, `ltr`, `rtl`, `ttb` or `btt`,
  which is the value the pdfpc helpers of other typst presentation packages take for a slide
  transition, and it is the direction of travel on a forward step.
  The values of the parameters are checked in typst rather than only in the runtime, because a
  mistake has to be refused at compile time: a value the runtime did not recognise would be a
  slide that quietly took a default.

- **Where is the transition of an epoch boundary named?** On the structural operation, as
  `transition:`, beside its `delay:` and `duration:`. What crosses a boundary is a region, and
  two regions of one boundary can want two transitions, such as a morph for an equation whose
  terms move and a crossfade for the caption replaced beside it. An argument of `sub` would make
  that cost two subslides. A region already takes its timing from its operations, and its
  transition follows the same rule and the same refusal.
  The argument takes the same transition functions as a slide, because one concept has one
  spelling, and refuses the ones a region cannot take.

- **What does a morph match?** A morph matches four kinds of pair inside the pair of region
  groups the boundary carries, in this order of precedence,
  and an element inside a matched pair is not matched again.

  1. A **tag match** pairs two labelled groups of one name by their index among the groups
     of that name in the region, in document order, and translates the outer slots.
     A tag the boundary itself changes is not matched as a whole, because its content differs
     between the renderings, and the content it holds is matched instead.
     The same holds for a tag or a `per-subslide` rendering that holds a tag the boundary
     changes, whose content differs for the same reason.
     Without this rule, a tag around an equation whose numerator is a separate tag would be
     carried as one block, and none of the terms or the fraction bar inside it would move.
     Without that exception, `replace("eq", transition: morph())` on a tag inside an explicit
     region would move the old equation as one block onto the new one and match none of its
     terms. Unequal multiplicity leaves the extra groups unmatched.

  1. An **ink match** pairs the glyphs, shapes and images of the unclaimed content by a longest
     common subsequence of one key per element, taken in document order, so that a box beside
     a word keeps its place among the letters and neither is diffed apart from the other.
     The key is what the element draws, without its place and without its colour.

     - A glyph is a `<use>`, and its key is the `href`. Typst names a glyph by a hash of its
       outline at its size, and the fill is an attribute of the `<use>` and not part of the
       hash, so equal names mean equal shapes whatever their colour (see *Findings*).
       A glyph that changes size or weight gets another name and is not matched, which is
       right for a morph that does not scale.
       Spaces are not elements of typst's output, so a word is carried as its letters.
     - A shape is a `<path>`, and its key is the `d` with the stroke width, cap, join, miter
       limit and dash. Typst starts the `d` of every shape at the origin of the shape and puts
       its place in a transform, so two copies of one shape at two places have one `d`
       (see *Findings*). The stroke width is in the key because a route does not scale a
       stroke, and so is the `fill-rule`, because two copies under two rules cover two areas.
     - An image is an `<image>`, and its key is the `href`, which holds the image's data,
       with the `width` and the `height`.

     The colours stay out of every key, `fill` and `stroke` alike, and so does a gradient.
     Two copies whose colours differ sum to the interpolation of the two colours under the
     crossfade's `plus-lighter`, for a stroke and an image as for a glyph, and a gradient moves
     with the shape that uses it (see *Findings*).
     Each distinct key is numbered before the diff, so the diff compares numbers rather than
     the long strings of a path's `d` or an image's data.

  1. A **resize** pairs two paths that the ink match left over, whose geometry differs and
     whose structure is the same, and animates the `d` and the stroke width of both from the
     outgoing geometry to the incoming one beside the translation of the route.
     The structure is the sequence of command letters of the `d`, the count of its numbers,
     the stroke attributes other than the width, the clips above the path and the labels of
     the groups between the path and its region.
     Chromium and firefox interpolate `d` number by number between two paths of the same
     commands and flip from one to the other halfway otherwise (see *Findings*),
     so the structure is what the engine needs, and no path is rewritten.
     For the rounded rectangles typst writes, every control point is linear in the width, the
     height and the radius, so the corners keep their shape and their radius goes over to the
     incoming one with the size.

     A resize pairs only paths within one **hunk**,
     which is the content that the ink match leaves over between two consecutive ink matches,
     or before the first or after the last.
     Within a hunk, the paths are paired by a second longest common subsequence over the
     structure.
     The bar of a fraction whose numerator grows is paired with the wider bar, because it
     sits between the numerator and the denominator in both renderings, while a box removed
     before a word and another added after it are not.
     Pairing any two paths of one structure in the region in document order would be simpler
     to compute, and would turn a box that disappears into an unrelated one that appears
     elsewhere. Pairing only inside a tag would be the most explicit, and would make the
     author tag every fraction bar of an equation.
     The labels in the structure are how an author steers the pairing:
     a tag around one of two shapes keeps them apart, and a tag the boundary changes around
     each holds them in one hunk.
     A resize needs the two user spaces to differ by a translation only, which holds for
     everything typst lays out unless a `scale` or a `rotate` sits above one path and not
     above the other.
     A pair whose user spaces differ by more than a translation is crossfaded.

     A resize is a refinement that an engine without the CSS `d` property skips:
     webkit 26.5 does not animate it, so the runtime tests `CSS.supports` once and webkit
     crossfades the shapes the other engines resize, while every other match moves.
     Paths whose structures differ, such as a rectangle against one with rounded corners,
     against a circle, or a rounded rectangle against one whose straight sides typst leaves
     out because they have no length, are left to the shape morph.

  1. A **shape morph** pairs two paths of any structure that the resize left over, when a tag
     the boundary changes holds exactly one of them in each rendering, and animates `d` and
     the stroke width as a resize does.
     A path belongs to the nearest tag above it, which is the tag around the region when the
     region is a tag's implicit one, and two tags inside a region are paired by name and
     index as in a tag match. The two paths need the same clips and user spaces that differ
     by a translation only, as for a resize.
     A tag that holds one shape before and one after is a clear statement that the one
     becomes the other, and no other clue pairs two shapes of different structures.
     Guessing from the structure or the place would turn a box that disappears into a circle
     that appears beside it. An argument of `morph()` that turns shape morphs on or names the
     tags they apply to was the alternative, and it would state a second time what the tag
     says already. The tag takes precedence over the hunks of the resize, so a box that a
     changed tag moves from before its words to after them morphs on the way.
     A tag that holds two leftover shapes on either side crossfades them.

     The engine interpolates only between paths of the same commands, so both paths are
     rewritten into one structure first, which manim calls aligning points.
     Every segment becomes an absolute cubic Bézier. The subpaths are paired by length, and
     a subpath without a partner is paired with a point at its place in the other path's box,
     so a hole grows out of nothing or closes. An open subpath against a closed one is closed
     the way its fill closes it, by a line when the path has a fill and by running back
     along itself when it has none, which strokes the same apart from its two ends.
     Two closed subpaths are made to run the same way round, as given by the sign of their
     area, because otherwise the shape turns inside out on the way.
     The second subpath then starts where the squared distance its points travel is least,
     which keeps a square from twisting on its way into a circle.
     Last, both subpaths are cut at the vertices of both, at the fraction of the length where
     each vertex lies, so every piece lies within one segment of each side.
     A square's sides are then cut at their middles against a circle,
     and a sharp corner against a rounded one becomes two short pieces that bend into the
     arc. The alignment reads no DOM and is linear in the number of segments apart from a
     search over the starting point.

     The fill rule of each path stays as it is, so a shape under the even-odd rule against
     one under the non-zero rule shows both rules crossfaded while the outline moves, and a
     filled shape against a stroked one crossfades the fill against the stroke.
     Webkit crossfades shape morphs as it crossfades resizes.

  A tag is how an author makes content move as one, and a paragraph that reflows is carried by
  its glyphs and shapes without any tag.
  A shape that changes size, such as the bar of a fraction whose numerator grows, has another
  `d` and is no ink match, and the resize carries it when its structure stays.
  A letter is a `<use>` of an outline in the definitions and not a path, so a shape morph does
  not turn a letter into another letter. Glyph outlines have many subpaths, and the
  `TransformMatchingTex` of manim fades the letters it cannot match rather than morphing them.
  An author who wants a letter to change its outline draws it as a shape, with typst's
  `curve` or with cetz.
  Elements of one key are paired in document order, which for a plot is the order it draws its
  marks in. When one point is added at the start of the data, every mark therefore moves to
  the place of the next point, and the routes cross the plot although a pairing exists in which
  no mark moves. That limitation is accepted. A pairing that minimises the total distance is the
  assignment problem, which the Hungarian method solves in time cubic in the number of marks.
  Finding near partners more cheaply gives up the linear cost of the match and brings edge
  cases too, in which the pairing a mark gets is harder to predict than its place in
  the order the plot draws.
  The subsequence is found with a diff of the Myers kind, whose cost grows with the number
  of elements times the number of differences, and a region whose ink differs in more than a
  fixed number of places matches none of it and crossfades it, because a crossfade is always
  correct. The bound is 400 differences, which the diff of two lists of 3000 glyphs takes about
  10 ms to reach in chromium 151 and firefox 153, measured with `benchmarks/morph.py`.

  **A match has the same clips above it in both regions.**
  A CSS `translate` carries the clip of the element it moves, but not the clip of an ancestor,
  which stays where the ancestor is laid out (see *Findings*).
  A copy that travels under a clip at another place than its partner's is cut off at an edge
  its partner does not have, and the two no longer sum to one opaque element.
  The clips between an element and its region group, each named by its `clip-path` and
  placed by its matrix on the screen, are therefore part of the key of an ink match,
  and a tag match needs them equal as well.
  The content of a clipped box that moves is therefore crossfaded,
  and a tag around the box carries the box and its content as one.
  The clip path's id is a hash of its path, so equal names mean equal clips.

  A morph interrupted by the next boundary continues from what the page shows:
  an outgoing element is measured where it is displayed and an incoming one where it is laid
  out, which is its displayed place less the running morph translations on it and above it.
  A path that a resize is still changing starts its next route from the `d` and the stroke
  width it shows, which `getComputedStyle` returns while the animation runs.
  A morph translation that the next step leaves behind in a region that step carries again
  runs on to its end on the new boundary's clock, and every other one snaps to rest, as the
  crossfade of a region the step does not carry does. The `d` and the stroke width of a
  resize do the same as the translation of their path.

- **Where do the title and the language of the HTML page come from?** From `set document(..)`
  and `set text(lang: ..)`, as for any typst document, so nothing is stated twice. Typst writes
  neither into a head that a package builds, so the deck's show rule reads them in a context and
  writes the `<title>`, the `lang` and the `<meta>` elements typst would write (see *Findings*).

- **Where does the timing of an automatic step go, and can one operation start late?** On either
  side of the gap it times, and yes. The three knobs are `wait:`, `hold:` and `delay:`, and
  *Timing* states them.
  `wait:` names the gap before the subslide it is written on and `hold:` the gap after it,
  and both apply to `sub` and to `init`.
  A slide's initial state is timed by `init(wait: ..)` and `init(hold: ..)`,
  because it has no `sub`.

  The first draft had only `wait:`.
  It defined the gap as the delay before a subslide,
  on the grounds that a "hold this state for *n* seconds" keyword would need two names
  to cover a slide's first and last states,
  and it recorded as a real cost that the other form survives editing better.
  Using the package reopened the question, and two of the three grounds did not survive.
  The two-keyword claim is wrong: `init(hold: ..)` times state 0, every later
  state is a `sub` that carries its `hold:`, and the last state of a slide with no `sub` at all *is*
  state 0, so one keyword covers it either way. And the coverage `wait:` alone was
  supposed to buy is not there: `init(wait: ..)` on the first slide of a deck does nothing,
  because a gap is read when its state is entered from a predecessor and state 0 of slide 1 has
  none. What is left is that the two forms are natural for different sentences and fail in
  opposite directions when a timeline is edited, which is why both are implemented.

  **One gap takes one number**, and a gap that both of its neighbours time is refused rather than
  summed. *Timing* states why, and the part that belongs here is the order of the two decisions:
  a refusal can be widened into a sum in a later version without breaking a deck, where a sum
  cannot be narrowed into a refusal without breaking several. Nothing about the runtime changes
  with the second keyword, which is what made this cheap: the plan carries both numbers per state
  and the runtime reads whichever of the two was written.

  **A backward step turns the clock around**, which using the package also showed to be needed.
  A deck that played itself forward over a run of gaps has to come back over the same run,
  and the state a backward step lands on arms the gap that the step just came over.
  The clock therefore
  steps the deck whichever way it is travelling, and the travel ends where the presenter would
  have had to press a key. The first state of a deck is the one place the clock is stopped
  instead, because nothing earlier is there to travel to.
  A forward step and `Space` both restart that clock.
  A pending timer is cleared by any manual step, so autoplay never races the presenter, and the
  pause never enters the fragment: it is the one piece of runtime state the URL does not carry.

  `delay:` is a separate name because it times an operation rather than a subslide.
  It becomes the delay of the Web Animations API effect, so the subslide keeps its one clock.
  On a structural operation, it holds back the crossfade of the region it changes,
  which is why two operations changing one region at one boundary may not disagree about it.

  **A backward step mirrors that schedule rather than replaying it**,
  which is the third thing that using the package showed.
  The first rule replayed the schedule,
  on the reading that an operation which arrived late should leave late.
  Presenting a slide of three lines staggered by `delay:` showed the problem.
  The line that arrived first left first, so the build came apart in the order it was built up,
  and the composition passed through pictures that the forward step never showed.
  Mirroring each operation about the length of its step makes the two directions one motion
  seen from two ends.
  It costs the plan one number per timed step,
  because the browser cannot compute the length of a step from the operations it receives,
  since an operation that states no timing carries none.
  *Timing* states the rule, and *Architecture* says what travels in the plan.
  All these timing values are plain numbers of seconds,
  since typst has no time literal and `2s` does not parse.

- **Does an operation get a separate duration, and in what unit?** Yes, `duration:`, beside
  `delay:` on every primitive, defaulting to `auto`, and in seconds like everything else an
  author writes.
  It was planned as `time:`, and was added once `delay:` had built the plumbing,
  because the plan carries per-operation timing to the browser either way,
  and the Web Animations API takes a duration exactly where it takes a delay.
  The name is `duration:` rather than `time:` because it sits beside `delay:`, where `time:`
  reads as a moment rather than as a length, and because it is the quantity
  `--animo-primitive-duration` already names.
  Three decisions made with it are the reason this is an entry rather than a line.
  **The unit is seconds**, not a multiple of `--animo-primitive-duration`,
  so that two numbers on one call mean the same thing by the same number.
  The multiple was the tempting form,
  because it would make the next point arithmetic instead of a rule.
  **Reduced motion still takes precedence.**
  When the reader asks for reduced motion, the runtime drops every explicit duration
  (see *Timing*), because a media query cannot reach a number written in a typst source,
  and a reader who asked for no motion should not have to ask a second time.
  **The default is `auto` rather than a number**,
  so that "unset" and "as long as the `primitive-duration:` of the deck" stay distinguishable.
  A deck-wide restyle needs that distinction to reach the operations that stated no duration
  and to leave the others alone.

- **How is a slide numbered, and can a subslide be?** Both, with `slide-number()`,
  `slide-count()` and `per-subslide(f)`, and the subslide half works by rendering every value
  rather than by substituting one.
  *Slides* describes the functions, and this entry explains why they have that shape.

  An earlier draft identified the obstacle correctly, but not the way around it.
  An HTML frame covers a whole
  run of subslides, so a number chosen when the frame is rendered is one number for all of them,
  and rendering one frame per subslide would destroy the cost model. The earlier draft's three
  ways out were to ship neither name, to ship the slide number alone, or to find a form in which
  the number is "a runtime value the browser substitutes rather than rendered ink".
  Substituting a value is the part of that third option that does not work.
  Typst emits glyphs as `<use>` references into per-frame `<defs>`,
  so a runtime that wrote a number would be rewriting glyph references by their hashed
  identifiers, which is the markup the shared-`<defs>` hoisting rewrites.

  What works needs no new mechanism. Typst renders **every** value and the browser chooses which
  one is shown, which is exactly what `reveal` and `hide` already do.
  A number is therefore a stack of renderings, each with a label,
  and the runtime shows the rendering that belongs to the current position,
  while a page of a paged output lays out the rendering of the state it shows.
  The three output types then agree by construction rather than by arrangement, and nothing
  about a number travels in the plan.

  **An overlay is the cheapest place for a number.** A layer is one rendering
  per slide where a region is one per epoch, so a stack costs once in a layer and once per epoch
  in a region. Measured on the controlled deck at its realistic point, a slide number and a
  subslide number in an overlay cost 3% of the raw page, 4% of the compressed page and 5% of the
  compile time, with the plan attributes byte-identical. The same stack built by hand out of
  tags and `reveal`/`hide`, which an author could already write, doubled both the plan and the
  compile time.
  That measurement decided for a reserved label over a generic display state.

  **Why a callback rather than a `subslidenum()`.**
  The machinery is the same either way, and only the callback makes a progress indicator
  possible.
  In HTML there is no integer at layout time to compute a bar's width from,
  only a rendering per state. One name in the
  manual therefore covers a number, a "3 of 6", a row of dots and a bar. It also puts the
  deck-wide pair, `step` and `steps`, where a bar spanning the talk can reach them.

  **Numbering epochs instead was rejected.**
  Numbering epochs would cost nothing, because a frame knows its epoch,
  but it would not serve the purpose of a number.
  An epoch number does not advance on a continuous subslide,
  so it is constant on the ordinary slide that only reveals things.
  It makes `hide` versus `remove` visible to the audience,
  which is the objection that keeps epochs out of the handout under
  *Does the handout show intermediate content?*.
  It would also stand beside the `slide.state` of the fragment as a second numbering system.
  Nothing named `epoch` is in the public API.

  The purpose of a number decides the trade-offs above.
  A number is there so that someone in the audience can ask about a particular moment of a talk,
  and so that the speaker can find that moment again.
  An exactly correct subslide number is a means to that and not the end.
  An exact number turned out to be affordable, so an approximate one was no longer needed.

- **Testing strategy.** The tests are split into three tiers under one runner,
  with the weight on the cheapest:

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

  - every label *outside* a region is laid out once, and every rendering of a region's stack
    starts at the same corner, read with `getScreenCTM` and with `getBBox` rather than with
    `getBoundingClientRect`, which the engines disagree about on a group (see *Findings*).
    A rendering's box is not one of these: a group's box is its ink, and the ink inside a
    region is exactly what an epoch changes, so what a region promises is its corner;
  - the rendering is pixel-identical outside the region between epochs, and stays so
    mid-crossfade, with every raster of the mid-crossfade comparison taken while the step is
    in flight (see *Findings*).

  Both are comparisons *within* one page load, so they need no stored reference images and are
  unaffected by glyph rasterisation changes. Stored image snapshots are brittle across typst
  versions and stay the exception. The runner, the tools and the reference-image policy are
  settled in [docs/testing.md](../docs/testing.md).
  `tytanic` is the ecosystem convention for testing typst packages,
  and was rejected only because it cannot see the HTML target at all.

## Open Questions

These questions were open while the design took shape.
The entries marked *Settled* have since been answered and keep their reasoning here,
and the others are still undecided.

- **How exact is the automatic canvas?** Settled: the approximation stays, and its error is
  documented in both directions rather than reduced. The `show place:` rule fires for *every*
  placement, including one nested inside a `box` or a grid cell, where `dx`/`dy` resolve
  against that container rather than against the canvas, and the rule cannot tell the two
  apart (measured; see *Findings*).
  The alternative was to count only the placements that Animo can attribute to the slide body,
  but no mechanism supports that.
  `layout(size => ..)` inside the rule reports the container exactly,
  but breaks the paragraph that the placement sits in.
  A nesting depth kept in a state reads zero for a placement inside another placement,
  which is how real decks are written,
  and would read every placement inside a tag as nested, since a tag site is a box
  (measured; see *Findings*).
  The error of the approximation is documented instead.
  A nested offset is counted short by wherever its container sits,
  a nested alignment is counted *long* from the body box,
  and a ratio-sized body contributes nothing at all.
  The last of these errors also occurs at the top level.
  An explicit `canvas: (width: .., height: ..)` is the escape hatch for all
  three.

- **Does autoplay want a pause key?** Settled: yes, on `Space`, and the pause does not survive a
  reload.
  A gap advances on a timer,
  and a manual step clears the pending timer and re-arms from the state it lands on.
  That is enough for a presenter who wants to run ahead,
  but not for one who wants to stop and take a question.
  It is also not enough for the reader that the pause is really for,
  who watches a deck that plays itself and wants to stop it the way they stop a video.
  `Space` toggles the clock while a timer is pending or the deck is already stopped,
  and steps forward otherwise,
  so the forward key that every presentation remote sends is unchanged on a deck without timed
  gaps.
  Resuming continues what is left of the wait.
  The two alternatives were rejected because of what each would cost.
  Leaving the pause out serves the presenter and not the reader.
  Putting the pause in the fragment would make the fragment something other than a position,
  and a shared link could then say that a deck is stopped.
  The pause therefore stays the one piece of runtime state that the URL does not carry,
  and the runtime publishes it as `data-animo-paused` on the root element for whatever wants to show
  it. *Timing* states the rule.

  After the package was used, a second way into the same stop was added:
  **a backward step stopped the clock**,
  because arming the gap it had just come over would carry the deck forward again,
  and that gap can be zero.
  A gap of zero then needed a second answer beside the stop.
  With only the stop, each backward step over a join left the presenter resting on a state
  that the audience had only ever seen in passing, one press per join.
  **A backward step therefore walks back to the nearest earlier state the deck would rest at**,
  as *Timing* states.

  Presenting a deck with a short gap across a slide boundary reopened the stop. The walk crosses a
  gap of zero and nothing else, so a gap of a third of a second left the presenter one press back
  on a state the audience had seen for a third of a second, and a second press was needed to reach
  the state they had left.
  A minimum gap below which the walk would also cross was rejected when the stop was written,
  and is still rejected.
  Such a floor is a magic number.
  Zero is what an author types to say that a state is not a stop,
  while a tiny number says the opposite just as deliberately.
  What replaced the stop needs no number.
  **The clock steps the deck whichever way it is travelling**,
  so a run of automatic gaps is crossed back the way it was crossed forward and the travel ends
  where the presenter would have had to press a key. The cost is that a deck which times every gap
  travels back to its first state. That is accepted, because such a deck plays itself forward to
  its last state as readily, and `Space` stops it either way.
  The stop remains for the one case that the travel cannot handle,
  which is the first state of a deck.
  The two stops publish the same attribute, and differ only in how they end.
  A forward step resumes the stop at the first state,
  and leaves a stop made with `Space` in place.
  *Timing* states those rules too.

  **The pause stops the motion as well as the clock**,
  which the same use of the package showed to be needed.
  A pause that let the step in flight run on to its end moved the picture after the key was
  pressed, while a reader who presses a pause key wants to keep the picture they are looking at.
  Every animation the key finds in flight is paused where it is and picked up from there, which
  the Web Animations API does on its own, and a step the presenter makes by hand while the deck is
  paused is left alone.

  The walk left one problem, which presenting showed later.
  A backward step over a join that runs out of a slide
  leaves the slide it walks back into at a state before its last state.
  On the way back, that slide now moves into the state it lands on while the boundary crosses it,
  rather than snapping into place under the crossfade.
  Only a backward step does so. *Timing* states
  that rule as well.

- **May an operation's duration run past the subslide it is in?** Settled: it may, and the
  boundary stretches with it.
  For a continuous operation, nothing was in question,
  because an interrupted animation continues from where it is (see *Architecture*),
  as it already does when a gap is shorter than a subslide's motion.
  The structural case was the open one.
  An epoch boundary lasts until the last of its crossfades has finished,
  so a long duration keeps two frames laid out for as long as it runs,
  and two boundaries can be in flight at once.
  The epoch model had never had to represent that situation.
  What decided it is that the situation is reachable without a duration at all.
  A deck that staggers a long `replace` against a fast timeline reaches it,
  and so does a presenter who clicks twice, with numerically the same result (measured).
  Clamping a structural duration to its subslide and refusing one that outlives it were the
  alternatives.
  Both can only be defined against the gap that follows the subslide, and a click has no length,
  so each would remove one way into the situation and leave the situation itself.
  The overlap needed an answer in the runtime instead, which rule 2 of *Architecture* states.
  Every frame other than the one being entered hands its carried regions over on the new
  boundary's clock, so the opacities in the region still add up to one,
  rather than dipping to the fraction that the interrupted crossfade had reached.
  The same answer repairs the dip that a short gap
  already produced.

- Whether a morph should ever scale. It translates only, and a glyph that changes size is not
  matched, so its size change is carried by the crossfade. Scaling would let a heading that
  changes size morph, and non-uniform `scale` distorts glyph strokes, which suggests leaving
  scaling for figures.
  For a shape, the resize answers the question without scaling the stroke.
  The question stays open for glyphs and images, which a resize cannot reach,
  because a glyph of another size is another outline.
  This has to be seen in motion before it is decided.
  The extra nested box under *Findings* is needed either way,
  since the two slots are separated by coordinate space
  and not merely by how many properties each one uses.

- Whether a group of shapes that travel one distance should move as one animation, as the
  glyphs of a run do. A cetz drawing that moves as a whole is better put in a tag, which
  already moves as one. A plot of 1000 marks whose axis range changes, so that each mark has a
  separate route, costs a key press of 93 ms in chromium 151 and 134 ms in firefox 153, and
  chromium then draws a frame every 51 ms, measured with `benchmarks/morph.py`.

## Development Infrastructure

This section is not part of the feature design.
It is recorded here because much of the infrastructure is constrained by the design,
and because two parts of it impose requirements back on the package:
the live preview needs the runtime's state to be addressable in the URL,
and Universe needs the version number to be correct in every example.

Most of the infrastructure now exists in the repository,
and is described where a contributor meets it.
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
`compiler = "0.15.0"`, and the `exclude` list that keeps documentation out of the published
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
knows yet what real use turns up.
A break still has a real cost, because it rewrites decks that already exist.
That cost, and the irreversibility of the submission itself,
are why the last step of the release path stays manual.

### The state the runtime has to expose

`typst watch` serves the HTML and reloads the browser itself (see *Findings*), so Animo ships
nothing for live preview. What it does require is that the runtime keep the current slide and
subslide in `location.hash` and restore from it on load,
which the testing strategy needs anyway for deep links.
This has two consequences:

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
  subtree and not the working tree, so it has to exist as a separate directory.
- `tools/release_notes.py` reads one version's section out of `CHANGELOG.md`, so a GitHub release
  does not restate it.

The benchmarks are a separate script for a reason stated in
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
  (`test/draw.typ` tags a `draw.grid(..)` with `hider: draw.hide`),
  which Animo does not and cannot do.
  The body of a `sanor` slide is a function of `s`, re-evaluated once per subslide,
  so its `tag` applies draw-to-draw wrappers eagerly at call time.
  Animo lays one content value out per epoch and reaches it with a show rule,
  which reaches content and not values.
  The difference in capability follows from that one decision alone.
  `sanor` is PDF-only, which lets it restyle and reflow freely,
  because every step is a fresh page anyway.
  It pays for the separation with
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

None of them uses Animo's per-element `data-typst-label` approach,
which allows one tagging mechanism to serve smooth HTML animation and paged snapshots alike.
The region concept lets the same mechanism also serve content changes,
which per-element animation alone cannot express.

## Related directories

These sibling directories (`..`) bear on this design.

Reference implementations and prior art:

| Directory   | Relevance                                                                              |
| ----------- | -------------------------------------------------------------------------------------- |
| `../sanor`  | tag/`apply` separation, cases, objects, pdfpc notes; PDF-only                          |
| `../slipst` | HTML export, custom runtime, stacked frames with `plus-lighter`, URL-addressable steps |
| `../kino`   | frame-by-frame animation in pure typst with an external python driver                  |

Upstream sources consulted for the findings:

| Directory             | Relevance                                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `../typst`            | typst 0.15.0 checkout; `crates/typst-svg` (label emission, def id hashing) and `crates/typst-library` (`measure`, `html.frame`) |
| `../typst-dev-assets` | assets used by the test suite of typst, handy for rendering tests                                                               |
| `../krilla`           | the PDF writer typst builds on; relevant only if PDF-level features (pdfpc metadata, layers) are ever needed                    |

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
