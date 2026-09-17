# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *CSS animation of typst SVG groups*.

Every continuous primitive is one row of the table in that finding.
The rows that matter most are negative: the `transform` shorthand clobbers typst's own
positioning, `scale` without `transform-box: fill-box` scales about the wrong origin, and
the `transform-box` that fixes it moves any group that carries a transform of typst's own.
All three fail silently, by moving content rather than by raising anything.
"""

import numpy as np
import pytest
from harness import TypstRunner, screenshot
from htmldoc import document
from measuring import rect
from svgtools import SVG, group, parse

# A labelled box with a nested box inside it, which is what `tag` emits:
# the outer group carries typst's own translate, the inner group is the slot animo writes to.
FRAME = '#html.frame[#v(20pt)#box(box[Hello world])#label("x")]\n'


def build(typst: TypstRunner, css: str):
    """Compile a one-frame document with the given rules and return its path."""
    return typst.html(document(FRAME, css))


def test_typst_emits_no_group_level_opacity_or_style(typst: TypstRunner):
    """Opacity is entirely free, because there is nothing of typst's to compose with."""
    element = group(parse(build(typst, "").read_text()), "x")
    assert "opacity" not in element.attrib
    assert "style" not in element.attrib


def test_opacity_reaches_the_group(typst: TypstRunner, open_page):
    """`reveal` and `hide` are an opacity animation on the tag's inner group."""
    page = open_page(build(typst, '[data-typst-label="x"] > g { opacity: 0.35; }'))
    computed = page.evaluate(
        """() => getComputedStyle(document.querySelector('[data-typst-label="x"] > g')).opacity"""
    )
    assert float(computed) == pytest.approx(0.35)


def test_the_translate_property_composes_with_typsts_own_transform(typst: TypstRunner, open_page):
    """`move` is the individual `translate` property, and it leaves typst's offset alone."""
    plain = build(typst, "")
    page = open_page(plain)
    before = rect(page, '[data-typst-label="x"]')
    transform_before = page.evaluate(
        """() => document.querySelector('[data-typst-label="x"]').getAttribute("transform")"""
    )

    moved = typst.html(
        document(FRAME, '[data-typst-label="x"] > g { translate: 50px 0; }'), name="moved.html"
    )
    page = open_page(moved)
    after = rect(page, '[data-typst-label="x"]')
    transform_after = page.evaluate(
        """() => document.querySelector('[data-typst-label="x"]').getAttribute("transform")"""
    )

    assert after.x > before.x, "the element did not move at all"
    assert after.y == pytest.approx(before.y, abs=0.05), "the element moved vertically as well"
    assert transform_after == transform_before, "typst's own transform attribute changed"


def test_the_transform_shorthand_clobbers_typsts_positioning(typst: TypstRunner, open_page):
    """The prohibition in *Architecture* rule 3, measured.

    Nothing errors: the element simply loses the offset typst gave it,
    which is why animo may never emit the shorthand and a stray one in user CSS
    silently breaks a deck.
    """
    page = open_page(build(typst, ""))
    before = rect(page, '[data-typst-label="x"]')

    clobbered = typst.html(
        document(FRAME, '[data-typst-label="x"] { transform: translate(50px, 0); }'),
        name="clobbered.html",
    )
    page = open_page(clobbered)
    after = rect(page, '[data-typst-label="x"]')

    assert after.y < before.y - 1, (
        "the vertical offset survived the shorthand, "
        f"so this probe no longer measures what it claims: {before} versus {after}"
    )


def test_scale_without_fill_box_displaces_the_element(typst: TypstRunner, open_page):
    """The default `transform-box: view-box` scales about the SVG origin, not the element."""
    page = open_page(build(typst, ""))
    before = rect(page, '[data-typst-label="x"]')

    scaled = typst.html(
        document(FRAME, '[data-typst-label="x"] > g { scale: 2; }'), name="scaled.html"
    )
    page = open_page(scaled)
    after = rect(page, '[data-typst-label="x"]')

    assert after.width == pytest.approx(2 * before.width, rel=0.01)
    assert after.center[1] != pytest.approx(before.center[1], abs=1.0), (
        "the element stayed put without `transform-box: fill-box`, "
        "which is not what this release was measured to do"
    )


