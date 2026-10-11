// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The morph, which carries what two versions of a region share to its new place and fades
// only what differs. It is a transition of the structural primitive that changes the region.
// The static output types show one state per page, so the notes say what the browser does.

#import "@preview/animo:0.1.1": *
// The colors, the title slide, the styles and the slide wrapper that the example decks share.
#import "_common.typ": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show: example-style

#title-slide("morph.typ")

#explained-slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    white,
    pale,
    angle: 90deg,
  )),
  notes: (
    [The body has an empty tag after "fox", in a region around the paragraph.],
    [The clause fades in, and every letter after it travels to its new place.],
    [`reset` removes the clause again, and the morph plays the same motion backwards.],
  ),
  animation: {
    import anim: *
    // The uncover lifts the curtain of the title slide.
    init(uncover(direction: btt))
    // Two operations that change one region at one boundary name the same transition.
    sub(
      replace("aside", transition: morph())[#text(
        fill: orange,
      )[*and a clause inserted*]],
      apply("word", text.with(fill: teal), transition: morph()),
    )
    // A morph runs backwards as well, and so does a step back over it.
    sub(
      reset("aside", transition: morph()),
      reset("word", transition: morph()),
    )
  },
)[
  = A Paragraph That Reflows

  // `wrap: none` lets the insertion push the rest of the paragraph along, which is what a
  // region around the paragraph is for.
  #region[
    #set text(size: 1.2em)
    The quick brown fox #tag("aside", wrap: none)[] jumps over the
    #tag("word", wrap: none)[lazy] dog, and every word after the insertion moves to its
    new place, across the end of a line where it has to.
  ]

  #v(1fr)

  #explain[
    The morph matches the letters one by one, so a paragraph needs no tags to morph.
    Only the inserted clause fades in, and the word "lazy" changes color on its way.
  ]
]

#explained-slide(
  notes: (
    [A box, a small figure and the bar of a fraction sit among the words of one region.],
    [The shapes travel with the words around them when the paragraph reflows.],
  ),
  animation: {
    import anim: *
    sub(replace("size", transition: morph())[#text(
      fill: orange,
    )[*small, solid and dark*]])
  },
)[
  = Shapes in a Paragraph

  #region[
    #set text(size: 1.2em)
    A #tag("size", wrap: none)[small] box #box(width: 0.8cm, height: 0.35cm, fill: dark)
    and a figure #box(baseline: 20%, stack(
      dir: ltr,
      spacing: 3pt,
      circle(radius: 0.2cm, fill: orange),
      polygon.regular(size: 0.45cm, vertices: 3, fill: teal),
      line(start: (0cm, 0.4cm), end: (0.5cm, 0cm), stroke: 2pt + pink),
    ))
    move with the words around them when the paragraph reflows, and a fraction $a/b$
    moves as well, because its bar keeps its length.
  ]

  #v(1fr)

  #explain[
    The morph matches a shape by its geometry, as it matches a letter by its glyph.
    Letters and shapes form one sequence in reading order, so each shape keeps its place.
  ]
]

// A column of the next slide, as a tinted panel with a title above the region it holds.
#let panel(color, title, body) = block(
  width: 100%,
  fill: color.lighten(90%),
  stroke: 0.8pt + color,
  radius: 3pt,
  inset: 0.3cm,
)[
  #text(fill: color)[*#title*]
  #region(body)
]

#explained-slide(
  notes: (
    [Both panels insert the same words, with `duration: 1.5` to make the motion easy to follow.],
    [On the left, two copies of each shifted word overlap. On the right, each letter travels.],
  ),
  animation: {
    import anim: *
    // `crossfade()` is the default transition, so the left panel names none.
    sub(
      replace("left", duration: 1.5)[#text(fill: orange)[*a few words more,*]],
      replace("right", duration: 1.5, transition: morph())[#text(
        fill: orange,
      )[*a few words more,*]],
    )
  },
)[
  = Crossfade and Morph

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 0.8cm,
    panel(dark, [`crossfade()`, the default])[
      This text, with #tag("left", wrap: none)[] shifts behind a dissolve,
      where two copies of every shifted word overlap halfway through.
    ],
    panel(teal, [`morph()`])[
      This text, with #tag("right", wrap: none)[] shifts by moving,
      where each shifted letter travels to its new place.
    ],
  )

  #v(1fr)

  #explain[
    A crossfade dissolves the old version of the region into the new version.
    A morph moves the content that both versions share, and fades only the rest.
  ]
]

// The two variables of the next slide, each in a color of its own,
// so that the eye can follow them to their new places.
#let va = text(fill: orange, $a$)
#let vb = text(fill: teal, $b$)

#explained-slide(
  notes: (
    [The tag holds the whole equation.],
    [The letters that keep their size travel, and the bar of the fraction widens.],
  ),
  animation: {
    import anim: *
    sub(replace("square", transition: morph())[$
      (#va^2 + 2 #va #vb + #vb^2) / 2
    $])
  },
)[
  = An Equation That Grows

  #v(1fr)

  #text(size: 2em, tag("square")[$ (#va + #vb)^2 / 2 $])

  #v(1fr)

  #explain[
    A letter that changes size gets another glyph, so the morph fades it.
    The bar of the fraction keeps its commands and changes its length, so the morph resizes it.
  ]
]

