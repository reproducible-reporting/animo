# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the deck animating in the browser.

This is where animo's central claim is either true or not, so the assertions are numeric
rather than pictorial: the geometry of a tagged element at each subslide, the value it
holds halfway through a step, and what a deep link lands on.

Two things make them reproducible.
A deep link *snaps*, so a test that only cares about a state never races a transition.
And a transition is driven by the Web Animations API, so a test that does care about the
middle of one pauses it at a stated moment instead of sampling whenever it got there.

Geometry is read with `getBBox` and `getScreenCTM`, never with `getBoundingClientRect`,
which firefox inflates to roughly the width of the whole frame. See *Findings*.
"""

import pytest
from decks import deck
from harness import Deck, TypstRunner

# One centimetre in typst points, which is the user unit of a frame's SVG.
CM = 28.3465

# How far a measured displacement may be from the length the source states, in CSS pixels.
# The floor is the browser's own rounding of a transform; a real error is far larger,
# because the smallest length a timeline states here is a centimetre, which is 28 points.
TOLERANCE = 0.5

# How long a presenter leaves the deck alone before stepping, in milliseconds, and how far
# into the step the runtime may already be by the time the key is pressed.
# Firefox 153 freezes `document.timeline` while the page draws nothing, so a runtime that
# takes a start time off it is a whole `PAUSE` into the step it has just begun,
# and with animo's own 400 ms it would be past the end of it. See *Findings*.
PAUSE = 500
BEGINNING = 100

# How far the centre of a group may move under a scale about its own centre.
# Zero is the claim. Firefox 153 resolves `fill-box` to a box whose centre sits about
# 0.7 CSS pixels from the one `getBBox` reports, which is invisible in a transition.
# See *Findings*, where the probe for that row allows the same.
CENTRE_TOLERANCE = 1.0


def mark(name: str, dx: str = "0cm", dy: str = "0cm", size: str = "2cm", **arguments) -> str:
    """A tagged filled square, placed at an offset from the body origin.

    A square rather than a glyph, because the claim is about where content lands and a
    square's corners are a number. The tag hugs, so the square's own geometry is the tag
    site's geometry and an assertion can be written in centimetres from the source.
    """
    extra = "".join(f", {key}: {value}" for key, value in arguments.items())
    return (
        f"#place(dx: {dx}, dy: {dy}, "
        f'tag("{name}", wrap: box{extra}, '
        f'rect(width: {size}, height: {size}, fill: rgb("#ff0000"))))'
    )


def timeline(*steps: str) -> str:
    """The animation argument of a slide, with the primitives imported inside it."""
    return "{ import anim: *\n  " + "\n  ".join(steps) + " }"


def animated(typst: TypstRunner, body: str, *steps: str, name: str = "deck.html"):
    """Compile a one-slide deck with a timeline, as a file the browser can open."""
    source = deck(f"slide(animation: {timeline(*steps)})[\n  {body}\n]")
    return typst.html(source, name=name)


@pytest.fixture
def moving(typst: TypstRunner):
    """A square that moves, then moves again and scales, so that operations accumulate."""
    return animated(
        typst,
        mark("m"),
        'sub(move("m", x: 3cm, y: 1cm))',
        'sub(move("m", x: 1cm), scale("m", 2))',
    )


# The geometry of each state.


def test_a_move_shifts_the_element_by_the_length_the_timeline_states(deck_at, moving):
    """The first claim of the phase: the browser puts the element where the plan says."""
    presentation: Deck = deck_at(moving)
    unit = presentation.unit
    before = presentation.rects("m")[0]
    after = presentation.goto(1, 1).rects("m")[0]
    assert after.x - before.x == pytest.approx(3 * CM * unit, abs=TOLERANCE)
    assert after.y - before.y == pytest.approx(1 * CM * unit, abs=TOLERANCE)
    assert after.width == pytest.approx(before.width, abs=TOLERANCE)


def test_moves_accumulate_and_a_scale_multiplies(deck_at, moving):
    """State 2 is state 1 with the second step applied, which is the state model itself."""
    presentation: Deck = deck_at(moving)
    unit = presentation.unit
    before = presentation.rects("m")[0]
    after = presentation.goto(1, 2).rects("m")[0]
    assert after.width == pytest.approx(2 * before.width, abs=TOLERANCE)
    # The centre has travelled the sum of the two moves; the corner has not, because the
    # square is twice as large about that centre.
    assert after.center[0] - before.center[0] == pytest.approx(4 * CM * unit, abs=TOLERANCE)
    assert after.center[1] - before.center[1] == pytest.approx(1 * CM * unit, abs=TOLERANCE)


def test_scale_grows_the_element_about_its_own_centre(deck_at, typst: TypstRunner):
    """`transform-box: fill-box` with a centred origin, which is what keeps a scale in place.

    Centres are also what a future morph pairs on, for the same reason.
    """
    presentation: Deck = deck_at(
        animated(typst, mark("m", dx="4cm", dy="2cm"), 'sub(scale("m", 2))')
    )
    before = presentation.rects("m")[0]
    after = presentation.goto(1, 1).rects("m")[0]
    assert after.width == pytest.approx(2 * before.width, abs=TOLERANCE)
    assert after.center[0] == pytest.approx(before.center[0], abs=CENTRE_TOLERANCE)
    assert after.center[1] == pytest.approx(before.center[1], abs=CENTRE_TOLERANCE)


def test_typsts_own_transform_survives_every_state(deck_at, moving):
    """*Architecture* rule 3, from the outside: the shorthand is never emitted.

    Typst writes the element's position as a `transform` attribute on the labelled group.
    A CSS `transform` would replace it and the element would lose its place on the slide
    without anything erroring, so what animo writes has to leave it untouched.
    """
    presentation: Deck = deck_at(moving)
    seen = set()
    for state in range(3):
        presentation.goto(1, state)
        seen.add(
            presentation.page.evaluate(
                """() => document
                    .querySelector('[data-typst-label="m"]')
                    .getAttribute('transform')"""
            )
        )
    assert len(seen) == 1, f"typst's own transform changed between states: {seen}"


def test_a_move_is_the_same_fraction_of_the_slide_at_any_window_size(page, deck_at, moving):
    """A length inside a frame is a user unit, so animo never has to measure the window.

    Measured at two sizes rather than assumed: the whole scheme of writing typst points
    as CSS lengths rests on it.
    """
    presentation: Deck = deck_at(moving)
    fractions = []
    for width in (1280, 640):
        page.set_viewport_size({"width": width, "height": width * 9 // 16})
        presentation.goto(1, 0)
        before = presentation.rects("m")[0]
        after = presentation.goto(1, 1).rects("m")[0]
        fractions.append((after.x - before.x) / presentation.unit)
    assert fractions[0] == pytest.approx(3 * CM, abs=TOLERANCE)
    assert fractions[1] == pytest.approx(fractions[0], abs=TOLERANCE)


# Visibility, and the asymmetry between the targets.


def test_reveal_and_hide_are_opacity_on_the_inner_slot(deck_at, typst: TypstRunner):
    """The continuous slot is the unlabelled group, so the labelled one stays free.

    That is what leaves the boundary slot to the epoch crossfade of a later version.
    """
    presentation: Deck = deck_at(
        animated(typst, mark("m"), 'sub(hide("m"))', 'sub(reveal("m"))')
    )
    assert [style["opacity"] for style in presentation.styles("m")] == ["1"]
    assert [style["opacity"] for style in presentation.goto(1, 1).styles("m")] == ["0"]
    assert [style["opacity"] for style in presentation.goto(1, 2).styles("m")] == ["1"]


def test_an_initially_hidden_tag_has_ink_in_the_dom_and_zero_opacity(
    deck_at, typst: TypstRunner
):
    """The asymmetry between the HTML output and the paged ones, in one assertion.

    Typst's `hide()` lays content out and emits nothing to draw, so no CSS could ever
    bring it back. The HTML target therefore renders an initially hidden element normally
    and the runtime hides it, while only the paged outputs may use `hide()`.
    """
    presentation: Deck = deck_at(
        animated(typst, mark("m", hidden="true"), 'sub(reveal("m"))')
    )
    painted = presentation.page.evaluate(
        """() => document
            .querySelector('[data-typst-label="m"]')
            .querySelectorAll('path, use, rect, image, text').length"""
    )
    assert painted > 0, "the hidden element emitted no ink, so nothing can reveal it"
    assert [style["opacity"] for style in presentation.styles("m")] == ["0"]
    assert [style["opacity"] for style in presentation.goto(1, 1).styles("m")] == ["1"]
    assert presentation.rects("m")[0].width > 0, "the hidden element lost its space"


# Stepping, deep links and the clock.


def test_a_step_interpolates_at_a_stated_moment(page, deck_at, moving):
    """Mid-flight, sampled rather than raced.

    The transition is a paused animation with an explicit `currentTime`, so halfway
    through the step the element is halfway along, and the test says which halfway.
    """
    presentation: Deck = deck_at(moving)
    page.add_style_tag(content=":root { --animo-duration: 4000ms; --animo-easing: linear }")
    unit = presentation.unit
    before = presentation.rects("m")[0]
    presentation.press("ArrowRight").scrub(2000)
    middle = presentation.rects("m")[0]
    assert middle.x - before.x == pytest.approx(1.5 * CM * unit, abs=TOLERANCE)
    assert middle.y - before.y == pytest.approx(0.5 * CM * unit, abs=TOLERANCE)
    presentation.scrub(4000)
    end = presentation.rects("m")[0]
    assert end.x - before.x == pytest.approx(3 * CM * unit, abs=TOLERANCE)


def test_a_step_animates_only_the_properties_it_changes(deck_at, typst: TypstRunner):
    """A property that holds still in the keyframes is not free.

    In chromium 151 a `translate` or `scale` that is equal at both ends stops the browser
    from drawing the `opacity` beside it: the element stays as it was for the whole step
    and jumps at the end. Nothing in the DOM says so, because every value the animation
    computes is right and only the drawing is missing, which is why this is asserted on
    what the step animates rather than on what it looks like. See *Findings*.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            mark("m", hidden="true"),
            'sub(reveal("m"))',
            'sub(move("m", x: 2cm))',
        )
    )
    presentation.press("ArrowRight")
    assert presentation.animating == [{"opacity"}], "the reveal animated more than opacity"
    presentation.settle()
    presentation.press("ArrowRight")
    assert presentation.animating == [{"translate"}], "the move animated more than translate"


