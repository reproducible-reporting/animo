---
description: >-
  The structural primitives replace, remove, apply and reset:
  content that changes along the timeline, how the primitives compose,
  and the epochs they introduce.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Structural Animations

The demo deck for this page is
[`structural.typ`](https://github.com/reproducible-reporting/animo/blob/main/demos/structural.typ)
([HTML](https://reproducible-reporting.github.io/animo/demos/structural.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/demos/structural-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/demos/structural-handouts.pdf)).
It shows each structural primitive, how the primitives compose on one tag,
how they divide a slide into epochs, and the box that a tag reserves for changing content.

The [continuous primitives](continuous.md) change how content is shown.
The structural primitives on this page change the content itself.
They decide what typst lays out at a tag site and how typst styles that content.

```typst
#slide(
  animation: {
    import anim: *
    sub(apply("claim", text.with(fill: red)))
    sub(replace("claim")[
      Actually the opposite holds. \
      Let's fill another line to make this replacement long enough to wrap.
    ])
    sub(reset("claim"))
  },
)[
  #tag("claim", wrap: block)[A short line.]

  This paragraph stays where it is on every subslide.
]
```

## Structural Animation Primitives

| Primitive             | Meaning                                                   |
| --------------------- | --------------------------------------------------------- |
| `replace(name, body)` | lay out `body` at the tag site instead of what is there   |
| `remove(name)`        | lay out nothing at the tag site                           |
| `apply(name, ..fns)`  | wrap the content in each function, the last one outermost |
| `reset(name)`         | lay out the body as written, without any wrapper          |

The `apply` primitive takes **functions only**, such as `text.with(fill: red)`, `emph`,
or any custom function you provide.
Named style properties, as in `apply("x", fill: red)`, are refused.
Animo does not look inside content, so Animo cannot know which `set` rule a property belongs to.
A function such as `text.with(fill: red)` states the element that the property belongs to.

Two patterns come up often:

- To **insert** content that is not in the body,
  put a tag with an empty body, such as `#tag("slot")[]`, in the body of the slide.
  Then fill the tag with `replace("slot")[..]` in the timeline.
- To **bring in** content that is in the body,
  tag the content as usual and call `reset` on the tag in the subslide where it should appear.
  A tag whose first structural primitive is `reset`
  [starts removed](tags.md#initial-state-of-tagged-content),
  so the content is absent until that subslide.

## How They Compose

The content of a tag has two parts, and the primitives set each part separately.
The first part is **what is laid out** (the body, a replacement or nothing).
The second part is **the wrappers** that `apply` puts around it.

- `replace` and `remove` set what is laid out, and keep the wrappers.
- `apply` adds wrappers, which stay around whatever is laid out now or later.
- `reset` sets both parts, so the body is laid out again without any wrapper.
- None of the structural primitives changes the [display state](continuous.md),
  so a tag that was moved, scaled or hidden stays moved, scaled or hidden.
- Animo applies the primitives in the order they are written,
  both within one `sub` call and across several `sub` calls.

The table below follows one tag through a timeline.
The first row is the body of the slide, and each further row is one subslide.

| Code                                | Laid out at the tag site                       |
| ----------------------------------- | ---------------------------------------------- |
| the body `#tag("x")[B]`             | B                                              |
| `sub(apply("x", emph))`             | B, emphasised                                  |
| `sub(replace("x")[R])`              | R, emphasised, because the wrapper stays       |
| `sub(apply("x", strong))`           | R, emphasised and then strong                  |
| `sub(remove("x"))`                  | nothing, but the two wrappers are kept         |
| `sub(replace("x")[S])`              | S, emphasised and then strong                  |
| `sub(reset("x"))`                   | B, without wrappers                            |
| `sub(apply("x", emph), reset("x"))` | B, because the `reset` comes after the `apply` |

One subslide can change the content of a tag and also move the tag.
For example, `sub(replace("eq")[..], move("eq", dx: 1cm))` replaces the content of `eq`
and moves the tag one centimeter to the right.
While the old content fades out and the replacement fades in,
both of them move to the right together, so the audience sees a single movement.

When one name tags several sites,
every site of that name gets the same replacement and the same wrappers.

## Epochs

An **epoch** is a run of consecutive states of a slide in which typst lays out the same content.
A new epoch begins at every subslide that contains at least one structural primitive.
The slide starts in epoch 0.

```typst
animation: {
  import anim: *
  sub(reveal("a"))         // state 1, epoch 0
  sub(replace("a")[new])   // state 2, epoch 1
  sub(move("a", dx: 1cm))  // state 3, epoch 1
  sub(remove("b"))         // state 4, epoch 2
}
```

The number of epochs determines what content changes cost,
because typst lays out the slide once for every epoch.
The states inside one epoch share that layout,
and differ only in how they show it, such as visibility, position and scale.
A slide without structural primitives has a single epoch, so typst lays it out only once.
See [Performance](performance.md) for the numbers.

## Box Reserved by a Changing Tag

A tag whose content changes reserves a box that is large enough for the content of every epoch.
Animo takes the largest width and the largest height separately,
and lays out the content of each epoch inside that box.
Because the box has the same size in every epoch,
the rest of the slide stays where it is when the content of the tag changes.
A tag whose content never changes reserves no box, and typst lays out its content at its natural
size.

- A tag **between paragraphs** fills the width of its container.
  The height of the tag is the height of its tallest content, laid out at that width.
  A replacement that needs more lines wraps inside that height.
- A tag **on a line** is as wide as its widest content.
  Its box reaches as far above the baseline as the tallest content,
  and as far below the baseline as the deepest content,
  so the line around the tag stays where it is.
  Content on a line never wraps inside the box,
  so a long replacement stays on one line and can run past the edge of its container.
  Use a tag on a line only for short content.

Under [`wrap: auto`](tags.md#what-auto-measures),
a tag whose body is a single paragraph of text counts as a tag **on a line**.
The reason is that `wrap: auto` checks whether the body breaks the line it is put in,
and a paragraph of text does not break that line.
When the replacement of such a tag should wrap, give the tag `wrap: block`,
as the example at the top of this page does.

The reserved box shows empty space while the content is smaller than the box.
For example, a tag whose first content is short and whose last content is long
shows a gap in its early states.

Because the box keeps its size in every epoch, a removed tag takes as much space as a hidden tag.
Outside a region, `remove` therefore frees no more space than `hide`.
The `remove` primitive is meant for a tag inside a [region](regions.md),
where the content that follows the removed tag fills the freed space.

A tag with `wrap: none` has no container, so the tag cannot reserve a box.
A structural primitive may change such a tag only inside a [region](regions.md),
because the region lays out all of its content again around the change.
Animo refuses a structural primitive on a `wrap: none` tag outside a region,
in every output type.
The error message names the two fixes:
give the tag a wrapper (`wrap: auto`, `box` or `block`), or put a region around the tag.

## What a Structural Step Looks Like

In the HTML presentation, a step to a subslide with a structural primitive is a **dissolve**.
The outgoing content fades out while the incoming content fades in,
and each version stays at its own position.
Nothing outside the changed area moves.

A dissolve suits a `replace` whose new text is unrelated to the old text,
because the audience sees one statement turn into another.
A dissolve does not suit content that only *shifts*.
During the dissolve, two copies of the same words appear a few pixels apart,
which looks like a smear rather than a movement.
A typical case is a small edit near the start of a long paragraph.
All text after the edit shifts a little,
so the old and the new copy of that text overlap with a small offset.

There are two ways to avoid such a smear:

- Name the [morph](morphs.md) transition on the primitive.
  A morph moves the content that shifts instead of dissolving it.
- Put a [region](regions.md) around the content that is replaced as a whole,
  and keep the content that only shifts outside that region.

The example below shows the second way:

```typst
#slide(
  animation: {
    import anim: *
    sub(replace("claim")[A claim long enough to make the rest of the paragraph reflow.])
  },
)[
  #region[
    #tag("claim")[A short claim.]
    The rest of this paragraph reflows around the replacement,
    so the whole region takes part in the dissolve.
  ]

  This paragraph is outside the region, so it stays out of the dissolve.
]
```

When the presenter steps backwards, the HTML presentation shows exactly the earlier rendering.
A [deep link](presenting.md#the-position-is-in-the-url) to a subslide in a later epoch
shows that epoch at once, without a dissolve.

The dissolve starts after the `delay:` of the structural primitive and lasts for its `duration:`.
When the primitive has no `duration:` argument,
the dissolve lasts for the `primitive-duration` of the deck.
A `duration:` of zero swaps the content at once (a hard cut):

```typst
sub(replace("claim", duration: 0)[The second answer.])
```

The dissolve is the `crossfade()` [transition](reference.md#transitions).
The `transition:` argument of a structural primitive uses `crossfade()` by default,
and also accepts `morph()`.
Animo refuses a transition that moves a whole slide, such as a push, in this argument.
