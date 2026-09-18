// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// Numbering: how a deck tells its audience which part of the talk they are looking at.
//
// Animo has no header or footer machinery, so a recurring element is a wrapper around
// `#slide` that fills one of the two outer layers. This deck writes one, and everything
// it puts in that layer is ordinary typst content.
//
// The overlay is the layer to put a number in, and the reason is the cost model rather than taste.
// It is one rendering per slide where the body is one rendering per epoch,
// so a stack of one rendering per subslide is paid for once here and once per epoch there.
// It also belongs to the viewport, so a `pan` leaves it where it is.

#import "@preview/animo:0.1.1": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show heading: set block(below: 1em)

#let accent = rgb("#204080")

// Style inline code
#let bgrb = rgb("#ddeeff")
#show raw.where(block: false): it => highlight(
  fill: bgrb,
  stroke: bgrb + 0.1cm,
  radius: 0.1cm,
  it,
)

// The footer every slide carries, and the whole of the numbering surface in one place.
//
// `slide-number()` and `slide-count()` are plain numbers, so anything can be computed from them,
// and `slide-number()` is `none` on a slide that `numbered: false` leaves out.
//
// `per-subslide` is what a number finer than a slide needs.
// Its callback is laid out once per subslide,
// and the one belonging to the subslide being shown is what the audience sees:
// the browser chooses between the renderings,
// and a page of a paged output carries the rendering of its own state.
// A subslide number is written only where there is more than one subslide to tell apart,
// which is what keeps it out of the way on an ordinary slide.
#let footer = context {
  let number = slide-number()
  if number != none {
    place(bottom + right, dx: -0.15cm, dy: -0.25cm, text(
      size: 0.7em,
      fill: gray,
      [
        slide #number of #slide-count()
        #per-subslide(it => if it.count > 1 [(sub #it.number of #it.count)])
      ],
    ))
  }
}

// A progress bar over the whole talk, which is the deck-wide half of the same callback.
//
// `step` and `steps` count every state of every slide,
// so the bar advances once per click rather than once per slide.
// It says `wrap: block` because a rendering that states a ratio
// needs a container width to be a ratio of, and only a filling container has one.
// The `stack` below is block-level, so `auto` chooses the same wrapper here.
// The argument is needed for a rendering that is inline and states a ratio,
// such as a bar drawn as a `box` of a ratio width:
// a stack of inline renderings measures them unbounded, where a `100%` width resolves to zero.
#let progress = place(bottom, per-subslide(
  it => stack(
    dir: ltr,
    rect(
      width: 100% * (it.step - 1) / (it.steps - 1),
      height: 4pt,
      fill: accent,
      stroke: none,
    ),
    rect(
      width: 100% * (it.steps - it.step) / (it.steps - 1),
      height: 4pt,
      fill: gray.lighten(70%),
      stroke: none,
    ),
  ),
  wrap: block,
))

// The wrapper the deck writes its slides with, which is the recurring-element pattern:
// no templating features, one function, two placements in a layer.
#let numbered-slide(body, ..arguments) = slide(
  overlay: {
    footer
    progress
  },
  ..arguments,
  body,
)

#numbered-slide(numbered: false)[
  #set align(center + horizon)
  #text(size: 2em)[*Numbering*]

  A title slide is `numbered: false`, \
  so it carries no number and the counter passes it by.
]

#numbered-slide(animation: {
  import anim: *
  sub(reveal("second"))
  sub(reveal("third"))
})[
  = A slide that animates

  #tag("first")[This is the first subslide, and the footer says so.]

  #tag("second")[The number beside the slide number counts these.]

  #tag(
    "third",
  )[Ask about "slide 1 (sub 3 of 3)" and the speaker can find it.]
]

#numbered-slide[
  = A static slide

  Due to lack of subslides, the footer writes the slide number alone.
]

#numbered-slide(animation: {
  import anim: *
  sub(replace("claim")[The bar underneath counts clicks, not slides.])
})[
  = The bar spans the talk

  #region[
    #tag("claim")[Every state of every slide is one step of the whole deck.]
  ]

  So the bar moves by the same amount on a slide that animates as on one that does not.
]
