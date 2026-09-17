// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The controlled benchmark deck: one slide shape, with every axis of the cost model
// turned into a knob, so that a term of that model is the difference between two runs
// rather than a guess about where the time went.
//
// A number here means something only when the deck it was measured on is the same deck,
// so this file is meant to stay as it is. Realism is `examples/tour.typ`'s job;
// this file's job is to hold everything constant except one axis at a time.
//
// The knobs, as `--input`:
//
// | Input      | Default | Meaning                                                    |
// | ---------- | ------- | ---------------------------------------------------------- |
// | `slides`   | 12      | slides in the deck                                         |
// | `states`   | 0       | continuous steps per slide, which add states, not epochs   |
// | `epochs`   | 1       | epochs per slide, one structural step less                 |
// | `regions`  | 0       | explicit regions per slide, 0 leaving the implicit ones    |
// | `height`   | auto    | a length given to every region, which skips its measuring  |
// | `figure`   | off     | a region holds a cetz canvas instead of a paragraph        |
// | `overlay`  | off     | every slide carries the same overlay, which is content     |
// | `number`   | off     | that overlay also numbers the subslide it is shown on      |
// | `plain`    | off     | lay the same content out as plain typst, one page a slide  |
//
// One more line is not a knob but a handle: `revision` below is rewritten in place to
// measure what `typst watch` recompiles after an edit that touches exactly one slide.
//
// `plain` is the floor the overhead factor divides by. It is the same content, laid out by
// typst with animo out of the way: `tag` and `region` become the plainest containers that
// hold the same ink, and the timeline is not built at all. The content itself is written
// once, as a function of those two, so the two drivers cannot drift apart.

#import "@preview/animo:0.1.0": *
#import "@preview/cetz:0.5.2"

#let flag(name) = sys.inputs.at(name, default: "off") == "on"
#let number(name, fallback) = int(sys.inputs.at(name, default: str(fallback)))

#let nslides = number("slides", 12)
#let nstates = number("states", 0)
#let nepochs = number("epochs", 1)
#let nregions = number("regions", 0)
#let height = sys.inputs.at("height", default: "auto")
#let height = if height == "auto" { auto } else { eval(height) }
#let figure = flag("figure")
#let overlay = flag("overlay")
#let number = flag("number")
#let plain = flag("plain")

#let shape = (width: 16cm, height: 9cm, margin: 1cm)

// The handle a live-preview measurement edits. It is shown on the first slide and nowhere
// else, so rewriting it is an edit of one slide's ink, which is the everyday authoring
// edit and the one whose recompile time an author feels.
#let revision = ""

// The names the timeline addresses. A slide's tags are numbered within the slide,
// because a name means nothing outside the slide it sits in.
#let claim(iregion) = "claim" + str(iregion)
#let bullet(istate) = "bullet" + str(istate)
#let term = "term"

// The text a region holds, long enough to wrap and to reflow when it changes.
#let prose(iregion, iepoch) = [
  Region #(iregion + 1) is showing the content of epoch #(iepoch + 1), which is a
  paragraph long enough to break over more than one line, so that replacing it really
  does relay the lines out rather than swapping one word for another.
]

// A cetz canvas, which is the most expensive thing a region can hold:
// inside a region it is laid out afresh in every epoch.
#let canvas(iregion, iepoch) = cetz.canvas({
  import cetz.draw: *
  for i in range(6) {
    let angle = 60deg * i
    line((0, 0), (3 * calc.cos(angle), 1.5 * calc.sin(angle)), stroke: 0.4pt)
  }
  circle((0, 0), radius: 1.2, stroke: 0.6pt)
  content((0, -1.8), [epoch #(iepoch + 1) of region #(iregion + 1)])
})

#let held(iregion, iepoch) = if figure { canvas(iregion, iepoch) } else {
  prose(iregion, iepoch)
}

