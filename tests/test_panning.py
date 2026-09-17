# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Panning: the viewport moving over a canvas larger than itself, in all three tiers.

`pan` is the slide primitive, so what it changes is not a tag but where the slide's
viewport sits on its canvas.
That position is resolved three times over: by the resolver, as an anchor and an offset per
axis; by typst on paper, which reads the anchor off a marker placed in the tag's wrapper;
and by the browser, which reads it off the origin of the tag's group.
The first is asserted in `test_plan.py`, the other two here, and whether the last two agree
with each other is asserted in `test_cross_target.py`.
"""

import numpy as np
import pytest
from decks import deck
from harness import Deck, PagedRunner, TypstRunner, assert_identical, screenshot

# One centimetre in typst points, which is one pixel at the default raster resolution.
CM = 28.3465

# A `relto` puts the tag it pans to at the deck's margin.
ORIGIN = CM

# How far a pan read in the browser may be from the length the source states, in points.
# The pan is read off two boxes on the page, each rounded to a fraction of a CSS pixel,
# which is under a tenth of a point at the default window, while a real error is a
# box height or a margin, several points at the least.
TOLERANCE = 0.1

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)


def square(color: str, dx: str = "2mm", dy: str = "2mm") -> str:
    """A filled square for one of the outer layers, placed near the viewport's corner."""
    return f'place(dx: {dx}, dy: {dy}, rect(width: 5mm, height: 5mm, fill: rgb("{color}")))'


def far(name: str = "far", dx: str = "18cm", dy: str = "2cm", size: str = "2cm") -> str:
    """A tagged red square placed at an offset from the body origin, beyond the viewport."""
    return (
        f"#place(dx: {dx}, dy: {dy}, "
        f'tag("{name}", wrap: box, rect(width: {size}, height: {size}, '
        'fill: rgb("#ff0000"))))'
    )


def timeline(*steps: str) -> str:
    """The animation argument of a slide, with the primitives imported inside it."""
    return "{ import anim: *\n  " + "\n  ".join(steps) + " }"


def panned(body: str, *steps: str, **slide) -> str:
    """A one-slide deck with a timeline."""
    extra = "".join(f", {key}: {value}" for key, value in slide.items())
    return deck(f"slide(animation: {timeline(*steps)}{extra})[\n  {body}\n]")


# Tier 1: the pan typst resolves for each state, as the paged outputs publish it.

PANS = """
#context {
  let pans = query(<animo-geometry>).map(it => it.value).filter(it => it.slide == SLIDE)
  assert.eq(pans.len(), 1, message: "slide SLIDE published " + repr(pans.len()) + " pans")
  let pans = pans.first().pans
  let near(a, b) = calc.abs((a - b).pt()) < 0.01
  ASSERTIONS
}
"""


def pans_check(*expected: tuple[str, str], slide: int = 1) -> str:
    """Assert the resolved pan of every state of one slide, as pairs of typst lengths."""
    lines = [f"assert.eq(pans.len(), {len(expected)})"]
    for state, pair in enumerate(expected):
        for axis, value in zip("xy", pair, strict=True):
            lines.append(
                f"assert(near(pans.at({state}).{axis}, {value}), "
                f'message: "state {state} {axis}: " + repr(pans.at({state}).{axis}))'
            )
    return (
        PANS.replace("SLIDE", str(slide)).replace("ASSERTIONS", "\n  ".join(lines))
    )


@pytest.mark.parametrize("mode", ["handout", "presentation"])
def test_relto_puts_the_tag_where_the_body_starts(typst: TypstRunner, mode):
    """The anchor of a `relto` is the tag's corner, less the margin the body is inset by.

    Both paged modes, because the handout renders fewer pages than there are states and
    still has to resolve every one of them from the pages it does render.
    """
    source = panned(far(dx="20cm", dy="3cm"), 'sub(pan(relto: "far"))')
    typst.ok(source + pans_check(("0pt", "0pt"), ("20cm", "3cm")), sysinp={"animo": mode})


def test_offsets_and_relative_steps_add_to_the_anchor(typst: TypstRunner):
    """`x` is measured from the anchor, `dx` from wherever the viewport already is."""
    source = panned(
        far(dx="20cm", dy="3cm"),
        'sub(pan(relto: "far", x: -1cm))',
        "sub(pan(dx: 2cm, y: 1cm))",
        "sub(pan(x: 0cm, y: 0cm))",
    )
    typst.ok(
        source
        + pans_check(("0pt", "0pt"), ("19cm", "3cm"), ("21cm", "1cm"), ("0cm", "0cm"))
    )


