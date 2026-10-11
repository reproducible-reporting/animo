---
description: >-
  Regions: areas of a slide laid out afresh in every epoch inside a fixed footprint,
  how to size, align and name them, and where they cannot go.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Regions

The demo deck for this page is
[`regions.typ`](https://github.com/reproducible-reporting/animo/blob/main/demos/regions.typ)
([HTML](https://reproducible-reporting.github.io/animo/demos/regions.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/demos/regions-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/demos/regions-handouts.pdf)).
It shows a region that reflows when its content changes,
ways to reduce the empty room that a region reserves,
nested and named regions, regions inside containers, and a region around a cetz canvas.

A region is an area of a slide that typst lays out again whenever the content inside it changes.
The room that the region takes on the slide stays the same.
Inside a region, [content that changes](structural.md) can move the content after it,
such as the paragraphs that follow.

```typst
#slide(
  animation: {
    import anim: *
    sub(replace("claim")[A claim long enough to wrap onto a second line.])
    sub(remove("caveat"))
  },
)[
  #region[
    #tag("claim")[A short claim.]
    #tag("caveat")[With a caveat.]

    This paragraph moves when the two above it change.
  ]

  This paragraph is outside the region, and never moves.
]
```

## The Fixed Footprint

Typst lays out the body of a region once for every [epoch](structural.md#epochs) of the slide.
The region then reserves a rectangle that fits all of these layouts.
This rectangle is as wide as the container of the region,
and as tall as the tallest of the layouts at that width.
The rectangle is the **footprint** of the region, and it is the same in every state of the slide.

Inside the footprint, typst lays out each epoch separately.
The line breaks can differ from one epoch to the next.
A removed tag frees its space, and the paragraphs after the removed tag move up.
Outside the footprint, every element stays at the same position, to the pixel.

Outside a region, a tag whose content changes reserves a box that fits the content of every epoch,
as [Box Reserved by a Changing Tag](structural.md#box-reserved-by-a-changing-tag) explains.
Inside a region, the tag reserves no box of its own, so typst can reflow the content around the tag.
As a result, `remove` frees the space of a tag inside a region,
and a later `reset` takes that space again.
The `hide` and `reveal` primitives change only the visibility of a tag,
so the space of a hidden tag stays reserved.

The footprint is fixed for three reasons, in decreasing order of importance.

1. **Continuous animations keep their meaning.**
   A `move` of 2 cm shifts a tag 2 cm away from the position where typst laid the tag out.
   Outside a region, that position stays the same when content changes,
   so the tag stays 2 cm away from it.
   If the whole slide reflowed instead, the positions that `move`, `scale` and `pan` start from
   would shift, and every element they act on would jump at the content change.
1. **A content change crossfades only the region.**
   In the HTML presentation, the browser crossfades between two renderings of the region.
   Everything outside the region is identical in both epochs, so it stays still on screen.
1. **All three output types lay out alike**, so one source file can produce all of them.

## The Price, and the Remedies

A region reserves room for its largest content.
When the first content of a region is short and its last content is tall,
the region shows an empty gap in its early states.
That gap is the cost of the three properties above.
The following remedies reduce the gap or move it:

- **Align the content.**
  The `align` argument places a state that is smaller than the footprint inside the footprint.
  With `align: bottom`, a short first state sits directly above the content after the region.
  The gap then appears above the state, where it usually looks like ordinary spacing.
- **Give a size.**
  A region with `height: 3cm` reserves exactly 3 cm and clips a state that is taller,
  so check every subslide for clipped content.
  A region with a given height also skips the measurement of its epochs,
  so it compiles faster than a region that measures them.
- **Merge regions** whose contents are tallest in different epochs.
  Two separate regions together reserve the sum of their tallest epochs.
  One region around both contents reserves only the height of the epoch
  in which the two contents together are tallest, and that height is less than the sum.
  In the merged region, a change of one content moves the other content.

Splitting a region into several smaller regions has a different effect.
A change inside one of the smaller regions reflows only that region,
and the content of the other regions stays where it is.
Splitting does not reduce the room that is reserved,
because each smaller region reserves the room of its tallest epoch.
Together, the smaller regions reserve at least as much as one region around all of them.

The `width` and `height` arguments take a length or a ratio of the size of the container.
The `align` argument defaults to `top`.
This alignment sets only the vertical position,
so a region inside `#set align(center)` still centres its content horizontally.
The `clip` argument defaults to `true` when a width or height is given, and to `false` otherwise.
A region without a given size needs no clipping, because its measured footprint fits every state.

## Nesting and Names

A region inside another region also has a fixed footprint,
so a change inside the inner region reflows only the inner region.
Each region measures its body once for every epoch.
The footprint of the inner region is the same in every epoch,
so the outer region needs no extra measurements for the states of the inner region.

Typst needs one extra pass of layout for every level of nesting, and stops after five passes.
As a result, regions nest at most three deep.
In the static presentation and the static handouts,
regions nest at most two deep on a slide where a `move` has a `relto` argument,
because typst needs another pass to read the position of the tag that `relto` names.
In the HTML presentation, the browser reads that position, so the limit stays at three.
Tags do not count toward this depth.
When regions nest deeper, typst warns that the document did not converge within five attempts.

In the HTML presentation, the browser animates the outermost region as one unit
when a step changes content inside that region, including content in the regions nested in it.
Suppose that one step changes content in two inner regions of the same outer region.
The two operations then need the same timing and the same transition,
and typst refuses them otherwise.

A region with a name, as in `region(name: "box")`, can be addressed by the timeline
like a tag with that name.
The primitives `move`, `scale`, `reveal` and `hide` then act on the whole footprint,
and `pan(relto: "box")` brings the footprint into view.
The timeline cannot address a region without a name,
but the browser still crossfades such a region when its content changes.
The structural primitives change the content of a region through the tags inside the region,
so typst refuses `replace("box")` on the name of a region.

`animo-` is a reserved prefix, and typst refuses a tag or region whose name starts with it,
because Animo uses that prefix for the labels of the elements it generates.

## Where a Region Cannot Go

A region is a block, so it takes its width from its container.
A region therefore gets the right width in a container whose width does not depend on its content.
In a container that takes the width of its content, the region gets the wrong width.

| Container                                               | A region there                                     |
| ------------------------------------------------------- | -------------------------------------------------- |
| the slide body, a `block`, a list item                  | is as wide as the container                        |
| a grid or table cell of a fixed or `fr` column          | is as wide as the cell                             |
| `#columns`                                              | is as wide as the column                           |
| a `#place`d or inline `box` with a `width`              | is as wide as the box                              |
| an `auto` grid column, `stack(dir: ltr)`, an `auto` box | **takes the whole body width**, give it a `width:` |
| a bare `#place`                                         | **takes the whole body width**, give it a `width:` |
| the middle of a paragraph                               | **breaks the paragraph** in two around it          |
| math, a cetz canvas                                     | does not belong there; use a [bare tag](tags.md)   |

Animo cannot detect the cases in bold, so it gives no warning for them.
In the cases that take the whole body width,
typst reports the width of the slide body to the region,
exactly as it does in a container that really is that wide.
Such a region reserves the wrong room unless you give it a `width:` argument.

A cetz canvas takes draw commands rather than content, so a region goes around the canvas
and not inside it.
The region then holds the whole canvas,
and the tags sit on the `content()` elements of the canvas
(see [Where a Tag May Sit](tags.md#where-a-tag-may-sit)).
When the content of one of those tags changes,
typst redraws the whole figure inside the footprint of the region.
A region around a canvas is the only way a cetz figure can change size on a slide.
It is also the most expensive construct in an Animo deck.
See [Performance](performance.md#what-costs-and-what-to-do-about-it) for the numbers.

Typst refuses a region outside a `#slide`, and a region whose body is not content.
