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
Two companion documents carry material that would otherwise overwhelm this document.

- [findings.md](findings.md), referred to throughout as *Findings*,
  records the verified behaviour of typst 0.15.0 and of the browsers Animo drives
  that this design rests on.
  Every entry there was expensive to establish and is easily lost again,
  and every one is guarded by a probe under `probes/`.
- [docs/architecture.md](../docs/architecture.md) describes how the browser runtime is built:
  its files and where each part of this design lives in them, its controller,
  the events it announces, the input it reads and the attributes it reads and writes on the page.
  This document specifies what the runtime does and why, and that page says where in the code.

Any other reference in italics, *Regions* or *Architecture* for instance,
is a section of this document.

Further development is tracked on GitHub as issues and pull requests,
not as a phase plan kept in this repository.

## Scope

Animo has the following features, each specified in a section below:

- showing, hiding, moving and scaling tagged content (*Animation Primitives*);
- replacing, removing and restyling tagged content,
  with **real reflow** of the surrounding content inside a bounded area (*Regions*);
- a **viewport** onto a **canvas** that may be larger, with `pan` moving the viewport
  over the canvas in the manner of Slipshow (*Canvas and Viewport*);
- a **background** and an **overlay** per slide, each a color or arbitrary content
  (*Background and Overlay*);
- a delay and a duration on every primitive, and gaps that run on a timer
  instead of waiting for the presenter (*Timing*);
- a slide number and a subslide number (*Slides*);
- a **transition** between two slides and between two epochs of a region (*Transitions*);
- handout pages chosen per subslide, defaulting to the final state of each slide
  (*Animation Primitives*);
- three output types from one source file (*Output Mode Selection*):
  - an HTML presentation for presenting in a browser, the only animated one;
  - a static presentation for presenting when a browser is not available at the venue;
  - static handouts for printing and distributing to the audience.

Animo deliberately leaves out the following:

- templating and styling features;
- header and footer machinery, because a recurring element is a `#place`
  in a wrapper around `#slide`;
- HTML and CSS in a deck's source,
  because every setting the runtime reads is an argument of the deck's show rule;
- overflow of content to a next slide,
  because whatever falls outside the viewport is clipped and `pan` brings it into view.

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

## Vocabulary

These are the terms of this document, and each is used for one concept only.
A section that relies on a term uses it without repeating its definition.

### Slides and Their Parts

- **deck**: the document, shaped by the `animo` show rule.
- **slide**: one `#slide` call, which holds a body, a timeline and two layers.
- **body**: the content argument of `slide`, which declares what is on the slide.
- **viewport**: the rectangle the audience sees,
  which is the slide container in the HTML presentation and one page on paper.
- **canvas**: the rectangle the body is laid out on, which is at least as large as the viewport.
- **layer**: the background or the overlay of a slide, which belongs to the viewport.
- **stage**: the element of the HTML presentation that holds the slide containers
  at the deck's aspect ratio.
- **output type**: the HTML presentation, the static presentation or the static handouts.

### Timelines and States

- **timeline**: the `animation` argument of a slide,
  which is an optional `init` call followed by `sub` calls.
- **primitive**: a function of the `anim` module that describes a change,
  such as `reveal` or `replace`.
- **operation**: one call of a primitive inside a `sub` call.
  An operation is a description and performs nothing itself.
- **continuous primitive**: `reveal`, `hide`, `move`, `scale` or `pan`,
  which change only how content that typst laid out is displayed.
- **structural primitive**: `replace`, `remove`, `apply` or `reset`,
  which change what typst lays out.
- **state**: one of the S+1 compositions of a slide whose timeline has S `sub` calls,
  also called a **subslide**.
  State 0 is the **initial state**, which is the body as declared.
- **step**: the move from one state to a neighbouring one,
  which the presenter or the clock makes.
- **gap**: the time between two consecutive states.
  The presenter ends a gap with a key, unless a `wait:` or a `hold:` times it.
- **join**: a gap of zero, which the deck crosses without resting.
- **plan**: the timeline resolved into the display state of every state
  and the content state of every epoch.
  The **resolver** computes the plan before the body is laid out.

### Tag Sites and Their State

- **tag**: content marked with `tag(name, body)`.
  A **tag site**, or **site**, is one place where a tag name occurs,
  and one name may have several sites on a slide.
- **slot**: one of the two nested wrappers that a site emits.
  The outer slot carries the label, and the inner slot carries the display state.
- **display state**: what the continuous primitives have done to a tag,
  which is its visibility, its position and its scale.
- **content state**: what the structural primitives have done to a tag,
  which is what is laid out (the body, a replacement or nothing) and the wrappers around it.
- **anchor**: the top-left corner of a tag's outer slot as the body laid it out.
  *Animation Primitives* states which site provides it.

### Epochs and Regions

- **epoch**: a maximal run of consecutive states that share one content state.
  A cost that is counted per epoch is never counted per state.
- **boundary**: the step between two epochs, an **epoch boundary**,
  or between two slides, a **slide boundary**.
- **region**: an area of a slide that is laid out afresh in every epoch
  inside a footprint that stays fixed.
  An **explicit region** is one the author writes with `region`.
  An **implicit region** is the one that a tag whose content changes forms
  when no explicit region holds it.
- **footprint**: the rectangle a region occupies in every epoch.
- **region key**: what identifies a region within a slide.
  An explicit region is numbered in document order within one rendering of the slide,
  and an implicit region is named after its tag.
- **rendering**: one layout of a body, a region or a `per-subslide` for one epoch or one state.
- **stack**: renderings placed at one point, of which the browser shows one at a time.
  An **epoch stack** holds one rendering of a region per epoch,
  and a **subslide stack** holds one rendering of a `per-subslide` per state.
- **transition**: how a boundary is crossed, such as `crossfade()` or `morph()`.
  A **hard cut** is a crossing that takes no time.
- **match**: a pair of elements that a morph carries from the outgoing to the incoming
  rendering.

### Mechanism

- **view**: the record that a slide hands to every site and region it lays out,
  which says what to lay out and how to display it (see *Scoping*).
  A **stack view** is the smaller record that a `per-subslide` receives.
- **report**: a `metadata` element that a site or a region emits,
  so that the slide can read back after layout what only layout knows.
  A **site report** says that a site exists and which tags enclose it,
  and a **membership report** says which region a site belongs to.

## Specification

### Slides

```typst
slide(body, animation: (), canvas: auto, background: none, overlay: none, numbered: true)
```

The arguments of `slide` say what the slide is.
The `animation` argument says when anything happens to the slide,
including how the slide is entered.

- `animation` is the timeline (see *Animation Primitives*).
  The transition into the slide, the gaps on either side of its initial state and the handout
  flag of that state are arguments of `init`.
- `canvas` is described in *Canvas and Viewport*.
- `background` and `overlay` are described in *Background and Overlay*.
  They are not styles applied to the body.
  They are two more pieces of content at two fixed depths,
  and Animo neither positions nor decorates what goes in them.
- `numbered` decides only whether the slide counter **counts** the slide.
  A title or section slide is typically `numbered: false`.
  Whether and how a number is *shown* is the author's job,
  because Animo has no header or footer machinery.
  The author shows a number with `#place` and a wrapper around `#slide`, or with `overlay`.

Beyond these, `#slide` has no templating or styling parameters by design.

A number that is shown is built from three functions,
and Animo has no other functions for numbering.

```typst
slide-number()               // the slide's number, or `none` on a slide with `numbered: false`
slide-count()                // how many slides of the deck carry a number
per-subslide(f, wrap: auto)  // content laid out once per state, of which one is shown
```

The `slide-number()` and `slide-count()` functions read the slide counter and return integers,
so a deck may compute with them.
Both must be called in a context.
On a slide that the counter passes over, `slide-number()` is `none`
rather than the number of the slide before it,
so one footer can serve a whole deck without a special case for such slides.
Neither number is the position that addresses a slide in the URL,
because that position counts every slide the presenter walks through.

`per-subslide` takes a callback rather than reading a counter.
In the HTML presentation, one rendering of a slide covers a run of states
(see *States and Epochs*),
so a value chosen when that rendering is laid out would be the same for all of those states.
Animo therefore calls the callback **once per state**
and places the results in a subslide stack.
The callback receives the **subslide info**, which is the dictionary
`(number, count, step, steps, handout)`.

- `number` and `count` are the state's number within its slide and how many states that slide
  has.
- `step` and `steps` are the same pair over the whole deck,
  so a progress indicator may span either the slide or the deck.
- `handout` is the state's resolved `handout:` flag,
  so a presentation can mark the states that the handout keeps.

Animo calls the callback for every state in every output type,
including the states that the handout leaves out,
so the subslide info of a state is the same in all three output types.
The `number` and `step` keys count from one, while the URL fragment counts states from zero,
because the fragment is an address and the number is what the audience reads on the slide.
A callback may return `none`, which lays nothing out for that state.
The `wrap:` argument takes `auto`, `box` or `block`,
and chooses between a hugging and a filling container exactly as the `wrap` of a tag does.
A rendering that states a ratio needs `block`,
because only a filling container has a width that the ratio can refer to.

The footprint of the stack fits its largest rendering.
A paged output lays out only the rendering of the state on the page,
and the browser shows the rendering that belongs to the current state.
All three output types therefore agree,
and a handout page carries the number of the state it keeps rather than the number of the page.

### Canvas and Viewport

A slide has two rectangles, and `pan` is defined by the difference between them.

- The **viewport** is what the audience sees,
  which is the slide container in the HTML presentation and one page in the paged outputs.
  Its size is the slide size of the deck.
- The **canvas** is what the body is laid out on.
  It is at least as large as the viewport and may be larger.
  Content that falls outside the viewport is clipped, not carried over to a next slide,
  and a `pan` brings the rest of the canvas into view.
- The canvas origin is the body's origin.
  The viewport starts at `(0pt, 0pt)` in state 0,
  so a slide with no `pan` is indistinguishable from one with no canvas at all.
- `canvas: (width: .., height: ..)` states the canvas size explicitly,
  which is also the remedy when the automatic size is wrong.

The body is laid out in a **body box**, which is as wide as the inner area of the viewport.
The body box is as tall as that inner area,
unless the flow of the body is taller, in which case it is as tall as the flow.
The body box has to grow, because a fixed-height container stacks the block-level content
that does not fit at its bottom edge rather than letting it flow past (see *Findings*).
In a fixed-height box, a derivation that runs off the viewport would therefore arrive
as a pile of overlapping blocks instead of as the content a `pan` is meant to reach.
A `#place` in the body resolves its alignment and its ratios against the body box,
so `place(bottom + right)` is the bottom right of the viewport on an ordinary slide
and the bottom right of the flow on a slide whose flow runs off the viewport.
A placement never changes the body box, because a placement contributes nothing to the flow.

`canvas: auto`, the default, sizes the canvas in one of two ways.

- **A slide whose timeline pans** gets the union of the body box
  and the extent of each `#place`d element, offset by the deck's margin
  and enlarged to at least the viewport.
  A slide that places nothing outside the viewport therefore has a canvas equal to the viewport.
- **A slide that never pans** gets the body box, offset by the deck's margin
  and enlarged to at least the viewport.
  `pan` is the only reader of the canvas, and the viewport clips in every output type,
  so such a slide is drawn the same whatever canvas it gets.
  Animo skips the union there, because the union costs a `context`, a `measure`
  and a queried element for every `#place` in the body.

The union cannot come from typst's own `auto` sizing,
because `#place` is out of flow and contributes nothing to it (see *Findings*).
It also cannot come from position introspection, which does not work in the HTML target.
Animo records the placements with a `show place:` rule over the body instead.
The rule fires for every placement and exposes `dx`, `dy`, `alignment` and a measurable `body`,
so the union is computed from content alone and comes out the same in every output type.
The canvas depends on the layout it sizes, which typst resolves by iterating,
and the iteration converges because no placement changes the body box.

The union is approximate, and it errs in both directions (see *Findings* for the measurements).

- A placement nested in another container states its offsets relative to that container,
  which the rule cannot tell apart from the body,
  so a nested offset is counted short by wherever its container sits.
- A nested placement stated as an alignment is counted from the body box,
  which is wider than the container the author aligned to, so it is counted long.
- A placed body whose size is a ratio has no container to resolve the ratio against
  when the rule measures it, so it contributes nothing, also at the top level.

Each epoch records its placements once.
The states of one epoch lay out the same content,
and a display state wraps a tag in `move`, `scale` and `hide` rather than in `place`,
so all renderings of one epoch hold the same placements at the same offsets and sizes.
Animo records the epochs that the output type lays out,
which are all epochs in the HTML presentation and in the static presentation,
and only the epochs with a handout page in the static handouts.
A region also lays its body out inside `measure` to size its footprint.
A `metadata` element inside a `measure` never reaches `query`,
so Animo labels the placements of such a layout and the recording passes over them.

### Background and Overlay

A slide has three layers, and the author fills the outer two:

1. the **background**, behind everything;
1. the **canvas**, carrying the body, which is what `pan` moves;
1. the **overlay**, in front of everything.

`background` and `overlay` both take either a **color** or **content**.
A color is a CSS declaration in the HTML presentation,
on the slide container for the background and on the overlay element for the overlay,
because `set page(..)` is unavailable in HTML (see *Findings*).
On paper, a background color is the page fill,
and an overlay color is a filled rectangle that Animo places over the canvas.
Content is laid out in a box the size of the viewport.
A `#place(bottom + right, ..)` in that content resolves its alignment against this box,
and an `image(width: 100%, height: 100%)` fills the slide.
A background that needs both a ground color and content puts a filled `rect` behind the rest
of the content.

A gradient and a tiling are refused rather than accepted as a third form,
and the error message says to wrap the gradient or tiling in a `rect` of the slide size.
Typst resolves a gradient or a tiling against the element it fills.
For CSS, Animo would have to write an equivalent itself,
and a tiling has no CSS equivalent at all,
so the output types would agree only by accident.
A `rect` is content, which every output type already draws the same way.

Four rules govern both layers alike.

