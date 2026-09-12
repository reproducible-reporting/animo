# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: what a tag site and a timeline leave in the HTML output.

This version animates nothing in the browser, so there are only two claims to check, and
both are seams that the runtime of a later version needs to find in place: the groups it
addresses, and the number of states it steps through.
"""

import pytest
from decks import deck
from harness import TypstRunner

ANIMATION = (
    '{ import anim: *\n  sub(reveal("second"))\n  sub(move("first", x: 1cm), scale("second", 2)) }'
)

DECK = deck(
    f"slide(animation: {ANIMATION})[\n"
    '  #tag("first")[A tagged phrase] in a paragraph.\n\n'
    '  #tag("second", hidden: true)[Hidden at first.]\n'
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
