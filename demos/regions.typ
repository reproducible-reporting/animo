// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// Regions, which are areas laid out afresh in every epoch inside a footprint that never
// changes, so that a change of content can push its surroundings around inside them.

#import "@preview/animo:0.1.1": *
// The colors, the title slide, the styles and the slide wrapper that the demo decks share.
#import "_common.typ": *
#import "@preview/cetz:0.5.2"

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show: demo-style

// A region draws nothing itself, so this tinted frame around it shows the footprint.
#let footprint(body, color: dark) = block(
  stroke: (paint: color, thickness: 0.8pt, dash: "dashed"),
  // A pale tint with the hue of the color, because a dark color that is lightened looks gray.
  fill: oklch(96%, 0.025, oklch(color).components().at(2)),
  radius: 2pt,
  inset: 0.2cm,
  body,
)

// A small caption above a figure, in the gray italics of the explanations.
#let caption(body) = explain(text(size: 0.85em, body))

// The same three paragraphs go into both columns of the first slide.
// `mark` draws around each tag, so the bare column can show the box that each tag reserves.
// The fills are set outside the tags, so that a replacement arrives in the same color.
// `wrap: block` gives the claim a container width, so that its replacement wraps inside it.
#let claims(mark) = [
  #mark(text(fill: orange, tag("claim", wrap: block)[*A short claim.*]))

  #mark(text(fill: teal, tag("caveat")[*A caveat that goes away.*]))

  This paragraph comes after both tags.
]

#title-slide("regions.typ", "Regions", "regions/")

#explained-slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    white,
    pale,
    angle: 90deg,
  )),
  notes: (
    [The same three paragraphs, inside a region on the left, and as bare tags on the right.],
    [`remove` frees the space of the caveat in the region, and the paragraph after it moves up.],
    [`replace` lays out a longer claim, which wraps and pushes the paragraph down again.],
  ),
  animation: {
    import anim: *
    // The uncover lifts the curtain of the title slide.
    init(uncover(direction: btt))
    // Each name has a site in both columns, so every primitive changes both columns alike.
    // Outside a region, a tag whose content changes reserves a box for its largest epoch,
    // so the removed caveat leaves a gap there.
    sub(remove("caveat"))
    sub(replace(
      "claim",
    )[*A claim that grew long enough to wrap onto a second line.*])
  },
)[
  = Reflow Inside a Region

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 0.8cm,
    row-gutter: 0.3cm,
    caption[Inside a `region`, typst lays out each epoch afresh.],
    caption[Bare tags, each in a box for its largest epoch.],

    footprint(region(claims(it => it))),
    footprint(claims(block.with(stroke: guide, width: 100%))),
  )

  #v(1fr)

  #explain[
    The tinted frame shows the footprint of the region, which is the same in every state.
    The content after the region therefore never moves.
  ]
]

#explained-slide(
  notes: (
    [Both regions reserve the room of their tallest state, so this short state leaves a gap.],
    [`reset` brings in the paragraph, which fills the footprint of both regions.],
  ),
  animation: {
    import anim: *
    // One name with a site in each region brings in both paragraphs at once.
    sub(reset("late"))
  },
)[
  = Where a Smaller State Sits

  #let late = tag("late")[#text(fill: orange)[
    This paragraph arrives in state 1.
    Both regions reserve its room from the start,
    so the line after them stays where it is.
  ]]

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 0.8cm,
    footprint(region[
      #text(fill: dark)[*`align: top`, the default*]
      #late
    ]),
    footprint(region(align: bottom)[
      #text(fill: dark)[*`align: bottom`*]
      #late
    ]),
  )

  #text(fill: teal)[*This line comes right after both regions.*]

  #v(1fr)

  #explain[
    With `align: bottom`, the gap sits above a short state,
    where it reads as the spacing after the heading.
  ]
]

// The two parts of the next slide, each a title that is always there and a tagged paragraph.
#let first-part = [
  #text(fill: orange)[*The first part*]
  #tag("one")[This paragraph arrives in state 1 and leaves again in state 2.]
]
#let second-part = [
  #text(fill: teal)[*The second part*]
  #tag("two")[This paragraph arrives in state 2, when the first one leaves.]
]

#explained-slide(
  notes: (
    [On the left, each part has a region. On the right, one region holds both parts.],
    [`reset` brings in the first paragraph. On the right, the second title moves down.],
    [The paragraphs swap. On the left, each region changes without moving the other.],
  ),
  animation: {
    import anim: *
    // The two paragraphs are tallest in different epochs, so the merged region reserves the
    // room of one paragraph, and the two separate regions reserve the room of both.
    sub(reset("one"))
    sub(remove("one"), reset("two"))
  },
)[
  = Splitting and Merging Regions

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 0.8cm,
    row-gutter: 0.3cm,
    caption[Two regions, one per part.], caption[One region around both parts.],
    stack(
      spacing: 0.3cm,
      footprint(region(first-part)),
      footprint(region(second-part)),
    ),
    footprint(region[
      #first-part

      #second-part
    ]),
  )

  #v(1fr)

  #explain[
    Separate regions reserve the sum of their tallest states.
    One region around both parts reserves less room, but a change in one part moves the other.
  ]
]

