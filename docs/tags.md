---
description: >-
  A tag marks a part of a slide so that a timeline can address it by name.
  What container a tag site becomes, what tagging costs, and where a tag may sit.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Tags

The example deck for this page is
[`hello.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/hello.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/hello.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/hello-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/hello-handouts.pdf)).
It illustrates most concepts explained below with one slide, one tag and one subslide.

A tag marks a part of a slide and names it.
The `animation` defines the animation within one slide through _subslides_, which reference the tags by name.
Each subslide specifies what happens to tagged contents to arrive at a new state.

```typst
#slide(animation: {
  import anim: *
  sub(reveal("caveat"))
})[
  A short claim.

  #tag("caveat")[With a caveat.]
]
```

## Initial State of Tagged Content

Nothing at the tag site says what state it starts in.
The timeline says it, and a tag takes its initial state from the first operation that
addresses each of its two slots:

- a tag whose first **display** operation is `reveal` **starts hidden**:
  laid out, taking its space, and invisible.
  `caveat` above is one.
- a tag whose first **content** operation is `reset` **starts removed**:
  not laid out at all, so it takes no space until the `reset` brings it in.

The two are independent, so a tag the timeline resets and later reveals starts out both
removed and hidden.
Anything else starts visible and laid out as you wrote it.

## One Name, Several Places

The same tag name may be used several times within one slide.
The timeline then addresses all of them together, as if they were one element.
Every site of one name starts in the same state,
because that state is a property of the name in the timeline and not of a site.

The same name in a different slide does not interfere.
A tag reads the plan of the slide it appears in and of no other,
so a deck that wraps `#slide` in a function of its own changes nothing about how its tags
resolve.

A name the slide tags nowhere is refused rather than ignored,
so a misspelt name in a timeline is a compile error and not an operation that does nothing.

## A Name Is a Label

A tag name becomes the label of the group Animo emits,
which is the same namespace typst's own `<label>` syntax writes into.
A slide that tags `"figure"` and also writes `#box[..]<figure>` has two groups of one name,
and in the browser both move.
Animo cannot tell them apart, because in the output they are the same thing.
Keep the names of a slide's tags out of the labels that slide writes for itself.

Animo keeps its own names apart as well:
`animo-` is a reserved prefix, and a tag or region named with it is refused.

## What a Tag Site Becomes

A tag generally wraps its body with typst `#box` or `#block`,
because these are the only two elements that typst makes addressable in the browser.
The default `auto` wrapping usually does the right thing,
and the `wrap:` argument overrules it where a corner case requires a different wrapper.

| `wrap`     | Wrapper                                                                     |
| ---------- | --------------------------------------------------------------------------- |
| `auto`     | `#box` for an inline body, `#block(width: 100%)` for a block-level one      |
| `box`      | `#box`, the wrapper for inline contents                                     |
| `block`    | `#block(width: 100%)`, a wrapper for full-width contents                    |
| `none`     | no wrapper and no label, the body returned untouched                        |
| a function | the function builds the inner slot, and has to produce a `box` or a `block` |

The `none` option is occasionally useful for a tag that is only addressed by `reset` and `replace`,
because those operations do not need a wrapper like `move` or `scale`.
While `none` limits animation functionality, the absence of a wrapper allows for content flowing across lines within a paragraph.

A function is accepted so that the wrapping element can be styled,
which will also move and scale with the element:

```typst
#tag("boxed", wrap: box.with(inset: 4pt, stroke: red))[Framed, and it moves framed.]
```

### What `auto` Measures

The choice `auto` makes is a function of the body alone and never of the timeline,
so adding a `sub()` call in the animation cannot reflow a paragraph,
and every output type lays the slide out the same way.

What `auto` reads off the body is whether it is **inline or block-level** in typst's own sense.
Animo determines this by measuring whether the body pushes a zero-sized neighbour onto a line of
its own.
The length of the body never enters into the choice.
The measurement is unbounded, so a paragraph never wraps while it is being measured,
and a run of text is inline whether it is three words or three lines.
An explicit `\` linebreak in the body leaves it inline as well.

| The body is                                                 | The wrapper is        |
| ----------------------------------------------------------- | --------------------- |
| text, inline math, inline raw, a `box`                      | `#box`                |
| a display equation, a list, a heading, a raw block          | `#block(width: 100%)` |
| a `block`, a `rect`, a `circle`, an `image`, a cetz canvas  | `#block(width: 100%)` |
| a `table`, a `grid`, a `stack`, anything inside `align(..)` | `#block(width: 100%)` |
| several paragraphs                                          | `#block(width: 100%)` |

A `rect`, a `circle` and an `image` are block-level elements in typst,
so they take the filling block, while a `box` of the same size takes a `#box`.

The wrapper also decides what the continuous primitives mean on the tag.
A `#box` hugs its body, so `scale` scales about the body's own centre,
and the `relto:` anchor of `move` and `pan` reads the body's own top-left corner.
A `#block(width: 100%)` fills its container,
so those primitives read the centre and the corner of the container instead.
A `#block(width: 100%)` also keeps content centred that its container was centring,
because a wrapper at `width: auto` left-aligns such content.

## Tagging Limitations

**Tagged content with a wrapper can not break across lines**.
A group that CSS can translate cannot be split over two lines.
Tag a whole paragraph, or a short phrase that has room,
rather than a long stretch in the middle of a paragraph.

**A tagged heading shifts by a few points.**
A heading carries its own block spacing, that spacing sits at the wrapper's edge and is
trimmed there, and typst does not expose the value Animo would have to restore.
Tag the heading's text instead when the shift matters:

```typst
= #tag("title")[A heading that moves]
```

## Where a Tag May Sit

Anything typst lays out as content can be tagged.

Inside **math** a tag is an ordinary tag site:

```typst
$ a + #tag("b")[$b$] = c $
```

Inside a **cetz canvas** a tag goes on a `content()` element,
and inside **fletcher** on a node label, because both hold ordinary content:

```typst
#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (4, 0))
  content((4, 0), tag("lab")[Hi], anchor: "west")
})
```

**Raw cetz draw commands are refused.**
`grid((0, 0), (4, 2))` is an array of closures rather than content,
built where it is written, before any show rule exists that could resolve it for a subslide,
so a tag there could never be reached by any primitive.
Animo refuses it at the tag site rather than silently doing nothing in every output.

What to write instead is a figure that is a function of what it draws,
tagged as a whole and replaced:

```typst
#let scene(mesh: true) = cetz.canvas({
  import cetz.draw: *
  circle((0, 0), radius: 1)
  if mesh { grid((-2, -2), (2, 2), stroke: gray) }
})

#slide(
  animation: {
    import anim: *
    sub(replace("fig")[#scene(mesh: false)])
  },
)[
  #tag("fig")[#scene()]
]
```

Anything on the figure that has to move smoothly, or be revealed and hidden,
must be a typst content element with a tag.

The [Reference](reference.md#tag) has the table of which primitives reach which kind of
tag site.
In that table, `wrap: none` is the special case:
such a tag has no group, so nothing continuous can address it.
