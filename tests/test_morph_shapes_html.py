# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the morph of shapes and images, which are matched beside the letters.

The primary assertion is the geometric one of `test_morph_html.py`, extended to every path
and image a region draws. At the midpoint of a step, each one the morph moves in the outgoing
region is displayed where an element of the same key in the incoming region is displayed,
halfway between the places the two are laid out at. The place of a path is the origin of its
`M 0 0`, and that of an image its top left corner, both through `getScreenCTM()`.
"""

import math

import pytest
from harness import UNDER, Deck, TypstRunner
from PIL import Image
from test_morph_html import CLOSE, MIDPOINT, SLOW, STILL, animated, resting

# A paragraph that reflows behind a clause inserted at its start, with a box beside a word,
# an image, a fraction, a clipped box and a clipped box in a tag in it, all of which move.
# A second region holds a clipped box that stays where it is while what it holds moves inside
# it, and the tags whose content changes: a rectangle that changes colour, one whose stroke
# changes width, and a fraction whose numerator grows.
SHAPES = """
  #region(name: "r")[
    Text #tag("ins", wrap: none)[] with a box #box(width: 0.6cm, height: 0.3cm, fill: blue)
    beside a word, an image #box(image("pattern.png", height: 0.4cm)), a fraction $a/b$, a
    clipped box #box(clip: true, width: 1.1cm, height: 0.35cm)[Clipped words], a tagged
    one #tag("boxed")[#box(clip: true, width: 1.1cm, height: 0.35cm)[Tagged words]] and the
    rest of this paragraph, which wraps onto another line.
  ]

  #region(name: "q")[
    #box(clip: true, width: 4cm, height: 0.6cm)[#tag("in", wrap: none)[] Inside the clip]
    #tag("c")[#box(rect(width: 0.5cm, height: 0.3cm, fill: blue))]
    #tag("s")[#box(rect(width: 0.5cm, height: 0.3cm, stroke: 1pt))]
    #tag("f")[$a/b$]
  ]
"""

STEP = (
    'sub(replace("ins", transition: morph())[and an inserted clause], '
    'replace("c", transition: morph())[and #box(rect(width: 0.5cm, height: 0.3cm, fill: red))], '
    'replace("s", transition: morph())[and #box(rect(width: 0.5cm, height: 0.3cm, stroke: 3pt))], '
    'replace("f", transition: morph())[$(a + c)/b$], '
    'replace("in", transition: morph())[Moved])'
)


def pattern(path) -> None:
    """A raster with a gradient and hard edges, which shows where it is resampled."""
    image = Image.new("RGB", (30, 15))
    for x in range(30):
        for y in range(15):
            edge = 0 if (x // 5 + y // 5) % 2 else 120
            image.putpixel((x, y), (8 * x, edge, 255 - 16 * y))
    image.save(path)


@pytest.fixture
def shapes(typst: TypstRunner):
    """A slide of two epochs whose boundary morphs both regions."""
    pattern(typst.scratch / "pattern.png")
    return animated(typst, SHAPES, STEP, name="shapes.html")


# Where every path and image of a region is displayed, per epoch rendering of the slide shown,
# as `[kind, key, x, y]` in CSS pixels. The key is what a morph compares, without the colour.
INK = (
    """label => {
    const slide = document.querySelector('.animo-slide[data-animo-current]');
    const key = (element) => element.localName === "image"
        ? `${element.href.baseVal} ${element.getAttribute("width")}`
        : `${element.getAttribute("d")} ${element.getAttribute("stroke-width")}`;
    return ("""
    + UNDER
    + """)(slide, label).map(
        (groups) => groups.flatMap((group) => Array.from(
            group.querySelectorAll(':is(path, image)'),
        )).filter((element) => element.closest("defs, clipPath, symbol") === null).map(
            (element) => {
                const point = new DOMPoint(0, 0).matrixTransform(element.getScreenCTM());
                return [element.localName, key(element), point.x, point.y];
            },
        ),
    );
}"""
)


def ink(presentation: Deck, label: str) -> list[list[tuple[str, str, float, float]]]:
    """Where each path and image of a region is displayed, per epoch rendering."""
    return [
        [tuple(element) for element in rendering]
        for rendering in presentation.page.evaluate(INK, label)
    ]


def apart(a, b) -> float:
    """How far apart two displayed elements are, in CSS pixels."""
    return math.hypot(a[2] - b[2], a[3] - b[3])


def test_every_moving_shape_has_a_partner_halfway_along_its_route(page, deck_at, shapes):
    """The claim the morph rests on, for the box, the image, the fraction bar and the clip.

    The fraction of `r` keeps its numerator, so its bar is matched like the box beside it.
    The count is what says the assertion is not vacuous.
    """
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    rest = ink(presentation, "r")
    presentation.press("ArrowRight").scrub(MIDPOINT)
    halfway = ink(presentation, "r")
    moving = [
        (index, element)
        for index, element in enumerate(halfway[0])
        if apart(element, rest[0][index]) >= STILL
    ]
    kinds = {element[0] for _, element in moving}
    assert kinds == {"path", "image"}, f"only {kinds} moved"
    assert len(moving) >= 3
    for index, element in moving:
        partner = next(
            (
                other
                for other, candidate in enumerate(halfway[1])
                if candidate[:2] == element[:2] and apart(candidate, element) < CLOSE
            ),
            None,
        )
        assert partner is not None, f"outgoing {element[0]} {index} has no partner"
        start, end = rest[0][index], rest[1][partner]
        middle = ((start[2] + end[2]) / 2, (start[3] + end[3]) / 2)
        assert math.hypot(element[2] - middle[0], element[3] - middle[1]) < CLOSE, (
            f"outgoing {element[0]} {index} is off its route"
        )


# Which paths, images and glyphs below a group of a label are moving, per epoch rendering, as
# the selector `what` picks them.
MOVING = (
    """([label, what]) => {
    const slide = document.querySelector('.animo-slide[data-animo-current]');
    const moving = (element) => {
        for (let node = element; node !== null; node = node.parentElement) {
            if (node.getAnimations().some((animation) =>
                animation.effect.getKeyframes().some((frame) => "translate" in frame))) {
                return true;
            }
        }
        return false;
    };
    return ("""
    + UNDER
    + """)(slide, label).map(
        (groups) => groups.flatMap((group) => Array.from(group.querySelectorAll(what), moving)),
    );
}"""
)


def moving(presentation: Deck, label: str, what: str) -> list[list[bool]]:
    """Whether each element `what` picks below a label moves, per epoch rendering."""
    return presentation.page.evaluate(MOVING, [label, what])


@pytest.fixture
def midway(page, deck_at, shapes) -> Deck:
    """The slide at the midpoint of the step."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    return presentation.press("ArrowRight").scrub(MIDPOINT)


