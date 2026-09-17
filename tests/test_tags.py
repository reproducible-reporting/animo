# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tiers 1 and 2: what a tag site becomes, and where it leaves the content it holds.

Tier 1 asserts the structure inside the document that lays it out.
Tier 2 asserts in pixels that the structure costs the slide nothing,
which is the claim the wrapping decision exists for.

The wrapper a tag chose and the display state it applied are both readable with `query`,
because a tag emits a labelled wrapper holding `move(scale(..))` holding a wrapper.
So the whole path from the timeline through the resolver and the provider to the wrapper
is assertable without exporting anything, which is what tier 1 is for.

The wrapping decision is the part worth the most attention here.
It is a measurement rather than an inspection of element kinds, and the axis it decides is
hugging versus filling, so the expected answers are `box` and `block` and never `block`
at its natural width.
"""

import pytest
from decks import deck
from harness import PagedRunner, TypstRunner, assert_differs, assert_identical
from test_subslides import timeline

# The display state as the tag site emitted it, and the wrappers it emitted it in.
# `query` returns one element per tag site per page, in document order, which is what
# makes both the several-sites case and the several-states case readable from here.
# The outer slot holds the display state, and the inner slot sits inside that, so the path
# down from the label is `move`, `scale`, an optional `hide` and then the inner wrapper.
# On paper the outer slot holds the anchor a `pan(relto:)` reads before the display state,
# so `moved-of` looks past it.
SITE = """
#let moved-of(outer) = {
  let body = outer.body
  if repr(body.func()) == "sequence" { body.children.last() } else { body }
}
#let inner-of(outer) = {
  let shown = moved-of(outer).body.body
  if shown.func() == hide { shown.body } else { shown }
}
#let site(name, occurrence: 0) = {
  let outer = query(label(name)).at(occurrence)
  let moved = moved-of(outer)
  let scaled = moved.body
  (
    outer: repr(outer.func()),
    inner: repr(inner-of(outer).func()),
    dx: moved.dx,
    dy: moved.dy,
    factor: scaled.x,
    uniform: scaled.x == scaled.y,
    hidden: scaled.body.func() == hide,
  )
}
"""

IDENTITY = "(dx: 0pt, dy: 0pt, factor: 100%, uniform: true, hidden: false)"


def check(*assertions: str) -> str:
    """A context block asserting about the tag sites of the document."""
    body = "\n  ".join(assertions)
    return f"{SITE}\n#context {{\n  {body}\n}}\n"


# The wrapping decision.


# One case per body, so that a failure names the construct it disagrees about.
# The block-level ones are the constructs a slide is likely to hold, plus the body that is
# itself several paragraphs, which is the blind spot of the measurement.
BODIES = {
    "a phrase": ("[a phrase of several words]", "box"),
    "inline math": ("$x^2$", "box"),
    "a box": ("box[boxed]", "box"),
    "an empty body": ("[]", "box"),
    "a context block": ("context [conditional]", "box"),
    "a list": ("list([one], [two])", "block"),
    "a grid": ("grid(columns: 2)[a][b]", "block"),
    "a figure": ("figure(rect(), caption: [cap])", "block"),
    "block math": ("$ x^2 $", "block"),
    "a styled block": ("text(red, block[styled])", "block"),
    "two paragraphs": ("[one#parbreak()two]", "block"),
    "a context block that is block-level": ("context block[conditional]", "block"),
}


@pytest.mark.parametrize(("body", "wrapper"), BODIES.values(), ids=list(BODIES))
def test_wrap_auto_measures_whether_the_body_breaks_the_line(typst: TypstRunner, body, wrapper):
    """`wrap: auto` picks the hugging wrapper for inline content and the filling one else.

    A `figure` and a block equation are the cases that say why the filling wrapper is a
    `block(width: 100%)` rather than a `block`: a wrapper at its natural width hugs, and
    hugging left-aligns what the container was centring.
    """
    source = deck(f'slide[#tag("t", {body})]') + check(
        f'assert.eq(site("t").outer, "{wrapper}", message: site("t").outer)',
        'assert.eq(site("t").inner, site("t").outer)',
    )
    typst.ok(source)


def test_a_tag_inside_a_heading_wraps_its_text(typst: TypstRunner):
    """This is the way around the few points a wrapper around a whole heading costs.

    The body is then an inline phrase, so it hugs, and the heading keeps its own block
    spacing because no wrapper sits at its edge.
    """
    source = deck('slide[= #tag("t")[Head]]') + check(
        'assert.eq(site("t").outer, "box")',
    )
    typst.ok(source)


def test_the_filling_wrapper_is_a_block_at_the_full_width(typst: TypstRunner):
    """The width is the whole point of the decision, so it is asserted on its own."""
    source = deck('slide[#tag("t", list([one], [two]))]') + check(
        "assert.eq(query(<t>).first().width, 100%)",
        "assert.eq(inner-of(query(<t>).first()).width, 100%)",
    )
    typst.ok(source)


@pytest.mark.parametrize(
    ("wrap", "expected"),
    [("box", "box"), ("block", "block")],
)
def test_wrap_overrides_the_measurement_in_both_directions(typst: TypstRunner, wrap, expected):
    """A tagged phrase can be made to fill and a tagged list to hug, on request."""
    for body in ("[a phrase]", "list([one], [two])"):
        source = deck(f'slide[#tag("t", {body}, wrap: {wrap})]') + check(
            f'assert.eq(site("t").outer, "{expected}", message: site("t").outer)',
        )
        typst.ok(source)


def test_a_wrap_function_builds_the_inner_slot_and_the_outer_one_follows_it(
    typst: TypstRunner,
):
    """A wrapper that carries ink of its own moves and scales with the element.

    The outer slot has to be a plain wrapper of the same kind, because the inner one is
    where the ink is and the outer one is the boundary slot.
    """
    body = 'slide[#tag("t", [x], wrap: box.with(inset: 4pt, stroke: red))]'
    source = deck(body) + check(
        'assert.eq(site("t").outer, "box")',
        # An unset stroke is an empty dictionary of sides, so this says the outer
        # wrapper carries none of the ink the inner one was given.
        "assert.eq(query(<t>).first().stroke, (:))",
        "assert.eq(inner-of(query(<t>).first()).inset, 4pt)",
        "assert.ne(inner-of(query(<t>).first()).stroke, (:))",
    )
    typst.ok(source)


def test_a_wrap_none_tag_is_the_body_and_nothing_else(typst: TypstRunner):
    """No wrapper and no label, so there is no group and nothing to query."""
    source = deck('slide[#tag("t", [plain], wrap: none)]') + check(
        "assert.eq(query(<t>), ())",
    )
    typst.ok(source)


def test_a_tag_whose_body_is_not_content_is_refused_whatever_its_wrap(typst: TypstRunner):
    """A value that is not content is a value no primitive could ever reach.

    It carries no marker, so it reaches no view, and the timeline would do nothing to it in
    every output without saying so. `wrap: none` does not make it reachable either, which
    is why the refusal does not depend on the wrap.
    """
    for wrap in ("auto", "none"):
        typst.fails(
            deck(f'slide[#tag("t", (1, 2, 3), wrap: {wrap})]'),
            "the body of the tag t is not content, but array",
        )


# The structure a tag site emits.


def test_a_tag_site_is_two_nested_wrappers_with_the_label_on_the_outer_one(
    typst: TypstRunner,
):
    """Continuous state and boundary state each need a slot of their own.

    CSS gives an element one `translate` and one `scale`, so without this nesting the
    crossfade and the morph would clobber `move` and `scale`.
    """
    source = deck('slide[#tag("t")[word]]') + check(
        "assert.eq(query(<t>).len(), 1)",
        'assert.eq(site("t").outer, "box")',
        'assert.eq(site("t").inner, "box")',
        "assert.eq(moved-of(query(<t>).first()).func(), move)",
        "assert.eq(moved-of(query(<t>).first()).body.func(), scale)",
        "assert.eq(moved-of(query(<t>).first()).body.reflow, false)",
        # The anchor of a `pan(relto:)`, first in the outer slot and outside the inner one,
        # so that the tag's own display state does not move it.
        "assert.eq(query(<t>).first().body.children.first().func(), place)",
    )
    typst.ok(source)


def test_a_tag_nothing_addresses_emits_the_identity(typst: TypstRunner):
    """The structure is the same in every state, and only the parameters change.

    That is what keeps a slide's states laying out identically, since `move`, `scale` and
    `hide` between the tag's two slots are layout-neutral.
    """
    source = deck('slide[#tag("t")[word]]') + check(
        f'assert.eq(site("t") + (outer: none, inner: none), {IDENTITY} + '
        "(outer: none, inner: none))",
    )
    typst.ok(source)


def test_a_tag_whose_first_display_operation_reveals_it_starts_hidden(typst: TypstRunner):
    """Nothing at the site says so: the timeline is where the initial state is read."""
    animation = timeline('sub(reveal("t"))')
    source = deck(f'slide(animation: {animation})[#tag("t")[word]]') + check(
        'assert.eq(site("t", occurrence: 0).hidden, true)',
        'assert.eq(site("t", occurrence: 1).hidden, false)',
    )
    typst.ok(source, sysinp={"animo": "presentation"})


def test_a_tag_whose_first_display_operation_hides_it_starts_visible(typst: TypstRunner):
    """The other order, which is the case the inference must not catch."""
    animation = timeline('sub(hide("t"))', 'sub(reveal("t"))')
    source = deck(f'slide(animation: {animation})[#tag("t")[word]]') + check(
        'assert.eq(site("t", occurrence: 0).hidden, false)',
        'assert.eq(site("t", occurrence: 1).hidden, true)',
        'assert.eq(site("t", occurrence: 2).hidden, false)',
    )
    typst.ok(source, sysinp={"animo": "presentation"})


def test_a_reveal_that_undoes_nothing_still_makes_the_tag_start_hidden(typst: TypstRunner):
    """The accepted cost of the inference, pinned so that it cannot change unnoticed.

    A `reveal` on a name that nothing hides used to be a no-op, and now it says that the
    name starts hidden. Animo refuses no timeline over it, because every timeline has a
    reading, so this is the one place where a mistake surfaces as a missing element
    rather than as a message.
    """
    animation = timeline('sub(reveal("t"), reveal("t"))')
    source = deck(f'slide(animation: {animation})[#tag("t")[word]]') + check(
        'assert.eq(site("t", occurrence: 0).hidden, true)',
    )
    typst.ok(source, sysinp={"animo": "presentation"})


# The plan reaching the tag sites.


def test_every_state_puts_its_own_display_state_on_the_tag_site(typst: TypstRunner):
    """The presentation renders one page per state, so `query` sees them in order.

    This is the assertion that the whole path works: the timeline is resolved, the result
    is provided to the body, and the tag site applies the state it was handed.
    """
    animation = (
        "{ import anim: *\n"
        '  sub(move("t", dx: 1cm, dy: 2mm))\n'
        '  sub(scale("t", f: 2), hide("t"))\n'
        '  sub(move("t", dx: 1cm), reveal("t")) }'
    )
    source = deck(f'slide(animation: {animation})[#tag("t")[word]]') + check(
        "assert.eq(query(<t>).len(), 4)",
        f'assert.eq(site("t", occurrence: 0), {IDENTITY} + (outer: "box", inner: "box"))',
        'assert.eq(site("t", occurrence: 1).dx, 1cm)',
        'assert.eq(site("t", occurrence: 1).dy, 2mm)',
        'assert.eq(site("t", occurrence: 2).factor, 200%)',
        'assert.eq(site("t", occurrence: 2).hidden, true)',
        'assert.eq(site("t", occurrence: 3).dx, 2cm)',
        'assert.eq(site("t", occurrence: 3).factor, 200%)',
        'assert.eq(site("t", occurrence: 3).hidden, false)',
    )
    typst.ok(source, sysinp={"animo": "presentation"})


def test_several_sites_with_one_name_are_addressed_together(typst: TypstRunner):
    """The same name in one slide is one element as far as the timeline is concerned."""
    animation = '{ import anim: *\n  sub(move("t", dx: 1cm)) }'
    body = f'slide(animation: {animation})[#tag("t")[one] and #tag("t")[two]]'
    source = deck(body) + check(
        "assert.eq(query(<t>).len(), 2)",
        'assert.eq(site("t", occurrence: 0).dx, 1cm)',
        'assert.eq(site("t", occurrence: 1).dx, 1cm)',
    )
    typst.ok(source)


def test_the_same_name_in_two_slides_resolves_independently(typst: TypstRunner):
    """Tags are scoped to their slide, and this is what that means in the paged output.

    The view is an argument of the slide rather than a position in the document, so the
    second slide's timeline cannot reach the first slide's tag.
    """
    first = '{ import anim: *\n  sub(move("t", dx: 1cm)) }'
    second = '{ import anim: *\n  sub(scale("t", f: 3)) }'
    source = deck(
        f'slide(animation: {first})[#tag("t")[one]]',
        f'slide(animation: {second})[#tag("t")[two]]',
    ) + check(
        "assert.eq(query(<t>).len(), 2)",
        'assert.eq(site("t", occurrence: 0).dx, 1cm)',
        'assert.eq(site("t", occurrence: 0).factor, 100%)',
        'assert.eq(site("t", occurrence: 1).dx, 0pt)',
        'assert.eq(site("t", occurrence: 1).factor, 300%)',
    )
    typst.ok(source)


def test_a_deck_that_wraps_slide_in_its_own_function_still_reaches_its_tags(
    typst: TypstRunner,
):
    """This is the case the show-rule question was really about.

    A recurring element is a `#place` inside a wrapper around `#slide`, which is animo's
    answer to headers and footers, so the plan may not depend on where `#slide` is called
    from. It does not: the view is provided lexically to the body it was given.
    """
    animation = '{ import anim: *\n  sub(move("t", dx: 1cm)) }'
    source = deck(
        "mine(animation: " + animation + ')[#tag("t")[word]]',
    ).replace(
        "#mine(",
        "#let mine(body, ..args) = slide(..args)[\n"
        "  #place(bottom + right)[a placed corner mark]\n"
        "  #body\n"
        "]\n#mine(",
    ) + check('assert.eq(site("t").dx, 1cm)')
    typst.ok(source)


def test_the_html_target_applies_no_display_state_yet(typst: TypstRunner):
    """A frame covers a whole run of states, so the browser is what applies them.

    Until the runtime exists, the HTML output shows every tag at the identity, a tag
    that starts hidden included, which the manual says.
    """
    animation = '{ import anim: *\n  sub(reveal("t"))\n  sub(move("t", dx: 1cm), hide("t")) }'
    body = f'slide(animation: {animation})[#tag("t")[word]]'
    source = deck(body) + check(
        "assert.eq(query(<t>).len(), 1)",
        f'assert.eq(site("t") + (outer: none, inner: none), {IDENTITY} + '
        "(outer: none, inner: none))",
    )
    typst.ok(source, html=True)


# The failures, each by its message.


def test_a_tag_outside_a_slide_is_refused(typst: TypstRunner):
    """A marker nobody replaced is invisible, so the tag's content would simply vanish.

    `query` cannot tell a replaced marker from a leftover, so this has to be diagnosed at
    the tag site, from a state the slide sets around its body.
    """
    typst.fails(
        deck("slide[fine]") + '\n#tag("loose")[outside]\n',
        "the tag loose is not inside a #slide",
    )


def test_the_refusal_of_a_body_that_is_not_content_says_what_to_do_instead(
    typst: TypstRunner,
):
    """The message has to name both ways out, because this is the cetz case."""
    result = typst.fails(
        deck('slide[#tag("t", (1, 2, 3))]'),
        "the body of the tag t is not content, but array",
    )
    assert "tag a cetz content() element" in result.stderr
    assert "tag the whole canvas" in result.stderr


def test_a_continuous_primitive_on_a_wrap_none_tag_is_refused(typst: TypstRunner):
    """Without a label there is no group, so the browser would silently do nothing.

    Failing here rather than in the browser much later is the reason a tag knows which
    names the timeline animates anywhere in the slide, and not only in its own state.
    """
    animation = '{ import anim: *\n  sub(move("t", dx: 1cm)) }'
    typst.fails(
        deck(f'slide(animation: {animation})[#tag("t", [x], wrap: none)]'),
        "the timeline addresses the tag t with a continuous primitive",
    )


def test_a_wrap_function_that_produces_no_container_is_refused(typst: TypstRunner):
    """Nothing but a box or a block becomes an addressable group in the output."""
    typst.fails(
        deck('slide[#tag("t", [x], wrap: rect.with(stroke: red))]'),
        "the wrap function of the tag t produced a rect",
    )


def test_a_wrap_value_that_is_none_of_the_forms_is_refused(typst: TypstRunner):
    """`wrap: true` is the shape of the mistake left behind by the earlier `block:`."""
    typst.fails(
        deck('slide[#tag("t", [x], wrap: true)]'),
        "the wrap argument of the tag t takes auto, box, block, none or a function",
    )


NO_GROUP = "the timeline of slide 2 addresses nowhere with a continuous primitive"


@pytest.mark.parametrize(
    "target",
    [{"sysinp": {"animo": "handout"}}, {"sysinp": {"animo": "presentation"}}, {"html": True}],
    ids=["handout", "presentation", "html"],
)
def test_a_continuous_primitive_on_a_name_the_slide_does_not_tag_is_refused(
    typst: TypstRunner, target
):
    """The two targets would answer it differently, so neither is allowed to answer it.

    Typst finds no site and the paged outputs do nothing, while the browser addresses a
    group by its label and any group of that name will do, including one the document
    labelled itself. A misspelt name is the likely cause and a silent no-op would hide it.

    The check depends on `query`, which is what can swallow a panic (see *Findings*), so
    the assertion is on the message itself, on the second slide of a deck that goes on
    after it, and on the absence of the second error the swallowing would bring along.
    """
    animation = timeline('sub(reveal("nowhere"))')
    source = deck(
        'slide[#tag("here")[here]]',
        f'slide(animation: {animation})[#tag("here")[here]]',
        'slide[#tag("after")[after]]',
    )
    result = typst.fails(source, NO_GROUP, **target)
    assert "not inside a #slide" not in result.stderr, result.stderr
    assert "did not converge" not in result.stderr, result.stderr


def test_a_tag_of_that_name_on_another_slide_does_not_answer_for_it(typst: TypstRunner):
    """A name is scoped to its own slide, and a continuous primitive is scoped with it."""
    animation = timeline('sub(move("nowhere", dx: 1cm))')
    source = deck(
        'slide[#tag("nowhere")[on another slide]]',
        f'slide(animation: {animation})[#tag("here")[here]]',
    )
    typst.fails(source, NO_GROUP, html=True)
    typst.fails(source, NO_GROUP)


def test_a_label_of_the_documents_own_is_not_a_tag_site(typst: TypstRunner):
    """The case this refusal exists for, and the one the browser would otherwise answer.

    `readSlide` in the runtime indexes every `[data-typst-label]` of a slide, because that
    is what a tag site becomes, and a label the document wrote itself is the same thing in
    the DOM. Without this check the browser moves it and the paged outputs do not.
    """
    animation = timeline('sub(move("nowhere", dx: 3cm))')
    source = deck(
        'slide[#tag("here")[here]]',
        f'slide(animation: {animation})[A paragraph with #box[a labelled box]<nowhere>.]',
    )
    result = typst.fails(source, NO_GROUP, html=True)
    assert "a label the document wrote itself is not a tag site" in result.stderr


def test_a_move_relative_to_a_tag_the_slide_does_not_have_is_refused(typst: TypstRunner):
    """The same refusal a `pan(relto:)` raises, and the message names the primitive.

    It is the same mistake for the same reason: a misspelt name is the likely cause, and a
    silent fallback would leave the element where it was in both targets.
    """
    animation = timeline('sub(move("here", relto: "nowhere"))')
    source = deck(f'slide(animation: {animation})[#tag("here")[here]]')
    for target in ({"html": True}, {}):
        result = typst.fails(
            source,
            "a move on slide 1 is relative to the tag nowhere, "
            "but that slide has no tag of that name",
            **target,
        )
        assert "did not converge" not in result.stderr, result.stderr


def test_a_move_relative_to_a_tag_without_a_wrapper_is_refused(typst: TypstRunner):
    """With no group there is no corner, in the browser as on paper."""
    animation = timeline('sub(move("here", relto: "plain"))')
    result = typst.fails(
        deck(
            f'slide(animation: {animation})'
            '[#tag("here")[here] #tag("plain", [x], wrap: none)]'
        ),
        "the timeline addresses the tag plain with a continuous primitive",
    )
    assert "its wrap is none" in result.stderr


BELOW = "reads the anchor of the tag inner, which sits inside the tag outer"

NESTED = (
    '#place(dx: 2cm, dy: 2cm, tag("outer", wrap: box)'
    '[before #tag("inner")[middle] after])'
)


@pytest.mark.parametrize(
    "target",
    [{"sysinp": {"animo": "handout"}}, {"sysinp": {"animo": "presentation"}}, {"html": True}],
    ids=["handout", "presentation", "html"],
)
@pytest.mark.parametrize(
    "step",
    ['move("outer", relto: "inner")', 'pan(relto: "inner")', 'move("inner", x: 1cm)'],
    ids=["a move relative to it", "a pan relative to it", "its own absolute move"],
)
def test_an_anchor_inside_a_transformed_tag_is_refused(typst: TypstRunner, step, target):
    """No rendering can read such an anchor as the design says an anchor is read.

    An anchor is the corner the body gave a tag, and a `move` or a `scale` on a tag around
    it moves that corner. The presentation and the browser still read an untransformed
    layout, the first from its own first page and the second from the slide before anything
    is written on it, while a handout reads whichever page it keeps. So the three would
    disagree, which is what the refusal is for, and `move("outer", relto: "inner")` would
    not even converge: the anchor it reads is one its own translation moves.

    Refused in every output type and for every way of reading the anchor, because a refusal
    that depended on the mode compiled would be worse than the disagreement it prevents.

    The message being reported is the whole assertion. A check that reads `query` can have
    its panic swallowed (see *Findings*), and a swallowed one leaves no message behind;
    the handout of the first case also warns that it did not converge, which is the cycle
    itself and is exactly what the refusal is there to stop an author from shipping.
    """
    animation = timeline('sub(move("outer", dx: 1cm))', f"sub({step})")
    typst.fails(deck(f"slide(animation: {animation})[{NESTED}]"), BELOW, **target)


def test_a_tag_inside_a_tag_that_is_only_revealed_keeps_its_anchor(typst: TypstRunner):
    """`reveal` and `hide` move nothing, so an anchor below one is still the body's own."""
    animation = timeline('sub(hide("outer"))', 'sub(pan(relto: "inner"))')
    typst.ok(deck(f"slide(animation: {animation})[{NESTED}]"))


