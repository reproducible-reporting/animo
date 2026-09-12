# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 1: what a timeline resolves to, asserted inside the document that resolves it.

The resolver is the cheapest part of animo to get wrong without noticing, because a
display state that accumulates incorrectly is a slide that looks plausible and is off by
half a centimetre. So the assertions are on the resolved structure and on nothing else:
the state count, the per-state display state, and the flags each state carries.

`replace` and `apply` will carry content and functions, which do not compare usefully,
which is the other reason this tier asserts on structure rather than on payloads.
"""

from harness import TypstRunner

PRELUDE = """\
#import "/src/plan.typ": continuous-names, identity, resolve
#import "/src/runtime.typ": browser-plan
#import "/src/anim.typ"
"""


def resolved(timeline: str, *assertions: str) -> str:
    """A document that resolves a timeline and asserts about the result.

    Parameters
    ----------
    timeline
        The body of the animation argument, without the `import anim: *` line.
    assertions
        Typst expressions, each asserted with the plan bound to `plan`
        and the continuous names to `names`.
    """
    steps = "\n".join("  " + line for line in timeline.splitlines())
    return "\n".join(
        (
            PRELUDE,
            "#let timeline = {",
            "  import anim: *",
            steps,
            "}",
            "#let plan = resolve(timeline)",
            "#let names = continuous-names(timeline)",
            *assertions,
            "",
        )
    )


# The state model.


def test_a_slide_without_a_timeline_has_one_state(typst: TypstRunner):
    """State 0 is the body as declared, and a slide that says nothing else stops there."""
    typst.ok(
        resolved(
            "",
            "#assert.eq(plan.states.len(), 1)",
            "#assert.eq(plan.states.first().display, (:))",
            "#assert.eq(names, ())",
        )
    )


def test_the_state_count_is_one_more_than_the_number_of_steps(typst: TypstRunner):
    """S+1 states, which is what the presentation PDF turns into pages."""
    typst.ok(
        resolved(
            """
sub(reveal("a"))
sub(hide("a"))
sub(move("a", x: 1cm))
""",
            "#assert.eq(plan.states.len(), 4)",
        )
    )


def test_an_empty_step_advances_without_changing_anything(typst: TypstRunner):
    """`sub()` is how an author asks for a click that does nothing."""
    typst.ok(
        resolved(
            """
sub(hide("a"))
sub()
""",
            "#assert.eq(plan.states.len(), 3)",
            "#assert.eq(plan.states.at(1).display, plan.states.at(2).display)",
        )
    )


# The four continuous primitives, and how they accumulate.


def test_every_primitive_lands_in_the_display_state_of_its_tag(typst: TypstRunner):
    """One step holding all four, so that the resolved shape is stated once in full."""
    typst.ok(
        resolved(
            """
sub(
  reveal("shown"),
  hide("gone"),
  move("here", x: 1cm, y: -2mm),
  scale("big", 2),
)
""",
            '#assert.eq(plan.states.at(1).display.at("shown"), (..identity, hidden: false))',
            '#assert.eq(plan.states.at(1).display.at("gone"), (..identity, hidden: true))',
            '#assert.eq(plan.states.at(1).display.at("here"), (..identity, x: 1cm, y: -2mm))',
            '#assert.eq(plan.states.at(1).display.at("big"), (..identity, scale: 2.0))',
        )
    )


def test_a_tag_nothing_addressed_has_no_entry_at_all(typst: TypstRunner):
    """The absence is what lets a tag fall back to its own `hidden:` argument.

    A resolved `hidden` of `none` says the same thing for a tag the timeline moved but
    never revealed or hid, which is why `identity` carries `none` rather than `false`.
    """
    typst.ok(
        resolved(
            'sub(move("moved", x: 1cm))',
            '#assert.eq("untouched" in plan.states.at(1).display, false)',
            '#assert.eq(plan.states.at(1).display.at("moved").hidden, none)',
            "#assert.eq(identity.hidden, none)",
        )
    )


def test_moves_add_and_scales_multiply_across_steps(typst: TypstRunner):
    """Continuous operations accumulate, and each state is the previous one plus a step."""
    typst.ok(
        resolved(
            """
sub(move("a", x: 1cm), scale("a", 2))
sub(move("a", x: 2cm, y: 1cm), scale("a", 3))
""",
            '#assert.eq(plan.states.at(1).display.at("a"), (..identity, x: 1cm, scale: 2.0))',
            "#assert.eq(",
            '  plan.states.at(2).display.at("a"),',
            "  (..identity, x: 3cm, y: 1cm, scale: 6.0),",
            ")",
        )
    )


def test_reveal_and_hide_overwrite_rather_than_accumulate(typst: TypstRunner):
    """Visibility is a flag, so the last word in the timeline is the one that counts."""
    typst.ok(
        resolved(
            """
