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

The example deck for this page is
[`hello.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/hello.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/hello.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/hello-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/hello-handouts.pdf)).
It illustrates most concepts explained below with one slide, one tag and one subslide.

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
and the only place where the shape of a deck is written.
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

The body says what is on the slide.
The body is laid out on a **canvas**, which is at least as large as the slide and may be larger.
The slide shows one rectangle of the canvas, which is called the **viewport**.
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

The outer two take a colour or content.

```typst
#slide(
  background: image("backdrop.jpg", width: 100%, height: 100%, fit: "cover"),
  overlay: place(bottom + right, dx: -1cm, dy: -1cm)[#emph[A talk]],
)[
  = On top of a picture
]
```

A **colour** fills the whole viewport.
A colour used as a background becomes the page fill on paper and a CSS background in the browser.
A colour used as an overlay is painted over the slide.
An overlay colour is therefore mostly useful with an alpha channel,
typically to dim the slide with a tint.

Instead of a colour, one may also fill the background and overlay with typst **content**,
laid out in a box the size of the viewport and clipped to it.
A `#place` inside the overlay or background resolves against the full viewport without margins,
so an `image(width: 100%, height: 100%)` fills the viewport entirely.

If you like **a gradient or a tiling**,
then use a `rect` of the slide size, which is treated as any other content:

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

A slide says how it is **entered** with `init(..)`, which is the first call of its timeline.
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

A slide with no other use for a timeline writes the call on its own, without the import:

```typst
#slide(animation: anim.init(anim.push()))[
  = Pushed in from the right
]
```

The `anim` module holds one function per transition:

| Transition              | What happens on a forward step                                          |
| ----------------------- | ----------------------------------------------------------------------- |
| `crossfade()`           | the slide fades in while the slide before it fades out                  |
| `push(direction: rtl)`  | the slide moves in from one edge and moves the slide before it out      |
| `cover(direction: rtl)` | the slide moves in from one edge over the slide before it               |
| `wipe(direction: ltr)`  | the slide is revealed over the slide before it behind a travelling edge |

The `direction` parameter takes a typst direction:
`ltr` travels from left to right, `rtl` from right to left,
`ttb` from top to bottom and `btt` from bottom to top.
A push and a cover default to `rtl`, so the slide comes in from the right,
and a wipe defaults to `ltr`.
A parameter or a value that a transition does not take is refused when the deck is compiled.

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

The boundary between two slides belongs to the slide with the higher number,
so stepping back over it plays the same transition backwards.
For example, stepping back from a slide that was pushed in from the right
moves that slide out to the right again and brings the previous slide back from the left.

A transition changes nothing inside either slide.
The slide being entered is already in its subslide state when it comes into view.

The `init` call also takes `wait:`, `hold:` and `handout:`,
which mean for the initial state what they mean for a subslide on a `sub`.
[Continuous Animations](continuous.md#timing) explains the first two,
and [Selecting States for Handouts](continuous.md#selecting-states-for-handouts) the third.
The `init` call is written at most once, before the first `sub`,
and Animo refuses it anywhere else.

### Default Transition of the Deck

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