def test_a_tag_inside_a_transformed_tag_is_fine_until_an_anchor_is_read(typst: TypstRunner):
    """The refusal is about reading the anchor, not about the nesting.

    A tag inside a moved tag is the ordinary way to move a group and light up a part of it,
    and nothing about that needs an anchor.
    """
    animation = timeline('sub(move("outer", dx: 1cm), reveal("inner"))')
    typst.ok(deck(f"slide(animation: {animation})[{NESTED}]"))


def test_a_tag_inside_a_moved_region_is_refused_for_the_same_reason(typst: TypstRunner):
    """A named region carries a display state too, so it encloses what it holds."""
    animation = timeline('sub(move("r", dx: 1cm))', 'sub(pan(relto: "t"))')
    typst.fails(
        deck(f'slide(animation: {animation})[#region(name: "r")[#tag("t")[inside]]]'),
        "reads the anchor of the tag t, which sits inside the tag r",
    )


def test_a_named_region_answers_for_a_continuous_primitive(typst: TypstRunner):
    """A named region is a site of its name, so the check is about groups and not about tags."""
    animation = timeline('sub(move("r", dx: 1cm))')
    source = deck(f'slide(animation: {animation})[#region(name: "r")[inside]]')
    typst.ok(source, html=True)
    typst.ok(source)