def test_a_step_taken_after_a_pause_starts_at_its_beginning(page, deck_at, moving):
    """A presenter talks over a slide and then steps, which is the ordinary case.

    The step is slowed down so that it cannot have finished within the pause,
    and the assertion is about the clock rather than about the geometry: an animation that
    began too early is not wrong about where it is going, only about when it set off, and
    that is invisible in every state it passes through and in the one it lands on.
    """
    presentation: Deck = deck_at(moving)
    page.add_style_tag(content=":root { --animo-duration: 4000ms; --animo-easing: linear }")
    page.wait_for_timeout(PAUSE)
    presentation.press("ArrowRight")
    flight = presentation.flight
    assert flight, "the step animated nothing at all"
    assert max(flight) < BEGINNING, (
        f"the step was already {max(flight):.0f} ms along when it began, "
        f"which is the {PAUSE} ms the page stood still"
    )


def test_stepping_back_returns_to_exactly_the_earlier_geometry(deck_at, moving):
    """A state is the same wherever it is arrived from, which is what makes it a state."""
    presentation: Deck = deck_at(moving)
    before = presentation.rects("m")[0]
    presentation.press("ArrowRight", 2).settle()
    assert presentation.position == (1, 2)
    presentation.press("ArrowLeft", 2).settle()
    assert presentation.position == (1, 0)
    assert presentation.rects("m")[0].approx(before), "the element did not come back"


