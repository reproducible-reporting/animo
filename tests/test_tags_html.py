# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: what a tag site and a timeline leave in the HTML output.

This version animates nothing in the browser, so there are only two claims to check, and
both are seams that the runtime of a later version needs to find in place: the groups it
addresses, and the number of states it steps through.
The layout inside those groups is checked here too, because the frames the browser is
handed are laid out by the same engine as the pages and can be wrong in the same way.
"""

import pytest
from decks import deck
from harness import MEASURE, Rect, TypstRunner

ANIMATION = (
    '{ import anim: *\n  sub(reveal("second"))\n  sub(move("first", dx: 1cm), scale("second", f: 2)) }'
)

DECK = deck(
    f"slide(animation: {ANIMATION})[\n"
    '  #tag("first")[A tagged phrase] in a paragraph.\n\n'
    '  #tag("second")[Hidden at first.]\n'
    "]",
    "slide[No timeline here.]",
)


@pytest.fixture
def animated(typst: TypstRunner):
    """A compiled deck whose first slide has a timeline and two tag sites."""
    return typst.html(DECK, name="deck.html")


def test_every_tag_site_is_a_labelled_group_holding_one_group(open_page, animated):
    """The two nested slots, as the browser sees them.

    Continuous state belongs to the inner group and boundary state to the labelled outer
    one, because CSS gives an element one `translate` and one `scale` and the two classes
    would otherwise clobber each other.
    """
    page = open_page(animated)
    for name in ("first", "second"):
        groups = page.locator(f'[data-typst-label="{name}"]')
        assert groups.count() == 1, name
        assert groups.locator(":scope > g").count() == 1, name


def test_a_slide_carries_one_state_per_subslide_step(open_page, animated):
    """S+1 states, which is what the runtime steps through and a deep link addresses."""
    page = open_page(animated)
    states = page.eval_on_selector_all(
        "[data-animo-slide]",
        "nodes => nodes.map(node => node.dataset.animoStates)",
    )
    assert states == ["3", "1"]


def test_the_runtime_steps_through_the_states_of_a_slide(deck_at, animated):
    """The position the states are addressed by, which `typst watch` reloads into.

    Nothing moves between them yet, and that is the one thing this test may not assert,
    because it is exactly what the browser runtime changes next.
    """
    presentation = deck_at(animated)
    assert presentation.goto(1, 2).position == (1, 2)
    # A hand-written fragment beyond the last state of the slide is clamped to it.
    presentation.page.evaluate("() => { location.hash = '#2.4' }")
    presentation.page.wait_for_function("() => document.documentElement.dataset.animo === '2.0'")


# A filled rectangle the slide centres, tagged, so that the group holds one shape whose
# box is exact in the browser. A glyph's ink is not centred on its advance width, so an
# equation would put a fraction of a pixel between the two centres for a reason that has
# nothing to do with the claim.
CENTRED_DECK = deck(
    "slide[\n  Before.\n\n"
    '  #tag("mark")[#align(center, rect(width: 3cm, height: 1cm, fill: blue))]\n]'
)


def test_a_tag_around_centred_content_is_a_group_the_slide_still_centres(open_page, typst):
    """The filling wrapper only fills when the display state is outside it.

    The HTML target puts every site at rest, and a display state at rest is still a `move`
    of nothing. A `move` is laid out as an inline element, so a filling block inside one
    would leave the rectangle at the left edge of the body instead of at its centre.
    """
    page = open_page(typst.html(CENTRED_DECK, name="centred.html"))
    group = Rect(**page.eval_on_selector('[data-typst-label="mark"]', MEASURE))
    slide = Rect(**page.eval_on_selector(".animo-slide[data-animo-current]", MEASURE))
    off_centre = abs(group.center[0] - slide.center[0])
    # One CSS pixel of a window 1280 pixels wide, against the several hundred that
    # left-aligning the rectangle would cost.
    assert off_centre < 1, f"the rectangle sits {off_centre} px off the centre of the slide"
