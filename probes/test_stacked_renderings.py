# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Choosing between stacked renderings: `opacity`, not `visibility`*.

A value finer than a slide number is rendered once per subslide and one of the renderings
is shown. Which property shows it is not a free choice, because a rendering in the body
sits inside an epoch frame, and a frame that is not being shown is `visibility: hidden`.

`visibility` is inherited and a descendant may take it back, which is exactly what the
region crossfade relies on. The same property therefore cannot select a rendering: one that
took its visibility back would paint out of a frame the slide is not showing. `opacity` does
not compose that way, and that asymmetry is what these probes pin.
"""

from harness import TypstRunner, screenshot
from htmldoc import stacked

# Two frames stacked as epoch frames are, each holding one labelled group.
# The second frame stands in for an epoch nobody is watching.
FRAMES = [
    '#box(rect(width: 30pt, height: 30pt, fill: rgb("#ff0000")))#label("front")',
    '#box(rect(width: 30pt, height: 30pt, fill: rgb("#0000ff")))#label("behind")',
]

# The stacking animo uses: one frame shown, the rest hidden with `visibility`.
HIDDEN = ".stack > svg:not(:first-child) { visibility: hidden; }\n"

PAINTED = """() => {
    const group = document.querySelector('[data-typst-label="behind"]');
    const style = getComputedStyle(group);
    return {visibility: style.visibility, opacity: style.opacity};
}"""


def test_a_descendant_takes_its_visibility_back_out_of_a_hidden_frame(
    typst: TypstRunner, open_page
):
    """The hazard, stated as the behaviour rather than as a rule.

    The group is inside a frame the stylesheet hid, and a `visibility: visible` on the
    group alone brings it back. This is the mechanism the region crossfade is built on and
    the reason a rendering may not be chosen with the same property.
    """
    css = HIDDEN + '[data-typst-label="behind"] { visibility: visible; }\n'
    page = open_page(typst.html(stacked(FRAMES, css)))
    assert page.evaluate(PAINTED)["visibility"] == "visible"


def test_opacity_does_not_reach_out_of_a_hidden_frame(typst: TypstRunner, open_page):
    """The property animo uses instead, which cannot undo the frame around it.

    A rendering at full opacity inside a hidden frame computes to `visibility: hidden`
    all the same, so a stack in the body shows nothing from the frames beside the one the
    slide is on.
    """
    css = HIDDEN + '[data-typst-label="behind"] { opacity: 1; }\n'
    page = open_page(typst.html(stacked(FRAMES, css), name="opacity.html"))
    painted = page.evaluate(PAINTED)
    assert painted == {"visibility": "hidden", "opacity": "1"}
    # And the pixels agree: what shows is the front frame's red and not the hidden blue.
    pixels = screenshot(page)
    assert tuple(pixels[10, 10]) == (255, 0, 0)


def test_opacity_selects_within_the_frame_that_is_shown(typst: TypstRunner, open_page):
    """And it still selects, which is the other half: hidden is hidden and shown is shown.

    Both groups are in the frame the stylesheet leaves visible, stacked as the renderings
    of one `per-subslide` are, and only the selected one has any ink.
    """
    frames = [
        '#box(width: 30pt, height: 30pt)[\n'
        "  #place(dx: 0pt, dy: 0pt)[#box(rect(width: 30pt, height: 30pt, fill: red))"
        '#label("front")]\n'
        "  #place(dx: 0pt, dy: 0pt)[#box(rect(width: 30pt, height: 30pt, fill: blue))"
        '#label("behind")]\n'
        "]"
    ]
    css = '[data-typst-label="behind"] { opacity: 0; }\n'
    page = open_page(typst.html(stacked(frames, css), name="within.html"))
    assert page.evaluate(PAINTED) == {"visibility": "visible", "opacity": "0"}
