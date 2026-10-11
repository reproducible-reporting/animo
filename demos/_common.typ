// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The colors, the title slide, the styles and the slide wrapper that the demo decks share.
// This file is not a deck, so `tools/build_demos.py` skips it,
// as it skips every file under `demos/` whose name starts with an underscore.
// A deck imports it with `#import "_common.typ": *` and applies the styles with
// `#show: demo-style`.

#import "@preview/animo:0.2.0": *

// The colors of the logo and of the documentation site, and a dark gray for text and rules.
// The names `teal` and `orange` shadow the colors of the same name that typst predefines.
#let teal = rgb("#008ba8")
#let orange = rgb("#c9600a")
#let pink = rgb("#d63c96")
#let dark = rgb("#2e3338")

// The fill behind inline code, which a few figures reuse as a pale teal.
#let pale = teal.lighten(88%)

// The show rules of the decks.
// They are a template function rather than top-level `show` rules,
// because a show rule in an imported file does not reach the file that imports it.
#let demo-style(body) = {
  show heading: set block(below: 1em)
  show heading: set text(fill: dark)
  show raw.where(block: false): it => highlight(
    fill: pale,
    stroke: pale + 0.1cm,
    radius: 0.1cm,
    it,
  )
  body
}

// Gray italics mark the text that explains a slide,
// so that it stands apart from the colored subjects that a timeline addresses.
#let explain(body) = text(fill: luma(110), style: "italic", body)

// A thin gray mark for the places a timeline refers to, which the body draws but never animates.
#let guide = (paint: luma(150), thickness: 0.5pt, dash: "dashed")

// The number of the state on screen, with one dot per state and the dot of that state filled.
// A slide with a single state shows no counter.
// With `handout-badge: true`, a badge beside the counter marks every state that the handout keeps.
// The `handout` key is the same in every output type,
// so the HTML presentation and the static presentation show the badge on the states
// that the handout keeps.
// The handout leaves the badge out, because every page of it would carry one.
#let state-counter(handout-badge: false) = per-subslide(it => context text(
  size: 0.75em,
  fill: dark,
)[
  // A state without the badge hides it rather than omitting it,
  // because the stack reserves the width of the widest rendering
  // and starts every rendering at its left edge,
  // so a rendering without the badge would put the counter further left.
  #if handout-badge {
    let badge = box(
      fill: dark,
      inset: (x: 3pt, y: 2pt),
      radius: 2pt,
      text(fill: white)[handout],
    )
    if it.handout and output-type() != "handout" { badge } else { hide(badge) }
  }
  // A handout page carries the number of the state it kept,
  // which is the state that the presentation showed.
  #if it.count > 1 [
    state #(it.number - 1)
    #for i in range(it.count) {
      box(circle(
        radius: 2.5pt,
        stroke: 0.6pt + dark,
        fill: if i == it.number - 1 { dark },
      ))
    }
  ]
])

// The note for the state on screen, from an array that holds one note per state.
#let state-note(notes) = per-subslide(it => {
  assert.eq(notes.len(), it.count, message: "one note per state")
  explain(text(size: 0.85em, notes.at(it.number - 1)))
})

// A thin bar along the bottom edge of the viewport, which grows with every state of the deck.
// `step` and `steps` count every state of every slide, so the bar advances once per step.
// The stack of renderings says `wrap: block`, because a width given as a ratio
// needs a container width to be a ratio of.
// See the deck `numbering.typ` for a slide-by-slide explanation.
#let progress-bar = place(bottom, per-subslide(
  it => {
    let done = if it.steps > 1 { (it.step - 1) / (it.steps - 1) } else { 1 }
    stack(
      dir: ltr,
      rect(width: 100% * done, height: 3pt, fill: dark, stroke: none),
      rect(
        width: 100% * (1 - done),
        height: 3pt,
        fill: dark.lighten(80%),
        stroke: none,
      ),
    )
  },
  wrap: block,
))

