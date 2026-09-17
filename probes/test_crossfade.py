# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Crossfading epoch frames*.

Two epoch frames stacked in one grid cell, at the midpoint of a transition,
compared against the single frame at full opacity.
A plain opacity crossfade washes the whole slide out; `mix-blend-mode: plus-lighter` does not.

What is probed here is the *whole-frame* crossfade, which is what the finding measured.
The region-scoped variant that *Architecture* prescribes is still an open question,
and this is its verified fallback.
"""

import pytest
from harness import (
    Box,
    PagedRunner,
    TypstRunner,
    assert_differs,
    assert_identical_outside,
    difference_report,
    screenshot,
)
from htmldoc import stacked
from measuring import rects

# Two epochs whose content differs only inside a region of fixed footprint,
# so that everything outside it is pixel-identical between the frames by construction.
EPOCHS = ("A short claim.", "A different claim, of a different length.")

REGION_HEIGHT = "24pt"


def frame(text: str) -> str:
    """One epoch frame: a stable line, a fixed-footprint region, and a stable line."""
    return f"""
  #box(width: 240pt)[
    #block[Stable line above the region.]
    #box(width: 240pt, height: {REGION_HEIGHT})[{text}]#label("region")
    #block[Stable line below the region.]
  ]
"""


PLAIN = """\
.stack > *:nth-child(1) { opacity: 0.5; }
.stack > *:nth-child(2) { opacity: 0.5; }
"""

LIGHTER = (
    PLAIN
    + """\
