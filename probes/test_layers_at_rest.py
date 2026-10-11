# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A Blended or Isolated Group at Rest*.

The renderings of an epoch stack carry `mix-blend-mode: plus-lighter`, and their container
carries `isolation: isolate`, also while no boundary is crossing.
At rest, one rendering is visible and the others are at opacity 0 and `visibility: hidden`.
Each of these properties is measured on its own against the same group drawn without it,
because a browser may draw a group with any of them through a layer of its own,
and the glyphs in a layer can come out differently from the same glyphs drawn without one.

The answer depends on where the glyphs fall on the device pixels.
One document therefore holds the same frame eight times, each with the stack at a different
fraction of a device pixel, and the probe reports the largest difference over the eight.
"""

import numpy as np
import pytest
from harness import TypstRunner
from htmldoc import document
from measuring import rects, settled_screenshot

# A paragraph rather than a word, so that some glyph edge falls on a partly covered pixel at
# every position.
TEXT = (
    "Sphinx of black quartz, judge my vow. The quick brown fox jumps over the lazy dog. "
    "Pack my box with five dozen liquor jugs. How vexingly quick daft zebras jump!"
)

# The height of a frame, a whole number of device pixels at both scales (`4/3` and `8/3`
# pixels to the point), so that each frame starts on a whole pixel and the offset of its
# stack is the only fraction.
FRAME_HEIGHT = 120

# The offsets of the stack in the eight frames, in steps of an eighth of a pixel at scale 1
# and a quarter of a pixel at scale 2.
OFFSETS = [0.09375 * step for step in range(8)]

# The sibling sits to the right of the group, so the columns of the group hold only its ink.
SIBLING_DX = 260


def frame(offset: float, sibling: bool) -> str:
    """One frame: a heading of static ink and a stack holding the group, and maybe a sibling."""
    group = f'#place(top + left)[#block(width: 230pt)[{TEXT}]#label("group")]'
    other = (
        f'#place(top + left, dx: {SIBLING_DX}pt)[#block(width: 230pt)[{TEXT}]#label("sibling")]'
        if sibling
        else ""
    )
    container = f"#box[#move(dx: 1pt)[#box(width: 500pt, height: 70pt)[{group}{other}]]]"
    return (
        f"#html.frame[#box(width: 520pt, height: {FRAME_HEIGHT}pt)["
        f"#place(top + left, dx: 10pt, dy: 6pt)[Static heading.]"
        f"#place(top + left, dx: {9 + offset}pt, dy: {30 + offset}pt)[{container}]"
        f"]]"
    )


BASE = """\
body { margin: 0; background: #ffffff; }
svg { isolation: isolate; }
"""

CONTAINER = 'g:has(> [data-typst-label="group"])'
GROUP = '[data-typst-label="group"]'
SIBLING = '[data-typst-label="sibling"]'

# Each condition, as whether the stack holds the sibling, the rules that set the condition up,
# and the condition it is compared with.
# The frame isolates in all of them, as in animo, so a blend on the group sums it with the
# transparent backdrop of the frame and nothing else.
LONE = "a lone group"
VISIBLE_SIBLING = "a visible sibling"
CONDITIONS = {
    "the container isolates": (False, f"{CONTAINER} {{ isolation: isolate; }}", LONE),
    "the group blends": (False, f"{GROUP} {{ mix-blend-mode: plus-lighter; }}", LONE),
    "both, as animo writes them": (
        False,
        f"{CONTAINER} {{ isolation: isolate; }}\n{GROUP} {{ mix-blend-mode: plus-lighter; }}",
        LONE,
    ),
    VISIBLE_SIBLING: (True, "", LONE),
    "a sibling at opacity 0 and hidden": (
        True,
        f"{SIBLING} {{ opacity: 0; visibility: hidden; }}",
        VISIBLE_SIBLING,
    ),
    "a sibling at opacity 0.5": (True, f"{SIBLING} {{ opacity: 0.5; }}", VISIBLE_SIBLING),
}
COMPARED = {LONE: (False, ""), VISIBLE_SIBLING: (True, "")}

# The two answers, by the largest difference over the eight positions.
# How large a difference is depends on the glyphs and on the position, from 1/255 on a single
# pixel to most of the range on a whole row of glyph edges, so the probe asserts only whether
# there is one. *Findings* has the sizes.
SAME = "the same pixels"
DIFFERENT = "different pixels"

# What each engine was measured to do, per device scale.
# Measured in chromium 153, firefox 155 and webkit 26.6 on 2026-10-11.
LAYERS = {
    "the container isolates": {
        "chromium": (SAME, SAME),
        "firefox": (SAME, SAME),
        "webkit": (DIFFERENT, DIFFERENT),
    },
    "the group blends": {
        "chromium": (DIFFERENT, DIFFERENT),
        "firefox": (DIFFERENT, DIFFERENT),
        "webkit": (DIFFERENT, DIFFERENT),
    },
    "both, as animo writes them": {
        "chromium": (DIFFERENT, DIFFERENT),
        "firefox": (DIFFERENT, DIFFERENT),
        "webkit": (DIFFERENT, DIFFERENT),
    },
    VISIBLE_SIBLING: {
        "chromium": (SAME, SAME),
        "firefox": (SAME, SAME),
        "webkit": (DIFFERENT, DIFFERENT),
    },
    "a sibling at opacity 0 and hidden": {
        "chromium": (SAME, SAME),
        "firefox": (SAME, SAME),
        "webkit": (SAME, SAME),
    },
    "a sibling at opacity 0.5": {
        "chromium": (SAME, SAME),
        "firefox": (SAME, SAME),
        "webkit": (SAME, SAME),
    },
}


def frames_shot(typst: TypstRunner, context, sibling: bool, css: str, name: str):
    """Render the eight frames under the given rules, and return their pixels and scale.

    The scale is read off the page, as `window.devicePixelRatio`.
    """
    body = "\n".join(frame(offset, sibling) for offset in OFFSETS)
    path = typst.html(document(body, BASE + css), name=name)
    return settled_screenshot(context, path, inspect=group_columns, full_page=True)


def group_columns(page) -> tuple[slice, int]:
    """The device pixel columns of the group, which hold none of the sibling's ink, and the
    device scale."""
    scale = page.evaluate("window.devicePixelRatio")
    found = rects(page, '[data-typst-label="group"]')
    assert len(found) == len(OFFSETS), f"expected one group per frame, found {len(found)}"
    right = max(box.x + box.width for box in found)
    # The rectangles are in CSS pixels, of which a point is 4/3.
    assert right < (9 + SIBLING_DX) * 4 / 3, "the group reaches the columns of the sibling"
    return slice(0, int(right * scale) + 2), int(scale)


@pytest.mark.parametrize("condition", list(CONDITIONS))
def test_which_property_changes_the_raster_of_a_group_at_rest(
    typst: TypstRunner, scaled_context, browser_name, condition
):
    """What session 17 can gain by writing the blend and the isolation only during a boundary.

    Chromium 153 and firefox 155 draw a group in an isolating container exactly as without
    one, and draw it differently when the group blends.
    Webkit 26.6 moves glyph edges for either property, and also when the stack holds a
    visible sibling, so in webkit the sibling's presence changes the raster.
    The opacity and the visibility of the sibling change nothing in any of the three.
    """
    sibling, css, against = CONDITIONS[condition]
    reference, (columns, scale) = frames_shot(
        typst, scaled_context, *COMPARED[against], "reference.html"
    )
    shot, _ = frames_shot(typst, scaled_context, sibling, css, "condition.html")
    difference = np.abs(reference[:, columns].astype(int) - shot[:, columns].astype(int))
    measured = int(difference.max())
    pixels = int((difference > 1).any(axis=2).sum())
    expected = LAYERS[condition][browser_name][scale - 1]
    assert (measured == 0) == (expected == SAME), (
        f"{browser_name} at scale {scale} with {condition}, against {against}: expected "
        f"{expected}, measured {measured}/255 with {pixels} pixels over one"
    )
