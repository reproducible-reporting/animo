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


# A timeline that pans, which is what makes a slide record its placements.
# The canvas is read by `pan` and by nothing else, so a slide whose timeline never pans
# takes the viewport clamped to its body box and records nothing.
# One centimetre, because how far it pans decides nothing here.
PANS = "animation: {import anim: *\nsub(pan(dx: 1cm))}, "


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
    the three output types rest on.
    """
    source = deck("slide[Just some in-flow text.]") + canvas_check(("16cm", "9cm"))
    typst.ok(source, html=html)


@pytest.mark.parametrize("html", [False, True])
def test_a_slide_that_never_pans_takes_the_viewport_whatever_it_places(
    typst: TypstRunner, html
):
    """The canvas of such a slide is unobservable, so animo does not pay to compute it.

    `pan` is the only reader of the canvas, and the viewport clips in both targets, so a
    slide with no pan in its timeline is drawn the same whatever canvas it gets. The
    second slide is the control: the same placement with a pan does grow the canvas, so
    this is about the timeline and not about the placement.
    """
    body = "[#place(dx: 20cm, dy: 2cm)[#box(width: 3cm, height: 1cm)]]"
    source = deck(f"slide{body}", f"slide({PANS}){body}") + canvas_check(
        ("16cm", "9cm"), ("1cm + 20cm + 3cm", "9cm")
    )
    typst.ok(source, html=html)


def test_a_top_level_placement_outside_the_viewport_grows_the_canvas(typst: TypstRunner):
    """The exact case: animo sees the offset the author wrote and adds what it holds.

    The expected width is the margin, plus the offset, plus the measured width of the
    placed content, so the assertion says the rule rather than a number read off a run.
    """
    body = f"slide({PANS})[#place(dx: 20cm, dy: 2cm)[#box(width: 3cm, height: 1cm)]]"
    source = deck(body) + canvas_check(("1cm + 20cm + 3cm", "9cm"))
    typst.ok(source)


def test_a_placement_taller_than_the_viewport_grows_the_canvas_downwards(typst: TypstRunner):
    """The same rule on the other axis, where the clamp to the viewport is what bites."""
    body = f"slide({PANS})[#place(dx: 1cm, dy: 12cm)[#box(width: 1cm, height: 2cm)]]"
    source = deck(body) + canvas_check(("16cm", "1cm + 12cm + 2cm"))
    typst.ok(source)


def test_an_aligned_placement_is_measured_from_the_edge_it_is_aligned_to(typst: TypstRunner):
    """`place(right, dx: ..)` starts at the right edge of the body, not at its origin.

    Ignoring the alignment would make this canvas 2 cm wide instead of 17 cm,
    which is the difference between a pan that works and one that goes nowhere.
    """
    body = f"slide({PANS})[#place(right, dx: 3cm)[#box(width: 2cm, height: 1cm)]]"
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
    inner = "#place(dx: 20cm)[#box(width: 3cm, height: 1cm)]"
    body = f"slide({PANS})[#box(width: 4cm, height: 2cm)[{inner}]]"
    source = deck(body) + canvas_check(("1cm + 20cm + 3cm", "9cm"))
    typst.ok(source)


def test_an_aligned_placement_inside_a_narrow_container_is_counted_long(typst: TypstRunner):
    """The other direction of the approximation, which is worth pinning because it surprises.

    The alignment is resolved against the body box, since that is the only container the
    rule knows, so a placement aligned to the right edge of a 2 cm box is counted from the
    right edge of the 14 cm body instead: 20 cm of canvas where 9 cm would hold the ink.
    An over-large canvas costs nothing until somebody pans onto the empty part of it,
    and `canvas:` is the override there as everywhere else.
    """
    inner = "#place(right, dx: 5cm)[#box(width: 1cm, height: 1cm)]"
    body = f"slide({PANS})[#box(width: 2cm, height: 1cm)[{inner}]]"
    source = deck(body) + canvas_check(("1cm + (16cm - 2cm) + 5cm", "9cm"))
    typst.ok(source)


def test_a_ratio_sized_placement_is_counted_short(typst: TypstRunner):
    """The union is not exact even for a top-level placement, and this is why.

    The rule measures the placed body without a container to resolve a ratio against, so
    `rect(width: 100%, height: 100%)` reports nothing and adds nothing. The second slide
    is the control: the same rectangle at an absolute size does grow the canvas, so the
    first is about the ratio and not about the placement.
    """
    ratio = f"slide({PANS})[#place(dx: 2cm, rect(width: 100%, height: 100%))]"
    absolute = f"slide({PANS})[#place(dx: 2cm, rect(width: 16cm, height: 9cm))]"
    source = deck(ratio, absolute) + canvas_check(
        ("16cm", "9cm"), ("1cm + 2cm + 16cm", "1cm + 9cm")
    )
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


@pytest.mark.parametrize(
    ("argument", "message"),
    [
        ("primitive-duration: -1", "takes primitive-duration as a number of seconds"),
        ('transition-duration: "0.4s"', "takes transition-duration as a number of seconds"),
        ('easing: "swoosh"', "takes easing as one of"),
    ],
)
def test_a_tempo_the_browser_could_not_take_is_refused(
    typst: TypstRunner, argument: str, message: str
):
    """A value that reaches the page unchecked fails in front of an audience instead.

    A duration is a number of seconds like every other time an author writes, and an
    easing is one of the five names the reference lists, so both are refusable here.
    The paged target checks them too, which is why this is a tier 1 test: a deck that
    compiles to a PDF has to compile to a presentation as well.
    """
    typst.fails(deck("slide[a]", timing=argument), message)


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


# The transition between two slides.

# A slide with ink of its own, so that a comparison of two renderings is about a page
# that holds something rather than about an empty one.
ENTERED = 'slide(BEFOREbackground: rgb("#204080"))[\n  = A slide\n  With a line of text.\n]'


@pytest.mark.parametrize("html", [False, True])
@pytest.mark.parametrize("value", ["auto", "none", '"crossfade"'])
def test_a_transition_takes_auto_none_or_a_strategy(typst: TypstRunner, value, html):
    """A strategy may be named, so a richer one later is a value added and not a type changed."""
    typst.ok(deck(ENTERED.replace("BEFORE", f"transition: {value}, ")), html=html)


@pytest.mark.parametrize("html", [False, True])
def test_a_transition_that_is_none_of_them_is_refused(typst: TypstRunner, html):
    """A misspelt transition would otherwise be a slide that quietly keeps the default.

    Typst refuses it rather than the runtime, because the runtime has no way to report it
    and a name it did not recognise would fall back to the deck's own strategy.
    """
    typst.fails(
        deck(ENTERED.replace("BEFORE", 'transition: "fade", ')),
        "transition takes `auto`",
        html=html,
    )


@pytest.mark.parametrize("mode", ["handout", "presentation"])
@pytest.mark.parametrize("value", ["auto", "none", '"crossfade"'])
def test_a_transition_leaves_the_paged_outputs_byte_identical(typst: TypstRunner, value, mode):
    """"Ignored in the paged outputs" means the bytes and not merely the look.

    Two consecutive pages have nothing between them to describe, so a transition may not
    reach either paged output at all. SVG rather than PDF, because a PDF carries the
    moment it was written and two compilations of one document therefore differ in it.
    """
    plain = typst.svg(
        deck(ENTERED.replace("BEFORE", "")),
        name=f"plain-{value}-{mode}.svg",
        sysinp={"animo": mode},
    )
    stated = typst.svg(
        deck(ENTERED.replace("BEFORE", f"transition: {value}, ")),
        name=f"stated-{value}-{mode}.svg",
        sysinp={"animo": mode},
    )
    assert stated == plain


def test_a_transition_reaches_the_html_output(typst: TypstRunner):
    """The control for the byte-identity above, which would otherwise pass on an argument
    that animo ignored everywhere.

    It travels as one attribute per slide rather than as an entry in the plan, for the
    reason the plan itself is an attribute: an inspector shows it beside the slide.
    """
    page = typst.html(
        deck(ENTERED.replace("BEFORE", "transition: none, "), ENTERED.replace("BEFORE", "")),
        name="transition.html",
    ).read_text()
    assert page.count('data-animo-transition="none"') == 1
    assert page.count('data-animo-transition="auto"') == 1


def test_a_named_strategy_travels_as_its_name(typst: TypstRunner):
    """`auto` stays `auto` rather than resolving to the deck's own strategy in typst.

    Which strategy `auto` means is the runtime's constant, so resolving it here would put
    the same answer in two places and let them drift.
    """
    page = typst.html(
        deck(ENTERED.replace("BEFORE", 'transition: "crossfade", ')),
        name="strategy.html",
    ).read_text()
    assert page.count('data-animo-transition="crossfade"') == 1


# The arguments a later version fills in.


def test_a_timeline_that_is_not_one_is_refused_by_the_slide(typst: TypstRunner):
    """The slide hands its argument to the resolver before it lays out its body.

    What a timeline may hold is asserted in `test_plan.py`; this is the one assertion
    that `#slide` is on that path at all rather than ignoring the argument.
    """
    typst.fails(
        deck("slide(animation: (1,))[body]"),
        "step 1 of the animation argument is not a sub(..) call",
    )


# The handout flag of the initial state.


def test_the_slide_takes_the_handout_flag_of_its_initial_state(typst: TypstRunner):
    """What it resolves to is asserted in `test_plan.py`; this is the one assertion that
    `#slide` is on that path at all rather than ignoring the argument."""
    typst.ok(deck("slide(handout: true)[body]", "slide(handout: false)[body]"))


def test_a_handout_flag_on_a_slide_that_is_not_a_flag_is_refused(typst: TypstRunner):
    """The message names the slide rather than `sub`, because the two flags are written in
    different places and a reader of the message is looking at one of them."""
    typst.fails(
        deck("slide(handout: 1)[body]"),
        "the handout argument of slide takes auto, true or false",
    )


def test_a_handout_that_holds_no_page_at_all_is_refused(typst: TypstRunner):
    """Typst does not refuse a document without pages: it emits one blank page of its own
    default size, which looks like a rendering failure rather than like the flag doing
    what it was told. So the deck says what really happened."""
    typst.fails(
        deck("slide(handout: false)[body]", "slide(handout: false)[body]"),
        "every state of this deck gave up its handout page",
    )


def test_one_page_anywhere_is_enough_for_the_deck(typst: TypstRunner):
    """The refusal is about the whole handout, so a slide that contributes nothing is
    not a mistake as long as another one does."""
    typst.ok(deck("slide(handout: false)[body]", "slide[body]"))


def test_a_handout_that_holds_no_page_is_only_refused_in_the_handout(typst: TypstRunner):
    """The presentation renders every state whatever the flags say, and the HTML output
    has no pages to give up."""
    source = deck("slide(handout: false)[body]")
    typst.ok(source, sysinp={"animo": "presentation"})
    typst.ok(source, html=True)


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


# The two outer layers.

# A placement far enough outside the viewport that counting it would double the canvas.
# Absolute rather than a ratio, because an unbounded `measure` resolves a ratio to zero
# and a full-bleed layer would therefore pass this test without saying anything.
FAR = "#place(dx: 20cm, dy: 2cm, box(width: 3cm, height: 1cm))"

# What an overlay really holds, which is the case the canvas rule has to survive.
CORNER = "#place(bottom + right, dx: -1cm, dy: -1cm, box(width: 2cm, height: 1cm))"


@pytest.mark.parametrize("which", ["background", "overlay"])
def test_a_layer_that_is_neither_a_colour_nor_content_is_refused(typst: TypstRunner, which):
    """A gradient is a page fill on paper and nothing at all in the browser.

    Refusing it keeps the two targets identical, and the message says the form that
    does work in all three output types.
    """
    typst.fails(
        deck(f"slide({which}: gradient.linear(red, blue))[body]"),
        f"{which} takes a colour or content",
    )


@pytest.mark.parametrize("html", [False, True])
@pytest.mark.parametrize("site", ['tag("t")[x]', "region[x]", 'region(name: "r")[x]'])
@pytest.mark.parametrize("which", ["background", "overlay"])
def test_a_tag_or_a_region_in_a_layer_is_refused(typst: TypstRunner, which, site, html):
    """Neither layer is addressable, so a tag there is a step that would do nothing.

    It cannot be diagnosed afterwards, because a marker nobody replaced is
    indistinguishable from one that was, so it is refused where it is written,
    in both targets, and the message names the argument it came from.
    """
    result = typst.fails(
        deck(f"slide({which}: [#{site}])[body]"),
        f"is in the {which} of slide 1",
        html=html,
    )
    assert "belongs to the viewport rather than to the body" in result.stderr


@pytest.mark.parametrize("html", [False, True])
def test_neither_layer_enters_the_automatic_canvas(typst: TypstRunner, html):
    """A full-bleed background may not make the body pannable by accident.

    The third slide is the control: the same placements in the *body* do grow the canvas,
    without which the first two would pass on a rule that counts nothing at all.
    """
    source = deck(
        f"slide({PANS})[plain]",
        f"slide({PANS}background: [{FAR}{CORNER}], overlay: [{FAR}{CORNER}])[plain]",
        f"slide({PANS})[plain {FAR}]",
    ) + canvas_check(("16cm", "9cm"), ("16cm", "9cm"), ("1cm + 20cm + 3cm", "9cm"))
    typst.ok(source, html=html)
