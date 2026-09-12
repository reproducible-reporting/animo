---
description: >-
  A slide is a viewport onto a canvas.
  How a deck declares its shape, what the canvas is for,
  and what the arguments of `#slide` do.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Slides

A deck is a document with a show rule at the top and a `#slide` call per slide.

```typst
#import "@preview/animo:0.1.0": *
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#slide[
  = A heading
  Some content.
]
```

Animo has no templating or styling features, and no header or footer machinery.
A recurring element is `#place` inside a wrapper around `#slide`.

## The Deck

`animo(body, width: 16cm, height: 9cm, margin: 1cm)`

The show rule is where a deck's shape is written, and the only place it is written.
It receives the whole document, which is what lets it be three things at once:
the page size of the two paged outputs,
the HTML page with its stylesheet and its runtime,
and the rule that fits the slide to the browser window.

- `width` and `height` are the size of the viewport, which is the size of a slide.
- `margin` insets the body inside the viewport.
  It moves the body's origin, so a `#place` offset is measured from the inset corner
  and `#place(bottom + right)` lands inside the margin rather than on the edge.

A document without the show rule still has slides, at these defaults.
That keeps a forgotten show rule a cosmetic mistake rather than a broken deck.

There is deliberately no `paper:` argument.
Typst does not expose its paper-size table to scripts,
so a paper name cannot be resolved to two lengths in the HTML target,
and a paper name that works in three outputs out of four is worse than no paper name.

## The Viewport and the Canvas

A slide has two rectangles, and keeping them apart is what makes panning mean anything.

The **viewport** is what the audience sees:
one HTML slide container, one presentation page, one handout page.
It is the size of the deck, and it clips.
Whatever falls outside it is not carried over to a next slide.

The **canvas** is what the body is laid out on.
It is at least as large as the viewport and may be larger.
Its origin is the viewport's origin, and the body sits inside it at the deck's margin.
A slide that places nothing outside the viewport has a canvas equal to its viewport,
so nothing about the ordinary case changes.

Content on the canvas but outside the viewport is invisible for now.
Panning is what brings it into view, and panning is not in this version yet.

## The Automatic Canvas

`canvas: auto`, the default, sizes the canvas to the content:
the union of the body's in-flow extent and the extent of every `#place`d element,
clamped to at least the viewport.

This cannot come from typst's own `auto` sizing,
because `#place` is out of flow and contributes nothing to it,
and it cannot come from position introspection, which does not exist in the HTML target.
What animo uses instead is a `show place:` rule over the body.
It fires for every placement, reads its offsets, its alignment and the size of its body,
and the union is computed from content alone,
which is why the canvas comes out the same in the browser and on paper.

The rule has one limit, and it is worth knowing before it bites.
A placement nested inside another container reports its offsets against *that* container,
and the rule cannot tell that apart from a placement written directly in the slide body.
Animo counts it anyway, from the canvas origin.
Since a container never sits at a negative coordinate,
the canvas then comes out **too small rather than too large**:

```typst
#slide[
  // Counted exactly: 1cm of margin, plus 20cm, plus the width of the content.
  #place(dx: 20cm)[far]

  #box(width: 4cm, height: 2cm)[
    // Counted as if the box were at the origin of the slide,
    // so the canvas is short by wherever the box actually sits.
    #place(dx: 20cm)[also far]
  ]
]
```

`canvas: (width: .., height: ..)` states the canvas explicitly and is the escape hatch
whenever the automatic extent is wrong.
An explicit canvas is still clamped to at least the viewport.

## Backgrounds

`background:` takes a colour or content.

A **colour** becomes the page fill in the paged outputs
and a CSS background in the HTML output,
because `set page` is unavailable in the HTML target.

Anything else is treated as **content** and is drawn into the slide behind the body,
covering the viewport and clipped to it.
This is how a background image works, in all four outputs:

```typst
#slide(background: image("backdrop.jpg", width: 100%, height: 100%, fit: "cover"))[
  = On top of a picture
]
```

An image cannot be a page fill in typst,
so a background image is content in the paged outputs as well,
and it belongs to the viewport rather than to the canvas.

## Numbering

`numbered:` decides only whether a slide is **counted** by the slide counter.
A title or section slide is typically `numbered: false`.

It does not decide whether or how a number is *shown*.
Nothing displays a slide number yet:
how a number is obtained at all is an open question of the design,
because an HTML frame covers a whole run of subslides
and cannot carry a subslide number as ink.

Navigation does not use this counter.
A presenter walks through a title slide whether or not it carries a number,
so the position in the deck is counted separately, over every slide.

## What Is Not Here Yet

`animation:`, `#tag` and `#region` are in the signature and do nothing.
A deck that hands `#slide` a non-empty `animation:` is told so rather than
having it silently ignored.
