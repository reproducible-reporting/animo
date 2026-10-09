# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the shape morph, which carries a shape into another of a different structure.

A tag the boundary changes that holds one shape left over on each side pairs the two, and
both paths animate their `d` through one structure that `src/js/paths.js` aligns them to.
The primary assertion is that the two copies compute the same `d` at the midpoint of a step,
which is the coincidence the `plus-lighter` sum of the crossfade rests on.

Webkit does not animate `d`, so it crossfades the shapes, and the tests that need a shape
morph assert that instead.
"""

import re

import pytest
from harness import Deck, TypstRunner
from test_morph_html import DURATION, MIDPOINT, SLOW, animated
from test_morph_resize_html import close, paths, resizing

# A square that becomes a circle in a tag of a region, a filled square that becomes a stroked
# circle, a tag that holds two shapes on each side, and a square that becomes a circle in a
# tag that forms an implicit region.
SHAPES = """
  #region(name: "r")[
    #tag("one")[#square(size: 1cm, fill: blue)]
    #tag("fill")[#square(size: 1cm, fill: green)]
    #tag("two")[#stack(dir: ltr, square(size: 0.5cm, fill: red), square(size: 0.5cm))]
  ]
  #tag("own")[#square(size: 1cm, fill: blue)]
"""

CHANGE = (
    'sub(replace("one", transition: morph())[#circle(radius: 0.6cm, fill: blue)], '
    'replace("fill", transition: morph())[#circle(radius: 0.5cm, stroke: 2pt + green)], '
    'replace("two", transition: morph())[#stack(dir: ltr, circle(radius: 0.25cm, fill: red), '
    "circle(radius: 0.25cm))], "
    'replace("own", transition: morph())[#circle(radius: 0.6cm, fill: blue)])'
)

UNDO = (
    "sub("
    + ", ".join(f'reset("{name}", transition: morph())' for name in ("one", "fill", "two", "own"))
    + ")"
)


@pytest.fixture
def shapes(typst: TypstRunner):
    """A slide of three epochs, each boundary crossed by a morph."""
    return animated(typst, SHAPES, CHANGE, UNDO, name="shape-morphs.html")


@pytest.fixture
def midway(page, deck_at, shapes) -> Deck:
    """The slide at the midpoint of the first step."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    return presentation.press("ArrowRight").scrub(MIDPOINT)


def numbers(shown: str) -> list[float]:
    """The numbers of a computed `d`."""
    return [float(value) for value in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?", shown)]


def same_geometry(a: str, b: str) -> bool:
    """Whether two computed `d` have one structure and the same numbers to within rounding."""
    letters = re.compile(r"[A-Za-z]")
    if letters.findall(a.removeprefix("path")) != letters.findall(b.removeprefix("path")):
        return False
    return numbers(a) == pytest.approx(numbers(b), abs=1e-3)


@pytest.mark.parametrize("label", ["one", "fill", "own"])
def test_both_copies_of_a_shape_morph_show_one_geometry(midway, label):
    """A square into a circle, a filled square into a stroked circle, and one in an implicit region.

    The two copies compute the same `d`, which the plus-lighter sum needs, and their box lies
    halfway between the boxes of the two shapes at rest.
    """
    outgoing, incoming = paths(midway, label)[:2]
    if not resizing(midway):
        assert not any(path["d"] for path in (*outgoing, *incoming))
        return
    assert [path["d"] for path in outgoing] == [True]
    assert [path["d"] for path in incoming] == [True]
    assert same_geometry(outgoing[0]["shown"], incoming[0]["shown"])
    assert close(outgoing[0]["box"], incoming[0]["box"])


def test_the_copies_change_their_outline_on_the_way(page, deck_at, shapes):
    """Halfway, the box is halfway between the square's and the circle's."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    rest = paths(presentation, "one")
    presentation.press("ArrowRight").scrub(MIDPOINT)
    if not resizing(presentation):
        pytest.skip("the engine does not animate d")
    halfway = paths(presentation, "one")
    start, end = rest[0][0]["box"], rest[1][0]["box"]
    assert start != pytest.approx(end, abs=1)
    middle = [(a + b) / 2 for a, b in zip(start, end, strict=True)]
    assert close(halfway[0][0]["box"], middle)


def test_a_tag_with_two_shapes_on_a_side_crossfades_them(midway):
    """Two squares into two circles give no clue which becomes which, so none is paired."""
    outgoing, incoming = paths(midway, "two")[:2]
    assert len(outgoing) == len(incoming) == 2
    assert not any(path["d"] for path in (*outgoing, *incoming))


def test_a_shape_morph_writes_no_geometry(page, deck_at, shapes):
    """Neither `d` nor the stroke width is inline style during the step or after it."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    found = [
        path
        for label in ("r", "own")
        for rendering in paths(presentation, label)
        for path in rendering
    ]
    assert all(path["inline"] == "" for path in found)
    presentation.scrub(DURATION).settle()
    assert presentation.page.evaluate("() => document.getAnimations().length") == 0
    found = [
        path
        for label in ("r", "own")
        for rendering in paths(presentation, label)
        for path in rendering
    ]
    assert all(path["inline"] == "" for path in found)


@pytest.mark.parametrize("key", ["ArrowLeft", "ArrowRight"])
def test_an_interrupted_shape_morph_goes_on_from_the_outline_it_shows(page, deck_at, shapes, key):
    """A step back or on halfway starts both copies from the `d` the page shows.

    A step on carries the circle into the third epoch's square, which the circle's copy is
    halfway to, so it starts from the outline halfway between the two as well.
    """
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    if not resizing(presentation):
        pytest.skip("the engine does not animate d")
    before = paths(presentation, "one")[0][0]
    presentation.press(key).scrub(0)
    after = [rendering[0] for rendering in paths(presentation, "one") if rendering[0]["d"]]
    assert after != []
    for path in after:
        assert close(path["box"], before["box"])
        shown = numbers(path["shown"])
        # The same outline, written in the aligned structure of the new step.
        assert min(shown[0::2]) == pytest.approx(min(numbers(before["shown"])[0::2]), abs=0.05)
    presentation.scrub(DURATION).settle()
    assert presentation.page.evaluate("() => document.getAnimations().length") == 0


def test_an_engine_without_d_crossfades_shape_morphs_without_errors(page, deck_at, shapes):
    """Webkit crossfades what the others morph, and every engine ends at rest."""
    errors = []

    # Playwright sets an attribute on a handler, which a bound method of a list refuses.
    def failed(error) -> None:
        errors.append(error)

    page.on("pageerror", failed)
    presentation: Deck = deck_at(shapes)
    presentation.press("ArrowRight").settle().press("ArrowRight").settle()
    presentation.press("ArrowLeft").settle()
    assert errors == []
    assert presentation.position == (1, 1)
