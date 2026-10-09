# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the resize, which carries a shape whose geometry changes while its structure stays.

The primary assertion is geometric. At the midpoint of a step, the box of each path a resize
carries in the outgoing region, read with `getBBox()` through the screen matrix, is the box of
its partner in the incoming region, and lies halfway between the two boxes at rest.
That is what makes the pair sum to one opaque shape under the crossfade's `plus-lighter`,
which `probes/test_path_interpolation.py` measures on rasters.

Webkit does not animate `d`, so it crossfades the shapes a resize would carry, and the tests
that need a resize assert that instead.
"""

import pytest
from harness import UNDER, Deck, TypstRunner
from test_morph_html import CLOSE, DURATION, MIDPOINT, SLOW, animated
from test_morph_shapes_html import moving

# A region of shapes that each change their geometry and keep their structure: the bar of a
# fraction whose numerator grows, a rectangle, a circle that becomes an ellipse, a rounded
# rectangle whose radius grows with it, and a rectangle whose stroke changes width.
SHAPES = """
  #region(name: "r")[
    #tag("f")[$a/b$]
    #tag("g")[#box(rect(width: 1cm, height: 0.4cm, fill: blue))]
    #tag("c")[#box(circle(radius: 0.2cm, fill: green))]
    #tag("rr")[#box(rect(width: 1cm, height: 0.5cm, radius: 2pt, fill: blue))]
    #tag("s")[#box(rect(width: 0.5cm, height: 0.3cm, stroke: 1pt))]
  ]
"""

GROW = (
    'sub(replace("f", transition: morph())[$(a + c)/b$], '
    'replace("g", transition: morph())[#box(rect(width: 2cm, height: 0.6cm, fill: blue))], '
    'replace("c", transition: morph())[#box(ellipse(width: 1cm, height: 0.5cm, fill: green))], '
    'replace("rr", transition: morph())[#box(rect(width: 2cm, height: 0.8cm, radius: 6pt, '
    "fill: blue))], "
    'replace("s", transition: morph())[#box(rect(width: 0.5cm, height: 0.3cm, stroke: 3pt))])'
)

# The same step undone, for the tests of two boundaries.
SHRINK = (
    "sub("
    + ", ".join(f'reset("{name}", transition: morph())' for name in ("f", "g", "c", "rr", "s"))
    + ")"
)


@pytest.fixture
def shapes(typst: TypstRunner):
    """A slide of three epochs, each boundary crossed by a morph of the region `r`."""
    return animated(typst, SHAPES, GROW, SHRINK, name="resize.html")


def resizing(presentation: Deck) -> bool:
    """Whether the engine animates `d`, which is what a resize needs."""
    return presentation.page.evaluate("""() => CSS.supports("d", 'path("M 0 0")')""")


# Every path below a label, per epoch rendering of the slide shown, as its box on the screen,
# which properties of a resize it animates, and the `d` and stroke width it shows.
PATHS = (
    """label => {
    const slide = document.querySelector('.animo-slide[data-animo-current]');
    const box = (path) => {
        const own = path.getBBox();
        const matrix = path.getScreenCTM();
        const corners = [[0, 0], [1, 0], [0, 1], [1, 1]].map(([u, v]) =>
            new DOMPoint(own.x + u * own.width, own.y + v * own.height).matrixTransform(matrix));
        const xs = corners.map((corner) => corner.x);
        const ys = corners.map((corner) => corner.y);
        return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
    };
    return ("""
    + UNDER
    + """)(slide, label).map(
        (groups) => groups.flatMap((group) => Array.from(group.querySelectorAll('path')))
            .filter((path) => path.closest("defs, clipPath, symbol") === null)
            .map((path) => {
                const animated = path.getAnimations().flatMap(
                    (animation) => animation.effect.getKeyframes().flatMap(Object.keys));
                const shown = getComputedStyle(path);
                return {
                    box: box(path),
                    d: animated.includes("d"),
                    width: animated.includes("strokeWidth"),
                    shown: shown.d ?? null,
                    stroke: shown.strokeWidth,
                    inline: path.style.d || path.style.strokeWidth || "",
                };
            }),
    );
}"""
)


def paths(presentation: Deck, label: str) -> list[list[dict]]:
    """Every path below a label, per epoch rendering."""
    return presentation.page.evaluate(PATHS, label)


def close(a: list[float], b: list[float]) -> bool:
    """Whether two boxes on the screen are the same to within `CLOSE`."""
    return all(abs(x - y) < CLOSE for x, y in zip(a, b, strict=True))


@pytest.fixture
def midway(page, deck_at, shapes) -> Deck:
    """The slide at the midpoint of the first step."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    return presentation.press("ArrowRight").scrub(MIDPOINT)