sub(hide("a"))
sub(reveal("a"))
""",
            '#assert.eq(plan.states.at(1).display.at("a").hidden, true)',
            '#assert.eq(plan.states.at(2).display.at("a").hidden, false)',
        )
    )


def test_a_scale_written_as_a_ratio_resolves_to_the_same_number(typst: TypstRunner):
    """Factors multiply along the timeline, so one of the two forms has to win."""
    typst.ok(
        resolved(
            """
sub(scale("a", 50%), scale("b", 0.5))
""",
            '#assert.eq(plan.states.at(1).display.at("a").scale, 0.5)',
            '#assert.eq(plan.states.at(1).display.at("b").scale, 0.5)',
        )
    )


def test_the_earlier_states_keep_the_display_state_they_had(typst: TypstRunner):
    """A step must not reach backwards, which is what makes a state a snapshot.

    The resolver builds each state from a dictionary it has already handed out,
    so this is the assertion that catches a value shared by reference.
    """
    typst.ok(
        resolved(
            """
sub(move("a", x: 1cm))
sub(move("a", x: 1cm))
""",
            "#assert.eq(plan.states.at(0).display, (:))",
            '#assert.eq(plan.states.at(1).display.at("a").x, 1cm)',
            '#assert.eq(plan.states.at(2).display.at("a").x, 2cm)',
        )
    )


# The names the timeline animates, which a tag has to know in every state.


def test_the_continuous_names_are_every_tag_a_continuous_primitive_addresses(
    typst: TypstRunner,
):
    """A tag site that cannot be animated has to say so in state 0 already.

    Waiting for the state that moves it would mean a silent no-op in the browser, which
    is the failure this list exists to turn into a compile error.
    """
    typst.ok(
        resolved(
            """
sub(move("b", x: 1cm))
sub(reveal("a"), hide("a"))
""",
            '#assert.eq(names, ("a", "b"))',
        )
    )


# The handout flag.


def test_the_handout_shows_the_final_state_of_a_slide(typst: TypstRunner):
    """`handout: auto` is every step saying "the last one, and no other"."""
    typst.ok(
        resolved(
            """
sub(hide("a"))
sub(reveal("a"))
""",
            "#assert.eq(plan.states.map(state => state.handout), (false, false, true))",
        )
    )


def test_a_slide_without_a_timeline_still_asks_for_its_handout_page(typst: TypstRunner):
    """State 0 is the final state there, so the rule has to hold with no steps at all."""
    typst.ok(resolved("", "#assert.eq(plan.states.first().handout, true)"))


def test_stating_the_handout_flag_overrides_the_automatic_choice(typst: TypstRunner):
    """Both directions, because a handout that loses a step and one that shows too many
    are the same mistake seen from two sides."""
    typst.ok(
        resolved(
            """
sub(handout: true, hide("a"))
sub(handout: false, reveal("a"))
""",
            "#assert.eq(plan.states.map(state => state.handout), (false, true, false))",
        )
    )


# The epoch placeholders, which the structural primitives fill in.


def test_every_state_is_in_the_first_epoch_and_there_is_one(typst: TypstRunner):
    """A slide with no structural operation has exactly one epoch, and this says so.

    The fields are in their final shape from the start, so that the phase which adds
    epochs extends the resolver rather than replacing it.
    """
    typst.ok(
        resolved(
            """