// What every slide of the deck carries in front of everything, when the knob asks for it.
//
// A deck gives every slide the same overlay, which is what makes its cost a per-slide term
// rather than a one-off: in the HTML target each is a frame of its own, with glyph
// definitions of its own, beside the epoch frames of the slide.
// It is one line of text and one rule, which is what a running header or a talk title is,
// and deliberately not an image: an image would measure the image rather than the layer.
//
// With `number` it also carries a slide and subslide number, which is the one thing in a
// layer that is not one rendering per slide: a stack holds one rendering per state, so the
// knob measures what a number finer than a slide number costs where it belongs.
#let banner = {
  place(bottom + left, line(length: 100%, stroke: 0.4pt))
  place(bottom + right, dy: -2mm, text(size: 9pt, {
    [The scaling deck, a controlled benchmark]
    if number {
      context [ #h(4mm) #slide-number()/#slide-count()]
      per-subslide(it => [ (#it.number/#it.count)])
    }
  }))
}

// One slide's body, as a function of the two containers that animo provides and that the
// plain driver stands in for. Everything the deck lays out is written here and nowhere
// else, so that the animo run and the plain run differ in the machinery and not in the ink.
#let body(islide, tag: tag, region: region) = {
  heading(level: 1)[Slide #(islide + 1)]

  if islide == 0 { [Revision #revision of this deck.] }

  [
    An ordinary paragraph of running text, with #tag("inline")[a tagged phrase] inside it,
    so that every slide carries at least one inline tag site and one wrapped paragraph.
  ]

  // The display equation is here rather than behind a knob: math is what a deck of this
  // kind is full of, and a tag inside one is a tag site of its own kind.
  $
    integral_(-oo)^oo e^(-x^2) dif x = #tag(term)[$sqrt(pi)$]
  $

  // The regions, each laid out once per epoch. With none of them, the structural steps
  // land on bare tags instead, which is the implicit region and the cheaper half of the
  // same mechanism.
  for iregion in range(nregions) {
    region(height: height)[
      #tag(claim(iregion))[#held(iregion, 0)]
    ]
  }
  // The tag is laid out whether or not the timeline changes it, so that a variant with one
  // epoch holds the same ink as one with four and the difference between them is the epochs
  // and nothing else. A tag whose content never changes reserves no footprint and is not
  // measured, which is exactly the control the comparison needs.
  if nregions == 0 {
    tag(claim(0))[#held(0, 0)]
  }

  // The continuous steps. These are states within one epoch, so they cost the HTML target
  // nothing beyond the plan they travel in, and the static presentation a page each.
  for istate in range(nstates) {
    tag(bullet(istate))[Step #(istate + 1) of this slide.]
  }
}

// The timeline of one slide: the continuous steps first, then the structural ones,
// so that a variant that asks for both keeps the two runs of states apart.
#let timeline(islide) = {
  import anim: *
  for istate in range(nstates) {
    sub(reveal(bullet(istate)), move(bullet(istate), dx: 2mm * istate))
  }
  for iepoch in range(1, nepochs) {
    let names = if nregions == 0 { (0,) } else { range(nregions) }
    sub(..names.map(iregion => replace(
      claim(iregion),
      held(iregion, iepoch),
    )))
  }
}

#if plain {
  // The floor: the same content, with the plainest containers that hold the same ink.
  // `tag` becomes what its wrapper would have been and `region` a filling block, so the
  // pages hold the same glyphs in the same order. What they do not hold is animo:
  // no plan, no per-epoch rendering, no footprint measurement.
  let plain-tag(name, body, hidden: false, removed: false, wrap: auto) = {
    if removed { none } else if hidden { std.hide(body) } else { body }
  }
  let plain-region(body, width: auto, height: auto, ..rest) = block(
    width: 100%,
    height: height,
    body,
  )
  set page(width: shape.width, height: shape.height, margin: shape.margin)
  for islide in range(nslides) {
    if islide > 0 { pagebreak() }
    body(islide, tag: plain-tag, region: plain-region)
  }
} else {
  show: animo.with(..shape)
  for islide in range(nslides) {
    slide(
      body(islide),
      animation: timeline(islide),
      overlay: if overlay { banner },
    )
  }
}
