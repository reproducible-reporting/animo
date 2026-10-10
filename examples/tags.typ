// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// A tag marks a part of a slide and names it, so that a timeline can address it.
// The timelines below use a few primitives that later pages of the guide explain,
// with a comment at each to say which page that is.

#import "@preview/animo:0.1.1": *
// The colors, the title slide, the styles and the slide wrapper that the example decks share.
#import "_common.typ": *
#import "@preview/cetz:0.5.2"

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show: example-style

#title-slide("tags.typ")

#slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    white,
    pale,
    angle: 90deg,
  )),
  animation: {
    import anim: *
    // The push lifts the curtain of the title slide.
    init(push(direction: btt))
    sub(reveal("caveat"))
  },
)[
  = Tags

  #text(fill: dark)[*A short claim.*]

  // The first operation on this tag is `reveal`, so the tag starts hidden:
  // laid out, taking its space, and invisible. Nothing at the tag site says so.
  #tag("caveat")[#text(fill: orange)[With a caveat that the timeline reveals.]]

  #explain[
    A tag name is also a label, so a slide keeps its tag names apart from the labels it writes.
  ]
]

#slide(animation: {
  import anim: *
  sub(reveal("hidden"))
  // `reset` is a structural primitive, which Structural Animations explains.
  // As the first content operation on a tag, it makes the tag start removed.
  sub(reset("removed"))
  // The two slots are independent, so this tag starts removed and hidden,
  // and needs both operations to appear.
  sub(reset("both"))
  sub(reveal("both"))
})[
  = Initial State of Tagged Content

  - #explain[Starts hidden:] #tag("hidden")[#text(fill: orange)[*here I am*]]
  - #explain[Starts removed:] #tag("removed")[#text(fill: teal)[*here I am*]]
  - #explain[Starts removed and hidden:] #tag("both")[#text(
      fill: pink,
    )[*here I am*]]
  - #explain[Starts as written:] #tag("plain")[#text(fill: dark)[*here I am*]]

  // A tag whose content changes reserves room for it, which is why the removed one leaves
  // a gap here. Structural Animations explains that box, and Regions how to free it.
  #explain[The timeline decides each initial state, never the tag site.]
]

#let key = text(fill: orange, strong[key])

// One name at several sites is addressed as if it were one element,
// and every site starts in the same state.
#slide(animation: {
  import anim: *
  sub(reveal("key"))
})[
  = One Name, Several Places

  The #tag("key")[#key] opens the door, the #tag("key")[#key] locks it,

  and without the #tag("key")[#key] you stay outside.
]

// The same name on another slide does not interfere.
// This slide has no timeline, so its "key" is visible from the start.
// The tinted background sets the slide apart from the previous one.
#slide(background: orange.lighten(92%))[
  = The Same Name on Another Slide

  The #tag("key")[#key] is visible here.

  #explain[A tag reads the plan of the slide it appears in, and this slide has no timeline.]

  #explain[
    A name that the slide tags nowhere is refused, so a misspelt name in a timeline is
    a compile error rather than an operation that does nothing.
  ]
]

// `move` and `scale` are continuous primitives, which Continuous Animations explains.
// They show the wrapper that `wrap: auto` chose, because a `#box` hugs its body and a
// `#block(width: 100%)` fills its container.
#slide(animation: {
  import anim: *
  sub(scale("inline", f: 1.5), scale("list", f: 1.1))
  sub(scale("inline", f: 1), scale("list", f: 1), move("boxed", dx: 4cm))
})[
  = What a Tag Site Becomes

  #explain[An inline phrase]
  #tag("inline")[#text(fill: orange)[*in a box*]]
  #explain[scales about its centre.]

  #explain[
    A list is block-level, so it fills the width and scales about the centre of the slide.
  ]
  #tag("list")[
    #set text(fill: teal)
    - A first item
    - A second item
  ]

  #explain[A filling block keeps centred content centred.]
  #tag("centred")[#align(center)[#text(fill: pink)[*Centred*]]]

  // A function as `wrap` builds the wrapper, so a frame moves with what it frames.
  #explain[A frame built by `wrap` moves along.]
  #tag("boxed", wrap: box.with(
    inset: 4pt,
    stroke: orange,
  ))[#text(fill: orange)[*Framed*]]
]

#slide(animation: {
  import anim: *
  sub(move("title", dx: 2cm))
})[
  // A tag around the heading would trim its block spacing and shift it by a few points,
  // so the tag goes around the text of the heading instead.
  = #tag("title")[A Heading That Moves]

  #explain[The tag holds the text of the heading, so the heading keeps its spacing.]

  // A wrapper cannot break across lines, so the tag holds the whole paragraph
  // rather than a long stretch in the middle of it.
  #tag("paragraph")[#text(fill: teal)[#lorem(30)]]

  #explain[
    A tagged paragraph wraps as usual inside its block,
    because the wrapper holds all of its lines.
  ]
]

#slide(animation: {
  import anim: *
  sub(reveal("b"))
  sub(scale("b", f: 1.5))
})[
  = Inside Math

  #explain[A tag inside an equation is an ordinary tag site.]

  #show math.equation: set text(fill: dark)
  $ a + #tag("b", text(fill: orange, $b$)) = c $
]

// A figure that is a function of what it draws, so that a variant can replace it.
#let scene(mesh: true) = cetz.canvas({
  import cetz.draw: *
  if mesh {
    grid(
      (-2, -1.5),
      (2, 1.5),
      step: 0.5,
      stroke: gray,
    )
  }
  circle((0, 0), radius: 1, stroke: 2pt + dark, fill: pale)
})

#slide(animation: {
  import anim: *
  sub(move("label", dy: -1cm))
  // `replace` is a structural primitive, which Structural Animations explains.
  // A raw draw command such as `grid(..)` cannot be tagged, so the whole figure is
  // replaced by the variant without the mesh.
  sub(replace("figure")[#scene(mesh: false)])
})[
  = Inside a Cetz Canvas

  #grid(
    columns: (1fr, 1fr),
    align: center + horizon,
    // A cetz `content()` element holds ordinary content, so a tag goes there.
    // A fletcher node label holds ordinary content as well.
    cetz.canvas({
      import cetz.draw: *
      line((0, 0), (4, 0), stroke: 2pt + dark)
      content((4, 0), tag("label")[#text(fill: orange)[*Hi*]], anchor: "west")
    }),
    tag("figure")[#scene()],
  )

  #explain[
    A tag goes on a `content()` element, or around a whole figure,
    because a raw draw command cannot be tagged.
  ]
]

#slide(animation: {
  import anim: *
  sub(hide("note"), move("panel", dy: 1cm))
})[
  = Inside a Grid Cell

  #explain[
    `hide` reaches the text inside a cell but not the fill of the cell,
    while `move` carries the fill of a block that the tag holds.
  ]

  // A tag around a cell that sets a fill is refused, so the tag goes inside the cell.
  // The grid paints the fill outside the group of the tag, so `hide` leaves it standing.
  // A block that the tag holds carries its fill along.
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 0.5cm,
    inset: 0.5cm,
    grid.cell(fill: pale, tag("note")[The fill of this cell stays.]),
    grid.cell(tag("panel", block(
      fill: gradient.linear(pale, orange),
      width: 100%,
      inset: 0.5cm,
    )[This fill moves with the tag.])),
  )
]
