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
    rects = page.evaluate(
        """() => Array.from(
            document.querySelectorAll('[data-typst-label="region"]'),
            node => {
                const r = node.getBoundingClientRect();
                return {top: r.top, bottom: r.bottom};
            },
        )"""
    )
    assert len(rects) == 2, f"expected one region per frame, found {len(rects)}"
    width = page.viewport_size["width"]
    top = int(min(r["top"] for r in rects))
    bottom = int(max(r["bottom"] for r in rects)) + 1
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


def test_plus_lighter_keeps_the_midpoint_exact(typst: TypstRunner, open_page):
    """With `plus-lighter` the sum is exact, so nothing outside the region dips.

    This is what makes the containment claim true *during* the transition
    and not only at its endpoints.
    """
    page, reference = shot(typst, open_page, ONLY_FIRST, "reference2.html")
    band = region_band(page)
    _, blended = shot(typst, open_page, LIGHTER, "lighter.html")
    outside = slice(band.y1, None)
    deviation = int(abs(reference[outside].astype(int) - blended[outside].astype(int)).max())
    assert deviation <= 1, (
        "the blended midpoint drifted from the single frame: "
        f"{difference_report(reference[outside], blended[outside], tol=1)}"
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