.stack > * { mix-blend-mode: plus-lighter; }
"""
)

ONLY_FIRST = """\
.stack > *:nth-child(2) { opacity: 0; }
"""


def shot(typst: TypstRunner, open_page, css: str, name: str):
    """Render the stacked frames under the given rules and return the page and its pixels."""
    path = typst.html(stacked([frame(text) for text in EPOCHS], css), name=name)
    page = open_page(path)
    return page, screenshot(page)


def region_band(page) -> Box:
    """The rows of the screenshot the region covers, as a full-width band.

    It is read off the rendered label rather than assumed,
    so the probe keeps meaning what it says if the layout changes.
    """
    found = rects(page, '[data-typst-label="region"]')
    assert len(found) == 2, f"expected one region per frame, found {len(found)}"
    width = page.viewport_size["width"]
    top = max(0, int(min(r.y for r in found)))
    bottom = int(max(r.y + r.height for r in found)) + 1
    return Box(0, top, width, bottom)


def test_the_two_epochs_differ_only_inside_the_region(typst: TypstRunner, open_page):
    """Without this, both crossfade probes below would be comparing an image with itself."""
    page, only_first = shot(typst, open_page, ONLY_FIRST, "first.html")
    band = region_band(page)
    _, only_second = shot(
        typst, open_page, ".stack > *:nth-child(1) { opacity: 0; }\n", "second.html"
    )
    assert_identical_outside(only_first, only_second, band, what="the two epoch frames")
    assert_differs(
        only_first[band.y0 : band.y1],
        only_second[band.y0 : band.y1],
        what="the region band of the two epoch frames",
    )


def test_a_plain_opacity_crossfade_washes_out_the_whole_slide(typst: TypstRunner, open_page):
    """The reason `plus-lighter` is not a nicety.

    Two identical layers at half opacity do not add up to one opaque layer:
    black text over white comes out at about a quarter grey at the midpoint.
    """
    page, reference = shot(typst, open_page, ONLY_FIRST, "reference.html")
    band = region_band(page)
    _, plain = shot(typst, open_page, PLAIN, "plain.html")
    outside = slice(band.y1, None)
    report = difference_report(reference[outside], plain[outside])
    assert "identical" not in report, f"the plain crossfade did not wash anything out: {report}"
    deviation = int(
        abs(reference[outside].astype(int) - plain[outside].astype(int)).max(),
    )
    assert deviation > 32, f"expected a visible wash-out, measured {deviation}/255"


# How far the blended midpoint may sit from the single frame, per engine, as a deviation
# out of 255 and a count of pixels allowed to exceed one.
#
# Exact is the claim, and all three engines meet it bit for bit with the frame isolating, as
# `STACK_CSS` writes it: two layers at half opacity add back to one opaque layer.
# Playwright's webkit 26.5 drifted by up to 42 out of 255 on ten antialiased glyph edges
# while the isolation sat on the stack instead, which is the subject of the reach probe at
# the end of this module.
MIDPOINT = {"chromium": (1, 0), "firefox": (1, 0), "webkit": (2, 2)}


def test_plus_lighter_keeps_the_midpoint_exact(typst: TypstRunner, open_page, browser_name):
    """With `plus-lighter` the sum is exact, so nothing outside the region dips.

    This is what makes the containment claim true *during* the transition
    and not only at its endpoints.
    """
    page, reference = shot(typst, open_page, ONLY_FIRST, "reference2.html")
    band = region_band(page)
    _, blended = shot(typst, open_page, LIGHTER, "lighter.html")
    outside = slice(band.y1, None)
    difference = abs(reference[outside].astype(int) - blended[outside].astype(int))
    allowed_deviation, allowed_pixels = MIDPOINT[browser_name]
    report = difference_report(reference[outside], blended[outside], tol=1)
    assert int(difference.max()) <= allowed_deviation, (
        f"the blended midpoint drifted from the single frame: {report}"
    )
    assert int((difference > 1).any(axis=2).sum()) <= allowed_pixels, (
        f"more of the slide dipped than this engine was measured to: {report}"
    )


def test_the_same_two_epochs_agree_on_paper(typst: TypstRunner, paged: PagedRunner):
    """The paged half of the same invariant, which needs no browser at all.

    The two epochs are laid out on two pages; everything outside the region band
    has to come out pixel-identical.
    """
    body = "#set page(width: 280pt, height: 160pt, margin: 20pt)\n" + "#pagebreak()\n".join(
        f"#box(width: 240pt)[\n"
        f"  #block[Stable line above the region.]\n"
        f"  #box(width: 240pt, height: {REGION_HEIGHT})[{text}]\n"
        f"  #block[Stable line below the region.]\n"
        f"]\n"
        for text in EPOCHS
    )
    pages = paged.png(body)
    assert len(pages) == 2
    # The band is generous on purpose: it is the region's footprint plus a line of slack,
    # and the assertion that matters is that everything below it is untouched.
    band = Box(0, 0, pages[0].shape[1], 70)
    assert_identical_outside(pages[0], pages[1], band, what="the two epochs on paper")


# Where the blend sits: on the region's group, or on the frame that holds it.
#
# *Architecture* scopes the crossfade to the region, so the two halves that have to add up
# are two `<g data-typst-label="region">` elements in two *different* inline SVGs.
# The two probes below differ only in which element carries `mix-blend-mode`, and both are
# given two frames of identical content, which makes the question sharp: two half-opacity
# copies of the same ink add back to exactly that ink when the blend reaches across the
# frames, and wash out when it does not.

SAME = (EPOCHS[0], EPOCHS[0])

# The blend on the region's own group, which is what *Architecture* asks for.
ON_GROUPS = """\
.stack > * [data-typst-label="region"] {
  opacity: 0.5;
  mix-blend-mode: plus-lighter;
}
"""

# The blend on the frames, with the outgoing frame scoped down to the region by visibility.
# `visibility` rather than `opacity` or `display`: a descendant can take it back, while the
# frame stays laid out and makes no stacking context of its own.
ON_FRAMES = """\
.stack > * { mix-blend-mode: plus-lighter; }
.stack > *:nth-child(2) { visibility: hidden; }
.stack > *:nth-child(2) [data-typst-label="region"] { visibility: visible; }
.stack > * [data-typst-label="region"] { opacity: 0.5; }
"""


# Two groups at the same place in one frame, which is the control's overlap.
OVERLAID = """
  #box(width: 240pt, height: 24pt)[
    #place(top + left)[#box[A short claim.]#label("a")]
    #place(top + left)[#box[A short claim.]#label("b")]
  ]
