# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: a deck that plays itself, and operations that arrive late or run long.

Two clocks meet here and are kept apart on purpose.

`wait:` is a `setTimeout` in the runtime, which is exactly what the animation harness
cannot scrub, so these tests stop the page's clock before the deck is loaded and state how
much time passes: `timed_deck_at` installs the fake clock and `Deck.run_for` fires the
timers that are due. Nothing in the runtime knows it is being tested.

`delay:` and `duration:` are the Web Animations API effect's own delay and duration, so
they run on the document timeline, which the fake clock leaves alone. An operation that
starts late or runs long is therefore asserted by scrubbing, as every other piece of motion
is, and never by racing it.
"""

import pytest
from decks import deck
from harness import EPOCH_GROUPS, Deck, TypstRunner

# How long a step takes in these tests, in milliseconds, and the moment sampled in it.
# Slowed down from animo's own 400 ms so that a paused animation cannot already have ended,
# and linear so that the moment sampled is the fraction of the step it looks like.
# Shorter than the 4 s the other browser modules use, because a delayed step is the one
# kind a test may also have to wait out: it runs for its delay and its duration together.
DURATION = 1000
MIDPOINT = DURATION / 2

SLOW = f":root {{ --animo-primitive-duration: {DURATION}ms; --animo-easing: linear }}"

# How long an operation is held back in these tests, in milliseconds.
# Half the step, so that the moment before it and the moment after it are both well inside.
DELAY = DURATION / 2

# How long an operation that states a duration of its own takes here, in milliseconds.
# Three times the deck's own step, so that a moment past the end of the step is still well
# inside it: an operation that never got its own duration would have finished by then.
OWN = 3 * DURATION


def timeline(*steps: str) -> str:
    """The animation argument of a slide, with the primitives imported inside it."""
    return "{ import anim: *\n  " + "\n  ".join(steps) + " }"


def animated(typst: TypstRunner, body: str, *steps: str, name: str = "deck.html", **slide):
    """Compile a one-slide deck with a timeline, as a file the browser can open."""
    extra = "".join(f", {key}: {value}" for key, value in slide.items())
    source = deck(f"slide(animation: {timeline(*steps)}{extra})[\n  {body}\n]")
    return typst.html(source, name=name)


LINE = '#tag("a", wrap: block)[A line that starts out hidden.]'


# A deck that plays itself: one timed subslide, then one timed slide.
#
# The waits are a second each, so a test can state a moment on either side of one without
# the numbers needing to be read twice.
SECOND = 1000

PLAYING = deck(
    'slide(animation: { import anim: *\n'
    '  sub(wait: 1, reveal("a"))\n'
    "  sub()\n"
    f"}})[\n  {LINE}\n]",
    "slide(wait: 1)[= Second]",
)


@pytest.fixture
def playing(typst: TypstRunner):
    """Two slides: a subslide on a timer, a step that waits for the presenter, a slide on one."""
    return typst.html(PLAYING, name="playing.html")


# The same deck timed from the other side: `hold:` names the gap after the step it is
# written on, where `wait:` names the gap before it, so these two decks run identically.
HELD = deck(
    'slide(hold: 1, animation: { import anim: *\n'
    '  sub(hold: 1, reveal("a"))\n'
    "  sub()\n"
    f"}})[\n  {LINE}\n]",
    "slide[= Second]",
)


@pytest.fixture
def held(typst: TypstRunner):
    """The `playing` deck with every gap timed by the state before it instead."""
    return typst.html(HELD, name="held.html")


# Two automatic gaps in a row, which is what backward travel has to get through.
CHAINED = deck(
    'slide(animation: { import anim: *\n'
    '  sub(wait: 1, reveal("a"))\n'
    "  sub(wait: 1)\n"
    "  sub()\n"
    f"}})[\n  {LINE}\n]",
)


@pytest.fixture
def chained(typst: TypstRunner):
    """One slide whose first two gaps are both on the clock."""
    return typst.html(CHAINED, name="chained.html")


# A gap of no length at all, which is the limiting case backward travel used to lose.
#
# The deck runs itself into its second slide the moment it is painted, so the state before
# the join is reachable for exactly no time by the clock alone.
JOINED = deck("slide(hold: 0)[= First]", "slide[= Second]")


@pytest.fixture
def joined(typst: TypstRunner):
    """Two slides joined by a gap of zero, the shape a build split over two slides has."""
    return typst.html(JOINED, name="joined.html")


# One slide with a join, then a run of two, and a state the presenter stops at between
# them: the deck rests at states 0, 1, 3 and 6 and runs through the rest.
#
# Every test below drives this deck with `run_for` and asserts where it rests, never where
# it is passing through, because a zero-length timer armed while the page loads is not held
# by the fake clock. See *Findings*.
RUN_ON = deck(
    'slide(animation: { import anim: *\n'
    '  sub(reveal("a"))\n'
    "  sub(hold: 0)\n"
    "  sub()\n"
    "  sub(hold: 0)\n"
    "  sub(hold: 0)\n"
    "  sub()\n"
    f"}})[\n  {LINE}\n]",
)


@pytest.fixture
def run_on(typst: TypstRunner):
    """One slide with a join in it, and a run of two joins after that."""
    return typst.html(RUN_ON, name="run-on.html")


# A join with a gap of a second in front of it, which gives the pause key a clock to stop:
# a stopped deck arms no timer at all, so a zero-length gap can be rested on here.
PACED = deck(
    'slide(animation: { import anim: *\n'
    '  sub(hold: 1, reveal("a"))\n'
    "  sub(hold: 0)\n"
    "  sub()\n"
    f"}})[\n  {LINE}\n]",
)


@pytest.fixture
def paced(typst: TypstRunner):
    """One slide that waits a second, then runs straight on through its next step."""
    return typst.html(PACED, name="paced.html")


# A gap the presenter owns, and a run of three automatic gaps behind it. One press forward
# takes the deck over the whole run, and one press back has to bring it back over.
TRAVELLED = deck(
    'slide(animation: { import anim: *\n'
    '  sub(reveal("a"))\n'
    "  sub(wait: 1)\n"
    "  sub(wait: 1)\n"
    "  sub(wait: 1)\n"
    f"}})[\n  {LINE}\n]",
)


@pytest.fixture
def travelled(typst: TypstRunner):
    """One slide whose first gap waits for the presenter and whose next three are timed."""
    return typst.html(TRAVELLED, name="travelled.html")


# A whole slide the deck runs through, which is the join that spans more than one boundary.
FLASHED = deck("slide[= First]", "slide(hold: 0)[= Second]", "slide[= Third]")


@pytest.fixture
def flashed(typst: TypstRunner):
    """Three slides, the middle one entered and left on the same press."""
    return typst.html(FLASHED, name="flashed.html")


# What a timer does.


def test_a_timed_subslide_advances_on_its_own(timed_deck_at, playing):
    """The whole point: a deck that is read rather than presented steps itself."""
    presentation: Deck = timed_deck_at(playing)
    assert presentation.position == (1, 0)
    presentation.run_for(SECOND - 1)
    assert presentation.position == (1, 0), "the step came early"
    presentation.run_for(2)
    assert presentation.position == (1, 1)


def test_the_first_waits_of_a_deck_are_measured_from_the_first_paint(timed_deck_at, playing):
    """There is no earlier trigger to measure from, and the deck is not waiting for a key.

    The clock is stopped before the page is loaded, so no time at all passes between the
    first paint and the assertion above it: a timer that were armed on the first key press
    instead would never fire here.
    """
    presentation: Deck = timed_deck_at(playing)
    presentation.run_for(SECOND)
    assert presentation.position == (1, 1)


def test_a_timed_slide_is_entered_on_its_own(timed_deck_at, playing):
    """One rule at both levels: the wait of the next position, whichever slide it is on."""
    presentation: Deck = timed_deck_at(playing).goto(1, 2)
    presentation.run_for(SECOND)
    assert presentation.position == (2, 0)


def test_a_step_that_says_nothing_waits_for_the_presenter(timed_deck_at, playing):
    """`wait: none` is the default, and it is what keeps a deck a presenter's deck.

    State 1 of the first slide is entered on a timer and is followed by a bare `sub()`,
    so the deck stops there however long it is left alone.
    """
    presentation: Deck = timed_deck_at(playing).goto(1, 1)
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 1), "a step with no wait was taken by a timer"


def test_a_manual_step_cancels_the_pending_timer(timed_deck_at, playing):
    """A presenter can always run ahead of the clock, and the deck does not then jump twice."""
    presentation: Deck = timed_deck_at(playing)
    presentation.press("ArrowRight")
    assert presentation.position == (1, 1)
    presentation.run_for(SECOND - 1)
    assert presentation.position == (1, 1), "the cancelled timer fired anyway"


# What `hold:` times, which is the gap `wait:` times, named from the other side.


def test_a_held_subslide_advances_on_its_own(timed_deck_at, held):
    """One timer, whichever of the two numbers armed it."""
    presentation: Deck = timed_deck_at(held).goto(1, 1)
    presentation.run_for(SECOND - 1)
    assert presentation.position == (1, 1), "the step came early"
    presentation.run_for(2)
    assert presentation.position == (1, 2)


def test_the_slides_own_hold_times_its_initial_state(timed_deck_at, held):
    """State 0 has no `sub`, so how long it stands there is written on the slide."""
    presentation: Deck = timed_deck_at(held)
    presentation.run_for(SECOND)
    assert presentation.position == (1, 1)


def test_a_hold_on_the_last_step_of_a_slide_enters_the_next(timed_deck_at, held):
    """A step does not have to know a slide boundary follows it to time the gap it opens."""
    presentation: Deck = timed_deck_at(held).goto(1, 1)
    presentation.run_for(SECOND)
    assert presentation.position == (1, 2)
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 2), "the last step of the slide held nothing"


# Backward travel, which the clock serves as it serves the way forward.


def test_backward_travel_carries_on_over_an_automatic_gap(timed_deck_at, travelled):
    """The clock that carries a deck forward over a gap carries it back over the same gap.

    The state a backward step lands on is one the deck leaves on its own going forward, so
    it leaves it on its own coming back, and after the same wait. A state inside a run is
    shown for as long in both directions.
    """
    presentation: Deck = timed_deck_at(travelled).goto(1, 3)
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 2)
    assert not presentation.paused
    presentation.run_for(SECOND - 1)
    assert presentation.position == (1, 2), "the travel ran ahead of the gap it was crossing"
    presentation.run_for(2)
    assert presentation.position == (1, 1)


def test_backward_travel_stops_where_the_deck_waits_for_the_presenter(
    timed_deck_at, playing
):
    """A gap the presenter owns is one the clock never crosses, in either direction.

    This is the shape of a build that runs into the next slide on a timer. The boundary is
    crossed back on the clock, and the travel ends on the state the presenter last pressed a
    key at, rather than on a state the audience saw for the length of one gap.
    """
    presentation: Deck = timed_deck_at(playing).goto(2, 0)
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 2)
    presentation.run_for(SECOND)
    assert presentation.position == (1, 1)
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 1), "the travel crossed a gap the presenter owns"
    assert not presentation.paused


def test_a_forward_step_turns_backward_travel_around(timed_deck_at, travelled):
    """A presenter who has seen enough of the way back steps forward and the deck plays on."""
    presentation: Deck = timed_deck_at(travelled).goto(1, 4)
    presentation.press("ArrowLeft")
    presentation.run_for(SECOND)
    assert presentation.position == (1, 2)
    presentation.press("ArrowRight")
    assert presentation.position == (1, 3)
    presentation.run_for(SECOND)
    assert presentation.position == (1, 4), "the clock stayed pointed backwards"


def test_backward_travel_stops_at_the_first_state_of_the_deck(timed_deck_at, playing):
    """The one end of the travel with nothing earlier to travel to, and the one clock stop.

    The gap that state carries would arm forwards and undo the step that just arrived, so
    the state would be reachable for that gap's length and no longer.
    """
    presentation: Deck = timed_deck_at(playing).goto(1, 1)
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 0)
    assert presentation.paused
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 0), "the clock took the deck back forward"


def test_a_forward_step_puts_back_the_clock_backward_travel_stopped(
    timed_deck_at, chained
):
    """A reader carried back to the first state expects the deck to play on when they move on."""
    presentation: Deck = timed_deck_at(chained).goto(1, 1)
    presentation.press("ArrowLeft")
    assert presentation.paused
    presentation.press("ArrowRight")
    assert presentation.position == (1, 1)
    assert not presentation.paused
    presentation.run_for(SECOND)
    assert presentation.position == (1, 2), "the clock stayed stopped"


def test_space_puts_back_the_clock_backward_travel_stopped(timed_deck_at, chained):
    """The other way out, for a reader who wants the deck to play on from where it is."""
    presentation: Deck = timed_deck_at(chained).goto(1, 1)
    presentation.press("ArrowLeft")
    presentation.press(" ")
    assert not presentation.paused
    assert presentation.position == (1, 0), "Space stepped instead of resuming"
    presentation.run_for(SECOND)
    assert presentation.position == (1, 1)


def test_a_backward_step_over_a_manual_gap_leaves_the_clock_alone(
    timed_deck_at, playing
):
    """Only a gap on the clock can defeat backward travel, so only that one stops it.

    A deck with no number in it therefore keeps the forward key every presentation remote
    sends, `Space` included, however its presenter walks through it.
    """
    presentation: Deck = timed_deck_at(playing).goto(1, 2)
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 1)
    assert not presentation.paused
    presentation.press(" ")
    assert presentation.position == (1, 2), "Space paused a deck with no clock to pause"


def test_a_backward_step_gets_over_a_gap_of_zero(timed_deck_at, joined):
    """The limiting case, and the reason the first state of a deck is a clock stop.

    A deck joined by a gap of zero runs into its second slide the moment it is painted.
    Arming that gap forwards again on the way back would leave the first slide reachable for
    no time at all, whatever a presenter did.
    """
    presentation: Deck = timed_deck_at(joined)
    presentation.run_for(1)
    assert presentation.position == (2, 0), "the join did not carry the deck over"
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 0)
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 0), "the join took the deck back over"


def test_a_backward_step_walks_back_over_a_join(timed_deck_at, run_on):
    """A gap of zero is a join, and a join is crossed in both directions.

    The state a join is measured from is left in the same breath as it is entered, so the
    audience never sees it at rest. Landing there would show a composition never shown.
    """
    presentation: Deck = timed_deck_at(run_on)
    presentation.press("ArrowRight", times=2).run_for(SECOND)
    assert presentation.position == (1, 3), "the join did not carry the deck through"
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 1), "the deck rested where it never rests"


def test_a_backward_step_walks_back_over_a_run_of_joins(timed_deck_at, run_on):
    """One press forward and one press back, whatever the run in between is made of.

    A join costs no press going forward, because the timer re-arms at every state it
    reaches, so it can cost none going back either.
    """
    presentation: Deck = timed_deck_at(run_on)
    presentation.press("ArrowRight", times=4).run_for(SECOND)
    assert presentation.position == (1, 6), "the run did not carry the deck through"
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 3), "walking back cost more presses than going did"


def test_a_backward_step_walks_back_over_a_slide_the_deck_runs_through(
    timed_deck_at, flashed
):
    """A join spans whatever lies between its two ends, a whole slide included."""
    presentation: Deck = timed_deck_at(flashed)
    presentation.press("ArrowRight").run_for(SECOND)
    assert presentation.position == (3, 0), "the join did not carry the deck through"
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 0), "the deck rested on the slide it ran through"


def test_a_stopped_clock_does_not_change_where_a_backward_step_lands(
    timed_deck_at, paced
):
    """Where a deck rests is what its timeline says, not what its clock is doing.

    A state the deck runs through stays addressable all the same, which is what makes the
    walk affordable: stepping forward through a stopped deck reaches it, and so does a
    fragment. Both are asserted here, because a stopped deck is the one place a test can
    rest on a zero-length gap at all: it arms no timer.
    """
    presentation: Deck = timed_deck_at(paced)
    presentation.press("ArrowRight")
    presentation.press(" ")
    assert presentation.paused, "Space stepped instead of stopping the clock"
    presentation.press("ArrowRight")
    assert presentation.position == (1, 2), "a stopped clock carried the deck over a join"
    presentation.press("ArrowRight")
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 1), "the stopped clock changed where the step landed"
    presentation.goto(1, 2)
    assert presentation.position == (1, 2), "a fragment could not reach a state in a run"


def test_a_pause_of_its_own_survives_a_forward_step(timed_deck_at, playing):
    """A deck stopped on purpose stays stopped, which a deck stopped on the way back does not.

    The two stops publish the same attribute and are told apart by what puts them back:
    stepping through a paused deck is browsing it, and stepping out of a backward step is
    carrying on.
    """
    presentation: Deck = timed_deck_at(playing)
    presentation.press(" ")
    presentation.press("ArrowRight")
    assert presentation.paused
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 1)


def test_a_deep_link_starts_its_own_timer_from_where_it_lands(timed_deck_at, playing):
    """The reload of `typst watch` is one of these, and it should keep playing."""
    presentation: Deck = timed_deck_at(playing).goto(1, 2)
    presentation.run_for(SECOND - 1)
    assert presentation.position == (1, 2)
    presentation.run_for(2)
    assert presentation.position == (2, 0)


# The pause key.


def test_space_pauses_a_deck_that_is_playing_itself(timed_deck_at, playing):
    """What a reader of a deck that plays itself asks for, and the clock stops for it."""
    presentation: Deck = timed_deck_at(playing)
    assert not presentation.paused
    presentation.press(" ")
    assert presentation.paused
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 0), "a paused deck advanced"


def test_a_second_space_resumes_with_what_is_left_of_the_wait(timed_deck_at, playing):
    """Resuming is not restarting: the deck picks the wait up where it stopped it."""
    presentation: Deck = timed_deck_at(playing)
    presentation.run_for(600)
    presentation.press(" ")
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 0)
    presentation.press(" ")
    assert not presentation.paused
    presentation.run_for(399)
    assert presentation.position == (1, 0), "the rest of the wait was thrown away"
    presentation.run_for(2)
    assert presentation.position == (1, 1)


def test_a_manual_step_while_paused_keeps_the_deck_paused(timed_deck_at, playing):
    """A paused deck is still a deck: stepping through it by hand is not resuming it."""
    presentation: Deck = timed_deck_at(playing)
    presentation.press(" ")
    presentation.press("ArrowRight")
    assert presentation.position == (1, 1)
    assert presentation.paused
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 1)


def test_the_pause_key_stops_backward_travel_and_resumes_it(timed_deck_at, travelled):
    """A pause keeps the direction of travel, so the deck resumes the way it was going.

    Every key but `Space` says which way it means. `Space` says nothing about direction and
    only stops the deck and starts it again.
    """
    presentation: Deck = timed_deck_at(travelled).goto(1, 3)
    presentation.press("ArrowLeft")
    presentation.press(" ")
    assert presentation.paused
    presentation.run_for(10 * SECOND)
    assert presentation.position == (1, 2), "a paused deck travelled on"
    presentation.press(" ")
    assert not presentation.paused
    presentation.run_for(SECOND)
    assert presentation.position == (1, 1), "the deck resumed the other way"


def test_the_pause_key_stops_the_motion_where_it_is(page, deck_at, typst: TypstRunner):
    """A pause stops the picture and not only the clock.

    A step that ran on to its end under a pause would leave the deck showing a state it was
    told not to reach yet. Real timers rather than the fake clock, because the animation in
    flight is what is measured here and a `wait:` of ten seconds is only there to give the
    key a clock to stop.
    """
    presentation: Deck = deck_at(
        animated(typst, LINE, 'sub(reveal("a"))', "sub(wait: 10)", name="in-flight.html")
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    presentation.press(" ")
    assert presentation.paused
    stopped = presentation.flight
    assert stopped, "the step had already ended when the deck was paused"
    assert presentation.flight == stopped, "the motion ran on under a pause"
    presentation.press(" ")
    presentation.settle()
    assert [style["opacity"] for style in presentation.styles("a")] == ["1"]


def test_space_steps_a_deck_that_waits_for_nobody(timed_deck_at, typst: TypstRunner):
    """The forward key every presentation remote sends, kept for the decks that have no clock."""
    presentation: Deck = timed_deck_at(
        animated(typst, LINE, 'sub(reveal("a"))', name="manual.html")
    )
    presentation.press(" ")
    assert presentation.position == (1, 1)
    assert not presentation.paused


# A delayed operation.


@pytest.fixture
def delayed(typst: TypstRunner):
    """A compiled deck whose one step reveals a line half a step late."""
    return animated(
        typst,
        LINE,
        f'sub(reveal("a", delay: {DELAY / 1000}))',
        name="delayed.html",
    )


def test_a_delayed_operation_holds_its_first_keyframe_until_it_starts(
    page, deck_at, delayed
):
    """The trap a delayed effect has to avoid, and the reason the effect fills backwards.

    The display state is written as inline style before the animation is created, so an
    effect that did not hold its first keyframe while it waits would show the state it is
    going to reach and then jump back to where it started.
    """
    presentation: Deck = deck_at(delayed)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    presentation.scrub(DELAY / 2)
    assert [style["opacity"] for style in presentation.styles("a")] == ["0"]
    presentation.scrub(DELAY + DURATION / 2)
    halfway = float(presentation.styles("a")[0]["opacity"])
    assert 0.4 < halfway < 0.6, f"the delayed reveal was {halfway} halfway through its own step"


def test_a_delayed_operation_ends_where_an_undelayed_one_does(deck_at, delayed):
    """A delay says when, and nothing about what: the state it lands on is the same one.

    At animo's own step duration rather than the slowed one, because this is the one
    assertion here that waits the whole step out instead of stating a moment in it.
    """
    presentation: Deck = deck_at(delayed)
    presentation.press("ArrowRight")
    presentation.settle()
    assert [style["opacity"] for style in presentation.styles("a")] == ["1"]


def test_two_operations_of_one_step_keep_their_own_moments(page, deck_at, typst: TypstRunner):
    """One effect has one delay, so a step with two moments in it is two effects.

    They are still created in one task and still start on the same frame, which is what
    keeps the step's one clock: the delay is the effect's own and never a timer.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            LINE,
            f'sub(reveal("a"), move("a", dx: 2cm, delay: {DELAY / 1000}))',
            name="staggered.html",
        )
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert sorted(presentation.animating, key=sorted) == [{"opacity"}, {"translate"}]
    delays = page.evaluate(
        "() => document.getAnimations().map(a => a.effect.getTiming().delay).sort()"
    )
    assert delays == [0, DELAY]


