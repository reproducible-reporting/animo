# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the HTML deck, in the chromium `playwright` bundles.

Two things are being checked, and they age differently.
The structure is the one *Architecture* prescribes, and it has to be right now because
phase 09 stacks more frames in the grid cell this phase creates.
The navigation is what makes `typst watch` a live preview and what every later tier-3
test deep-links through, so it is asserted through the same `Deck` contract the runtime
promises rather than through the DOM it happens to have today.
"""

import pytest
from decks import deck
from harness import TypstRunner, state_hash

DECK = deck("slide[One]", "slide[Two]", "slide[Three]")


@pytest.fixture
def three_slides(typst: TypstRunner):
    """A compiled three-slide deck, as a file the browser can open."""
    return typst.html(DECK, name="deck.html")


# The structure.


def test_a_slide_is_a_viewport_holding_a_canvas_holding_one_frame(open_page, three_slides):
    """The shape phase 09 stacks its epoch frames in, built once here and not again.

    One frame per slide today, because a static slide has exactly one content state.
    """
    page = open_page(three_slides)
    assert page.locator(".animo-slide").count() == 3
    for index in range(3):
        slide = page.locator(".animo-slide").nth(index)
        assert slide.get_attribute("data-animo-slide") == str(index + 1)
        canvas = slide.locator(":scope > .animo-canvas")
        assert canvas.count() == 1
        assert canvas.locator(":scope > svg").count() == 1


def test_the_canvas_is_an_isolated_grid_cell(open_page, three_slides):
    """The crossfade of phase 09 is contained by this and by nothing else.

    Without `isolation: isolate` the blend that keeps a structural step from dipping
    reaches out of the slide, and without the single grid cell there is nothing to stack.
    """
    page = open_page(three_slides)
    style = page.evaluate(
        """() => {
            const canvas = document.querySelector('.animo-canvas');
            const computed = getComputedStyle(canvas);
            const frame = getComputedStyle(canvas.firstElementChild);
            return {
                display: computed.display,
                isolation: computed.isolation,
                row: frame.gridRowStart,
                column: frame.gridColumnStart,
            };
        }"""
    )
    assert style == {"display": "grid", "isolation": "isolate", "row": "1", "column": "1"}


def test_the_viewport_clips_and_fills_the_window_at_the_deck_aspect_ratio(
    page, open_page, three_slides
):
    """A deck that does not fit the window is not a presentation.

    The window is set to the deck's own aspect ratio, so the viewport has to be the
    whole of it: any letterboxing here would be a scaling bug rather than a choice.
    """
    page.set_viewport_size({"width": 1280, "height": 720})
    open_page(three_slides)
    box = page.locator(".animo-slide").first.bounding_box()
    assert box == pytest.approx({"x": 0, "y": 0, "width": 1280, "height": 720}, abs=0.05)
    assert (
        page.evaluate("() => getComputedStyle(document.querySelector('.animo-slide')).overflow")
        == "hidden"
    )


def test_a_canvas_larger_than_the_viewport_scales_with_it(page, open_page, typst: TypstRunner):
    """The canvas is measured in typst points at any window size.

    The canvas element is scaled as a whole rather than sized in pixels, so a canvas of
    twice the viewport's width is twice as wide as the window, whatever the window is.
    """
    source = deck("slide[#place(dx: 30cm, dy: 1cm)[far]]", width="16cm", height="9cm")
    page.set_viewport_size({"width": 1280, "height": 720})
    open_page(typst.html(source, name="wide.html"))
    ratio = page.evaluate(
        """() => {
            const slide = document.querySelector('.animo-slide');
            const canvas = slide.querySelector('.animo-canvas');
            return canvas.getBoundingClientRect().width / slide.getBoundingClientRect().width;
        }"""
    )
    # One centimetre of margin, thirty of offset and the width of the word "far".
    assert ratio > 31 / 16
    assert ratio < 32 / 16


# The navigation.


def test_the_deck_opens_on_the_first_slide(deck_at, three_slides):
    """A deck with no fragment starts at the beginning, not at nothing."""
    assert deck_at(three_slides).position == (1, 0)


def test_a_key_moves_to_the_next_slide_and_back(page, open_page, three_slides):
    """Keyboard first, because that is how a deck is actually presented."""
    open_page(three_slides)
    assert page.evaluate("() => document.documentElement.dataset.animo") == "1.0"
    page.keyboard.press("ArrowRight")
    assert page.evaluate("() => document.documentElement.dataset.animo") == "2.0"
    page.keyboard.press("ArrowLeft")
    assert page.evaluate("() => document.documentElement.dataset.animo") == "1.0"


def test_a_click_moves_to_the_next_slide(page, open_page, three_slides):
    """A presenter without a keyboard, and a remote that sends a click."""
    open_page(three_slides)
    page.locator(".animo-deck").click()
    assert page.evaluate("() => document.documentElement.dataset.animo") == "2.0"


def test_stepping_stops_at_both_ends(page, open_page, three_slides):
    """Walking off a deck would leave the runtime showing nothing at all."""
    open_page(three_slides)
    for _ in range(5):
        page.keyboard.press("ArrowLeft")
    assert page.evaluate("() => document.documentElement.dataset.animo") == "1.0"
    for _ in range(9):
        page.keyboard.press("ArrowRight")
    assert page.evaluate("() => document.documentElement.dataset.animo") == "3.0"


def test_only_the_current_slide_is_shown(page, open_page, three_slides):
    """Every slide of the deck is in the DOM at once, so exactly one may be visible."""
    open_page(three_slides)
    page.keyboard.press("ArrowRight")
    shown = page.evaluate(
        """() => Array.from(
            document.querySelectorAll('.animo-slide'),
            node => getComputedStyle(node).display !== 'none',
        )"""
    )
    assert shown == [False, True, False]


def test_the_current_slide_is_in_the_fragment_and_survives_a_reload(page, deck_at, three_slides):
    """This is what makes `typst watch` a live preview.

    Typst serves the HTML and reloads the browser itself, with a plain `location.reload()`,
    so a deck whose position lives in the fragment comes back where the author left it.
    """
    deck = deck_at(three_slides).goto(3)
    assert page.url.endswith(state_hash(3))
    page.reload()
    assert deck.position == (3, 0)


def test_a_fragment_outside_the_deck_lands_inside_it(deck_at, page, three_slides):
    """A hand-edited or stale fragment has to be survivable, not fatal."""
    deck_at(three_slides)
    page.evaluate("() => { location.hash = '#9.4' }")
    page.wait_for_function("() => document.documentElement.dataset.animo === '3.0'")


def test_stepping_leaves_no_history_behind(page, open_page, three_slides):
    """`replaceState`, not `pushState`: otherwise the back button walks one step per click.

    A deck is stepped through hundreds of times in a talk, and a history entry per step
    makes the browser's own back button useless for leaving the deck.
    """
    open_page(three_slides)
    before = page.evaluate("() => history.length")
    for _ in range(4):
        page.keyboard.press("ArrowRight")
    assert page.evaluate("() => history.length") == before


def test_a_colour_background_becomes_css_on_the_slide(open_page, typst: TypstRunner):
    """`set page` is ignored in the HTML target, so the background has to be CSS.

    It sits on the viewport element, which is the slide's visible box,
    so it stays put when the canvas is larger and later moves under a pan.
    """
    source = deck('slide(background: rgb("#ff0000"))[body]')
    page = open_page(typst.html(source, name="background.html"))
    assert (
        page.evaluate(
            "() => getComputedStyle(document.querySelector('.animo-slide')).backgroundColor"
        )
        == "rgb(255, 0, 0)"
    )