def test_an_inline_tag_is_anchored_at_its_corner_and_not_at_its_baseline(typst: TypstRunner):
    """Typst records an element in the middle of a line at the line's baseline.

    Read that way, this tag would be anchored one square lower than it starts, and the
    viewport would cut the square off. The marker in its wrapper is what says where the
    wrapper really begins, which is the top of the first line here, since the square is
    the tallest thing on it.
    """
    body = 'Words #tag("w", wrap: box)[#box(rect(width: 1cm, height: 1cm))] after.'
    source = panned(body, 'sub(pan(relto: "w"))')
    typst.ok(
        source
        + PANS.replace("SLIDE", "1").replace(
            "ASSERTIONS",
            'assert(near(pans.at(1).y, 0pt), message: "y: " + repr(pans.at(1).y))\n'
            '  assert(pans.at(1).x > 1cm, message: "x: " + repr(pans.at(1).x))',
        )
    )


def test_a_tag_is_anchored_where_the_body_put_it_and_not_where_it_was_moved(
    typst: TypstRunner,
):
    """A tag's own display state sits inside its wrapper, so the anchor ignores it.

    That makes `relto` mean the same in every state, and the browser agrees, because it
    reads the anchor before the timeline has written anything on the slide.
    """
    source = panned(
        far(dx="20cm", dy="3cm"),
        'sub(move("far", x: 3cm, y: 1cm))',
        'sub(pan(relto: "far"))',
    )
    typst.ok(source + pans_check(("0pt", "0pt"), ("0pt", "0pt"), ("20cm", "3cm")))


MISSING = "a pan on slide 2 is relative to the tag nowhere, but that slide has no tag of that name"


@pytest.mark.parametrize(
    "target",
    [{"sysinp": {"animo": "handout"}}, {"sysinp": {"animo": "presentation"}}, {"html": True}],
    ids=["handout", "presentation", "html"],
)
def test_a_relto_the_slide_does_not_tag_is_refused(typst: TypstRunner, target):
    """A misspelt name is the likely cause, and a silent fallback would hide it.

    The check depends on `query`, which is what can swallow a panic (see *Findings*),
    so the assertion is on the message itself, on the second slide of a deck that goes on
    after it, and on the absence of the second error the swallowing would bring along.
    """
    source = deck(
        f"slide(animation: {timeline('sub(pan(relto: \"far\"))')})[\n  {far()}\n]",
        f"slide(animation: {timeline('sub(pan(relto: \"nowhere\"))')})[\n  {far()}\n]",
        'slide[#tag("after")[after]]',
    )
    result = typst.fails(source, MISSING, **target)
    assert "not inside a #slide" not in result.stderr, result.stderr
    assert "did not converge" not in result.stderr, result.stderr


def test_a_tag_of_that_name_on_another_slide_does_not_count(typst: TypstRunner):
    """A tag name means nothing outside its own slide, and that includes a `relto`."""
    source = deck(
        f"slide[\n  {far('nowhere', dx='5cm')}\n]",
        f"slide(animation: {timeline('sub(pan(relto: \"nowhere\"))')})[\n  {far()}\n]",
    )
    typst.fails(source, MISSING)


def test_the_same_name_on_another_slide_is_no_anchor(typst: TypstRunner):
    """Each slide pans to its own site of a name, and a deck that does so converges."""
    source = deck(
        f"slide[\n  {far('t', dx='5cm')}\n]",
        f"slide(animation: {timeline('sub(pan(relto: \"t\"))')})[\n  {far('t', dx='10cm')}\n]",
    )
    result = typst.ok(source + pans_check(("0pt", "0pt"), ("10cm", "2cm"), slide=2))
    assert "did not converge" not in result.stderr, result.stderr


def test_a_slide_without_a_handout_page_is_not_refused_for_its_relto(typst: TypstRunner):
    """With no page there is no tag site to read back, which is not a missing tag.

    The plain second slide is what keeps the handout from holding no page at all, which
    the deck refuses for its own reasons.
    """
    source = deck(
        f"slide(animation: {timeline('sub(handout: false, pan(relto: \"far\"))')})[\n  {far()}\n]",
        "slide[plain]",
    )
    result = typst.ok(source)
    assert "did not converge" not in result.stderr, result.stderr


