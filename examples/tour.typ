// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

#import "@preview/animo:0.1.0": *

// The deck's shape is written once, as a document-level show rule.
// It is also what emits the HTML page, its stylesheet and its runtime,
// and what sets the page size of the two paged outputs.
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#slide(numbered: false)[
  #set align(center + horizon)
  #text(size: 2em)[*Animo*]

  A slide is a viewport onto a canvas.
]

#slide[
  = The viewport

  The viewport is what the audience sees:
  one HTML slide container, one presentation page, one handout page.
  It is the size of the deck, and it clips.

  Whatever falls outside it is not carried over to a next slide.
]

#slide(background: rgb("#eef2ff"))[
  = A background

  A colour becomes the page fill on paper and a CSS background in the browser,
  because `set page` is unavailable in the HTML target.
]

#slide[
  = The canvas

  The canvas is what the body is laid out on.
  It is at least as large as the viewport, and the placement below makes it wider:
  the word after this paragraph sits four centimetres beyond the right edge,
  so it is on the canvas and not on the slide.

  #place(dx: 17cm, dy: 2cm)[Out of view, for now.]

  Panning brings it into view, and panning is what a later version adds.
]

#slide[
  = Placing things

  Animo has no header, footer or templating machinery.
  A recurring element is `#place` inside a wrapper around `#slide`.

  #place(bottom + right)[#text(size: 0.7em, fill: gray)[a placed corner mark]]
]