def test_a_deep_link_snaps_to_the_state_without_animating(page, deck_at, moving):
    """What `typst watch` reloads into, and what every other test here relies on.

    The reload keeps the fragment, so the author comes back on the same subslide.
    Animating into a restored state would mean every recompile plays the step again.
    """
    presentation: Deck = deck_at(moving)
    unit = presentation.unit
    before = presentation.rects("m")[0]
    page.reload()
    presentation.goto(1, 1)
    assert page.evaluate("() => document.getAnimations().length") == 0
    after = presentation.rects("m")[0]
    assert after.x - before.x == pytest.approx(3 * CM * unit, abs=TOLERANCE)


def test_a_subslide_step_leaves_no_history_behind(page, deck_at, moving):
    """`replaceState`, not `pushState`, for subslides as well as for slides.

    A talk steps hundreds of times, and a history entry per step makes the browser's own
    back button useless for leaving the deck.
    """
    presentation: Deck = deck_at(moving)
    before = page.evaluate("() => history.length")
    presentation.press("ArrowRight", 2).settle()
    assert page.url.endswith("#1.2")
    assert page.evaluate("() => history.length") == before


# Scoping, and reaching every occurrence of a tag.


def test_one_tag_at_two_sites_moves_as_one_element(deck_at, typst: TypstRunner):
    """The same name in one slide addresses every site, which is the scoping rule.

    It is also what applies a display state to every epoch frame of a slide at once,
    since a frame holds one more occurrence of the same name.
    """
    body = mark("m") + "\n  " + mark("m", dx="6cm")
    presentation: Deck = deck_at(animated(typst, body, 'sub(move("m", x: 2cm))'))
    unit = presentation.unit
    before = presentation.rects("m")
    assert len(before) == 2
    after = presentation.goto(1, 1).rects("m")
    for one, other in zip(before, after, strict=True):
        assert other.x - one.x == pytest.approx(2 * CM * unit, abs=TOLERANCE)


