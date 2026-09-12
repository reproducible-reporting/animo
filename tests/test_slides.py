# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 1: what a slide resolves to, asserted inside the document that resolves it.

The canvas is the interesting value here.
It cannot come from typst's own `auto` sizing, so animo computes it, and a computation
that is wrong by a centimetre is invisible in a rendering and obvious in a number.
Every slide publishes the canvas it settled on as metadata, which is the only channel
that reaches the paged and the HTML target alike.
"""

import pytest
from decks import PREAMBLE, deck
from harness import TypstRunner

# One centimetre of tolerance would hide every mistake worth catching,
# so the assertions are on hundredths of a centimetre and the text extents are measured,
# never guessed.
CHECK = """
#context {
  let canvases = query(<animo-canvas>).map(it => it.value)
  assert.eq(canvases.len(), COUNT, message: "slides: " + repr(canvases.len()))
  ASSERTIONS
}
"""


def canvas_check(*sizes: tuple[str, str]) -> str:
    """Assert the canvas of every slide in the document, in slide order.

    Each size is a pair of typst expressions for the expected width and height.
    """
    lines = []
    for index, (width, height) in enumerate(sizes):
        for axis, expected in (("width", width), ("height", height)):
            lines.append(
                f"assert.eq(\n"
                f"    canvases.at({index}).{axis}, {expected},\n"
                f'    message: "slide {index + 1} {axis}: "'
                f" + repr(canvases.at({index}).{axis}),\n"
                f"  )"
            )
    return CHECK.replace("COUNT", str(len(sizes))).replace("ASSERTIONS", "\n  ".join(lines))


@pytest.mark.parametrize("html", [False, True])
def test_a_slide_without_placements_has_canvas_equal_to_viewport(typst: TypstRunner, html):
    """The ordinary case, which the canvas concept may not make more expensive.

    Both targets are checked, because one canvas rule serving both is the invariant
    the four outputs rest on.
    """
    source = deck("slide[Just some in-flow text.]") + canvas_check(("16cm", "9cm"))
    typst.ok(source, html=html)


def test_a_top_level_placement_outside_the_viewport_grows_the_canvas(typst: TypstRunner):
    """The exact case: animo sees the offset the author wrote and adds what it holds.

    The expected width is the margin, plus the offset, plus the measured width of the
    placed content, so the assertion says the rule rather than a number read off a run.
    """
    body = "slide[#place(dx: 20cm, dy: 2cm)[#box(width: 3cm, height: 1cm)]]"
    source = deck(body) + canvas_check(("1cm + 20cm + 3cm", "9cm"))
    typst.ok(source)


def test_a_placement_taller_than_the_viewport_grows_the_canvas_downwards(typst: TypstRunner):
    """The same rule on the other axis, where the clamp to the viewport is what bites."""
    body = "slide[#place(dx: 1cm, dy: 12cm)[#box(width: 1cm, height: 2cm)]]"
    source = deck(body) + canvas_check(("16cm", "1cm + 12cm + 2cm"))
    typst.ok(source)


def test_an_aligned_placement_is_measured_from_the_edge_it_is_aligned_to(typst: TypstRunner):
    """`place(right, dx: ..)` starts at the right edge of the body, not at its origin.

    Ignoring the alignment would make this canvas 2 cm wide instead of 17 cm,
    which is the difference between a pan that works and one that goes nowhere.
    """
    body = "slide[#place(right, dx: 3cm)[#box(width: 2cm, height: 1cm)]]"
    # The body is the viewport less twice the margin, and the margin shifts it back.
    source = deck(body) + canvas_check(("1cm + (16cm - 2cm) + 3cm", "9cm"))
    typst.ok(source)


def test_a_nested_placement_is_counted_from_the_canvas_origin(typst: TypstRunner):
    """The approximate case, and the one worth pinning down because it is a choice.

    A placement inside a box reports its offset against that box, and the show rule
    cannot tell that apart from an offset against the slide body.
    Animo counts it anyway, from the canvas origin, which is short of the truth by
    wherever the box sits: the canvas comes out too small rather than too large,
    and `canvas:` is the override.
    """
    body = "slide[#box(width: 4cm, height: 2cm)[#place(dx: 20cm)[#box(width: 3cm, height: 1cm)]]]"
    source = deck(body) + canvas_check(("1cm + 20cm + 3cm", "9cm"))
    typst.ok(source)


def test_an_explicit_canvas_overrides_the_computed_one(typst: TypstRunner):
    """The escape hatch, which has to win even when the automatic rule would say more."""
    body = "slide(canvas: (width: 30cm, height: 20cm))[#place(dx: 40cm)[far]]"
    source = deck(body) + canvas_check(("30cm", "20cm"))
    typst.ok(source)


def test_an_explicit_canvas_is_still_at_least_the_viewport(typst: TypstRunner):
    """A canvas smaller than the viewport would leave part of the slide on nothing."""
    body = "slide(canvas: (width: 2cm, height: 1cm))[small]"
    source = deck(body) + canvas_check(("16cm", "9cm"))
    typst.ok(source)


def test_a_canvas_argument_that_is_not_a_size_is_refused(typst: TypstRunner):
    """The message has to name the argument, because `auto` and a dictionary look alike."""
    typst.fails(deck("slide(canvas: 5cm)[body]"), "canvas must be `auto`")


def test_the_deck_shape_reaches_every_slide(typst: TypstRunner):
    """The show rule is the only place the deck's shape is written, so it has to arrive."""
    source = deck("slide[a]", "slide[b]", width="20cm", height="15cm", margin="2cm") + canvas_check(
        ("20cm", "15cm"), ("20cm", "15cm")
    )
    typst.ok(source)


