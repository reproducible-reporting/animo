// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The structural primitives, which change what typst lays out rather than how it is
// shown, how they compose, and the epochs they introduce.

#import "@preview/animo:0.1.1": *
// The colors, the title slide, the styles and the slide wrapper that the demo decks share.
#import "_common.typ": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show: demo-style

#title-slide("structural.typ", "Structural Animations", "structural/")

#explained-slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    white,
    orange.lighten(85%),
    angle: 90deg,
  )),
  notes: (
    [The body lays out a short line, in a tag that reserves room for two lines.],
    [`apply` wraps the line in `text.with(fill: ..)`, which colors it.],
    [`replace` lays out a longer text, which arrives colored because the wrapper stays.],
    [`reset` lays out the body as written again, without the wrapper.],
  ),
  animation: {
    import anim: *
    // The uncover lifts the curtain of the title slide.
    init(uncover(direction: btt))
    // `apply` takes functions, never named properties: animo does not look inside content,
    // so it cannot know which `set` rule a property would belong to.
    sub(apply("claim", text.with(fill: orange)))
    // `replace` sets what is laid out and keeps the wrappers, so the replacement arrives colored.
    sub(replace("claim")[
      *This replacement is a good deal longer than the short line it replaces,
      so that it wraps onto a second line inside the room that the tag reserves.*
    ])
    // `reset` sets both back: the body as written, with every wrapper dropped.
    sub(reset("claim"))
  },
)[
  = Replace, Apply and Reset

  // `wrap: block` because a short paragraph measures as inline, and a replacement that
  // is meant to wrap onto a second line needs a container width to wrap inside.
  // The tagged text sets no fill, because a fill inside the tag would override
  // the fill that the wrapper of `apply` sets around it.
  #tag("claim", wrap: block)[*A short line.*]

  #explain[
    This paragraph stays where it is on every state,
    because a tag whose content changes reserves the room of its largest epoch.
  ]
]

#explained-slide(
  notes: (
    [The dashed frames mark the room that each tag reserves. The second tag starts removed.],
    [`replace` on an empty tag inserts content that the body does not hold.],
    [`reset` brings in the body of a tag that started removed.],
  ),
  animation: {
    import anim: *
    // Inserting content that is not in the body is `replace` on an empty tag.
    sub(replace("slot")[#text(fill: orange)[*inserted by the timeline*]])
    // Content that is in the body and starts out absent is a tag the timeline resets,
    // because a first content operation `reset` makes the tag start removed.
    sub(reset("later"))
  },
)[
  = Inserting Content

  // The frames sit outside the tags, so they show the box that each tag reserves.
  An empty tag receives #box(stroke: guide, tag("slot")[]) a replacement.

  A word in the body can #box(stroke: guide, tag("later")[#text(fill: teal)[*arrive later*]])
  with a `reset`.

  #v(1fr)

  #explain[
    An empty tag in the body and `replace` in the timeline insert content.
    A tag whose first content operation is `reset` starts removed.
  ]
]

// The states of the tag "x" on the next slide, as what is laid out and the wrappers around it.
#let laid-out = ([B], [B], [R], [R], [nothing], [S], [B], [B])
#let wrappers = (
  [none],
  [`emph`],
  [`emph`],
  [`emph` inside `strong`],
  [`emph` inside `strong`],
  [`emph` inside `strong`],
  [none],
  [none],
)

// One tag stepped through the rules of composition, with a panel that shows the two parts of
// the content of the tag, so the slide reads as the table of the manual.
#explained-slide(
  notes: (
    [The body lays out B, with no wrappers.],
    [`apply("x", emph)` adds a wrapper around B.],
    [`replace("x")[R]` lays out R, and the wrapper stays.],
    [`apply("x", strong)` adds a second wrapper, outside the first one.],
    [`remove("x")` lays out nothing, and both wrappers are kept.],
    [`replace("x")[S]` lays out S inside the two kept wrappers.],
    [`reset("x")` lays out the body again, without wrappers.],
    [`apply("x", emph), reset("x")` applies in order, so the reset wins.],
  ),
  animation: {
    import anim: *
    sub(apply("x", emph))
    sub(replace("x")[R])
    sub(apply("x", strong))
    sub(remove("x"))
    sub(replace("x")[S])
    sub(reset("x"))
    // Operations are applied in the order they are written, so the reset wins.
    sub(apply("x", emph), reset("x"))
  },
)[
  = How They Compose

  #grid(
    columns: (1fr, 1.4fr),
    align: center + horizon,
    box(stroke: guide, inset: 0.3cm, text(size: 5em, fill: orange, tag(
      "x",
    )[B])),
    // `per-subslide` lays the panel out once per state, which costs no rendering of the body.
    per-subslide(it => text(size: 1.2em, grid(
      columns: 2,
      align: (right, left),
      column-gutter: 0.4cm,
      row-gutter: 0.5cm,
      explain[laid out], text(fill: orange, strong(laid-out.at(it.number - 1))),
      explain[wrappers], wrappers.at(it.number - 1),
    ))),
  )

  #v(1fr)

  #explain[
    `replace` and `remove` set what is laid out and keep the wrappers,
    `apply` adds wrappers, and `reset` sets both.
  ]
]