def test_a_timeline_moves_only_the_tags_of_its_own_slide(deck_at, typst: TypstRunner):
    """A tag name means nothing outside the slide it sits in."""
    source = deck(
        f"slide(animation: {timeline('sub(move(\"m\", x: 3cm))')})[\n  {mark('m')}\n]",
        f"slide[\n  {mark('m')}\n]",
    )
    presentation: Deck = deck_at(typst.html(source, name="two.html"))
    untouched = presentation.goto(2, 0).rects("m")[0]
    moved = presentation.goto(1, 1).rects("m")[0]
    assert moved.x - untouched.x == pytest.approx(3 * CM * presentation.unit, abs=TOLERANCE)


def test_a_tag_inside_a_tag_is_animated_on_its_own(deck_at, typst: TypstRunner):
    """Two slots nested in two more, which is what a tag inside a tag emits.

    The inner tag's own group sits inside the outer tag's continuous slot, so the two
    displacements compose rather than replacing one another.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            '#tag("outer")[before #tag("inner")[middle] after]',
            'sub(move("outer", x: 2cm), move("inner", y: 1cm))',
        )
    )
    unit = presentation.unit
    outer, inner = presentation.rects("outer")[0], presentation.rects("inner")[0]
    presentation.goto(1, 1)
    moved_outer, moved_inner = presentation.rects("outer")[0], presentation.rects("inner")[0]
    assert moved_outer.x - outer.x == pytest.approx(2 * CM * unit, abs=TOLERANCE)
    assert moved_outer.y - outer.y == pytest.approx(0, abs=TOLERANCE)
    assert moved_inner.x - inner.x == pytest.approx(2 * CM * unit, abs=TOLERANCE)
    assert moved_inner.y - inner.y == pytest.approx(1 * CM * unit, abs=TOLERANCE)


def test_sites_of_one_name_that_disagree_all_start_out_hidden(deck_at, typst: TypstRunner):
    """The one place the four outputs do not agree, pinned down rather than left open.

    One rule addresses every site of a name at once, so the browser cannot honour two
    different `hidden:` arguments. It hides both, which withholds content rather than
    leaking it, and the manual says to use one argument or two names.
    """
    body = mark("d", hidden="true") + "\n  " + mark("d", dx="6cm")
    presentation: Deck = deck_at(animated(typst, body, "sub()"))
    assert [style["opacity"] for style in presentation.styles("d")] == ["0", "0"]


# The plan, as the page carries it.


def test_the_slide_carries_the_resolved_plan(deck_at, moving):
    """The channel, asserted where it is read rather than where it is written.

    It is a `data-` attribute so that the state a runtime applies can be read off the
    element it belongs to, in a browser's inspector as well as in a test.
    """
    presentation: Deck = deck_at(moving)
    states = presentation.plan["states"]
    assert len(states) == 3
    assert [state["tags"]["m"]["x"] for state in states] == pytest.approx(
        [0, 3 * CM, 4 * CM], abs=0.01
    )
    assert [state["tags"]["m"]["scale"] for state in states] == [1, 1, 2]
    assert [state["tags"]["m"]["hidden"] for state in states] == [False, False, False]