#explained-slide(
  notes: (
    [The box holds a tag with a few words.],
    [The box grows around the new words, and its corners keep their radius.],
  ),
  animation: {
    import anim: *
    sub(replace("words", transition: morph())[#text(
      fill: orange,
    )[*a few more words, which it grows around*]])
  },
)[
  = A Box That Grows

  #v(1fr)

  #region[
    #set text(size: 1.4em)
    #box(
      fill: orange.lighten(85%),
      stroke: 1.5pt + orange,
      radius: 8pt,
      inset: 10pt,
    )[A box with #tag("words", wrap: none)[#text(fill: orange)[*a few words*]]]
  ]

  #v(1fr)

  #explain[
    The box keeps its commands when its size changes, so the morph resizes it rather than
    fading it. The words inside the box move as the letters of a paragraph do.
  ]
]

// A star of five points, as a polygon of ten corners around the middle of its box.
#let star(size, fill) = polygon(
  fill: fill,
  ..range(10).map(i => {
    let angle = -90deg + i * 36deg
    let radius = if calc.even(i) { size / 2 } else { size / 5 }
    (size / 2 + radius * calc.cos(angle), size / 2 + radius * calc.sin(angle))
  }),
)

// An arrow pointing right, as a polygon in a box of the given size.
#let arrow(size, fill) = polygon(
  fill: fill,
  (0pt, 0.4 * size),
  (0.65 * size, 0.4 * size),
  (0.65 * size, 0.2 * size),
  (size, 0.5 * size),
  (0.65 * size, 0.8 * size),
  (0.65 * size, 0.6 * size),
  (0pt, 0.6 * size),
)

// The color of the rectangle on the next slide, which turns pink as it gets rounded corners.
#let gold = rgb("#c08a00")

#explained-slide(
  background: pink.lighten(90%),
  notes: (
    [Each of the five tags holds exactly one shape.],
    [Each shape turns into the new shape, and its fill and stroke change on the way.],
    [`reset` turns every shape back into the shape of the body.],
  ),
  animation: {
    import anim: *
    sub(
      replace("square", transition: morph())[#circle(
        radius: 1cm,
        fill: dark,
      )],
      replace("star", transition: morph())[#polygon.regular(
        size: 2cm,
        vertices: 5,
        fill: orange,
      )],
      replace("arrow", transition: morph())[#line(
        start: (0cm, 1cm),
        end: (2cm, 1cm),
        stroke: 3pt + pink,
      )],
      replace("filled", transition: morph())[#circle(
        radius: 1cm,
        stroke: 3pt + teal,
      )],
      replace("corners", transition: morph())[#rect(
        width: 2cm,
        height: 1.2cm,
        radius: 0.3cm,
        fill: pink,
      )],
    )
    sub(
      ..("square", "star", "arrow", "filled", "corners").map(name => reset(
        name,
        transition: morph(),
      )),
    )
  },
)[
  = Shapes That Change Their Outline

  #v(1fr)

  // The captions sit outside the tags, so they stay put while the shapes change.
  #region[
    #grid(
      columns: 5,
      column-gutter: 0.8cm,
      row-gutter: 0.4cm,
      align: center + horizon,
      tag("square")[#square(size: 2cm, fill: dark)],
      tag("star")[#star(2cm, orange)],
      tag("arrow")[#arrow(2cm, pink)],
      tag("filled")[#square(size: 2cm, fill: teal)],
      tag("corners")[#rect(width: 2cm, height: 1.2cm, fill: gold)],
      ..(
        [square to circle],
        [star to pentagon],
        [arrow to line],
        [fill to stroke],
        [rounded corners],
      ).map(it => explain(text(size: 0.8em, it))),
    )
  ]

  #v(1fr)

  #explain[
    A tag that holds one shape before the step and one after it turns the one into the other,
    whatever their outlines.
  ]
]

// A box with `clip: true` that holds more than fits, so that its edges cut its content.
#let clipped = box(
  width: 3.5cm,
  height: 1cm,
  clip: true,
  fill: pink.lighten(85%),
  stroke: 0.8pt + pink,
  inset: 0.2cm,
)[
  #text(fill: pink)[A clipped box cuts off this text at its edges.]
]

#explained-slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    white,
    orange.lighten(85%),
    angle: 90deg,
  )),
  notes: (
    [Both rows hold the same clipped box. Only the lower box sits inside a tag.],
    [Words push both boxes along. The upper text fades, and the lower box travels as one piece.],
  ),
  animation: {
    import anim: *
    // One name with a site in each row inserts the same words in both regions.
    sub(replace("before", transition: morph())[#text(
      fill: orange,
    )[*pushed along by these words*]])
  },
)[
  = A Tag Moves as One

  #v(1fr)

  #grid(
    columns: (auto, 1fr),
    column-gutter: 0.6cm,
    row-gutter: 0.8cm,
    align: horizon,
    text(fill: dark)[*Without a tag*],
    // The morph does not move the edges of a clipped box along with what it moves inside
    // the box, so the content of a clipped box that moves fades.
    region[#tag("before", wrap: none)[] #clipped],

    text(fill: dark)[*With a tag*],
    // A tag around the clipped box carries the box and its content as one.
    region[#tag("before", wrap: none)[] #tag("carried")[#clipped]],
  )

  #v(1fr)

  #explain[
    The morph leaves the edges of a clipped box where typst laid them out,
    so it fades the content of a clipped box that moves.
    A tag around the box carries the box and its content as one piece.
  ]
]