def test_a_relto_to_a_tag_without_a_wrapper_is_refused(typst: TypstRunner):
    """With no group there is no position for the browser to read."""
    typst.fails(
        panned('#tag("n", wrap: none)[plain]', 'sub(pan(relto: "n"))'),
        "the timeline addresses the tag n with a continuous primitive",
    )


# Tier 2: the pages a panned slide becomes.


def color_box(page: np.ndarray, color=RED, tol: int = 8) -> tuple[int, int, int, int] | None:
    """The bounding box `(x0, y0, x1, y1)` of the pixels of approximately this colour."""
    near = np.abs(page.astype(np.int16) - np.array(color, dtype=np.int16)).max(axis=2)
    found = near <= tol
    if not found.any():
        return None
    rows = np.flatnonzero(found.any(axis=1))
    cols = np.flatnonzero(found.any(axis=0))
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def test_a_panned_step_is_a_page_showing_another_part_of_the_canvas(paged: PagedRunner):
    """The square is beyond the viewport in state 0 and at the body origin in state 1."""
    pages = paged.png(panned(far(), 'sub(pan(relto: "far"))'), mode="presentation")
    assert len(pages) == 2
    assert color_box(pages[0]) is None, "content beyond the viewport reached the page"
    x0, y0, x1, y1 = color_box(pages[1])
    assert abs(x0 - ORIGIN) <= 1.5 and abs(y0 - ORIGIN) <= 1.5, (x0, y0)
    assert abs((x1 - x0) - 2 * CM) <= 1.5


def test_content_beyond_the_viewport_never_reaches_another_page(paged: PagedRunner):
    """One page per state and every page the size of the viewport, however large the canvas."""
    body = far(dx="30cm", dy="20cm") + "\n  " + far("near", dx="0cm", dy="0cm")
    pages = paged.png(panned(body, "sub(pan(dx: 5cm))"), mode="presentation")
    assert len(pages) == 2
    assert {page.shape for page in pages} == {(255, 454, 3)}


def test_the_handout_shows_the_viewport_of_each_state_it_keeps(paged: PagedRunner):
    """A handout page is the presentation page of the same state, pan included.

    This is the decision for a panned slide: nothing outside the kept viewports reaches the
    handout, and `handout: true` is how a panned-away view is kept.
    """
    source = paged.typst.source(
        panned(far(), 'sub(handout: true, pan(relto: "far"))', "sub(pan(x: 0cm, y: 0cm))")
    )
    presentation = paged.png(source, mode="presentation")
    handout = paged.png(source)
    assert len(handout) == 2
    assert_identical(handout[0], presentation[1], what="the kept page and its state")
    assert_identical(handout[1], presentation[2], what="the final page and its state")


def test_both_layers_stay_with_the_viewport_while_the_canvas_pans(paged: PagedRunner):
    """Both belong to the viewport, so a pan moves the canvas between them.

    The body is the control: the red square is off the page in state 0 and on it in state 1,
    so the two layers holding still is a fact about them and not about the pan.
    """
    source = panned(
        far(),
        'sub(pan(relto: "far"))',
        background=square("#0000ff"),
        overlay=square("#00ff00", dx="1cm"),
    )
    pages = paged.png(source, mode="presentation")
    assert color_box(pages[0], BLUE) == color_box(pages[1], BLUE) is not None
    assert color_box(pages[0], GREEN) == color_box(pages[1], GREEN) is not None
    assert color_box(pages[0], RED) is None and color_box(pages[1], RED) is not None


# Tier 3: the canvas element in the browser.


@pytest.fixture
def beyond(typst: TypstRunner):
    """A square beyond the viewport, panned to, and then panned to relatively."""
    source = panned(
        far(),
        'sub(pan(relto: "far"))',
        "sub(pan(dx: -2cm, y: 1cm))",
    )
    return typst.html(source, name="beyond.html")


def assert_pan(presentation: Deck, x: float, y: float):
    """Assert the pan the browser shows, in centimetres of the slide."""
    got = presentation.pan
    assert got == pytest.approx((x * CM, y * CM), abs=TOLERANCE), (
        f"panned to {got[0] / CM:.3f} cm, {got[1] / CM:.3f} cm"
    )


def test_a_pan_translates_the_canvas_and_leaves_the_frame_alone(deck_at, beyond):
    """*Architecture* rule 5: the pan belongs to the canvas, never to a frame.

    The epoch renderings sit in a frame inside the canvas, so moving the canvas moves them
    all and keeps them registered, which is what the epoch crossfade rests on.
    """
    presentation: Deck = deck_at(beyond)
    assert_pan(presentation, 0, 0)
    assert_pan(presentation.goto(1, 1), 18, 2)
    assert_pan(presentation.goto(1, 2), 16, 1)
    frame = presentation.page.evaluate(
        """() => {
            const svg = document.querySelector('.animo-canvas > svg');
            const computed = getComputedStyle(svg);
            return [computed.translate, computed.transform, svg.getAttribute('style')];
        }"""
    )
    assert frame[:2] == ["none", "none"], f"a frame carries a transform of its own: {frame}"