# How far the centre of a group may move under a scale about its own centre.
#
# Zero is the claim, and chromium 151 meets it to well under a tenth of a pixel.
# Firefox 153 resolves `fill-box` to a box whose centre sits about 0.7 px from the one
# `getBBox` reports, so a doubling moves the centre by that much on an 11 px line.
# The tolerance is the larger of the two, because the claim is "in place" and not
# "to the pixel", and a difference this size is invisible in a transition.
CENTRE_TOLERANCE = 1.0


def test_scale_about_the_element_centre_needs_fill_box(typst: TypstRunner, open_page):
    """With `fill-box` and a centred origin, `scale` grows the element in place.

    The centre is invariant, which is also what makes centres the right thing
    to pair on in a future morph.
    """
    page = open_page(build(typst, ""))
    before = rect(page, '[data-typst-label="x"]')

    scaled = typst.html(
        document(
            FRAME,
            """\
[data-typst-label="x"] > g {
  scale: 2;
  transform-box: fill-box;
  transform-origin: center;
}""",
        ),
        name="in-place.html",
    )
    page = open_page(scaled)
    after = rect(page, '[data-typst-label="x"]')

    assert after.width == pytest.approx(2 * before.width, rel=0.01)
    assert after.center[0] == pytest.approx(before.center[0], abs=CENTRE_TOLERANCE)
    assert after.center[1] == pytest.approx(before.center[1], abs=CENTRE_TOLERANCE)


def test_opacity_translate_and_scale_compose(typst: TypstRunner, open_page):
    """All three at once, which is what a subslide that moves, scales and fades does."""
    page = open_page(build(typst, ""))
    before = rect(page, '[data-typst-label="x"]')

    combined = typst.html(
        document(
            FRAME,
            """\
[data-typst-label="x"] > g {
  opacity: 0.5;
  translate: 50px 0;
  scale: 2;
  transform-box: fill-box;
  transform-origin: center;
}""",
        ),
        name="combined.html",
    )
    page = open_page(combined)
    after = rect(page, '[data-typst-label="x"]')
    opacity = page.evaluate(
        """() => getComputedStyle(document.querySelector('[data-typst-label="x"] > g')).opacity"""
    )

    assert float(opacity) == pytest.approx(0.5)
    assert after.width == pytest.approx(2 * before.width, rel=0.01)
    assert after.center[0] > before.center[0]


def test_a_css_length_inside_a_group_is_a_user_unit(typst: TypstRunner, open_page):
    """A move expressed in typst lengths stays the same fraction of the slide at any size.

    Inside the SVG, `50px` is 50 user units, which the browser scales by the ratio between
    the rendered size of the frame and its `viewBox`.
    """
    page = open_page(build(typst, ""))
    before = rect(page, '[data-typst-label="x"]')
    scale = page.evaluate(
        """() => {
            const svg = document.querySelector("svg");
            return svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
        }"""
    )
    assert scale != pytest.approx(1.0, abs=0.01), (
        "the frame happens to render at one pixel per user unit, "
        "so this probe cannot tell the two units apart"
    )

    moved = typst.html(
        document(FRAME, '[data-typst-label="x"] > g { translate: 50px 0; }'), name="units.html"
    )
    page = open_page(moved)
    after = rect(page, '[data-typst-label="x"]')
    assert after.x - before.x == pytest.approx(50 * scale, rel=0.01)


