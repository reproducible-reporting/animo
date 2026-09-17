# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tiers 1 and 2: what the timing arguments resolve to, and what they leave alone.

All of them are numbers of seconds, and they decide *when* and *how long* rather than
*what*:
`wait:` and `hold:` time a step, at the subslide level and at the slide level alike,
the first naming the gap before it and the second the gap after it,
`delay:` times one operation inside a step,
and `duration:` says how long that operation then takes.
`duration:` also takes `auto`, which is the deck's own step duration and its default:
that number lives in a stylesheet the resolver cannot read,
so `auto` travels to the browser as itself rather than as a number.
None of the three changes a layout, so the assertions are of two kinds:
the resolved structure, which holds the numbers,
and the rasterised paged outputs, which have no clock and must be untouched.

The one refusal that needs a rendering is here too:
two operations that change one region at one boundary may not disagree about their timing,
and which region a tag belongs to is a fact only layout knows,
so the deck is compiled rather than resolved.
"""

import pytest
from decks import deck
from harness import PagedRunner, TypstRunner, assert_identical

PRELUDE = """\
#import "/src/plan.typ": resolve, timeline-asks
#import "/src/runtime.typ": browser-plan
#import "/src/anim.typ"
"""


def resolved(timeline: str, *assertions: str, wait: str = "none", hold: str = "none") -> str:
    """A document that resolves a timeline and asserts about the result.

    Parameters
    ----------
    timeline
        The body of the animation argument, without the `import anim: *` line.
    assertions
        Typst expressions, each asserted with the plan bound to `plan`.
    wait, hold
        The slide's own two gap numbers, as typst literals.
        They are what `#slide(wait: ..)` and `#slide(hold: ..)` hand the resolver
        for state 0.
    """
    steps = "\n".join("  " + line for line in timeline.splitlines())
    return "\n".join(
        (
            PRELUDE,
            "#let timeline = {",
            "  import anim: *",
            steps,
            "}",
            f"#let plan = resolve(timeline, wait: {wait}, hold: {hold})",
            "#let names = timeline-asks(plan).names",
            *assertions,
            "",
        )
    )


def timeline(*steps: str) -> str:
    """The animation argument of a slide, with the primitives imported inside it."""
    return "{ import anim: *\n  " + "\n  ".join(steps) + " }"


# What the two arguments accept.


@pytest.mark.parametrize("value", ["2", "0.25", "0"])
def test_a_wait_is_a_number_of_seconds(typst: TypstRunner, value):
    """An int and a float alike, because typst has no time literal to prefer."""
    typst.ok(
        resolved(
            f'sub(wait: {value}, reveal("a"))',
            f"#assert.eq(plan.states.at(1).wait, {float(value)})",
        )
    )


@pytest.mark.parametrize("value", ['"2s"', "auto", "true"])
def test_a_wait_that_is_not_a_number_is_refused(typst: TypstRunner, value):
    """A string is not a number, and neither is the `auto` that `handout:` takes."""
    typst.fails(resolved(f"sub(wait: {value})"), "as a number of seconds")


def test_a_time_literal_does_not_parse(typst: TypstRunner):
    """Why the unit is seconds and never written down: typst has no `2s` to write."""
    typst.fails(resolved("sub(wait: 2s)"), "invalid number suffix")


def test_a_negative_wait_is_refused(typst: TypstRunner):
    """A step cannot be entered before the one it follows."""
    typst.fails(resolved("sub(wait: -1)"), "not negative")


@pytest.mark.parametrize(
    "operation",
    [
        'reveal("a", delay: 0.2)',
        'hide("a", delay: 0.2)',
        'move("a", dx: 1cm, delay: 0.2)',
        'scale("a", f: 2, delay: 0.2)',
        "pan(dx: 1cm, delay: 0.2)",
        'replace("a", delay: 0.2)[x]',
        'remove("a", delay: 0.2)',
        'apply("a", emph, delay: 0.2)',
        'reset("a", delay: 0.2)',
    ],
)
def test_every_primitive_takes_a_delay(typst: TypstRunner, operation):
    """Continuous, slide and structural alike, which is what makes it one vocabulary."""
    typst.ok(resolved(f"sub({operation})"))


@pytest.mark.parametrize("value", ['"late"', "20%", "auto"])
def test_a_delay_that_is_not_a_number_is_refused(typst: TypstRunner, value):
    """A ratio has nothing here to be a ratio of, which a scale factor does."""
    typst.fails(resolved(f'sub(reveal("a", delay: {value}))'), "as a number of seconds")


def test_a_negative_delay_is_refused(typst: TypstRunner):
    """An operation cannot start before the step it is written in."""
    typst.fails(resolved('sub(reveal("a", delay: -0.5))'), "not negative")


@pytest.mark.parametrize(
    "operation",
    [
        'reveal("a", duration: 2)',
        'hide("a", duration: 2)',
        'move("a", dx: 1cm, duration: 2)',
        'scale("a", f: 2, duration: 2)',
        "pan(dx: 1cm, duration: 2)",
        'replace("a", duration: 2)[x]',
        'remove("a", duration: 2)',
        'apply("a", emph, duration: 2)',
        'reset("a", duration: 2)',
    ],
)
def test_every_primitive_takes_a_duration(typst: TypstRunner, operation):
    """Continuous, slide and structural alike, beside the delay it sits with."""
    typst.ok(resolved(f"sub({operation})"))


@pytest.mark.parametrize("value", ['"slow"', "200%", "true"])
def test_a_duration_that_is_neither_a_number_nor_auto_is_refused(typst: TypstRunner, value):
    """`auto` is the one non-number it takes, and a ratio is not a multiple of anything."""
    typst.fails(resolved(f'sub(reveal("a", duration: {value}))'), "as a number of seconds")


def test_a_negative_duration_is_refused(typst: TypstRunner):
    """An operation cannot take less than no time at all."""
    typst.fails(resolved('sub(reveal("a", duration: -2))'), "not negative")


def test_a_duration_of_auto_is_accepted_on_every_kind(typst: TypstRunner):
    """Stating the default explicitly is how a deck says "the deck's own step"."""
    typst.ok(
        resolved(
            'sub(reveal("a", duration: auto), replace("b", duration: auto)[x])',
            "#assert.eq(plan.states.at(1).timing.tags.a.opacity.duration, auto)",
        )
    )


# Where a wait ends up.


def test_a_state_carries_the_wait_before_it_is_entered(typst: TypstRunner):
    """The rule is the delay *before* a step, so the wait belongs to the state it brings up."""
    typst.ok(
        resolved(
            """