- **The layers belong to the viewport, not to the canvas.**
  A `pan` moves the canvas under them and leaves them where they are,
  so a logo stays in the same place on screen instead of travelling with the canvas.
  The layers contribute nothing to the automatic canvas size either,
  so a full-bleed image in the background cannot enlarge the canvas
  and make the body pannable by accident.
- **The layers hold no `tag` and no `region`,** and Animo refuses either there.
  The layers are outside the body, so nothing in the timeline could address them,
  and a tag that silently resolved to nothing would hide the cause of a mistake.
  A `per-subslide` in a layer is accepted,
  because a `per-subslide` addresses nothing in the timeline.
- **Each layer is laid out once per slide in the HTML presentation**, not once per epoch,
  because nothing in a layer can depend on an epoch.
  Each layer is a separate `html.frame` beside the canvas element,
  so a slide with four epochs still carries one background and one overlay.
  A subslide stack in a layer still holds one rendering per state,
  so a layer may carry a subslide number,
  and a layer is the cheapest place for one (see *States and Epochs*).
  In the paged outputs, each layer is laid out **once per page** of the slide,
  under or over the panned canvas,
  because a subslide stack in the layer shows the rendering of that page's state.
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

**A tag's initial state is inferred from the timeline.**
The display state and the content state of a tag are set independently
(see *Animation Primitives*),
and each takes its initial value from the first operation that addresses it.

- A name whose first continuous operation is `reveal` **starts hidden**.
  It is invisible in the initial state, but still occupies its space.
- A name whose first structural operation is `reset` **starts removed**.
  It is not laid out at all in the initial state,
  so it contributes nothing to the layout of the first epoch.
  Starting removed differs from starting hidden only inside an explicit region.
  An implicit region reserves the footprint of the tag's largest epoch either way.

The first operation is found in the order of the slide, which is first over its states,
and within one `sub` over the operations as written.
The resolver applies the operations in that same order.
A name that neither operation addresses first is visible and laid out as the body wrote it.
Adding a `reset` to a timeline therefore changes what the initial state lays out,
inside the region that bounds the change.
Adding a `reveal` does not, because content that starts hidden keeps its space.
The display state and the content state stay independent,
so a name that the timeline resets and later reveals starts out removed and hidden at once,
and the `reset` and the `reveal` undo different things.
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
Handing such a body back untouched would make every primitive a silent no-op on it,
and the author would meet the symptom far from its cause.
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

Wrapping has two costs, and the manual states both (see *Findings* for the measurements).
A tagged inline phrase can no longer break across lines, so its paragraph may reflow.
A tagged heading shifts by a few points, because the block spacing of a heading is trimmed
at the wrapper's edge and replaced by the generic block spacing.
Tagging the heading's text instead, as in `= #tag("t")[Head]`, avoids the shift exactly,
because the wrapper is then inside the heading rather than around it.

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
tagged stops.
*Resolved Design Decisions* explains why no mechanism of Animo can reach such a command.

### Regions

A region is a **bounded area of the slide whose interior may be laid out afresh between
epochs**. It is the unit of reflow and the unit of redrawing.

```typst
#region[
  Some content
  #tag("name")[tagged content]
  Some more content
]
```

`region(body, width: auto, height: auto, align: top, clip: auto, name: none)`

- **Fixed footprint.** The region occupies the same rectangle on the slide in every state.
  By default, the footprint is as wide as the region's container,
  and as tall as the tallest epoch of the region laid out at that width.
  An explicit `width` or `height` overrides this default.
  The `clip` argument, which is on by default when a size is given,
  clips an epoch that does not fit.
- **Reflow is contained.** Inside the footprint, typst lays the content out afresh for each
  epoch, so replaced, removed and restyled content genuinely reflows:
  line breaks change and following paragraphs shift.
  Outside the footprint, nothing moves.
- **Regions nest.** An inner region has a fixed footprint of its own,
  so the layout of an outer region does not depend on the epoch of the inner one.
  Footprints compose, and epochs do not multiply
  (see *States and Epochs* for why this matters to the cost).
  Regions nest at most three deep, and at most two deep on paper on a slide with a `move` that
  has a `relto`,
  because each level of nesting costs one of the five passes of layout that typst allows
  (see *Findings*).
  Tags do not count toward this depth.
- **A tag that is not inside an explicit region behaves as if an implicit region surrounded
  it**, so `#tag("x")[c]` behaves as `#region[#tag("x")[c]]`.
  Animo builds the implicit region only for a tag whose content changes,
  because a tag whose content never changes lays out the same in every epoch by itself.
  In this document, "outside a region" therefore means outside an explicit region.
  A structural change to a tag in an implicit region reflows only within the box that the tag
  reserves.
  A replacement is laid out in the largest box that any epoch of the tag needs,
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

Why a fixed footprint, rather than letting the slide reflow around a growing region? Three
reasons, in decreasing order of importance:

1. It keeps the continuous primitives composable with the structural ones. An element that
   has been moved 2 cm keeps its meaning across a content change, because its base position
   did not change. If the whole slide reflowed, every `move`, `scale` and `pan` in flight
   would jump at the same moment.
1. It keeps the HTML transition correct and cheap: the redrawn slide is pixel-identical
   outside the region, so the transition is invisible there (measured; see *Findings*).
1. It keeps the HTML and paged outputs laying out identically, which is the invariant that
   lets one source produce all three output types.

The cost is that a region reserves room for its largest epoch,
so a slide whose first epoch is short and whose last epoch is tall shows a gap at the start.
The remedies are authorial (choose `align`, give explicit sizes,
or put one region around contents that are tallest in different epochs).
Splitting a region is not among them,
because each part reserves the room of its tallest epoch,
and the maximum of a sum never exceeds the sum of the maxima.
A split makes a change reflow only the part that holds it.
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

### Animation Primitives

The timeline is a code block of an optional `init(..)` call followed by `sub(..)` calls,
with `import anim: *` inside it.
Every primitive returns a plain description (a dictionary) and performs no action itself.
`sub(..ops)` groups the operations that happen together in one step,
and the state that step reaches is the state of that `sub`.
An empty `sub()` adds a state without changing anything.
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
`handout:` says whether the handout shows the state of that `sub`, and is three-valued:

- `handout: auto`, the default, resolves to `true` for the **last** state of the slide and to
  `false` for every other one, which gives the usual handout of one page per slide.
- `handout: true` asks for an extra page at that state, which is how a state that a later
  `sub` destroys is kept.
- `handout: false` takes a page away, including the final state, so a slide can be left out
  of the handout entirely.

Every state carries this flag, the initial state included.
The initial state has no `sub`, so its flag is written as `init(handout: ..)`,
with the same three values and the same meaning.
A slide with no `sub` at all has only state 0, which is therefore also its last state,
so `auto` keeps it and `init(handout: false)` leaves the slide out of the handout.

The resolver resolves the flag to a boolean per state, and the handout renders the
states whose resolved flag is true. This makes `handout:` the only thing that says what a
handout holds, rather than a set of exceptions to a rule written elsewhere.

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
| `scale(tag, f:, fx:, fy:)`            | scale the element in place, or from its anchor once it is placed   |
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

The anchor of a tag is the top-left corner of the outer slot of the first site of its name,
as the body laid it out.
The first site is the first in document order in the first rendering that lays a site of that
name out, because a tag whose content changes is not laid out in every rendering of its slide.

- In the HTML presentation, the first rendering is the lowest epoch that lays out a site,
  and a site outside every stack counts as epoch 0,
  because the body around the stacks is laid out for every epoch.
- On paper, the first rendering is the first page of the slide that lays out a site.
  In the static presentation, the pages are the states in order,
  so that page shows the first state of the same epoch that the browser reads.
  The handouts lay out a subset of the states, so they read the first page they keep.

Document order alone would disagree with paper,
because a site that only a later epoch lays out may come earlier in the body
than one that every epoch lays out.
The handouts are the one place where the anchor depends on the output type.
The difference is harmless,
because an anchor can only differ between two renderings if a transform sits above it,
and that case is refused, as the rule below says.

This definition has the following consequences:

1. **A tag's anchor excludes the display state of that tag**, so it means the same in every state. A
   `move` is therefore idempotent in its absolute form: `move("a", x: 2cm)` twice leaves `a` in
   the same place, and `move("b", relto: "a", ..)` is unaffected by whatever moved `a`.
1. **A name with several sites moves as one.** The first site in document order lands on the
   target and every other site takes the same translation, exactly as `relto` already reads the
   first site. Two sites of one name cannot land on one point without moving independently,
   which the "several places, one tag" rule does not allow.
1. **A placed element grows from its anchor.** An axis that `x`, `y` or `relto` placed has an
   anchor other than the tag itself, and a `scale` grows the element from the start of its box
   on that axis, so an element that is both moved and scaled lands its *scaled* corner on the
   target and keeps it there at any later factor.
   The paragraph on what `scale` does, below, states the rule.

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

How the output types read an anchor is under *Architecture*.

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

**A factor is set, not multiplied into what is already there.** `scale("a", f: 2)` in one `sub`
and `scale("a", f: 2)` in the next leaves `a` at twice its size, not four times, and
`scale("a", f: 1)` restores it whatever came before. An axis the call does not mention keeps
its factor, so `scale("a", fx: 2)` after `scale("a", f: 3)` leaves `a` at 2 horizontally and 3
vertically. Successive growth is written as the product, so the author multiplies once
instead of tracking a history across every later `sub`.

**A `scale` grows an element in place, unless a `move` placed it.**
On an axis whose anchor is the tag itself, the element grows about the centre of the box typst
laid out, in every output type, and not about the centre of the ink.
That axis is one the timeline never moved, or shifted only with `dx`/`dy`,
so the element stays where it was.
On an axis that `x`, `y` or `relto` placed, the element grows from the start of that box,
which is its anchor, so the corner a `move` put on a target stays there at any factor.
The placement is a property of the position pair the resolver already keeps,
so it holds in every later state, and a `dx` after an `x` keeps it.
Each axis decides on its own.

The point a scale grows about changes only when a `move` changes the placement.
For a tag that is already scaled, the browser moves that point on the timing of the `move`,
so the tag reaches its target without a jump.
For a tag at its unscaled size, the browser moves that point at once,
so the corner of a tag that one step both places and scales travels to its target
in a straight line.

**Structural primitives** change what typst has to lay out or paint.
Only typst can render the result,
so each of them starts a new epoch (see *States and Epochs*).
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
- `apply` is structural even when the wrapper cannot possibly reflow, as with a color change.
  The reason is rendering rather than reflow,
  because typst's styling cannot be expressed in CSS in general.
  The cheap CSS-only special case, a primitive that changes a color and nothing
  else, is left for a later release.
- **`reveal` and `reset` are not pure undos**, because they also declare an initial state
  (see *Tags*).
  A `reveal` written where nothing hid the tag makes the tag start hidden.
- **Inserting** content that is not in the body is `replace` on an empty tag:
  `#tag("slot")[]` in the body, `replace("slot")[..]` in the timeline. Content that *is* in
  the body but should start out absent is a plain `#tag` that the timeline resets, which is
  what makes it start removed.
- `remove` versus `hide`: `hide` keeps the space and is smooth,
  while `remove` frees the space and reflows.
  Regions give the "occupies no space" state a bounded meaning.
  Outside a region there is nothing for `remove` to reflow,
  because the implicit region reserves the footprint of the element's largest epoch
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
- **How they compose.** A tag's content state has two parts that are set independently:
  what is laid out (the body, a replacement or nothing) and the list of wrappers.
  `replace` and `remove` set the first and keep the second. `apply` appends to the second, so it wraps whatever is laid
  out then or later, a later replacement included. `reset` sets both, back to the body with no
  wrappers.
  Consequently, `apply` followed by `replace` gives a restyled replacement,
  `reset` after `remove` gives the body with no wrappers,
  and replacing twice keeps the second replacement. None of the four
  touches the display state: a moved tag that is replaced is a moved replacement, and `reset`
  does not undo a `move`. Several operations on one tag in one `sub` apply in the order written,
  as continuous operations do, so `apply("x", f, g)` in one `sub` lays out `g(f(content))`,
  as `apply("x", f)` and `apply("x", g)` in two consecutive `sub` calls do.
- **How a region crosses its boundary.**
  All four structural primitives take `transition:`,
  which is one of the transition functions of *Transitions*
  and says how the region they change crosses the epoch boundary.
  `auto`, the default, is the crossfade, whatever the deck's `transition:` says,
  because the deck's argument is about slide boundaries.
  The `delay:` and `duration:` of the operation time the transition,
  and a `duration:` of zero is a hard cut of the region.
  The `transition:` argument belongs to the operation rather than to `sub`,
  so that one `sub` can carry one region with one transition and another region with
  another. Two operations that change one region at one boundary and
  name two transitions are refused, as two that disagree about `delay:` are. The argument is
  HTML only, because two pages have nothing between them.

### Transitions

A transition is named by a function of the `anim` module,
so that it is written where the timeline is written,
and an editor can show the parameters each one takes.

| Transition                | What it does                                         | Slide | Region |
| ------------------------- | ---------------------------------------------------- | ----- | ------ |
| `crossfade()`             | fades the outgoing content out and the incoming in   | yes   | yes    |
| `morph()`                 | moves the shared content and fades the rest          | no    | yes    |
| `push(direction: rtl)`    | moves the incoming slide in and the outgoing one out | yes   | no     |
| `cover(direction: rtl)`   | moves the incoming slide in over the outgoing one    | yes   | no     |
| `uncover(direction: rtl)` | moves the outgoing slide out over the incoming one   | yes   | no     |
| `wipe(direction: ltr)`    | shows the incoming slide behind a moving edge        | yes   | no     |

A transition is written in three places:

- as the positional argument of `init`, for the boundary into the slide;
- as `transition:` on a structural primitive, for the region it changes;
- as `transition:` on the deck's show rule, for every slide whose `init` names none.

A transition says what the crossing looks like and nothing about time.
The time is stated by the call that causes the change,
which is the structural primitive for a region and `init` for a slide.
A hard cut is therefore written as `duration: 0` rather than as a separate transition,
and every transition with a duration of zero is the same cut.

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