@pytest.mark.parametrize("label", ["f", "g", "c", "rr"])
def test_a_resized_shape_has_its_partner_halfway_between_the_two_boxes(
    page, deck_at, shapes, label
):
    """The claim a resize rests on, for a fraction bar, a rectangle, an ellipse and corners."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    rest = paths(presentation, label)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    halfway = paths(presentation, label)
    if not resizing(presentation):
        assert not any(path["d"] for rendering in halfway for path in rendering)
        return
    carried = [index for index, path in enumerate(halfway[0]) if path["d"]]
    assert len(carried) == 1, f"{len(carried)} paths of {label} are resized"
    [index] = carried
    partner = next(
        (other for other, path in enumerate(halfway[1]) if path["d"]),
        None,
    )
    assert partner is not None
    assert close(halfway[0][index]["box"], halfway[1][partner]["box"]), "the copies differ"
    start, end = rest[0][index]["box"], rest[1][partner]["box"]
    assert start != pytest.approx(end, abs=1), "the shape does not change"
    middle = [(a + b) / 2 for a, b in zip(start, end, strict=True)]
    assert close(halfway[0][index]["box"], middle), "the shape is off its route"


def test_both_copies_show_one_geometry(midway):
    """The two copies of the rounded rectangle compute the same `d`, corners included."""
    if not resizing(midway):
        pytest.skip("the engine does not animate d")
    outgoing, incoming = paths(midway, "rr")[:2]
    assert outgoing[0]["shown"] == incoming[0]["shown"]


def test_a_stroke_that_changes_width_is_resized(midway):
    """The `d` stays and the stroke width is halfway, on both copies."""
    outgoing, incoming = paths(midway, "s")[:2]
    if not resizing(midway):
        assert not outgoing[0]["width"]
        return
    for path in (outgoing[0], incoming[0]):
        assert path["width"]
        assert not path["d"]
        assert float(path["stroke"].removesuffix("px")) == pytest.approx(2, abs=1e-3)


def test_a_step_at_rest_writes_no_geometry(page, deck_at, shapes):
    """Neither `d` nor the stroke width is ever inline style, so a path shows its attribute."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    assert all(path["inline"] == "" for rendering in paths(presentation, "r") for path in rendering)
    presentation.scrub(DURATION).settle()
    assert presentation.page.evaluate("() => document.getAnimations().length") == 0
    assert all(path["inline"] == "" for rendering in paths(presentation, "r") for path in rendering)


def boxes(presentation: Deck) -> list[list[list[float]]]:
    """The box of every path of the region `r`, per epoch rendering."""
    return [[path["box"] for path in rendering] for rendering in paths(presentation, "r")]


def unmoved(before, after) -> None:
    """Assert that no path of the two renderings shown is displayed elsewhere than it was.

    The third rendering is not shown before a second step enters it.
    """
    for rendering in (0, 1):
        for index, (a, b) in enumerate(zip(before[rendering], after[rendering], strict=True)):
            assert close(a, b), f"path {index} of rendering {rendering} jumped"