def test_a_wrap_none_tag_keeps_its_own_refusal(typst: TypstRunner):
    """Such a tag became no group, so both refusals are true and its own says what to do.

    They come from different blocks, so typst reports both. The one worth reading is the
    one at the tag site, which names the wrap.
    """
    animation = timeline('sub(move("t", dx: 1cm))')
    result = typst.fails(
        deck(f'slide(animation: {animation})[#tag("t", [x], wrap: none)]'),
        "the timeline addresses the tag t with a continuous primitive",
    )
    assert "its wrap is none" in result.stderr


def test_a_tag_name_that_is_not_a_string_is_refused(typst: TypstRunner):
    """A label would work in typst and not in the browser, where the name is an attribute."""
    typst.fails(deck("slide[#tag(<t>, [x])]"), "a tag takes its name as a string")


# Tier 2: where the tag site leaves what it holds.


# Bodies the slide centres by itself, one per construct that does the centring differently.
# Each is block-level, so `wrap: auto` chooses the filling block for all three.
CENTRED = {
    "block math": "$ x^2 + y^2 = z^2 $",
    "a figure": "figure(rect(width: 3cm, height: 1cm), caption: [Cap])",
    "an aligned phrase": "align(center)[a centred phrase]",
}


def between_paragraphs(body: str, animation: str = "") -> str:
    """A one-slide deck holding the body between two paragraphs."""
    timeline = f"(animation: {animation})" if animation else ""
    return deck(f"slide{timeline}[\n  Before.\n\n  {body}\n\n  After the body.\n]")


