# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 2: the three paged outputs of a static deck.

A static deck has no subslides, so the presentation and the handout are the same pages,
and saying so numerically is what proves that both go through one layout rather than two.
Everything else here is about the viewport: it is the page, it clips, and it carries the
background.
"""

import numpy as np
from decks import deck
from harness import PagedRunner, assert_identical

# The deck is 16 by 9 centimetres, which is 453.54 by 255.12 points,
# and `PagedRunner.png` renders one pixel per point by default.
VIEWPORT = (255, 454)

RED = (255, 0, 0)


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
    """Nothing in this phase distinguishes them, and the pixels have to agree that they do.

    When subslides arrive the presentation grows pages and this stops holding,
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
    assert tuple(pages[0][-1, -1]) == RED


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
    """The deck's margin moves the body's origin, which is where placements start."""
    without = paged.png(deck(f"slide[{mark('0cm', '0cm')}]", margin="0cm"))[0]
    with_margin = paged.png(deck(f"slide[{mark('0cm', '0cm')}]", margin="1cm"))[0]
    assert tuple(without[1, 1]) == RED
    assert tuple(with_margin[1, 1]) != RED
    # One centimetre is 28.35 points, and one point is one pixel here.
    assert tuple(with_margin[30, 30]) == RED


def test_svg_export_writes_one_file_per_page(paged: PagedRunner):
    """Multi-page SVG needs a page number template, which is the handout SVG output."""
    pages = paged.svg(deck("slide[one]", "slide[two]", "slide[three]"))
    assert [path.name for path in pages] == ["page-1.svg", "page-2.svg", "page-3.svg"]
    assert all("<svg" in path.read_text() for path in pages)