- `wait:` and `hold:` time the gaps around a state.
  `wait:` names the gap before the state and `hold:` the gap after it.
- `delay:` holds one operation back within its step.
- `duration:` says how long one operation takes,
  and on `init` how long the transition into the slide takes.

All four are plain numbers of seconds,
because typst has no time literal and `2s` would not parse,
and because one unit across the whole API keeps two numbers on one call comparable.
All four are HTML only,
because the paged outputs show one page per state with nothing between two pages,
so they have no clock to measure any of them on.
In the stylesheet a time carries a unit,
because a custom property read as a CSS `<time>` must carry one.
Animo writes the values it generates as `0.4s` rather than as `400ms`,
so that every number an author reads or writes is still a number of seconds,
and the runtime accepts either spelling.

#### Defaults of the Deck

Three arguments of the deck's show rule say how long motion takes when a call states nothing.

- `primitive-duration:` is how long one operation takes.
- `transition-duration:` is how long the transition into a slide takes.
- `easing:` is the timing function that both follow.
  It takes one of `"linear"`, `"ease"`, `"ease-in"`, `"ease-out"` and `"ease-in-out"`,
  the last being the default.
  A name outside that list is refused at compile time,
  because a timing function that the browser rejects would throw in the middle of a talk.

Both durations are `0.4` by default.
A fourth argument, `transition:`, is the transition of every slide whose `init` names none,
which is the crossfade by default.

```typst
#show: animo.with(primitive-duration: 0.2, transition-duration: 0, easing: "ease-out")
```

The two durations are defaults, so a call that states a `duration:` takes that duration,
also where the default is zero.
The deck above therefore cuts between its slides while the steps inside them keep moving.
A slide of that deck that is to be pushed in states the duration as well as the transition,
as in `init(push(), duration: 0.4)`.
The shorter `init(push())` takes the deck's `transition-duration:` of zero,
so the slide is entered with a cut, and the manual says so where it teaches `init`.

The deck writes the three values into the `:root` block of its stylesheet,
as the custom properties `--animo-primitive-duration`, `--animo-transition-duration`
and `--animo-easing`, and the runtime reads them at every step.
An operation that states no duration therefore follows a change of the deck's tempo,
and an operation that states one keeps it.
The `transition:` argument reaches the runtime in the deck's configuration, `data-animo-config`,
rather than as a custom property, because it is structured and no media query has to reach it.

#### Gaps

`sub(wait: 2, ..ops)` brings the state of that `sub` up two seconds after the previous state
came up, instead of on a presenter click.
`sub(hold: 2, ..ops)` keeps that state up for two seconds and then brings up the next state,
which after the last `sub` of a slide is the initial state of the next slide.
`init(wait: 2)` enters the slide two seconds after the last state of the previous slide came up,
and `init(hold: 2)` keeps the initial state up for two seconds.
`none`, the default of both, waits for the presenter.

A gap is measured from the moment the step into the earlier state was **triggered**,
not from the moment that the motion of that step finished.
A gap shorter than that motion therefore interrupts it,
and the motion continues from where it is (see *Architecture*).
A `hold: 0` is the limiting case and the reason for this definition.
It starts the next step at the same moment as the step it is written on,
so a build that runs over two slides keeps its motion and the slide transition on one clock.

One gap has two spellings, because each is the natural spelling for a different intent.
"This slide needs no click" is about the slide being entered, and is written `init(wait: 0)`.
"Do not stop here, run straight on" is about the motion that is playing,
and is written `sub(hold: 0)` on the `sub` that plays it.
Neither spelling covers every gap.
`wait:` means nothing on the first state of a deck, and `hold:` means nothing on the last one.
`wait:` also cannot be written on a `sub` that a loop generated.

The two spellings behave differently when a timeline is edited.
Take a `sub` *A* followed by a `sub` *B*, and insert a new `sub` between them.
A `wait:` on *B* still times the gap in front of *B*, which now runs from the new state to *B*.
A `hold:` on *A* still times the gap after *A*, which now runs from *A* to the new state.
In the same way, when a `sub` is appended to a slide,
the slide's trailing `hold:` times the gap into the new state,
while a `wait:` on the `init` of the next slide still times the slide boundary.

**One gap takes one number.**
A gap that both of its neighbours time is refused, and the error names both sides.
Inside a slide, the resolver sees both sides of every gap.
Across a slide boundary, the trailing `hold:` and the leading `wait:` are resolved by two calls
of `slide`.
A slide therefore hands its trailing `hold:` to the next slide through a typst `state`,
and the next slide checks that `hold:` against its leading `wait:`.
The refusal of a handout without pages uses the same mechanism.

#### Stepping

**A forward step cancels the pending timer and arms the timer of the state it lands on**,
so a presenter can always run ahead of the clock,
and a deep link starts a new timer from where it lands.

**A deep link, the first paint and a jump snap.**
A jump is any move other than a step to a neighbouring state, such as `Home` and `End`.
None of them animates, because the audience has not seen the steps that lead to the state
they would animate into.
The first paint is a deep link to wherever the fragment points,
and a reload by `typst watch` is a deep link as well.

**A backward step lands on the nearest earlier state at which the deck rests.**
The deck rests at every state except the earlier state of a join.
That state is left at the same moment it is entered,
so the audience never sees it at rest, and its motion is redirected in its first frame.
A backward step that landed there would show a composition that was never on screen,
and would cost one press per join where the forward run cost none.
A backward step therefore crosses every join it meets,
including a run of joins and a slide that the deck ran through.
The timeline decides where a deck rests, so a backward step walks the same way
while the clock is stopped.
A state that a backward step walks over stays reachable by a fragment,
and by stepping forward through a stopped deck.
Only a gap of exactly zero is a join, so `hold: 0.001` makes its state a resting point.

**A backward step over a join that ran out of a slide animates that slide into the state it
lands on.**
Going forward, the audience saw one motion,
in which the step inside the slide ran while the boundary carried the slide away.
The backward step lands on a state before the last state of the slide it enters.
If that slide snapped into the state,
the transition would show a picture that was never on screen.
The slide therefore animates into the state on `--animo-primitive-duration`,
while the boundary crosses on the duration of the slide's `init`,
and both start on the same frame.
This is the one case where a slide that is being entered moves.
A forward step into a slide snaps instead.
A slide keeps the state it was last shown in,
so animating out of that state would play backwards a step the audience never saw.
A step that crosses more than one slide boundary snaps as a whole.

#### The Clock

**The clock steps the deck in the direction it is travelling.**
One gap times the step over it in both directions,
because a gap lies between two states rather than belonging to one of them.
Going forward, the deck leaves a state after the gap that follows it.
Going back, the deck leaves a state after the gap that precedes it,
because that is the gap the next backward step crosses.
A run of automatic gaps is therefore played back as it was played forward, mirrored in time.
The clock never crosses a gap that waits for the presenter,
so backward travel ends at the state that the presenter's last forward press brought up.
The timer of the gap after that state stays unarmed,
because the presenter is the one who sets the deck going forward again.
A deck that times every gap travels back to its first state.
A backward key pressed during the travel is one more step back.

**The clock stops at the first state of a deck** rather than turning,
because no earlier state exists.
Otherwise, the timer of the gap after the first state would carry the deck forward
and undo the step that just arrived.
This stop also holds a deck that would run out of its first slide at the first paint.
A forward step or `Space` starts the clock again.
A backward step over a gap that waits for the presenter does not touch the clock,
so a deck that times none of its gaps behaves as a deck without a clock.

**`Space` pauses and resumes the clock** while the deck has one,
and steps forward otherwise, because that is the key a presentation remote sends.
The pause also pauses every animation in flight, so the picture holds still.
Resuming continues what is left of the gap and of the motion,
in the direction the deck was travelling.
A step made by hand during a pause leaves the clock paused.
A forward step therefore ends the stop at the first state, but not a pause.
Both the stop and the pause set the attribute `data-animo-paused` on the root element.
Neither is part of the URL fragment, which holds only the position,
so a deck restored from a fragment comes back running, also after a reload by `typst watch`.

#### Delays and Durations

**`delay:` holds one operation back within its step**, and every primitive takes it,
defaulting to zero.
`scale("a", f: 2, delay: 0.2)` starts a fifth of a second after its step begins.
**`duration:` says how long the operation then takes**, and every primitive takes it as well,
defaulting to `auto`, which is the deck's `primitive-duration:`.
A number is a number of seconds, so `reveal("a", delay: 0.5, duration: 2)` fades in over two
seconds.
The delay and the duration become the delay and the duration of a Web Animations API effect,
and all animations of a step are created in one task, so a step keeps one clock.

On a structural operation, the delay and the duration time the transition of the region that
the operation changes.
The epoch boundary lasts until the last of these transitions has finished,
and the outgoing rendering stays visible in a region until the transition of that region ends.
Two structural changes can therefore be staggered when they sit in two regions,
which two bare tags always do.
Two operations that change one region at one boundary and disagree about their timing are
refused, because a region crosses a boundary once.

**A duration may run past its step.**
An operation that outlives its step is overtaken rather than clamped or refused.
A continuous operation then continues from where it is, as any interrupted animation does.
For a structural operation, the epoch boundary stretches with the duration,
so two boundaries may be in flight at once, and three renderings may paint one region together.
*Architecture* describes how the newer boundary takes the older one over.
A short gap and a presenter who presses twice reach the same situation,
so clamping or refusing a long duration would not remove the situation.

**A backward step is the step it undoes, mirrored in time.**
The length of a step is the time until its last operation ends.
An operation that ran from `delay` to `delay + duration`
runs backwards from `length - delay - duration`, for the same duration.
The last thing the audience saw arrive is therefore the first thing they see leave,
and a step of three staggered lines comes apart in the reverse of the order it was built up.
Replaying the forward schedule instead would let the line that arrived first leave first,
and the composition would pass through pictures that the forward step never showed.
A backward step over joins runs between two states that are not neighbours.
The audience saw one redirected motion there, so the backward step is one motion as well,
mirrored about the length of the step that began it.
The epoch boundaries it crosses share its clock (see rule 2 under *Architecture*).

#### Reduced Motion

**A reader who asked for less motion gets none, whatever the deck or the timeline says.**
A number in a typst source is invisible to a media query,
so the reader's preference reaches the runtime as the custom property `--animo-motion` on `:root`.
The property is `auto`, unless `prefers-reduced-motion: reduce` sets it to `none`.
While it is `none`, every step snaps and ignores its delays, as a deep link does.
Zeroing the deck's durations would not have this effect,
because a duration that a call states overrides them.
The declaration in the media query is `!important`,
so it outranks the `:root` block of the deck and any stylesheet that an author adds to the page,
although both come later in source order.
A reduced motion leaves the gaps alone, because they are pacing rather than motion,
and zeroing them would run an autoplaying deck to its end at once.

### States and Epochs

States and epochs form the execution model that ties the two classes of primitives together.

- A slide with *S* `sub` calls has **S+1 states**, numbered 0 to S.
  State 0 is the slide exactly as the body declares it.
  State *i* is state *i-1* with the operations of the *i*-th `sub` applied.
  Continuous operations accumulate as display state,
  and structural operations accumulate as content state.
- A new epoch starts at every state whose `sub` holds at least one structural operation,
  so a slide with no structural operations has exactly one epoch.
- The content state of an epoch fixes the content of every tag (body, replacement, or nothing)
  and its accumulated wrappers.
  That is all typst needs to lay out the epoch.
- A region's content depends only on the content state, so a region measures per **epoch**,
  not per state.
  Each region measures **only the epochs the slide actually has**,
  not every combination of the content states of its tags,
  and consecutive states within one epoch cost it nothing.
  The inner regions of a region have fixed footprints,
  so the measurement of an outer region does not depend on the epochs of its inner regions.
  The cost of a region is therefore linear in the number of epochs.

**How a region measures one epoch.**
A region cannot substitute the content of an epoch into its body,
because it receives its body as opaque content and cannot rewrite the tags nested inside it.
Instead, the epoch to lay out is an entry of the view that the slide provides to the body
(see *Scoping*).
The region lays its body out once per epoch, under a copy of the view with that entry set,
and each tag resolves its content for that epoch as it is laid out (see *Findings*).
This mechanism makes reflow inside a region possible
without turning the body into a function of the epoch,
which is the `s => ([body], s)` threading that *Resolved Design Decisions* rejects.

The renderings that each output type lays out per slide are the following.

| Output type         | Renderings                                                  |
| ------------------- | ----------------------------------------------------------- |
| HTML presentation   | one, with an epoch stack in every region in no other region |
| Static presentation | one per state (S+1)                                         |
| Static handouts     | one per state with `handout` resolved to true               |

A slide with one epoch is one rendering in the HTML presentation, and nothing more.
Once a slide has two epochs, every region that sits in no other region holds an epoch stack,
also a region whose content is the same in every epoch.
Which tags a region holds is known only after layout,
so a region cannot tell in advance whether its content changes.
Content that never changes is therefore cheaper outside every explicit region.
Each layer is one rendering per slide whatever the epochs (see *Background and Overlay*).

A `per-subslide` is the one construct whose cost is counted in **states** rather than in epochs,
because it is one rendering per state of its slide, wherever it sits.
In a layer, or in the body outside every region, a `per-subslide` is one stack per slide.
Inside a region, it is one stack per rendering of the region's epoch stack,
which makes a layer the cheapest place for a subslide number.
The plan carries nothing about a `per-subslide`,
because the runtime finds the renderings by the label each of them carries.

### Architecture

The same tagged content feeds three output types.
This section specifies how each of them is built.
How the browser runtime is organised in files, which input it reads,
which events it announces and which attributes it reads and writes on the page
is described in [docs/architecture.md](../docs/architecture.md),
and the URL fragment in [docs/presenting.md](../docs/presenting.md).

#### What Typst Emits for the HTML Presentation

A slide is *one* `html.frame`, which is one inline SVG laid out on the canvas
and holding one rendering of the body.
Everything outside the regions is the same in every epoch, so it is laid out once.
Every region that sits in no other region,
whether explicit or the implicit region of a tag, lays its body out once per epoch.
The region places these renderings on top of each other at the corner of its footprint,
in epoch order, as its epoch stack.
Each rendering of a stack is a labelled block,
so that it becomes a group `<g data-typst-label="animo-<kind>-<index>">` that the runtime can
address.
The kind is `epoch` or `subslide`,
and says what the index counts and how the runtime chooses the rendering it shows.

