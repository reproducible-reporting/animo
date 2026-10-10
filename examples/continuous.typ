// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The timeline of a slide: subslides, the continuous primitives,
// and the four keywords that time them.
// No timeline here changes what typst lays out, so every step is free on paper
// and smooth in the browser.

#import "@preview/animo:0.1.1": *
// The colors, the title slide, the styles and the slide wrapper that the example decks share.
#import "_common.typ": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show: example-style

// A cross centred on the point where it is placed, with a label above it on the right.
#let cross(label) = {
  let stroke = 0.6pt + luma(150)
  place(dx: -0.3cm, line(length: 0.6cm, stroke: stroke))
  place(dy: -0.3cm, line(angle: 90deg, length: 0.6cm, stroke: stroke))
  place(dx: 0.15cm, dy: -0.6cm, explain(text(size: 0.8em, label)))
}

#title-slide("continuous.typ")

// Two `sub` calls give three states: the body as written, and one state per `sub`.
#explained-slide(animation: {
  import anim: *
  // The push lifts the curtain of the title slide.
  init(push(direction: btt))
  sub(reveal("a"))
  sub(hide("a"), move("b", dy: 1cm))
})[
  = Subslides

  #tag("a")[#text(
    fill: orange,
  )[*State 1 reveals this line, and state 2 hides it again.*]]

  #tag("b")[#text(fill: teal)[*State 2 moves this line down by a centimeter.*]]

  #place(bottom, explain[
    A slide with $S$ `sub` calls has $S + 1$ states, numbered from 0 to $S$.
  ])
]

// The import is scoped to the animation block, so `hide`, `move` and `scale` in the body
// below are the elements of typst, which act on the layout.
#explained-slide(animation: {
  import anim: *
  sub(scale("typst", f: 1.5))
})[
  = The Block-Scoped Import

  #explain[In the body, `move` and `scale` are the elements of typst, which change the layout.]

  typst's #box(move(dy: -0.2em)[`move`]) lifts a word,
  and typst's #box(scale(x: 150%, reflow: true)[`scale`]) stretches one.

  #explain[In the timeline, `scale` is the primitive of Animo, which scales a tag.]

  #align(center, tag("typst")[#text(fill: orange)[*This phrase grows.*]])

  #explain[typst's own `hide` hides the framed sentence, and no timeline can reveal it.]

  #box(stroke: guide, inset: 3pt, hide[This sentence is hidden by typst.])
]

// A star import of the package brings in `anim`, so a timeline of one `sub` can be
// written without the inner import.
#explained-slide(animation: anim.sub(anim.reveal("short")))[
  = Without the Import

  #explain[A star import of the package also brings in `anim`, so this timeline needs no `import`:]

  ```typst
  animation: anim.sub(anim.reveal("short"))
  ```

  #tag("short")[#text(
    fill: orange,
  )[*This line is the tag that the timeline reveals.*]]
]

#explained-slide(
  notes: (
    [The body puts the ball at the top left, and the dashed target on the right.],
    [`x: 12cm, y: 5cm` puts the top-left corner of the ball on the cross.],
    [`dx: -3cm` shifts the ball to the left, and `f: 2` doubles it about its centre.],
    [`relto: "target"` puts the ball on the target, and `f: 1` restores its size.],
    [`hide` makes the target invisible, and the ball stays where it is.],
  ),
  animation: {
    import anim: *
    // An absolute move puts the top-left corner of the moved tag at a distance from the
    // canvas origin. The anchor is the corner the body gave the tag, so the move is idempotent:
    // stating it twice leaves the ball where the first one put it.
    sub(move("ball", x: 12cm, y: 5cm))
    // A relative move shifts the tag from wherever it already is.
    // A factor is set rather than multiplied into what is there, so `f: 2` after `f: 2`
    // is still twice the size, and `f: 1` restores the ball whatever came before it.
    sub(move("ball", dx: -3cm), scale("ball", f: 2))
    // `relto` names the tag the move is measured from, so the ball lands on the target.
    // A move without `x` or `y` on an axis keeps the anchor of that axis.
    sub(move("ball", relto: "target"), scale("ball", f: 1))
    // `hide` keeps the space the element took, which is what keeps the slide still.
    sub(hide("target"))
  },
)[
  = Move and Scale

  // The canvas origin is the corner of the slide and the body starts at the margin,
  // so the point `x: 12cm, y: 5cm` is 1cm closer to the body origin on each axis.
  // A `#place` without an alignment starts where the flow is, below the heading,
  // so the cross is aligned to the top of the body.
  #place(top + left, dx: 11cm, dy: 4cm, cross[`x: 12cm, y: 5cm`])

  #place(dx: 10cm, dy: 1cm, tag("target", circle(
    radius: 0.6cm,
    stroke: (paint: dark, dash: "dashed"),
  )))

  // `wrap: box` makes the wrapper hug the ball, so the scale is about the centre of the ball
  // rather than of a block as wide as the slide.
  #tag("ball", wrap: box, circle(radius: 0.6cm, fill: orange))
]