sub(wait: 2, reveal("a"))
sub(hide("a"))
""",
            "#assert.eq(plan.states.map(state => state.wait), (none, 2.0, none))",
        )
    )


def test_the_slide_writes_the_wait_of_its_initial_state(typst: TypstRunner):
    """State 0 has no `sub` of its own, so `#slide(wait: ..)` is where its wait is written."""
    typst.ok(
        resolved(
            'sub(wait: 1, reveal("a"))',
            "#assert.eq(plan.states.map(state => state.wait), (3.0, 1.0))",
            wait="3",
        )
    )


def test_two_waits_in_a_row_are_two_states(typst: TypstRunner):
    """The degenerate call *Animation primitives* states the reading for.

    A wait is measured from its predecessor's trigger, so `sub(wait: a)` in front of
    `sub(wait: b, ..ops)` holds for `a + b` in total and is one extra state, rather than
    collapsing into one step of `a + b`.
    """
    typst.ok(
        resolved(
            """
sub(wait: 1)
sub(wait: 2, reveal("a"))
""",
            "#assert.eq(plan.states.map(state => state.wait), (none, 1.0, 2.0))",
            "#assert.eq(plan.states.len(), 3)",
        )
    )


# Where a hold ends up, and the one gap the two of them share.


@pytest.mark.parametrize("value", ["2", "0.25", "0"])
def test_a_hold_is_a_number_of_seconds(typst: TypstRunner, value):
    """The same values `wait:` takes, checked by the same function."""
    typst.ok(
        resolved(
            f'sub(hold: {value}, reveal("a"))',
            f"#assert.eq(plan.states.at(1).hold, {float(value)})",
        )
    )


@pytest.mark.parametrize("value", ['"2s"', "auto", "true"])
def test_a_hold_that_is_not_a_number_is_refused(typst: TypstRunner, value):
    """`auto` is reserved for the clip of a narrated deck and means nothing yet."""
    typst.fails(resolved(f"sub(hold: {value})"), "as a number of seconds")


def test_a_negative_hold_is_refused(typst: TypstRunner):
    """A step cannot be left before it is entered."""
    typst.fails(resolved("sub(hold: -1)"), "not negative")


def test_a_state_carries_the_hold_before_the_state_after_it(typst: TypstRunner):
    """`hold:` names the gap on the other side of the step `wait:` names."""
    typst.ok(
        resolved(
            """
