# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Fitting the slide to the browser window*.

The finding is a negative and a positive.
A length divided by a length is not arithmetic every engine has, so the fit may not be
written that way; a length divided by a *number* is, so it can.

Nothing here compiles a typst document: the claim is about CSS alone.
"""

import pytest

# A deck 453.5433pt wide, at 16:9, in a 1280 by 720 window.
WIDTH = 453.5433
ASPECT = 1.7777778
WINDOW = {"width": 1280, "height": 720}

# The recipe animo emits: the viewport, one typst point as a length, and a canvas
# a third wider than the slide, sized in that unit.
CANVAS = 604.9682

PAGE = f"""\
<style>
html, body {{ margin: 0; padding: 0; }}
:root {{
  --animo-viewport: min(100vw, 100vh * {ASPECT});
  --animo-unit: calc(var(--animo-viewport) / {WIDTH});
}}
.slide {{ position: relative; overflow: hidden;
         width: var(--animo-viewport); aspect-ratio: {ASPECT}; }}
.canvas {{ position: absolute; top: 0; left: 0;
          width: calc(var(--animo-unit) * {CANVAS});
          height: calc(var(--animo-unit) * 255.1181); }}
</style>
<div class="slide"><div class="canvas"></div></div>
"""

# Which engines compute `calc(<length> / <length>)` to a number.
#
# This is the whole reason animo does not write the fit that way.
# Chromium 151 computes it, as CSS Values 4 type checking says it should, and so does
# playwright's webkit 26.5, measured in a container because no webkit build runs on every
# contributor's distribution. Firefox 153 is the one that does not parse it at all, and it
# drops the entire declaration the division sits in, which is a silent failure: the canvas
# then renders unscaled in the top-left corner of the window.
# A changed value here is a finding that changed, not a probe that needs fixing.
DIVIDES_LENGTHS = {"chromium": True, "firefox": False, "webkit": True}


def test_dividing_a_length_by_a_length_is_not_portable(page, browser_name):
    """The negative half of the finding, per engine."""
    supported = page.evaluate("() => CSS.supports('scale', 'calc(100px / 40px)')")
    assert supported == DIVIDES_LENGTHS[browser_name], (
        f"{browser_name} now reports support={supported} for a length over a length; "
        "the finding this probe records has changed"
    )


def test_a_declaration_that_divides_lengths_is_dropped_whole(page, browser_name):
    """Why the negative matters: there is no partial result to fall back on.

    An engine that cannot parse the division discards the declaration,
    so the element keeps whatever the property was before, with nothing on the console.
    """
    page.set_content("<div id=x style='scale: calc(100px / 40px)'></div>")
    scale = page.evaluate("() => getComputedStyle(document.getElementById('x')).scale")
    expected = "2.5" if DIVIDES_LENGTHS[browser_name] else "none"
    assert scale == expected


def test_a_length_over_a_number_fits_the_canvas_in_every_engine(page):
    """The positive half: what animo emits instead, measured end to end.

    The window is set to the deck's own aspect ratio, so the slide is the whole of it
    and the canvas is exactly as much wider as it is in typst points.
    """
    page.set_viewport_size(WINDOW)
    page.set_content(PAGE)
    boxes = page.evaluate(
        """() => Object.fromEntries(
            ['.slide', '.canvas'].map(sel => {
                const r = document.querySelector(sel).getBoundingClientRect();
                return [sel, {width: r.width, height: r.height, x: r.x, y: r.y}];
            }),
        )"""
    )
    slide, canvas = boxes[".slide"], boxes[".canvas"]
    assert slide["width"] == pytest.approx(WINDOW["width"], abs=0.05)
    assert canvas["x"] == pytest.approx(0, abs=0.05)
    assert canvas["y"] == pytest.approx(0, abs=0.05)
    assert canvas["width"] == pytest.approx(WINDOW["width"] * CANVAS / WIDTH, abs=0.05), (
        "the canvas is not the width its size in typst points asks for"
    )


def test_the_unit_follows_the_window(page):
    """The fit is CSS, so a resize needs no runtime and no measurement.

    Halving the window halves everything the unit sizes, which is the property that lets
    animo emit the geometry once at compile time.
    """
    page.set_viewport_size(WINDOW)
    page.set_content(PAGE)
    before = page.evaluate("() => document.querySelector('.canvas').getBoundingClientRect().width")
    page.set_viewport_size({"width": WINDOW["width"] // 2, "height": WINDOW["height"] // 2})
    after = page.evaluate("() => document.querySelector('.canvas').getBoundingClientRect().width")
    assert after == pytest.approx(before / 2, abs=0.05)
