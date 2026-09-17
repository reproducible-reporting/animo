# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The invariant the whole design rests on: the HTML and paged targets lay out identically.

One source produces three output types, and much of the design leans on the two targets agreeing:
regions measure their footprints once and expect both targets to reserve the same space,
and the handout is supposed to be the same slide the audience saw.
If the two drift, nothing downstream can be trusted, so the agreement is tested directly
rather than inferred from the features that depend on it.

It is expressed in numbers rather than in pixels.
Typst's own rasteriser and a browser's SVG renderer do not have to agree on the pixels of
a glyph, and asking them to would make this test fail on an unrelated upgrade.
They do have to agree on where a filled square lands, to a fraction of the slide.
"""

import numpy as np
import pytest
from decks import MARK_SIZE, MARKS, deck, marks_deck
from harness import Deck, TypstRunner, screenshot

# The browser window is the deck's own aspect ratio, so the viewport fills it and the
# comparison is between two pictures of the same rectangle at two resolutions.
WINDOW = {"width": 908, "height": 511}

# The floor of this measurement is two pixels of the raster the edge is read out of,
# and the two axes do not share it: the handout page is 454 by 255 pixels at 72 ppi,
# so a pixel is 0.0022 of the slide across and 0.0039 down, while the screenshot is twice
# that in each direction.
#
# Two pixels rather than one, for two reasons that each cost up to one.
# An edge quantised into a raster lands on a pixel boundary, so the same edge read out of
# two rasters of different resolution differs by up to a pixel of the coarser one.
# And the box is the extent of the *exact* mark colour, so a row of edge pixels that a
# renderer antialiases is not counted at all.
# Neither is a layout difference, and a real one is far larger: a lost margin would be
# 0.11 of the slide and the `em` sizing bug of *Findings* was 0.08.
#
# Measured on typst 0.15.1, chromium 151 and firefox 153, the largest disagreement is one
# pixel of the coarser raster. The only place the two engines differ from each other is
# the bottom edge of the red mark, by one pixel of the 511-pixel screenshot, which is a
# row of edge pixels firefox blends and chromium does not.


def color_box(image: np.ndarray, hexcolor: str) -> tuple[float, float, float, float]:
    """The bounding box of one exact colour, as fractions of the image.

    Returns
    -------
    box
        `(left, top, right, bottom)`, each between zero and one.
    """
    rgb = np.array([int(hexcolor[i : i + 2], 16) for i in (1, 3, 5)], dtype=np.uint8)
    found = (image == rgb).all(axis=2)
    assert found.any(), f"no pixel of {hexcolor} in a {image.shape[1]}x{image.shape[0]} raster"
    rows = np.flatnonzero(found.any(axis=1))
    columns = np.flatnonzero(found.any(axis=0))
    height, width = found.shape
    return (
        columns[0] / width,
        rows[0] / height,
        (columns[-1] + 1) / width,
        (rows[-1] + 1) / height,
    )


def centimetres(value: str) -> float:
    """The number in a typst length literal written in centimetres."""
    return float(value.removesuffix("cm"))


def declared_box(dx: str, dy: str) -> tuple[float, float, float, float]:
    """Where a mark should land, from the deck's shape and the offsets in the source."""
    margin, size = 1.0, centimetres(MARK_SIZE)
    left = (margin + centimetres(dx)) / 16.0
    top = (margin + centimetres(dy)) / 9.0
    return (left, top, left + size / 16.0, top + size / 9.0)


def floor(image: np.ndarray) -> tuple[float, float]:
    """Two pixels of a raster, horizontally and vertically, as fractions of it."""
    height, width = image.shape[:2]
    return 2 / width, 2 / height


def assert_boxes_agree(got, expected, coarser: np.ndarray, what: str):
    """Compare two boxes edge by edge, each axis against the floor of `coarser`."""
    across, down = floor(coarser)
    assert (got[0], got[2]) == pytest.approx((expected[0], expected[2]), abs=across), what
    assert (got[1], got[3]) == pytest.approx((expected[1], expected[3]), abs=down), what


@pytest.fixture
def rendered(page, typst: TypstRunner, paged):
    """The same one-slide deck, rasterised from the handout and screenshotted in a browser."""
    source = typst.source(marks_deck())
    paper = paged.png(source)
    assert len(paper) == 1
    page.set_viewport_size(WINDOW)
    page.goto(typst.html(source, name="marks.html").resolve().as_uri())
    browser = screenshot(page.locator(".animo-slide[data-animo-current]"))
    return paper[0], browser


