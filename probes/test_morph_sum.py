# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A morph keeps the `plus-lighter` sum*.

Two renderings of one frame stand for two epochs of a region: `Hello world`, and
`Oh, Hello world`, which shifts the ten letters the two share. They are summed under
`plus-lighter`, as a crossfade sums them. A morph translates the outgoing copy of each shared
letter from its own place to the place of the incoming copy, and the incoming copy from the
outgoing place to its own, while the outgoing rendering fades out and the incoming one in.
The claim is that the two copies then sum to one opaque letter on the route.

The letters are paired here by a longest common subsequence of the glyphs they show, which is
what a morph does, and nothing else of animo is involved.
The letters the two renderings do not share are hidden in every raster, so the comparison is
about the pairs alone.
"""

import numpy as np
import pytest
from harness import TypstRunner, screenshot
from htmldoc import document

# The two renderings, placed at one point of one frame, each a labelled group.
# The frame isolates, which is where animo states the containment of the blend.
BODY = """\
#html.frame(block(width: 320pt, height: 60pt, {
  set text(size: 30pt)
  place(top + left, [#box(width: 320pt, height: 60pt, pad(10pt)[Hello world])#label("r0")])
  place(top + left, [#box(width: 320pt, height: 60pt, pad(10pt)[Oh, Hello world])#label("r1")])
}))
"""

CSS = """\
body { margin: 0; background: #ffffff; }
svg { isolation: isolate; }
[data-typst-label="r0"], [data-typst-label="r1"] { mix-blend-mode: plus-lighter; }
"""

# How long the probed step lasts, in milliseconds.
DURATION = 400

# Pair the letters, hide the ones that are not paired, and compute each copy's route as a
# `translate` in the user space of its parent, which for a letter is a run typst flipped
# with `matrix(1 0 0 -1 ..)`.
SETUP = """() => {
    const [r0, r1] = ["r0", "r1"].map((label) =>
        document.querySelector(`[data-typst-label="${label}"]`));
    const u0 = [...r0.querySelectorAll("use")];
    const u1 = [...r1.querySelectorAll("use")];
    const a = u0.map((use) => use.href.baseVal);
    const b = u1.map((use) => use.href.baseVal);
    const table = Array.from({length: a.length + 1}, () => new Array(b.length + 1).fill(0));
    for (let i = a.length - 1; i >= 0; i--) {
        for (let j = b.length - 1; j >= 0; j--) {
            table[i][j] = a[i] === b[j]
                ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
        }
    }
    const pairs = [];
    for (let i = 0, j = 0; i < a.length && j < b.length;) {
        if (a[i] === b[j]) { pairs.push([i, j]); i++; j++; }
        else if (table[i + 1][j] >= table[i][j + 1]) i++; else j++;
    }
    const origin = (use) => new DOMPoint(use.x.baseVal.value, use.y.baseVal.value)
        .matrixTransform(use.getScreenCTM());
    const inParent = (use, x, y) => new DOMPoint(x, y, 0, 0)
        .matrixTransform(use.parentNode.getScreenCTM().inverse());
    const moves = pairs.map(([i, j]) => {
        const start = origin(u0[i]);
        const end = origin(u1[j]);
        const dx = end.x - start.x, dy = end.y - start.y;
        return {i, j, out: inParent(u0[i], dx, dy), back: inParent(u1[j], -dx, -dy), dx, dy};
    });
    const paired0 = new Set(pairs.map(([i]) => i)), paired1 = new Set(pairs.map(([, j]) => j));
    u0.forEach((use, k) => { if (!paired0.has(k)) use.style.visibility = "hidden"; });
    u1.forEach((use, k) => { if (!paired1.has(k)) use.style.visibility = "hidden"; });
    window.probe = {r0, r1, u0, u1, moves};
    return {glyphs: [a.length, b.length], paired: pairs.length, shift: moves[0].dx};
}"""

# The morph at one fraction of the step: both copies moving, both renderings fading, all of
# it paused at that moment.
MORPH = """([duration, fraction]) => {
    const {r0, r1, u0, u1, moves} = window.probe;
    const timing = {duration, easing: "linear", fill: "both"};
    for (const {i, j, out, back} of moves) {
        u0[i].animate([{translate: "0px 0px"}, {translate: `${out.x}px ${out.y}px`}], timing);
        u1[j].animate([{translate: `${back.x}px ${back.y}px`}, {translate: "0px 0px"}], timing);
    }
    r0.animate([{opacity: 1}, {opacity: 0}], timing);
    r1.animate([{opacity: 0}, {opacity: 1}], timing);
    for (const animation of document.getAnimations()) {
        animation.pause();
        animation.currentTime = duration * fraction;
    }
}"""

# What the morph has to look like at that fraction: the outgoing rendering hidden and the
# incoming one opaque, with its letters where the route puts them, and an opacity animation
# held at one on it, because chromium rasterises a group differently while one runs (see
# *Findings*).
REFERENCE = """([duration, fraction]) => {
    const {r0, r1, u0, u1, moves} = window.probe;
    for (const animation of document.getAnimations()) {
        animation.cancel();
    }
    r0.style.visibility = "hidden";
    for (const {j, back} of moves) {
        const rest = 1 - fraction;
        u1[j].style.translate = `${back.x * rest}px ${back.y * rest}px`;
    }
    const hold = r1.animate([{opacity: 1}, {opacity: 1}], {duration, fill: "both"});
    hold.pause();
    hold.currentTime = duration / 2;
}"""

# The box of the paired letters at the start of the route, with room for antialiasing.
BOX = """() => {
    const {u0, moves} = window.probe;
    const boxes = moves.map(({i}) => u0[i].getBoundingClientRect());
    const left = Math.min(...boxes.map((box) => box.left)) - 4;
    const right = Math.max(...boxes.map((box) => box.right)) + 4;
    const top = Math.min(...boxes.map((box) => box.top)) - 4;
    const bottom = Math.max(...boxes.map((box) => box.bottom)) + 4;
    return {x: Math.max(0, left), y: Math.max(0, top), width: right - left, height: bottom - top};
}"""


def opened(typst: TypstRunner, open_page, name: str):
    """The two renderings in a page, with the letters paired."""
    page = open_page(typst.html(document(BODY, CSS), name=name))
    found = page.evaluate(SETUP)
    assert found["paired"] == 10, f"expected the ten letters of Hello world, got {found}"
    return page


def deviation(reference: np.ndarray, image: np.ndarray) -> tuple[int, int, int]:
    """The largest difference out of 255, the pixels above 2/255, and the ink pixels."""
    difference = abs(reference.astype(int) - image.astype(int)).max(axis=2)
    ink = int((reference.min(axis=2) < 200).sum())
    return int(difference.max()), int((difference > 2).sum()), ink


def morphed(page, fraction: float) -> tuple[int, int, int]:
    """How far the morph at one fraction of the step is from one opaque copy on the route."""
    page.evaluate(MORPH, [DURATION, fraction])
    clip = page.evaluate(BOX)
    morph = screenshot(page, animations="allow", clip=clip)
    page.evaluate(REFERENCE, [DURATION, fraction])
    reference = screenshot(page, animations="allow", clip=clip)
    return deviation(reference, morph)


# How far the midpoint of the morph may sit from one opaque copy, per engine, as a largest
# difference out of 255 and a number of pixels above 2/255. Chromium sums the copies to
# within rounding. Firefox carries the difference the next probe measures, halved, because
# at the midpoint each copy has half the weight. Webkit differs on the antialiased corners of
# a stem while the copies move, on a dozen pixels.
MIDPOINT = {"chromium": (2, 0), "firefox": (16, 600), "webkit": (96, 24)}


def test_the_two_copies_of_a_morph_sum_to_one(typst: TypstRunner, open_page, browser_name):
    """The claim: no change of the blend, no clone and no opacity of the morph's own."""
    page = opened(typst, open_page, "midpoint.html")
    largest, pixels, ink = morphed(page, 0.5)
    allowed_largest, allowed_pixels = MIDPOINT[browser_name]
    assert ink > 1000, "the paired letters are not in the compared box"
    assert largest <= allowed_largest, f"the midpoint differs by {largest}/255"
    assert pixels <= allowed_pixels, f"{pixels} of {ink} ink pixels differ by more than 2/255"


def test_a_plain_opacity_crossfade_of_the_two_copies_dips(typst: TypstRunner, open_page):
    """Why the comparison above is not vacuous: without `plus-lighter` the pair washes out."""
    page = opened(typst, open_page, "plain.html")
    # Important, because the page's own rule comes later in the document than one added here.
    page.add_style_tag(content='[data-typst-label^="r"] { mix-blend-mode: normal !important; }')
    largest, _, _ = morphed(page, 0.5)
    assert largest > 32, f"the plain crossfade of the pair did not dip: {largest}/255"


# Firefox's difference, with no animation and no blend at all: one letter at one place on the
# screen, reached through its own `x` attribute or through a `translate`.
STATIC = """(which) => {
    const {r0, r1, u0, u1, moves} = window.probe;
    for (const rendering of [r0, r1]) {
        rendering.style.visibility = "hidden";
    }
    for (const {i, j, back} of moves) {
        u0[i].style.visibility = which === "attribute" ? "visible" : "hidden";
        u1[j].style.visibility = which === "translate" ? "visible" : "hidden";
        u1[j].style.translate = `${back.x}px ${back.y}px`;
    }
}"""

# How far the two may differ, per engine, as for `MIDPOINT`.
# Firefox is the engine the entry is about, and it is asserted to differ as well.
# Chromium 151 draws the two alike on some loads of the page and differs by 50/255 on a dozen
# pixels on others, which is not the difference this probe is about.
DECOMPOSED = {"chromium": (64, 24), "firefox": (32, 800), "webkit": (2, 0)}


def test_firefox_draws_a_letter_by_how_it_reached_its_place(
    typst: TypstRunner, open_page, browser_name
):
    """Why firefox's midpoint is not exact, which is not about the sum.

    The difference is there with no animation running and nothing blended, so it is how
    firefox places a glyph and not how it adds two of them.
    """
    page = opened(typst, open_page, "static.html")
    clip = page.evaluate(BOX)
    page.evaluate(STATIC, "attribute")
    attribute = screenshot(page, clip=clip)
    page.evaluate(STATIC, "translate")
    translated = screenshot(page, clip=clip)
    largest, pixels, ink = deviation(attribute, translated)
    assert ink > 1000, "the paired letters are not in the compared box"
    allowed_largest, allowed_pixels = DECOMPOSED[browser_name]
    assert largest <= allowed_largest, f"the two placements differ by {largest}/255"
    assert pixels <= allowed_pixels, f"{pixels} of {ink} ink pixels differ by more than 2/255"
    if browser_name == "firefox":
        assert largest > 2, "firefox now draws both placements alike; update *Findings*"


# Where `getScreenCTM()` puts a letter, under a `translate` written, animated, and in a
# rendering that is hidden.
CTM = """() => {
    const {r0, u0, u1} = window.probe;
    const origin = (use) => {
        const point = new DOMPoint(use.x.baseVal.value, use.y.baseVal.value)
            .matrixTransform(use.getScreenCTM());
        return [point.x, point.y];
    };
    const shift = (use) => {
        const point = new DOMPoint(20, 10, 0, 0).matrixTransform(use.parentNode.getScreenCTM());
        return [point.x, point.y];
    };
    r0.style.visibility = "hidden";
    const found = {};
    for (const [name, use] of [["shown", u1[0]], ["hidden", u0[0]]]) {
        const rest = origin(use);
        const expected = shift(use);
        use.style.translate = "20px 10px";
        const written = origin(use);
        use.style.translate = "";
        const animation = use.animate(
            [{translate: "0px 0px"}, {translate: "40px 20px"}], {duration: 1000});
        animation.pause();
        animation.currentTime = 500;
        const animated = origin(use);
        animation.cancel();
        found[name] = {rest, expected, written, animated};
    }
    return found;
}"""


@pytest.mark.parametrize("which", ["shown", "hidden"])
def test_the_screen_matrix_includes_the_elements_own_translate(
    typst: TypstRunner, open_page, which
):
    """What lets a morph read where an element is displayed, and so continue an interrupted one.

    The `translate` acts in the user space of the parent, so the expected offset on the screen
    is the parent's matrix applied to it, which typst has flipped upside down for a letter.
    """
    page = opened(typst, open_page, "ctm.html")
    found = page.evaluate(CTM)[which]
    rest, expected = found["rest"], found["expected"]
    for key in ("written", "animated"):
        moved = (found[key][0] - rest[0], found[key][1] - rest[1])
        message = f"a {key} translate moved the letter by {moved}, not by {expected}"
        assert abs(moved[0] - expected[0]) < 0.01, message
        assert abs(moved[1] - expected[1]) < 0.01, message
