---
description: >-
  A slide is a viewport onto a canvas that may be larger than it.
  How `pan` moves the viewport, how large the canvas is,
  and what panning becomes in each output type.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# The Viewport

The demo deck for this page is
[`viewport.typ`](https://github.com/reproducible-reporting/animo/blob/main/demos/viewport.typ)
([HTML](https://reproducible-reporting.github.io/animo/demos/viewport.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/demos/viewport-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/demos/viewport-handouts.pdf)).
It shows a canvas two screens wide, a body longer than the viewport,
a pan past the edge of the canvas, a background and an overlay that stay in place during a pan,
and a canvas with an explicit size.

A slide has two rectangles.
The **viewport** is what the audience sees,
which is a slide container in the browser and a page in the static outputs.
The viewport has the slide size that the `width` and `height` arguments of `animo` set,
and it clips everything outside it.
The **canvas** is what the body is laid out on.
It is at least as large as the viewport and may be larger.

Content on the canvas but outside the viewport is **clipped, never carried over** to a next
slide or a next page.
A slide is a fixed rectangle, so there is no next page for it to flow onto.
The `pan` primitive brings the rest of the canvas into view.

```typst
#slide(
  animation: {
    import anim: *
    sub(pan(relto: "details"))
    sub(pan(dy: 4cm))
  },
)[
  = An overview
  The details are to the right, beyond the edge of the slide.

  #place(dx: 18cm, tag("details")[
    = The details
    #lorem(80)
  ])
]
```

## Panning

The `pan` primitive is a continuous animation primitive, like `move` and `scale`,
but it addresses no tag.
Instead, `pan` moves the viewport over the canvas.
Positive values move the viewport right and down, so the content moves left and up.

The **anchor** of a `pan` is the canvas origin,
or the anchor of the tag that `relto` names (see [What `relto` Reads](#what-relto-reads)).
A `pan` to the anchor puts the anchor at the margin of the viewport,
which is where the body of a new slide starts.
`pan(relto: "details")` therefore shows the tag where a new slide would show its first line,
and `pan(x: 0cm, y: 0cm)` returns the viewport to its position at the start of the slide.

A `pan` sets the position of the viewport in one of two ways,
and it chooses between them separately for the x and y directions:

| Argument   | Effect                                                          |
| ---------- | --------------------------------------------------------------- |
| `x`, `y`   | puts the viewport at that distance from the anchor              |
| `dx`, `dy` | moves the viewport over that distance from its current position |
| `relto`    | names the tag whose anchor `x` and `y` are measured from        |

When a `pan` has neither `x` nor `dx`, the viewport keeps its horizontal position,
unless the `pan` has a `relto`.
With a `relto`, the viewport goes to the anchor in that direction.
The same holds for `y`, `dy` and the vertical position.
The [`move`](continuous.md#where-move-puts-things) primitive takes the same arguments
and puts a tagged element where `pan` would put the viewport.

One `pan` can use a different way for each direction:

```typst
animation: {
  import anim: *
  sub(pan(relto: "details"))           // bring the tag into view
  sub(pan(dy: 4cm))                    // scroll down, and stay on the tag horizontally
  sub(pan(relto: "summary", x: -1cm))  // the next tag, with a centimeter to its left
  sub(pan(x: 0cm, dy: -2cm))           // back to the left edge, and up a little
}
```

Animo refuses a `pan` that combines `x` with `dx`, or `y` with `dy`,
because the two offsets of such a pair are measured from different places.

The position of the viewport is part of the state of the slide,
like everything else that the timeline sets.
The viewport stays where a `pan` puts it until the next `pan`,
and stepping back to an earlier subslide restores the earlier position of the viewport.

The viewport can move **past the edge of the canvas**.
Where the viewport extends beyond the canvas, it shows the background of the slide.
A `pan` can therefore bring a tag near the edge of the canvas to the middle of the viewport,
rather than only to its top-left corner.

### What `relto` Reads

The anchor of a tag is the **top-left corner of its wrapper**,
at the place where the body laid the tag out.
`pan` and `move` read the anchor in the same way, which has the following consequences:

- The anchor is a corner of the wrapper, and the wrapper can extend beyond the visible glyphs.
  A tagged phrase in a paragraph is anchored at the top of its line,
  rather than at the top of its letters.
- A `move` or a `scale` of a tag leaves the anchor of that tag unchanged,
  so the anchor is the same in every state.
- When one name tags several sites, the anchor is the anchor of the first site in the body.

Animo refuses each of the cases below,
because each of them would produce a subslide that looks different on paper and in the browser.

- A `relto` that **names no tag on the same slide**, which is almost certainly a misspelt name.
  A tag with that name on another slide is ignored.
- A `relto` to a tag with **`wrap: none`**,
  because such a tag has no wrapper and therefore no corner to serve as its anchor.
- A `relto` or a `move` that addresses a tag **nested inside a tag that the timeline moves or
  scales**.
  A `move` or a `scale` of the outer tag also shifts the corner of the inner tag,
  so that corner is no longer where the body laid the inner tag out.
  Use the anchor of the outer tag instead, or take the inner tag out of the outer one in the body.
  Nested tags are allowed in all other cases.
  For example, an inner tag keeps its anchor when the outer tag is only revealed or hidden.

## How Large the Canvas Is

The `canvas` argument of `slide` defaults to `auto`.
When the timeline of a slide contains a `pan`, `auto` sizes the canvas to fit the content of the
slide.
Animo computes that size as the smallest rectangle that holds two things:
the regular content of the body (its **flow**) and every element placed with `#place`.
When that rectangle is smaller than the viewport, Animo enlarges it to the viewport.
A slide whose content fits inside the viewport therefore has a canvas equal to its viewport.
A slide whose body is simply longer than its viewport gets a taller canvas,
and a `pan` brings the rest of the body into view.
Nothing has to be placed for that to work.

When the timeline of a slide contains no `pan`, Animo skips the computation of the canvas size,
because no subslide can show the part of the canvas outside the viewport.
The slide then draws its body directly inside the viewport,
which makes a slide that does not pan cheaper to compile.
See [Performance](performance.md) for the cost of a slide that does pan.

The `background:` and `overlay:` arguments of `slide` never count toward the canvas size,
whatever content they hold.
A full-bleed image in the background therefore cannot enlarge the canvas by accident.

Animo computes the canvas size from the placed content and its offsets,
without asking typst where that content ended up,
because typst cannot report positions when it compiles to HTML.
The computation is therefore the same in the browser and on paper, and so is the canvas.
The computed size is exact for a `#place` written directly in the slide body,
provided that the placed content has a fixed size.
In the cases below, the computed size is an approximation.
A container in the table is any element that holds the `#place`, such as a `box` or a grid cell.

| Placement                                         | How Animo counts it                         |
| ------------------------------------------------- | ------------------------------------------- |
| `#place` in a container                           | from the canvas origin, so too small        |
| an alignment in a container                       | against the slide body, so too large        |
| content with a ratio size, as `rect(width: 100%)` | not at all, also directly in the slide body |

You do not need to check for these cases in advance.
A canvas that is too large costs nothing, unless a `pan` moves the viewport onto its empty part.
A canvas that is too small becomes apparent the first time a `pan` fails to bring the expected
content into view.
In either case, `canvas: (width: .., height: ..)` sets the size of the canvas explicitly.
Animo enlarges an explicit canvas to the viewport when it is smaller than the viewport.

Animo lays out the body of a slide in a box as tall as the area inside the margins,
or as tall as the flow of the body when the flow is taller.
A `#place` in the body aligns its content against that box.
When the flow runs past the bottom of the viewport,
`place(bottom + right)` therefore puts its content at the bottom right of the whole flow,
rather than at the bottom right of the first screenful.
To put a mark at the bottom of the first screenful, place it from the top with an explicit `dy:`.

## What Panning Means in Each Output

| Output type         | How a `pan` appears                                                        |
| ------------------- | -------------------------------------------------------------------------- |
| HTML presentation   | an animated `translate` of the canvas, like every other step               |
| Static presentation | a separate page for each subslide, showing the canvas through the viewport |
| Static handouts     | a page showing the viewport of each subslide that the handout keeps        |

In the browser, a `pan` moves the HTML element that holds the whole canvas,
so all content on the canvas moves together.
The background and the overlay stay in place, because they belong to the viewport.
Animo expresses the `translate` as a percentage of the canvas size,
so the viewport shows the same part of the canvas at any window size.

A handout page shows the viewport in one state of the slide, which is by default the final state.
When the timeline pans away from some content and never pans back,
that content is therefore missing from the handout.
See [Handouts](handouts.md#content-missing-from-the-final-state) for how to keep it.
