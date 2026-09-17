# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the hard tag sites in the browser.

A tag inside math and a tag on a cetz `content()` element have to reach the browser as
`<g data-typst-label>` groups and animate like any other, because that is the whole of the
promise that anything laid out as content can be tagged.

The negative half is asserted just as directly: a `wrap: none` tag emits no group at all.
That is the reason the continuous primitives are refused on such a tag at compile time, so
a typst release that started emitting one should be noticed here rather than quietly make
a refusal pointless.
"""

import pytest
from decks import deck
from harness import CETZ, Deck, TypstRunner, require
from test_animation_html import CM, TOLERANCE, timeline

# The figure of `test_tag_sites.py`, without the geometry that is not needed here.
SCENE = """#let scene() = cetz.canvas({
  import cetz.draw: *
  circle((0, 0), radius: 1)
  content((4, 0), tag("lab")[Labelled], anchor: "west")
})

"""


@pytest.fixture
def sites(typst: TypstRunner):
    """A slide with a tag in an equation, a tag on a cetz label and a `wrap: none` tag."""
    require(typst, CETZ)
    animation = timeline('sub(move("b", dy: 1cm), move("lab", dx: 2cm))')
    source = deck(
        f"slide(animation: {animation})[\n"
        "  #scene()\n\n"
        '  $ a + #tag("b")[$b$] = c $\n\n'
        '  #tag("bare", wrap: none)[No wrapper, no group.]\n'
        "]",
        preamble=f'#import "{CETZ}"\n\n' + SCENE,
    )
    return typst.html(source, name="deck.html")


def test_a_tag_inside_math_is_a_group_the_runtime_moves(deck_at, sites):
    """Math is laid out into the same SVG, so a labelled box in it is an ordinary group."""
    presentation: Deck = deck_at(sites)
    unit = presentation.unit
    before = presentation.rects("b")
    assert len(before) == 1
    after = presentation.goto(1, 1).rects("b")[0]
    assert after.y - before[0].y == pytest.approx(1 * CM * unit, abs=TOLERANCE)
    assert after.x == pytest.approx(before[0].x, abs=TOLERANCE)


def test_a_tag_on_a_cetz_content_element_is_a_group_the_runtime_moves(deck_at, sites):
    """cetz draws into the frame's own coordinates, so the group is addressable as usual."""
    presentation: Deck = deck_at(sites)
    unit = presentation.unit
    before = presentation.rects("lab")
    assert len(before) == 1
    after = presentation.goto(1, 1).rects("lab")[0]
    assert after.x - before[0].x == pytest.approx(2 * CM * unit, abs=TOLERANCE)


def test_a_wrap_none_tag_emits_no_group_at_all(deck_at, sites):
    """Which is why a continuous primitive on such a tag is refused when the deck compiles.

    Asserted directly rather than inferred from the refusal, so that a typst release that
    began labelling something else would be noticed here.
    """
    presentation: Deck = deck_at(sites)
    assert presentation.rects("bare") == []


def test_every_tag_site_of_the_three_kinds_has_the_two_nested_slots(open_page, sites):
    """Boundary state outside, continuous state inside, wherever the tag site sits."""
    page = open_page(sites)
    for name in ("b", "lab"):
        groups = page.locator(f'[data-typst-label="{name}"]')
        assert groups.count() == 1, name
        assert groups.locator(":scope > g").count() == 1, name
