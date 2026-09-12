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

In this version a slide has exactly one step,
so the presentation and the handout are the same pages.
They stop being the same as soon as a slide has subslides.

## Live Preview

Typst serves the HTML and reloads the browser itself, so animo ships nothing for this:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

Every successful recompile pushes a reload to the browser.
The reload is a plain `location.reload()`, so the URL survives it, fragment included,
and a deck comes back on the slide the author was looking at.

The flags of the built-in server are `--port` (the first free port in 3000-3005 by
default), `--no-serve` and `--no-reload`.

## Presenting

The HTML deck is stepped with the keyboard or with a click:

| Key                                                     | Does                |
| ------------------------------------------------------- | ------------------- |
| `→`, `↓`, `Page Down`, `Space`, `Enter`, `n`, any click | one step forward    |
| `←`, `↑`, `Page Up`, `Backspace`, `p`                   | one step backward   |
| `Home`, `End`                                           | the first, the last |

The position is in the URL fragment as `#<slide>.<state>`,
written with `history.replaceState` so that stepping through a deck
leaves no browser history behind.
Opening a fragment restores that position without animating into it,
which is what makes a deep link and a live-preview reload land on the same picture.

The slide fills the browser window at the deck's aspect ratio,
and everything inside it is measured in typst points at any window size,
because the canvas is scaled as a whole rather than laid out in pixels.

## An Example

The deck the test suite compiles to all four outputs on every build:

```typst title="examples/tour.typ"
--8<-- "examples/tour.typ"
```