#explained-slide(
  notes: (
    [The name `var` tags both sites of $x$ in the equation.],
    [`replace` gives every site of `var` the same replacement.],
    [A `replace` and a `move` in one subslide read as one movement.],
    [`apply` recolors the line, which stays where the `move` put it.],
  ),
  animation: {
    import anim: *
    // Every site of one name receives the same replacement.
    sub(replace("var", text(fill: orange, $y$)))
    // A change of content and a move in one subslide read as one movement,
    // because the leaving and the arriving rendering are moved alike.
    sub(replace("moved")[*A different line*], move("moved", dx: 6cm))
    // A structural primitive leaves the display state alone, so the tag stays moved.
    sub(apply("moved", text.with(fill: pink)))
  },
)[
  = Several Sites and a Move

  #text(size: 1.4em)[
    $
      f(#tag("var", text(fill: orange, $x$))) = #tag("var", text(fill: orange, $x$)) + 1
    $
  ]

  #explain[Both sites of `var` change together.]

  #v(0.5cm)

  // The fill is set outside the tag, so that the wrapper of `apply` can override it.
  #set text(fill: teal)
  #tag("moved")[*A short line*]
]

// The states of the next slide grouped by epoch, with the state on screen filled.
#let epoch-diagram(current) = {
  let node(i) = box(
    inset: 4pt,
    radius: 3pt,
    stroke: 0.8pt + dark,
    fill: if i == current { dark.lighten(80%) } else { white },
    text(fill: dark)[state #i],
  )
  let epoch(number, ..states) = box(
    stroke: guide,
    fill: white.transparentize(40%),
    radius: 3pt,
    inset: 5pt,
    stack(
      spacing: 5pt,
      explain(text(size: 0.8em)[epoch #number]),
      stack(dir: ltr, spacing: 5pt, ..states.pos().map(node)),
    ),
  )
  stack(dir: ltr, spacing: 0.4cm, epoch(0, 0, 1), epoch(1, 2, 3), epoch(2, 4))
}

#explained-slide(
  background: dark.lighten(92%),
  notes: (
    [The body as written is the first layout of the slide, which is epoch 0.],
    [`reveal` changes no content, so state 1 stays in epoch 0.],
    [`replace` starts epoch 1, so typst lays the slide out a second time.],
    [`move` changes no content, so state 3 shares epoch 1 with state 2.],
    [`remove` starts epoch 2, so typst lays this slide out three times in all.],
  ),
  animation: {
    import anim: *
    // A new epoch begins at every subslide that holds a structural primitive,
    // and typst lays the slide out again once per epoch.
    sub(reveal("a")) // state 1, epoch 0
    sub(replace("a")[#text(fill: orange)[*This replacement starts epoch 1.*]]) // state 2, epoch 1
    sub(move("a", dx: 1cm)) // state 3, epoch 1
    sub(remove("b")) // state 4, epoch 2
  },
)[
  = Epochs

  #tag("a")[#text(fill: orange)[*A line revealed, then replaced and moved.*]]

  #tag("b")[#text(fill: teal)[*A line removed in the last epoch.*]]

  #v(1fr)

  #align(center, per-subslide(it => epoch-diagram(it.number - 1)))

  #v(1fr)

  #explain[A new epoch begins at every subslide that holds a structural primitive.]
]

#explained-slide(
  notes: (
    [The dashed frames mark the room each tag reserves. The word starts removed.],
    [`reset` lays out the word in the room that was kept for it.],
    [`replace` lays out a longer phrase, as wide as the room that was kept for it.],
  ),
  animation: {
    import anim: *
    // `reset` is what makes the word start out removed: it is not laid out at all until
    // this subslide, and the box that the tag reserves keeps the room for it meanwhile.
    sub(reset("word"))
    // An inline tag is as wide as its widest epoch, so the line stays where it is.
    sub(replace("short")[#text(fill: teal)[*a much longer phrase*]])
  },
)[
  = Space That Is Reserved

  // The frames sit outside the tags, so they show the box that each tag reserves.
  This sentence contains a #box(stroke: guide, tag("word")[#text(fill: orange)[*hidden*]]) word
  and reserves space for it.

  A #box(stroke: guide, tag("short")[#text(fill: teal)[*short*]]) phrase on a line reserves
  the width of its longest epoch.

  #v(1fr)

  // A tag between paragraphs fills the width of its container and is as tall as its
  // tallest epoch, so a replacement that wraps reflows inside that height.
  #explain[
    The rest of the slide does not move, because a tag reserves room for its largest content.
    Starting removed and starting hidden look the same inside a reserved box.
  ]
]

#explained-slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(
    pale,
    white,
    angle: 90deg,
  )),
  notes: (
    [Each of the next two states replaces one answer, which the browser animates.],
    [`duration: 2` dissolves the first answer slowly into the second.],
    [`duration: 0` swaps the content at once, which is a hard cut.],
  ),
  animation: {
    import anim: *
    // A structural step is a dissolve of the tag site, with the `delay:` and `duration:`
    // of the primitive that changes it. The transition `crossfade()` is the default.
    sub(replace("slow", duration: 2, transition: crossfade())[#text(
      fill: orange,
    )[*The second answer.*]])
    // A duration of zero swaps the content at once, which is a hard cut.
    sub(replace("cut", duration: 0)[#text(fill: orange)[*The second answer.*]])
  },
)[
  = What a Structural Step Looks Like

  #set text(fill: dark)
  #tag("slow")[*The first answer.*] #h(
    1fr,
  ) #explain[a slow dissolve, `duration: 2`]

  #tag("cut")[*The first answer.*] #h(1fr) #explain[a hard cut, `duration: 0`]

  #v(1fr)

  // Content that only shifts would smear in a dissolve. A region or a morph avoids that,
  // as the pages Regions and Morphs explain.
  #explain[
    Neither content travels to meet the other.
    The old one fades out where the new one fades in.
  ]
]
