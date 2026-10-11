---
description: >-
  How to number slides and subslides, how to draw a progress bar,
  and where on the slide to put a number.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Numbering

The demo deck for this page is
[`numbering.typ`](https://github.com/reproducible-reporting/animo/blob/main/demos/numbering.typ)
([HTML](https://reproducible-reporting.github.io/animo/demos/numbering.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/demos/numbering-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/demos/numbering-handouts.pdf)).
It illustrates the three numbering functions in one deck.

A number on a slide helps the audience to refer to it,
for example when someone asks a question about a specific subslide.
Animo provides three functions that give you these numbers.
You decide how to format the numbers and where to place them.

| Function                 | What it gives                                                    |
| ------------------------ | ---------------------------------------------------------------- |
| `slide-number()`         | the number of the current slide, or `none` if it is not numbered |
| `slide-count()`          | how many slides of the deck are numbered                         |
| `per-subslide(it => ..)` | content for each subslide, of which the current one is visible   |

## The Slide Number

Animo counts the slides of a deck with a counter.
The `numbered:` argument of `#slide` decides whether the counter **counts** that slide,
and it defaults to `true`.
A title slide or a section slide typically has `numbered: false`.
Animo does not show the number anywhere by itself.

`slide-number()` returns the value of the counter on the current slide,
and `slide-count()` returns the number of slides the counter counts in the whole deck.
Both functions return plain integers, so you can compute with them.
Both are context functions, which means that you call them inside a `context` expression:

```typst
#context [Slide #slide-number() of #slide-count()]
```

On a slide with `numbered: false`, `slide-number()` returns **`none`**,
and not the number of the slide before it.
A footer can test for `none` and show nothing on such a slide,
so the same footer works on every slide of the deck:

```typst
#let footer = context {
  let number = slide-number()
  if number != none {
    place(bottom + right, [#number / #slide-count()])
  }
}
```

Navigation in the HTML presentation does not use this counter.
The URL holds the position of a slide in the deck, and that position counts every slide,
because the presenter also passes through the slides without a number.

## The Subslide Number

You get the subslide number from a callback,
which is a function you pass to `per-subslide`.
A counter would not work, because of how Animo builds the HTML presentation.
Typst lays out each [epoch](structural.md#epochs) of a slide once,
where an epoch is a run of subslides in which no content changes.
The browser then animates between the subslides of an epoch without a new layout.
A number in that layout would be the same on every subslide of the epoch.

`per-subslide` calls the callback **once per subslide** and lays out each result.
Each laid-out result is called a rendering.
`per-subslide` reserves room for the largest rendering,
so the content around the number stays in place on every subslide.
In the HTML presentation, all renderings are in the page,
and the browser makes only the rendering of the current subslide visible.
In the static presentation and the handouts, each page shows a single subslide,
so Animo puts only the rendering of that subslide on the page.
All three output types therefore show the same number on the same subslide.

```typst
#per-subslide(it => [#it.number of #it.count])
```

The callback receives one argument, a dictionary called the **subslide info**.
See the [Reference](reference.md#per-subslide) for all its keys.
The key `number` is the position of the subslide within its slide, counting from **one**,
and the key `count` is how many subslides the slide has.
The URL fragment of the HTML presentation counts the subslides of a slide from zero instead,
as `#3.0` for the first subslide of slide 3.
The fragment is an address for the browser,
while `number` is meant for the audience to read.

The key `step` is the position of the subslide within the whole deck,
and the key `steps` is how many subslides the deck has.
Both count the subslides of every slide, including the slides with `numbered: false`,
because they measure progress through the talk rather than the slide numbers.
Despite their names, `step` and `steps` count subslides.
The presenter takes `steps - 1` steps to get from the first subslide of the deck to the last.

A callback may return `none`, and then nothing is laid out for that subslide.
The following callback uses this to show a subslide number
only on a slide with more than one subslide:

```typst
#per-subslide(it => if it.count > 1 [ (#it.number/#it.count)])
```

## A Progress Bar

A progress bar for the whole talk computes its length from `step` and `steps`.
Because the callback returns content, the progress bar can be anything typst can draw.

```typst
#per-subslide(
  it => rect(width: 100% * (it.step - 1) / (it.steps - 1), height: 4pt, fill: blue),
  wrap: block,
)
```

The `wrap:` argument of `per-subslide` chooses the container that holds the renderings.
With `wrap: block`, the container is a block that fills the width of the slide.
With `wrap: box`, the container is an inline box that is only as wide as the renderings.
The default, `wrap: auto`, chooses a block for block-level content and a box otherwise.

A width given as a percentage, such as `100%`,
needs a container that fills the width of the slide,
because a box has no width of its own to take a percentage of.
Inside a box, a `100%` width resolves to zero, and the progress bar would be invisible.
The `rect` above is block-level, so `wrap: auto` would also choose a block.
The `wrap: block` argument in this example only makes that choice explicit.
For an inline progress bar, such as one drawn as `box(width: 100% * f, ..)`,
the `wrap: block` argument is required.

## Where a Number Goes

Animo has no header or footer machinery.
To repeat a number on every slide, write a wrapper function around `#slide`
that puts the number in one of the two [outer layers](slides.md#backgrounds-and-overlays),
which are the background and the overlay.

**Put the number in the overlay.**
Typst lays out the overlay once per slide,
but it lays out a [region](regions.md) in the body once per *epoch*.
A `per-subslide` in the overlay therefore costs its renderings once,
while a `per-subslide` in a region costs them once for every epoch of the slide.
The overlay is also fixed to the viewport,
so the number stays in place while a [pan](viewport.md) moves the canvas.
A footer placed in the body moves along with the canvas.

## What This Costs

A `per-subslide` holds one rendering per subslide.
It is therefore the only construct in Animo whose cost grows with the number of subslides
of a slide, rather than with its number of epochs.
A slide number and a subslide number of a few characters each
make the HTML page and the compile time a few percent larger.
See [What a Number Costs](performance.md#what-a-number-costs) for the measurements.
