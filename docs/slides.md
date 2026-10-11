---
description: >-
  The show rule that gives a deck its shape, the arguments of a slide,
  and the two layers around its body.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Slides

The demo deck for this page is
[`slides.typ`](https://github.com/reproducible-reporting/animo/blob/main/demos/slides.typ)
([HTML](https://reproducible-reporting.github.io/animo/demos/slides.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/demos/slides-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/demos/slides-handouts.pdf)).
It shows the margin, backgrounds and overlays of each kind, and every slide transition.

A deck is a document with a show rule at the top and a `#slide` call per slide.

```typst
#import "@preview/animo:0.1.1": *
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#slide[
  = An optional heading
  Some content.
]
```

Everything inside a slide body is plain typst.
Animo has no templating or styling features.
You can roll your own template using [standard typst styling techniques](https://typst.app/docs/tutorial/advanced-styling/)
and by writing wrappers for Animo's `#slide` command.
There is no built-in support for headers or footers.
You can put recurring element with `#place` command inside a wrapper around `#slide`,
e.g. in the slide background or overlay.

## The Deck

The `animo` function is a document show rule,
and the only place where the shape of a deck is written,
e.g. with `#show: animo.with(...)`.
Because the show rule receives the whole document, it determines three things at once:
the page size of the two paged outputs,
the HTML page with its stylesheet and its runtime,
and the rule that fits a slide to the browser window.

The `width` and `height` arguments set the size of a slide.
The `margin` argument insets the body within the slide and moves the origin of the body,
so a `#place` offset is measured from the inset corner
and `#place(bottom + right)` lands inside the margin rather than on the edge.

A document without the show rule still has slides, at the defaults in the
[Reference](reference.md#animo).

There is no `paper:` argument.
Typst does not expose its paper-size table to scripts,
so a paper name cannot be resolved to two lengths in the HTML target.
The default slide size is such that the default font size of Typst is readable,
even with a poor projector.

## The Body

The body of a slide is the content block between the square brackets of the `#slide` call,
e.g. `#slide[ ... ]` and determines what is on the slide.
This content is laid out on a **canvas**, which is at least as large as the slide and may be larger.
The output (HTML or PDF) shows one rectangle of the canvas, which is called the **viewport**.
Content outside the viewport is clipped, and never carried over to a next slide.
[The Viewport](viewport.md) says how large the canvas is and how to travel over it.

The parts of the body a timeline may address are marked with [`tag`](tags.md),
and `animation:` is the timeline itself.
A slide without an `animation:` argument has a single state, which shows the body as written.

## Backgrounds and Overlays

A slide has three layers:

1. the **background**, behind everything;
1. the **canvas**, carrying the body, which is what a [`pan`](viewport.md) moves;
1. the **overlay**, in front of everything.

The outer two take a color or content.

```typst
#slide(
  background: image("backdrop.jpg", width: 100%, height: 100%, fit: "cover"),
  overlay: place(bottom + right, dx: -1cm, dy: -1cm)[#emph[A talk]],
)[
  = On top of a picture
]
```

A **color** fills the whole viewport.
A color used as a background becomes the page fill on paper and a CSS background in the browser.
A color used as an overlay is painted over the slide.
An overlay color is therefore mostly useful with an alpha channel,
typically to dim the slide with a tint.

Instead of a color, one may also fill the background and overlay with typst **content**,
laid out in a box the size of the viewport and clipped to it.
A `#place` inside the overlay or background resolves against the full viewport without margins,
so an `image(width: 100%, height: 100%)` fills the viewport entirely.

**A gradient or a tiling** are implemented with a `rect` that fills the slide
and is treated as any other content:

```typst
#slide(
  background: rect(width: 100%, height: 100%, fill: gradient.linear(blue, purple))
)[
  = On a gradient
]
```

Four rules govern both overlay and background layers.

1. **They belong to the viewport, not to the canvas.**
   A [`pan`](viewport.md) moves the slide body between them and leaves them where they are,
   so a logo stays in the same place on screen instead of travelling with the canvas.

1. **They hold no `tag` and no `region`,** and Animo refuses either there.
   They are outside the body, so nothing in a timeline could address them.

1. **They are rendered once per slide (or optionally subslide)**,
   independently of the slide's timeline.

1. **The viewport clips all three layers alike.**
   There is no coupling between the three layers.

## Slide Transitions

A slide says how it is **entered** with an optional `init(..)`,
which must be placed first in the animation block.
Animo will refuse a slide whose `init` follows a `sub` call.

The `init` call describes the **initial state** of the slide,
which is the state that the body declares before the first `sub`.
The `init` call adds no subslide.
Its first argument is the transition into the slide:

```typst
#slide(animation: {
  import anim: *
  init(push(direction: btt))
  sub(reveal("detail"))
})[
  = Pushed up into view
  #tag("detail")[A detail that comes later.]
]
```

A slide with no other use for a timeline just uses `init()`
and can be written compactly without the import and braces:

```typst
#slide(animation: anim.init(anim.push()))[
  = Pushed in from the right
]
```

The `anim` module holds one function per transition:

| Transition                | What happens on a forward step                                          |
| ------------------------- | ----------------------------------------------------------------------- |
| `crossfade()`             | the slide fades in while the slide before it fades out                  |
| `push(direction: rtl)`    | the slide moves in from one edge and moves the slide before it out      |
| `cover(direction: rtl)`   | the slide moves in from one edge over the slide before it               |
| `uncover(direction: rtl)` | the slide before it moves out at one edge and shows the slide in place  |
| `wipe(direction: ltr)`    | the slide is revealed over the slide before it behind a travelling edge |

The `direction` parameter takes a typst direction:

- `ltr` travels from left to right,
- `rtl` from right to left,
- `ttb` from top to bottom and
- `btt` from bottom to top.

A push, a cover and an uncover default to `rtl`, so the slide comes in from the right
or the slide before it leaves at the left.
A wipe defaults to `ltr`.

The `duration:` argument of `init` is how long the transition takes, in seconds.
It defaults to `auto`, which is the deck's
[`transition-duration`](presenting.md#motion).
A duration of zero is a **hard cut**, whatever the transition:

```typst
#slide(animation: anim.init(duration: 0))[
  = Arrived without a fade
]

#slide(animation: anim.init(anim.wipe(direction: ttb), duration: 0.8))[
  = Wiped in from the top, slowly
]
```

The boundary between two slides belongs to the later slide,
so stepping back over it plays the same transition backwards.
For example, stepping back from a slide that was pushed in from the right
moves that slide out to the right again and brings the previous slide back from the left.

A transition changes nothing inside either slide.
The slide being entered is already in its subslide state when it comes into view.

The `init` call also takes `wait:`, `hold:` and `handout:`,
which mean for the initial state what they mean for a subslide on a `sub`.
[Continuous Animations](continuous.md#timing) explains the first two,
and [Handouts](handouts.md#the-handout-flag) the third.

## Default Transition of the Deck

A slide whose `init` names no transition takes the default transition of the deck,
which is the `transition:` argument of the show rule and defaults to `anim.crossfade()`:

```typst
#show: animo.with(transition: anim.push(direction: btt))
```

The duration of a transition is the deck's `transition-duration`,
unless an `init` call states a `duration:`.
A `transition-duration` of zero makes a hard cut the default.
A slide in such a deck that names a transition and states no duration takes that zero,
and is entered with a cut rather than with the transition it names.
A slide that is to be pushed in states its duration as well:

```typst
#show: animo.with(transition-duration: 0)

#slide(animation: anim.init(anim.push(), duration: 0.4))[
  = The one slide that is pushed in
]
```

A reader whose browser asks for reduced motion gets a hard cut at every boundary,
whatever the deck and its slides state.

Transitions are HTML only.
The paged outputs put two slides on two pages with nothing between them,
so they ignore the transition, the `duration:` and the `wait:` of `init`.