// A label that a move can put on a target, as a filled chip whose corner is easy to see.
#let chip(color, body) = box(
  fill: color.lighten(80%),
  stroke: 0.8pt + color,
  inset: 4pt,
  text(fill: color, strong(body)),
)

#explained-slide(
  notes: (
    [The label and the two sites of `pair` are where the body put them.],
    [`relto: "node"` puts the top-left corner of the label on that of the node.],
    [`dy: -5mm` lifts the label from where it is.],
    [`x: 1cm, y: 6cm` is measured from the corner of the slide, so `x: 1cm` is the margin.],
    [The first site of `pair` lands on the node, and the second site moves along.],
  ),
  animation: {
    import anim: *
    // The label goes onto the node, is lifted from there, and then goes to a corner of the
    // canvas. `x` and `dx` on one axis are refused, because they are measured from different
    // places, so each step uses one of the two per axis.
    sub(move("label", relto: "node"))
    sub(move("label", dy: -5mm))
    // The canvas origin is the corner of the slide, so `x: 1cm` is the left margin.
    sub(move("label", x: 1cm, y: 6cm))
    // A name with several sites moves as one: the first site lands on the target,
    // and the other site takes the same translation.
    sub(move("pair", relto: "node"))
  },
)[
  = Where `move` Puts Things

  #place(dx: 9cm, dy: 1cm, tag("node", rect(
    width: 4cm,
    height: 1.5cm,
    stroke: dark,
    align(bottom + right, explain[node]),
  )))

  #tag("label", chip(orange)[label])

  #tag("pair", chip(teal)[first]) and #tag("pair", chip(teal)[second])
]

#explained-slide(
  notes: (
    [The square is 1cm wide, and the dashed target is 2cm wide.],
    [`f: 2` and `relto` in one subslide put the corner of the doubled square on the target.],
    [`f: 1` shrinks the placed square towards the corner it was put on.],
  ),
  animation: {
    import anim: *
    // `wrap: box` makes both wrappers hug their squares, so the box a scale grows is the
    // square rather than a block as wide as the slide.
    // A tag placed with `relto` grows from its anchor, so the corner of the doubled square
    // lands on the corner of the target, and stays there when the factor changes.
    sub(move("square", relto: "corner"), scale("square", f: 2))
    sub(scale("square", f: 1))
  },
)[
  = Moved and Scaled

  #place(dx: 8cm, dy: 1cm, tag("corner", wrap: box, rect(
    width: 2cm,
    height: 2cm,
    stroke: (paint: dark, dash: "dashed"),
  )))

  #tag("square", wrap: box, rect(width: 1cm, height: 1cm, fill: orange))
]

#explained-slide(
  notes: (
    [The dashed frame marks the size of the word as the body laid it out.],
    [`fx: 2` makes the word twice as wide.],
    [`fy: 200%` makes it twice as tall, and the width keeps its factor of 2.],
    [`f: 1` sets both factors back to 1.],
  ),
  animation: {
    import anim: *
    sub(scale("word", fx: 2))
    // An axis the call does not mention keeps the factor it had, so this word is now
    // twice as wide and twice as tall.
    sub(scale("word", fy: 200%))
    // A factor is set, so `f: 1` restores both axes.
    sub(scale("word", f: 1))
  },
)[
  = What `scale` Sets

  #v(1fr)

  // The frame sits outside the tag, so it keeps the unscaled size while the word scales.
  #align(center, box(stroke: guide, inset: 3pt, tag("word")[#text(
    size: 1.6em,
    fill: orange,
  )[*stretch*]]))

  #v(1fr)

  #explain[
    `f` sets both axes, `fx` and `fy` one axis each.
    A factor is a number or a ratio, so `f: 2` and `f: 200%` are the same.
  ]
]

