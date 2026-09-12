# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 1: what a tag site becomes, asserted inside the document that lays it out.

The wrapper a tag chose and the display state it applied are both readable with `query`,
because a tag emits a labelled wrapper holding a wrapper holding `move(scale(..))`.
So the whole path from the timeline through the resolver and the provider to the wrapper
is assertable without exporting anything, which is what this tier is for.

The wrapping decision is the part worth the most attention here.
It is a measurement rather than an inspection of element kinds, and the axis it decides is
hugging versus filling, so the expected answers are `box` and `block` and never `block`
at its natural width.
"""

import pytest
from decks import deck
from harness import TypstRunner

# The display state as the tag site emitted it, and the wrappers it emitted it in.
# `query` returns one element per tag site per page, in document order, which is what
# makes both the several-sites case and the several-states case readable from here.
SITE = """
#let site(name, occurrence: 0) = {
  let outer = query(label(name)).at(occurrence)
  let inner = outer.body
  let moved = inner.body
  let scaled = moved.body
  (
    outer: repr(outer.func()),
    inner: repr(inner.func()),
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
        "assert.eq(query(<t>).first().body.width, 100%)",
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
        "assert.eq(query(<t>).first().body.inset, 4pt)",
        "assert.ne(query(<t>).first().body.stroke, (:))",
    )
    typst.ok(source)


def test_a_wrap_none_tag_is_the_body_and_nothing_else(typst: TypstRunner):
    """No wrapper and no label, so there is no group and nothing to query."""
    source = deck('slide[#tag("t", [plain], wrap: none)]') + check(
        "assert.eq(query(<t>), ())",
    )
    typst.ok(source)


def test_a_tag_whose_body_is_not_content_is_handed_back_unchanged(typst: TypstRunner):
    """This is the form a stream of raw draw commands takes, and it has to survive.

    Nothing else can be done with it: a value that is not content cannot carry a marker,
    so such a tag reaches no view and animo knows nothing about it.
    """
    source = deck(
        'slide[#let commands = (1, 2, 3)\n  #assert.eq(tag("t", commands, wrap: none), commands)]'
    ) + check("assert.eq(query(<t>), ())")
    typst.ok(source)


# The structure a tag site emits.


def test_a_tag_site_is_two_nested_wrappers_with_the_label_on_the_outer_one(
    typst: TypstRunner,
):
    """Continuous state and boundary state each need a slot of their own.

    CSS gives an element one `translate` and one `scale`, so a later phase would have the
    crossfade and the morph clobbering `move` and `scale` without this nesting.
    """
    source = deck('slide[#tag("t")[word]]') + check(
        "assert.eq(query(<t>).len(), 1)",
        'assert.eq(site("t").outer, "box")',
        'assert.eq(site("t").inner, "box")',
        "assert.eq(query(<t>).first().body.body.func(), move)",
        "assert.eq(query(<t>).first().body.body.body.func(), scale)",
        "assert.eq(query(<t>).first().body.body.body.reflow, false)",
    )
    typst.ok(source)


def test_a_tag_nothing_addresses_emits_the_identity(typst: TypstRunner):
    """The structure is the same in every state, and only the parameters change.

    That is what keeps a slide's states laying out identically, since `move`, `scale` and
    `hide` inside the tag's own wrapper are layout-neutral.
    """
    source = deck('slide[#tag("t")[word]]') + check(
        f'assert.eq(site("t") + (outer: none, inner: none), {IDENTITY} + '
        "(outer: none, inner: none))",
    )
    typst.ok(source)


def test_hidden_is_the_initial_state_counterpart_of_hide(typst: TypstRunner):
    """A tag the timeline never mentions still starts out invisible when it says so."""
    source = deck('slide[#tag("t", hidden: true)[word]]') + check(
        'assert.eq(site("t").hidden, true)',
    )
    typst.ok(source)


# The plan reaching the tag sites.


def test_every_state_puts_its_own_display_state_on_the_tag_site(typst: TypstRunner):
    """The presentation renders one page per state, so `query` sees them in order.

    This is the assertion that the whole path works: the timeline is resolved, the result
    is provided to the body, and the tag site applies the state it was handed.
    """
    animation = (
        "{ import anim: *\n"
        '  sub(move("t", x: 1cm, y: 2mm))\n'
        '  sub(scale("t", 2), hide("t"))\n'
        '  sub(move("t", x: 1cm), reveal("t")) }'
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
    animation = '{ import anim: *\n  sub(move("t", x: 1cm)) }'
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
    first = '{ import anim: *\n  sub(move("t", x: 1cm)) }'
    second = '{ import anim: *\n  sub(scale("t", 3)) }'
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
    animation = '{ import anim: *\n  sub(move("t", x: 1cm)) }'
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

    Until the runtime exists, the HTML output shows every tag at the identity and a
    `hidden: true` tag is visible, which the manual says.
    """
    animation = '{ import anim: *\n  sub(move("t", x: 1cm), hide("t")) }'
    body = f'slide(animation: {animation})[#tag("t", hidden: true)[word]]'
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


def test_a_body_that_is_not_content_needs_wrap_none(typst: TypstRunner):
    """The message has to say the way out, because this is the cetz case."""
    typst.fails(
        deck('slide[#tag("t", (1, 2, 3))]'),
        "the body of the tag t is not content, but array",
    )


def test_a_continuous_primitive_on_a_wrap_none_tag_is_refused(typst: TypstRunner):
    """Without a label there is no group, so the browser would silently do nothing.

    Failing here rather than in the browser much later is the reason a tag knows which
    names the timeline animates anywhere in the slide, and not only in its own state.
    """
    animation = '{ import anim: *\n  sub(move("t", x: 1cm)) }'
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


def test_a_hidden_tag_without_a_wrapper_is_refused(typst: TypstRunner):
    """Hiding is a display state, and a tag site that is no group cannot carry one."""
    typst.fails(
        deck('slide[#tag("t", [x], hidden: true, wrap: none)]'),
        "the tag t is hidden and has no wrapper",
    )


def test_the_removed_argument_is_refused_for_now(typst: TypstRunner):
    """It is the initial-state counterpart of `remove`, which needs the epochs."""
    typst.fails(
        deck('slide[#tag("t", [x], removed: true)]'),
        "the removed argument of the tag t is not implemented yet",
    )


def test_a_tag_name_that_is_not_a_string_is_refused(typst: TypstRunner):
    """A label would work in typst and not in the browser, where the name is an attribute."""
    typst.fails(deck("slide[#tag(<t>, [x])]"), "a tag takes its name as a string")
