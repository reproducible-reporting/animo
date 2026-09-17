# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Typst sources the feature tests compile, written once and shared between the tiers.

The same deck has to be looked at from the paged side and from the browser side for the
cross-target invariant to say anything, so a deck that only one tier can build is a deck
that cannot be compared.

These are internal tests, so they import `/src/lib.typ` by absolute path.
Everything a reader is meant to copy imports `@preview/animo:0.1.0` instead.
"""

__all__ = ("PREAMBLE", "deck", "marks_deck")


PREAMBLE = '#import "/src/lib.typ": *\n'
"""The import every generated deck starts with."""


def deck(
    *slides: str,
    width: str = "16cm",
    height: str = "9cm",
    margin: str = "1cm",
    timing: str = "",
    preamble: str = "",
) -> str:
    """A document with the deck show rule and one `#slide` call per argument.

    Parameters
    ----------
    slides
        The text of each slide call, without the leading `#`, e.g. `slide[body]`.
    width, height, margin
        The deck's shape, as typst length literals.
    timing
        Further arguments for the show rule, as typst source,
        e.g. `primitive-duration: 0.2, easing: "linear"`.
    preamble
        Source placed between the deck's show rule and its first slide.
        An import of a third-party package and the definitions a slide body calls
        belong there.

    Returns
    -------
    source
        The document, ready to be written and compiled.
    """
    shape = f"width: {width}, height: {height}, margin: {margin}"
    if timing:
        shape += f", {timing}"
    body = "\n\n".join("#" + slide for slide in slides)
    return f"{PREAMBLE}#show: animo.with({shape})\n\n{preamble}{body}\n"


# Three filled squares at offsets that are easy to state and easy to find in a raster.
# They are rectangles rather than glyphs on purpose: the cross-target invariant is about
# where content lands, and typst's rasteriser and chromium's SVG renderer do not have to
# agree on the pixels of a letter to agree on the corners of a box.
MARKS = {
    "red": ("#ff0000", "0cm", "0cm"),
    "green": ("#00ff00", "9cm", "3cm"),
    "blue": ("#0000ff", "4cm", "5.5cm"),
}

MARK_SIZE = "1.5cm"


def marks_deck(**kwargs) -> str:
    """A one-slide deck of three filled squares at stated offsets from the body origin."""
    placements = "\n  ".join(
        f"#place(dx: {dx}, dy: {dy}, rect(width: {MARK_SIZE}, height: {MARK_SIZE}, "
        f'fill: rgb("{color}")))'
        for color, dx, dy in MARKS.values()
    )
    return deck(f"slide[\n  {placements}\n]", **kwargs)
