// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The smallest deck that animates: one slide, one tag, one step.

#import "@preview/animo:0.1.0": *

// The shape of the deck is a document-level show rule, written once.
// It is also what emits the HTML page, its stylesheet and its runtime,
// and what gives the two paged outputs their page size.
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

// Style inline code
#let bgrb = rgb("#ddeeff")
#show raw.where(block: false): it => highlight(
  fill: bgrb,
  stroke: bgrb + 0.1cm,
  radius: 0.1cm,
  it,
)

#slide(animation: {
  // The timeline vocabulary is imported inside this block, in the style of cetz.
  // The import is scoped to the block, so `hide`, `move` and `scale` still mean
  // typst's own elements everywhere else, the slide body included.
  import anim: *
  sub(reveal("punchline"))
})[
  = Hello Animo!

  The body holds the slide contents and tags parts to be animated.

  // This tag starts out laid out, taking its space, and invisible, because the first
  // thing the timeline does to it is `reveal`. Nothing at the site says so.
  #tag("punchline")[
    The `animation` argument controls when and how those parts appear, move or change.
  ]
]
