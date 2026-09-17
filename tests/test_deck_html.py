# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the HTML deck, in the chromium `playwright` bundles.

Two things are being checked, and they age differently.
The structure is the one *Architecture* prescribes, and it has to be right because the
epoch frames of a slide are stacked in the grid cell it creates.
The navigation is what makes `typst watch` a live preview and what every later tier-3
test deep-links through, so it is asserted through the same `Deck` contract the runtime
promises rather than through the DOM it happens to have today.
"""

import re

import numpy as np
import pytest
from decks import deck
from harness import EPOCH_GROUPS, TypstRunner, screenshot, state_hash

DECK = deck("slide[One]", "slide[Two]", "slide[Three]")


@pytest.fixture
def three_slides(typst: TypstRunner):
    """A compiled three-slide deck, as a file the browser can open."""
    return typst.html(DECK, name="deck.html")


# The structure.


def test_a_slide_is_a_viewport_holding_a_canvas_holding_one_frame(open_page, three_slides):
    """The shape every epoch rendering of a slide is placed in, whatever the epochs.

    One frame per slide, always: the epochs are groups inside it, which is what shares
    their glyph definitions.
    """
    page = open_page(three_slides)
    assert page.locator(".animo-slide").count() == 3
    for index in range(3):
        slide = page.locator(".animo-slide").nth(index)
        assert slide.get_attribute("data-animo-slide") == str(index + 1)
        canvas = slide.locator(":scope > .animo-canvas")
        assert canvas.count() == 1
        assert canvas.locator(":scope > svg").count() == 1
        assert slide.locator(EPOCH_GROUPS).count() == 1


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
    # The slide pans, because that is what makes animo record its placements and size the
    # canvas from them. A slide that never pans takes the viewport.
    timeline = "animation: {import anim: *\nsub(pan(dx: 1cm))}, "
    source = deck(
        f"slide({timeline})[#place(dx: 30cm, dy: 1cm)[far]]",
        width="16cm",
        height="9cm",
    )
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


# The tempo.


TEMPO = 'primitive-duration: 0.2, transition-duration: 0, easing: "ease-out"'

TEMPO_PROPERTIES = """() => {
    const style = getComputedStyle(document.documentElement);
    return {
        step: style.getPropertyValue('--animo-primitive-duration').trim(),
        slide: style.getPropertyValue('--animo-transition-duration').trim(),
        easing: style.getPropertyValue('--animo-easing').trim(),
    };
}"""


def test_the_deck_writes_its_tempo_into_the_stylesheet(page, open_page, typst: TypstRunner):
    """The three arguments are what an author writes; the properties are what the runtime reads.

    The values are asserted as the browser computes them rather than as they are spelled in
    the page, because that is the form the runtime asks for at every step.
    """
    source = deck("slide[One]", "slide[Two]", timing=TEMPO)
    open_page(typst.html(source, name="tempo.html"))
    assert page.evaluate(TEMPO_PROPERTIES) == {
        "step": "0.2s",
        "slide": "0s",
        "easing": "ease-out",
    }


def test_reduced_motion_outranks_a_deck_that_asked_for_motion(
    page, open_page, typst: TypstRunner
):
    """The deck writes its `:root` block after animo's stylesheet, so order cannot decide this.

    The reduced-motion query carries `!important` for that reason, and this is the test
    that says so: without it the deck's own durations would win, and a reader who asked
    for less motion would get the deck's answer instead of theirs.
    """
    page.emulate_media(reduced_motion="reduce")
    source = deck("slide[One]", "slide[Two]", timing='primitive-duration: 2, transition-duration: 2')
    open_page(typst.html(source, name="reduced-tempo.html"))
    properties = page.evaluate(TEMPO_PROPERTIES)
    assert properties["step"] == "0s"
    assert properties["slide"] == "0s"


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


def test_only_the_current_slide_paints(page, deck_at, three_slides):
    """Every slide of the deck is in the DOM at once, so exactly one may be seen.

    Two are laid out after a step, because a boundary crossfades the two containers and
    the one it came from keeps its layout, but only one of them is left carrying any ink.
    """
    presentation = deck_at(three_slides).goto(2).settle()
    shown = page.evaluate(
        """() => Array.from(document.querySelectorAll('.animo-slide'), node => {
            const computed = getComputedStyle(node);
            return computed.display !== 'none' && Number(computed.opacity) > 0;
        })"""
    )
    assert shown == [False, True, False]


def test_a_deck_lays_out_two_slides_at_a_time_and_no_more(page, deck_at, three_slides):
    """The cost of the crossfade, which is what keeps a long deck cheap to open.

    A deep link snaps, so it lays out the one slide it lands on; a step crossfades, so it
    lays out the slide it came from as well and no third one.
    """
    laid_out = """() => Array.from(
        document.querySelectorAll('.animo-slide'),
        node => getComputedStyle(node).display !== 'none',
    )"""
    presentation = deck_at(three_slides).goto(2)
    assert page.evaluate(laid_out) == [False, True, False]
    presentation.press("ArrowRight").settle()
    assert page.evaluate(laid_out) == [False, True, True]


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


def test_a_colour_overlay_becomes_css_on_a_layer_of_its_own(open_page, typst: TypstRunner):
    """An overlay colour cannot be the container's background, which is behind the canvas.

    It is ink over the slide, so it gets an element of its own in front of the canvas,
    and only its alpha makes it useful: a dimming tint is the case it exists for.
    """
    source = deck('slide(overlay: rgb("#0000ff80"))[body]')
    page = open_page(typst.html(source, name="tint.html"))
    computed = page.evaluate(
        "() => getComputedStyle(document.querySelector('.animo-overlay')).backgroundColor"
    )
    # The components rather than the string: an engine is free to spell the alpha of
    # `#0000ff80` as either 0.5 or 0.502, and both did.
    found = re.fullmatch(r"rgba\((\d+), (\d+), (\d+), ([\d.]+)\)", computed)
    assert found is not None, computed
    assert tuple(int(found[axis]) for axis in (1, 2, 3)) == (0, 0, 255)
    assert float(found[4]) == pytest.approx(0x80 / 255, abs=0.01)


def test_an_opaque_colour_overlay_covers_the_body_in_the_browser(open_page, typst: TypstRunner):
    """The declaration is on an element in front of the canvas, and this is what that means.

    A background of the same colour is the control: it sits on the slide container, which
    is behind the canvas, so the body stays visible there.
    """
    body = '[#place(dx: 2cm, dy: 2cm, rect(width: 2cm, height: 2cm, fill: rgb("#ff0000")))]'
    shots = {}
    for layer in ("overlay", "background"):
        page = open_page(typst.html(deck(f'slide({layer}: rgb("#0000ff")){body}'), name=f"{layer}.html"))
        shots[layer] = screenshot(page.locator(".animo-slide[data-animo-current]"))
    red = (shots["background"] == np.array([255, 0, 0], dtype=np.uint8)).all(axis=2)
    assert red.any(), "the control lost the body for a reason of its own"
    assert not (shots["overlay"] == np.array([255, 0, 0], dtype=np.uint8)).all(axis=2).any(), (
        "the body shows through an opaque overlay, so the layer is behind the canvas"
    )


# The two outer layers are rendered once per slide, whatever the timeline does.

# A slide with three epochs, so that "once per slide" is a claim about the layers rather
# than a claim that the slide has one frame.
EPOCHS = (
    "slide(background: [#box(width: 100%, height: 100%, fill: rgb(\"#ff0000\"))], "
    'overlay: [#place(bottom + right)[o]], animation: { import anim: *\n'
    '  sub(replace("t")[two])\n'
    '  sub(replace("t")[three]) })[#tag("t")[one]]'
)


@pytest.fixture
def layered(typst: TypstRunner):
    """A compiled one-slide deck with three epochs and both outer layers."""
    return typst.html(deck(EPOCHS), name="layers.html")


def test_a_slide_carries_one_frame_per_epoch_and_one_per_layer(open_page, layered):
    """The claim that keeps the two layers off the epoch cost curve.

    Neither may hold a tag or a region, so neither can depend on a state or an epoch,
    and three epochs still leave one background and one overlay.
    """
    page = open_page(layered)
    slide = page.locator(".animo-slide")
    assert slide.locator(":scope > .animo-canvas > svg").count() == 1
    assert slide.locator(EPOCH_GROUPS).count() == 3
    for layer in ("animo-background", "animo-overlay"):
        assert slide.locator(f":scope > .{layer}").count() == 1
        assert slide.locator(f":scope > .{layer} > svg").count() == 1


def test_the_layers_are_siblings_of_the_canvas_in_painting_order(open_page, layered):
    """*Architecture* rule 5: beside the canvas, never among its frames.

    The order is the painting order, because all three are positioned elements with no
    z-index of their own. Being outside the canvas is also what keeps them out of the
    `plus-lighter` blend the epoch renderings use, which is asserted here rather than left
    to the selector that happens to express it. Neither layer's own frame carries the
    blend either, which is what says the selector reaches the renderings and not every
    frame of the slide.
    """
    page = open_page(layered)
    order = page.evaluate(
        f"""() => {{
            const slide = document.querySelector('.animo-slide');
            const blend = (element) => getComputedStyle(element).mixBlendMode;
            return {{
                children: Array.from(slide.children, (child) => child.className),
                layers: Array.from(
                    slide.querySelectorAll(':scope > :not(.animo-canvas) > svg'), blend),
                frame: blend(slide.querySelector(':scope > .animo-canvas > svg')),
                renderings: Array.from(slide.querySelectorAll({EPOCH_GROUPS!r}), blend),
            }};
        }}"""
    )
    assert order["children"] == ["animo-background", "animo-canvas", "animo-overlay"]
    assert order["layers"] == ["normal", "normal"]
    assert order["frame"] == "normal"
    assert order["renderings"] == ["plus-lighter"] * 3
