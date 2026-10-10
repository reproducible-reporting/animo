---
description: >-
  The three output types of one source file, the command lines that produce them,
  and the file formats that the static output types export to.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Output Types

The example deck for this page is
[`tour.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/tour.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/tour.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/tour-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/tour-handouts.pdf)).
The commands below compile a deck in `talk.typ` to each output type:

```bash
# HTML presentation
typst compile --format html --features html talk.typ talk.html

# Static presentation (one page per subslide)
typst compile --input animo=presentation talk.typ talk-presentation.pdf

# Static handouts (final state per slide), the default when --input animo= is absent
typst compile talk.typ talk-handout.pdf
```

The value of `--input animo=` selects a static output type,
and it is either `presentation` or `handout`.
Any other value raises an error, so a typo never produces handouts without a warning.

By default, typst also uses the fonts installed on the machine, and these differ between machines.
Add `--ignore-system-fonts` to make typst use only the fonts it embeds,
so that every machine renders the deck identically.
The examples bundled with Animo use only these embedded fonts.

| Output type         | What it shows                                        |
| ------------------- | ---------------------------------------------------- |
| HTML presentation   | the deck, animated, in a browser                     |
| Static presentation | one page per subslide, for a venue without a browser |
| Static handouts     | one page per slide, for printing or distributing     |

A slide without `sub` calls has a single state, so it takes one page in both static output types.
A slide with subslides takes one page per subslide in the static presentation.
In the static handouts, the same slide takes one page for its final state
and one for each state that has `handout: true`.
See [The `handout` Flag](handouts.md#the-handout-flag) for the details.

Each page shows only the part of the canvas that is inside the viewport in that state.
A slide that pans therefore shows a different part of its canvas on each page.
The handout pages show only the parts of the canvas that are in view in the states they keep.

Both static output types **ignore all timing**, because a page cannot change over time.
Typst writes the same pages with or without the arguments
[`wait:`, `hold:`, `delay:` and `duration:`](continuous.md#timing)
and the [slide transitions](slides.md#slide-transitions).
For example, a deck that plays itself in a browser and a deck that waits for the presenter
produce identical pages, if they differ only in these arguments.

## Content per Output Type

`output-type()` returns the output type being compiled:
`"html"` for the HTML presentation, `"presentation"` for the static presentation
and `"handout"` for the static handouts.
The last two strings are the values that `--input animo=` accepts.
Because `output-type()` is a context function, a call to it has to be inside `context`.
`output-type()` returns the same value in a slide's body, in its overlay and background,
and outside every slide.
A deck can therefore show content in some output types only.
The hint below appears only in the HTML presentation:

```typst
#let hint = context if output-type() == "html" {
  place(bottom + left, text(size: 0.6em)[Use the arrow keys to step through the talk.])
}
```

The `target()` function of typst cannot replace `output-type()` inside a slide.
In the HTML presentation, Animo lays out each slide inside an `html.frame`,
and inside such a frame `target()` returns `"paged"`.

## File Formats of the Static Output Types

A static output type is a paged *mode*, which decides which pages the document contains.
The `--format` flag of typst decides the file format in which typst writes those pages.
The two choices are independent, so either static output type exports to PDF, SVG or PNG.
SVG suits embedding a page in another document,
and PNG suits a program that accepts only raster images.

```bash
# The handout pages as SVG, one file per page
typst compile -f svg talk.typ 'talk-handout-{p}.svg'

# The presentation pages as SVG, the same way
typst compile -f svg --input animo=presentation talk.typ 'talk-presentation-{p}.svg'

# The handout pages as PNG at 300 dots per inch
typst compile -f png --ppi 300 talk.typ 'talk-handout-{p}.png'
```

Typst writes each page of an SVG or PNG export to a separate file.
The output path of such an export therefore contains a page number template,
and typst refuses to export more than one page without it.
A PDF file holds all pages, so its output path has no template.
In the template, `{p}` is the page number.
`{0p}` is the same number, padded with zeros to the number of digits in the page count.
