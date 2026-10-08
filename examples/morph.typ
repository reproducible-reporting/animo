// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The morph, which carries what two versions of a region share to its new place and fades
// only what differs. It is a transition of the structural primitive that changes the region.

#import "@preview/animo:0.1.1": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show heading: set block(below: 1em)

#slide(animation: {
  import anim: *
  // Two operations that change one region at one boundary name the same transition.
  sub(
    replace("aside", transition: morph())[and a clause inserted near the start],
    apply("word", text.with(fill: red), transition: morph()),
  )
  // A morph runs backwards as well, and so does a step back over it.
  sub(
    reset("aside", transition: morph()),
    reset("word", transition: morph()),
  )
})[
  = A Paragraph That Reflows

  // The letters are matched one by one, so a paragraph needs no tags to morph.
  // `wrap: none` lets the insertion push the rest of the paragraph along, which is what a
  // region around the paragraph is for.
  #region[
    The quick brown fox #tag("aside", wrap: none)[] jumps over the
    #tag("word", wrap: none)[lazy] dog, and every word after the insertion moves to its
    new place, across the end of a line where it has to.
  ]
]

#slide(animation: {
  import anim: *
  sub(replace("size", transition: morph())[small, solid and blue])
})[
  = Shapes in a Paragraph

  // A shape is matched by its geometry, as a letter is by its shape, so a box and a small
  // figure keep their place among the words.
  #region[
    A #tag("size", wrap: none)[small] box #box(width: 0.8cm, height: 0.35cm, fill: blue)
    and a figure #box(baseline: 20%, stack(
      dir: ltr,
      spacing: 3pt,
      circle(radius: 0.2cm, fill: red),
      polygon.regular(size: 0.45cm, vertices: 3, fill: green),
      line(start: (0cm, 0.4cm), end: (0.5cm, 0cm), stroke: 2pt + gray),
    ))
    move with the words around them when the paragraph reflows, and a fraction $a/b$
    moves as well, because its bar keeps its length.
  ]
]

#slide(animation: {
  import anim: *
  sub(
    replace("left")[a few words more,],
    replace("right", transition: morph())[a few words more,],
  )
})[
  = Crossfade and Morph

  #grid(
    columns: (1fr, 1fr),
    column-gutter: 1cm,
    region[
      *Crossfade.* This text, with #tag("left", wrap: none)[] shifts behind a dissolve,
      where two copies of every shifted word overlap halfway through.
    ],
    region[
      *Morph.* This text, with #tag("right", wrap: none)[] shifts by moving, where each
      shifted letter travels to its new place.
    ],
  )
]

#slide(animation: {
  import anim: *
  sub(replace("square", transition: morph())[$ (a^2 + 2 a b + b^2) / 2 $])
})[
  = An Equation That Grows

  // A letter that changes size gets another glyph, so the morph matches the ones that keep
  // their size and fades the others. The bar of the fraction keeps its commands and changes
  // its length, so it is resized and widens under the longer numerator.
  #tag("square")[$ (a + b)^2 / 2 $]
]

#slide(animation: {
  import anim: *
  sub(replace(
    "words",
    transition: morph(),
  )[a few more words, which it grows around])
})[
  = A Box That Grows

  // The box keeps its commands when its size changes, so it is resized rather than faded.
  // Its corners keep their radius on the way, and the words it holds move as letters do.
  #region[
    #box(fill: aqua, stroke: 1pt + blue, radius: 6pt, inset: 8pt)[
      A box with #tag("words", wrap: none)[a few words]
    ]
  ]
]
