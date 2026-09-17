// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The placement benchmark deck: one slide covered in placed marks,
// in the four shapes that say what the automatic canvas costs.
//
// The canvas of a slide is the union of its body and of every `#place`d element on it,
// and animo computes that union only on a slide whose timeline pans.
// The union is the one part of laying out a slide whose cost grows with how much the body
// draws, so a slide of many marks is where it becomes visible.
// This deck measures what computing it costs, and what a stated canvas and a single image
// save against it.
//
// Every variant draws the same marks in the same order and holds the same number of states,
// so a pair of runs differs in the one knob that is turned and in nothing else.
//
// The knobs, as `--input`:
//
// | Input    | Default | Meaning                                                      |
// | -------- | ------- | ------------------------------------------------------------ |
// | `points` | 10000   | marks the slide carries                                      |
// | `states` | 20      | states of the slide, which is one continuous step more       |
// | `pan`    | off     | the timeline pans, which is what reads the canvas            |
// | `canvas` | auto    | `stated` gives the slide its canvas, leaving nothing to sum  |
// | `marks`  | place   | `image` draws the same marks as one SVG element instead      |
//
// A number measured here means something only when the deck it was measured on is the same
// deck, so this file is meant to stay as it is.

#import "@preview/animo:0.1.0": *

#let flag(name, value) = sys.inputs.at(name, default: "") == value
#let number(name, fallback) = int(sys.inputs.at(name, default: str(fallback)))

#let npoints = number("points", 10000)
#let nstates = number("states", 20)
#let pans = flag("pan", "on")
#let stated = flag("canvas", "stated")
#let drawn = flag("marks", "image")

#let shape = (width: 16cm, height: 9cm, margin: 1cm)

// The area the marks are scattered over, which is wider and taller than the viewport,
// so that the canvas a pan reads is larger than the slide and the pan has somewhere to go.
#let spread = (width: 26cm, height: 14cm)

// The canvas the `stated` knob hands to the slide. It covers the spread, which is what a
// presentation author works out for themselves when they state one.
#let given = (width: 28cm, height: 16cm)

#show: animo.with(..shape)

// The colour of a mark, written once so that the placed marks and the drawn ones are the
// same ink. A colour name is not shared between typst and SVG, which spell some of them
// differently, so the SVG is given the hexadecimal form of this one.
#let ink = rgb("#0074d9")

// Where the marks sit, as fractions of the spread.
// The positions come from a linear congruential generator rather than from typst's own
// randomness, so that every variant and every machine draws the same scatter.
#let coords = {
  let seed = 12345
  let out = ()
  for _ in range(npoints) {
    seed = calc.rem(seed * 1103515245 + 12345, 2147483648)
    let x = calc.rem(seed, 10000) / 10000
    seed = calc.rem(seed * 1103515245 + 12345, 2147483648)
    let y = calc.rem(seed, 10000) / 10000
    out.push((x, y))
  }
  out
}

// The marks as one `#place` each, which is one element for typst to lay out per mark and
// one contribution to the union per mark.
#let placed = {
  for (x, y) in coords {
    place(
      dx: x * spread.width,
      dy: y * spread.height,
      circle(radius: 0.5mm, fill: ink, stroke: none),
    )
  }
}

// The same marks as one SVG image, which is a single element wherever it is placed.
// The `viewBox` is in millimetres of the spread, so the marks land where the placements
// put them.
#let drawing = place(dx: 0cm, dy: 0cm, image(
  bytes({
    let circles = coords.map(((x, y)) => (
      "<circle cx=\""
        + str(x * spread.width / 1mm)
        + "\" cy=\""
        + str(y * spread.height / 1mm)
        + "\" r=\"0.5\" fill=\""
        + ink.to-hex()
        + "\"/>"
    ))
    (
      "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 "
        + str(spread.width / 1mm)
        + " "
        + str(spread.height / 1mm)
        + "\">"
        + circles.join("")
        + "</svg>"
    )
  }),
  format: "svg",
  width: spread.width,
))

// The timeline, which carries the same number of states whichever knob is turned.
// Without `pan` the states move a tag instead, so that the two runs of a pair differ in
// what the viewport does and not in how many states the slide has.
#let timeline = {
  import anim: *
  for istate in range(1, nstates) {
    if pans {
      sub(pan(dx: 0.5cm * istate))
    } else {
      sub(move("mark", dx: 1mm * istate))
    }
  }
}

#slide(
  animation: timeline,
  canvas: if stated { given } else { auto },
)[
  = A Scatter of Marks

  #tag("mark")[The mark the continuous steps of this slide address.]

  #if drawn { drawing } else { placed }
]