def test_a_step_that_times_nothing_is_still_one_effect(page, deck_at, typst: TypstRunner):
    """Two properties timed alike share their effect, which is every step that says nothing."""
    presentation: Deck = deck_at(
        animated(
            typst,
            LINE,
            'sub(reveal("a"), move("a", dx: 2cm))',
            name="together.html",
        )
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert presentation.animating == [{"opacity", "translate"}]


# An operation with a duration of its own.


def timings(page, field: str) -> list:
    """One field of the timing of every animation now in flight, sorted.

    Read off the effect rather than off the clock: a duration is what the operation asked
    the browser for, and the browser is what says whether it was asked.
    """
    return sorted(
        page.evaluate(
            f"() => document.getAnimations().map(a => a.effect.getTiming().{field})"
        )
    )


@pytest.fixture
def slow_reveal(typst: TypstRunner):
    """A compiled deck whose one step reveals a line over three times the deck's own step."""
    return animated(
        typst,
        LINE,
        f'sub(reveal("a", duration: {OWN / 1000}))',
        name="duration.html",
    )


def test_an_operation_takes_the_duration_it_states(page, deck_at, slow_reveal):
    """The whole point: one step at a tempo of its own, in a deck that keeps its own.

    Asserted by scrubbing to a moment the deck's own step would already have ended at,
    rather than by racing the operation to it.
    """
    presentation: Deck = deck_at(slow_reveal)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert timings(page, "duration") == [OWN]
    presentation.scrub(DURATION + MIDPOINT)
    halfway = float(presentation.styles("a")[0]["opacity"])
    assert 0.4 < halfway < 0.6, f"the reveal was {halfway} halfway through its own duration"


def test_an_operation_that_states_nothing_takes_the_decks_own_step(
    page, deck_at, typst: TypstRunner
):
    """`auto` is the default, and the number it stands for lives in the stylesheet.

    So a deck that restates `--animo-primitive-duration` reaches this operation and the one above
    goes on taking what it asked for, which is what `auto` rather than a number is for.
    """
    presentation: Deck = deck_at(
        animated(typst, LINE, 'sub(reveal("a"))', name="auto.html")
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert timings(page, "duration") == [DURATION]
    presentation.settle().press("ArrowLeft")
    presentation.settle()
    page.add_style_tag(content=":root { --animo-primitive-duration: 250ms }")
    presentation.press("ArrowRight")
    assert timings(page, "duration") == [250]


def test_a_stated_duration_still_follows_a_delay_of_its_own(
    page, deck_at, typst: TypstRunner
):
    """The two are one record and become one effect, so a step may say both."""
    presentation: Deck = deck_at(
        animated(
            typst,
            LINE,
            f'sub(reveal("a", delay: {DELAY / 1000}, duration: {OWN / 1000}))',
            name="both.html",
        )
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert timings(page, "delay") == [DELAY]
    assert timings(page, "duration") == [OWN]


def test_a_step_ends_when_the_last_of_its_operations_does(
    page, deck_at, typst: TypstRunner
):
    """Two durations in one step are two effects, and the step lasts as long as the longer.

    Read as the audience sees it: at a moment past the end of the short one and inside the
    long one, the first has arrived and the second is still on its way.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            LINE + '\n  #tag("b", wrap: block)[And a second line.]',
            f'sub(reveal("a", duration: {MIDPOINT / 1000}),'
            f' reveal("b", duration: {OWN / 1000}))',
            name="two-durations.html",
        )
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert timings(page, "duration") == [MIDPOINT, OWN]
    presentation.scrub(DURATION)
    assert presentation.styles("a")[0]["opacity"] == "1", "the short operation had not ended"
    ongoing = float(presentation.styles("b")[0]["opacity"])
    assert 0.2 < ongoing < 0.5, f"the long operation was {ongoing} a third of the way in"


# A backward step, which is the step it undoes played from the other end.


def schedule(page) -> dict[str, float]:
    """When each animation now in flight starts, keyed by the tag it is animating.

    Read off the effect rather than off the clock, as the durations above are: a delay is
    what the operation asked the browser for. One entry per tag, so a step that animates
    two properties of one tag is not what this reads.
    """
    return dict(
        page.evaluate(
            """() => document.getAnimations().map((animation) => [
                animation.effect.target.parentElement.dataset.typstLabel,
                animation.effect.getTiming().delay,
            ])"""
        )
    )


LINES = "\n  ".join(
    f'#tag("{name}", wrap: block)[Line {name}.]' for name in "abc"
)

# Three operations of one step, arriving one after another, the last of them slower than
# the deck's own step. The delays alone would not say which order they leave in: what does
# is where each of them ends, which is what mirroring the step is about.
STAGGERED = (
    'sub(reveal("a"),'
    f' reveal("b", delay: {DELAY / 1000}),'
    f' reveal("c", delay: {DURATION / 1000}, duration: {OWN / 1000}))'
)

# How long that step lasts: the last operation of it starts after one step of the deck and
# then runs for three, and nothing else is still going by then.
STEP = DURATION + OWN


@pytest.fixture
def staggered(typst: TypstRunner):
    """A compiled deck whose one step brings three lines up one after the other."""
    return animated(typst, LINES, STAGGERED, name="staggered.html")


def test_a_backward_step_mirrors_the_schedule(page, deck_at, delayed):
    """A backward step is the forward one played from the other end.

    The one operation of this step is the last to arrive because it is the only one, so
    going back it is the first to leave: the delay that held it back moves to the end of
    the step, where it holds the step open for exactly as long.
    """
    presentation: Deck = deck_at(delayed)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert timings(page, "delay") == [DELAY]
    presentation.settle().press("ArrowLeft")
    assert presentation.position == (1, 0)
    assert timings(page, "delay") == [0]


def test_a_backward_step_reverses_the_order_its_operations_arrived_in(
    page, deck_at, staggered
):
    """The last thing the audience saw arrive is the first thing they see leave.

    Each operation keeps its own duration and is mirrored about the length of the step, so
    an operation that ran from `delay` to `delay + duration` runs from the other side of
    the step to the other side of where it started.
    """
    presentation: Deck = deck_at(staggered)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert schedule(page) == {"a": 0, "b": DELAY, "c": DURATION}
    presentation.settle().press("ArrowLeft")
    assert presentation.position == (1, 0)
    assert schedule(page) == {
        "a": STEP - DURATION,
        "b": STEP - DELAY - DURATION,
        "c": 0,
    }


def test_a_backward_step_keeps_the_duration_of_every_operation(page, deck_at, staggered):
    """A mirror says when, and nothing about how long: the step lasts the same either way."""
    presentation: Deck = deck_at(staggered)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert timings(page, "duration") == [DURATION, DURATION, OWN]
    presentation.settle().press("ArrowLeft")
    assert timings(page, "duration") == [DURATION, DURATION, OWN]


def test_the_last_line_to_arrive_is_the_first_to_go(page, deck_at, staggered):
    """The same claim as the schedule above, read as the audience sees it.

    A third of the way into the long operation the line that arrived last is halfway out,
    and the two that were on the screen before it are untouched.
    """
    presentation: Deck = deck_at(staggered)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    presentation.settle().press("ArrowLeft")
    presentation.scrub(OWN / 2)
    leaving = float(presentation.styles("c")[0]["opacity"])
    assert 0.4 < leaving < 0.6, f"the last line to arrive was {leaving} halfway out"
    assert [presentation.styles(name)[0]["opacity"] for name in "ab"] == ["1", "1"], (
        "a line that arrived earlier left before the one that arrived last"
    )


def test_a_backward_step_ends_on_the_state_it_walked_back_to(deck_at, staggered):
    """A mirror is a schedule and not a state: where it lands is where it always landed."""
    presentation: Deck = deck_at(staggered)
    presentation.press("ArrowRight")
    presentation.settle().press("ArrowLeft")
    presentation.settle()
    assert [presentation.styles(name)[0]["opacity"] for name in "abc"] == ["0"] * 3


def test_a_zero_deck_duration_snaps_a_stated_duration(page, deck_at, slow_reveal):
    """The reduced-motion rule, and the one assertion here that must not regress.

    A media query cannot reach a number written in a typst source, so the runtime is where
    it is enforced, in the one line that already reads the property for a step and a delay.
    """
    presentation: Deck = deck_at(slow_reveal)
    page.add_style_tag(content=":root { --animo-primitive-duration: 0s }")
    presentation.press("ArrowRight")
    assert presentation.animating == []
    assert [style["opacity"] for style in presentation.styles("a")] == ["1"]


def test_reduced_motion_snaps_a_stated_duration(page, deck_at, typst: TypstRunner):
    """The same path, reached the way a reader actually reaches it."""
    page.emulate_media(reduced_motion="reduce")
    presentation: Deck = deck_at(
        animated(
            typst,
            LINE,
            f'sub(reveal("a", duration: {OWN / 1000}))',
            name="reduced-duration.html",
        )
    )
    presentation.press("ArrowRight")
    assert presentation.animating == []
    assert [style["opacity"] for style in presentation.styles("a")] == ["1"]


# A delayed structural operation, which holds back the crossfade of its region.

CLAIM = '#tag("claim", wrap: block)[A short claim.]\n\n  Text after the tag.'
LONGER = (
    "Actually the opposite holds, and this replacement is long enough to wrap onto a "
    "second line, which pushes the rest of the region down."
)


def region_paint(presentation: Deck, label: str) -> list[dict]:
    """What one region's group paints in every epoch rendering, in epoch order.

    The boundary crossfades the *labelled* group of the region, which is the outer slot,
    where a display state goes on the unlabelled one inside it. Visibility is read beside
    the opacity because the outgoing rendering is hidden as a whole and the regions it
    hands over are what take their visibility back.
    """
    slide, _ = presentation.position
    return presentation.page.evaluate(
        f"""() => Array.from(
            document.querySelectorAll('[data-animo-slide="{slide}"] {EPOCH_GROUPS}'),
            (frame) => {{
                const group = frame.querySelector('[data-typst-label="{label}"]');
                const style = getComputedStyle(group);
                return {{visibility: style.visibility, opacity: Number(style.opacity)}};
            }},
        )"""
    )


def test_a_delayed_structural_operation_holds_back_its_regions_crossfade(
    page, deck_at, typst: TypstRunner
):
    """The outgoing frame goes on painting the region it is handing over for the whole delay.

    The frames themselves have already swapped, which is invisible: they are
    pixel-identical everywhere but in the region the boundary redraws.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            CLAIM,
            f'sub(replace("claim", delay: {DELAY / 1000})[{LONGER}])',
            name="structural.html",
        )
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    presentation.scrub(DELAY / 2)
    assert region_paint(presentation, "claim") == [
        {"visibility": "visible", "opacity": 1},
        {"visibility": "visible", "opacity": 0},
    ], "the region crossfaded during the delay instead of after it"
    presentation.scrub(DELAY + DURATION)
    assert region_paint(presentation, "claim") == [
        {"visibility": "visible", "opacity": 0},
        {"visibility": "visible", "opacity": 1},
    ]


def test_a_structural_duration_holds_its_regions_crossfade_open(
    page, deck_at, typst: TypstRunner
):
    """A long `replace` keeps two frames laid out, and both paint the region while it runs.

    The moment sampled is past the end of the deck's own step, so a crossfade that had not
    taken the operation's duration would be over by then and the outgoing frame dark.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            CLAIM,
            f'sub(replace("claim", duration: {OWN / 1000})[{LONGER}])',
            name="structural-duration.html",
        )
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    # One effect per frame: the region fades out in the outgoing one and in in the
    # incoming one, and both take the duration the operation stated.
    assert timings(page, "duration") == [OWN, OWN]
    presentation.scrub(DURATION + MIDPOINT)
    outgoing, incoming = region_paint(presentation, "claim")
    assert outgoing["visibility"] == "visible", "the outgoing frame stopped painting early"
    assert 0.4 < outgoing["opacity"] < 0.6, outgoing
    assert 0.4 < incoming["opacity"] < 0.6, incoming
    presentation.scrub(OWN)
    assert region_paint(presentation, "claim") == [
        {"visibility": "visible", "opacity": 0},
        {"visibility": "visible", "opacity": 1},
    ]


def test_a_boundary_overtaken_mid_crossfade_keeps_its_region_opaque(
    page, deck_at, typst: TypstRunner
):
    """The answer to whether a duration may outlive its step: it may, and it is overtaken.

    A long `replace` that is still running when the next boundary is crossed leaves two
    frames painting the region at once, which is a state the epoch model has never had to
    represent. Every frame that is not the one being entered hands the region over on the
    new boundary's clock, so all of them fade out under one easing while the incoming one
    fades in and the region's ink stays at exactly one throughout.
    The overlap is not particular to a duration: a `wait:` shorter than a step, or a
    presenter clicking twice, reaches it as well.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            CLAIM,
            f'sub(replace("claim", duration: {OWN / 1000})[{LONGER}])',
            'sub(replace("claim")[A third claim.])',
            name="overtaken.html",
        )
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    presentation.scrub(MIDPOINT)
    ink = lambda: sum(frame["opacity"] for frame in region_paint(presentation, "claim"))
    assert ink() == pytest.approx(1, abs=0.01), "the first crossfade did not add to one"
    presentation.press("ArrowRight")
    assert ink() == pytest.approx(1, abs=0.01), "the region dipped when it was overtaken"
    presentation.scrub(MIDPOINT)
    assert ink() == pytest.approx(1, abs=0.01), "the region dipped halfway through"
    presentation.scrub(DURATION)
    assert region_paint(presentation, "claim") == [
        {"visibility": "visible", "opacity": 0},
        {"visibility": "visible", "opacity": 0},
        {"visibility": "visible", "opacity": 1},
    ]


def test_a_step_that_walks_back_over_a_join_hands_over_every_boundary_it_crosses(
    page, deck_at, typst: TypstRunner
):
    """A backward step that walked over a join runs between epochs that are not neighbours.

    Each of the boundaries it crosses is a region to hand over, so the step takes the union
    of them and the rendering being entered fades in against all of them at once, which is
    what the crossfade already does for a boundary crossed while an earlier one is running.
    Handing over only the nearest one would cut the rest, and the region would jump.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            CLAIM,
            f'sub(hold: 0, replace("claim")[{LONGER}])',
            'sub(replace("claim")[A third claim.])',
            name="run-on-regions.html",
        )
    ).goto(1, 2)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 0), "the step did not walk back over the join"
    presentation.scrub(MIDPOINT)
    incoming, skipped, outgoing = region_paint(presentation, "claim")
    assert 0.4 < incoming["opacity"] < 0.6, "the rendering being entered cut instead"
    assert 0.4 < outgoing["opacity"] < 0.6, "the rendering being left cut instead"
    # The rendering in the middle was already dark, since the step that walked over it had
    # handed it over on the way through, so it has nothing to fade and paints nothing.
    assert skipped["opacity"] == 0, skipped
    ink = incoming["opacity"] + skipped["opacity"] + outgoing["opacity"]
    assert ink == pytest.approx(1, abs=0.01), "the region dipped while it was handed over"


# A join that runs out of a slide, which is the one backward step that moves two things.

# How long a slide boundary takes in these tests, in milliseconds.
# Stated rather than left at animo's own, and different from the step above it, because a
# join walked back over runs both at once and the two clocks are what tell them apart.
BOUNDARY = 2 * DURATION

JOINING = f"{SLOW}\n:root {{ --animo-transition-duration: {BOUNDARY}ms }}"

# A build that spills into the next slide: one press starts the step's own motion and the
# boundary, which is what `hold: 0` is written on a step for.
SPILLING = deck(
    'slide(animation: { import anim: *\n'
    '  sub(hold: 0, reveal("a"))\n'
    f"}})[\n  {LINE}\n]",
    "slide[= Second]",
)

# The same join with something to lay out again on the way, so that walking back over it
# has an epoch boundary to hand back as well as a display state to undo.
SPILLING_REGION = deck(
    'slide(animation: { import anim: *\n'
    f'  sub(hold: 0, replace("claim")[{LONGER}])\n'
    f"}})[\n  {CLAIM}\n]",
    "slide[= Second]",
)


@pytest.fixture
def spilling(typst: TypstRunner):
    """Two slides, the first of which runs into the second while its own step is moving."""
    return typst.html(SPILLING, name="spilling.html")


@pytest.fixture
def spilling_region(typst: TypstRunner):
    """The same, with the step that spills laying its slide out again."""
    return typst.html(SPILLING_REGION, name="spilling-region.html")


def test_a_backward_step_over_a_join_rewinds_the_slide_it_lands_on(
    page, deck_at, spilling
):
    """The slide being entered is below its own last state, and the way back says so.

    Going forward the audience saw one motion: the step running inside the slide while the
    boundary carried it away. A backward step that snapped that slide into place would
    crossfade a picture the audience never saw, so the slide moves as the boundary crosses
    it, which is the same pair of clocks started on the same frame.
    """
    presentation: Deck = deck_at(spilling)
    page.add_style_tag(content=JOINING)
    presentation.press("ArrowRight")
    presentation.settle()
    assert presentation.position == (2, 0), "the join did not carry the deck through"
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 0), "the step did not walk back over the join"
    assert timings(page, "duration") == [DURATION, BOUNDARY, BOUNDARY], (
        "the slide being rewound and the boundary did not take their own clocks"
    )
    presentation.scrub(MIDPOINT)
    halfway = float(presentation.styles("a")[0]["opacity"])
    assert 0.4 < halfway < 0.6, f"the line was {halfway} halfway back out"


def test_a_backward_step_over_a_join_hands_the_region_back(
    page, deck_at, spilling_region
):
    """The epoch boundary such a step walks back over is crossed rather than snapped.

    It is the same handover an ordinary backward step makes, on a slide the deck is
    entering rather than one it is standing on.
    """
    presentation: Deck = deck_at(spilling_region)
    page.add_style_tag(content=JOINING)
    presentation.press("ArrowRight")
    presentation.settle()
    assert presentation.position == (2, 0), "the join did not carry the deck through"
    presentation.press("ArrowLeft")
    assert presentation.position == (1, 0), "the step did not walk back over the join"
    presentation.scrub(MIDPOINT)
    incoming, outgoing = region_paint(presentation, "claim")
    assert 0.4 < incoming["opacity"] < 0.6, "the rendering being entered cut instead"
    assert 0.4 < outgoing["opacity"] < 0.6, "the rendering being left cut instead"


# A forward step, which enters a slide rather than rewinding one.

STEPPED = deck(
    "slide[= First]",
    'slide(animation: { import anim: *\n'
    '  sub(reveal("a"))\n'
    f"}})[\n  {LINE}\n]",
)


def test_a_forward_step_snaps_a_slide_that_was_left_further_on(
    page, deck_at, typst: TypstRunner
):
    """Only a backward step rewinds the slide it enters, and this is why it is only that one.

    A slide keeps the state it was last shown in, so a forward step may enter one that is
    showing a later state than the one it is entering it at. Animating out of that state
    would play a step the audience was shown no route to, backwards, while the slide is
    coming up.
    """
    presentation: Deck = deck_at(typst.html(STEPPED, name="stepped.html"))
    page.add_style_tag(content=JOINING)
    presentation.goto(2, 1).goto(1, 0)
    presentation.press("ArrowRight")
    assert presentation.position == (2, 0)
    presentation.scrub(0)
    assert [style["opacity"] for style in presentation.styles("a")] == ["0"], (
        "the slide being entered rewound itself while it was coming up"
    )


# What reduced motion does to the three of them.


def test_a_snapping_step_drops_a_delay_with_the_duration(page, deck_at, delayed):
    """A step with no motion in it has no moment for an operation to be late for.

    `--animo-primitive-duration: 0ms` is the one line a reader who asked for less motion reaches
    through the media query in animo's own stylesheet, and it is where the runtime reads
    the question: a step that snaps snaps whole, delays and all.
    """
    presentation: Deck = deck_at(delayed)
    page.add_style_tag(content=":root { --animo-primitive-duration: 0ms }")
    presentation.press("ArrowRight")
    assert presentation.animating == []
    assert [style["opacity"] for style in presentation.styles("a")] == ["1"]


def test_reduced_motion_drops_a_delay(page, deck_at, typst: TypstRunner):
    """The same path, reached the way a reader actually reaches it."""
    page.emulate_media(reduced_motion="reduce")
    presentation: Deck = deck_at(
        animated(
            typst,
            LINE,
            f'sub(reveal("a", delay: {DELAY / 1000}))',
            name="reduced.html",
        )
    )
    presentation.press("ArrowRight")
    assert presentation.animating == []
    assert [style["opacity"] for style in presentation.styles("a")] == ["1"]


def test_reduced_motion_keeps_a_wait(page, timed_deck_at, typst: TypstRunner):
    """A wait is pacing rather than motion, and zeroing it would run the deck through itself.

    A reader who asked for less motion asked for less motion, not for a deck that arrives
    at its last slide before they have read the first.
    """
    page.emulate_media(reduced_motion="reduce")
    presentation: Deck = timed_deck_at(typst.html(PLAYING, name="reduced-wait.html"))
    presentation.run_for(SECOND - 1)
    assert presentation.position == (1, 0), "a wait was zeroed with the durations"
    presentation.run_for(2)
    assert presentation.position == (1, 1)


# A wait shorter than the step it interrupts.


def test_a_step_interrupted_by_a_shorter_wait_continues_from_where_it_is(
    page, timed_deck_at, typst: TypstRunner
):
    """A wait is measured from its predecessor's trigger, not from the end of its motion.

    So a wait shorter than a step's own duration interrupts it, and that needs no rule of
    its own: an interrupted step continues from where it is, because the display state is
    the state and the animation is only the route to it.
    """
    source = deck(
        "slide(animation: { import anim: *\n"
        '  sub(wait: 1, reveal("a"))\n'
        '  sub(wait: 1, hide("a"))\n'
        f"}})[\n  {LINE}\n]"
    )
    presentation: Deck = timed_deck_at(typst.html(source, name="interrupted.html"))
    page.add_style_tag(content=SLOW)
    presentation.run_for(SECOND)
    assert presentation.position == (1, 1)
    presentation.scrub(MIDPOINT)
    presentation.run_for(SECOND)
    assert presentation.position == (1, 2)
    resumed = page.evaluate(
        "() => document.getAnimations().map(a => a.effect.getKeyframes()[0].opacity)"
    )
    assert resumed == ["0.5"], f"the step restarted rather than turning round: {resumed}"
