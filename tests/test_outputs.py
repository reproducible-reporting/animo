# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 2: the three paged outputs of a static deck.

A static deck has no subslides, so the presentation and the handout are the same pages,
and saying so numerically is what proves that both go through one layout rather than two.
Everything else here is about the viewport: it is the page, it clips, and it carries the
background and the overlay.
"""

import numpy as np
from decks import deck
from harness import PagedRunner, assert_identical

# The deck is 16 by 9 centimetres, which is 453.54 by 255.12 points,
# and `PagedRunner.png` renders one pixel per point by default.
VIEWPORT = (255, 454)

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# One centimetre in points, which is one pixel at the default raster resolution.
CM = 28.3465


def has_color(page: np.ndarray, color: tuple[int, int, int]) -> bool:
    """Whether a raster holds at least one pixel of exactly this colour."""
    return bool((page == np.array(color, dtype=np.uint8)).all(axis=2).any())


def mark(dx: str, dy: str, color: str = "#ff0000") -> str:
    """A filled square placed at an offset from the body origin."""
    return f'#place(dx: {dx}, dy: {dy}, rect(width: 2cm, height: 2cm, fill: rgb("{color}")))'


def test_a_deck_is_one_page_per_slide_at_the_deck_size(paged: PagedRunner):
    """The viewport is the page, and its size is the deck's, not typst's default."""
    pages = paged.png(deck("slide[one]", "slide[two]", "slide[three]"))
    assert len(pages) == 3
    assert all(page.shape == (*VIEWPORT, 3) for page in pages)


def test_the_presentation_and_the_handout_are_identical_for_a_static_deck(paged: PagedRunner):
    """A deck without subslides gives the two modes nothing to differ about.

    A deck with subslides grows pages in the presentation and stops holding this,
    which is exactly when the two modes start meaning something different.
    """
    source = paged.typst.source(deck("slide[one]", f"slide[two {mark('3cm', '2cm')}]"))
    handout = paged.png(source)
    presentation = paged.png(source, mode="presentation")
    assert len(handout) == len(presentation) == 2
    for index, (first, second) in enumerate(zip(handout, presentation, strict=True)):
        assert_identical(first, second, what=f"the two modes on page {index + 1}")


def test_a_colour_background_fills_the_page(paged: PagedRunner):
    """The background is the page fill on paper, so it reaches the corners."""
    pages = paged.png(deck('slide(background: rgb("#ff0000"))[body]'))
    assert tuple(pages[0][0, 0]) == RED
    assert tuple(pages[0][-1, -1]) == RED


def test_a_content_background_covers_the_viewport_and_no_more(paged: PagedRunner):
    """An image background is not a page fill in either target, so it is drawn instead.

    It covers the viewport rather than the canvas, which is what keeps a background
    from being stretched over whatever the automatic canvas happened to become.
    """
    body = 'slide(background: rect(width: 100%, height: 100%, fill: rgb("#ff0000")))[body]'
    pages = paged.png(deck(body))
    assert tuple(pages[0][0, 0]) == RED
    # A 16 cm slide is 453.54 pt, so at one pixel per point the raster's last column lies only
    # half on the page, and a drawn background covers it only half. A page fill covers the
    # whole raster instead, which is why this pixel is one in from the corner.
    assert tuple(pages[0][-2, -2]) == RED


def test_content_outside_the_viewport_is_clipped_and_not_carried_over(paged: PagedRunner):
    """The rule that makes a slide a slide: no overflow to a next page, ever."""
    pages = paged.png(deck(f"slide[{mark('20cm', '1cm')}]"))
    assert len(pages) == 1
    assert not has_color(pages[0], RED)


def test_the_same_content_inside_the_viewport_does_appear(paged: PagedRunner):
    """The control for the previous test, which would otherwise pass on a blank page."""
    pages = paged.png(deck(f"slide[{mark('3cm', '1cm')}]"))
    assert has_color(pages[0], RED)


def test_the_margin_insets_the_body_and_not_the_viewport(paged: PagedRunner):
    """Placements start at the body's origin, and the deck's margin moves that origin."""
    without = paged.png(deck(f"slide[{mark('0cm', '0cm')}]", margin="0cm"))[0]
    with_margin = paged.png(deck(f"slide[{mark('0cm', '0cm')}]", margin="1cm"))[0]
    assert tuple(without[1, 1]) == RED
    assert tuple(with_margin[1, 1]) != RED
    # One centimetre is 28.35 points, and one point is one pixel here.
    assert tuple(with_margin[30, 30]) == RED


# The two outer layers.


def at(page: np.ndarray, x: float, y: float) -> tuple[int, int, int]:
    """The colour of the pixel at a position on the page, in centimetres from its corner."""
    return tuple(int(value) for value in page[round(y * CM), round(x * CM)])


# A background under the body under an overlay, each a square the others do not cover,
# so that one raster says which layer is where.
BACKDROP = '#place(rect(width: 100%, height: 100%, fill: rgb("#ff0000")))'
MIDDLE = '#place(dx: 2cm, dy: 2cm, rect(width: 4cm, height: 4cm, fill: rgb("#00ff00")))'
FRONT = '#place(dx: 3cm, dy: 3cm, rect(width: 2cm, height: 2cm, fill: rgb("#0000ff")))'


def layered(body: str = "", timeline: str = "") -> str:
    """The three overlapping layers, with whatever else the slide needs in its body."""
    extra = f", animation: {timeline}" if timeline else ""
    return (
        f"slide(background: [{BACKDROP}], overlay: [{FRONT}]{extra})[{body}{MIDDLE}]"
    )


def test_the_overlay_is_drawn_over_the_body_and_the_background_under_it(paged: PagedRunner):
    """The three layers, in one raster, each sampled where only it can be.

    The body is inset by the deck's margin and the two layers are not,
    because a layer belongs to the viewport rather than to the body.
    """
    page = paged.png(deck(layered()))[0]
    assert at(page, 0.5, 0.5) == RED, "the background is not behind everything"
    assert at(page, 6.5, 6.5) == GREEN, "the background is not behind the body"
    assert at(page, 4, 4) == BLUE, "the overlay is not in front of the body"


def test_a_colour_overlay_is_ink_over_the_slide_and_not_a_page_fill(paged: PagedRunner):
    """This is where the two arguments stop being symmetric.

    A background colour is the page's own `fill`, which is behind everything;
    an overlay colour is a layer of its own, so an opaque one covers the body.
    The second raster is the control: the same colour as a background leaves the body
    visible, so the first assertion is about the layer and not about the colour.
    """
    body = f"[{mark('2cm', '2cm')}]"
    over = paged.png(deck(f'slide(overlay: rgb("#0000ff")){body}'))[0]
    under = paged.png(deck(f'slide(background: rgb("#0000ff")){body}'))[0]
    assert not has_color(over, RED), "the overlay was drawn behind the body"
    assert at(over, 4, 4) == BLUE
    assert has_color(under, RED), "the control lost the body for another reason"


def test_a_layer_is_drawn_identically_on_every_page_of_a_slide(paged: PagedRunner):
    """One layer per slide has to reach every page the slide contributes.

    The slide has four states over two epochs, so the presentation gives it four pages
    that differ in the body alone, and the two layers have to be the same ink on each.
    """
    timeline = (
        "{ import anim: *\n"
        '  sub(hide("t"))\n'
        '  sub(replace("t")[a much longer replacement])\n'
        '  sub(reveal("t")) }'
    )
    source = deck(layered(body='#tag("t")[x]', timeline=timeline))
    pages = paged.png(source, mode="presentation")
    assert len(pages) == 4
    # A crop of each layer that the body never reaches, compared page by page rather than
    # sampled, so that "identically" is the claim and not "present".
    crops = {
        "background": (slice(0, round(CM)), slice(0, round(CM))),
        "overlay": (slice(round(3.5 * CM), round(4.5 * CM)), slice(round(3.5 * CM), round(4.5 * CM))),
    }
    for index, page in enumerate(pages[1:], start=2):
        for layer, (rows, columns) in crops.items():
            assert_identical(
                pages[0][rows, columns],
                page[rows, columns],
                what=f"the {layer} on pages 1 and {index}",
            )
    # And the crops are the layers rather than blank paper, which is what makes the
    # comparison above say anything at all.
    assert at(pages[0], 0.5, 0.5) == RED
    assert at(pages[0], 4, 4) == BLUE
    # The body is the control: it does differ between the pages, so the two layers holding
    # still is a fact about them.
    assert not np.array_equal(pages[0], pages[1]), "the four pages are the same page"


def test_svg_export_writes_one_file_per_page(paged: PagedRunner):
    """Multi-page SVG needs a page number template, unlike the single-file PDF export."""
    pages = paged.svg(deck("slide[one]", "slide[two]", "slide[three]"))
    assert [path.name for path in pages] == ["page-1.svg", "page-2.svg", "page-3.svg"]
    assert all("<svg" in path.read_text() for path in pages)
