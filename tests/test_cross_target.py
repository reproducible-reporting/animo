# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The invariant the whole design rests on: the HTML and paged targets lay out identically.

One source produces four outputs, and every later phase leans on the two targets agreeing:
regions measure their footprints once and expect both targets to reserve the same space,
and the handout is supposed to be the same slide the audience saw.
If the two drift, nothing downstream can be trusted, so the agreement is tested directly
rather than inferred from the features that depend on it.

It is expressed in numbers rather than in pixels.
Typst's own rasteriser and chromium's SVG renderer do not have to agree on the pixels of
a glyph, and asking them to would make this test fail on an unrelated upgrade.
They do have to agree on where a filled square lands, to a fraction of the slide.
"""

import numpy as np
import pytest
from decks import MARK_SIZE, MARKS, marks_deck
from harness import TypstRunner, screenshot

# The browser window is the deck's own aspect ratio, so the viewport fills it and the
# comparison is between two pictures of the same rectangle at two resolutions.
WINDOW = {"width": 908, "height": 511}

# The floor is one pixel of the coarser of the two rasters, which is 454 pixels wide,
# so 0.0022 of the slide. Measured on typst 0.15.1 and playwright's chromium 151,
# the two targets disagree by at most 0.0017 of the slide on any edge of any mark,
# which is that floor and not a layout difference.
TOLERANCE = 0.0025


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


@pytest.fixture
def rendered(page, typst: TypstRunner, paged):
    """The same one-slide deck, rasterised from the handout and screenshotted in chromium."""
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
        assert color_box(browser, hexcolor) == pytest.approx(
            color_box(paper, hexcolor), abs=TOLERANCE
        ), f"the {name} mark lands elsewhere in the browser than on paper"


@pytest.mark.parametrize("side", ["paper", "browser"])
def test_both_targets_agree_with_the_geometry_the_source_declares(rendered, side):
    """Agreeing with each other is not enough if both are wrong in the same way.

    This is the half that says the deck's margin, the viewport and the placements mean
    what the source says they mean, and it is why the marks are placed at round offsets.
    """
    image = rendered[0] if side == "paper" else rendered[1]
    for name, (hexcolor, dx, dy) in MARKS.items():
        assert color_box(image, hexcolor) == pytest.approx(declared_box(dx, dy), abs=TOLERANCE), (
            f"the {name} mark is not where the source places it"
        )


def test_the_handout_page_and_the_browser_frame_have_the_same_aspect(rendered):
    """A scaling mistake that kept every position right would still change every shape."""
    paper, browser = rendered
    assert paper.shape[1] / paper.shape[0] == pytest.approx(
        browser.shape[1] / browser.shape[0], rel=0.002
    )
