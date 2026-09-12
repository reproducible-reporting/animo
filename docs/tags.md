---
description: >-
  A tag marks a part of a slide so that a timeline can address it by name.
  What container a tag site becomes, what tagging costs,
  and which primitives reach which kind of tag site.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Tags

A tag marks a part of a slide so that the [timeline](animation.md) can address it by name.

```typst
#import "@preview/animo:0.1.0": *
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#slide(
  animation: {
    import anim: *
    sub(reveal("caveat"))
  },
)[
  #tag("claim")[A short claim.]

  #tag("caveat", hidden: true)[With a caveat.]
]
```

`tag(name, body, hidden: false, removed: false, wrap: auto)`

- `name` is a string, and it is what the timeline refers to.
- `hidden: true` makes the element invisible on the first subslide
  while it still occupies its space.
  It is the initial-state counterpart of `hide`.
- `wrap` decides what container the tag site becomes, which the rest of this page is about.
- `removed: true` is the initial-state counterpart of the `remove` primitive
  and is not implemented yet.

## One Name, Several Places

The same name may be used several times within one slide.
The timeline then addresses all of them together, as if they were one element.

The same name may also be used in different slides without interfering.
A tag is scoped to the slide it appears in:
it reads the plan of that slide and of no other,
because the plan is handed to the slide's body as an argument
rather than published to the document.

That is also why a deck that wraps `#slide` in a function of its own,
which is how a recurring element is added,
changes nothing about how its tags resolve.

## What a Tag Site Becomes

A tag always wraps its body, unless `wrap: none` says otherwise.
Wrapping is what makes the element addressable:
only a labelled `box` or `block` becomes a group that a browser can move,
and a tag that no container holds is a tag that nothing can animate.

The decision is a property of the body alone and never of the timeline,
so that adding an animation step cannot reflow a paragraph,
and so that the four outputs and all of a slide's states lay out the same.

| `wrap`     | Wrapper                                                                     |
| ---------- | --------------------------------------------------------------------------- |
| `auto`     | `box` for an inline body, `block(width: 100%)` for a block-level one        |
| `box`      | `box`, the hugging wrapper                                                  |
| `block`    | `block(width: 100%)`, since a hugging block loses the container's alignment |
| `none`     | no wrapper and no label, the body is returned untouched                     |
| a function | the function builds the inner slot, animo matches the outer one to it       |

`auto` decides by **measuring** whether the body breaks the line it is put in,
and not by inspecting what kind of element it is.
Inspection cannot see into a `#context` block, which reports nothing about what it will
produce, and the measurement can.

The axis it decides is hugging versus filling rather than inline versus block.
A `box` and a `block` render identically for content that already sits between paragraph
breaks, while a wrapper at its natural width hugs its content,
which left-aligns anything the container was centring, such as a `figure` or a block
equation.
`block(width: 100%)` reproduces the original rendering, so that is the filling wrapper.

A function is accepted so that the inner slot can carry ink of its own,
which then moves and scales with the element:

```typst
#tag("boxed", wrap: box.with(inset: 4pt, stroke: red))[Framed, and it moves framed.]
```

The function has to produce a `box` or a `block`.
Anything else is refused, naming the tag,
because nothing else becomes an addressable group in the output.

## What Tagging Costs

Wrapping is not free, and it is better read here than discovered on a slide.

**A tagged inline phrase can no longer break across lines**, so its paragraph may reflow.
That one is inherent: a group that CSS can translate cannot be split over two lines.
Tag a whole paragraph, or a short phrase that has room, rather than a long stretch
in the middle of one.

**A tagged heading shifts by a few points.**
A heading carries its own block spacing, that spacing sits at the wrapper's edge and is
trimmed there, and the wrapper contributes the generic paragraph spacing instead.
Typst does not expose the value animo would have to restore.
Tag the heading's text instead when the shift matters:

```typst
= #tag("title")[A heading that moves]
```

## Which Primitives Reach Which Tag Site

| Tag site                                    | Structural primitives | Continuous primitives |
| ------------------------------------------- | --------------------- | --------------------- |
| ordinary content                            | yes                   | yes                   |
| inside math                                 | yes                   | yes                   |
| a cetz `content()` element or fletcher node | yes                   | yes                   |
| raw cetz draw commands (`wrap: none`)       | unverified            | no                    |

The asymmetry has one cause.
The structural primitives are resolved by typst when it renders the slide,
so they work wherever a tag can wrap something at all.
The continuous primitives are resolved by the browser and need a group to address,
which typst emits only for labelled boxes and blocks.

`wrap: none` is therefore also the way to say
"this tag is only ever addressed structurally".
A timeline that asks for a continuous primitive on such a tag is refused at compile time,
rather than doing nothing at all in the browser much later.

A body that is not content, such as a stream of raw cetz draw commands,
can only be tagged with `wrap: none`, since a wrapper would destroy it.
Animo then hands the body back exactly as it came in and knows nothing else about it,
so nothing about such a tag is checked.
The area it belongs to is bounded by a `#region` around the whole canvas,
which is a later version.

## What Is Not Here Yet

`#region` is in the signature and does nothing,
so every tag is its own area for now and a structural change has nothing to reflow inside.
The structural primitives, `removed: true` and `#region` arrive together.

In the HTML output a tag site is emitted with its groups and its label,
and **no display state is applied**:
a `hidden: true` tag is visible there, and nothing moves between subslides.
The browser runtime is the next version.
The presentation PDF shows the whole state model today.