def test_the_two_targets_put_the_same_content_in_the_same_place(rendered):
    """The invariant itself, as a number per edge of every mark."""
    paper, browser = rendered
    for name, (hexcolor, _, _) in MARKS.items():
        assert_boxes_agree(
            color_box(browser, hexcolor),
            color_box(paper, hexcolor),
            paper,
            f"the {name} mark lands elsewhere in the browser than on paper",
        )


@pytest.mark.parametrize("side", ["paper", "browser"])
def test_both_targets_agree_with_the_geometry_the_source_declares(rendered, side):
    """Agreeing with each other is not enough if both are wrong in the same way.

    This is the half that says the deck's margin, the viewport and the placements mean
    what the source says they mean, and it is why the marks are placed at round offsets.
    """
    image = rendered[0] if side == "paper" else rendered[1]
    for name, (hexcolor, dx, dy) in MARKS.items():
        assert_boxes_agree(
            color_box(image, hexcolor),
            declared_box(dx, dy),
            image,
            f"the {name} mark is not where the source places it",
        )


def test_a_panned_state_shows_the_same_part_of_the_canvas_in_both_targets(
    page, typst: TypstRunner, paged
):
    """The invariant again, for a viewport that is no longer at the canvas origin.

    The pan is a `relto`, which is the case where the two targets resolve the position
    by different means: typst from a marker's position, the browser from a group's origin.
    """
    marks = {
        "green": ("#00ff00", "17cm", "1cm"),
        "blue": ("#0000ff", "20cm", "4cm"),
    }
    placements = "\n  ".join(
        f'#place(dx: {dx}, dy: {dy}, tag("{name}", wrap: box, '
        f'rect(width: {MARK_SIZE}, height: {MARK_SIZE}, fill: rgb("{color}"))))'
        for name, (color, dx, dy) in marks.items()
    )
    animation = '{ import anim: *\n  sub(pan(relto: "green")) }'
    source = typst.source(deck(f"slide(animation: {animation})[\n  {placements}\n]"))
    paper = paged.png(source, mode="presentation")[1]
    page.set_viewport_size(WINDOW)
    page.goto(typst.html(source, name="panned.html").resolve().as_uri() + "#1.1")
    page.wait_for_function("() => document.documentElement.dataset.animo === '1.1'")
    browser = screenshot(page.locator(".animo-slide[data-animo-current]"))
    for name, (hexcolor, dx, dy) in marks.items():
        # Panned to green, so every mark lands 17 cm left of and 1 cm above its place.
        expected = declared_box(f"{centimetres(dx) - 17}cm", f"{centimetres(dy) - 1}cm")
        for side, image in (("paper", paper), ("browser", browser)):
            assert_boxes_agree(
                color_box(image, hexcolor), expected, image, f"the {name} mark on {side}"
            )


# The tag sites a `relto` may name, one slide each, with something before the tag so that
# its anchor is not the body origin. Every kind of place a tag can sit is here, because the
# two targets read an anchor differently and a kind that one of them reads wrong is the
# failure this measures: typst records a tag in the middle of a line at the line's baseline.
RELTO_SITES = {
    "placed": '#place(dx: 7cm, dy: 3cm, tag("a", wrap: box, rect(width: 1cm, height: 1cm)))',
    "inline phrase": 'A few words and #tag("a")[a tagged phrase] in a paragraph.',
    "inline box": 'Words #tag("a")[#box(rect(width: 5mm, height: 8mm))] and words.',
    "block": 'A paragraph first.\n\n  #tag("a", wrap: block)[A block-level paragraph.]',
    "centred figure": 'Before.\n\n  #tag("a")[#figure(rect(width: 3cm), caption: [Cap])]',
    "math": '$ x = #tag("a")[$y^2$] + z $',
    "heading text": 'Before.\n\n  = #tag("a")[A heading]',
    "grid cell": '#grid(columns: (1fr, 1fr), [left], tag("a")[right])',
    "list item": '- one\n  - #tag("a")[two]',
    "nested tag": '#tag("outer")[before #tag("a")[inner] after]',
}

# How far the two targets may disagree about where a `relto` puts the viewport, in points.
# Measured on typst 0.15.1 over these sites, at windows 1280 and 640 pixels wide: at most
# 0.001 pt in chromium 151 and 0.005 pt in firefox 153, which is the rounding of the two
# boxes the browser's pan is read off. The disagreement this guards against is a box height,
# which is what reading typst's own position of a tag in the middle of a line would cost.
RELTO_TOLERANCE = 0.05


