# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Styling from CSS: what is and is not reachable*.

Typst writes `fill` as a presentation attribute on every glyph.
A CSS rule on the glyphs outranks it, a rule on their group does not,
and that asymmetry is what puts `apply` in the structural class
and leaves a colour-only primitive in the future-features list.
"""

import pytest
from harness import TypstRunner
from htmldoc import document, stacked

FRAME = '#html.frame[#box(box[Hello world])#label("x")]\n'

GLYPH_FILL = """() => {
    const glyph = document.querySelector('[data-typst-label="x"] use');
    return getComputedStyle(glyph).fill;
}"""


def test_a_rule_on_the_descendants_wins_without_important(typst: TypstRunner, open_page):
    """Any CSS declaration outranks a presentation attribute."""
    path = typst.html(document(FRAME, '[data-typst-label="x"] use { fill: rgb(0, 128, 0); }'))
    page = open_page(path)
    assert page.evaluate(GLYPH_FILL) == "rgb(0, 128, 0)"


def test_a_rule_on_the_group_does_not_reach_the_glyphs(typst: TypstRunner, open_page):
    """The glyphs' own attribute beats an inherited value, so the group is the wrong target."""
    path = typst.html(
        document(FRAME, '[data-typst-label="x"] { fill: rgb(0, 128, 0); }'), name="group.html"
    )
    page = open_page(path)
    assert page.evaluate(GLYPH_FILL) == "rgb(0, 0, 0)"


def test_fill_interpolates_smoothly(typst: TypstRunner, open_page):
    """A colour-only primitive would be free, if it targets descendants explicitly."""
    page = open_page(typst.html(document(FRAME)))
    midpoint = page.evaluate(
        """() => {
            const glyph = document.querySelector('[data-typst-label="x"] use');
            const animation = glyph.animate(
                [{fill: "rgb(0, 0, 0)"}, {fill: "rgb(255, 0, 0)"}],
                {duration: 1000, fill: "both"},
            );
            animation.pause();
            animation.currentTime = 500;
            return getComputedStyle(glyph).fill;
        }"""
    )
    assert midpoint == "rgb(128, 0, 0)"


def test_stacking_order_is_fixed_at_compile_time(typst: TypstRunner, open_page):
    """SVG paints in document order, and `z-index` does not apply to SVG children.

    Z-order changing animations are therefore out of scope,
    and a slide's overlap has to be decided when it is written.
    Note that epoch frames are stacked as *HTML* elements,
    where the grid and `opacity` do apply, which is a different mechanism.
    """
    body = """\
#html.frame[
  #box(width: 40pt, height: 40pt)[
    #place(dx: 0pt, dy: 0pt)[#box(rect(width: 30pt, height: 30pt, fill: red))#label("under")]
    #place(dx: 10pt, dy: 10pt)[#box(rect(width: 30pt, height: 30pt, fill: blue))#label("over")]
  ]
]
"""
    path = typst.html(document(body, '[data-typst-label="under"] { z-index: 10; }'))
    page = open_page(path)
    colour = page.evaluate(
        """() => {
            const over = document.querySelector('[data-typst-label="over"]');
            const r = over.getBoundingClientRect();
            const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
            return hit.closest("[data-typst-label]").dataset.typstLabel;
        }"""
    )
    assert colour == "over", "z-index reordered the SVG children, which it is not supposed to do"


@pytest.mark.parametrize("selector", ['[data-typst-label="x"] use', '[data-typst-label="x"] > g'])
def test_a_selector_reaches_every_frame_that_carries_the_tag(
    typst: TypstRunner, open_page, selector
):
    """One rule applies continuous state to every epoch frame of a slide at once.

    Duplicate labels are what makes this work,
    and it is why entering an epoch never needs re-initialisation.
    """
    path = typst.html(
        stacked(
            ['#box(box[Hello world])#label("x")', '#box(box[Hello there])#label("x")'],
            f"{selector} {{ opacity: 0.25; }}",
        )
    )
    page = open_page(path)
    opacities = page.evaluate(
        f"""() => Array.from(
            document.querySelectorAll({selector!r}),
            node => Number(getComputedStyle(node).opacity),
        )"""
    )
    assert len(opacities) >= 2
    assert all(value == pytest.approx(0.25) for value in opacities)
