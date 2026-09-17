// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The continuous primitives, and the four keywords that time them.
// Nothing here changes what typst lays out, so every step is free on paper
// and smooth in the browser.

#import "@preview/animo:0.1.0": *

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


#slide(animation: {
  import anim: *
  // An absolute move puts the tag's own top-left corner at a distance from the canvas
  // origin. The anchor is the corner the body gave the tag, so the move is idempotent:
  // stating it twice leaves the ball where the first one put it.
  sub(move("ball", x: 12cm, y: 5cm))
  // A relative move shifts the tag from wherever it already is.
  // A factor is set rather than multiplied into what is there, so `f: 2` after `f: 2`
  // is still twice the size, and `f: 1` restores the ball whatever came before it.
  sub(move("ball", dx: -3cm), scale("ball", f: 2))
  // `relto` names the tag the move is measured from, so the ball lands on the target.
  sub(move("ball", relto: "target"), scale("ball", f: 1))
  // `hide` keeps the space the element took, which is what keeps the slide still.
  sub(hide("target"))
})[
  = Move and Scale

  #place(dx: 10cm, dy: 1cm, tag("target", circle(
    radius: 0.6cm,
    stroke: (paint: accent, dash: "dashed"),
  )))

  #tag("ball", circle(radius: 0.6cm, fill: accent))
]

// Timing is the one thing a timeline says that no page can show,
// so the slide that explains it is also the slide that does it.
#slide(animation: {
  import anim: *
  // `wait:` brings this step up two seconds after the step before it was triggered,
  // and `hold:` sends the deck on two seconds after this one was.
  sub(wait: 2, hold: 2, reveal("gap"))
  // `delay:` holds one operation back inside its step, and `duration:` gives it a tempo
  // of its own. The step keeps one clock: both become the browser animation's own.
  sub(
    reveal("first"),
    reveal("second", delay: 0.4),
    reveal("third", delay: 0.8, duration: 1.5),
  )
})[
  = Timing

  #tag("gap")[
    `wait:` and `hold:` are the two names of one gap between two steps.
  ]

  #v(0.5cm)

  #tag("first")[`delay:` staggers the operations of one step,]
  #tag("second")[so they arrive in the order they are written,]
  #tag("third")[and `duration:` says how long each of them takes.]

  #v(1fr)

  A presenter can always step ahead of a timer. \
  Stepping back or pressing `Space` stops the clock.
]
