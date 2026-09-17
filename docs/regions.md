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

The example deck for this page is
[`content.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/content.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/content.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/content-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/content-handouts.pdf)).
It illustrates a region reflowing around a change.

A region is an area whose inside is laid out afresh whenever its content changes,
while the room it takes on the slide never changes.
Inside a region, [content that changes](structural.md) may push its surroundings
around.

```typst
#slide(
  animation: {
    import anim: *
    sub(replace("claim")[A claim long enough to take a second line of its own.])
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

A region lays its body out once for every [epoch](structural.md#epochs) of the slide and
reserves the largest of those layouts: the width of its container, and the height of its
tallest epoch at that width.
That rectangle is its **footprint**, and it is the same in every state.
Inside it, typst lays each epoch out as if nothing else existed:
line breaks change, a removed tag frees its space, and the paragraphs after it move.
Outside it, nothing moves, down to the pixel.

A tag inside a region reserves no box of its own, which is what lets the region reflow around it.
So inside a region `remove` and `reset` can really free space (or restore it).
In contrast, `hide` and `reveal` primitives preserve the space that was initially reserved.

The footprint is fixed for three reasons, in decreasing order of importance.

1. **Continuous animations keep their meaning.**
   A tag moved by 2 cm is still 2 cm from where it was laid out after a content change.
   If the slide reflowed, every `move`, `scale` and `pan` in flight would jump at once.
1. **The crossfade between two contents stays invisible everywhere else**,
   because the new rendering is identical outside the region.
1. **All three output types lay out alike**, so one source file can produce all of them.

## The Price, and the Remedies

A region reserves room for its largest content,
so a region whose first content is short and whose last content is tall shows an empty gap
in its early states.
That is the cost of the three properties above, and three remedies are available:

- **`align`** says where a smaller state sits in the footprint.
  `align: bottom` puts a short first state against whatever follows the region,
  which moves the gap above it, where it usually reads as spacing.
- **Split the region** into several smaller ones,
  so that each reserves only the room its own content needs.
- **Give a size.** `height: 3cm` reserves exactly that, and a state that needs more is
  clipped, so check every subslide. A region with a given height also measures nothing at all,
  which is the cheapest form of a region.

`width` and `height` arguments take a length or a ratio of the container.
The `align` argument defaults to `top`, which has no horizontal part,
so a region inside `#set align(center)` keeps its content centred.
The `clip` argument defaults to `true` as soon as a size is given and to `false` otherwise,
since a measured footprint fits every state anyway.

## Nesting and Names

A region inside a region is itself a fixed footprint,
so a change inside the inner one reflows only the inner one.
Each region measures each epoch once, however deeply they nest.

`region(name: "box")` makes the footprint a site the timeline can address,
like a tag of that name: `move`, `scale`, `reveal`, `hide` and `pan(relto: "box")` act on
the whole of it. An unnamed region is invisible to the timeline, and still crossfades.
The structural primitives address the content inside a region through its tags,
so `replace("box")` on a region's name is refused.

`animo-` is a reserved prefix, and a tag or region named with it is refused,
because Animo labels what it emits for itself that way.

## Where a Region Cannot Go

A region is a block, and it takes its width from its container.
That makes it work where the container has a width of its own,
and go wrong where the container takes the width of its content.

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

Animo cannot detect the rows in bold, because typst tells a region the same width in each
of them that it tells a region in a container that really is that wide.
A region that is too wide reserves the wrong room silently, so give it a `width:` there.

A cetz canvas takes draw commands rather than content, so a region goes around the canvas
and not inside it.
What the region then holds is the canvas as a whole, with
[tags on its `content()` elements](tags.md#where-a-tag-may-sit),
and a change of one of them redraws the whole figure inside the region's footprint.
It is the only way a cetz figure changes size on a slide,
and it is also the most expensive construct in an Animo deck.
See [Performance](performance.md#what-costs-and-what-to-do-about-it) for the numbers.

A region outside a `#slide` is refused, and so is one around something that is not content.

## What Is Not Here Yet

A region that pushes its surroundings around rather than keeping its footprint.
It needs an animated transition to look right.