"""

WITHIN = """\
.stack > * [data-typst-label="a"], .stack > * [data-typst-label="b"] {
  opacity: 0.5;
  mix-blend-mode: plus-lighter;
}
"""

WITHIN_ONE = """\
.stack > * [data-typst-label="b"] { opacity: 0; }
"""


def twice(typst: TypstRunner, open_page, css: str, name: str):
    """Render two frames of identical content under the given rules."""
    path = typst.html(stacked([frame(text) for text in SAME], css), name=name)
    page = open_page(path)
    return page, screenshot(page)


# How far a blended result may sit from the single opaque copy it has to come back to,
# per engine, as a deviation out of 255 and a count of pixels allowed to exceed one.
#
# Measured in chromium 151 and firefox 153 on 2026-09-15, and in playwright's webkit 26.5
# on 2026-09-17, with the frame isolating as `STACK_CSS` writes it. What webkit does without
# that rule is the subject of the reach probe at the end of this module.
EXACT = {"chromium": (1, 0), "firefox": (2, 2), "webkit": (2, 2)}


def deviation(reference, image) -> tuple[int, int]:
    """How far two images sit apart, as a maximum out of 255 and a count of pixels."""
    difference = abs(reference.astype(int) - image.astype(int))
    return int(difference.max()), int((difference > 1).any(axis=2).sum())


def test_a_group_blends_with_ink_in_its_own_frame(typst: TypstRunner, open_page, browser_name):
    """Two half-opacity groups over each other in one frame add back to one opaque copy.

    This is the control for the probe below: `plus-lighter` on a `<g>` is not inert,
    and what the next probe measures is the reach of the blend and not the blend itself.
    """
    shots = {}
    for what, css in (("blended", WITHIN), ("one", WITHIN_ONE)):
        path = typst.html(stacked([OVERLAID], css), name=f"within-{what}.html")
        shots[what] = screenshot(open_page(path))
    measured, pixels = deviation(shots["one"], shots["blended"])
    allowed_deviation, allowed_pixels = EXACT[browser_name]
    assert measured <= allowed_deviation, (
        f"a group did not blend with ink beside it in the same frame: {measured}/255"
    )
    assert pixels <= allowed_pixels, f"{pixels} pixels dipped inside one frame"


def test_a_group_does_not_blend_with_ink_in_another_frame(typst: TypstRunner, open_page):
    """Why the crossfade is not scoped to a region's own group.

    Two frames of identical content, each with its region group at half opacity and
    `mix-blend-mode: plus-lighter` on the group: if the blend reached across the frames,
    the two halves would add back to the one opaque copy the control renders.
    They do not. The result is the plain opacity crossfade, washed out by the same amount
    as the probe above measures without any blend at all.

    This is the measurement the design was decided on, when a slide was one frame per
    epoch. It is recorded as what it is and not as a rule about where a backdrop stops:
    the probe below measures a handwritten stack where chromium 151 does add the frame
    below, so the boundary is not the inline SVG in every engine or every structure.
    Both engines agree here, which is why this is asserted for every engine rather than
    tabulated per engine: an engine that starts blending across the frames reopens a design
    decision and should say so by failing.
    """
    _, one_copy = twice(typst, open_page, ONLY_FIRST, "one-copy.html")
    _, on_groups = twice(typst, open_page, ON_GROUPS, "on-groups.html")
    measured, _ = deviation(one_copy, on_groups)
    assert measured > 32, (
        f"the group-scoped blend reached across the frames after all: {measured}/255"
    )


# The two shapes the scoped crossfade has been built on, and what each engine does with
# them. A slide holds one frame with a rendering per epoch, so the renderings are the groups
# the blend sits on; it held one frame per epoch before that, and the earlier shape is kept
# here because the engines do not answer the two alike.
SUMS = "the two halves add back to one opaque copy"
WASHES = "the two halves stay at half, which is a plain crossfade"
SHAPES = {
    "the frames": {"chromium": SUMS, "firefox": SUMS, "webkit": WASHES},
    "the epoch renderings of one frame": {"chromium": SUMS, "firefox": SUMS, "webkit": SUMS},
}

# How far a summed result may sit from the single opaque copy, per engine, where the answer
# above is `SUMS`.
#
# Webkit 26.5 rasterises a blended group into a buffer whose bounds it rounds, and the bottom
# row of the region comes back white where the single copy has the antialiasing of the glyphs
# below their baseline: 95 pixels along that one row, by up to 128/255.
# The halves are summed, and the pixel count is what says so: a wash-out moves the glyph cores
# across the whole band, which is what this probe measures on the frames shape, where webkit
# moves 473 pixels over twelve rows instead of 95 over one.
SUMMED = {"chromium": (1, 0), "firefox": (2, 2), "webkit": (128, 128)}


def rendering(index: int, text: str) -> str:
    """One epoch rendering, placed at the frame's origin as the others are."""
    return f'#place(top + left)[{frame(text)}#label("rendering-{index}")]'


