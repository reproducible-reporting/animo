// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// Slide numbers, subslide numbers and a progress bar, written into the overlay by a wrapper
// around `#slide`, because Animo has no header or footer machinery.
// Each of the three numbering functions has a color on every slide of this deck:
// the slide number is dark gray, the subslide number is orange and the progress bar is teal.

#import "@preview/animo:0.1.1": *
// The colors, the title slide, the styles and the slide wrapper that the demo decks share.
#import "_common.typ": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show: demo-style

// A number in the footer, as white text on a colored label.
#let pill(color, body) = box(
  fill: color,
  inset: (x: 4pt, y: 2pt),
  radius: 2pt,
  text(fill: white, weight: "bold", body),
)

// The footer of every slide, in the bottom right corner of the viewport.
// `slide-number()` is `none` on a slide with `numbered: false`, so such a slide has no footer.
// `per-subslide` lays its callback out once per subslide,
// and the browser shows the rendering of the subslide on screen.
// The subslide number is written only on a slide with more than one subslide,
// because a slide with a single subslide has nothing to tell apart.
#let footer = context {
  let number = slide-number()
  if number != none {
    place(bottom + right, dx: -0.4cm, dy: -0.35cm, text(size: 0.75em, {
      pill(dark)[slide #number of #slide-count()]
      per-subslide(it => if it.count > 1 {
        h(3pt)
        pill(orange)[sub #it.number of #it.count]
      })
    }))
  }
}

// The fraction of the talk that lies behind the subslide on screen.
// `step` and `steps` count every subslide of every slide, so the bar advances once per step.
#let done(it) = if it.steps > 1 { (it.step - 1) / (it.steps - 1) } else { 1 }

// A progress bar as wide as its container, drawn for one subslide.
#let bar(it, height) = stack(
  dir: ltr,
  rect(width: 100% * done(it), height: height, fill: teal, stroke: none),
  rect(
    width: 100% * (1 - done(it)),
    height: height,
    fill: teal.lighten(80%),
    stroke: none,
  ),
)

// The stack of renderings says `wrap: block`, because a width given as a ratio
// needs a container width to be a ratio of.
#let progress = place(bottom, per-subslide(it => bar(it, 3pt), wrap: block))

// The wrapper that this deck writes its slides with.
// It puts the footer, the note for the subslide on screen and the progress bar in the overlay.
// The overlay is laid out once per slide, where the body is laid out once per epoch,
// so a `per-subslide` in the overlay costs its renderings only once.
// The overlay also belongs to the viewport, so a `pan` leaves the numbers where they are.
#let numbered-slide(body, notes: none, ..arguments) = slide(
  overlay: {
    footer
    if notes != none {
      place(bottom + left, dx: 1cm, dy: -0.35cm, block(
        width: 9cm,
        state-note(notes),
      ))
    }
    progress
  },
  ..arguments,
  body,
)

// A function name in the color that the deck gives it, for the legend on the title slide.
#let chip(color, body) = box(
  fill: color.lighten(85%),
  stroke: 0.8pt + color,
  inset: 5pt,
  radius: 3pt,
  text(fill: color, weight: "bold", body),
)

#title-slide("numbering.typ", "Numbering", "numbering/")

#numbered-slide(
  numbered: false,
  // The uncover lifts the curtain of the title slide.
  animation: anim.init(anim.uncover(direction: btt)),
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    white,
    pale,
    angle: 90deg,
  )),
  notes: (
    [`numbered: false` leaves this slide out of the count, so it has no footer.],
  ),
)[
  #set align(center + horizon)
  #text(size: 2.4em, fill: dark)[*Numbering*]

  #explain[Slide numbers, subslide numbers and a progress bar]

  #v(0.6cm)

  #chip(dark)[`slide-number()`]
  #h(0.3cm)
  #chip(orange)[`per-subslide`: `number` and `count`]
  #h(0.3cm)
  #chip(teal)[`per-subslide`: `step` and `steps`]
]

#numbered-slide(
  notes: (
    [This slide has a single subslide, so the footer writes the slide number alone.],
  ),
)[
  = The Slide Number

  #explain[`slide-number()` and `slide-count()` are context functions that return integers.]

  #v(1fr)

  #align(center, text(size: 2.4em, fill: dark)[
    *slide #context slide-number() of #context slide-count()*
  ])

  #align(center)[`#context [slide #slide-number() of #slide-count()]`]

  #v(1fr)

  #explain[
    The title slide and the slide after it have `numbered: false`, so the counter skips both,
    and the third slide of the deck is slide 1.
    The footer in the corner shows the same number.
  ]
]