// The next slide comes up on its own, so this slide warns the audience that no key is needed.
// The gap after it is timed by the `init(wait: 6)` of the next slide,
// because one gap takes one number.
#explained-slide(background: orange.lighten(70%))[
  #set align(center + horizon)
  #text(size: 1.6em, fill: orange)[*The next slide plays on its own.*]

  It comes up in six seconds, so there is no need to press a key.
]

// Timing is the one thing a timeline says that no page can show,
// so the slide that explains it is also the slide that does it.
#explained-slide(
  notes: (
    [`init(wait: 6)` brings this state up six seconds after the slide before it.],
    [`wait: 2` brings this state up two seconds later, and `hold: 2` keeps it for two.],
    [`delay:` and `duration:` stagger the three lines, and a step back plays them in reverse.],
  ),
  animation: {
    import anim: *
    // `init(wait: ..)` times the gap into the initial state of this slide.
    init(wait: 6)
    // `wait:` brings this subslide up two seconds after the one before it was triggered,
    // and `hold:` sends the deck on two seconds after this one was.
    sub(wait: 2, hold: 2, reveal("gap"))
    // `delay:` holds one operation back inside its subslide, and `duration:` gives it a
    // separate tempo. The subslide keeps one clock,
    // because both become the delay and the duration of the browser animation.
    // A step back plays this schedule mirrored, so the lines leave in reverse order.
    sub(
      reveal("first"),
      reveal("second", delay: 0.4),
      reveal("third", delay: 0.8, duration: 1.5),
    )
  },
)[
  = Timing

  #tag("gap")[#text(fill: orange)[
    *`wait:` and `hold:` are the two names of one gap between two subslides.*
  ]]

  #v(0.5cm)

  #[
    #set text(fill: teal, weight: "bold")
    #tag("first")[`delay:` staggers the operations of one subslide,]
    #tag("second")[so they arrive in the order they are written,]
    #tag("third")[and `duration:` says how long each of them takes.]
  ]

  #v(1fr)

  #explain[
    A presenter can always step ahead of a timer. \
    Stepping back plays the deck backwards, and `Space` stops it where it is.
  ]
]

// The states of the next slide and the gaps between them, with the state on screen filled.
// The two states that `hold: 0` joins share a dashed frame.
#let join-diagram(current) = {
  let node(i) = box(
    inset: 4pt,
    radius: 3pt,
    stroke: 0.8pt + dark,
    fill: if i == current { dark.lighten(80%) },
    text(fill: dark)[state #i],
  )
  let gap(label) = stack(
    spacing: 3pt,
    explain(text(size: 0.8em, label)),
    sym.arrow.r.long,
  )
  // The caption of the join is a second row, so that it does not lift the frame
  // above the other states when the first row is centred vertically.
  grid(
    columns: 5,
    align: center + horizon,
    column-gutter: 6pt,
    row-gutter: 4pt,
    node(0),
    gap[a press],
    node(1),
    gap[a press],
    box(stroke: guide, inset: 4pt, grid(
      columns: 3,
      align: center + horizon,
      column-gutter: 6pt,
      node(2), gap[`hold: 0`], node(3),
    )),
    grid.cell(x: 4, explain(text(
      size: 0.8em,
    )[a join, crossed by one press either way])),
  )
}

#explained-slide(
  notes: (
    [The next press starts a move that takes four seconds.],
    [A press while the move is still running overtakes it rather than cutting it short.],
    [`hold: 0` brings state 3 up at the same time as state 2, so the deck does not stop here.],
    [One press forward ran through the join, and one press back returns over it to state 1.],
  ),
  animation: {
    import anim: *
    // A duration may run past the subslide it is in. Stepping on while the slow move is
    // still running overtakes it rather than cutting it short.
    sub(move("slow", dx: 8cm, duration: 4))
    // `hold: 0` starts the next state at the same time as this one, so the deck does not
    // stop between them, and one press back returns over both.
    sub(hold: 0, reveal("joined"))
    sub(reveal("together"))
  },
)[
  = Durations and Joins

  #tag("slow")[#text(fill: orange)[*A slow move of four seconds*]]

  #[
    #set text(fill: teal, weight: "bold")
    #tag("joined")[State 2 comes up with a press,]
    #tag("together")[and state 3 comes up with it.]
  ]

  #v(1fr)

  // `per-subslide` lays the diagram out once per state, which costs no rendering of the body.
  #align(center, per-subslide(it => join-diagram(it.number - 1)))

  #v(1fr)
]