def test_relto_resolves_to_the_same_anchor_in_both_targets(deck_at, typst: TypstRunner):
    """The open question of the design, measured rather than assumed, for every kind of site.

    The browser's numbers are handed to the paged compilation through `--input`, which
    asserts the agreement inside the document that resolved its own.
    """
    slides = [
        f"slide(animation: {{ import anim: *\n  sub(pan(relto: \"a\")) }})[\n  {body}\n]"
        for body in RELTO_SITES.values()
    ]
    source = typst.source(deck(*slides))
    presentation: Deck = deck_at(typst.html(source, name="relto.html"))
    inputs = {}
    for index in range(1, len(RELTO_SITES) + 1):
        x, y = presentation.goto(index, 1).pan
        inputs[f"x{index}"], inputs[f"y{index}"] = repr(x), repr(y)
    lines = []
    for index, kind in enumerate(RELTO_SITES, start=1):
        for axis in "xy":
            lines.append(
                f"  let paper = pans.at({index - 1}).at(1).{axis}.pt()\n"
                f'  let browser = float(sys.inputs.{axis}{index})\n'
                f"  assert(calc.abs(paper - browser) < {RELTO_TOLERANCE}, message: "
                f'"{kind} {axis}: paper " + repr(paper) + ", browser " + repr(browser))'
            )
    check = (
        "#context {\n"
        "  let pans = query(<animo-geometry>).map(it => it.value.pans)\n"
        + "\n".join(lines)
        + "\n}\n"
    )
    typst.ok(source.read_text() + check, sysinp=inputs)


# How far the two targets may disagree about how far a `move` translates a tag, in points.
# A move reads two anchors and subtracts them, so the rounding of a `relto` enters twice,
# and one of the two is the anchor of the tag being transformed, which is the case an inline
# tag site makes awkward: the wrapper's own position is the line's baseline.
# Measured on typst 0.15.1 over the sites below, at windows 1280 and 640 pixels wide: at
# most 0.0005 pt in chromium 151 and in firefox 153, over every kind of site. That is ten
# times closer than the `relto` figure above, because the browser's own translation is read
# here where a pan is read off two boxes. The same allowance is kept all the same, since the
# disagreement this guards against is a box height either way.
MOVE_TOLERANCE = RELTO_TOLERANCE


def test_a_move_resolves_to_the_same_translation_in_both_targets(deck_at, typst: TypstRunner):
    """A move subtracts two anchors, so a target that reads either one wrong lands elsewhere.

    The browser's own translation is read rather than the geometry it produces: it is the
    number the runtime computed, in the user units of the frame, which are typst points,
    so the comparison is between the two resolutions and not between two measurements.
    Paper publishes its own beside the pans it resolved.
    """
    target = '#place(dx: 11cm, dy: 5cm, tag("m", wrap: box, rect(width: 1cm, height: 1cm)))'
    slides = [
        f'slide(animation: {{ import anim: *\n  sub(move("m", relto: "a")) }})'
        f"[\n  {body}\n  {target}\n]"
        for body in RELTO_SITES.values()
    ]
    source = typst.source(deck(*slides))
    presentation: Deck = deck_at(typst.html(source, name="moved.html"))
    inputs = {}
    for index in range(1, len(RELTO_SITES) + 1):
        translate = presentation.goto(index, 1).styles("m")[0]["translate"]
        x, y = (float(value.removesuffix("px")) for value in translate.split())
        inputs[f"x{index}"], inputs[f"y{index}"] = repr(x), repr(y)
    lines = []
    for index, kind in enumerate(RELTO_SITES, start=1):
        for axis in "xy":
            lines.append(
                f"  let paper = displays.at({index - 1}).at(1).m.{axis}.pt()\n"
                f"  let browser = float(sys.inputs.{axis}{index})\n"
                f"  assert(calc.abs(paper - browser) < {MOVE_TOLERANCE}, message: "
                f'"{kind} {axis}: paper " + repr(paper) + ", browser " + repr(browser))'
            )
    check = (
        "#context {\n"
        "  let displays = query(<animo-geometry>).map(it => it.value.displays)\n"
        + "\n".join(lines)
        + "\n}\n"
    )
    typst.ok(source.read_text() + check, sysinp=inputs)


def test_the_handout_page_and_the_browser_frame_have_the_same_aspect(rendered):
    """A scaling mistake that kept every position right would still change every shape."""
    paper, browser = rendered
    assert paper.shape[1] / paper.shape[0] == pytest.approx(
        browser.shape[1] / browser.shape[0], rel=0.002
    )
