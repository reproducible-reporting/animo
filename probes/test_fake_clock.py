# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A faked clock drives a timer without touching the document timeline*.

A deck that plays itself is a `setTimeout` in the runtime, and a `setTimeout` is exactly
what the animation harness cannot scrub: an animation is paused and told where it is,
while a timer only ever fires. So the timer is driven instead, with `playwright`'s own
fake clock, and the runtime carries no test seam at all.

Four properties make that work, and all four are asserted here, because each of them
could be lost in a `playwright` upgrade and the loss would show up as a flaky timing tier
rather than as a broken tool.

- Installed and then paused, the clock stops: a timer does not fire in real time.
- One length gets past the pause all the same: a timer of zero armed while the page is
  loading fires. A millisecond is enough to stop it, and so is arming it once the page has
  settled, so what a test may not do is expect a zero-length gap to stay pending.
- `run_for` fires the timers that fall due, in order, including the ones a fired timer
  sets, which is what makes a deck step itself more than once.
- The document timeline is the browser's own and is not faked, so the motion a timed step
  starts still runs in real time and is still scrubbable.

What the pause does reach is `requestAnimationFrame`, which stops firing with the timers,
so a frame cannot be waited for on such a page and an animation is read by scrubbing it
rather than by letting it run to a frame.
"""

import time

import pytest

# How long the page is left alone in real time before the clock is asked to move.
# Long enough to dwarf the timer it must not fire, short enough to pay for in three engines.
PAUSE = 300

# The timer under test, in milliseconds.
STEP = 1000

# Where the clock is stopped, as a time after the one it was installed at.
# An installed clock is still running and cannot be paused in its own past, and the two
# calls take real milliseconds, so this is a minute ahead rather than nothing at all.
# Nothing is loaded when the jump happens, so it has no timer to fire.
PAUSED_AT = 60_000

# A page that counts itself forward on a chain of timers, one every `STEP`, and publishes
# the count where a test can read it. This is the shape of the runtime's own autoplay: a
# timer armed whenever a step is entered, which the step it enters arms again.
PAGE = """<!doctype html>
<script>
  let count = 0;
  function advance() {
    count += 1;
    document.documentElement.dataset.count = String(count);
    setTimeout(advance, %d);
  }
  setTimeout(advance, %d);
</script>""" % (STEP, STEP)  # noqa: UP031

COUNT = "() => Number(document.documentElement.dataset.count ?? 0)"

# A page that arms four timers as it loads and records which of them fired, by name.
# Loaded by navigation rather than by `set_content`, because that is what a test of the
# HTML output does and because the two do not behave alike here.
LENGTHS = (0, 1, 5, STEP)
ARMING = """<!doctype html>
<script>
  window.fired = [];
  window.arm = (delay) => setTimeout(() => window.fired.push(delay), delay);
  %s
