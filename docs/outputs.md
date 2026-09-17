---
description: >-
  The three output types of one source file, the command lines that produce them,
  and why the file format is not one of them.
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
It is compiled to every output type from one source file as follows:

```bash
# HTML presentation
typst compile --format html --features html talk.typ talk.html

# Static presentation (one page per subslide)
typst compile --input animo=presentation talk.typ talk-presentation.pdf

# Static handouts (final state per slide), the default for paged output
typst compile talk.typ talk-handout.pdf
```

A mistyped mode raises an error instead of silently producing a handout.
Add `--ignore-system-fonts` to make a rendering reproducible between machines.
Examples bundled with Animo use only the fonts that typst embeds.

| Output type         | What it shows                                        |
| ------------------- | ---------------------------------------------------- |
| HTML presentation   | the deck, animated, in a browser                     |
| Static presentation | one page per subslide, for a venue without a browser |
| Static handouts     | one page per slide, for printing or distributing     |

A slide with no `sub` call has one state, so it is one page in both static output types.
The two stop being the same as soon as a slide has subslides:
the presentation gets a page per subslide, and the handout keeps the states that
[asked for one](continuous.md#selecting-states-for-handouts).

Every page is a viewport, so a slide that pans shows a different part of its canvas on each
page, and the handout shows no more of the canvas than the states it keeps.

Everything about time is **absent rather than approximated** in both static types.
A page has no clock, so [`wait:`, `hold:`, `delay:` and `duration:`](continuous.md#timing)
say nothing there, and neither does [`transition:`](slides.md#slide-transitions).
A deck that plays itself in a browser is the same pages on paper as a deck that waits for a
presenter, to the pixel.

## The File Format Is Not an Output Type

A static output type is a paged *mode*, and it says which pages exist.
The file format is typst's own `--format` flag, and it says how those pages are written.
The two are independent, so either static type exports to PDF, SVG or PNG:
SVG embeds a page in another document, and PNG serves consumers that need a raster image.

```bash
# The handout pages as SVG, one file per page
typst compile -f svg talk.typ 'talk-handout-{p}.svg'

# The presentation pages as SVG, the same way
typst compile -f svg --input animo=presentation talk.typ 'talk-presentation-{p}.svg'

# The handout pages as PNG at 300 dots per inch
typst compile -f png --ppi 300 talk.typ 'talk-handout-{p}.png'
```

Multi-page SVG and PNG export fails without a page number template in the output path,
which is why those command lines carry one and the PDF ones do not.
`{p}` is the page number and `{0p}` is the same number padded to the page count.
