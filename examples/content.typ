// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The structural primitives, which change what typst lays out rather than how it is
// shown, and the region that lets a change push its surroundings around.

#import "@preview/animo:0.1.1": *

#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#show heading: set block(below: 1em)

#slide(animation: {
  import anim: *
  // `apply` takes functions, never named properties: animo does not look inside content,
  // so it cannot know which `set` rule a property would belong to.
  sub(apply("claim", text.with(fill: red)))
  // `replace` sets what is laid out and keeps the wrappers, so the replacement arrives
  // red. `handout: true` keeps this step, which `replace` would otherwise destroy.
  sub(handout: true, replace("claim")[
    This silly replacement keeps on rambling for ever and ever until it is long enough to wrap.
  ])
  // `reset` sets both back: the body as written, with every wrapper dropped.
  sub(reset("claim"))
})[
  = Replace, Apply and Reset

  // `wrap: block` because a short paragraph measures as inline, and a replacement that
  // is meant to wrap onto a second line needs a container width to wrap inside.
  #tag("claim", wrap: block)[A short line.]

  This paragraph stays where it is on every step:
  a tag whose content changes reserves the room of its largest state.
]

#slide(animation: {
  import anim: *
  // Inside a region a `remove` really frees space, and everything after it moves up.
  // Outside one it would free nothing, because the tag reserves its own box.
  sub(handout: true, remove("caveat"))
  sub(replace("claim")[
    A line looooooooooooooooooooooooooooooooooooooooooooong enough to take a second line of its own.
  ])
})[
  = Reflow Inside a Region

  #region[
    #tag("claim")[A short line that will soon get longer.]

    #tag("caveat")[A second line that goes away.]

    This paragraph moves when the two above it change.
  ]

  This paragraph is outside the region, and never moves.
]

#slide(handout: true, animation: {
  import anim: *
  // `reset` is what makes the word start out removed: it is not laid out at all until
  // this step, and the tag's own box keeps the room for it meanwhile.
  sub(reset("word"))
})[
  = Space That Is Reserved

  #block(inset: 0.4cm, stroke: rgb("#204080"))[
    This sentence contains a #tag("word")[hidden] word
    and reserves space for it.
  ]
]