def merged(texts: tuple[str, ...]) -> str:
    """One frame holding a rendering per epoch, which is the shape a slide has."""
    inner = "\n".join(rendering(index, text) for index, text in enumerate(texts))
    return f"\n  #box(width: 240pt, height: 96pt)[\n{inner}\n  ]\n"


# The blend on the epoch renderings, with the outgoing one scoped down to the region by
# visibility, which is the rule animo's stylesheet writes.
ON_RENDERINGS = """\
[data-typst-label="rendering-1"] { visibility: hidden; }
[data-typst-label="rendering-1"] [data-typst-label="region"] { visibility: visible; }
[data-typst-label^="rendering-"] { mix-blend-mode: plus-lighter; }
[data-typst-label^="rendering-"] [data-typst-label="region"] { opacity: 0.5; }
"""

# The same document with the outgoing rendering taken away entirely, which is the one
# opaque copy the crossfade has to come back to.
ONE_RENDERING = '[data-typst-label="rendering-1"] { visibility: hidden; }\n'


@pytest.mark.parametrize("shape", list(SHAPES))
def test_whether_a_scoped_blend_sums_depends_on_the_shape_and_the_engine(
    typst: TypstRunner, open_page, browser_name, shape
):
    """What animo does instead, and the reason it is a crossfade at all.

    The blend goes where it reaches, and the outgoing side is scoped down to the region it
    hands over by `visibility`, which a descendant can take back. The two halves of the
    region then add back to one opaque copy, and outside the region the outgoing side paints
    nothing whatsoever.

    Which element carries the blend decides whether webkit 26.5 sums the halves at all.
    On the epoch renderings of one frame, which is what a slide holds, all three engines sum
    them. On one frame per epoch, which is the shape a slide had before, webkit leaves the
    glyph cores of the whole region at half, which is the plain opacity crossfade. So the
    merged frame is what makes the crossfade work in webkit, and a blend on the frames is not
    a fallback it could return to. Measured on 2026-09-17.
    """
    if shape == "the frames":
        _, reference = twice(typst, open_page, ONLY_FIRST, "one-copy2.html")
        _, blended = twice(typst, open_page, ON_FRAMES, "on-frames.html")
    else:
        source = merged(SAME)
        reference = screenshot(
            open_page(typst.html(stacked([source], ONE_RENDERING), name="one-rendering.html"))
        )
        blended = screenshot(
            open_page(typst.html(stacked([source], ON_RENDERINGS), name="on-renderings.html"))
        )
    measured, pixels = deviation(reference, blended)
    if SHAPES[shape][browser_name] == WASHES:
        assert measured > 32, (
            f"{browser_name} summed the halves on {shape} after all: {measured}/255"
        )
        return
    allowed_deviation, allowed_pixels = SUMMED[browser_name]
    assert measured <= allowed_deviation, (
        f"the scoped crossfade on {shape} drifted from the single copy: {measured}/255"
    )
    assert pixels <= allowed_pixels, f"{pixels} pixels dipped during the crossfade"


# How far a group's blend reaches past its own frame, which is not the same in every engine
# and is why the frame isolates instead of the containment being inherited.
#
# The probe above answers it for typst's own output, where chromium and firefox contain the
# blend. These answer it for a handwritten stack of the same shape, where the three engines
# do not agree: the mark is dark red over dark green, so a blend that reaches the green comes
# back with green in it and one that does not stays pure red.
#
# The frame's own isolation is taken off for these, because the question is where a blend
# stops when no frame confines it, and `STACK_CSS` writes the rule that confines it.
MARK = '#box(width: 120pt, height: 60pt, fill: rgb("#400000"))[]#label("mark")'
UNDER = '#box(width: 120pt, height: 60pt, fill: rgb("#004000"))[]'