// One box per subslide of the slide, with the box of the subslide on screen filled.
#let subslide-diagram(it) = stack(
  spacing: 8pt,
  stack(
    dir: ltr,
    spacing: 6pt,
    ..range(1, it.count + 1).map(i => box(
      inset: 6pt,
      radius: 3pt,
      stroke: 0.8pt + orange,
      fill: if i == it.number { orange } else { white },
      text(fill: if i == it.number { white } else { orange })[*sub #i*],
    )),
  ),
  explain[`it.number` is #it.number and `it.count` is #it.count],
)

#numbered-slide(
  notes: (
    [The orange label in the footer counts the subslides of this slide.],
    [`it.number` grows by one with every step, and `it.count` stays the same.],
    [A question about "slide 2, sub 3" points at one subslide.],
    [A page of the static presentation shows the number of its subslide.],
  ),
  animation: {
    import anim: *
    sub(reveal("count"))
    sub(reveal("rule"))
    sub(reveal("pages"))
  },
)[
  = The Subslide Number

  #[
    #set text(fill: orange, weight: "bold")
    `it.number` is the position of the subslide on screen, counting from one.

    #tag("count")[`it.count` is how many subslides the slide has.]

    #tag("rule")[The footer writes both only when `it.count > 1`.]

    #tag("pages")[Every output type shows the same number on the same subslide.]
  ]

  #v(1fr)

  // The diagram is a second `per-subslide`, which costs no rendering of the body.
  #align(center, per-subslide(subslide-diagram))

  #v(1fr)

  #explain[
    `per-subslide(it => ..)` calls its callback once per subslide,
    and the browser shows the rendering of the subslide on screen.
  ]
]

#numbered-slide(
  notes: (
    [`it.step` counts the subslides of every slide, including the title slide.],
    [Each step advances the bar by the same amount.],
    [The bar on the slide and the thin one at the bottom edge are drawn by one function.],
  ),
  animation: {
    import anim: *
    sub(reveal("same"))
    sub(reveal("thin"))
  },
)[
  = A Progress Bar

  #align(center, per-subslide(it => text(size: 2em, fill: teal)[
    *step #it.step of #it.steps*
  ]))

  #per-subslide(it => bar(it, 0.5cm), wrap: block)

  #align(center, per-subslide(it => explain[
    The bar is `100% * (it.step - 1) / (it.steps - 1)` wide,
    which is #calc.round(100 * done(it))% here.
  ]))

  #v(1fr)

  #[
    #set text(fill: teal, weight: "bold")
    #tag(
      "same",
    )[A slide that animates and a slide that does not move the bar alike.]

    #tag(
      "thin",
    )[The same bar runs along the bottom edge of every slide, 3pt thin.]
  ]

  #v(1fr)
]

// A bar drawn inline, whose width is a ratio of the container that holds it.
#let inline-bar(it) = box(width: 100% * done(it), height: 0.4cm, fill: teal)

// A frame of the full width around a stack of renderings,
// which stays visible when the stack is empty.
#let frame(body) = block(
  width: 100%,
  height: 0.6cm,
  inset: 0.1cm,
  stroke: guide,
  body,
)

#numbered-slide(
  notes: (
    [The two frames hold the same inline bar, and only the upper one shows it.],
  ),
)[
  = The `wrap:` Argument

  #explain[Both frames hold `per-subslide(it => box(width: 100% * .., ..))`.]

  #v(1fr)

  #grid(
    columns: (auto, 1fr),
    align: (right + horizon, left + horizon),
    column-gutter: 0.4cm,
    row-gutter: 0.6cm,
    [`wrap: block`], frame(per-subslide(inline-bar, wrap: block)),
    [`wrap: auto`], frame(per-subslide(inline-bar)),
  )

  #v(1fr)

  #explain[
    `wrap: auto` chooses a box for inline content, and a box is only as wide as what it holds.
    A `100%` width inside such a box resolves to zero, so the lower bar is invisible.
    `wrap: block` gives the stack a block that fills the width of the slide.
  ]
]

#numbered-slide(
  notes: (
    [The footer is in the overlay, and the dashed label is a copy in the body.],
    [`pan(dx: 10cm)` moves the canvas with the copy, and the footer stays in its corner.],
    [`pan(x: 0cm)` returns to the origin of the canvas, and the copy returns with it.],
  ),
  animation: {
    import anim: *
    sub(pan(dx: 10cm))
    sub(pan(x: 0cm))
  },
)[
  = Where a Number Goes

  #explain[
    Typst lays out the overlay once per slide and the body once per epoch.
    A `per-subslide` in the overlay therefore costs its renderings only once,
    and the overlay stays in place when a `pan` moves the canvas.
  ]

  // The copy is placed in the body, so it travels with the canvas.
  #place(bottom + right, box(
    stroke: (paint: dark, dash: "dashed"),
    inset: (x: 4pt, y: 2pt),
    radius: 2pt,
    text(size: 0.75em, fill: dark, weight: "bold")[
      slide #context slide-number() in the body
    ],
  ))

  // A placed card makes the canvas wider than the viewport, which gives the pan room.
  #place(dx: 15cm, dy: 1.5cm, block(
    width: 9cm,
    inset: 0.5cm,
    radius: 0.2cm,
    fill: pale,
  )[
    The canvas has moved 10cm to the left, and the copy in the body has moved with it.
    The footer is still in its corner.
  ])
]