def test_the_viewport_clips_the_canvas(page, deck_at, beyond):
    """The square is on the canvas in every state and on the screen only once panned to."""
    presentation: Deck = deck_at(beyond)
    page.set_viewport_size({"width": 908, "height": 511})
    slide = page.locator(".animo-slide[data-animo-current]")
    red = np.array(RED, dtype=np.uint8)
    assert not (screenshot(slide) == red).all(axis=2).any(), "the viewport did not clip"
    presentation.goto(1, 1)
    assert (screenshot(slide) == red).all(axis=2).any(), "the pan did not bring it into view"


def test_a_deep_link_to_a_panned_state_snaps(page, deck_at, beyond):
    """What `typst watch` reloads into, for the canvas as for the tags."""
    presentation: Deck = deck_at(beyond)
    presentation.goto(1, 2)
    page.reload()
    presentation.goto(1, 2)
    assert page.evaluate("() => document.getAnimations().length") == 0
    assert_pan(presentation, 16, 1)


def test_a_pan_step_animates_the_canvas_translate_and_nothing_else(page, deck_at, beyond):
    """A step animates only what it changes, and halfway through it is halfway along."""
    presentation: Deck = deck_at(beyond)
    page.add_style_tag(content=":root { --animo-primitive-duration: 4000ms; --animo-easing: linear }")
    presentation.press("ArrowRight")
    assert presentation.animating == [{"translate"}]
    presentation.scrub(2000)
    assert_pan(presentation, 9, 1)


def test_stepping_back_brings_the_viewport_back(deck_at, beyond):
    """A pan is a state, so arriving at state 0 from state 2 is arriving at the origin."""
    presentation: Deck = deck_at(beyond)
    presentation.press("ArrowRight", 2).settle()
    assert_pan(presentation, 16, 1)
    presentation.press("ArrowLeft", 2).settle()
    assert_pan(presentation, 0, 0)


def test_a_pan_is_the_same_fraction_of_the_slide_at_any_window_size(page, deck_at, beyond):
    """The runtime writes a percentage of the canvas and never measures the window."""
    presentation: Deck = deck_at(beyond)
    for width in (1280, 640):
        page.set_viewport_size({"width": width, "height": width * 9 // 16})
        assert_pan(presentation.goto(1, 1), 18, 2)


def test_an_inline_tag_is_anchored_at_its_corner_in_the_browser(deck_at, typst: TypstRunner):
    """The group's origin is the wrapper's corner, whatever the tag's ink looks like."""
    body = 'Words #tag("w", wrap: box)[#box(rect(width: 1cm, height: 1cm))] after.'
    presentation: Deck = deck_at(typst.html(panned(body, 'sub(pan(relto: "w"))')))
    x, y = presentation.goto(1, 1).pan
    assert y == pytest.approx(0, abs=TOLERANCE)
    assert x > CM


@pytest.mark.parametrize("layer", ["background", "overlay"])
def test_a_layer_stays_put_while_the_canvas_pans(deck_at, typst: TypstRunner, layer):
    """Each layer is a frame of the viewport, beside the canvas rather than inside it.

    The frame count is what says that: a layer inside the canvas would be a second frame
    there, and it would then be panned along with the epoch renderings.
    """
    source = panned(
        far(),
        'sub(pan(relto: "far"))',
        background=square("#0000ff"),
        overlay=square("#00ff00", dx="1cm"),
    )
    presentation: Deck = deck_at(typst.html(source, name=f"{layer}.html"))
    where = """(layer) => {
        const slide = document.querySelector('.animo-slide');
        const frames = slide.querySelectorAll(':scope > .animo-canvas > svg').length;
        const box = slide.querySelector(`:scope > .animo-${layer}`).getBoundingClientRect();
        return [frames, box.x, box.y, box.width, box.height];
    }"""
    before = presentation.page.evaluate(where, layer)
    after = presentation.goto(1, 1).page.evaluate(where, layer)
    assert before[0] == 1, f"the {layer} became a frame of the canvas"
    assert after == pytest.approx(before, abs=0.01)