Epoch stacks do not nest.
A region inside a rendering of an epoch stack is already laid out once per rendering,
so the inner region lays out the epoch of that rendering.
A subslide stack does sit inside each rendering of an epoch stack that holds it.
A region on paper lays out the epoch of its page, so an epoch stack exists only in HTML.

The slide is one frame rather than one frame per stack,
because typst's deduplicator works within one frame.
The renderings of a slide then define each glyph they share once between them
rather than once each,
which is the only part of that duplication a package can reach (see *Findings*).

The canvas element sits inside the slide container,
which is the viewport and clips the canvas (`overflow: hidden`).
Inside the slide container, the canvas element sits between the frame of the background
and the frame of the overlay.
These two are frames of the slide rather than renderings inside the frame of the canvas,
so a `pan` does not move them.
The slide containers are the children of the stage.
The stage clips its content and isolates the blend between two slides,
and the deck centres the stage on the surround of the page.
Each tag site appears as a `<g data-typst-label="...">` group,
once if it lies outside every region and once in every rendering of the stack it sits in.

#### What the Browser Animates

**A tag's display state.**
`reveal` and `hide` animate `opacity` on the tag's inner slot.
`move` animates the CSS `translate` property, computed from the anchors that the browser
measures as *anchor(relto) + offset - anchor(self)*,
which is the identity for a tag the timeline has not moved.
`scale` animates the CSS `scale` property,
about the centre of the box typst laid out for the element, or from its start on a placed axis,
with one value for `f` and two for `fx`/`fy`.
The HTML target places a zero-size marker at the far corner of that box, beside the slot,
and the runtime reads the centre off it.
A `move` that changes the placement animates `transform-origin` with its `translate`.

**A pan** animates `translate` on the canvas element as a percentage of the canvas,
which follows the size of the window without being measured.

**A subslide stack** shows the rendering of the state being entered and hides the others,
by writing `opacity` on the labelled group of each rendering.
The switch snaps, also in a step that animates,
because two numbers that crossfade into each other are both unreadable.
The stack uses `opacity` rather than `visibility`,
although `visibility` hides the renderings of an epoch stack that are not shown.
A descendant may take its visibility back,
so a rendering that did so would paint out of an epoch that the slide is not showing,
while a rendering at `opacity: 1` inside a hidden epoch stays hidden (see *Findings*).

**An epoch boundary** carries each changed region across with the transition its operations
name.
The crossfade fades the outgoing rendering of the region's epoch stack out
and the incoming one in.
While it runs, the renderings carry `mix-blend-mode: plus-lighter`
and the container of the stack carries `isolation: isolate`.
Every other stack shows the rendering of the epoch being entered without animating.

The morph crossfades the region in the same way,
and also animates `translate` on the matches inside it.
The outgoing element of a match travels from its place to the place of the incoming one,
and the incoming element travels from the place of the outgoing one to its place,
so the two are at one position at every moment.
Their opacities are those of the crossfade, `1 - t` and `t`,
which `plus-lighter` adds to one.
The pair therefore reads as one opaque element on the path,
and a pair whose colors differ reads as the interpolation of the two colors.
Nothing is cloned, and no opacity is touched other than the one the crossfade animates.
Unmatched content fades out or in where it is.
The translations are animation effects and never inline style,
so a slide at rest carries no morph translation.
The outgoing element jumps back to its place when its animation ends,
at which point its opacity is zero.
*Resolved Design Decisions* says what counts as a match.

**A slide boundary** crossfades the two slide containers by the same means.
The containers inside the stage, which isolates, carry `plus-lighter`,
and the outgoing container stays laid out until the two have crossed.
The crossfade lasts for the duration of the slide's `init`,
which is `--animo-transition-duration` unless the `init` states one.
The crossfade is not scoped to regions, because two slides share nothing that has to hold
still, so the whole container is the unit.
A duration of zero is a hard cut, whatever the transition,
and shows one container in place of the other without any animation.
The slide crossfade differs from the transition of an epoch boundary in two ways.

- A slide that takes no part in a boundary is hidden with `display`,
  while a rendering of an epoch stack is hidden with `visibility`.
  A hidden rendering has to keep the geometry that the morph reads,
  while a hidden slide is needed neither for its ink nor for its geometry,
  and laying out every slide of a long deck costs seconds of first paint
  (see *Resolved Design Decisions*).
- The surround of the deck is a color on the page rather than on the stage,
  because the stage isolates the blend,
  and the background of the stage would otherwise be added into both slides (see *Findings*).

Typst names a gradient, a clip path, a tiling, a mask and a filter by an id derived from its
content, and a reference resolves to the first definition of that id in the document.
That definition may sit in a slide hidden with `display`, and the reference then draws nothing
(see *Findings*).
At load, the runtime therefore copies the first definition of each id into a zero-size `<svg>`,
which is the first child of `body` and stays laid out,
and removes the id from every original.
The originals lose their ids because webkit drops every reference to an id
when one definition of it stops being laid out, even while the copy still defines it
(see *Findings*).

A slide boundary that pushes, covers, uncovers or wipes animates `translate` or a `clip-path`
inset on the two containers instead.
Such a transition is a function of the boundary's owner, which is the slide with the higher
number,
and of a progress `p` that runs from 0, where the owner has not arrived, to 1, where it has.
A forward step animates each container from what it shows to the state at 1,
and a backward step to the state at 0, which is the mirror that *Timing* prescribes.
A slide that had no layout before the step starts at the far end.
The owner comes later in the document, so the owner is in front in both directions.
These transitions overlap two opaque slides, which `plus-lighter` would add together,
so both containers carry `mix-blend-mode: normal` until the deck moves again,
which is as long as the slide being left keeps its layout.
An uncover moves the other slide out over the owner,
so Animo gives the other slide `z-index: 1`, which puts it in front of the owner.
The `z-index` stays as long as the blend does,
because the owner is still laid out beneath the other slide after a backward uncover.
A single slide renders the same under either blend (see *Findings*).
The stage clips a slide that is pushed out of it.

#### The Five Rules of the HTML Presentation

1. **Continuous state is applied to every site of a tag in every rendering of every stack at
   once**, not only in the rendering being shown.
   Entering an epoch therefore never needs initialisation,
   and a step that is both structural and continuous, such as a `replace` together with a
   `move`, animates in lockstep in the outgoing and the incoming rendering,
   so the composite reads correctly.
   An operation on a tag that is absent from a rendering is a no-op in that rendering.

1. **The transition of an epoch boundary is scoped to the regions whose content state
   changed**, not to the whole frame.
   Only the epoch stacks of the changed regions are animated, and nothing else on the slide
   takes part. Two mechanisms together make that true.

   - **The stack holds nothing but its region.** The renderings of a stack are the region's
     body laid out once per epoch and nothing else, so the outgoing rendering has no ink
     outside the region's footprint, and the containment outside the region is exact *by
     construction*.
     A rendering that is not being shown is hidden with `visibility: hidden`
     rather than `display: none`, because `visibility` keeps the rendering laid out,
     so the morph can still read its geometry.
     Every rendering of the stack that is still painting takes part in a transition,
     not only the one the step is leaving.
     A boundary crossed while an earlier boundary is still running
     finds more than one rendering painting the region.
     Those renderings then all leave on the new boundary's clock, under one easing,
     while the incoming rendering arrives under the complement of that easing.
     Their opacities therefore still add up to one,
     whatever each rendering was showing when the boundary began.
     A step may also cross more than one boundary at once, as a backward step over a join does.
     Such a step carries the stacks of all the boundaries it crosses, each stack once,
     on the clock of the step itself,
     and the timings that the operations of the crossed steps stated are dropped.
     The boundaries that such a step crosses lie in the slide it stands on,
     or in the slide it enters when the join it walks back over ran out of a slide.
   - **`plus-lighter` on the renderings makes the two halves add, inside a container that
     isolates.** The renderings of a stack are siblings in one group.
     While a transition runs, the renderings it carries take `mix-blend-mode: plus-lighter`
     and that group takes `isolation: isolate`,
     so the outgoing rendering at `1 - t` and the incoming one at `t` add up to
     exactly one opaque region, and nothing dips.
     Without the isolation, chromium and webkit also add the two halves to the ink
     under the region (see *Findings*).
     The SVG of the slide's frame isolates at all times,
     which keeps the blend off the page behind the slide.
     The effects of the transition hold the blend and the isolation as keyframes
     with the same value at both ends, so neither is part of the state at rest,
     because a blended or isolated group is drawn through a layer that changes some glyph edges
     (see *Resolved Design Decisions*).

   The measured cost is a rounding error of 1/255 inside the region,
   against 62/255 for a plain opacity crossfade, and nothing at all outside the region
   (see *Findings*).

1. **Animo emits only the individual transform properties** (`translate`, `scale`) and
   never the `transform` shorthand, which would clobber typst's own positioning (see
   *Findings*).
   `transform-box: view-box` and a `transform-origin` at the centre of the box typst laid out,
   or at its start on a placed axis, make a `scale` grow the element as typst's `scale` does on
   paper.
   These two properties fall under a similar prohibition,
   because they also re-anchor the `transform` attribute of the element,
   so on a group that typst positioned they move the group's content (see *Findings*).
   The runtime therefore writes both properties on the slot it is about to transform,
   and never as a rule in the stylesheet, which cannot tell a slot from a region's content.
   A resize and a shape morph also animate `d` and `stroke-width` on the two paths they pair.
   Neither property is a transform, and neither is ever written as inline style,
   so a path at rest shows its attributes.

1. **Continuous state and boundary state get separate nested slots.** `tag` wraps its body
   twice, in two wrappers of the same kind, so every tag site emits a labelled outer group with
   an unlabelled inner group inside it (see *Findings*).
   Continuous primitives address the inner group (`[data-typst-label="x"] > g`).
   Everything that belongs to an epoch boundary, which is the transition of a region and the
   translation of a match, addresses the labelled outer group.
   CSS gives each element only one `translate` and one `scale`,
   so the split is what keeps the two classes from clobbering each other.
   The order follows from how a boundary effect is measured:
   it is measured in the coordinates of the frame
   and must sit *above* the continuous transforms rather than inside them,
   or a tag that is being scaled while its region reflows
   moves by the wrong amount in the wrong direction.
   The morph measures a match on the screen and maps the difference into the user space of
   the parent of the element it translates, through the inverse of that parent's
   `getScreenCTM()`, which holds every transform above the element, typst's own included.
   Opacity is exempt from the ordering argument, since the two slots simply multiply,
   but it follows the same convention.

1. **`pan` belongs to the canvas element, not to what is inside it.**
   `pan` is a slide primitive, so it must not be applied per epoch.
   The body and its stacks sit in the frame that the canvas holds,
   so moving the canvas moves all of them together and keeps them registered.
   The canvas element is also the one place where Animo applies a transform outside an SVG
   group.
   The prohibition of rule 3 does not apply there,
   but `translate` is used there too, for consistency and to leave `scale` free for a future
   zoom.

#### How the Plan Reaches the Browser

The resolved display state of every state of a slide travels as compact JSON, keyed by tag name,
in a `data-animo-plan` attribute on the slide container.
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
so the runtime applies what it is given and resolves nothing,
and no tag site reports a display state.

The one exception is the anchor of a position.
Each state carries its pan, and each moved tag its position,
as an anchor and an offset per axis, `(relto:, offset:)`, with the offset in points.
The slide's margin and canvas size travel beside the states.
A tag's position cannot be read in HTML,
so the resolver keeps the anchor as a name and the runtime adds the position it measures
(see *Anchors in the Two Targets*).
A tag's display state in the plan holds its visibility, its position and its scale factors,
and an anchor of `null` is the canvas origin:

```json
{
  "hidden": false,
  "x": {
    "relto": "node",
    "offset": 14.17
  },
  "y": {
    "relto": null,
    "offset": 0
  },
  "scale": {
    "x": 2,
    "y": 1
  }
}
```

Beside the display state, each state carries the `wait:` and the `hold:` it was given,
and each operation the `delay:` and `duration:` it was given, all in seconds,
because none of them can be resolved anywhere but at the moment the step runs.
Both gap numbers travel rather than one resolved number per gap,
because the gap across a slide boundary is timed by two slides and emitted by two calls,
so the runtime is the first place that sees both sides of it.

A state also carries the length of the step that enters it,
which is the length that a backward step mirrors its operations about.
That length travels as two numbers rather than one, which are `stated` and `unstated` in
the state's `span`.
The resolver can add up only the operations that stated a duration,
because the other operations take the `primitive-duration:` of the deck,
which lives in the stylesheet.
The resolver therefore hands over the largest end it could compute as `stated`
and the largest delay of the operations it could not as `unstated`,
and the runtime adds `--animo-primitive-duration` to `unstated`.
The length of the step is the larger of the two sums.
A step that states no timing at all carries neither number,
and lasts exactly one `primitive-duration:` of the deck.

Each state also carries its resolved `handout:` flag,
so that a view of the deck that shows one state per slide can show the state the handout shows.

Each epoch lists in `changed` the names of the tags that the boundary into it changes,
each with the timing and the `transition:` of the operations that changed it,
and nothing for `auto`.
The runtime finds the stacks that a boundary crosses by those names,
because a stack holds the groups of the tags laid out in it,
and by comparing the renderings of each stack on the two sides of the boundary.
A stack that crosses only because its renderings differ takes the deck's default timing
and the crossfade.
A `wrap: none` tag becomes no group,
so the epoch also lists in `regions` the tag whose timing and transition a stack takes,
keyed by the label of the group of the region that holds the stack.
Only the membership reports know which region holds such a tag.

The transition into a slide travels in the attributes `data-animo-transition` and
`data-animo-transition-args` of the slide container,
for the reason the plan is an attribute.

#### Motion and the Clock

