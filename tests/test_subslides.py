# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 2: the paged outputs of a slide with a timeline.

The presentation renders one page per state and applies the display state with typst's own
`move`, `scale` and `hide`. Two claims are being made about those pages, and pixels are the
only honest way to check either.
The first is that the display state lands where the timeline said it should.
The second is the invariant of the whole design: nothing moves between two states except
what the timeline moved, down to the pixel, outside the box of the tag it addressed.

The marks are filled squares at stated offsets rather than glyphs, because a square's
corners are a number that can be asserted, and one pixel is one typst point here.
"""

import numpy as np
import pytest
from decks import deck
from harness import (
    Box,
    PagedRunner,
    assert_differs,
    assert_identical,
    assert_identical_outside,
)

RED = (255, 0, 0)

GREEN = (0, 255, 0)

# One centimetre in typst points, which is one pixel each at the default resolution.
CM = 28.3465

# The body's origin sits at the deck's margin.
ORIGIN = CM


def mark(name: str, dx: str, dy: str, size: str = "2cm") -> str:
    """A tagged filled square, placed at an offset from the body origin.

    The tag hugs, so that the square's own geometry is the tag site's geometry and the
    assertions can be written in centimetres from the source.
    """
    return (
        f"#place(dx: {dx}, dy: {dy}, "
        f'tag("{name}", wrap: box, rect(width: {size}, height: {size}, '
        'fill: rgb("#ff0000"))))'
    )


def timeline(*steps: str) -> str:
    """The animation argument of a slide, with the primitives imported inside it."""
    body = "\n  ".join(steps)
    return "{ import anim: *\n  " + body + " }"


def color_box(page: np.ndarray, color=RED, tol: int = 8) -> Box | None:
    """The bounding box of the pixels of approximately this colour.

    The tolerance is what makes an antialiased edge count as part of the square,
    so a box asserted from the source has to allow a pixel of rounding either way.
    """
    near = np.abs(page.astype(np.int16) - np.array(color, dtype=np.int16)).max(axis=2)
    found = near <= tol
    if not found.any():
        return None
    rows = np.flatnonzero(found.any(axis=1))
    cols = np.flatnonzero(found.any(axis=0))
    return Box(int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1)


def assert_close(found: float, expected: float, what: str, tol: float = 1.5):
    """Assert a pixel coordinate against the length the source states.

    A centimetre is 28.3465 points, so an edge lands between two pixels and the
    assertion has to be on the rule rather than on a number read off a run.
    """
    if abs(found - expected) > tol:
        raise AssertionError(f"{what}: found {found}, expected {expected}")


# The page count.


def test_the_presentation_renders_one_page_per_state(paged: PagedRunner):
    """S+1 states, and the handout still shows one page per slide.

    This is the point at which the two paged modes stop being the same output.
    """
    animation = timeline('sub(hide("m"))', 'sub(reveal("m"))', "sub()")
    source = paged.typst.source(
        deck(f"slide(animation: {animation})[{mark('m', '2cm', '2cm')}]", "slide[plain]")
    )
    assert len(paged.png(source, mode="presentation")) == 5
    assert len(paged.png(source)) == 2


def test_the_handout_shows_the_final_state_of_the_slide(paged: PagedRunner):
    """`handout: auto` on every step means the last one, which is this page."""
    animation = timeline('sub(move("m", dx: 3cm))')
    source = paged.typst.source(deck(f"slide(animation: {animation})[{mark('m', '0cm', '0cm')}]"))
    handout = paged.png(source)
    presentation = paged.png(source, mode="presentation")
    assert len(handout) == 1
    assert_identical(handout[0], presentation[-1], what="the handout and the last state")
    assert_differs(handout[0], presentation[0], what="the handout and the first state")


def test_a_state_can_be_taken_out_of_the_handout_and_others_put_in(paged: PagedRunner):
    """`handout:` is the only thing that says what a handout holds.

    Stating it in both directions is how an author keeps a step that a later step
    destroys, and drops a final state that is only a punchline.
    """
    animation = timeline(
        'sub(handout: true, move("m", dx: 3cm))',
        'sub(handout: false, move("m", dx: 3cm))',
    )
    source = paged.typst.source(deck(f"slide(animation: {animation})[{mark('m', '0cm', '0cm')}]"))
    handout = paged.png(source)
    presentation = paged.png(source, mode="presentation")
    assert len(presentation) == 3
    assert len(handout) == 1
    assert_identical(handout[0], presentation[1], what="the handout and the middle state")


def test_the_slide_flag_hands_out_the_initial_state(paged: PagedRunner):
    """The page the handout keeps is the state the body declared, and not the final one.

    This is the case the argument exists for: a timeline that restores what the body hides
    leaves a final state on which the slide makes no point.
    """
    animation = timeline('sub(move("m", dx: 3cm))')
    source = paged.typst.source(
        deck(f"slide(handout: true, animation: {animation})[{mark('m', '0cm', '0cm')}]")
    )
    handout = paged.png(source)
    presentation = paged.png(source, mode="presentation")
    assert len(presentation) == 2
    assert len(handout) == 2
    assert_identical(handout[0], presentation[0], what="the first page and the initial state")
    assert_identical(handout[1], presentation[1], what="the second page and the final state")


def test_the_slide_flag_and_the_step_flag_choose_their_pages_independently(paged: PagedRunner):
    """"Keep the first" and "drop the last" are the same slide's business, and neither
    says anything about the other."""
    animation = timeline('sub(handout: false, move("m", dx: 3cm))')
    source = paged.typst.source(
        deck(
            f"slide(handout: true, animation: {animation})[{mark('m', '0cm', '0cm')}]",
            "slide[plain]",
        )
    )
    handout = paged.png(source)
    presentation = paged.png(source, mode="presentation")
    assert len(presentation) == 3
    assert len(handout) == 2
    assert_identical(handout[0], presentation[0], what="the kept page and the initial state")


def test_a_slide_without_a_timeline_can_be_left_out_of_the_handout(paged: PagedRunner):
    """Its only state is also its final one, so nothing but the slide's own flag could
    take its page away."""
    source = paged.typst.source(
        deck(f"slide(handout: false)[{mark('m', '0cm', '0cm')}]", "slide[plain]")
    )
    handout = paged.png(source)
    presentation = paged.png(source, mode="presentation")
    assert len(presentation) == 2
    assert len(handout) == 1
    assert_identical(handout[0], presentation[1], what="the only page and the plain slide")


@pytest.mark.parametrize("flag", ["auto", "true", "false"])
def test_the_static_presentation_ignores_the_slide_flag(paged: PagedRunner, flag: str):
    """The presentation renders every state whatever the flags say, down to the pixel."""
    animation = timeline('sub(move("m", dx: 3cm))')
    body = mark("m", "0cm", "0cm")
    plain = paged.png(
        paged.typst.source(deck(f"slide(animation: {animation})[{body}]")),
        mode="presentation",
    )
    stated = paged.png(
        paged.typst.source(
            deck(f"slide(handout: {flag}, animation: {animation})[{body}]")
        ),
        mode="presentation",
    )
    assert len(stated) == len(plain)
    for index, (one, other) in enumerate(zip(stated, plain, strict=True)):
        assert_identical(one, other, what=f"state {index} with and without the flag")


# The four continuous primitives, in pixels.


def test_move_shifts_the_tagged_element_and_nothing_else(paged: PagedRunner):
    """The displacement is the one the timeline stated, and it is the only change.

    The box is the union of where the square was and where it went, which is what
    "nothing moves except what the timeline moved" means for a `move`.
    """
    animation = timeline('sub(move("m", dx: 3cm, dy: 1cm))')
    body = f"slide(animation: {animation})[{mark('m', '0cm', '0cm')}\n  A paragraph.]"
    pages = paged.png(deck(body), mode="presentation")
    before, after = (color_box(page) for page in pages)
    assert_close(before.x0, ORIGIN, "the square's left edge in state 0")
    assert_close(after.x0 - before.x0, 3 * CM, "the horizontal displacement")
    assert_close(after.y0 - before.y0, CM, "the vertical displacement")
    assert_identical_outside(
        pages[0],
        pages[1],
        Box(before.x0 - 2, before.y0 - 2, after.x1 + 2, after.y1 + 2),
        what="the two states",
    )


def test_scale_grows_the_element_about_its_own_centre(paged: PagedRunner):
    """About its centre, because that is the origin CSS scales about in the browser."""
    animation = timeline('sub(scale("m", f: 2))')
    body = f"slide(animation: {animation})[{mark('m', '2cm', '2cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    before, after = (color_box(page) for page in pages)
    assert_close(before.x1 - before.x0, 2 * CM, "the square's width in state 0")
    assert_close(after.x1 - after.x0, 4 * CM, "the square's width in state 1")
    assert_close(
        (after.x0 + after.x1) / 2,
        (before.x0 + before.x1) / 2,
        "the horizontal centre",
    )
    assert_close(
        (after.y0 + after.y1) / 2,
        (before.y0 + before.y1) / 2,
        "the vertical centre",
    )


def test_an_absolute_move_puts_the_corner_at_a_point_on_the_canvas(paged: PagedRunner):
    """`x` and `y` are measured from the canvas origin, which is the viewport's own corner.

    The square is placed at the body origin, a margin in, so an absolute move to 2 cm has
    to overshoot the shift a `dx: 2cm` would give by exactly that margin.
    """
    animation = timeline('sub(move("m", x: 2cm, y: 1cm))')
    body = f"slide(animation: {animation})[{mark('m', '0cm', '0cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    before, after = (color_box(page) for page in pages)
    assert_close(before.x0, ORIGIN, "the square's left edge in state 0")
    assert_close(after.x0, 2 * CM, "the square's left edge in state 1")
    assert_close(after.y0, CM, "the square's top edge in state 1")


def test_an_absolute_move_is_idempotent(paged: PagedRunner):
    """A tag's anchor excludes its own display state, so saying it twice says it once.

    This is what makes the absolute form usable at all: a step can restate where something
    belongs without having to know what the steps before it did to it.
    """
    animation = timeline('sub(move("m", x: 4cm, y: 3cm))', 'sub(move("m", x: 4cm, y: 3cm))')
    body = f"slide(animation: {animation})[{mark('m', '1cm', '2cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    assert_identical(pages[1], pages[2], what="a move stated twice and the same move once")
    assert_close(color_box(pages[1]).x0, 4 * CM, "the square's left edge")


def test_relto_puts_one_tag_where_another_one_is(paged: PagedRunner):
    """The anchor of `relto` is the other tag's corner, not the corner of its ink.

    Both squares hug their tag, so the two corners coincide to the pixel when the red one
    lands on the green one.
    """
    green = (
        '#place(dx: 8cm, dy: 3cm, tag("g", wrap: box, '
        'rect(width: 2cm, height: 2cm, fill: rgb("#00ff00"))))'
    )
    animation = timeline('sub(move("m", relto: "g"))')
    # The green square is written first, so the red one lands on top of it rather than
    # under it and its own box is the one the raster shows.
    body = f"slide(animation: {animation})[{green}\n  {mark('m', '0cm', '0cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    target = color_box(pages[0], GREEN)
    landed = color_box(pages[1])
    assert_close(landed.x0, target.x0, "the left edge of the moved square")
    assert_close(landed.y0, target.y0, "the top edge of the moved square")


def test_a_relative_move_does_not_move_what_is_relative_to_it(paged: PagedRunner):
    """`move("m", relto: "g")` reads where the body put `g`, not where a step took it.

    The two steps are in one timeline rather than in two decks, so the claim is about one
    rendering: whatever order the operations resolve in, the anchor is the same number.
    """
    green = (
        '#place(dx: 8cm, dy: 3cm, tag("g", wrap: box, '
        'rect(width: 2cm, height: 2cm, fill: rgb("#00ff00"))))'
    )
    animation = timeline('sub(move("g", dx: -3cm), move("m", relto: "g"))')
    body = f"slide(animation: {animation})[{green}\n  {mark('m', '0cm', '0cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    before = color_box(pages[0], GREEN)
    landed = color_box(pages[1])
    assert_close(landed.x0, before.x0, "the left edge of the moved square")
    assert_close(color_box(pages[1], GREEN).x0, before.x0 - 3 * CM, "the green square")


def test_a_per_axis_scale_renders_as_two_factors(paged: PagedRunner):
    """`fx` and `fy` are independent all the way to typst's own `scale`.

    A single factor would keep the square square, so the shape of the box is the assertion.
    """
    animation = timeline('sub(scale("m", f: 3))', 'sub(scale("m", fx: 2))')
    body = f"slide(animation: {animation})[{mark('m', '4cm', '2cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    tripled, mixed = (color_box(page) for page in pages[1:])
    assert_close(tripled.x1 - tripled.x0, 6 * CM, "the width at f: 3")
    assert_close(tripled.y1 - tripled.y0, 6 * CM, "the height at f: 3")
    # The axis the second step names is set to 2; the one it omits keeps the 3 it had.
    assert_close(mixed.x1 - mixed.x0, 4 * CM, "the width at fx: 2")
    assert_close(mixed.y1 - mixed.y0, 6 * CM, "the height at fx: 2")


def test_a_moved_and_scaled_element_lands_its_unscaled_corner(paged: PagedRunner):
    """An anchor is a layout corner and a scale is about a centre, so the two compose.

    The painted corner sits half the growth further out, which is why the manual says that
    absolute placement of scaled content is approximate by construction.
    """
    animation = timeline('sub(move("m", x: 5cm, y: 3cm), scale("m", f: 2))')
    body = f"slide(animation: {animation})[{mark('m', '0cm', '0cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    painted = color_box(pages[1])
    assert_close(painted.x0, 5 * CM - CM, "the painted left edge, one square-half out")
    assert_close(painted.y0, 3 * CM - CM, "the painted top edge, one square-half out")


def test_the_anchor_is_read_from_the_first_page_that_lays_the_tag_out(paged: PagedRunner):
    """Which site is the first one, when a tag is not laid out in every epoch.

    The presentation renders one page per state in order, so the first page holding the tag
    is the first state of the first epoch that lays it out, which is the frame the browser
    reads its anchor from. The tag here is inside an explicit region and absent from epoch
    0, so the two definitions have somewhere to diverge.
    """
    green = (
        '#region[#tag("a", wrap: box)'
        '[#rect(width: 2cm, height: 2cm, fill: rgb("#00ff00"))] #h(6cm)]'
    )
    animation = timeline('sub(reset("a"))', 'sub(move("m", relto: "a"))')
    body = f"slide(animation: {animation})[{green}\n  {mark('m', '0cm', '5cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    target = color_box(pages[1], GREEN)
    landed = color_box(pages[2])
    assert_close(landed.x0, target.x0, "the left edge of the moved square")
    assert_close(landed.y0, target.y0, "the top edge of the moved square")


def test_hide_takes_the_ink_and_leaves_the_space(paged: PagedRunner):
    """The defining difference between `hide` and the `remove` of a later version."""
    animation = timeline('sub(hide("m"))')
    body = f"slide(animation: {animation})[{mark('m', '2cm', '2cm')}]"
    pages = paged.png(deck(body), mode="presentation")
    assert color_box(pages[0]) is not None
    assert color_box(pages[1]) is None


def test_a_hidden_tag_holds_its_place_in_the_flow(paged: PagedRunner):
    """A tag the timeline reveals starts hidden, and hidden keeps the space.

    The red mark sits in the flow below the tagged green one, so it is what says whether
    the space was reserved: it may not move when the green one appears.
    """
    animation = timeline('sub(reveal("t"))')
    body = (
        f"slide(animation: {animation})[\n"
        '  #tag("t")[#rect(width: 3cm, height: 1cm, fill: rgb("#00ff00"))]\n\n'
        '  #rect(width: 2cm, height: 2cm, fill: rgb("#ff0000"))\n'
        "]"
    )
    pages = paged.png(deck(body), mode="presentation")
    assert color_box(pages[0], GREEN) is None
    assert color_box(pages[1], GREEN) is not None
    assert color_box(pages[0], RED) == color_box(pages[1], RED)


# The invariants.


def test_a_timeline_that_addresses_nothing_changes_no_pixel(paged: PagedRunner):
    """A tag site is the same structure in every state, and the identity is one of them.

    A slide full of tags and empty steps has to render exactly as the same slide with no
    timeline at all, or the two nested wrappers are not as layout-neutral as claimed.
    """
    body = (
        "  = A heading\n"
        '  #tag("phrase")[A tagged phrase] in a paragraph that runs on for a while.\n\n'
        '  #tag("items", list([one], [two]))\n\n'
        '  #tag("math")[$ x^2 + y^2 = z^2 $]\n'
    )
    animation = timeline("sub()", "sub()")
    static = paged.png(deck(f"slide[\n{body}]"))
    animated = paged.png(deck(f"slide(animation: {animation})[\n{body}]"))
    assert_identical(static[0], animated[0], what="the same slide with and without steps")


def test_a_wrap_none_tag_renders_exactly_as_its_untagged_body(paged: PagedRunner):
    """The body is handed back untouched, and a heading is the case that proves it.

    A heading shifts under every wrapper, because its own block spacing is trimmed at the
    wrapper's edge, so it is what would betray a wrapper that `wrap: none` did emit.
    """
    body = (
        "  = A heading\n"
        "  A paragraph before.\n\n"
        "  BODY\n\n"
        "  A paragraph after, long enough to wrap when the space is tight indeed.\n"
    )
    tagged = body.replace("BODY", '#tag("h", wrap: none)[= Another heading]')
    plain = body.replace("BODY", "= Another heading")
    assert_identical(
        paged.png(deck(f"slide[\n{plain}]"), ppi=144)[0],
        paged.png(deck(f"slide[\n{tagged}]"), ppi=144)[0],
        what="the untagged and the unwrapped tagged body",
    )


def test_tagging_a_headings_text_leaves_the_heading_where_it_was(paged: PagedRunner):
    """The remedy the manual gives for the shift a wrapper around a heading costs.

    A wrapper trims the heading's own block spacing at its edge and contributes the
    generic paragraph spacing instead, and typst does not expose the value animo would
    have to restore. Tagging the text rather than the heading is exact, not merely close.
    """
    body = "  HEADING\n  A paragraph after the heading that runs on for a while.\n"
    plain = body.replace("HEADING", "= A heading")
    tagged = body.replace("HEADING", '= #tag("t")[A heading]')
    assert_identical(
        paged.png(deck(f"slide[\n{plain}]"), ppi=144)[0],
        paged.png(deck(f"slide[\n{tagged}]"), ppi=144)[0],
        what="the untagged heading and the tagged heading text",
    )


def test_a_timeline_moves_only_the_tags_of_its_own_slide(paged: PagedRunner):
    """Tags are scoped to their slide, and this is what that looks like on paper."""
    first = timeline('sub(move("m", dx: 3cm))')
    source = deck(
        f"slide(animation: {first})[{mark('m', '0cm', '0cm')}]",
        f"slide[{mark('m', '0cm', '0cm')}]",
    )
    pages = paged.png(source, mode="presentation")
    assert len(pages) == 3
    moved = color_box(pages[1])
    untouched = color_box(pages[2])
    assert_close(moved.x0 - ORIGIN, 3 * CM, "the moved square of the first slide")
    assert_close(untouched.x0, ORIGIN, "the untouched square of the second slide")