def test_a_deck_without_the_show_rule_still_has_slides(typst: TypstRunner):
    """A slide is usable on its own, at the defaults, which keeps the failure gentle."""
    source = PREAMBLE + "#slide[body]\n" + canvas_check(("16cm", "9cm"))
    typst.ok(source)


def test_a_margin_that_leaves_no_room_is_refused(typst: TypstRunner):
    """Without this the body gets a negative size and typst complains much later."""
    typst.fails(deck("slide[a]", margin="9cm"), "margin leaves no room")


# The counters.


COUNTS = """
#context {
  assert.eq(counter("animo-slide").final().first(), NUMBERED)
  assert.eq(counter("animo-position").final().first(), TOTAL)
}
"""


def test_numbered_counts_slides_and_position_counts_all_of_them(typst: TypstRunner):
    """`numbered:` decides only what the slide counter counts.

    Navigation and the DOM use the position instead, because a presenter walks through
    a title slide whether or not it carries a number.
    """
    source = deck(
        "slide[one]",
        "slide(numbered: false)[title]",
        "slide[two]",
    ) + COUNTS.replace("NUMBERED", "2").replace("TOTAL", "3")
    typst.ok(source)


# The arguments that phase 04 fills in.


def test_a_non_empty_animation_is_refused_for_now(typst: TypstRunner):
    """The signature is already the final one, so phase 04 does not change it.

    Until the timeline exists, a deck that hands one over must be told so rather than
    have it silently ignored.
    """
    typst.fails(
        deck("slide(animation: (1,))[body]"),
        "`animation` argument is not implemented yet",
    )


# The output mode.


@pytest.mark.parametrize("mode", ["handout", "presentation"])
def test_both_paged_modes_compile(typst: TypstRunner, mode):
    """`--input animo=` selects the paged output exactly as an ordinary user would."""
    typst.ok(deck("slide[body]"), sysinp={"animo": mode})


def test_an_unknown_paged_mode_is_refused(typst: TypstRunner):
    """A typo in the mode would otherwise produce a handout that looks like a success."""
    typst.fails(
        deck("slide[body]"),
        "--input animo= takes `handout` or `presentation`",
        sysinp={"animo": "handou"},
    )


# Backgrounds.


def test_a_background_that_is_neither_a_colour_nor_content_is_refused(typst: TypstRunner):
    """A gradient is a page fill on paper and nothing at all in the browser.

    Refusing it keeps the two targets identical, and the message says the form that
    does work in all four outputs.
    """
    typst.fails(
        deck("slide(background: gradient.linear(red, blue))[body]"),
        "background takes a colour or content",
    )