**Motion is driven by the Web Animations API**, not by CSS transitions.
A step writes the new display state as inline style,
and animates from what the element was showing to that new state.
The inline style is therefore the state, and the animation is only how the element got there.
An interrupted step therefore continues from where it is,
a backward step lands on exactly the geometry the earlier state had,
and a restore needs no transition to suppress.
A backward step differs from a forward one in two ways.
Every effect of a backward step is mirrored about the length of the step it undoes,
and a backward step may animate the slide it enters into its state (see *Timing*).

A step is put on the page in two phases.
The first phase plans an effect for every element and property that the step changes,
from what the element shows to what it is to show, and writes nothing.
The transitions of the step's epoch boundaries are planned in this phase as well,
so the geometry they read, such as the places a morph measures, is the page before the step.
The second phase writes every style of the step, then reads what the elements compute,
and then creates every animation,
so the browser recalculates style once per step rather than once per element.

Every animation of a step is created in one task, and none of them is given a start time,
so the browser starts them all on the same frame.
The step therefore has one clock, and the transitions of its epoch boundaries join that clock.
Reading that clock off `document.timeline` instead would be wrong,
because the timeline does not advance while the page draws nothing (see *Findings*).
A step animates only the properties it changes,
because a property that holds still in the keyframes stops chromium from drawing the properties
beside it (see *Findings*).
An operation's `delay:` is the delay of its effect, and a delayed effect fills backwards.
The state it is arriving at is already the element's inline style,
so an effect that did not hold its first keyframe while it waits would show that state first
and then jump back to animate into it (see *Findings*).

A gap's `wait:` or `hold:` is the only timer the runtime sets.
That timer is armed when a state is entered,
and cleared whenever another state is entered, whatever entered it,
so a presenter stepping by hand never races a clock that is still counting.
A backward step arms the timer of the gap before the state it lands on (see *Timing*).

#### Anchors in the Two Targets

*Animation Primitives* defines which site's corner a tag's anchor is.
The anchor is the corner of the tag's outer slot,
and the display state of the tag sits inside that slot,
so `relto` means the same in every state, and an absolute `move` is idempotent.
`pan` reads the anchor of its `relto`, and `move` reads the anchor of its `relto` and of the
tag it moves.
The two targets read the corner by different means, because positions cannot be read in HTML.

- The browser reads the origin of the labelled group, mapped into the user space of its frame,
  when the slide is first shown and before anything is written on it.
- On paper, typst cannot use the position of the outer slot,
  which for a box on a line is the line's baseline (see *Findings*).
  Every tag site therefore carries a zero-size marker at the corner of its outer slot,
  and every page carries a marker at the canvas origin,
  which turns a position on a panned page back into a position on the canvas.
  Only the paged targets emit these markers, so the groups the browser addresses are untouched.

Over every kind of tag site measured, the anchors that the two targets resolve differ by at most
0.0005 pt, and a pan read back off the rendered page differs by at most 0.005 pt
(see *Resolved Design Decisions*).

Anchors are resolved once per slide rather than once per state.
On paper, that is one introspection pass over the slide's pages,
and in the browser, one measurement when the slide is first shown.
Only the tags that the plan actually names are read.
A position whose `relto` names the moved tag needs no reading at all,
since the two terms cancel whatever that anchor is.

#### Refusals That Depend on Layout

Three refusals can only be decided after the body is laid out:

- a pan or a move relative to a tag the slide does not have;
- an anchor read from inside a tag that the timeline moves or scales;
- two operations that change one region at one boundary and disagree about their timing or
  their transition, because which region holds a tag is known only after layout.

All three can only be detected from `query`, and a panic raised there may be swallowed.
They are reported reliably because each runs in a separate context block after the slide,
which emits nothing.
The checks compare the timeline against the reports of the slide's rendering:
the site reports, the anchor markers on paper and the membership reports.
Each site report carries the tags whose display state encloses the site.
A failing check then empties only the context block it runs in.
A site that is reported one layout pass late is forgotten together with the errors of that pass,
and a tag that is really missing fails the pass that typst ends on (see *Findings*).

A site learns which tags enclose it from the view it is handed,
as it learns everything else about its slide,
because the body is opaque to the resolver.
Every enclosing site that carries a display state, which is a wrapped tag or a named region,
extends the `within` entry of the view (see *Scoping*).
Only a name that the timeline addresses with a continuous primitive extends it,
so a deck with no continuous primitive threads nothing.

#### Static Presentation

The static presentation has one page per state.
Each page is a snapshot of the viewport at that state, clipped out of the canvas,
with the background under it and the overlay over it.
The `move`, `scale` and `pan` primitives become discrete jumps between pages,
and `replace`, `remove` and `apply` are rendered in place.
A panned state is therefore a page showing a different part of the canvas,
so panning survives into the paged output.
Everything under *Timing* is absent rather than approximated,
and so is every transition, because two consecutive pages have nothing between them.

#### Static Handouts

The static handouts have one page per state whose `handout` flag resolves to true.
By default, that is only the **final state of the slide**,
which shows the viewport at its final position, as in the static presentation.
Extra pages are asked for with `sub(handout: true, ..)`, and with
`init(handout: true)` for the slide's initial state.
Pages are given up with `sub(handout: false, ..)` and `init(handout: false)`,
so an ordinary slide contributes one page
and an author who says so contributes any number, none included.
A deck whose every state gives up its page is refused,
because typst would otherwise emit one blank page at a size the deck never mentioned.

A handout therefore loses content on a slide that overwrites it.
A `replace` destroys what it replaces, and only an explicit `handout: true` keeps it.
Animo cannot warn about this, because typst offers packages no way to emit a warning,
so the manual says so.
A panned slide loses content in the same way.
A handout page shows the viewport of its state rather than the whole canvas,
so `handout: true` is also how a view that a later pan leaves is kept.

### Scoping

Tags live in the scope of their slide, with no per-slide context object threaded through
the body:

- In the **HTML** output, CSS/JS selection is scoped to the current slide's container, so
  `[data-typst-label="line1"]` in slide 3 cannot affect slide 7.
  Such a selector naturally matches *all* elements with the same tag inside one slide.
  This is exactly the "several places, one tag" requirement,
  and it also applies continuous state to every rendering of every stack of the slide at once.
- In the **paged** outputs, `#slide` resolves its plan before laying out its states
  and hands the result to the body, so each tag site sees the plan of the slide it
  sits in.

Names share one namespace with the labels Animo emits for itself, since both end up as a
`data-typst-label` in the same output and the runtime addresses what it finds there. The prefix
`animo-` is reserved for Animo's own labels, and `tag` and `region` refuse a name that starts
with it.
An unnamed region needs a label,
because the runtime addresses its group when a boundary carries it across,
and only a labelled box becomes a group at all.
An unnamed region therefore gets the label `animo-region-<n>`,
where `n` is the number in its region key, which is the same in every output type.
A region inside an epoch stack counts once, not once per rendering,
and a region inside content that changes borrows the key of the region around it,
so that the numbers agree across epochs.
The renderings of a stack take `animo-epoch-<n>` and `animo-subslide-<n>`
out of the same reserved prefix.

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

The plan has to reach the tag sites in the HTML presentation as well,
because regions measure their epochs while the body is laid out.
This creates no cycle, because the plan is an argument of `#slide` and does not depend on the
body.

The plan is **provided**, not published.
`#slide` installs a show rule over its body,
and every tag and every region emits a marker that the rule replaces with a rendering
for the view it is given.
A view has the following entries.

- `slide` is the position of the slide in the deck.
  A site needs it to report anything back out of the frame it sits in,
  because `query` is document-wide while a tag name means nothing outside its own slide.
- `state` is the state to lay out, or `none` in the HTML presentation,
  where one frame covers every state and the browser applies the display states.
- `states` is how many states the slide has,
  and `handouts` holds the resolved `handout:` flag of each of them.
  Both are properties of the slide rather than of a rendering,
  so they are the same in every view of one slide.
- `epoch` is the epoch to lay out.
- `epochs` holds the content state of every epoch, and not only of the one laid out,
  because a tag whose content changes reserves room for the largest of them,
  and a region measures another epoch with a copy of the view whose `epoch` differs.
- `display` is the display state of `state`, keyed by tag name.
  It holds only the tags that the timeline addressed,
  so a tag that the timeline never touched rests where the body put it.
  Every position in it is resolved to two lengths,
  rather than kept as the anchor and the offset that the resolver holds,
  because only the rendering knows where an anchor is.
  A tag site applies to its content what it is handed and resolves nothing itself,
  so the anchors are read only once per slide.
- `continuous` holds the names that a continuous primitive addresses anywhere in the slide,
  the target of a `pan(relto:)` included.
  A tag site that cannot be animated at all has to say so in state 0
  rather than in the state that moves it,
  and a `wrap: none` tag learns only from this entry that the timeline animates it.
- `region` says where the content sits, in three fields:
  the region key of the nearest region whose footprint is the same in every epoch,
  whether an explicit region bounds the content,
  and whether the content is laid out in every epoch.
  Every site reports the key of its region in a membership report,
  which is how the regions that a boundary carries are found.
- `within` holds the tags whose display state encloses the content, outermost first,
  and every site reports it, which is how an anchor read from inside a transformed tag is
  refused (see *Architecture*).
- `numbering` says how a region inside the rendering of an epoch stack takes its number,
  so that it counts once rather than once per rendering.
  Such a region counts on a second counter, which every rendering sets back to zero,
  and its number is the number of the region that holds the stack plus the second counter.
  On paper, where only one rendering is laid out, the region therefore gets the same number.
  Every update of either counter is a constant or a step,
  so the numbers settle in one pass of layout however many regions a slide has.
- `stack` says whether a region places an epoch stack in its footprint,
  which only the outermost regions of the HTML presentation do.

A `per-subslide` uses a second kind of marker.
A tag marker is answered by the body's view and refused anywhere else,
while a stack marker is answered wherever a slide lays content out,
including the background and the overlay.
The stack marker is handed the **stack view**,
which is the part of a view that content outside the body may have:
the `handouts` of the slide and the `state` being laid out.

A state variable cannot do this,
because `state.get()` inside `measure(..)` resolves at the enclosing context's location,
so a caller cannot set a state, measure, set it again and measure again,
which is exactly what a region has to do to size its footprint over its epochs.
A show rule does reach inside `measure`, providers nest with the innermost winning,
and the label of the marker does not reach the output (measured; see *Findings*).
Because a view is an argument rather than a document position,
a deck that wraps `#slide` in a custom function changes nothing.

A few things about a slide are published in a counter or a state rather than provided,
and none of them is the plan.
Each is constant over the slide, so nothing about it has to vary inside a `measure`.

- The slide counter and the flag that says whether the slide is counted are published,
  because `slide-number()` is an ordinary counter read
  that an author writes anywhere, in the body or in a layer.
- The deck-wide step counter is published for the same reason,
  and a subslide stack reads it.
- Whether the document is compiled to HTML is published, as *Output Mode Selection* says.
- The trailing `hold:` of the slide is published, as *Timing* says.
- Whether a body is being laid out is published, so that a tag outside any slide can
  be diagnosed at the tag site. That diagnosis cannot come afterwards, because a marker nobody
  replaced is indistinguishable from one that was (measured; see *Findings*), and a tag whose
  marker is never replaced would simply drop its content.
  The check is a separate `context` block beside the marker,
  because a check in the block that holds the marker would delay every site nested inside it
  by a pass of layout (see *Findings*).

Duplicate labels across a document are permitted by typst and cause no error.

### Output Mode Selection

One source file is compiled once per output type.
The HTML target is detected automatically with `target()`.
The two static modes are selected explicitly, and the default is `handout`:

