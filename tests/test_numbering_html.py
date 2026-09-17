# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: which rendering of a stack the browser shows.

This is the tier the whole construct exists for. One frame covers a run of states, so a
value finer than a slide number cannot be chosen when the frame is rendered: typst renders
one value per state and the runtime shows the one belonging to the position it is on.

Every assertion here is about which rendering is opaque, read per state off the computed
style, because that is the choice the runtime makes. What the rendering says is tier 1's
business and what it looks like on paper is tier 2's.
"""

import numpy as np
import pytest
from decks import deck
from harness import Deck, TypstRunner, screenshot

# One colour per subslide, so that a rendering can be found in a screenshot.
SWATCHES = ("#ff0000", "#00ff00", "#0000ff")

SWATCH = (
    "per-subslide(it => rect(width: 1cm, height: 1cm, "
    "fill: rgb((" + ", ".join(f'"{colour}"' for colour in SWATCHES) + ").at(it.number - 1))))"
)


def shown(state: int, count: int = 3) -> list[float]:
    """The opacities a stack of `count` renderings has while `state` is the one shown."""
    return [1.0 if index == state else 0.0 for index in range(count)]


def numbered_deck(typst: TypstRunner, *steps: str, name: str = "deck.html", **arguments):
    """A one-slide deck whose overlay carries one rendering per state of the slide."""
    timeline = "{ import anim: *\n" + "\n".join(steps) + " }"
    extra = "".join(f", {key}: {value}" for key, value in arguments.items())
    source = deck(
        f"slide(animation: {timeline}, overlay: place(top + left, {SWATCH}){extra})"
        "[\n  = A slide\n  With a line of text.\n]"
    )
    return typst.html(source, name=name)


@pytest.fixture
def stacked(typst: TypstRunner):
    """A slide of three states, of which the overlay says which one is being shown."""
    return numbered_deck(typst, "sub()", "sub()")


def test_every_subslide_shows_its_own_rendering(deck_at, stacked):
    """The whole claim, walked forwards: the position decides which rendering is opaque."""
    presentation: Deck = deck_at(stacked)
    for state in range(3):
        presentation.goto(1, state)
        assert presentation.subslides == shown(state)


def test_a_deep_link_lands_on_the_right_rendering(deck_at, stacked):
    """A position reached without passing through the ones before it, which is a shared link.

    The runtime writes the choice on every step, the snapping ones included, so a deck
    restored from a fragment shows the number of the state it restored and not the first.
    """
    presentation: Deck = deck_at(stacked).goto(1, 2)
    assert presentation.subslides == shown(2)


def test_stepping_backwards_puts_the_earlier_rendering_back(deck_at, stacked):
    """A backward step undoes exactly what a forward step did, here as everywhere else."""
    presentation: Deck = deck_at(stacked).goto(1, 2)
    presentation.press("ArrowLeft").settle()
    assert presentation.subslides == shown(1)
    presentation.press("ArrowLeft").settle()
    assert presentation.subslides == shown(0)


def test_a_step_the_clock_took_shows_the_rendering_it_arrived_at(timed_deck_at, typst):
    """A deck that plays itself numbers itself, and nothing about the choice is a click.

    The runtime makes the choice where it renders a state, so a step nobody pressed a key
    for is the same code path as one that was pressed.
    """
    playing = numbered_deck(typst, "sub(wait: 1)", "sub()", name="playing.html")
    presentation: Deck = timed_deck_at(playing)
    assert presentation.subslides == shown(0)
    presentation.run_for(1100)
    assert presentation.position == (1, 1)
    assert presentation.subslides == shown(1)


def test_a_stack_in_the_body_paints_only_the_rendering_of_the_state(deck_at, typst):
    """A stack in an epoch frame nobody is watching may not paint through it.

    A frame that is not the one being shown is hidden with `visibility`, which a descendant
    may take back, so the renderings are chosen with `opacity` instead: one at opacity 1
    inside a hidden frame stays hidden, where one that took its visibility back would paint
    out of a frame the slide is not showing.
    """
    source = deck(
        "slide(animation: { import anim: *\n"
        '  sub(replace("a")[second])\n'
        "  sub()\n"
        "})[\n"
        f"  #place(top + left, {SWATCH})\n"
        '  #tag("a", wrap: block)[first]\n'
        "]"
    )
    presentation: Deck = deck_at(typst.html(source, name="body.html"))
    for state in range(3):
        presentation.goto(1, state).settle()
        assert presentation.subslides == shown(state)
        pixels = screenshot(presentation.current)
        for index, colour in enumerate(SWATCHES):
            wanted = np.array([int(colour[at : at + 2], 16) for at in (1, 3, 5)], dtype=np.uint8)
            found = bool((pixels == wanted).all(axis=2).any())
            assert found == (index == state), (
                f"subslide {state + 1} paints the rendering of subslide {index + 1}"
            )
