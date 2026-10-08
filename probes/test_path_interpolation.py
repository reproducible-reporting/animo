# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *The `d` of a path interpolates between paths of one structure*.

A resize carries a shape whose geometry changes while its commands stay the same, such as a
fraction bar that widens or a rounded rectangle that grows, by animating the CSS `d` property
of both copies from the outgoing path to the incoming one.
That rests on what the engines do with `d`: whether they animate it at all, how they
interpolate the relative commands typst writes, what they do with two paths whose commands
differ, whether `getBBox()` follows the animated geometry, and whether two copies that resize
together still sum to one opaque shape under `plus-lighter`.
The paths are the ones typst 0.15.0 writes, read from a compiled frame.
"""

import re

import pytest
from harness import TypstRunner, screenshot
from htmldoc import document
from test_morph_sum import DURATION, deviation

# Pairs of shapes of one structure, each written twice at two sizes, and a pair whose
# structures differ. Every shape is placed at the origin of its own rendering.
# The shapes are filled, because typst strokes a shape without a fill and writes the stroke
# as a path of its own, which starts elsewhere.
PAIRS = {
    "rect": (
        "rect(width: 20pt, height: 10pt, fill: black)",
        "rect(width: 40pt, height: 30pt, fill: black)",
    ),
    "rounded": (
        "rect(width: 20pt, height: 10pt, radius: 2pt, fill: black)",
        "rect(width: 40pt, height: 30pt, radius: 8pt, fill: black)",
    ),
    "ellipse": (
        "circle(radius: 5pt, fill: black)",
        "ellipse(width: 30pt, height: 10pt, fill: black)",
    ),
    "line": ("line(length: 6pt, stroke: 0.5pt)", "line(length: 24pt, stroke: 0.5pt)"),
    "sharp-rounded": (
        "rect(width: 20pt, height: 10pt, fill: black)",
        "rect(width: 20pt, height: 10pt, radius: 2pt, fill: black)",
    ),
}

CSS = """\
body { margin: 0; background: #ffffff; }
svg { isolation: isolate; }
[data-typst-label^="r"] { mix-blend-mode: plus-lighter; }
"""


def body(pairs: dict[str, tuple[str, str]]) -> str:
    """One frame with a rendering per shape, labelled by the pair and the side."""
    places = []
    for row, (name, shapes) in enumerate(pairs.items()):
        for side, shape in enumerate(shapes):
            places.append(
                f"  place(top + left, dx: {10 + 120 * side}pt, dy: {10 + 50 * row}pt, "
                f'[#box({shape})#label("{name}-{side}")])'
            )
    height = 50 * len(pairs) + 20
    return (
        f"#html.frame(block(width: 300pt, height: {height}pt, {{\n" + "\n".join(places) + "\n}))\n"
    )


@pytest.fixture
def page(typst: TypstRunner, open_page):
    """The frame of every pair, opened."""
    return open_page(typst.html(document(body(PAIRS), CSS), name="paths.html"))


# The `d` of the path below each label.
PATHS = """(names) => Object.fromEntries(names.map((name) => [
    name,
    document.querySelector(`[data-typst-label="${name}"] path`).getAttribute("d"),
]))"""

# The first path animated from its own `d` to that of the second, paused at each moment, with
# the computed `d` and the box `getBBox()` gives.
SAMPLE = """([name, duration, moments]) => {
    const [a, b] = [0, 1].map((side) =>
        document.querySelector(`[data-typst-label="${name}-${side}"] path`));
    const animation = a.animate(
        [{d: `path("${a.getAttribute("d")}")`}, {d: `path("${b.getAttribute("d")}")`}],
        {duration, easing: "linear"},
    );
    animation.pause();
    const found = moments.map((moment) => {
        animation.currentTime = duration * moment;
        const box = a.getBBox();
        return {d: getComputedStyle(a).d, box: [box.x, box.y, box.width, box.height]};
    });
    animation.cancel();
    return found;
}"""


def numbers(d: str) -> list[float]:
    """The numbers of a path, in order."""
    return [float(value) for value in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)]


def commands(d: str) -> str:
    """The command letters of a path, in order, from its data or from a CSS `path()`."""
    data = re.sub(r'^path\("(.*)"\)$', r"\1", d)
    return "".join(re.findall(r"[MmZzLlHhVvCcSsQqTtAa]", data))


def supported(page) -> bool:
    """Whether the engine says it supports the CSS `d` property."""
    return page.evaluate("""() => CSS.supports("d", 'path("M 0 0")')""")


def test_typst_writes_one_structure_per_pair(page):
    """The pairs of one structure have the same commands, and the last pair does not.

    The sharp rectangle runs `v h v Z` from its corner, and the rounded one starts on its left
    side with a `m` and alternates curves and lines in the other direction.
    """
    found = page.evaluate(PATHS, [f"{name}-{side}" for name in PAIRS for side in (0, 1)])
    for name in PAIRS:
        a, b = commands(found[f"{name}-0"]), commands(found[f"{name}-1"])
        assert (a == b) == (name != "sharp-rounded"), f"{name}: {a} against {b}"
        assert found[f"{name}-0"].startswith("M 0 0")


def test_chromium_and_firefox_animate_d_and_webkit_does_not(page, browser_name):
    """Webkit 26.5 neither supports `d` in CSS nor computes it, and animating it is no error."""
    assert supported(page) == (browser_name != "webkit")
    if browser_name == "webkit":
        sample = page.evaluate(SAMPLE, ["rect", DURATION, [0.5]])
        assert sample[0]["d"] is None
        assert sample[0]["box"][2:] == pytest.approx([20, 10])


@pytest.mark.parametrize("name", ["rect", "rounded", "ellipse", "line"])
def test_relative_commands_interpolate_number_by_number(page, name):
    """At a quarter of the step every number of the computed path is a quarter of the way.

    Both engines compute the absolute form, so the relative numbers are summed first.
    For the rounded rectangle the second pair is the start of its left side, `0 r`, so the
    radius is a quarter of the way from 2 to 8 as well, which is what a corner that keeps its
    shape needs.
    """
    if not supported(page):
        pytest.skip("the engine does not animate d")
    paths = page.evaluate(PATHS, [f"{name}-0", f"{name}-1"])
    a, b = (absolute(paths[f"{name}-{side}"]) for side in (0, 1))
    [sample] = page.evaluate(SAMPLE, [name, DURATION, [0.25]])
    expected = [x + (y - x) / 4 for x, y in zip(a, b, strict=True)]
    assert numbers(sample["d"]) == pytest.approx(expected, abs=1e-3)
    if name == "rounded":
        assert expected[3] == pytest.approx(3.5)


def test_different_commands_flip_halfway(page):
    """A pair whose commands differ shows the first path until the middle and then the second."""
    if not supported(page):
        pytest.skip("the engine does not animate d")
    paths = page.evaluate(PATHS, ["sharp-rounded-0", "sharp-rounded-1"])
    before, after = page.evaluate(SAMPLE, ["sharp-rounded", DURATION, [0.49, 0.51]])
    assert commands(before["d"]).upper() == commands(paths["sharp-rounded-0"]).upper()
    assert commands(after["d"]).upper() == commands(paths["sharp-rounded-1"]).upper()


def test_get_bbox_follows_the_animated_d(page):
    """The box of the rectangle at its midpoint is halfway between the two boxes at rest."""
    if not supported(page):
        pytest.skip("the engine does not animate d")
    [sample] = page.evaluate(SAMPLE, ["rect", DURATION, [0.5]])
    assert sample["box"] == pytest.approx([0, 0, 30, 20], abs=1e-3)


def absolute(d: str) -> list[float]:
    """The numbers of one of typst's relative paths in the absolute form an engine computes.

    Only the commands typst writes are handled: `M`, `m`, `h`, `v`, `l`, `c` and `Z`.
    """
    found = []
    x = y = 0.0
    tokens = re.findall(r"[MmZzHhVvLlCc]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)
    index = 0
    while index < len(tokens):
        command = tokens[index]
        index += 1
        take = {"M": 2, "m": 2, "h": 1, "v": 1, "l": 2, "c": 6, "Z": 0, "z": 0}[command]
        values = [float(value) for value in tokens[index : index + take]]
        index += take
        if command == "M":
            x, y = values
            found += [x, y]
        elif command in "ml":
            x, y = x + values[0], y + values[1]
            found += [x, y]
        elif command == "h":
            x += values[0]
            found.append(x)
        elif command == "v":
            y += values[0]
            found.append(y)
        elif command == "c":
            found += [x + values[0], y + values[1], x + values[2], y + values[3]]
            x, y = x + values[4], y + values[5]
            found += [x, y]
    return found


# Both copies resize from the outgoing geometry to the incoming one and travel from the place
# of the outgoing to that of the incoming, as a resize moves them, while their renderings
# crossfade, paused at one fraction of the step.
RESIZE = """([duration, fraction]) => {
    const [r0, r1] = ["rounded-0", "rounded-1"].map((label) =>
        document.querySelector(`[data-typst-label="${label}"]`));
    const [e0, e1] = [r0, r1].map((rendering) => rendering.querySelector("path"));
    const origin = (element) => new DOMPoint(0, 0).matrixTransform(element.getScreenCTM());
    const inParent = (element, x, y) => new DOMPoint(x, y, 0, 0)
        .matrixTransform(element.parentNode.getScreenCTM().inverse());
    const start = origin(e0), end = origin(e1);
    const out = inParent(e0, end.x - start.x, end.y - start.y);
    const back = inParent(e1, start.x - end.x, start.y - end.y);
    const shapes = [e0, e1].map((element) => `path("${element.getAttribute("d")}")`);
    const timing = {duration, easing: "linear", fill: "both"};
    e0.animate([
        {translate: "0px 0px", d: shapes[0]},
        {translate: `${out.x}px ${out.y}px`, d: shapes[1]},
    ], timing);
    e1.animate([
        {translate: `${back.x}px ${back.y}px`, d: shapes[0]},
        {translate: "0px 0px", d: shapes[1]},
    ], timing);
    r0.animate([{opacity: 1}, {opacity: 0}], timing);
    r1.animate([{opacity: 0}, {opacity: 1}], timing);
    for (const animation of document.getAnimations()) {
        animation.pause();
        animation.currentTime = duration * fraction;
    }
    window.probe = {r0, r1, e0, e1};
    const boxes = [e0, e1].map((element) => element.getBoundingClientRect());
    const left = Math.min(start.x, end.x) - 4, top = Math.min(start.y, end.y) - 4;
    const right = Math.max(...boxes.map((box) => box.right)) + 4;
    const bottom = Math.max(...boxes.map((box) => box.bottom)) + 4;
    return {x: left, y: top, width: right - left, height: bottom - top};
}"""

# One opaque incoming copy with the geometry and the place the resize shows, written as inline
# style, with an opacity animation held at one on its rendering for the reason
# `test_morph_sum.py` gives.
STILL = """(duration) => {
    const {r0, r1, e1} = window.probe;
    const shown = getComputedStyle(e1);
    const d = shown.d, translate = shown.translate;
    for (const animation of document.getAnimations()) {
        animation.cancel();
    }
    r0.style.visibility = "hidden";
    e1.style.d = d;
    e1.style.translate = translate;
    const hold = r1.animate([{opacity: 1}, {opacity: 1}], {duration, fill: "both"});
    hold.pause();
    hold.currentTime = duration / 2;
}"""


def test_two_copies_that_resize_together_sum_to_one(page):
    """The two copies have one geometry at every moment, so the sum is one rounded rectangle."""
    if not supported(page):
        pytest.skip("the engine does not animate d")
    clip = page.evaluate(RESIZE, [DURATION, 0.5])
    resized = screenshot(page, animations="allow", clip=clip)
    page.evaluate(STILL, DURATION)
    reference = screenshot(page, animations="allow", clip=clip)
    largest, pixels, ink = deviation(reference, resized)
    assert ink > 300, "the shape is not in the compared box"
    assert largest <= 2, f"the midpoint differs by {largest}/255"
    assert pixels == 0, f"{pixels} of {ink} ink pixels differ by more than 2/255"