sub(hold: 2, reveal("a"))
sub(hide("a"))
""",
            "#assert.eq(plan.states.map(state => state.hold), (none, 2.0, none))",
        )
    )


def test_the_slide_writes_the_hold_of_its_initial_state(typst: TypstRunner):
    """State 0 has no `sub`, so how long it is held is written on the slide.

    This is the gap the author thinks of as "how long the slide stands there before it
    starts moving", and it is one keyword rather than two: every later state is a `sub`
    and carries its own, the last one included.
    """
    typst.ok(
        resolved(
            'sub(reveal("a"))',
            "#assert.eq(plan.states.map(state => state.hold), (3.0, none))",
            hold="3",
        )
    )


def test_one_gap_may_be_timed_from_either_side(typst: TypstRunner):
    """Two spellings of one thing, and a deck may use both as long as they name two gaps."""
    typst.ok(
        resolved(
            """
sub(hold: 1, reveal("a"))
sub(hide("a"))
sub(wait: 2, reveal("b"))
""",
            "#assert.eq(plan.states.map(state => state.hold), (none, 1.0, none, none))",
            "#assert.eq(plan.states.map(state => state.wait), (none, none, none, 2.0))",
        )
    )


def test_a_gap_timed_from_both_sides_is_refused(typst: TypstRunner):
    """A gap elapses once, so two numbers on it are two answers and not two parts.

    The same resolution two operations disagreeing about a `delay:` in one region get.
    Summing them would produce a length that neither of the two says.
    """
    typst.fails(
        resolved(
            """
sub(hold: 1, reveal("a"))
sub(wait: 2, hide("a"))
"""
        ),
        "timed twice",
    )


def test_the_message_names_both_sides_of_the_gap(typst: TypstRunner):
    """A reader of the message is looking at one of the two calls and needs the other."""
    result = typst.fails(
        resolved(
            """
sub(reveal("a"))
sub(hold: 1, hide("a"))
sub(wait: 2, reveal("b"))
"""
        ),
        "sub 2's hold:",
    )
    assert "sub 3's wait:" in result.stderr


def test_the_slides_own_hold_can_collide_with_the_first_subs_wait(typst: TypstRunner):
    """State 0's two numbers are `#slide`'s, so the slide is one side of that gap."""
    typst.fails(
        resolved('sub(wait: 1, reveal("a"))', hold="2"),
        "slide(hold: ..)",
    )


def test_a_hold_and_a_wait_on_one_state_are_its_two_gaps(typst: TypstRunner):
    """One step sits between two gaps and may name both of them."""
    typst.ok(
        resolved(
            """
