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
  sub(replace("square", transition: morph())[$ (a + b)^2 = a^2 + 2 a b + b^2 $])
})[
  = An Equation That Grows

  // A letter that changes size gets another glyph, so the morph matches the ones that keep
  // their size and fades the others.
  #tag("square")[$ (a + b)^2 $]
]
