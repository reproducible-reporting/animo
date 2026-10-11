// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The states that the handout keeps, and the reasons to keep more than the final one.
// The handout keeps the final state of every slide by default,
// so content that a slide shows earlier and then hides, removes, replaces or pans away from
// reaches the handout only on a state that asks for a page.

#import "@preview/animo:0.2.0": *
// The colors, the title slide, the styles and the slide wrapper that the demo decks share.
#import "_common.typ": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show: demo-style

// Every slide of this deck marks the states that the handout keeps.
#let explained-slide = explained-slide.with(handout-badge: true)

#title-slide("handouts.typ", "Handouts", "handouts/")

// No state of this slide states a flag, so the handout keeps the final state alone.
#explained-slide(
  notes: (
    [The handout does not keep this state, which shows nothing the final state lacks.],
    [Every state adds to the one before it.],
    [The final state shows everything, and the handout keeps it by default.],
  ),
  animation: {
    import anim: *
    // The uncover lifts the curtain of the title slide.
    init(uncover(direction: btt))
    sub(reveal("second"))
    sub(reveal("third"))
  },
)[
  = The Final State by Default

  #[
    #set text(fill: teal, weight: "bold")
    #tag("first")[A first point,]
    #tag("second")[a second point,]
    #tag("third")[and a third one.]
  ]

  #v(1fr)

  #explain[A slide whose final state shows all of its content needs no flag.]
]

// One step of the derivation on the next slide, as the body and each replacement lay it out.
#let step(body) = text(size: 1.6em, fill: orange, body)

// Each step of the derivation replaces the one before it, so the final state shows only the
// result. `init(handout: true)` and `handout: true` keep the earlier steps as well.
#explained-slide(
  notes: (
    [`init(handout: true)` keeps the expression as the body writes it.],
    [`sub(handout: true, ...)` keeps the step that the next `replace` destroys.],
    [The final state shows only the result.],
  ),
  animation: {
    import anim: *
    init(handout: true)
    sub(handout: true, replace("step", step($ (a + b)(a + b) $)))
    sub(replace("step", step($ a^2 + 2 a b + b^2 $)))
  },
)[
  = Content That Is Replaced

  #tag("step", wrap: block, step($ (a + b)^2 $))

  #v(1fr)

  #explain[
    `replace` and `remove` destroy what they replace or remove,
    so the final state of this slide holds none of the earlier steps.
  ]
]

// The hint is hidden again before the answer appears, so the final state does not show it.
#explained-slide(
  notes: (
    [The handout does not keep the bare question, which the next state repeats.],
    [`handout: true` keeps the hint, which the next subslide hides.],
    [The final state shows the answer without the hint.],
  ),
  animation: {
    import anim: *
    sub(handout: true, reveal("hint"))
    sub(hide("hint"), reveal("answer"))
  },
)[
  = Content That Is Hidden

  How many states does a slide with two `sub` calls have?

  #tag("hint")[#text(fill: orange)[*Hint:* the body as written is a state too.]]

  #tag("answer")[#text(fill: teal)[*Three*, numbered 0 to 2.]]

  #v(1fr)

  #explain[A hidden tag still takes up its room, so the answer stays below the hint.]
]

// The handout keeps no state of an exercise that shows the solution,
// so that the reader of the handout can try the exercise first.
#explained-slide(
  notes: (
    [`init(handout: true)` keeps the exercise with the blank.],
    [`handout: false` leaves the solution out of the handout.],
  ),
  animation: {
    import anim: *
    init(handout: true)
    sub(handout: false, reset("blank"))
  },
)[
  = Content That Is Filled In

  The timeline of a slide is read before the body is laid out,
  which is why it is #box(
    stroke: guide,
    tag("blank")[#text(fill: teal)[*an argument*]],
  ) of `#slide`.

  #v(1fr)

  #explain[
    A tag whose first content operation is `reset` starts removed,
    so the initial state shows the blank and the final state fills it in.
  ]
]

// A handout page is the viewport of one state, so it shows no more of the canvas than the
// presentation does. The overview is kept, which the last state has panned away from.
#explained-slide(
  notes: (
    [`init(handout: true)` keeps the overview.],
    [The final state shows the card that was placed outside the viewport.],
  ),
  animation: {
    import anim: *
    init(handout: true)
    sub(pan(relto: "detail"))
  },
)[
  = Content That Is Panned Away From

  An overview, with the details beyond the right edge of the viewport.

  #v(1fr)

  #explain[A handout page shows the viewport of the state it keeps, not the whole canvas.]

  #place(dx: 18cm, dy: 0cm, tag("detail", block(
    width: 12cm,
    inset: 0.5cm,
    radius: 0.2cm,
    fill: pale,
  )[
    = The Details

    The last state of the slide shows only this card.
  ]))
]

// A slide without `sub` calls has one state, which is also its final state,
// so `init(handout: false)` leaves the whole slide out of the handout.
#explained-slide(animation: {
  import anim: *
  init(handout: false)
})[
  = A Slide Left Out

  #text(size: 1.5em)[The presenter switches to a live demonstration here.]

  #v(1fr)

  #explain[
    `init(handout: false)` leaves this slide out of the handout,
    because a reader of the handout cannot watch the demonstration.
  ]
]