```bash
# HTML presentation
typst compile --format html --features html talk.typ talk.html

# Static presentation (one page per state)
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

The file format is not an output type.
Both static types are paged modes, and typst exports either of them to PDF, SVG or PNG.
SVG is suited to embedding a page in another document,
and PNG serves a consumer that needs a raster image.
Multi-page export to SVG or PNG needs a page-number template in the output path:

```bash
typst compile -f svg talk.typ 'talk-handout-{p}.svg'
typst compile -f svg --input animo=presentation talk.typ 'talk-presentation-{p}.svg'
```

### Consequences of Confining Reflow to Regions

Bounding reflow by regions, rather than forbidding it or letting it reach the whole slide,
has the following consequences:

1. A slide with no structural operations is exactly **one** rendering in the HTML presentation,
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

Each entry below answers a question that is settled,
with the reasons for the answer and the alternatives that were rejected.
*Specification* states the rule itself, and *Findings* holds the evidence.

### Feasibility

- **Is this feasible in typst?** Yes, for all three output types.
  The enabling mechanism is the `data-typst-label` attribute,
  which makes tagged content individually addressable in the SVG that `html.frame` produces
  (see *Findings*).

- **Can content and style change, with reflow?** Yes, but only within a bounded area,
  and only by laying that area out again.
  Typst cannot lay out a fragment of an SVG it already wrote, and the browser cannot lay out
  typst content, so the only available mechanism is to lay the area out for every content state
  and let the browser choose between the renderings.
  Regions exist to keep the cost and the visual consequences of that choice bounded.
  Fixing the footprint of a region at the maximum over its epochs
  keeps everything outside the region pixel-identical between epochs,
  in the browser as well as on paper.

- **HTML export: `reveal.js` or custom?** Custom.
  Animo animates `<g>` nodes inside an inline SVG,
  so reveal.js's DOM-fragment machinery contributes almost nothing while
  imposing a separate slide model, CSS cascade and scaling.
  Panning is not part of reveal's model either,
  which is why `touying-exporter` turned to impress.js for it.
  `slipst`'s complete custom runtime is about 214 lines of TypeScript plus about 68 lines of
  CSS, so a custom runtime is small.
  Animo uses plain JavaScript, inlined with `read()`,
  so that a package installed from Universe needs no node toolchain.

### The Body, Tags and Regions

- **Should the whole slide body be a region?** No.
  The body stays a plain layout in which nothing reflows, and regions are opt-in.
  If the body were a region, every structural operation would lay out the whole slide again,
  which would move the base geometry under every continuous animation in flight
  and make a transition visible everywhere.
  Opting in per region also documents the author's intent about where reflow may happen.

- **How are group-like containers and tags related?** They are orthogonal and both are kept.
  A region is the *unit of reflow and redrawing*, and a tag is the *addressable handle*.
  A tag that is not inside an explicit region behaves as if it had an implicit region,
  so the simple case needs no extra syntax,
  and `region(name: ..)` covers the case where the container itself must be animated.

- **Is the name `group` right for the container?** No, it is called `region`.
  `group` collides with two neighbouring meanings,
  which are cetz's `draw.group` and the SVG `<g>` groups that Animo itself emits.
  The point of the construct is that it is a *bounded area* of the slide.

- **What crosses a boundary when no region bounds the change?** Nothing,
  because such a change is refused.
  A `wrap: none` tag outside an explicit region has no box,
  so no area could hold its change,
  and Animo refuses a structural primitive on it in every output type
  rather than only in the one that could not show it.
  The refusal names the two ways out, a wrapper or a region around the tag.
  The alternative was a transition of the whole rendering of the slide.
  It would need a second structure beside the epoch stacks, chosen from the membership reports,
  and a structure that depends on the reports it produces did not converge when it was tried.
  Typst gave up after five attempts, and the query saw 0, 0, 1, 0 and 0 reports in them.
  A reduced document with a switch on a `query` of the same shape converged,
  so the cause inside Animo was not isolated.

- **Which regions hold an epoch stack?** Every region that sits in no other region, and no other.
  A region inside the rendering of a stack is laid out once per rendering already,
  so a stack there would multiply the renderings by the epochs again.
  The outermost region therefore crosses a boundary with everything inside it,
  and two operations that change two regions inside one region at one boundary
  have to agree about their timing and their transition,
  as two operations inside one region do.
  A region whose content never changes still holds an epoch stack once its slide has two
  epochs, because the region cannot know before layout which tags it holds.
  Deciding from the membership reports of an earlier pass of layout
  would make the structure depend on the reports it produces,
  which is the shape that did not converge in the previous entry.

- **Is the max-footprint rule tolerable?** Yes, with the authorial remedies,
  and there is no "pin the footprint to epoch *i*" option.
  On a region that grows from one line to a five-item list,
  `align: bottom` turns the gap into spacing above the line,
  and a given `height` clips the larger epochs without any sign,
  which is all a pin option would do.
  `align` defaults to `top` rather than `top + left`,
  because a horizontal component overrides an inherited alignment (see *Findings*).

- **Does `layout(size => ..)` give a region the right width?** In a container whose width does
  not depend on its content, yes.
  In a container that takes the width of its content, `layout` hands over the whole body width,
  and the region cannot detect this.
  That is a documented restriction with `width:` as the remedy (see *Findings*).

- **Do implicit regions behave acceptably inside cetz canvases and math?** Yes.
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
  cannot.

- **Where does a tag's initial state live: the body or the timeline?** The timeline,
  inferred from the first operation that addresses each part of the tag's state (see *Tags*).
  The alternative declared both at the tag site, as `hidden:` and `removed:` arguments of `tag`.
  Those arguments made an author keep two places in sync for one fact.
  Nothing can usefully start hidden without a `reveal` somewhere,
  and nothing can usefully start removed without a `reset`,
  so the timeline already carries the information,
  and an argument would repeat it once per site of the name.
  The inference was checked against every tag site in the demo decks, the documentation and
  the test documents, and it reproduced the state that each argument declared.
  A `reset` that undoes an `apply` or a `replace` rather than a `remove` is unaffected,
  because the first structural operation on such a name is the `apply` or the `replace`.
  The inference also makes state 0 an ordinary state for the resolver,
  so no display state is read at a tag site at all.

  The cost is accepted rather than mitigated.
  `reveal` and `reset` are not pure undos,
  so a `reveal` on a name that nothing hid changes the initial state.
  Animo cannot diagnose this mistake, because every timeline yields a valid answer,
  so the mistake surfaces as an element missing from the initial state.
  This is the one place where Animo guesses instead of refusing.
  It is accepted because the refusals elsewhere are about what an author cannot have meant,
  while here every reading is meant by somebody.
  Shortening the arguments with exported `htag` and `rtag` partials was rejected as well,
  because it leaves the two places to keep in sync.

- **Can a tag over raw cetz draw commands be made to work?** No,
  and Animo refuses it rather than ignoring it.
  A draw command is an array of closures built where it is written, a canvas
  body cannot hold content at all, and a tag reaches its plan through a marker element and a
  show rule, so there is nothing in the stream for the mechanism to attach to
  (see *Findings*).
  No other channel exists either.
  A `state` cannot vary inside `measure`,
  so varying the array per epoch would mean evaluating the block that built it once per epoch.
  That is the `s => ([body], s)` threading that this document rejects below,
  and it is how `sanor` reaches the same case,
  because the body of a `sanor` slide is a function that is evaluated once per subslide.
  Animo lays one content value out once per epoch instead,
  and a show rule reaches content where evaluation reaches values.
  What remains for the author is a canvas written as a function of what it draws and tagged as a
  whole, which changes the geometry at the granularity of the canvas,
  and a `content()` element for anything that has to animate.
  A canvas body evaluated per epoch would recover the per-object granularity,
  which is left for a later release.

- **Is the per-slide plan published as a state or passed down through a show rule?** Passed
  down, as a view, through a marker element and a show rule over the slide body.
  A state cannot carry anything that has to vary inside `measure`,
  which is what a region's footprint measurement needs,
  and no amount of care with document order fixes that (see *Scoping* and *Findings*).

### Primitives and the Timeline

- **Is `sub` the right structure?** Yes. A code block of `sub(...)` calls joins into a
  list of subslides, and `sub` takes `handout:`, `wait:` and `hold:` as keywords.
  Without a context object, the primitives are free functions returning plain data,
  which is easier to inspect, test and extend than methods on a context object.

- **Must the syntax become heavier (body as a function)?** No.
  `sanor` threads a mutable context through the body (`s => ([body], s)`)
  because it accumulates actions while the body is evaluated.
  Animo passes the plan as an argument instead, so the body stays an ordinary content block,
  even though tags and regions *read* that plan while the body is laid out.
  That read is a `context` read rather than a threaded accumulator.

- **Is a context object `c` needed?** No.
  In `sanor`, `c` provides two things, and Animo obtains both otherwise.
  Scoping is handled by the slide container in HTML and by the view on paper,
  and a namespace for the primitives is handled by the cetz-style block-scoped import.
  Without `c`, `tag` is also usable in any context,
  including inside `context` blocks and third-party packages.

- **How are primitives named without shadowing the built-ins?** Following cetz,
  the primitives are imported *inside* the animation block (`import anim: *`).
  The import is scoped to that block, so `move`, `scale` and `hide` keep their natural names
  there while remaining the typst built-ins everywhere else,
  including in the slide body, where authors legitimately use `#move`, `#scale` and `#hide`.
  `region`, `tag` and `slide` are body-level names and are imported at the top level.

- **Can the timeline be placed after the body?** Technically yes,
  with a marker at the end of the body that `query` collects,
  but it costs extra introspection passes and makes the plan discovered rather than passed.
  The body's layout depends on the plan,
  so the plan must be known before the body is laid out,
  and the timeline stays a named argument.

- **Where does time-dependent content live: the timeline or the body?** In the timeline, as
  `replace(tag, body)`.
  The alternative declares several content values at the tag site
  and selects among them from the timeline, in the style of `sanor`'s named cases.
  It is expressible under the measuring mechanism of *States and Epochs*,
  so feasibility does not decide it.
  The interaction with duplicate tags decides it,
  and that interaction matters most for the morph.

  - Every site that shares a tag name receives the **same** replacement content,
    so the tags inside it, their multiplicities and their document order match automatically
    between the outgoing and the incoming rendering.
    That is exactly the precondition that the morph's pairing rule needs.
    With variants per site, two sites named `eq` could show different variants in the same
    epoch, so the two renderings could hold different sets of tags,
    and the pairing would become ambiguous in precisely the case that morphing exists for.
  - Variants impose an **arity agreement** across same-named sites:
    every site named `x` must offer the variant that the timeline asks for.
    `sanor` enforces its equivalent by panicking in `resolve-case`.
    `replace` has no such failure mode, because it hands the same content to all sites.
  - With `replace`, the timeline stays a complete account of every content state,
    while a call such as `switch("eq", 2)` means nothing without looking up the body.
  - `apply`, `remove` and `reset` cannot move into the body anyway,
    so variants would split time-dependent content across two places rather than unify it.

  The argument for the other side is real.
  With the content in the timeline, reading the body alone does not tell how tall a region will
  be, since the content that determines its footprint is declared elsewhere.
  That is a cost to legibility rather than to correctness,
  and the pairing property above outweighs it.
  If per-site content is ever genuinely wanted, the answer is distinct tag names, not variants.

- **How much structure does `apply` need?** `apply(tag, ..fns)` with content-to-content
  functions only.
  `sanor`'s richer `case()`/`object()` machinery exists to cache object state across
  subslides.
  Animo has no such state, because its plan is resolved to per-epoch content states in one pass.
  Named style properties would also require guessing which `set` rule a property
  belongs to, which Animo cannot do without inspecting content.

- **Can `hide` and `remove` be one primitive, with the reflow inferred?** No,
  and the obstacle is the order in which a slide is built rather than a judgement about the API.
  The two differ only inside an explicit region,
  so the inference would have to read whether the tag sits in one.
  Where a tag sits is a fact known only after layout,
  while the plan is resolved *before* the body is laid out,
  because the body's layout depends on its epochs.
  Nothing in the timeline can stand in for that fact, because the resolver never sees the body.
  Both ways around this cost more than the problem.
  Making the merged primitive always structural puts a fresh epoch behind the most common
  animation in a deck, which roughly doubles the renderings and the page weight of an
  ordinary slide.
  Making it always continuous drops `remove`, which is the primitive that regions made
  meaningful.

  A second reason holds even if the order of building ever changes.
  `hide` sets the display state and `remove` the content state,
  and the two compose independently by design (see *Animation Primitives*),
  so a tag may be hidden and removed at once, and `reveal` and `reset` undo different things.
  One name covering both would make `hide(reflow: true)` followed by `reveal()` a near-no-op
  that reads like an undo.

- **Should there be a `once` primitive?** No, and it is dropped rather than deferred.
  The idea comes from `sanor`: make something true for exactly one state,
  by revealing and hiding it again, or by applying a wrapper and dropping it.
  It is not hard to resolve, because the resolver is a forward pass
  and could write the undo into the next state.
  It is ruled out because no single meaning exists.
  Reveal-then-hide and reset-then-remove are both "once",
  and nothing can choose between them without an argument.
  An `apply`-then-drop form is a third meaning.
  It needs identity in the wrapper list so that only the wrapper it added is dropped,
  and it costs two epochs where the display form costs none.
  Each of these forms also needs a rule for a `once` in the last `sub`,
  which has no next state to undo it in.
  All this would take a cluster of optional arguments,
  standing in for two lines that an author can already write,
  `sub(reveal("x"))` and `sub(hide("x"))`, which say exactly which meaning was wanted.

- **How does `move` say where something goes?** The same two ways `pan` does,
  and for the same reason: `x`/`y` place, `dx`/`dy` shift, `relto` names another tag to place
  against.
  A `move` that could only shift would make "put this label where that node is" a computation
  by hand from a layout the author cannot see,
  and the result would stop being right the moment the slide was edited.
  Sharing the vocabulary with `pan` costs nothing,
  because the resolver already keeps a pan as an anchor and an offset per axis,
  and the runtime already measures a tag's anchor for `relto`.
  `move` differs in only one term, which subtracts the anchor of the moved tag.

- **Does a scale factor multiply into what is there, or set it?** It sets it.
  A multiplied factor cannot be read in isolation.
  `scale("a", f: 2)` in the seventh `sub` would mean nothing until every earlier `scale` on
  `a` had been found and multiplied,
  and returning an element to its unscaled size would mean writing a reciprocal
  that changes whenever an earlier `sub` does.
  Setting makes `scale("a", f: 1)` restore the element whatever came before,
  and makes the primitive agree with `move`, whose absolute form is likewise idempotent.
  Successive growth is a product that an author can write once.

- **About which point does a `scale` grow a tag?** About the centre of the box typst laid out,
  in every output type, and from the start of that box on an axis a `move` placed.
  Typst's `scale` grows its body about the centre of the box on paper unless its `origin` says
  otherwise, and it offers no way to grow about the centre of the ink.
  The alternative was to grow about the centre of the ink in the browser,
  with `transform-box: fill-box`, and to document that the output types differ.
  The output types then disagree wherever the ink does not fill the box.
  A list in a filling block grows about the middle of its text in the browser
  and about the middle of the slide on paper,
  and a tag around a moved tag grows about a point that follows the move.
  Firefox also resolves `fill-box` without the `translate` typst writes on a path,
  so its centre can lie outside the ink altogether (see *Findings*).
  The handout would then not show the slide the audience saw.
  The browser has no other access to the box typst laid out,
  so the HTML target places a zero-size marker labelled `animo-corner` at the far corner of the
  box of every slot, beside the slot.
  The runtime then writes `transform-box: view-box` with a `transform-origin` at half the
  translate of that marker, which is a point of the same user space as the slot's box.

  A tag that is both moved and scaled grows from its anchor on the placed axes,
  so that it lands its scaled corner on the target.
  With the centre on every axis, the author would have to add half the growth as a shift.
  Growing every tag from its anchor would land a placed tag as well,
  but would make an emphasis in place grow to the right and down, which is the more common case.
  Making the target of a `relto` its scaled corner as well was considered and left out,
  because the anchor of a tag ignores its display state for the reasons under *Animation
  Primitives*.