sub(reveal("a"))
sub(wait: 1, hold: 2, hide("a"))
sub(reveal("b"))
""",
            "#assert.eq(plan.states.at(2).wait, 1.0)",
            "#assert.eq(plan.states.at(2).hold, 2.0)",
        )
    )


def test_a_hold_reaches_the_browser_plan(typst: TypstRunner):
    """Both numbers travel, because the gap across a slide boundary is emitted twice.

    One resolved number per gap cannot be written here: a slide's trailing `hold:` and the
    next slide's leading `wait:` are resolved by two calls, so the runtime is the first
    place that sees both sides of that one gap.
    """
    typst.ok(
        resolved(
            'sub(hold: 2, reveal("a"))',
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            "  assert.eq(states.at(1).hold, 2.0)",
            '  assert.eq(states.at(0).keys(), ("tags", "pan", "epoch"))',
            "}",
        )
    )


# The one gap no single slide can see.


def test_a_slide_boundary_timed_from_both_sides_is_refused(typst: TypstRunner):
    """The trailing `hold:` of one slide and the leading `wait:` of the next are one gap.

    Neither slide can refuse it alone: the two numbers are resolved by two calls of
    `resolve`, so the pair is visible nowhere but between the slides.
    """
    result = typst.fails(
        deck(
            "slide(animation: { import anim: *\n  sub(hold: 1) })[= First]",
            "slide(wait: 2)[= Second]",
        ),
        "timed twice",
    )
    assert "slide 1 and slide 2" in result.stderr


def test_the_slides_own_hold_can_time_the_boundary_after_it(typst: TypstRunner):
    """A slide with no `sub` has one state, so `#slide(hold: ..)` times its boundary."""
    typst.fails(
        deck("slide(hold: 1)[= First]", "slide(wait: 2)[= Second]"),
        "timed twice",
    )


def test_a_hold_does_not_reach_across_a_slide_that_says_nothing(typst: TypstRunner):
    """Both spellings in one deck, naming two gaps with a silent slide between them.

    A slide hands on its own trailing `hold:` whether it has one or not, so the `hold:` of
    slide 1 times the boundary below it and nothing else. Were it handed on only when it
    was written, the `wait:` of slide 3 would collide with it two boundaries later.
    """
    typst.ok(
        deck(
            "slide(hold: 1)[= First]",
            "slide[= Second]",
            "slide(wait: 2)[= Third]",
        )
    )


# Where a delay ends up: on the property its operation writes, in the state its step enters.


def test_a_delay_lands_on_the_property_its_operation_animates(typst: TypstRunner):
    """One effect has one delay, so a step is as many effects as it has moments."""
    typst.ok(
        resolved(
            'sub(reveal("a", delay: 0.2), move("a", dx: 1cm), scale("b", f: 2, delay: 0.5))',
            "#assert.eq(plan.states.at(1).timing.tags.a.opacity.delay, 0.2)",
            "#assert.eq(plan.states.at(1).timing.tags.a.translate.delay, 0.0)",
            "#assert.eq(plan.states.at(1).timing.tags.b.scale.delay, 0.5)",
        )
    )


def test_a_duration_lands_beside_the_delay_of_the_same_operation(typst: TypstRunner):
    """One effect takes both, so the record the browser reads is the pair."""
    typst.ok(
        resolved(
            'sub(reveal("a", delay: 0.5, duration: 2))',
            "#assert.eq(plan.states.at(1).timing.tags.a.opacity, (delay: 0.5, duration: 2.0))",
        )
    )


def test_an_unstated_duration_stays_auto_in_the_plan(typst: TypstRunner):
    """The default is `auto` and not the number `--animo-primitive-duration` happens to hold.

    The resolver cannot read a stylesheet, and carrying `auto` through is what keeps
    "unset" and "as long as the deck's own step" apart, so that a deck-wide restyle
    reaches the operations that said nothing and leaves the ones that did alone.
    """
    typst.ok(
        resolved(
            'sub(reveal("a", delay: 0.2), replace("b")[x])',
            "#assert.eq(plan.states.at(1).timing.tags.a.opacity.duration, auto)",
            "#assert.eq(plan.epochs.at(1).timings.b, ((delay: 0.0, duration: auto),))",
        )
    )


def test_a_pan_keeps_its_delay_beside_the_tags(typst: TypstRunner):
    """A slide primitive touches no tag, and its timing is kept apart in the same way."""
    typst.ok(
        resolved(
            "sub(pan(dx: 1cm, delay: 0.3))",
            "#assert.eq(plan.states.at(1).timing.pan, (delay: 0.3, duration: auto))",
            "#assert.eq(plan.states.at(1).timing.tags, (:))",
        )
    )


def test_state_zero_is_untimed(typst: TypstRunner):
    """No step enters it, so there is nothing for an operation of its own to be late for."""
    typst.ok(
        resolved(
            'sub(reveal("a", delay: 0.2))',
            "#assert.eq(plan.states.at(0).timing, (tags: (:), pan: none))",
        )
    )


def test_an_epoch_carries_the_timing_of_what_changed_it(typst: TypstRunner):
    """A structural delay holds back the crossfade of the region it changes."""
    typst.ok(
        resolved(
            'sub(replace("a", delay: 0.4)[x], apply("b", emph))',
            "#assert.eq(plan.epochs.at(1).timings.a, ((delay: 0.4, duration: auto),))",
            "#assert.eq(plan.epochs.at(1).timings.b, ((delay: 0.0, duration: auto),))",
        )
    )


# What reaches the browser, which leaves out everything that says nothing.


def test_a_timeline_that_times_nothing_carries_no_timing(typst: TypstRunner):
    """The runtime reads a missing record as "starts with its step", so the plan stays small."""
    typst.ok(
        resolved(
            'sub(reveal("a"), pan(dx: 1cm))',
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            '  assert.eq(states.at(1).keys(), ("tags", "pan", "epoch"))',
            "}",
        )
    )


def test_a_timed_timeline_carries_both_numbers_in_seconds(typst: TypstRunner):
    """`wait` on the state it brings up, and `timing` on what its own step performed."""
    typst.ok(
        resolved(
            'sub(wait: 2, reveal("a", delay: 0.2))',
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            "  assert.eq(states.at(1).wait, 2.0)",
            "  assert.eq(states.at(1).timing, (tags: (a: (opacity: (delay: 0.2)))))",
            '  assert.eq(states.at(0).keys(), ("tags", "pan", "epoch"))',
            "}",
        )
    )


def test_a_stated_duration_travels_as_a_number_of_seconds(typst: TypstRunner):
    """And the delay beside it stays out, because a field at its default says nothing."""
    typst.ok(
        resolved(
            'sub(reveal("a", duration: 2))',
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            "  assert.eq(states.at(1).timing, (tags: (a: (opacity: (duration: 2.0)))))",
            "}",
        )
    )


def test_an_auto_duration_reaches_the_browser_as_nothing_at_all(typst: TypstRunner):
    """`auto` is the duration that lives in the stylesheet, so it has no number to carry.

    The runtime reads a missing duration as the deck's own, which is what `auto` means,
    so a deck that states none carries none.
    """
    typst.ok(
        resolved(
            'sub(reveal("a", delay: 0.2, duration: auto))',
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            "  assert.eq(states.at(1).timing, (tags: (a: (opacity: (delay: 0.2)))))",
            "}",
        )
    )


# Two operations that change one region at one boundary.

DISAGREE = 'sub(replace("a", delay: 0.2)[A2], replace("b")[B2])'
"""One step whose two structural operations are timed differently."""

DISAGREE_DURATION = 'sub(replace("a", duration: 2)[A2], replace("b")[B2])'
"""The same, disagreeing about the second number of the pair rather than the first."""


def test_two_operations_in_one_region_may_not_disagree_about_their_timing(
    typst: TypstRunner,
):
    """A region crossfades once, so there is nothing for a precedence rule to pick between."""
    body = '#region[#tag("a")[A] #tag("b")[B]]'
    source = deck(f"slide(animation: {timeline(DISAGREE)})[{body}]")
    typst.fails(source, "disagree about their timing")


def test_two_operations_in_one_region_may_not_disagree_about_a_duration_either(
    typst: TypstRunner,
):
    """The comparison is the pair, so the second number is refused as the first one is."""
    body = '#region[#tag("a")[A] #tag("b")[B]]'
    source = deck(f"slide(animation: {timeline(DISAGREE_DURATION)})[{body}]")
    typst.fails(source, "disagree about their timing")


def test_the_same_two_durations_in_two_regions_are_not_refused(typst: TypstRunner):
    """Two bare tags are two regions, so each crossfade has a length of its own."""
    body = '#tag("a")[A]\n#tag("b")[B]'
    source = deck(f"slide(animation: {timeline(DISAGREE_DURATION)})[{body}]")
    typst.ok(source)


def test_the_same_two_operations_in_two_regions_are_not_refused(typst: TypstRunner):
    """Two bare tags are always two regions, so each crossfade has one timing of its own."""
    body = '#tag("a")[A]\n#tag("b")[B]'
    source = deck(f"slide(animation: {timeline(DISAGREE)})[{body}]")
    typst.ok(source)


def test_two_operations_on_one_tag_may_not_disagree_either(typst: TypstRunner):
    """One tag is one region whatever else is around it, and one crossfade with it."""
    body = '#tag("a")[A]'
    steps = ('sub(apply("a", emph, delay: 0.3), replace("a")[A2])',)
    source = deck(f"slide(animation: {timeline(*steps)})[{body}]")
    typst.fails(source, "disagree about their timing")


def test_a_region_inside_a_changed_region_shares_its_timing(typst: TypstRunner):
    """The outer region is what crossfades, so the inner one's operation is part of it."""
    body = '#region[#tag("a")[A] #region[#tag("b")[B]]]'
    source = deck(f"slide(animation: {timeline(DISAGREE)})[{body}]")
    typst.fails(source, "disagree about their timing")