@pytest.mark.parametrize("body", CENTRED.values(), ids=list(CENTRED))
def test_a_tag_leaves_centred_content_where_the_slide_put_it(paged: PagedRunner, body):
    """The filling wrapper only fills when the display state is outside it.

    A display state at rest is a `move` of nothing and a `scale` of one, and a `move` is
    laid out as an inline element, so a filling block inside one fills the paragraph the
    `move` opened rather than the container. A block equation, a figure and an `align`
    would all be left-aligned by a tag that nested the two the other way round.
    """
    plain = paged.png(between_paragraphs("#" + body))[0]
    tagged = paged.png(between_paragraphs(f'#tag("t", {body})'))[0]
    # The one greyscale step a fractional position rounds to, as *Findings* records.
    assert_identical(plain, tagged, tol=1, what=f"a tag around {body}")


@pytest.mark.parametrize("body", CENTRED.values(), ids=list(CENTRED))
def test_the_wrap_of_a_tag_decides_whether_centred_content_stays_centred(
    paged: PagedRunner,
    body,
):
    """Which is what makes the test above a measurement rather than a tautology.

    `wrap: box` hugs and `wrap: block` fills, and the two have to disagree on a centred
    body for the wrapping decision to mean anything at the tag site.
    """
    hugging = paged.png(between_paragraphs(f'#tag("t", {body}, wrap: box)'))[0]
    filling = paged.png(between_paragraphs(f'#tag("t", {body}, wrap: block)'))[0]
    assert_differs(hugging, filling, what=f"box against block around {body}")


@pytest.mark.parametrize("body", CENTRED.values(), ids=list(CENTRED))
def test_a_moved_tag_leaves_centred_content_centred_in_every_other_state(
    paged: PagedRunner,
    body,
):
    """A tag the timeline moves is at rest in its first state, and lays out as such.

    The test above holds the tag at rest in every state, so it says nothing about a tag
    whose display state is the identity in one state and not in another. Here the timeline
    moves the tag, and the state before the move has to be the untagged slide.
    """
    animated = between_paragraphs(f'#tag("t", {body})', timeline('sub(move("t", dx: 2cm))'))
    plain = paged.png(between_paragraphs("#" + body))[0]
    pages = paged.png(animated, mode="presentation")
    assert len(pages) == 2
    assert_identical(plain, pages[0], tol=1, what=f"the first state of a moved {body}")
    assert_differs(pages[0], pages[1], what=f"the two states of a moved {body}")
