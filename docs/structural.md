---
description: >-
  The structural primitives replace, remove, apply and reset:
  content that changes along the timeline, how the primitives compose,
  the epochs they introduce, and what the handout keeps of them.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Structural Animations

The example deck for this page is
[`content.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/content.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/content.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/content-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/content-handouts.pdf)).
It illustrates the four structural animation primitives, `replace`, `remove`, `apply` and `reset`, with and without a region.

The [continuous primitives](continuous.md) change how content is shown.
The four on this page change the content itself:
what typst lays out at a tag site, and how it is styled.

```typst
#slide(
  animation: {
    import anim: *
    sub(apply("claim", text.with(fill: red)))
    sub(handout: true, replace("claim")[
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
| `reset(name)`         | back to the body as written, with every wrapper dropped   |

`apply` takes **functions only**, such as `text.with(fill: red)`, `emph`, or one of your
own. Named style properties, as in `apply("x", fill: red)`, are refused:
Animo does not look inside content, so it cannot know which `set` rule a property belongs
to. Wrapping with `text.with(..)` leaves no room for ambiguity.

Two patterns come up often:

- **Inserting** content that is not in the body is `replace` on an empty tag:
  `#tag("slot")[]` in the body, and `replace("slot")[..]` in the timeline.
- Content that **is** in the body but starts out absent is a plain `#tag` the timeline resets.
  The `reset` is both what says the tag starts removed and the subslide that brings it in.

## How They Compose

A tag's content has two parts the primitives set independently:
**what is laid out**, which is the body, a replacement or nothing,
and **the wrappers around it**.

- `replace` and `remove` set what is laid out, and keep the wrappers.
- `apply` adds wrappers, around whatever is laid out now or later.
- `reset` sets both: the body, and no wrappers.
- None of the four touches the display state,
  so a moved, scaled or hidden tag stays that way.
- Operations are applied in the order they are written,
  within one `sub` as well as across several.

Stepping through one tag makes the rules concrete:

| Step                                | Laid out at the tag site                 |
| ----------------------------------- | ---------------------------------------- |
| the body `#tag("x")[B]`             | B                                        |
| `sub(apply("x", emph))`             | B, emphasised                            |
| `sub(replace("x")[R])`              | R, emphasised: the wrapper stays         |
| `sub(apply("x", strong))`           | R, emphasised and then strong            |
| `sub(remove("x"))`                  | nothing, while the two wrappers are kept |
| `sub(replace("x")[S])`              | S, emphasised and then strong            |
| `sub(reset("x"))`                   | B, as the body declares it               |
| `sub(apply("x", emph), reset("x"))` | B: the reset comes second                |

A subslide may change a tag's content and move it at the same time:
`sub(replace("eq")[..], move("eq", dx: 1cm))` lays the replacement out a centimetre to the
right, in the rendering that leaves as well as in the one that arrives,
so the two stay registered and it reads as one movement.

Where one name tags several sites, every site receives the same replacement and the same
wrappers.

## Epochs

An **epoch** is a run of consecutive states in which no content changes,
and a new one begins at every subslide that holds at least one of the four primitives.

```typst
animation: {
  import anim: *
  sub(reveal("a"))         // state 1, epoch 0
  sub(replace("a")[new])   // state 2, epoch 1
  sub(move("a", dx: 1cm))  // state 3, epoch 1
  sub(remove("b"))         // state 4, epoch 2
}
```

Epochs determine what a content change costs.
Typst lays the slide out again for every epoch,
while the states inside one epoch differ only in how the same layout is shown.
A slide with no structural operation has one epoch and costs nothing extra.
See [Performance](performance.md) for the numbers.

## A Changing Tag Keeps Its Own Box

The rest of the slide does not move when a tag's content changes,
because the tag reserves room for the largest content it holds in any epoch,
separately for the width and the height, and lays each epoch out inside that box.
A tag whose content never changes reserves nothing and lays out exactly as before.

- A tag **between paragraphs** fills the width of its container
  and is as tall as its tallest epoch at that width.
  A replacement that wraps onto more lines reflows inside that height.
- A tag **on a line** is as wide as its widest epoch,
  and reserves the tallest reach above the baseline and the deepest below it,
  so the line it sits on stays where it is.
  Content on a line cannot wrap to fit the box: a longer replacement runs on past its edge.
  Inline tag sites are for short content.

A paragraph of one line is **on a line** as far as a tag can tell,
because [`wrap: auto`](tags.md#what-auto-measures) measures whether the body breaks
the line it is put in. So a tag around a short paragraph whose replacement is meant to wrap
needs `wrap: block`, as the example at the top of this page has.

The reserved room has a cost: a tag whose first content is short and whose last content is
long shows a gap in its early states.

Inside a tag's own box, starting removed and starting hidden look the same, since the box
keeps the room either way, and `remove` frees no space that `hide` would not.
`remove` is for where the freed space is meant to be taken up by something else,
which is inside a [region](regions.md).

A `wrap: none` tag has no box to reserve room with,
so its content changes and the layout around it follows.

## What a Structural Step Looks Like

A structural step is a **dissolve, not motion**:
the outgoing content fades out where the incoming content fades in,
and neither travels to meet the other.
Nothing outside the changed area moves at all.

A `replace` reads well this way, because the two texts are unrelated
and the dissolve reads as a change from one statement to another.
Content that merely *shifts* reads badly:
two copies of the same words a few pixels apart are a smear rather than a movement.
A small edit near the start of a long paragraph is the case to avoid,
since everything after the edit moves a little and ghosts against itself.

Avoiding this is up to the author.
Put a [region](regions.md) around what is replaced wholesale,
and keep out of it whatever only shifts as a consequence:

```typst
#region(
  import anim: *
  sub(reveal("claim"))
)[
  #tag("claim")[A short claim.]
  Everything in this region will be redrawn as a whole,
  meaning that the paragraph will reflow.
]

Text that should not be dragged into the crossfade.
```

Stepping backwards returns exactly the earlier rendering,
and a deep link into a later epoch shows that epoch without animating into it.

## Selecting States for Handouts

`replace` and `remove` **destroy** what they replace or remove,
so a slide whose content changes loses its earlier content in the handout,
which shows one state per slide.
`sub(handout: true, ..)` is the only way to keep an earlier state:

```typst
sub(handout: true, replace("claim")[The first answer.])
sub(replace("claim")[The final answer.])
```

This handout has two pages for the slide, one per answer.

The content a slide starts out with is destroyed the same way,
and it has no `sub` to keep it, so its flag is written on the slide.
That is the case to watch for whenever a timeline **restores** what the body hides or
removes, because the handout then shows the completed slide and not the initial state the
timeline filled in.
[What the Handout Keeps](continuous.md#selecting-states-for-handouts) is the flag itself.
