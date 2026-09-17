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

import pytest
from harness import TypstRunner

PRELUDE = """\
#import "/src/plan.typ": (
  anchor-names, at, identity, pristine, resolve, timeline-asks, unpanned, varies,
)
#import "/src/runtime.typ": browser-plan
#import "/src/anim.typ"
"""


def resolved(timeline: str, *assertions: str, handout: str = "auto") -> str:
    """A document that resolves a timeline and asserts about the result.

    Parameters
    ----------
    timeline
        The body of the animation argument, without the `import anim: *` line.
    assertions
        Typst expressions, each asserted with the plan bound to `plan`,
        what the timeline asks of the tag sites to `asked`
        and the continuous names to `names`.
    handout
        The slide's own handout flag, as a typst literal.
        It is what `#slide(handout: ..)` hands the resolver for state 0.
    """
    steps = "\n".join("  " + line for line in timeline.splitlines())
    return "\n".join(
        (
            PRELUDE,
            "#let timeline = {",
            "  import anim: *",
            steps,
            "}",
            f"#let plan = resolve(timeline, handout: {handout})",
            "#let asked = timeline-asks(plan)",
            "#let names = asked.names",
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
    """One step holding all four, so that the resolved shape is stated once in full.

    A position is an anchor and an offset per axis, and the anchor a tag starts from is its
    own, so an axis nothing addressed is `(relto: <the tag>, offset: 0pt)` rather than a
    zero length. That pair is what a target resolves to the identity.
    """
    typst.ok(
        resolved(
            """
sub(
  reveal("shown"),
  hide("gone"),
  move("here", x: 1cm, dy: -2mm),
  scale("big", f: 2),
)
""",
            '#assert.eq(plan.states.at(1).display.at("shown"), '
            '(: ..identity("shown"), hidden: false))',
            '#assert.eq(plan.states.at(1).display.at("gone"), '
            '(: ..identity("gone"), hidden: true))',
            "#assert.eq(",
            '  plan.states.at(1).display.at("here"),',
            '  (: ..identity("here"), x: (relto: none, offset: 1cm),',
            '     y: (relto: "here", offset: -2mm)),',
            ")",
            "#assert.eq(",
            '  plan.states.at(1).display.at("big"),',
            '  (: ..identity("big"), scale: (x: 2.0, y: 2.0)),',
            ")",
        )
    )


def test_a_tag_nothing_addressed_has_no_entry_at_all(typst: TypstRunner):
    """A name absent from a state rests: visible, where the body put it, at its own size.

    A tag the timeline moved but never revealed or hid is visible for the same reason,
    which is what `identity` says.
    """
    typst.ok(
        resolved(
            'sub(move("moved", x: 1cm))',
            '#assert.eq("untouched" in plan.states.at(1).display, false)',
            '#assert.eq(plan.states.at(1).display.at("moved").hidden, false)',
            '#assert.eq(identity("moved"), '
            '(: hidden: false, ..at("moved"), scale: (x: 1.0, y: 1.0)))',
        )
    )


def test_a_relative_move_adds_and_an_absolute_one_overwrites(typst: TypstRunner):
    """`dx` shifts from wherever the element is, and `x` puts it at a distance from an anchor.

    Which is the same rule `pan` follows, one axis at a time, and it is why a relative axis
    keeps the anchor it moves from rather than resolving against it here.
    """
    typst.ok(
        resolved(
            """
sub(move("a", dx: 1cm))
sub(move("a", dx: 2cm, dy: 1cm))
sub(move("a", x: 5cm))
""",
            '#assert.eq(plan.states.at(1).display.at("a").x, (relto: "a", offset: 1cm))',
            '#assert.eq(plan.states.at(2).display.at("a").x, (relto: "a", offset: 3cm))',
            '#assert.eq(plan.states.at(2).display.at("a").y, (relto: "a", offset: 1cm))',
            '#assert.eq(plan.states.at(3).display.at("a").x, (relto: none, offset: 5cm))',
            "// The axis the last step said nothing about keeps the pair it had.",
            '#assert.eq(plan.states.at(3).display.at("a").y, (relto: "a", offset: 1cm))',
        )
    )


def test_a_move_says_where_it_goes_in_the_two_ways_a_pan_does(typst: TypstRunner):
    """The anchor is the canvas origin, or with `relto` another tag, and `relto` alone
    sends both axes to it."""
    typst.ok(
        resolved(
            """
sub(move("a", relto: "b"))
sub(move("a", relto: "c", x: 1cm, dy: 2cm))
""",
            '#assert.eq(plan.states.at(1).display.at("a").x, (relto: "b", offset: 0pt))',
            '#assert.eq(plan.states.at(1).display.at("a").y, (relto: "b", offset: 0pt))',
            '#assert.eq(plan.states.at(2).display.at("a").x, (relto: "c", offset: 1cm))',
            "// `dy` keeps the anchor it moves from, so the second axis is still b's.",
            '#assert.eq(plan.states.at(2).display.at("a").y, (relto: "b", offset: 2cm))',
        )
    )


def test_a_factor_is_set_rather_than_multiplied_into_what_is_there(typst: TypstRunner):
    """Two `scale(f: 2)` steps leave the element at twice its size, not four times.

    That is what lets a factor be read on its own, and it makes `f: 1` the restore whatever
    came before it.
    """
    typst.ok(
        resolved(
            """
sub(scale("a", f: 2))
sub(scale("a", f: 2))
sub(scale("a", f: 1))
""",
            '#assert.eq(plan.states.at(1).display.at("a").scale, (x: 2.0, y: 2.0))',
            '#assert.eq(plan.states.at(2).display.at("a").scale, (x: 2.0, y: 2.0))',
            '#assert.eq(plan.states.at(3).display.at("a").scale, (x: 1.0, y: 1.0))',
        )
    )


def test_an_axis_a_scale_omits_keeps_the_factor_it_had(typst: TypstRunner):
    """`fx` after `f` leaves the vertical factor where the earlier step put it."""
    typst.ok(
        resolved(
            """
sub(scale("a", f: 3))
sub(scale("a", fx: 2))
""",
            '#assert.eq(plan.states.at(2).display.at("a").scale, (x: 2.0, y: 3.0))',
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
    """The browser and the paged renderer both take a number, so one of the forms has to win."""
    typst.ok(
        resolved(
            """
sub(scale("a", f: 50%), scale("b", f: 0.5), scale("c", fx: 150%))
""",
            '#assert.eq(plan.states.at(1).display.at("a").scale, (x: 0.5, y: 0.5))',
            '#assert.eq(plan.states.at(1).display.at("b").scale, (x: 0.5, y: 0.5))',
            '#assert.eq(plan.states.at(1).display.at("c").scale.x, 1.5)',
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
sub(move("a", dx: 1cm))
sub(move("a", dx: 1cm))
""",
            "#assert.eq(plan.states.at(0).display, (:))",
            '#assert.eq(plan.states.at(1).display.at("a").x.offset, 1cm)',
            '#assert.eq(plan.states.at(2).display.at("a").x.offset, 2cm)',
        )
    )


# The slide primitive, which keeps a state of its own.


def test_a_pan_is_slide_state_and_touches_no_tag(typst: TypstRunner):
    """A slide primitive addresses the viewport, so the display state of the tags is untouched.

    The target of a `relto` is still one of the continuous names, because the browser reads
    its position off its group, and a tag with no group has to say so in state 0.
    """
    typst.ok(
        resolved(
            'sub(pan(relto: "t", x: 1cm))',
            "#assert.eq(plan.states.at(0).slide.pan, unpanned)",
            "#assert.eq(plan.states.at(1).display, (:))",
            '#assert.eq(names, ("t",))',
        )
    )


def test_x_and_y_put_the_viewport_at_a_distance_from_the_canvas_origin(typst: TypstRunner):
    """Without `relto`, the anchor is the canvas origin, and `x` overwrites rather than adds."""
    typst.ok(
        resolved(
            """
sub(pan(x: 1cm))
sub(pan(x: 2cm, y: 3cm))
""",
            "#assert.eq(plan.states.at(1).slide.pan.x, (relto: none, offset: 1cm))",
            "#assert.eq(plan.states.at(1).slide.pan.y, (relto: none, offset: 0pt))",
            "#assert.eq(plan.states.at(2).slide.pan.x, (relto: none, offset: 2cm))",
            "#assert.eq(plan.states.at(2).slide.pan.y, (relto: none, offset: 3cm))",
        )
    )


def test_relto_alone_brings_both_axes_to_the_tag(typst: TypstRunner):
    """ "Pan so that this tag comes into view" is the whole call, with nothing else said."""
    typst.ok(
        resolved(
            'sub(pan(relto: "t"))',
            '#assert.eq(plan.states.at(1).slide.pan.x, (relto: "t", offset: 0pt))',
            '#assert.eq(plan.states.at(1).slide.pan.y, (relto: "t", offset: 0pt))',
        )
    )


def test_dx_and_dy_move_from_where_the_viewport_already_is(typst: TypstRunner):
    """A relative axis keeps the anchor it moves from, which only a rendering can resolve.

    It also mixes with an absolute one on the other axis, which is why the resolver works
    one axis at a time.
    """
    typst.ok(
        resolved(
            """
sub(pan(relto: "t", x: 1cm, y: 1cm))
sub(pan(dx: 2cm, y: 3cm))
sub(pan(relto: "u", x: 0cm, dy: -1cm))
""",
            '#assert.eq(plan.states.at(2).slide.pan.x, (relto: "t", offset: 3cm))',
            "#assert.eq(plan.states.at(2).slide.pan.y, (relto: none, offset: 3cm))",
            '#assert.eq(plan.states.at(3).slide.pan.x, (relto: "u", offset: 0cm))',
            "#assert.eq(plan.states.at(3).slide.pan.y, (relto: none, offset: 2cm))",
        )
    )


def test_an_axis_a_pan_does_not_mention_stays_where_it_is(typst: TypstRunner):
    """Scrolling down a canvas is `pan(dy: ..)`, and it must not bring the viewport back left."""
    typst.ok(
        resolved(
            """
sub(pan(x: 5cm))
sub(pan(dy: 1cm))
""",
            "#assert.eq(plan.states.at(2).slide.pan.x, (relto: none, offset: 5cm))",
            "#assert.eq(plan.states.at(2).slide.pan.y, (relto: none, offset: 1cm))",
        )
    )


def test_an_axis_given_both_forms_is_refused(typst: TypstRunner):
    """`x` and `dx` are measured from different places, so both at once means nothing."""
    typst.fails(resolved("sub(pan(x: 1cm, dx: 1cm))"), "pan takes either x or dx, not both")
    typst.fails(resolved("sub(pan(y: 1cm, dy: 1cm))"), "pan takes either y or dy, not both")


def test_a_pan_that_says_nothing_is_refused(typst: TypstRunner):
    """An empty `pan()` would leave the viewport where it is, which is `sub()` in disguise."""
    typst.fails(resolved("sub(pan())"), "pan takes at least one of x, y, dx, dy or relto")


def test_a_pan_in_a_ratio_or_to_a_label_is_refused(typst: TypstRunner):
    """The same two mistakes the element primitives refuse, named for `pan`."""
    typst.fails(resolved("sub(pan(dx: 50%))"), "pan takes dx as a length")
    typst.fails(resolved("sub(pan(relto: <t>))"), "pan takes relto as the name of a tag")


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


# The handout flag of the initial state, which is `#slide(handout: ..)`.


def test_the_slide_flag_asks_for_the_page_of_the_initial_state(typst: TypstRunner):
    """The state the body declares has no `sub` of its own, so the slide speaks for it."""
    typst.ok(
        resolved(
            """
sub(reveal("a"))
""",
            "#assert.eq(plan.states.map(state => state.handout), (true, true))",
            handout="true",
        )
    )


def test_a_slide_that_says_nothing_still_keeps_only_its_final_state(typst: TypstRunner):
    """`auto` on the slide is `auto` on state 0, which is the behaviour of every deck
    written before the argument existed."""
    typst.ok(
        resolved(
            """
sub(reveal("a"))
""",
            "#assert.eq(plan.states.map(state => state.handout), (false, true))",
        )
    )


def test_the_slide_flag_and_the_first_step_flag_resolve_independently(typst: TypstRunner):
    """The argument names one state, and every other state keeps its own flag.

    "Keep the first" and "drop the last" are the same slide's business, and a reader will
    expect one to imply something about the other, so the combination is asserted.
    """
    typst.ok(
        resolved(
            """
sub(handout: false, reveal("a"))
""",
            "#assert.eq(plan.states.map(state => state.handout), (true, false))",
            handout="true",
        )
    )


def test_a_slide_without_a_timeline_can_be_left_out_of_the_handout(typst: TypstRunner):
    """State 0 is the only state there, so `false` on the slide takes its only page away,
    which was not expressible before the argument existed."""
    typst.ok(
        resolved(
            "",
            "#assert.eq(plan.states.map(state => state.handout), (false,))",
            handout="false",
        )
    )


# Epochs: the runs of states that share a content state.


def test_a_timeline_without_structural_steps_has_exactly_one_epoch(typst: TypstRunner):
    """This is the cost claim for the ordinary slide: nothing about it is measured twice."""
    typst.ok(
        resolved(
            """
sub(hide("a"))
sub(move("a", x: 1cm), pan(dx: 1cm))
sub()
""",
            "#assert.eq(plan.states.map(state => state.epoch), (0, 0, 0, 0))",
            "#assert.eq(plan.epochs, ((tags: (:), changed: (), timings: (:)),))",
        )
    )


# A timeline that mixes continuous and structural steps, with two steps that stay in an epoch.
MIXED = """
sub(reveal("a"))
sub(replace("a")[new])
sub(move("a", x: 1cm))
sub(apply("b", emph), hide("a"))
sub()
sub(remove("a"), remove("b"))
"""


def test_every_step_with_a_structural_operation_starts_an_epoch(typst: TypstRunner):
    """Boundaries fall exactly at the structural steps, and nowhere else."""
    typst.ok(
        resolved(
            MIXED,
            "#assert.eq(plan.states.map(state => state.epoch), (0, 0, 1, 1, 2, 2, 3))",
            "#assert.eq(plan.epochs.len(), 4)",
        )
    )


def test_an_epoch_names_the_tags_its_first_step_changed(typst: TypstRunner):
    """These are the implicit regions a boundary redraws, one name per tag.

    A step that addresses one tag twice names it once.
    """
    typst.ok(
        resolved(
            MIXED + 'sub(apply("a", emph), reset("a"))\n',
            "#assert.eq(plan.epochs.map(epoch => epoch.changed), "
            '((), ("a",), ("b",), ("a", "b"), ("a",)))',
        )
    )


def test_the_content_state_of_an_epoch_is_carried_forward(typst: TypstRunner):
    """An epoch holds every tag addressed so far, not only the ones its step changed."""
    typst.ok(
        resolved(
            MIXED,
            "#assert.eq(plan.epochs.map(epoch => epoch.tags.keys().sorted()), "
            '((), ("a",), ("a", "b"), ("a", "b")))',
            '#assert.eq(plan.epochs.map(epoch => epoch.tags.at("a", default: pristine).source), '
            '("body", "replacement", "replacement", "removed"))',
            '#assert.eq(plan.epochs.map(epoch => epoch.tags.at("b", default: pristine).source), '
            '("body", "body", "body", "removed"))',
        )
    )


def test_only_a_tag_a_structural_operation_addresses_varies(typst: TypstRunner):
    """Only such a tag needs a footprint, which is what keeps the others as cheap as before."""
    typst.ok(
        resolved(
            MIXED,
            '#assert(varies(plan.epochs, "a"))',
            '#assert(varies(plan.epochs, "b"))',
            '#assert(not varies(plan.epochs, "untouched"))',
            '#assert(not varies(resolve({ import anim: *; sub(move("a", x: 1cm)) }).epochs, "a"))',
        )
    )


# How the structural primitives compose: two slots, applied in the order written.


def test_a_replacement_inherits_the_wrappers_applied_before_it(typst: TypstRunner):
    """`apply` then `replace`: the replacement arrives restyled."""
    typst.ok(
        resolved(
            'sub(apply("a", emph))\nsub(replace("a")[new])',
            '#assert.eq(plan.epochs.at(2).tags.a, (source: "replacement", body: [new], '
            "wrappers: (emph,)))",
        )
    )


def test_a_wrapper_applied_after_a_replacement_wraps_the_replacement(typst: TypstRunner):
    """`replace` then `apply`: the wrapper goes around whatever is laid out now."""
    typst.ok(
        resolved(
            'sub(replace("a")[new])\nsub(apply("a", emph))',
            '#assert.eq(plan.epochs.at(2).tags.a, (source: "replacement", body: [new], '
            "wrappers: (emph,)))",
        )
    )


def test_reset_after_remove_brings_the_body_back_without_wrappers(typst: TypstRunner):
    """`reset` is the one operation that sets both slots."""
    typst.ok(
        resolved(
            'sub(apply("a", emph))\nsub(remove("a"))\nsub(reset("a"))',
            '#assert.eq(plan.epochs.at(2).tags.a, (source: "removed", body: none, '
            "wrappers: (emph,)))",
            '#assert.eq(plan.epochs.at(3).tags.a, (source: "body", body: none, wrappers: ()))',
        )
    )


def test_a_replacement_after_a_remove_keeps_the_wrappers(typst: TypstRunner):
    """Removing clears what is laid out, not how it is styled."""
    typst.ok(
        resolved(
            'sub(apply("a", emph))\nsub(remove("a"))\nsub(replace("a")[back])',
            "#assert.eq(plan.epochs.at(3).tags.a.wrappers, (emph,))",
        )
    )


def test_the_second_of_two_replacements_wins(typst: TypstRunner):
    """In two steps as in one, since operations apply in the order they are written."""
    typst.ok(
        resolved(
            'sub(replace("a")[first])\nsub(replace("a")[second])\n'
            'sub(replace("a")[third], replace("a")[fourth])',
            "#assert.eq(plan.epochs.at(2).tags.a.body, [second])",
            "#assert.eq(plan.epochs.at(3).tags.a.body, [fourth])",
        )
    )


def test_two_wrappers_in_one_step_are_two_wrappers_in_two_steps(typst: TypstRunner):
    """`apply("a", f, g)` is `apply("a", f)` then `apply("a", g)`, outermost last."""
    typst.ok(
        resolved(
            'sub(apply("a", emph, strong))\nsub(apply("b", emph))\nsub(apply("b", strong))',
            "#assert.eq(plan.epochs.at(1).tags.a.wrappers, (emph, strong))",
            "#assert.eq(plan.epochs.at(3).tags.b.wrappers, plan.epochs.at(1).tags.a.wrappers)",
        )
    )


def test_operations_on_one_tag_in_one_step_apply_in_the_order_written(typst: TypstRunner):
    """So a step that restyles and then resets ends at the body, and the reverse does not."""
    typst.ok(
        resolved(
            'sub(apply("a", emph), reset("a"))\nsub(reset("b"), apply("b", emph))',
            "#assert.eq(plan.epochs.at(1).tags.a.wrappers, ())",
            "#assert.eq(plan.epochs.at(2).tags.b.wrappers, (emph,))",
        )
    )


def test_a_structural_and_a_continuous_operation_in_one_step_both_take_effect(
    typst: TypstRunner,
):
    """The two classes keep separate state, so neither undoes the other."""
    typst.ok(
        resolved(
            'sub(replace("a")[new], move("a", dx: 1cm))',
            "#assert.eq(plan.states.at(1).epoch, 1)",
            '#assert.eq(plan.epochs.at(1).tags.a.source, "replacement")',
            "#assert.eq(plan.states.at(1).display.a.x.offset, 1cm)",
        )
    )


def test_reset_leaves_the_display_state_alone(typst: TypstRunner):
    """A moved and hidden tag that is reset stays moved and hidden."""
    typst.ok(
        resolved(
            'sub(move("a", x: 1cm), hide("a"))\nsub(reset("a"))',
            "#assert.eq(plan.states.at(2).display, plan.states.at(1).display)",
        )
    )


def test_a_structural_operation_is_not_a_continuous_name(typst: TypstRunner):
    """A `wrap: none` tag may be replaced, so replacing it may not make it look animated."""
    typst.ok(
        resolved(
            'sub(replace("a")[new], remove("b"), apply("c", emph), reset("d"), hide("e"))',
            '#assert.eq(names, ("e",))',
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
        "sub takes no named argument besides wait, hold and handout",
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
    typst.fails(
        resolved('sub(move("a", dy: 50%))'),
        "move takes dy as a length",
    )


def test_a_scale_factor_that_is_not_a_number_is_refused(typst: TypstRunner):
    """Both targets take a number, so the factor has to resolve to one."""
    typst.fails(
        resolved('sub(scale("a", f: "big"))'),
        "scale takes fx as a number or a ratio",
    )


def test_an_isotropic_factor_together_with_a_per_axis_one_is_refused(typst: TypstRunner):
    """A call that gives both says two different things, so neither wins by precedence."""
    typst.fails(
        resolved('sub(scale("a", f: 2, fx: 3))'),
        "scale takes either f or fx and fy, not both",
    )


def test_a_scale_that_names_no_axis_is_refused(typst: TypstRunner):
    """It would leave the element the size it is, which is `sub()` in disguise."""
    typst.fails(resolved('sub(scale("a"))'), "scale takes at least one of f, fx or fy")


def test_an_absolute_and_a_relative_move_on_one_axis_are_refused(typst: TypstRunner):
    """The two are measured from different places, exactly as they are for a `pan`."""
    typst.fails(resolved('sub(move("a", x: 1cm, dx: 1cm))'), "move takes either x or dx, not both")
    typst.fails(resolved('sub(move("a", y: 1cm, dy: 1cm))'), "move takes either y or dy, not both")


def test_a_move_that_says_nothing_is_refused(typst: TypstRunner):
    """An empty `move()` would leave the element where it is."""
    typst.fails(resolved('sub(move("a"))'), "move takes at least one of x, y, dx, dy or relto")


def test_a_move_relative_to_something_that_is_not_a_name_is_refused(typst: TypstRunner):
    """A label is what a reader reaches for first, here as everywhere else."""
    typst.fails(resolved('sub(move("a", relto: <b>))'), "move takes relto as the name of a tag")


def test_a_replacement_that_is_not_content_is_refused(typst: TypstRunner):
    """A string would be laid out, but a stream of draw commands would not, so neither is taken."""
    typst.fails(
        resolved('sub(replace("a", "text"))'),
        "replace takes its replacement as content, got string",
    )


def test_apply_refuses_named_style_properties(typst: TypstRunner):
    """Animo cannot know which `set` rule a bare property belongs to, and says what to write."""
    typst.fails(
        resolved('sub(apply("a", fill: red))'),
        "apply takes functions only",
    )


def test_apply_without_a_function_is_refused(typst: TypstRunner):
    """It would start an epoch that changes nothing."""
    typst.fails(resolved('sub(apply("a"))'), "apply takes at least one function")


def test_apply_names_the_argument_that_is_not_a_function(typst: TypstRunner):
    """Content in place of a wrapper is the likely mistake, as in `apply("a", [x])`."""
    typst.fails(
        resolved('sub(apply("a", emph, [x]))'),
        "argument 2 of apply on the tag a is not a function, but content",
    )


@pytest.mark.parametrize("call", ["remove(<a>)", "reset(1)", "replace(<a>)[x]", "apply(<a>, emph)"])
def test_a_structural_primitive_takes_its_tag_name_as_a_string(typst: TypstRunner, call):
    """The same check as for the continuous primitives, with the primitive's own name."""
    typst.fails(resolved(f"sub({call})"), f"{call.split('(')[0]} takes the name of a tag")


# What the browser is handed.


def test_every_state_of_the_browser_plan_holds_every_addressed_tag(typst: TypstRunner):
    """A state that said nothing about a tag would leave the previous state's CSS in place.

    The browser keeps a display state as inline style until something overwrites it,
    so stepping backwards would not undo what stepping forwards did.
    """
    typst.ok(
        resolved(
            """sub(move("a", dx: 1cm))
sub(scale("b", f: 2))""",
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            "  assert.eq(states.len(), 3)",
            '  assert(states.all(state => state.tags.keys().sorted() == ("a", "b")))',
            "  assert.eq(states.at(0).tags.a, (: hidden: false,",
            '    x: (relto: "a", offset: 0.0), y: (relto: "a", offset: 0.0),',
            "    scale: (x: 1.0, y: 1.0)))",
            '  assert.eq(states.at(2).tags.a.x, (relto: "a", offset: 28.3465))',
            "  assert.eq(states.at(2).tags.b.scale, (x: 2.0, y: 2.0))",
            "}",
        )
    )


def test_a_tag_the_timeline_reveals_reaches_the_browser_as_hidden_in_state_zero(
    typst: TypstRunner,
):
    """State 0 is resolved from the timeline like every other state.

    Nothing about a display state travels out of the frame, so the plan is complete when it
    leaves typst and the runtime applies what it is given.
    """
    typst.ok(
        resolved(
            """sub(reveal("h"))""",
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            "  assert.eq(states.at(0).tags.h.hidden, true)",
            "  assert.eq(states.at(1).tags.h.hidden, false)",
            "}",
        )
    )


def test_a_pan_reaches_the_browser_as_an_anchor_name_and_an_offset_in_points(
    typst: TypstRunner,
):
    """The anchor stays a name, because only the browser can read a tag's position there."""
    typst.ok(
        resolved(
            """sub(pan(relto: "t", x: 1in))""",
            "#context {",
            "  let states = browser-plan(plan, names, ()).states",
            "  assert.eq(states.at(0).pan.x, (relto: none, offset: 0.0))",
            '  assert.eq(states.at(1).pan.x, (relto: "t", offset: 72.0))',
            '  assert.eq(states.at(1).pan.y, (relto: "t", offset: 0.0))',
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
            'sub(move("a", x: 1in, dy: 3pt))',
            "#context {",
            "  let tags = browser-plan(plan, names, ()).states.at(1).tags",
            "  assert.eq(tags.a.x.offset, 72.0)",
            "  assert.eq(tags.a.y.offset, 3.0)",
            "}",
        )
    )


# Which anchors a rendering has to read, which is what keeps the paged target from querying
# for every tag of every state.


def test_a_tag_the_timeline_only_reveals_needs_no_anchor(typst: TypstRunner):
    """Its position is its own anchor at offset zero, and the two terms cancel."""
    typst.ok(
        resolved(
            'sub(reveal("a"), move("b", dx: 1cm))',
            "#assert.eq(anchor-names(plan), ())",
        )
    )


def test_an_absolute_move_asks_for_the_moved_tag_and_a_relative_one_for_both(
    typst: TypstRunner,
):
    """The translation is `anchor(relto) + offset - anchor(self)`, so it needs what it names."""
    typst.ok(
        resolved(
            """sub(move("a", x: 1cm))
sub(move("b", relto: "c"))
sub(pan(relto: "d"))""",
            '#assert.eq(anchor-names(plan), ("a", "b", "c", "d"))',
        )
    )


def test_the_tags_a_timeline_is_relative_to_carry_the_primitive_that_names_them(
    typst: TypstRunner,
):
    """A refusal has to say whether a pan or a move is the one that cannot find its tag."""
    typst.ok(
        resolved(
            'sub(pan(relto: "p"), move("a", relto: "m"), move("b", relto: "m"))',
            "#assert.eq(",
            "  asked.targets,",
            '  ((kind: "pan", relto: "p"), (kind: "move", relto: "m")),',
            ")",
        )
    )