- **Do the two resolutions of `pan(relto:)` agree?** Yes, to within the rounding of the
  measurement, once both read the same point.
  Over ten kinds of tag site (placed, inline phrase, inline box, block, centred figure, math,
  heading text, grid cell, list item, a tag inside a tag), at windows 1280 and 640 pixels wide,
  the browser's pan differs from typst's by at most 0.001 pt in chromium and 0.005 pt in
  firefox.
  Reading the position that typst reports for the tag does not agree,
  because that position is a box height too low for every tag on a line.
  The agreement therefore comes neither from a tolerance nor from making one output type
  authoritative.
  `relto` promises the corner of the tag's outer slot,
  and each output type is built to read exactly that (see *Architecture*).

  **And do they agree about a `move`, which reads two anchors and subtracts them?** Yes,
  to at most 0.0005 pt over the same ten kinds of site, at the same two window widths,
  in both engines.
  The figure is smaller than the one above because it is a different measurement,
  not because the mechanism is better.
  Here the `translate` that the runtime writes is read in the user units of the frame,
  while a pan is read off two boxes on the page.
  The 0.005 pt is therefore the error of reading a rendered pan,
  and 0.0005 pt is the difference between the two resolutions themselves.

### The Initial State, Handouts and Numbering

- **Where does a slide say what happens to its initial state?** In `init(..)`,
  the first call of its timeline, which takes the transition into the slide, its `duration:`,
  the `wait:` and `hold:` around state 0 and its `handout:` flag.
  The arguments of `slide` then say what the slide is,
  namely its canvas, its layers and whether it is counted,
  and the timeline says when anything happens to the slide,
  which is the separation the package is built on.
  `init` adds no state, so it keeps every subslide index,
  and it takes the keywords of `sub` with the meaning they have there,
  so the initial state is described in the same way as every other state.
  `init` is a separate call rather than a keyword of the first `sub`,
  because a slide without `sub` has an initial state too.
  A timeline holds `init` at most once and before its first `sub`,
  so its position carries no meaning.

  Two alternatives were rejected.
  A leading `sub` that carries the flags and nothing else does not describe the initial state,
  but adds a second state with the same pixels.
  That shifts every subslide index by one,
  and the leading `sub` has to be written `sub(wait: 0, handout: true)`
  to avoid a presenter click that changes nothing.
  Slide arguments `transition:`, `wait:`, `hold:` and `handout:`
  would mix what and when in the slide's signature,
  and would put the transition of the slide in a different call from the transitions of its
  regions.

- **Does the handout show intermediate content?** Only where the timeline says so.
  One page per epoch was considered and rejected,
  because it makes the page count of a handout depend on an implementation concept (epochs)
  rather than on an authorial decision,
  and it silently inflates handouts for slides that merely restyle something.

  A three-valued flag is used rather than a boolean that defaults to `false`
  with the final state added on top.
  With such a boolean, the final state would be a rule written somewhere else,
  and there would be no way to say that a slide's last state is a punchline
  the audience should not read ahead.
  With `auto`, the flag is the whole answer, the default costs nothing,
  and every page of the handout is one that a state asked for.

  The flag is a **keyword argument of `sub` and `init`**,
  not a free-standing `handout()` call between `sub` calls.
  A marker whose meaning depends on its position in the block is harder to read and to validate
  than a keyword on the state it belongs to.
  A keyword also keeps one more name out of the top-level namespace,
  and it keeps a timeline block down to `sub` calls and at most one `init` before them,
  which is what lets the timeline refuse anything else
  (see the `import *` footgun under *Findings*).
  The same argument puts `wait:` and `hold:` on `sub` and `init`.

- **What does a handout page of a panned slide show?** The viewport of its state,
  exactly as the presentation shows it, with no `#slide` argument.
  The alternative was a page that shows the whole canvas scaled to fit.
  That suits a deck that pans,
  but not a slide whose canvas is merely a little larger than its viewport.
  `sub(handout: true)` already keeps any view that a later pan leaves,
  and the manual says plainly that the handout does not show the canvas.

- **How is a slide numbered, and can a subslide be?** Both, with `slide-number()`,
  `slide-count()` and `per-subslide(f)`, and the subslide number works by rendering every
  value rather than by substituting one.
  One rendering in the HTML presentation covers a run of states,
  so a number chosen when that rendering is laid out is one number for all of them,
  and laying out one rendering per state would destroy the cost model.
  Substituting a value in the browser does not work either.
  Typst emits glyphs as `<use>` references into the `<defs>` of a frame,
  so a runtime that wrote a number would be rewriting glyph references by their hashed
  identifiers.

  What works needs no new mechanism.
  Typst renders **every** value and the browser chooses which one is shown,
  which is what an epoch stack already does.
  A number is therefore a subslide stack,
  and nothing about a number travels in the plan.
  Building the same stack by hand out of tags and `reveal`/`hide`,
  which an author could already write, doubled both the plan and the compile time,
  while a reserved label costs a few percent (see `docs/performance.md`).

  A callback rather than a `subslidenum()` makes a progress indicator possible,
  because in HTML there is no integer at layout time to compute a bar's width from,
  only a rendering per state.
  One name in the manual therefore covers a number, a "3 of 6", a row of dots and a bar,
  and the deck-wide pair `step` and `steps` lets a bar span the talk.

  Numbering epochs instead was rejected.
  It would cost nothing, because a rendering knows its epoch,
  but it would not serve the purpose of a number,
  which is to let someone in the audience ask about a particular moment of a talk,
  and to let the speaker find that moment again.
  An epoch number does not advance on a continuous step,
  so it is constant on the ordinary slide that only reveals things.
  It would make `hide` versus `remove` visible to the audience,
  which is the objection that keeps epochs out of the handout.
  It would also stand beside the state in the URL fragment as a second numbering system.
  Nothing named `epoch` is in the public API.

- **Why are two of the keys of the subslide info called `step` and `steps`?** Because a progress
  indicator is read as how far through the talk the presenter is, and that is what those two
  numbers are written for.
  Everywhere else in Animo a **step** is the move from one state to the next,
  so the *n*-th state of a deck is reached by *n-1* steps, and `steps` counts states rather
  than steps.
  These two keys are the one place where the word for the presenter's action names what the
  presenter arrives at.
  The alternative was `subslide` and `subslides`, which says the same thing and reads worse in
  the expression a progress bar is written as.

- **Why is the `handout:` flag a key of the subslide info rather than a function
  like `slide-number()`?** Because the flag differs between the states of one slide,
  it has the problem that `per-subslide` solves:
  one rendering in the HTML presentation covers a run of states,
  and a value read when that rendering is laid out would be one value for all of them.
  The dictionary is called the *subslide info* rather than the *subslide numbers*,
  because it holds the flag beside the numbers.

- **What does `output-type()` return?** One of `"html"`, `"presentation"` and `"handout"`.
  These are the strings a deck is already compiled with: `target()` returns `"html"`, and the
  two paged modes are the values of `--input animo=`.
  The function is named after the output types that this document and the manual describe.
  It is a context function, as `slide-number()` is, because it reads `target()` and a state.

### Gaps, Delays and Durations

- **Where is the timing of a transition stated, and what is a hard cut?** On the call that
  causes the change, and a hard cut is a duration of zero.
  A structural primitive states the `delay:` and `duration:` of the transition of its region,
  just as a continuous primitive states the `delay:` and `duration:` of its operation,
  so one `sub` times all its operations in the same way.
  `init` states the `duration:` of the transition into the slide, because no primitive
  causes that change, and `wait:` takes the place of a delay there.
  A transition is then only what the crossing looks like,
  and a transition never receives a number it would have to refuse.
  A cut is the crossing that takes no time, so `duration: 0` with any transition is a cut,
  which the runtime handles as one code path.
  A transition named `cut` would have been a transition that refused a duration.
  It follows that a deck's durations are defaults that a stated `duration:` overrides,
  also when the default is zero, since otherwise a deck of hard cuts could not push one slide in.
  It also follows that reduced motion needs a separate property, `--animo-motion`,
  because zeroing a default does not stop a stated duration.
  A per-slide easing was dropped together with the dictionary form of a transition,
  because a primitive states no easing.
  An easing on every call is left for when a deck needs it.

- **Why do `wait:` and `hold:` both exist?** Because each is the natural spelling of a
  different intent, and the two fail in opposite directions when a timeline is edited
  (see *Timing*).
  `wait:` alone looked sufficient at first,
  on the grounds that a "hold" keyword would need two names to cover a slide's first and last
  states, and that `wait:` alone covers every gap.
  Neither ground holds.
  `init(hold: ..)` times state 0, every later state is a `sub` that carries its `hold:`,
  and the last state of a slide with no `sub` at all *is* state 0, so one keyword covers both.
  `init(wait: ..)` on the first slide of a deck does nothing,
  because a gap is read when its state is entered from a predecessor,
  and state 0 of the first slide has none.
  The runtime needed no change for the second keyword,
  because the plan carries both numbers per state
  and the runtime reads whichever of the two was written.

- **Why does one gap take one number?** Because a gap elapses once,
  so there is nothing for a precedence rule to pick between.
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

- **Where does a backward step land, and what does the clock do then?** On the nearest earlier
  state at which the deck rests, with the clock travelling backwards (see *Timing*).
  Three alternatives were rejected.

  - A backward step that stopped the clock would leave the presenter on a state that the
    audience saw only in passing, one press per join.
  - A minimum gap below which a backward step also walks on would be a magic number.
    Zero is what an author types to say that a state is not a resting point,
    while a tiny number says the opposite just as deliberately.
  - A backward step that armed the gap it had just come over would carry the deck forward
    again, and that gap can be zero.

  The cost of the travelling clock is that a deck which times every gap travels back to its
  first state.
  That is accepted, because such a deck plays itself forward to its last state as readily,
  and `Space` stops it either way.

- **Does autoplay want a pause key?** Yes, on `Space`, and the pause does not survive a reload.
  A forward step that clears the pending timer serves a presenter who wants to run ahead,
  but not one who wants to stop and take a question,
  nor the reader who watches a deck that plays itself and wants to stop it as a video is stopped.
  `Space` is a forward key on a deck without a clock,
  so the key that every presentation remote sends keeps its meaning there.
  The pause stops the motion in flight as well as the clock,
  because a reader who presses a pause key wants to keep the picture they are looking at.
  Leaving the pause out was rejected, because it serves the presenter and not the reader.
  Putting the pause in the fragment was rejected,
  because the fragment would then be something other than a position,
  and a shared link could then say that a deck is stopped.

- **Why does a backward step mirror its schedule rather than replay it?** Because a replayed
  schedule lets the operation that arrived first leave first,
  so a build of three lines staggered by `delay:` comes apart in the order it was built up,
  and the composition passes through pictures that the forward step never showed.
  Mirroring each operation about the length of its step makes the two directions one motion
  seen from two ends.
  It costs the plan up to two numbers per timed step,
  because the browser cannot compute the length of a step from the operations it receives
  when an operation states no timing.

- **Does an operation get a separate duration, and in what unit?** Yes, `duration:`,
  beside `delay:` on every primitive, defaulting to `auto`, and in seconds.
  The name is `duration:` rather than `time:`, because it sits beside `delay:`,
  where `time:` reads as a moment rather than as a length,
  and because it is the quantity `--animo-primitive-duration` already names.
  The unit is seconds rather than a multiple of `--animo-primitive-duration`,
  so that two numbers on one call mean the same thing by the same number.
  Reduced motion still takes precedence,
  because a reader who asked for no motion should not have to ask a second time.
  The default is `auto` rather than a number,
  so that "unset" and "as long as the `primitive-duration:` of the deck" stay distinguishable,
  which a change of the deck's tempo needs to reach only the operations that stated nothing.

- **May an operation's duration run past its step?** Yes, and the epoch boundary stretches
  with it (see *Timing*).
  Clamping a structural duration to its step and refusing one that outlives it were the
  alternatives.
  Both can only be defined against the gap that follows the step, and a click has no length.
  The situation they would prevent is also reachable without a long duration,
  through a short gap or a presenter who presses twice,
  with numerically the same result.
  The overlap therefore needed an answer in the runtime, which rule 2 of *Architecture* states.

- **Is the Web Animations API the right driver?** Yes.
  A step writes the display state as inline style and animates from what the element was
  showing to that state, so the inline style is the state
  and the animation is only how the element gets there.
  A property that only the way there needs, such as the blend and the isolation of a
  transition, is held by the animation as a keyframe with the same value at both ends,
  and is never written as inline style.
  Reversible stepping, an interrupted step that continues from where it is,
  and a deep link that needs no transition to suppress all follow without extra code,
  and CSS transitions handle none of the three well.
  The API also makes a test reproducible in the middle of a step,
  because the test pauses the animation and sets a `currentTime` instead of racing it.

- **How does an author state the deck's tempo?** As arguments of the deck's show rule,
  which the deck writes into the `:root` block of its stylesheet (see *Timing*).
  The alternative was to let the author write that CSS,
  which fails on two counts.
  Writing a `<style>` element from typst means calling `html.elem`,
  guarded by a `target()` test because the paged outputs have no `html` module,
  which is markup in a deck's source and a guard an author has to know about.
  Such a stylesheet also lands after the stylesheet of Animo,
  where it would outrank the reduced-motion query without the `!important` the query carries.
  An easing is checked against a list of five names rather than passed through,
  because the list is what a reference page can state.
  The principle is narrow.
  Every setting that the runtime of Animo reads is stated in typst,
  which is not a promise to expose the page's styling,
  and `html.elem` stays available for what Animo does not cover.

### The HTML Presentation

- **Where do the blend and the isolation of a transition go?** On the renderings of an epoch
  stack and on the group that holds them, and only while a transition runs.
  A stack holds nothing but its region, so the outgoing rendering paints nowhere outside the
  region, and nothing has to scope it there.
  The isolation keeps the sum of the two halves off the ink under the region
  (see *Findings*).
  It is written as `isolation`, because forming the group is all that property declares.
  `opacity: 0.999` forms the group too, by letting a thousandth of the backdrop through,
  which rounds to the same pixels.
  `filter: opacity(1)` forms no group in webkit and breaks the sum in firefox.
  Both apply only while a transition runs,
  because a group that blends or isolates is drawn through a layer that changes glyph edges
  (see *Findings*).
  A difference on every still slide weighs more than one that lasts a frame at either end of
  a transition, and in chromium every frame of a transition is drawn differently anyway.
  The slides make the opposite choice and keep `plus-lighter` at rest,
  so that a slide rasterises the same whether or not it is in a transition.
  One slide blended against the transparent backdrop of the stage is that slide to within
  rounding (see *Findings*).

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
  boundary is a named, swappable one.
  The authoring advice is to name `morph()` on the primitive when content shifts,
  and otherwise to put a region around what is replaced wholesale
  and to keep what merely shifts out of it.