def test_two_boundaries_are_timed_independently(typst: TypstRunner):
    """The refusal is about one boundary, so two steps may say two different things."""
    body = '#region[#tag("a")[A] #tag("b")[B]]'
    steps = (
        'sub(replace("a", delay: 0.2)[A2], replace("b", delay: 0.2)[B2])',
        'sub(replace("a")[A3], replace("b")[B3])',
    )
    source = deck(f"slide(animation: {timeline(*steps)})[{body}]")
    typst.ok(source)


# Tier 2: a page has no clock.

TIMED = timeline(
    'sub(wait: 2, reveal("a", delay: 0.4, duration: 3))',
    'sub(replace("b", delay: 0.3, duration: 2)[A longer claim than the one it replaces.])',
    "sub(pan(dx: 1cm, delay: 0.1, duration: 0.1))",
)

UNTIMED = timeline(
    'sub(reveal("a"))',
    'sub(replace("b")[A longer claim than the one it replaces.])',
    "sub(pan(dx: 1cm))",
)

BODY = '#tag("a")[Hidden at first.]\n  #tag("b")[A claim.]'


@pytest.mark.parametrize("mode", [None, "presentation"])
def test_the_paged_outputs_are_unchanged_by_any_of_the_three(paged: PagedRunner, mode):
    """One page per state with nothing between them, so no number has a clock here.

    The slide-level wait is on the deck as well as the subslide one, because all three
    are absent rather than approximated on paper.
    """
    timed = paged.png(deck(f"slide(wait: 1, animation: {TIMED})[{BODY}]"), mode=mode)
    plain = paged.png(deck(f"slide(animation: {UNTIMED})[{BODY}]"), mode=mode)
    assert len(timed) == len(plain)
    for index, (one, other) in enumerate(zip(timed, plain, strict=True)):
        assert_identical(one, other, what=f"page {index + 1} with and without timing")
