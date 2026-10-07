# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A morph keeps the `plus-lighter` sum*, for a stroke and for a raster image.

`test_morph_sum.py` measures the sum on letters, which are filled outlines.
A stroke is antialiased along both of its edges, and a raster image is resampled when it is
drawn at a size or a place that is not a whole number of its pixels, so neither is a letter.
Two renderings of one frame stand for two epochs of a region, and each holds the same element
at another place. They are summed under `plus-lighter`, as a crossfade sums them, and the
outgoing copy travels to the place of the incoming one while the incoming copy comes from the
place of the outgoing one, as a morph moves them.
"""

import pytest
from harness import TypstRunner, screenshot
from htmldoc import document
from PIL import Image
from test_morph_sum import DURATION, deviation

# The element each probe moves, as typst markup, and where it sits in each rendering.
# The shift is not a whole number of pixels, so the copies are resampled on the way.
SHAPES = {
    "stroke": "rect(width: 60pt, height: 30pt, stroke: 1.5pt + black)",
    "image": 'image("pattern.png", width: 60pt)',
}
PLACES = ((10, 10), (137.3, 41.7))

CSS = """\
body { margin: 0; background: #ffffff; }
svg { isolation: isolate; }
[data-typst-label="r0"], [data-typst-label="r1"] { mix-blend-mode: plus-lighter; }
"""


def body(kind: str) -> str:
    """Two renderings of one frame, each holding the element at its place."""
    renderings = "\n".join(
        f"  place(top + left, [#box(width: 240pt, height: 100pt, place(top + left, "
        f'dx: {x}pt, dy: {y}pt, {SHAPES[kind]}))#label("r{index}")])'
        for index, (x, y) in enumerate(PLACES)
    )
    return f"#html.frame(block(width: 240pt, height: 100pt, {{\n{renderings}\n}}))\n"


def pattern(path) -> None:
    """A raster of 30 by 15 pixels with a gradient and hard edges, drawn at twice its size."""
    image = Image.new("RGB", (30, 15))
    for x in range(30):
        for y in range(15):
            edge = 0 if (x // 5 + y // 5) % 2 else 120
            image.putpixel((x, y), (8 * x, edge, 255 - 16 * y))
    image.save(path)


# The element of each rendering, and each copy's route as a `translate` in the user space of
# its parent.
SETUP = """(selector) => {
    const [r0, r1] = ["r0", "r1"].map((label) =>
        document.querySelector(`[data-typst-label="${label}"]`));
    const [e0, e1] = [r0, r1].map((rendering) => rendering.querySelector(selector));
    const origin = (element) => new DOMPoint(0, 0).matrixTransform(element.getScreenCTM());
    const inParent = (element, x, y) => new DOMPoint(x, y, 0, 0)
        .matrixTransform(element.parentNode.getScreenCTM().inverse());
    const start = origin(e0);
    const end = origin(e1);
    const dx = end.x - start.x, dy = end.y - start.y;
    window.probe = {r0, r1, e0, e1, out: inParent(e0, dx, dy), back: inParent(e1, -dx, -dy)};
    return {dx, dy};
}"""

# The morph at one fraction of the step, paused at that moment.
MORPH = """([duration, fraction]) => {
    const {r0, r1, e0, e1, out, back} = window.probe;
    const timing = {duration, easing: "linear", fill: "both"};
    e0.animate([{translate: "0px 0px"}, {translate: `${out.x}px ${out.y}px`}], timing);
    e1.animate([{translate: `${back.x}px ${back.y}px`}, {translate: "0px 0px"}], timing);
    r0.animate([{opacity: 1}, {opacity: 0}], timing);
    r1.animate([{opacity: 0}, {opacity: 1}], timing);
    for (const animation of document.getAnimations()) {
        animation.pause();
        animation.currentTime = duration * fraction;
    }
}"""

# One opaque incoming copy where the route puts it, with an opacity animation held at one on
# its rendering, for the reason `test_morph_sum.py` gives.
REFERENCE = """([duration, fraction]) => {
    const {r0, r1, e1, back} = window.probe;
    for (const animation of document.getAnimations()) {
        animation.cancel();
    }
    r0.style.visibility = "hidden";
    const rest = 1 - fraction;
    e1.style.translate = `${back.x * rest}px ${back.y * rest}px`;
    const hold = r1.animate([{opacity: 1}, {opacity: 1}], {duration, fill: "both"});
    hold.pause();
    hold.currentTime = duration / 2;
}"""

# The box both copies travel through, with room for antialiasing.
BOX = """() => {
    const {e0, e1} = window.probe;
    const boxes = [e0, e1].map((element) => element.getBoundingClientRect());
    const left = Math.min(...boxes.map((box) => box.left)) - 4;
    const right = Math.max(...boxes.map((box) => box.right)) + 4;
    const top = Math.min(...boxes.map((box) => box.top)) - 4;
    const bottom = Math.max(...boxes.map((box) => box.bottom)) + 4;
    return {x: Math.max(0, left), y: Math.max(0, top), width: right - left, height: bottom - top};
}"""

# How far the midpoint of the morph may sit from one opaque copy, per engine and element, as
# a largest difference out of 255 and a number of pixels above 2/255.
MIDPOINT = {
    "chromium": {"stroke": (2, 0), "image": (2, 0)},
    "firefox": {"stroke": (2, 0), "image": (2, 0)},
    "webkit": {"stroke": (2, 0), "image": (2, 0)},
}

# What each probe moves, as a selector inside a rendering.
SELECTORS = {"stroke": "path", "image": "image"}


@pytest.mark.parametrize("kind", ["stroke", "image"])
def test_the_two_copies_of_a_moving_element_sum_to_one(
    typst: TypstRunner, open_page, browser_name, kind
):
    """The claim of the glyph probe, for an element that is not a letter."""
    pattern(typst.scratch / "pattern.png")
    page = open_page(typst.html(document(body(kind), CSS), name=f"{kind}.html"))
    shift = page.evaluate(SETUP, SELECTORS[kind])
    assert shift["dx"] > 100, "the two copies are not at two places"
    page.evaluate(MORPH, [DURATION, 0.5])
    clip = page.evaluate(BOX)
    morph = screenshot(page, animations="allow", clip=clip)
    page.evaluate(REFERENCE, [DURATION, 0.5])
    reference = screenshot(page, animations="allow", clip=clip)
    largest, pixels, ink = deviation(reference, morph)
    allowed_largest, allowed_pixels = MIDPOINT[browser_name][kind]
    assert ink > 300, "the element is not in the compared box"
    assert largest <= allowed_largest, f"the midpoint differs by {largest}/255"
    assert pixels <= allowed_pixels, f"{pixels} of {ink} ink pixels differ by more than 2/255"
