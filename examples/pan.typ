// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// A canvas larger than the slide, travelled over by panning.
// The viewport is what the audience sees and what clips;
// the canvas is what the body is laid out on, and it may be larger.

#import "@preview/animo:0.1.1": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show heading: set block(below: 1em)

#let card(body) = block(
  width: 12cm,
  inset: 0.5cm,
  radius: 0.2cm,
  fill: rgb("#ddeeff"),
  body,
)

// `handout: true` on the slide keeps the overview, which the last state has panned away
// from: a handout page is the viewport of one state and shows no more of the canvas.
#slide(handout: true, animation: {
  import anim: *
  // `relto` shows the tag the way a fresh slide shows its first line,
  // which is at the deck's own margin.
  sub(handout: true, pan(relto: "right"))
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

  // A placed element contributes its own extent to the automatic canvas,
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