</script>""" % "\n  ".join(  # noqa: UP031
    f"arm({length});" for length in LENGTHS
)

FIRED = "() => window.fired"

# How long an animation is left to run in real time, and how far short of that it may
# report. It measures itself against the document timeline, which is updated once per
# frame, so it is behind by at most one. See *The document timeline is not a clock*.
FLIGHT = 400
FRAME = 100

# How much further into itself an animation may report than the real time that passed since
# it was created, in milliseconds.
# It cannot have begun before it existed, so real time is the bound, and the allowance covers
# the rounding of the two clocks that bound is read from.
# The real time is taken from python, because `performance.now()` is faked along with the
# timers and jumps by the whole of a `run_for`.
SLACK = 50

# Start an animation and leave it where a test can read it.
# Not awaited on a frame: `requestAnimationFrame` is faked along with the timers, and a
# page whose clock is stopped never reaches the frame such a wait asks for.
START = """() => {
    window.probe = document.documentElement.animate(
        [{opacity: 1}, {opacity: 0}],
        10000,
    );
}"""


@pytest.fixture
def counting(page):
    """A page whose timers only run when the clock is told to, loaded with it already stopped.

    The clock is installed before the content, because the runtime this stands in for arms
    its first timer as the page is loaded.
    """
    page.clock.install(time=0)
    page.clock.pause_at(PAUSED_AT)
    page.set_content(PAGE)
    return page


@pytest.fixture
def arming(page, tmp_path):
    """A navigated page that arms timers of four lengths as it loads, with the clock stopped."""
    path = tmp_path / "arming.html"
    path.write_text(ARMING)
    page.clock.install(time=0)
    page.clock.pause_at(PAUSED_AT)
    page.goto(path.as_uri())
    return page


def test_a_stopped_clock_fires_no_timer_in_real_time(counting):
    """What makes "it did not come early" an assertion rather than a race."""
    counting.wait_for_timeout(PAUSE + STEP)
    assert counting.evaluate(COUNT) == 0


def test_a_zero_length_timer_armed_while_loading_fires_anyway(arming):
    """The one length the pause does not hold, and the reason a test never counts on it.

    A gap of zero is the shape a deck joined by `hold: 0` has, and such a gap arms its
    timer as the page is loaded. A test that expected it to stay pending would be flaky
    rather than wrong, and only on a loaded machine, so it is asserted here instead: a
    timing test reaches the far side of such a gap with `run_for` and asserts where the
    deck rests, never where it is passing through.
    """
    arming.wait_for_timeout(PAUSE)
    assert arming.evaluate(FIRED) == [0]


def test_a_zero_length_timer_armed_after_loading_is_held(arming):
    """The other half, which is what keeps the pause worth having at all."""
    arming.wait_for_timeout(PAUSE)
    arming.evaluate("() => arm(0)")
    arming.wait_for_timeout(PAUSE)
    assert arming.evaluate(FIRED) == [0], "a timer armed on a settled page got past the pause"


def test_running_the_clock_fires_the_timers_that_fall_due(counting):
    """One step short of the timer, and then one millisecond past it."""
    counting.clock.run_for(STEP - 1)
    assert counting.evaluate(COUNT) == 0
    counting.clock.run_for(2)
    assert counting.evaluate(COUNT) == 1


def test_a_timer_set_by_a_timer_falls_due_in_the_same_run(counting):
    """A deck that steps itself twice does so on a chain, so the chain has to be followed.

    This is the property `fast_forward` does not have: it jumps the clock and fires each
    timer at most once, which would step such a page exactly one place however far it
    jumped.
    """
    counting.clock.run_for(3 * STEP)
    assert counting.evaluate(COUNT) == 3


def test_running_the_clock_does_not_run_the_animations(counting):
    """Why a delayed operation is asserted by scrubbing rather than by running the clock.

    Motion is driven by the Web Animations API, which measures itself against the document
    timeline, and the fake clock does not reach that timeline. Were it to, a step driven
    forward by a timer would arrive already over and no moment inside it could be stated.

    The bound is the real time that passed rather than nothing: the animation goes on
    running in real time while the clock is moved, and the calls around the move take real
    milliseconds. A fixed budget instead would measure the machine rather than the engine:
    the animation reported 168 ms on a workstation running the whole suite in parallel,
    against the 17 ms of *A faked clock drives a timer without touching the document
    timeline*.
    """
    started = time.monotonic()
    counting.evaluate(START)
    counting.clock.run_for(10 * STEP)
    current = counting.evaluate("() => probe.currentTime")
    real = (time.monotonic() - started) * 1000
    assert current < real + SLACK, (
        f"an animation was {current:.0f} ms in after the clock was moved {10 * STEP} ms, "
        f"{real:.0f} ms of real time after it was created"
    )


def test_an_animation_still_runs_while_the_clock_stands_still(counting):
    """The other half of the same claim: the motion a timed step starts is real motion.

    The comparison is not vacuous next to the test above: the same reading is taken after
    the same animation has been left alone, and only the kind of time that passed differs.
    """
    counting.evaluate(START)
    counting.wait_for_timeout(FLIGHT)
    assert counting.evaluate("() => probe.currentTime") > FLIGHT - FRAME