// The wrapper that the decks write their slides with.
// Its overlay names the state on screen in the bottom right corner,
// shows the note for that state, if the slide passes one per state, in the bottom left,
// and draws the progress bar along the bottom edge.
// `per-subslide` lays its callback out once per state, and the browser shows the rendering
// of the state on screen, so a page of the static presentation explains itself as well.
// The overlay is laid out in a box the size of the viewport, so all three land in the margin.
#let explained-slide(
  body,
  notes: none,
  handout-badge: false,
  ..arguments,
) = slide(
  overlay: {
    place(
      bottom + right,
      dx: -0.4cm,
      dy: -0.35cm,
      state-counter(handout-badge: handout-badge),
    )
    if notes != none {
      place(bottom + left, dx: 1cm, dy: -0.35cm, state-note(notes))
    }
    progress-bar
  },
  ..arguments,
  body,
)

// A theatre curtain as wide as the viewport, which hangs from the top edge.
// Its hem is a row of scallops shaped like the hem of the logo,
// and each fold of the fill ends in one scallop.
// The scallop of the logo is 6 units wide and the gap to the next one is 4/3 units.
// With `trim`, a cord of that color runs along the hem.
#let curtain(color, width: 16cm, height: 8cm, folds: 11, trim: none) = {
  let pitch = width / folds
  let gap = pitch * (4 / 3) / (6 + 4 / 3)
  // As in the logo, the control points of a scallop lie two thirds of its width below the
  // line where it starts, and the cubic curve reaches three quarters of that depth.
  let depth = (pitch - gap) * 2 / 3
  let top = height - depth * 3 / 4
  let hem = for i in range(folds).rev() {
    let left = i * pitch + gap / 2
    let right = left + pitch - gap
    (
      curve.line((right, top)),
      curve.cubic((right, top + depth), (left, top + depth), (left, top)),
    )
  }
  // A fold is dark in the crease at either side and catches the light left of its middle,
  // because the light falls on the curtain from the left.
  let fold = gradient.linear(
    (color.darken(20%), 0%),
    (color, 12%),
    (color.lighten(8%), 30%),
    (color, 60%),
    (color.darken(20%), 100%),
  )
  place(curve(
    fill: fold.repeat(folds),
    stroke: none,
    curve.move((0cm, 0cm)),
    curve.line((width, 0cm)),
    curve.line((width, top)),
    ..hem,
    curve.line((0cm, top)),
    curve.close(),
  ))
  if trim != none {
    place(curve(
      stroke: 1.5pt + trim,
      curve.move((width, top)),
      ..hem,
      curve.line((0cm, top)),
    ))
  }
}

// The address of the documentation site, without the scheme that a reader need not type.
#let site = "reproducible-reporting.github.io/animo/"

// The title slide of a demo deck, with the name of its source file on a curtain.
// Below the name, the title slide links to the page of the Presentation Author Guide
// that explains the features the deck demonstrates.
// `page` is the title of that guide page and `path` is its address relative to `site`.
// The slide after it enters with `anim.uncover(direction: btt)`,
// which lifts the curtain out of view and shows that slide in place behind it.
// The stage floor below the curtain is dark, as in a theatre.
// Each cord is a darker shade of the fabric it runs along.
#let title-slide(name, page, path) = slide(numbered: false, background: {
  place(rect(width: 100%, height: 100%, fill: dark))
  curtain(teal, height: 8.5cm, trim: teal.darken(40%))
  // The valance hides the top of the curtain, as in a theatre.
  curtain(orange, height: 1cm, folds: 22, trim: orange.darken(40%))
})[
  // The text sits in the body rather than in the background,
  // because in the browser the body lies on top of the background and receives the click
  // on the link.
  #set align(center)
  #set text(fill: white)
  #v(0.5cm)
  // The badge takes the color of the text, which is white here.
  #made-with-animo(height: 2cm)
  #v(0.3cm)
  #text(size: 2em, raw(name, block: true))
  #v(0.1cm)
  #set text(size: 0.85em, fill: white.transparentize(20%))
  _A demo of the features explained on the page "#page" \
  of the Presentation Author Guide_
  #v(0.1cm)
  // Plain text rather than inline code, because the decks highlight inline code on a pale fill.
  #link("https://" + site + path, underline(site + path))
]
