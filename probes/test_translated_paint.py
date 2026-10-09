# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A `translate` carries an element's clip and gradient, not an ancestor's clip*.

A morph moves a matched element with a CSS `translate`, and whether that is the whole of the
motion depends on what else draws the element.
Typst writes a clipped box as a group with a `clip-path` whose path is in that group's user
space, and a gradient as a paint server in `userSpaceOnUse`.
Each probe moves one element by a whole number of CSS pixels and compares what is drawn at
the new place with what was drawn at the old one.
Nothing of animo is involved apart from the hoisting of the paint servers into another
`<svg>`, which is reproduced here because it is how a deck references them.
"""

import numpy as np
from harness import TypstRunner, screenshot
from htmldoc import document

# A clipped box holding a circle with a gradient, a clipped box holding two letters, and a
# rectangle with a gradient and a stroke. A label on a shape is not written to the output, so
# the rectangle is found as the only path with a stroke.
BODY = """\
#html.frame(block(width: 400pt, height: 200pt, {
  place(top + left, dx: 10pt, dy: 10pt, [#box(
    clip: true, width: 40pt, height: 40pt, circle(radius: 30pt, fill: gradient.linear(red, blue)),
  )#label("clipped")])
  place(top + left, dx: 10pt, dy: 100pt, [#box(clip: true, width: 60pt, height: 40pt, [#box(
    text(size: 30pt)[Ab],
  )#label("inner")])#label("outer")])
  place(top + left, dx: 200pt, dy: 10pt, rect(
    width: 40pt, height: 30pt, fill: gradient.linear(red, blue), stroke: 2pt + green,
  ))
}))
"""

# One user unit of the frame is one CSS pixel, so that a `translate` in the element's user space
# moves it by a whole number of pixels on the screen.
CSS = """\
body { margin: 0; background: #ffffff; }
svg { width: 400px !important; height: 200px !important; }
"""

# How far each probe moves its element, in CSS pixels and in user units.
SHIFT = (120, 30)

# Move every paint server and clip path into a zero-size `<svg>` of its own, as the runtime
# does when it hoists them, so that the references cross from one `<svg>` to another.
HOIST = """() => {
    const holder = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    holder.setAttribute("width", "0");
    holder.setAttribute("height", "0");
    holder.style.cssText = "position: absolute; overflow: hidden";
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    for (const node of document.querySelectorAll("clipPath, linearGradient")) {
        defs.append(node);
    }
    holder.append(defs);
    document.body.prepend(holder);
}"""

# The box an element draws in, in CSS pixels, rounded out to whole pixels with a margin.
BOX = """(selector) => {
    const element = document.querySelector(selector);
    const box = element.getBBox();
    const matrix = element.getScreenCTM();
    const corners = [[box.x, box.y], [box.x + box.width, box.y + box.height]].map(
        ([x, y]) => new DOMPoint(x, y).matrixTransform(matrix));
    const left = Math.floor(Math.min(...corners.map((p) => p.x))) - 3;
    const top = Math.floor(Math.min(...corners.map((p) => p.y))) - 3;
    const right = Math.ceil(Math.max(...corners.map((p) => p.x))) + 3;
    const bottom = Math.ceil(Math.max(...corners.map((p) => p.y))) + 3;
    return {x: left, y: top, width: right - left, height: bottom - top};
}"""


def opened(typst: TypstRunner, open_page, name: str):
    """The document in a page, with its paint servers hoisted."""
    page = open_page(typst.html(document(BODY, CSS), name=name))
    page.evaluate(HOIST)
    return page


def moved(page, selector: str, clip: dict) -> tuple[np.ndarray, np.ndarray]:
    """What an element draws before and after a `translate` of `SHIFT`, each at its place."""
    before = screenshot(page, clip=clip)
    page.evaluate(
        "([selector, x, y]) => { document.querySelector(selector).style.translate = "
        "`${x}px ${y}px`; }",
        [selector, *SHIFT],
    )
    after = screenshot(page, clip={**clip, "x": clip["x"] + SHIFT[0], "y": clip["y"] + SHIFT[1]})
    return before, after


def ink(image: np.ndarray) -> int:
    """The number of pixels that are not white."""
    return int((image.min(axis=2) < 250).sum())


def largest(a: np.ndarray, b: np.ndarray) -> int:
    """The largest difference between two rasters, out of 255."""
    return int(abs(a.astype(int) - b.astype(int)).max())


def test_a_translated_group_carries_its_own_clip(typst: TypstRunner, open_page):
    """The group that holds `clip-path` moves with its clip, which is what a tag match needs.

    The clip path is in the group's user space, and the `translate` acts before that space is
    resolved, so the clipped circle arrives whole and with the same edges.
    """
    page = opened(typst, open_page, "own.html")
    selector = '[data-typst-label="clipped"] > g'
    clip = page.evaluate(BOX, selector)
    before, after = moved(page, selector, clip)
    assert ink(before) > 1000, "the clipped circle is not in the compared box"
    assert largest(before, after) <= 2


def test_a_translated_child_stays_under_its_ancestors_clip(typst: TypstRunner, open_page):
    """A clip above the moved element stays where it is and cuts the element off.

    Two copies of a letter under two clips at two places are therefore not drawn alike while
    they move, and the morph keeps such a pair apart.
    """
    page = opened(typst, open_page, "ancestor.html")
    page.evaluate(
        "() => { document.querySelector('[data-typst-label=\"inner\"]').style.translate = "
        "'0px 30px'; }"
    )
    # The 40 px below the clip, which ends 140 px from the top of the frame.
    origin = page.evaluate(
        "() => document.querySelector('svg:not([width=\"0\"])').getBoundingClientRect().toJSON()"
    )
    below = {"x": origin["x"] + 10, "y": origin["y"] + 140, "width": 60, "height": 40}
    assert ink(screenshot(page, clip=below)) == 0
    # Without the clip, the moved letters do reach below it.
    page.evaluate(
        "() => document.querySelector('[data-typst-label=\"outer\"] > g')"
        ".removeAttribute('clip-path')"
    )
    assert ink(screenshot(page, clip=below)) > 50, "the letters did not move below the clip"


def test_a_translated_shape_carries_its_gradient(typst: TypstRunner, open_page):
    """A gradient in `userSpaceOnUse` is in the space of the shape that references it.

    The `translate` changes that space, so the gradient moves with the shape, also when the
    gradient is defined in another `<svg>`.
    """
    page = opened(typst, open_page, "gradient.html")
    selector = "path[stroke]"
    clip = page.evaluate(BOX, selector)
    before, after = moved(page, selector, clip)
    colours = len(np.unique(before.reshape(-1, 3), axis=0))
    assert colours > 20, "the rectangle does not show a gradient"
    assert largest(before, after) <= 2
