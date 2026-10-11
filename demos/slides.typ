// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The shape of a deck, the two layers around the body of a slide,
// and the transitions by which a slide is entered.

#import "@preview/animo:0.1.1": *
// The colors and the title slide that several demo decks share.
#import "_common.typ": dark, orange, pale, pink, teal, title-slide

// The show rule is the only place where the shape of the deck is written.
// It also takes `transition:`, the default transition of the deck, which this deck leaves
// at `anim.crossfade()`, so that each slide below names the transition it shows.
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show heading: set block(below: 1em)

// Style inline code
#show raw.where(block: false): it => highlight(
  fill: pale,
  stroke: pale + 0.1cm,
  radius: 0.1cm,
  it,
)

#title-slide("slides.typ", "Slides", "slides/")

// A color as a background is the page fill on paper and a CSS background in the browser.
// The overlay is content, laid out in a box the size of the viewport, so its `#place`
// resolves against the edge of the slide rather than against the margin.
#slide(
  background: dark,
  // The uncover lifts the curtain of the title slide.
  animation: anim.init(anim.uncover(direction: btt)),
  overlay: place(bottom + right, dx: -0.5cm, dy: -0.5cm, text(
    fill: white,
    size: 0.8em,
  )[_An overlay, in the corner of the viewport_]),
)[
  #set text(fill: white)
  #show raw: set text(fill: dark)
  = Slides

  A deck is a show rule and one `#slide` call per slide.

  Everything inside a slide body is plain typst.
]

#slide(
  background: luma(220),
  overlay: place(bottom + right, box(fill: orange, inset: 0.2cm)[overlay]),
)[
  #place(box(fill: white, width: 100%, height: 100%))

  = The Margin

  The `margin` argument insets the body within the slide,
  and moves the origin of the body.

  // The same placement in the body and in the overlay lands in two places,
  // because the body starts at the margin and the overlay at the edge of the viewport.
  #place(bottom + right, box(fill: teal, inset: 0.2cm)[body])

  A `#place(bottom + right)` in the body lands inside the margin,
  while the same placement in the overlay lands on the edge.
]

// Content in the background is clipped to the viewport like the body,
// so a disc that is larger than the slide shows only the part that falls inside it.
#slide(background: {
  place(dx: 11cm, dy: -3cm, circle(radius: 5cm, fill: teal))
  place(dx: -2cm, dy: 6cm, circle(radius: 2.5cm, fill: orange))
})[
  = Content as a Background

  A background that is content is laid out in a box the size of the viewport.

  The viewport clips all three layers alike,
  so the two discs show only their part inside the slide.
]

// A gradient or a tiling is not a color, so it goes into a `rect` of the slide size,
// which is content like any other.
#slide(background: rect(
  width: 100%,
  height: 100%,
  fill: gradient.linear(teal, pink, angle: 30deg),
))[
  = A Gradient
  A `rect` of the slide size takes a gradient as its fill.
]

#slide(background: rect(width: 100%, height: 100%, fill: tiling(
  size: (1cm, 1cm),
  place(dx: -0.05cm, dy: -0.05cm, circle(radius: 0.55cm, fill: luma(220))),
)))[
  = A Tiling
  The same `rect` takes a tiling.
]

// An overlay color is painted over the whole slide, so it is useful with an alpha channel,
// which dims the slide with a tint.
#slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    teal,
    orange,
    angle: 70deg,
  )),
  overlay: pink.transparentize(50%),
)[
  = A Tinted Overlay
  An overlay color with an alpha channel colors everything beneath it.
]

// `init` describes the initial state, and its first argument is the transition into
// the slide. A slide that has no other use for a timeline writes the call on its own.
#slide(animation: anim.init(anim.push()))[
  = Pushed in from the Right

  `anim.push()` moves the slide in from one edge and the slide before it out.
  Its `direction` defaults to `rtl`, which is the direction of travel.

  Stepping back plays the same transition backwards.
]

// The `import` inside the block gives the timeline its vocabulary, as on every slide
// whose timeline has more than one call.
#slide(
  background: rect(
    width: 100%,
    height: 100%,
    fill: gradient.linear(
      pink.darken(30%),
      orange,
      angle: -70deg,
    ),
  ),
  animation: {
    import anim: *
    init(push(direction: btt))
    sub(reveal("detail"))
  },
)[
  = Pushed up into View

  This slide travels from bottom to top.

  #tag("detail")[
    A transition changes nothing inside either slide,
    so this line is still hidden when the slide arrives.
  ]
]

#slide(animation: anim.init(anim.cover(direction: ttb)))[
  = Covered from the Top

  `anim.cover(direction: ttb)` moves the slide in over the slide before it,
  which stays where it is.
]

#slide(
  background: orange.lighten(60%),
  animation: anim.init(anim.uncover(direction: ltr)),
)[
  = Uncovered to the Right

  `anim.uncover(direction: ltr)` moves the slide before it out at the right edge,
  over this slide, which stays where it is.
]

#slide(
  background: teal.lighten(50%),
  animation: anim.init(anim.wipe()),
)[
  = Wiped In

  `anim.wipe()` reveals the slide behind an edge that travels from left to right.
]

// `duration:` overrides the `transition-duration` of the deck for this slide.
#slide(animation: anim.init(anim.wipe(direction: ttb), duration: 1.2))[
  = Wiped in from the Top, Slowly

  `init` takes a `duration:` in seconds.
]

#slide(animation: anim.init(anim.crossfade(), duration: 1.2))[
  = A Slow Crossfade

  `anim.crossfade()` is the default transition of the deck, here written explicitly.
]

// A duration of zero is a hard cut, whatever the transition.
// The dark background arriving without a fade reads as a change of chapter.
#slide(background: dark, animation: anim.init(duration: 0))[
  #set text(fill: white)
  #show raw: set text(fill: dark)
  = Arrived without a Fade

  A duration of zero is a hard cut.

  Transitions are HTML only.
  The two paged outputs put two slides on two pages with nothing between them.
]