def test_a_paused_animation_interpolates_smoothly(typst: TypstRunner, open_page):
    """The Web Animations API is what makes a mid-flight assertion reproducible.

    A paused animation with an explicit `currentTime` samples the transition deterministically
    instead of racing it, and typst's own transform survives every sample.
    """
    page = open_page(build(typst, ""))
    samples = page.evaluate(
        """() => {
            const outer = document.querySelector('[data-typst-label="x"]');
            const inner = outer.querySelector("g");
            const animation = inner.animate(
                [
                    {translate: "0px 0", opacity: 0},
                    {translate: "50px 0", opacity: 1},
                ],
                {duration: 1000, fill: "both"},
            );
            animation.pause();
            const out = [];
            for (const t of [0, 500, 1000]) {
                animation.currentTime = t;
                const r = outer.getBoundingClientRect();
                out.push({
                    x: r.x,
                    opacity: Number(getComputedStyle(inner).opacity),
                    transform: outer.getAttribute("transform"),
                });
            }
            return out;
        }"""
    )
    xs = [sample["x"] for sample in samples]
    opacities = [sample["opacity"] for sample in samples]
    assert xs[0] < xs[1] < xs[2], f"the motion is not monotonic: {xs}"
    assert xs[1] == pytest.approx((xs[0] + xs[2]) / 2, abs=0.5), f"the midpoint is off: {xs}"
    assert opacities == pytest.approx([0.0, 0.5, 1.0], abs=0.01)
    assert len({sample["transform"] for sample in samples}) == 1, (
        "typst's own transform attribute changed during the animation"
    )


def test_a_running_animation_rasterises_as_the_same_inline_style(
    typst: TypstRunner, open_page
):
    """The end of a transition is not a moment the audience can see.

    A step writes its display state as inline style and animates from the old values to
    it, so at the end the animation stops applying and the style takes over. If a value
    that comes from a running animation rasterised differently from the same value in a
    style declaration, every step would pop at its end, at the moment the audience is
    looking hardest.

    The two paths are compared directly, with an animation that holds one value from
    beginning to end, so that nothing but the path differs. They agree bit for bit in
    chromium 151 and firefox 153.
    """
    style = {"translate": "40px 12px", "scale": "1.6"}

    page = open_page(build(typst, ""))
    page.evaluate(
        """style => {
            Object.assign(
                document.querySelector('[data-typst-label="x"] > g').style, style
            );
        }""",
        style,
    )
    settled = screenshot(page)

    page = open_page(build(typst, ""))
    page.evaluate(
        """style => {
            const inner = document.querySelector('[data-typst-label="x"] > g');
            const animation = inner.animate([style, style], {duration: 1000});
            animation.pause();
            animation.currentTime = 500;
        }""",
        style,
    )
    animating = screenshot(page, animations="allow")

    difference = np.abs(settled.astype(np.int16) - animating.astype(np.int16))
    assert difference.max() == 0, (
        "a value under a running animation does not rasterise as the same value in a "
        f"style declaration, deviating by {difference.max()} over "
        f"{int((difference.max(axis=2) > 0).sum())} pixels"
    )


# A glyph long enough to have a lot of edge, so that the band around it is a real number.
GLYPHS = '#html.frame[#v(20pt)#box(box[Hamburgefonstiv])#label("x")]\n'


def edge_band(image: np.ndarray) -> float:
    """How much antialiasing edge a rendering carries, per unit of ink.

    Ink is what is nearly black, the band is everything in between, and the ratio is what
    tells a re-rasterised glyph from an upscaled picture of one: ink grows with the square
    of a scale factor while an edge grows with the factor, so the ratio halves at every
    doubling if the glyph is drawn afresh, and stays put if it is stretched.
    """
    grey = image.mean(axis=2)
    ink = int((grey < 64).sum())
    band = int(((grey >= 64) & (grey <= 200)).sum())
    assert ink > 0, "the probe found no ink to measure the edge of"
    return band / ink