def test_a_recoloured_rectangle_is_a_match(midway):
    """The colour is not part of the key, and the pair sums to the interpolated colour."""
    assert moving(midway, "c", "path")[:2] == [[True], [True]]


def resizing(presentation: Deck) -> bool:
    """Whether the engine animates `d`, which a resize needs and webkit 26.5 lacks."""
    return presentation.page.evaluate("""() => CSS.supports("d", 'path("M 0 0")')""")


def test_a_rectangle_whose_stroke_changes_width_is_a_resize(midway):
    """A route does not scale a stroke, so the pair is no exact match but a resize.

    In an engine without `d` there is no resize, and the two rectangles fade where they are.
    `test_morph_resize_html.py` asserts what a resize shows.
    """
    expected = resizing(midway)
    assert moving(midway, "s", "path")[:2] == [[expected], [expected]]


def test_a_fraction_whose_numerator_grows_resizes_its_bar(midway):
    """The bar is longer in the incoming fraction, so its `d` differs and it is a resize.

    The denominator is matched and moves to the middle of the longer bar.
    In an engine without `d` the bar fades instead.
    """
    expected = resizing(midway)
    assert moving(midway, "f", "path")[:2] == [[expected], [expected]]
    assert any(moving(midway, "f", "use")[0])


def test_a_match_inside_a_clip_that_stays_is_allowed(midway):
    """Both copies of `Inside the clip` move under the same clip at the same place."""
    region = moving(midway, "q", "g[clip-path] use")
    assert any(region[0])
    assert any(region[1])


def test_a_match_under_a_clip_that_moves_is_not(midway):
    """The clipped box of `r` moves with the paragraph, and its letters do not.

    A clip above a moving element stays where it is, so the copies under the old and the new
    clip would be cut off at two edges. The letters fade, and a tag around the box is how to
    carry it.
    """
    region = moving(midway, "r", "g[clip-path]:not([data-typst-label=boxed] *) use")
    for rendering in region[:2]:
        assert rendering, "no letters under a clip in the paragraph"
        assert not any(rendering)


def test_a_tag_carries_a_clipped_box_as_one(midway):
    """A `translate` on the tag's outer slot carries the clip below it, as the probe shows."""
    assert moving(midway, "boxed", "g[clip-path] use")[:2] == [[True] * 11, [True] * 11]


def test_a_shape_morph_ends_at_rest(deck_at, shapes):
    """After the motion, no path or image carries a translation."""
    presentation: Deck = deck_at(shapes)
    presentation.press("ArrowRight").settle()
    assert resting(presentation)
    assert presentation.page.evaluate(
        """() => Array.from(
            document.querySelectorAll(
                '.animo-slide[data-animo-current] .animo-canvas :is(path, image)'),
        ).every((element) => getComputedStyle(element).translate === 'none')"""
    )