def test_an_interrupted_resize_turns_back_from_where_it_is(page, deck_at, shapes):
    """A backward step halfway through starts from the geometry the page shows."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    before = boxes(presentation)
    presentation.press("ArrowLeft").scrub(0)
    unmoved(before, boxes(presentation))
    presentation.scrub(DURATION).settle()
    assert presentation.position == (1, 0)
    assert presentation.page.evaluate("() => document.getAnimations().length") == 0


def test_two_quick_steps_resize_nothing_abruptly(page, deck_at, shapes):
    """A second boundary crossed while the first one's resize is still under way."""
    presentation: Deck = deck_at(shapes)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    before = boxes(presentation)
    presentation.press("ArrowRight").scrub(0)
    unmoved(before, boxes(presentation))
    presentation.scrub(DURATION).settle()
    assert presentation.position == (1, 2)
    assert presentation.page.evaluate("() => document.getAnimations().length") == 0


# Two rectangles of one structure in two places of a region whose words are matched.
# One is removed before the words and the other added after them, so they are in two hunks.
# A circle is added beside the second, so that the tag holds two shapes after the step and
# does not pair the two rectangles as a shape morph.
HUNKS = """
  #region(name: "q")[
    #tag("h")[#box(rect(width: 0.5cm, height: 0.3cm, fill: blue)) Some words]
  ]
"""


def test_a_shape_removed_in_one_place_is_not_resized_into_one_added_in_another(
    page, deck_at, typst: TypstRunner
):
    """The words between the two rectangles are matched, so the two rectangles fade."""
    html = animated(
        typst,
        HUNKS,
        'sub(replace("h", transition: morph())[Some words '
        "#box(rect(width: 0.8cm, height: 0.3cm, fill: blue)) #box(circle(radius: 2pt))])",
        name="hunks.html",
    )
    presentation: Deck = deck_at(html)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    assert not any(path["d"] for rendering in paths(presentation, "q") for path in rendering)
    assert any(moving(presentation, "q", "use")[0])


# A rectangle that is replaced by a larger one in a separate tag.
FENCED = """
  #region(name: "k")[
    #tag("t")[#box(rect(width: 0.5cm, height: 0.3cm, fill: blue))]
  ]
"""


@pytest.mark.parametrize("fenced", [True, False])
def test_a_tag_keeps_two_shapes_apart(page, deck_at, typst: TypstRunner, fenced):
    """A shape in a tag is not resized into a shape outside it, and is without the tag."""
    rect = "#box(rect(width: 0.8cm, height: 0.3cm, fill: blue))"
    replacement = f'#tag("other")[{rect}]' if fenced else rect
    html = animated(
        typst,
        FENCED,
        f'sub(replace("t", transition: morph())[{replacement}])',
        name=f"fenced-{fenced}.html",
    )
    presentation: Deck = deck_at(html)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    resized = any(path["d"] for rendering in paths(presentation, "k") for path in rendering)
    assert resized == (resizing(presentation) and not fenced)


# A tag the boundary leaves alone around a tag it changes, with a stroked box between them.
NESTED = """
  #region(name: "o")[
    Before #tag("outer")[#box(stroke: 1pt, inset: 2pt)[#tag("inner")[word]]] after.
  ]
"""


def test_a_tag_that_holds_a_changed_tag_is_matched_in_its_place(page, deck_at, typst: TypstRunner):
    """The content of `outer` differs, so it is not carried as one, and its box is resized.

    The letters of `word` move to the end of the longer content, which they could not if
    `outer` were matched as a whole.
    """
    html = animated(
        typst,
        NESTED,
        'sub(replace("inner", transition: morph())[a much longer word])',
        name="nested.html",
    )
    presentation: Deck = deck_at(html)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    assert any(moving(presentation, "outer", "use")[0])
    box = paths(presentation, "outer")
    assert [path["d"] for path in box[0]] == [resizing(presentation)]


def test_an_engine_without_d_steps_through_without_errors(page, deck_at, shapes):
    """Webkit crossfades what the others resize, and every engine ends at rest."""
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