def test_a_scaled_glyph_is_drawn_afresh_rather_than_stretched(typst: TypstRunner, open_page):
    """What a `scale` looks like, which is the half of this finding that is not a number.

    Text under a CSS scale stays as sharp as text at its own size, because the browser
    rasterises the glyph outline at the scale it ends up at. Measured over a doubling and
    a quadrupling, the edge per unit of ink halves each time, in chromium 151 and firefox
    153: 0.20, 0.10 and 0.05.
    """
    page = open_page(typst.html(document(GLYPHS, "body { margin: 0; background: #fff; }")))
    ratios = []
    for factor in (1, 2, 4):
        page.evaluate(
            """factor => {
                document.querySelector('[data-typst-label="x"] > g').style.scale =
                    String(factor);
            }""",
            factor,
        )
        ratios.append(edge_band(screenshot(page)))
    for coarse, fine in zip(ratios, ratios[1:], strict=False):
        assert fine < 0.7 * coarse, (
            "a doubled glyph carries as much antialiasing edge per unit of ink as the "
            f"glyph at its own size, so it is being stretched rather than drawn: {ratios}"
        )


# The same frame without the nested box, so that the only group inside the labelled one is
# a group typst positioned rather than a slot animo built.
# `#box[..]` puts the content's own group directly inside the label, and typst writes the
# line's y-flip on it, which is what every glyph run in a frame carries.
# This is the shape of a region footprint: its children are the region's content.
CONTENT = '#html.frame[#v(20pt)#box[Hello world]#label("y")]\n'

# What the slot of a tag site needs, applied one level too far out.
ANCHORED = """\
[data-typst-label="y"] > g {
  transform-box: fill-box;
  transform-origin: center;
}"""


def test_a_group_typst_positioned_carries_a_flip(typst: TypstRunner):
    """What the next probe rests on, asserted separately so its failure names the cause."""
    element = group(parse(typst.html(document(CONTENT)).read_text()), "y")
    inside = element.findall(f"{SVG}g")
    assert len(inside) == 1
    assert inside[0].get("transform", "").startswith("matrix("), (
        "typst no longer writes a matrix on the group inside a labelled box, "
        f"but {inside[0].get('transform')!r}"
    )


def test_fill_box_moves_a_group_that_carries_typsts_own_transform(typst: TypstRunner, open_page):
    """`transform-box` and `transform-origin` are not free, and this is the trap.

    They are about the element's *own* `transform` as much as about the CSS transform
    properties beside it, so setting them re-anchors what typst wrote. A `translate` is
    unaffected, since translation does not depend on an origin, but the `matrix(1 0 0 -1 ..)`
    of a glyph run is a reflection and moves by twice the distance from the origin to the
    fill box's centre. Nothing errors and no transform property is set at all.

    So a rule that reaches a group animo did not build displaces content, which is the same
    failure mode as the `transform` shorthand two probes up.
    """
    page = open_page(typst.html(document(CONTENT), name="plain.html"))
    before = rect(page, '[data-typst-label="y"] > g')

    page = open_page(typst.html(document(CONTENT, ANCHORED), name="anchored.html"))
    after = rect(page, '[data-typst-label="y"] > g')

    assert after.width == pytest.approx(before.width, abs=0.05), "the group changed size"
    assert after.center[1] != pytest.approx(before.center[1], abs=1.0), (
        "the flip stayed put under `transform-box: fill-box`, "
        "which is not what this release was measured to do: "
        f"{before} versus {after}"
    )


def test_fill_box_leaves_a_slot_animo_built_where_it_is(typst: TypstRunner, open_page):
    """The other half of the trap: on a slot the two declarations move nothing.

    `tag` wraps its body twice, so the inner group carries no transform of its own and
    there is nothing for an origin to re-anchor. That is what makes the declarations safe
    where animo writes them and unsafe anywhere else.
    """
    page = open_page(build(typst, ""))
    before = rect(page, '[data-typst-label="x"] > g')

    page = open_page(
        typst.html(
            document(
                FRAME,
                """\
[data-typst-label="x"] > g {
  transform-box: fill-box;
  transform-origin: center;
}""",
            ),
            name="slot.html",
        )
    )
    after = rect(page, '[data-typst-label="x"] > g')

    assert after.approx(before, tol=0.05), f"the slot moved: {before} versus {after}"
