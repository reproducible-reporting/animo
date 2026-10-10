// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// A canvas larger than the slide, travelled over by panning.
// The viewport is what the audience sees and what clips;
// the canvas is what the body is laid out on, and it may be larger.

#import "@preview/animo:0.1.1": *
// The colors and the title slide that several example decks share.
#import "_common.typ": orange, pale, title-slide

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show heading: set block(below: 1em)

// Style inline code
#show raw.where(block: false): it => highlight(
  fill: pale,
  stroke: pale + 0.1cm,
  radius: 0.1cm,
  it,
)

#let card(body) = block(
  width: 12cm,
  inset: 0.5cm,
  radius: 0.2cm,
  fill: pale,
  body,
)

#title-slide("viewport.typ")

#slide(animation: {
  import anim: *
  // The push lifts the curtain of the title slide.
  init(push(direction: btt))
  // `relto` shows the tag the way a fresh slide shows its first line,
  // which is at the margin of the deck.
  sub(pan(relto: "right"))
  // The two ways of saying where the viewport goes combine, one per axis:
  // stay on the tag horizontally and scroll down from where the viewport is.
  sub(pan(dy: 5cm))
  // `x: 0cm` and `y: 0cm` are the canvas origin, the position the slide started at.
  sub(pan(x: 0cm, y: 0cm))
})[
  = An Overview

  The rest of this slide lies beyond the edge of the viewport.
  Nothing there flows onto a next slide: the viewport clips, and `pan` is what brings
  the rest of the canvas into view.

  // A placed element contributes its extent to the automatic canvas,
  // so this is what makes the slide two screens wide.
  #place(dx: 18cm, dy: 0cm, tag("right", card[
    = To the Right

    The canvas is the union of the body and everything placed on it,
    clamped to at least the viewport.
  ]))

  #place(dx: 18cm, dy: 6cm, card[
    = And Further Down

    A pan is not clamped to the canvas,
    so a slide can scroll a card to the middle of the viewport
    rather than to its corner.
  ])
]

// A body that is longer than the viewport gets a taller canvas, and nothing has to be
// placed for that to work.
#slide(animation: {
  import anim: *
  sub(pan(dy: 6cm))
  sub(pan(relto: "last"))
})[
  = A Long Body

  #for i in range(1, 17) [
    + Item #i of a list that is longer than one screenful.
  ]

  // The anchor of a tag is the top-left corner of its wrapper, so this phrase is anchored
  // at the top of its line rather than at the top of its letters.
  #tag("last")[*The list ends here*], at the line the last pan goes to.

  // The body is laid out in a box as tall as its flow, so this mark lands at the bottom of
  // the whole flow rather than of the first screenful.
  #place(bottom + right)[the end of the flow]
]

// A pan past the edge of the canvas shows the background of the slide there.
#slide(background: orange.lighten(92%), animation: {
  import anim: *
  // `x` and `y` are measured from the anchor, so negative values put the tag towards the
  // middle of the viewport rather than in its corner.
  sub(pan(relto: "middle", x: -4cm, y: -2.5cm))
  sub(pan(x: -6cm, y: -4cm))
})[
  = Past the Edge

  The viewport is not clamped to the canvas.

  #place(dx: 18cm, dy: 6cm, tag("middle", box(
    fill: pale,
    inset: 0.4cm,
  )[In the middle of the viewport]))
]

// The background and the overlay belong to the viewport, so a pan moves the body between
// them and leaves the two layers where they are.
#slide(
  background: place(right + horizon, dx: -1cm, circle(
    radius: 2cm,
    fill: orange.lighten(60%),
  )),
  overlay: place(bottom + left, dx: 0.5cm, dy: -0.5cm, box(
    fill: pale,
    inset: 0.15cm,
  )[A logo in the overlay]),
  animation: {
    import anim: *
    sub(pan(dx: 10cm))
    sub(pan(dx: -10cm))
  },
)[
  = Layers Stay Put

  A pan moves the canvas, which carries the body,
  between the background and the overlay.

  #place(
    dx: 12cm,
    dy: 2cm,
    card[The body travels, the disc and the logo do not.],
  )
]

// The automatic canvas counts a placement nested in another container from the canvas
// origin, so it comes out short by where the container sits. An explicit canvas is the
// escape hatch, and it is still clamped to at least the viewport.
#slide(canvas: (width: 36cm, height: 9cm), animation: {
  import anim: *
  sub(pan(relto: "far"))
})[
  = An Explicit Canvas

  #block(inset: (left: 6cm))[
    #place(dx: 16cm, tag("far", card[
      This card is placed inside an indented block,
      and the explicit canvas makes room for it.
    ]))
  ]
]