OPEN_FRAME = ".stack > * { isolation: auto; }\n"
BLEND_ON_MARK = '.stack > * [data-typst-label="mark"] { mix-blend-mode: plus-lighter; }\n'
BLENDED = OPEN_FRAME + BLEND_ON_MARK
ON_GROUND = ".stack { background: #004000; }\n" + BLENDED
ON_PAGE = "body { background: #004000; }\n" + BLENDED
ON_PAGE_WITHOUT_ISOLATION = ".stack { isolation: auto; }\n" + ON_PAGE

# What each engine was measured to do, as the pixel under the mark.
# Dark red alone means the blend stopped before whatever was put under the mark's own frame;
# red plus green means that ground was summed into it.
CONTAINED = (0x40, 0x00, 0x00)
REACHED = (0x40, 0x40, 0x00)

# The ground under the mark's own frame, and what each engine does with it.
# The last row is the control for the one above it: with the isolation taken off the stack,
# chromium reaches the page, which is what says its answer in the third row is the isolation
# working rather than a boundary it would have stopped at anyway.
REACH = {
    "the element the svg is painted on": {
        "chromium": REACHED,
        "firefox": CONTAINED,
        "webkit": REACHED,
    },
    "an svg below it": {
        "chromium": REACHED,
        "firefox": CONTAINED,
        "webkit": REACHED,
    },
    "the page, behind the element that isolates": {
        "chromium": CONTAINED,
        "firefox": CONTAINED,
        "webkit": REACHED,
    },
    "the same page, with isolation auto": {
        "chromium": REACHED,
        "firefox": CONTAINED,
        "webkit": REACHED,
    },
}


def reach_source(under: str) -> str:
    """The handwritten stack for one row of `REACH`."""
    if under == "an svg below it":
        return stacked([UNDER, MARK], BLENDED)
    if under == "the page, behind the element that isolates":
        return stacked([MARK], ON_PAGE)
    if under == "the same page, with isolation auto":
        return stacked([MARK], ON_PAGE_WITHOUT_ISOLATION)
    return stacked([MARK], ON_GROUND)


@pytest.mark.parametrize("under", list(REACH))
def test_how_far_a_groups_blend_reaches_past_its_frame_differs_by_engine(
    typst: TypstRunner, open_page, browser_name, under
):
    """Why the frame isolates, now that the blend sits on the epoch renderings.

    Firefox 153 stops a group's blend at the root of the inline SVG, whatever is under it.
    Chromium 151 sums both the ground and a frame below into it, and stops at the element
    that carries `isolation: isolate`.
    Playwright's webkit 26.5 stops at none of the three: a group's blend reaches the page
    behind the isolating element, and taking that isolation off changes nothing there.

    So an isolating ancestor written in HTML does not confine a blend that sits on a group
    inside an inline SVG in every engine, and the probe below says where one that does
    belongs. Measured on 2026-09-15, and on 2026-09-17 for webkit.
    """
    name = f"reach-{under.replace(' ', '-')}.html"
    source = reach_source(under)
    pixel = tuple(
        int(value) for value in screenshot(open_page(typst.html(source, name=name)))[10, 10]
    )
    assert pixel == REACH[under][browser_name], (
        f"{browser_name} changed how far a group's blend reaches past {under}"
    )


def test_isolating_the_frame_confines_a_groups_blend_in_every_engine(
    typst: TypstRunner, open_page
):
    """Where the isolation has to sit for the containment to hold in all three engines.

    The probe above measures a blend on a group escaping to the page in webkit 26.5, past an
    ancestor that isolates. The inline SVG that holds the group is the one element that
    confines it in chromium 151, firefox 153 and webkit 26.5 alike, which is why animo writes
    `isolation: isolate` on the epoch frame and why `STACK_CSS` carries the same rule.
    The green is on the page, which the probe above reaches in webkit without this rule.
    Measured on 2026-09-17.
    """
    source = stacked([MARK], "body { background: #004000; }\n" + BLEND_ON_MARK)
    pixel = tuple(
        int(value)
        for value in screenshot(open_page(typst.html(source, name="reach-frame.html")))[10, 10]
    )
    assert pixel == CONTAINED, f"the blend escaped the frame that isolates it: {pixel}"
