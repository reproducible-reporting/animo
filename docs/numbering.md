---
description: >-
  What a slide is called and what one of its subslides is called,
  how a deck shows either of them, and where the number goes.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Numbering

The example deck for this page is
[`numbering.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/numbering.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/numbering.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/numbering-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/numbering-handouts.pdf)).
It illustrates the three numbering functions in one deck.

A number on a slide can be useful for the audience:
someone who wants to ask a question about a specific subslide needs a way to reference it.
Animo gives a deck three functions to build such a handle,
and it is up to you how to use these functions to format and position (sub)slide numbers.

| Function                 | What it gives                                           |
| ------------------------ | ------------------------------------------------------- |
| `slide-number()`         | the number of the slide, or `none` on an unnumbered one |
| `slide-count()`          | how many slides of the deck carry a number              |
| `per-subslide(it => ..)` | content laid out once per subslide, one of them shown   |

## The Slide Number

`numbered:` on `#slide` decides whether a slide is **counted**.
A title or section slide is typically `numbered: false`.
It says nothing about whether a number is shown.

`slide-number()` and `slide-count()` read that counter.
Both are context functions and hand back plain integers,
so anything can be computed from them.

```typst
#context [Slide #slide-number() of #slide-count()]
```

On a slide that `numbered: false` leaves out, `slide-number()` is **`none`** rather than
the number of the slide before it, so one footer can serve a whole deck:

```typst
#let footer = context {
  let number = slide-number()
  if number != none {
    place(bottom + right, [#number / #slide-count()])
  }
}
```

Navigation does not use this counter.
A presenter walks through a title slide whether or not it carries a number,
so the position in the deck, as referenced by the URL, is counted separately over every slide.

## The Subslide Number

A subslide number is a callback rather than a counter.
The HTML output renders one rendering per [epoch](structural.md#epochs),
and a rendering covers every state that shares its content,
so a number written into it would be one number for a whole run of subslides.

`per-subslide` lays its callback out **once per subslide**,
stacks the renderings in a container the size of the largest of them,
and the browser shows the one belonging to the subslide on screen.
A page of a paged output knows its own single state, so it just carries that state's rendering.
Despite these different mechanisms, all three output types agree.

```typst
#per-subslide(it => [#it.number of #it.count])
```

The callback receives the **subslide numbers**, one dictionary of four, listed in the
[Reference](reference.md#per-subslide).
`number` counts from **one**, where the URL fragment addresses state 0 of a slide:
the fragment is an address, while the number is what the audience reads on the slide.
`step` and `steps` count every subslide of every slide, unnumbered slides included,
because they measure the talk rather than its numbering.
They are named for the presenter's steps, and a step is the transition from one subslide to the
next, so `steps` counts subslides rather than transitions.

A callback may return `none`, which lays nothing out for that subslide.
This writes a number only where it carries information:

```typst
#per-subslide(it => if it.count > 1 [ (#it.number/#it.count)])
```

## A Progress Bar

`step` and `steps` are what an indicator spanning the whole talk is measured against,
and the callback returns content, so the indicator can be anything typst draws.

```typst
#per-subslide(
  it => rect(width: 100% * (it.step - 1) / (it.steps - 1), height: 4pt, fill: blue),
  wrap: block,
)
```

A rendering that states a ratio needs a container width to be a ratio of,
and only a filling container has one.
The `rect` above is block-level, so `auto` chooses the filling block as well,
and `wrap: block` states the requirement rather than changing the outcome.
The argument is needed for a rendering that is inline and states a ratio,
such as a bar drawn as `box(width: 100% * f, ..)`.
A stack of inline renderings measures them unbounded, where a `100%` width resolves to zero,
so such a bar lays out with no width at all.

## Where a Number Goes

Animo has no header or footer machinery, so a recurring element is a wrapper around
`#slide` that fills one of the two [outer layers](slides.md#backgrounds-and-overlays).

**Put it in the overlay.**
An overlay is one rendering per slide, where the body is one rendering per *epoch*,
so a stack of one rendering per subslide is paid for once in an overlay and once per epoch
in the body. The overlay also belongs to the viewport, so a [pan](viewport.md) leaves it
where it is, where a footer placed in the body travels with the canvas.

## What a Handout Shows

A handout page carries the number of the **state it kept**,
which is not the number of the page it is.
A slide whose third subslide is the one the handout keeps shows "3 of 3" on a page that may
be the seventh of the handout.
Someone who noted a number during the talk looks for that number,
rather than for the position of the page within the handout.

## What This Costs

A stack is one rendering per subslide,
so it is the only construct in Animo whose cost grows with a slide's states rather than
with its epochs.
For a number that is a few glyphs it is a few percent of a deck.
See [What a Number Costs](performance.md#what-a-number-costs) for empirical tests.
