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
  = A heading
  Some content.
]
```

Everything inside a slide body is plain typst.
Animo has no templating or styling features.
You can roll your own template using [standard typst styling techniques](https://typst.app/docs/tutorial/advanced-styling/)
and by writing wrappers for Animo's `#slide` command.
There is no built-in support for headers or footers.
You can put recurring element with `#place` command inside a wrapper around `#slide`.

## The Deck

`animo` is a document show rule, and the only place a deck's shape is written.
It receives the whole document, so it determines three things at once:
the page size of the two paged outputs,
the HTML page with its stylesheet and its runtime,
and the rule that fits a slide to the browser window.

`width` and `height` are the size of a slide.
`margin` insets the body inside it and moves the body's origin,
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
It is laid out on a **canvas**, which is at least as large as the slide and may be larger,
and the slide shows one rectangle of it, the **viewport**.
Content outside the viewport is clipped, and never carried over to a next slide.
[The Viewport](viewport.md) says how large the canvas is and how to travel over it.

The parts of the body a timeline may address are marked with [`tag`](tags.md),
and `animation:` is the timeline itself.
A slide with no `animation:` is just displays of the slide's body.

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
As a background it is the page fill on paper and a CSS background in the browser.
As an overlay it is ink over the slide rather than a fill behind it,
so it is useful with an alpha channel, typically to dim the slide with a tint.

Instead of a colour, one may also fill the background and overlay with typst **content**,
laid out in a box the size of the viewport and clipped to it.
A `#place` inside the overlay or background resolves against the full viewport without margins,
so an `image(width: 100%, height: 100%)` fills it entirely.

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

`transition:` says how a slide is **entered**:
`auto`, the default, is the deck's own strategy, and `none` cuts abruptly.
A transition may also be named, and `"crossfade"` is the only one implemented so far,
which is what `auto` defaults to.

```typst
#slide(transition: none)[
  = Arrived without a fade
]
```

A transition moves nothing.
Two slides share nothing to hold still, so the whole slide is what crosses,
and the subslide state of the slide being entered is in place before it comes up.
How long a crossfade takes is the deck's
[`transition-duration`](presenting.md#motion) rather than an argument here,
so turning every boundary into a hard cut is one argument on the show rule.

This is an HTML-only argument.
The paged outputs cannot have any transitions by definition, so they ignore it.