#explained-slide(
  notes: (
    [The measured region reserves room for the long text. The other region is 2cm tall.],
    [The long text fits in the measured region, and is clipped in the region of a given size.],
  ),
  animation: {
    import anim: *
    sub(reset("long"))
  },
)[
  = A Given Size

  #let long = tag("long")[#text(fill: orange)[
    This text arrives in state 1 and needs more room than 2cm.
    #lorem(18)
  ]]

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 0.8cm,
    row-gutter: 0.3cm,
    caption[`region[..]` measures every epoch.],
    caption[`region(height: 2cm)[..]` measures nothing.],

    footprint(region(long)), footprint(region(height: 2cm, long)),
  )

  #v(1fr)

  #explain[
    A region of a given size compiles faster, because it skips the measurement of its epochs.
    It clips by default, so check every subslide for content that is cut off.
  ]
]

#explained-slide(
  notes: (
    [The outer region is named `box`, and holds an inner region.],
    [`reset` brings in a sentence, which reflows only the inner region.],
    [`scale` shrinks the whole outer footprint, because the region has a name.],
    [`move` shifts the footprint, and `hide` makes it invisible half a second later.],
  ),
  animation: {
    import anim: *
    // A change inside the inner region reflows only the inner region.
    sub(reset("inner"))
    // A name makes the footprint a site that the continuous primitives reach.
    sub(scale("box", f: 0.8))
    sub(move("box", dx: 2cm), hide("box", delay: 0.5))
  },
)[
  = Nesting and Names

  // The frame of the outer region is inside the region, so it scales and moves with it.
  #region(name: "box")[
    #footprint[
      #text(fill: dark)[*The outer region, named `box`*]

      #footprint(color: teal, region[
        #text(fill: teal)[*An inner region*]
        #tag(
          "inner",
        )[A sentence that arrives inside the inner region, which reflows alone.]
      ])

      The outer region continues here, and stays where it is.
    ]
  ]

  #v(1fr)

  #explain[
    The timeline can address a region with a name like a tag.
    Regions nest at most three deep.
  ]
]

#explained-slide(
  notes: (
    [Each region is as wide as its container, which is the width it lays out its body at.],
    [`reset` brings in the same sentence in all three regions, which wrap it at three widths.],
  ),
  animation: {
    import anim: *
    sub(reset("late"))
  },
)[
  = Regions in Containers

  #let late = tag("late")[#text(fill: orange)[
    This sentence arrives in state 1 and wraps at the width of its region.
  ]]

  // The placed box sits under the left column, because the region in `#columns(2)` is the
  // tallest and sets the height of the grid.
  #place(dy: 2.2cm, box(width: 5cm, footprint(region[
    #caption[In a placed box with `width: 5cm`.] #late
  ])))

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 0.8cm,
    footprint(region[#caption[In a `1fr` grid column.] #late]),
    columns(2, footprint(region[#caption[In `#columns(2)`.] #late])),
  )

  #v(1fr)

  #explain[
    In an `auto` grid column, a `stack(dir: ltr)` or a bare `#place`,
    a region takes the whole body width unless it is given a `width:`.
  ]
]

// A cetz canvas takes draw commands rather than content, so the region goes around the
// canvas. A change of a tag on a `content()` element redraws the whole figure inside the
// footprint, which is the only way a cetz figure changes size, and the most expensive
// construct in a deck.
#explained-slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    white,
    orange.lighten(85%),
    angle: 90deg,
  )),
  notes: (
    [The label is a tag on a `content()` element of the cetz canvas.],
    [`replace` lays out a larger label, and typst draws the whole figure again.],
  ),
  animation: {
    import anim: *
    sub(replace("label")[#text(
      fill: orange,
      size: 1.6em,
    )[*a much longer label*]])
  },
)[
  = A Region Around a Cetz Canvas

  #footprint(region[
    #align(center)[
      #cetz.canvas({
        import cetz.draw: *
        content(
          (0, 0),
          tag("label")[#text(fill: orange)[*a label*]],
          name: "label",
          frame: "rect",
          padding: 0.2,
          fill: white,
          stroke: orange,
        )
        circle((0, -2.2), radius: 0.3, fill: teal, stroke: none, name: "dot")
        line("label.south", "dot.north", mark: (end: ">"), stroke: dark)
      })
    ]
  ])

  #v(1fr)

  #explain[
    The arrow stays attached to the frame of the label, because the whole figure is drawn again.
    A region around a canvas is the most expensive construct in a deck.
  ]
]