sub(hide("a"))
sub(move("a", x: 1cm))
""",
            "#assert.eq(plan.states.map(state => state.epoch), (0, 0, 0))",
            "#assert.eq(plan.epochs, ((:),))",
        )
    )


# The footgun, and the other ways a timeline can be written wrong.


def test_an_operation_that_is_not_one_names_the_star_import(typst: TypstRunner):
    """This is the footgun `sub` exists to close.

    `import ..: *` leaves every name the module does not define bound to the standard
    library, so `rotate("b", 45deg)` quietly calls `std.rotate` and returns content.
    Without this check it surfaces much later as a confusing missing-field error.
    """
    result = typst.fails(
        resolved('sub(rotate("b", 45deg))'),
        "argument 1 of sub is not an animo operation, but content",
    )
    assert "import anim: *" in result.stderr


def test_the_offending_argument_is_named_by_its_position(typst: TypstRunner):
    """A step holds several operations, so the message has to say which one it is."""
    typst.fails(
        resolved('sub(reveal("a"), hide("b"), 3)'),
        "argument 3 of sub is not an animo operation, but integer 3",
    )


def test_a_step_that_is_not_a_sub_call_is_refused(typst: TypstRunner):
    """A timeline is a code block of `sub(..)` calls and nothing else."""
    typst.fails(
        PRELUDE + '#let plan = resolve(((kind: "reveal", name: "a"),))\n',
        "step 1 of the animation argument is not a sub(..) call",
    )


def test_a_content_block_as_a_timeline_is_refused(typst: TypstRunner):
    """The shape of the mistake is a body written in the animation argument."""
    typst.fails(
        PRELUDE + "#let plan = resolve([a body])\n",
        "a content block is the slide body, not its timeline",
    )


def test_a_bare_step_dictionary_is_refused(typst: TypstRunner):
    """`sub` returns a one-element array, and the message says why.

    A code block joins arrays and *merges* dictionaries, so a timeline of bare
    dictionaries would silently collapse into one step.
    """
    typst.fails(
        resolved('sub(reveal("a")).first()'),
        "the animation argument received the inside of a sub(..) call",
    )


def test_an_unknown_named_argument_of_sub_is_refused(typst: TypstRunner):
    """`sub` takes one keyword of its own, so anything else is a typo."""
    typst.fails(
        resolved('sub(handuot: true, reveal("a"))'),
        "sub takes no named argument besides handout",
    )


def test_a_handout_flag_that_is_not_a_flag_is_refused(typst: TypstRunner):
    """It takes auto, true or false, and nothing in between."""
    typst.fails(
        resolved('sub(handout: 1, reveal("a"))'),
        "the handout argument of sub takes auto, true or false",
    )


def test_a_tag_name_that_is_not_a_string_is_refused(typst: TypstRunner):
    """A label is what a reader reaches for first, and it is not what animo uses."""
    typst.fails(
        resolved("sub(reveal(<a>))"),
        "reveal takes the name of a tag as a string",
    )


def test_a_move_in_a_ratio_of_nothing_is_refused(typst: TypstRunner):
    """A ratio has no meaning here: a tag does not know what it would be a ratio of."""
    typst.fails(
        resolved('sub(move("a", x: 50%))'),
        "move takes x as a length",
    )


def test_a_scale_factor_that_is_not_a_number_is_refused(typst: TypstRunner):
    """Factors multiply along the timeline, so they have to be numbers."""
    typst.fails(
        resolved('sub(scale("a", "big"))'),
        "scale takes a factor as a number or a ratio",
    )


# The primitives that are named and not implemented.


def test_panning_says_it_is_not_implemented(typst: TypstRunner):
    """A timeline the resolver silently ignores is worse than one that does not compile."""
    typst.fails(resolved("sub(pan(x: 1cm))"), "pan is not implemented yet")


def test_the_structural_primitives_say_they_are_not_implemented(typst: TypstRunner):
    """They need the epochs, and each is named so that the message points at the call."""
    for call, name in (
        ('replace("a")[new]', "replace"),
        ('remove("a")', "remove"),
        ('apply("a", emph)', "apply"),
        ('reset("a")', "reset"),
    ):
        typst.fails(resolved(f"sub({call})"), f"{name} is not implemented yet")


# What the browser is handed.


def test_every_state_of_the_browser_plan_holds_every_addressed_tag(typst: TypstRunner):
    """A state that said nothing about a tag would leave the previous state's CSS in place.

    The browser keeps a display state as inline style until something overwrites it,
    so stepping backwards would not undo what stepping forwards did.
    """
    typst.ok(
        resolved(
            '''sub(move("a", x: 1cm))
sub(scale("b", 2))''',
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            "  assert.eq(states.len(), 3)",
            "  assert(states.all(state => state.tags.keys().sorted() == (\"a\", \"b\")))",
            "  assert.eq(states.at(0).tags.a, (hidden: false, x: 0.0, y: 0.0, scale: 1.0))",
            "  assert.eq(states.at(2).tags.a.x, 28.3465)",
            "  assert.eq(states.at(2).tags.b.scale, 2.0)",
            "}",
        )
    )


def test_a_tag_hidden_by_its_own_argument_reaches_the_browser_as_hidden(typst: TypstRunner):
    """The fallback the timeline cannot take, taken before the plan leaves typst.

    `hidden:` is written at the tag site, so the tag site reports it and the slide folds
    it in. The runtime then applies what it is given and resolves nothing.
    """
    typst.ok(
        resolved(
            '''sub(reveal("h"))''',
            "#context {",
            '  let states = browser-plan(plan, names, ("h", "other")).states',
            "  assert.eq(states.at(0).tags.h.hidden, true)",
            "  assert.eq(states.at(1).tags.h.hidden, false)",
            '  // A hidden tag the timeline never mentions is in the plan all the same.',
            "  assert.eq(states.at(0).tags.other.hidden, true)",
            "  assert.eq(states.at(1).tags.other.hidden, true)",
            "}",
        )
    )


def test_a_length_reaches_the_browser_as_a_number_of_typst_points(typst: TypstRunner):
    """The user unit of a frame's SVG is a typst point, which is what the runtime writes.

    Rounded, because typst's own numbers run to fifteen digits that no renderer can tell
    apart and that make the emitted page hard to read and hard to diff.
    """
    typst.ok(
        resolved(
            'sub(move("a", x: 1in, y: 3pt))',
            "#context {",
            "  let tags = browser-plan(plan, names, ()).states.at(1).tags",
            "  assert.eq(tags.a.x, 72.0)",
            "  assert.eq(tags.a.y, 3.0)",
            "}",
        )
    )
