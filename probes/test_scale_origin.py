# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *The Centre a Scale Is About*.

A `scale` on paper and a `scale` in the browser have to grow the same box about the same point.
Typst's `scale` grows its body about the centre of the box typst laid out.
CSS with `transform-box: fill-box` grows a group about the centre of its ink,
which is a different rectangle whenever the ink does not fill the box.
These probes assert the behaviours that let the browser scale about the box instead.

- Typst scales about the centre of the layout box, wherever the ink sits inside it.
- `transform-box: fill-box` with `transform-origin: center` scales about the centre of the ink
  in chromium and webkit, and about a point that need not even be that in firefox.
- `transform-box: view-box` with `transform-origin` in `px` scales about that point of the
  user space of the group's parent, whatever translates the ancestors of that parent carry.
- Typst's `origin` picks the point per axis, from the start, the centre or the end of the box.
- An animated `transform-origin` in `px` under `view-box` passes through the points between
  its two ends, so a scaled group whose origin moves has no jump.
- A zero-size labelled box placed at `bottom + right` inside a box or a filling block is
  emitted as a group whose origin is the far corner of that box.
"""

import numpy as np
import pytest
from harness import PagedRunner, TypstRunner
from htmldoc import document

# A box 200 by 20 points whose ink is a 20 point square at its right end, so that the centre of
# the ink is 50 points right of the centre of the box.
# The box is the slot, inside a labelled box that typst positions with a translate, and the
# zero-size box placed at its far corner is a sibling of the slot.
INK_RIGHT = "box(width: 200pt, pad(left: 140pt, rect(width: 20pt, height: 20pt, fill: black)))"
CORNER = "place(bottom + right, [#box(width: 0pt, height: 0pt)<corner>])"
FRAME = f'#html.frame[#v(20pt)#h(30pt)#box({{ {INK_RIGHT}; {CORNER} }})#label("x")]\n'

# The centre of the ink and of the box, in the user space of the labelled group,
# whose origin is the corner of the box.
INK_CENTRE = (150.0, 10.0)
BOX_CENTRE = (100.0, 10.0)

# How far a centre measured in user units may be from the one the geometry predicts.
# The floor is the rounding of a transform in the browser, a hundredth of a point, while the
# difference these probes tell apart is the 50 points between the two centres, doubled.
TOLERANCE = 0.5

# The centre of the ink of the slot, in the user space of the labelled group.
INK = """() => {
    const outer = document.querySelector('[data-typst-label="x"]');
    const slot = outer.querySelector(':scope > g');
    const box = slot.getBBox();
    const m = outer.getScreenCTM().inverse().multiply(slot.getScreenCTM());
    const x = box.x + box.width / 2;
    const y = box.y + box.height / 2;
    return [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
}"""


def ink_centre(typst: TypstRunner, open_page, css: str, name: str) -> tuple[float, float]:
    """The centre of the ink of the slot, after the rules in `css` apply to it."""
    page = open_page(typst.html(document(FRAME, css), name=name))
    return tuple(page.evaluate(INK))


def test_typst_scales_about_the_centre_of_the_layout_box(paged: PagedRunner):
    """The paged outputs put a display state on the page with typst's `scale`.

    The ink of a doubled box lands as far again from the centre of the box as it was,
    so its centre moves from 150 to 200 points across the box.
    """
    source = (
        "#set page(width: 300pt, height: 60pt, margin: 0pt)\n"
        f"#place(dx: 50pt, dy: 20pt, scale(200%, reflow: false, {INK_RIGHT}))\n"
    )
    image = paged.png(source, ppi=144)[0]
    ink = image.min(axis=2) < 128
    columns = np.flatnonzero(ink.any(axis=0))
    rows = np.flatnonzero(ink.any(axis=1))
    # From pixels at 144 ppi, which is 2 pixels per point, to points of the page.
    centre = ((columns[0] + columns[-1] + 1) / 4, (rows[0] + rows[-1] + 1) / 4)
    assert centre == pytest.approx((50 + 2 * INK_CENTRE[0] - BOX_CENTRE[0], 30), abs=1.0)


# Two origins of typst's `scale`, each with the centre of the ink of the doubled box on the
# page.
# A start edge stays put on its axis and a centre keeps the centre of the box,
# so the ink lands 2 * 150 - 0 = 300 or 2 * 150 - 100 = 200 points across the box,
# and 2 * 10 - 0 = 20 or 2 * 10 - 10 = 10 points down it.
TYPST_ORIGINS = {
    "left + horizon": (50 + 300, 20 + 10),
    "center + top": (50 + 200, 20 + 20),
}


@pytest.mark.parametrize("origin", TYPST_ORIGINS)
def test_typst_scales_about_an_origin_per_axis(paged: PagedRunner, origin: str):
    """Each axis of a paged `scale` grows from the start of the box or about its centre.

    The alignment of each axis is independent, so a tag placed on one axis only can grow
    from its edge on that axis and about its centre on the other.
    """
    source = (
        "#set page(width: 450pt, height: 80pt, margin: 0pt)\n"
        f"#place(dx: 50pt, dy: 20pt, scale(200%, origin: {origin}, reflow: false, {INK_RIGHT}))\n"
    )
    image = paged.png(source, ppi=144)[0]
    ink = image.min(axis=2) < 128
    columns = np.flatnonzero(ink.any(axis=0))
    rows = np.flatnonzero(ink.any(axis=1))
    # From pixels at 144 ppi, which is 2 pixels per point, to points of the page.
    centre = ((columns[0] + columns[-1] + 1) / 4, (rows[0] + rows[-1] + 1) / 4)
    assert centre == pytest.approx(TYPST_ORIGINS[origin], abs=1.0)


# The point `fill-box` with a centred origin scales about, per engine.
# Chromium 151 and webkit 26.5 take the centre of the ink.
# Firefox 153 takes the box of the path without the `transform` attribute typst wrote on it,
# which is the 20 point square at the left end of the box, so it scales about x = 10.
FILL_BOX_ORIGIN = {
    "chromium": INK_CENTRE,
    "firefox": (10.0, 10.0),
    "webkit": INK_CENTRE,
}


def test_fill_box_scales_about_the_centre_of_the_ink(typst: TypstRunner, open_page, browser_name):
    """The ink lands elsewhere than on paper, and in firefox elsewhere than in chromium.

    Neither engine scales about the centre of the box typst laid out.
    """
    css = """\
[data-typst-label="x"] > g {
  scale: 2;
  transform-box: fill-box;
  transform-origin: center;
}"""
    centre = ink_centre(typst, open_page, css, "fill-box.html")
    origin = FILL_BOX_ORIGIN[browser_name]
    expected = tuple(2 * ink - at for ink, at in zip(INK_CENTRE, origin, strict=True))
    assert centre == pytest.approx(expected, abs=TOLERANCE)


def test_view_box_scales_about_a_point_of_the_parent_user_space(typst: TypstRunner, open_page):
    """A `px` origin under `view-box` is a point of the user space the slot is laid out in.

    The labelled group that holds the slot carries the translate typst positioned it with,
    and so do the groups around it, and none of them enters the origin.
    An origin at the centre of the box makes the browser agree with paper.
    """
    css = f"""\
[data-typst-label="x"] > g {{
  scale: 2;
  transform-box: view-box;
  transform-origin: {BOX_CENTRE[0]}px {BOX_CENTRE[1]}px;
}}"""
    centre = ink_centre(typst, open_page, css, "view-box.html")
    expected = tuple(2 * ink - box for ink, box in zip(INK_CENTRE, BOX_CENTRE, strict=True))
    assert centre == pytest.approx(expected, abs=TOLERANCE)


# A zero-size box placed at the far corner of a hugging box, of a filling block whose height
# its content decides, and of a filling block in a paragraph, laid out by a `move`,
# which is how a tag holds a block-level body.
CORNER_SITES = {
    "box": (INK_RIGHT, (200.0, 20.0)),
    "block": (
        "block(width: 100%, rect(width: 40pt, height: 30pt))",
        (300.0, 30.0),
    ),
    "moved block": (
        "move(block(width: 100%, rect(width: 40pt, height: 30pt)))",
        (300.0, 30.0),
    ),
}


@pytest.mark.parametrize("site", CORNER_SITES)
def test_a_placed_zero_size_box_is_a_group_at_the_far_corner(
    typst: TypstRunner, open_page, site: str
):
    """The browser reads the size of a slot off the origin of such a group.

    The group is a child of the labelled group, beside the slot,
    so its origin in the user space of the labelled group is the width and the height of the box.
    """
    body, expected = CORNER_SITES[site]
    wrapper = "box" if site == "box" else "block.with(width: 100%)"
    frame = (
        "#html.frame[#block(width: 300pt)[Before.\n\n"
        f'  #{wrapper}({{ {body}; {CORNER} }})#label("x")\n\n  After.]]\n'
    )
    page = open_page(typst.html(frame, name="corner.html"))
    corner = page.evaluate(
        """() => {
            const outer = document.querySelector('[data-typst-label="x"]');
            const marker = outer.querySelector(':scope > [data-typst-label="corner"]');
            const m = outer.getScreenCTM().inverse().multiply(marker.getScreenCTM());
            return [m.e, m.f];
        }"""
    )
    assert tuple(corner) == pytest.approx(expected, abs=0.01)


def test_an_animated_view_box_origin_passes_through_the_points_between(
    typst: TypstRunner, open_page
):
    """Halfway through, the origin is the point halfway between its two ends.

    The slot is doubled throughout, while its origin travels from the centre of the box to its
    corner, which is how a scaled tag comes to grow from the corner that a `move` puts on a
    target.
    The engine interpolates the two lengths of the origin, so the ink travels in a straight
    line and with no jump at either end.
    """
    css = """\
[data-typst-label="x"] > g {
  scale: 2;
  transform-box: view-box;
}"""
    page = open_page(typst.html(document(FRAME, css), name="travelling-origin.html"))
    start = f"{BOX_CENTRE[0]}px {BOX_CENTRE[1]}px"
    page.evaluate(
        """(start) => {
            const slot = document.querySelector('[data-typst-label="x"] > g');
            const keyframes = [{ transformOrigin: start }, { transformOrigin: "0px 0px" }];
            const animation = slot.animate(keyframes, { duration: 1000, easing: "linear" });
            animation.pause();
            animation.currentTime = 500;
        }""",
        start,
    )
    halfway = tuple(at / 2 for at in BOX_CENTRE)
    expected = tuple(2 * ink - at for ink, at in zip(INK_CENTRE, halfway, strict=True))
    assert tuple(page.evaluate(INK)) == pytest.approx(expected, abs=TOLERANCE)