- **Where are `transform-box` and `transform-origin` written?** By the runtime, on the slot it
  is about to transform, and never as a rule in the stylesheet.
  The alternative was a single rule, `.animo-canvas [data-typst-label] > g`,
  which is the selector through which the continuous properties themselves are written.
  The two declarations re-anchor the `transform` attribute of the element
  as much as the properties beside them (see *Findings*),
  and a labelled group is not always a tag site.
  A region's footprint carries a label too, because the runtime addresses it,
  and its children are the author's content rather than a slot,
  so the rule would reach typst's glyph runs and move each of them by its fill box.
  Every candidate selector that excludes a region's children is a guess about the shape of
  content Animo does not build:
  `:only-child` fails on a region holding one group,
  and `:not([transform])` would exclude a real slot the moment an inline footprint offsets one.
  Writing the two declarations where the transform is written needs no such guess,
  because the element is the one the runtime already holds.

- **How do CSS-animated typst SVG groups look in motion?** Well enough that nothing about the
  defaults changes (see *Findings*).
  A scaled glyph is drawn afresh at the scale it ends up at rather than stretched,
  so text stays as sharp at 200% as at its unscaled size,
  and strokes scale geometrically with it.
  That is what a figure needs, and it makes `scale` usable on text.
  A value under a running animation rasterises bit for bit as the same value in a style
  declaration, so the hand-off at the end of a step is invisible.
  An author still has to know what a `scale` does.
  It scales about the centre of the element and nothing reflows,
  so a doubled paragraph overlaps its neighbours.

- **What happens between two slides?** A transition, which may take no time.
  In both directions, the boundary takes the `init` of the slide with the higher number,
  which is the slide a forward step enters,
  so stepping back over a boundary undoes exactly what stepping forward over it did,
  and the setting is written on the slide it is about,
  rather than on the slide that happens to precede it in the file.
  The crossfade uses the mechanism that the epoch transition already proved,
  which is `plus-lighter` on the two containers inside an isolated stacking context,
  and which keeps two opaque backgrounds from dipping halfway through.
  Two slides are laid out only while they cross.
  Laying every slide out for the whole session doubled the first paint of a deck of sixty
  slides in chromium, and the first paint is paid again at every reload by `typst watch`.

  A transition is a function of the `anim` module, as in `push(direction: ttb)`, rather than a
  name per variant or a dictionary.
  A parameter is then a named argument, so a misspelt one is refused by typst at the call that
  wrote it, a misspelt transition is an unknown variable, and an editor shows each transition's
  parameters and their defaults.
  The functions live in the `anim` module,
  where new transitions add no names to the namespace of the slide body.
  A direction is a typst direction, `ltr`, `rtl`, `ttb` or `btt`,
  which is the value that the pdfpc helpers of other typst presentation packages take for a
  slide transition.

- **Where is the transition of an epoch boundary named?** On the structural operation, as
  `transition:`, beside its `delay:` and `duration:`.
  What crosses a boundary is a region, and two regions of one boundary can want two
  transitions, such as a morph for an equation whose terms move and a crossfade for the caption
  replaced beside it.
  An argument of `sub` would make that cost two states.
  A region already takes its timing from its operations, and its transition follows the same
  rule and the same refusal.
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
     The key is what the element draws, without its place and without its color.

     - A glyph is a `<use>`, and its key is the `href`. Typst names a glyph by a hash of its
       outline at its size, and the fill is an attribute of the `<use>` and not part of the
       hash, so equal names mean equal shapes whatever their color (see *Findings*).
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

     The colors stay out of every key, `fill` and `stroke` alike, and so does a gradient.
     Two copies whose colors differ sum to the interpolation of the two colors under the
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
     webkit does not animate it, so the runtime tests `CSS.supports` once and webkit
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
  Typst draws a run of text as a group of glyphs,
  so a run whose glyphs all travel the same distance is translated as one group,
  with one animation rather than one per glyph.
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
  correct. The bound is 400 differences (see `docs/performance.md` for what it costs).

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
  and `set text(lang: ..)`, as for any typst document, so nothing is stated twice.
  Typst writes neither into a head that a package builds, so the deck's show rule reads them in
  a context and writes the `<title>`, the `lang` and the `<meta>` elements typst would write
  (see *Findings*).

- **What may a layer hold, and where does it belong?** A color or arbitrary content,
  and the layer belongs to the viewport rather than to the canvas.
  A content background costs nothing beyond a color, because each layer is already a frame
  beside the canvas, and `overlay` is the same construct one layer up.
  A viewport-bound layer keeps a logo in the same place on screen
  instead of letting it travel with the canvas,
  keeps a full-bleed image from silently enlarging the automatic canvas,
  and keeps a color layer and a content layer behaving identically under a `pan`.
  A layer that pans with the canvas is left for a later release.
  It would be a different construct rather than a flag on this one,
  because a color and a content layer would otherwise behave differently under a `pan`.
  Tags and regions are refused in a layer rather than ignored,
  because a silent no-op hides the cause of a mistake.

### The Canvas

- **Does every slide compute the union of its placements?** No, only a slide whose timeline
  pans.
  The union is the one part of laying out a slide whose cost grows with the number of `#place`
  calls in the body, which becomes noticeable in a deck that draws data as thousands of small
  placed marks (see `docs/performance.md` for the numbers).
  Only `pan` reads the canvas.
  The viewport clips in every output type, and an offset given as a ratio is refused,
  so no length in a timeline is a fraction of the canvas either.
  A slide with no `pan` in its timeline is therefore drawn identically whatever canvas it is
  given, so skipping the union saves time without changing any output.
  An author who does pan and wants the cost gone states `canvas:`,
  which skips the recording as well.

- **How exact is the automatic canvas?** Approximate, with its error documented in both
  directions rather than reduced (see *Canvas and Viewport*).
  The alternative was to count only the placements that Animo can attribute to the slide body,
  but no mechanism supports that.
  `layout(size => ..)` inside the rule reports the container exactly,
  but breaks the paragraph that the placement sits in.
  A nesting depth kept in a state reads zero for a placement inside another placement,
  which is how real decks are written,
  and would read every placement inside a tag as nested, since a tag site is a box
  (see *Findings*).

### Costs

- **What does a realistic deck cost to compile?** About twice the same content laid out as
  plain typst pages, for a deck without structural steps,
  and the live preview recompiles a deck in a fraction of a cold compile,
  so Animo is fast enough to author with.
  `docs/performance.md` has the measured numbers and says where they come from.
  The most expensive construct is a cetz canvas inside a region,
  because the region lays the canvas out afresh for every epoch.
  That cost follows from letting a figure change size, as the region design predicts,
  so it asks for no change of the design.
  The author keeps such a canvas outside a region to keep it rigid,
  or gives the region a `height`, which skips the measuring.

- **Is gzip enough for the page weight, or is the hoisting of shared definitions needed?** Gzip
  is enough for now.
  Gzip compresses a deck by about a factor of five.
  Gzip does not recover the definitions that typst repeats in every frame,
  because deflate's window is 32 KiB and one frame is larger,
  so hoisting would be worth a further factor of about two on top of it (see *Findings*).
  Hoisting the shared definitions into one document-level `<svg>` is sound in the browser
  and out of reach from typst 0.15.0, because a package never holds the markup that a frame
  became.
  The reachable part is one frame per slide,
  which lets typst's deduplicator share the definitions of a slide's epochs,
  and *Architecture* specifies it.

### Naming and Testing

- **Is the name appropriate?** Yes.
  *Animo* is at once the first person singular of *animare*, "I bring to life", and the
  ablative of *animus*, "with mind, with intent",
  which states the package's position in a single word:
  an animation earns its place on a slide when it is put there deliberately,
  and so does everything else on that slide.
  Anything added without a reason competes with the speaker for the audience's attention.

- **How is Animo tested?** In three tiers under one runner, with the weight on the cheapest:
  plan resolution compiled without export, rasterised comparisons of the paged outputs,
  and checks of the HTML presentation in headless browsers.
  [docs/testing.md](../docs/testing.md) describes the tiers, the engines and the policy on
  stored reference images,
  and [docs/probes.md](../docs/probes.md) describes the probes that guard *Findings*.
  The tests assert numbers rather than compare pixels against stored images wherever they can,
  because stored images are brittle across typst versions.
  The two invariants that the region design rests on are comparisons within one page load,
  so they need no stored images either.
  `tytanic` is the ecosystem convention for testing typst packages,
  and was rejected only because it cannot see the HTML target at all.

## Open Questions

These questions are deliberately undecided.

- **Should a morph ever scale?** A morph translates only, and a glyph that changes size is not
  matched, so its size change is carried by the crossfade.
  Scaling would let a heading that changes size morph,
  but a non-uniform `scale` distorts glyph strokes, which suggests leaving scaling for figures.
  For a shape, the resize answers the question without scaling the stroke.
  The question stays open for glyphs and images, which a resize cannot reach,
  because a glyph of another size is another outline.
  This has to be seen in motion before it is decided.

- **Should a group of shapes that travel one distance move as one animation**, as the
  glyphs of a run do?
  A cetz drawing that moves as a whole is better put in a tag, which already moves as one.
  A plot of 1000 marks whose axis range changes gives each mark a separate route,
  which makes the key press and the frames of the motion measurably slower
  (see `docs/performance.md`).

- **Does the non-blocking job that tests the newest typst release yield a useful signal**,
  or only noise?

## Development Infrastructure

This section is not part of the feature design.
It is recorded here because much of the infrastructure is constrained by the design,
and because two parts of it impose requirements back on the package:
the live preview needs the runtime's state to be addressable in the URL,
and Universe needs the version number to be correct in every example.

The infrastructure is described where a contributor meets it,
and this section keeps only what the design decides.

| Subject                                                | Where it is written up                                                |
| ------------------------------------------------------ | --------------------------------------------------------------------- |
| Environment, the two import paths, version numbers     | [docs/environment.md](../docs/environment.md), `snipwise.md`          |
| The three test tiers, the engines, reference images    | [docs/testing.md](../docs/testing.md)                                 |
| Continuous integration                                 | [docs/testing.md](../docs/testing.md)                                 |
| Probes, and what to do when one fails                  | [docs/probes.md](../docs/probes.md)                                   |
| The live preview loop                                  | [docs/presenting.md](../docs/presenting.md)                           |
| What a deck costs, and where the numbers come from     | [docs/performance.md](../docs/performance.md), `benchmarks/README.md` |
| The public surface, name by name                       | [docs/reference.md](../docs/reference.md)                             |
| Where the specification lives, for a contributor       | [docs/development.md](../docs/development.md)                         |
| The files, controller, events and input of the runtime | [docs/architecture.md](../docs/architecture.md)                       |

### Repository Layout and Manifest

`typst.toml` is the root of everything downstream: the entrypoint, the version,
`compiler = "0.15.0"`, and the `exclude` list that keeps documentation out of the published
archive.

```text
animo/
├── src/          the package itself, entrypoint `src/lib.typ`
├── tests/        pytest: plan assertions, paged rasters, browser checks
├── probes/       one probe per entry in *Findings*
├── demos/        the demo decks the documentation embeds
├── benchmarks/   compile time and page weight
├── docs/         the Zensical site
├── planning/     design documents, including this one
└── tools/        the build and release scripts
```

One rule of the Universe submission guidelines shapes the package itself rather than the release
path: every demo deck and every snippet, including the README, imports `@preview/animo:X.Y.Z`
rather than a relative path, so that a reader can copy any file and compile it.
Keeping those strings correct is `snipwise`'s job.

A submission cannot be withdrawn: publishing a first version commits to the name and to that version
number for good. It does not commit to the API. Animo is not API-stable before 1.0, and
saying so plainly is better than a promise that real use would break anyway, because nobody
knows yet what real use turns up.
A break still has a real cost, because it rewrites decks that already exist.
That cost, and the irreversibility of the submission itself,
are why the last step of the release path stays manual.

### The State the Runtime Has to Expose

`typst watch` serves the HTML and reloads the browser itself (see *Findings*), so Animo ships
nothing for live preview. What it does require is that the runtime keep the current slide and
state in `location.hash` and restore from it on load,
which the testing strategy needs anyway for deep links.
This has two consequences:

- the restore must *snap* to the state rather than animate into it, which is one more argument for
  driving animations through the Web Animations API;
- the hash must be written with `history.replaceState`, or every step leaves a browser
  history entry behind.

Narration audio, should it ever be added, is silent on a restore.
The reload is what makes that rule an everyday case rather than an edge case.

### Task Layer

Everything is a command a contributor can type, and there is no build tool between them.
`pytest`, `pre-commit`, `zensical` and `typst watch` are invoked directly,
and what takes more than one command is a script under `tools/`:

- `tools/build_demos.py` compiles every deck under `demos/` to all three output types and
  writes them into `docs/demos/`, which the site build publishes. This is where "one compile
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

## Comparison with the Packages That Inspired This

- **`sanor`** separates declaration from animation, as Animo does, and its `apply`/`case`
  mechanism is the direct ancestor of Animo's `apply`. It also tags raw cetz draw commands
  (`test/draw.typ` tags a `draw.grid(..)` with `hider: draw.hide`),
  which Animo cannot do for the reason under *Resolved Design Decisions*.
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

## Related Directories

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
| `../stepup-core`, `../stepup-reprep` | the build tool driving those decks, which Animo itself does not use                                                     |
| `../templates`, `../bootstrap`       | repository templates where an Animo-based talk template would eventually land                                           |
| `../snipwise`                        | keeps text snippets in sync across files; copies the version from `typst.toml` into every `@preview/animo:X.Y.Z` string |
| `../stepup-benchmark`                | precedent for tracking compile time and output size across releases                                                     |
