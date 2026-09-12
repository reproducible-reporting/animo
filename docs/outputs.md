---
description: >-
  The four outputs of one source file, the command lines that produce them,
  and the live preview that typst serves itself.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# The Four Outputs

One source file, one compile per output.
The HTML target is detected automatically with `target()`;
the paged modes are selected with `--input animo=`, and default to the handout.

```bash
# HTML presentation
typst compile --format html --features html talk.typ talk.html

# Presentation PDF (one page per subslide)
typst compile --input animo=presentation talk.typ talk-presentation.pdf

# Handout PDF (final state per slide), the default for paged output
typst compile talk.typ talk-handout.pdf

# Handout SVG (one file per page)
typst compile -f svg talk.typ 'talk-{p}.svg'
```

A mistyped mode is an error rather than a handout that looks like a success.

Multi-page SVG export fails without a page number template in the output path,
which is why the last command line is the odd one out.
`{p}` is the page number and `{0p}` is the same number padded to the page count.

Add `--ignore-system-fonts` to every command to make a rendering reproducible
between machines. Animo itself uses only the fonts typst embeds.

## What Each Output Is

| Output            | What it shows                                        |
| ----------------- | ---------------------------------------------------- |
| HTML presentation | the deck, animated, in a browser                     |
| Presentation PDF  | one page per step, for a venue without a browser     |
| Handout PDF       | one page per slide, for printing                     |
| Handout SVG       | the handout pages, for embedding in another document |

A slide with no `sub` call has one state, so it is one page in both paged outputs.
The two stop being the same as soon as a slide has subslides:
the presentation gets a page per step and the handout keeps the states that asked for one.

## Presenting and the Live Preview

The keys, the position in the URL and the `typst watch` loop are on their own page:
[Presenting](presenting.md).

## An Example

The deck the test suite compiles to all four outputs on every build:

```typst title="examples/tour.typ"
--8<-- "examples/tour.typ"
```
