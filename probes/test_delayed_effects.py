# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A delayed effect does not hold its first keyframe unless it is told to*.

An effect with a delay has a phase before it runs, and what the element shows during that
phase is decided by the fill mode alone. With `fill: none` the element shows whatever the
style underneath says, which for a runtime that writes the state it is arriving at as
inline style is the state at the *end* of the animation: the element jumps ahead, waits
there, and then jumps back to where it started to animate forwards again.

`fill: backwards` is what holds the first keyframe instead, and it is what animo writes on
every delayed effect. The second half of this module is why it can be written
unconditionally: an animation that fills backwards is still dropped when it finishes, so
"nothing is in flight" stays a question the page can answer.
"""

import pytest

# The shape of the effect under test, in milliseconds.
# The delay is long enough that a moment inside it is unambiguous, and the duration long
# enough that the element is still animating when the delay is over.
DELAY = 500
DURATION = 1000

# The page: one element the style underneath says is fully opaque.
# The animation runs from transparent to opaque, so the value during the delay tells the
# two fill modes apart with no arithmetic: 0 is the first keyframe, 1 is the style.
PAGE = """<!doctype html>
<div id="target" style="width: 50px; height: 50px; background: red; opacity: 1"></div>"""

# The JavaScript below is full of braces,
# so percent formatting is what keeps it readable as JavaScript:
# an f-string or `str.format` would have to double every one of them.
DURING_THE_DELAY = """fill => {
    const target = document.getElementById("target");
    const animation = target.animate(
        [{opacity: "0"}, {opacity: "1"}],
        {duration: %d, delay: %d, fill},
    );
    animation.pause();
    animation.currentTime = %d;
    return getComputedStyle(target).opacity;
}""" % (DURATION, DELAY, DELAY / 2)  # noqa: UP031

AFTER_IT_FINISHES = """fill => {
    const target = document.getElementById("target");
    const animation = target.animate(
        [{opacity: "0"}, {opacity: "1"}],
        {duration: %d, delay: %d, fill},
    );
    animation.finish();
    return document.getAnimations().length;
}""" % (DURATION, DELAY)  # noqa: UP031


@pytest.fixture
def target(page):
    """A page holding one element with an opacity of its own."""
    page.set_content(PAGE)
    return page


@pytest.mark.parametrize(
    ("fill", "shown"),
    [("none", "1"), ("backwards", "0"), ("both", "0")],
)
def test_the_fill_mode_alone_decides_what_a_delay_shows(target, fill, shown, browser_name):
    """The finding itself, over the three fill modes that can be written.

    The comparison is not vacuous: the element's own style says `1` and the first keyframe
    says `0`, so the two answers are the two ends of the animation and neither can be
    reached by accident.
    """
    assert target.evaluate(DURING_THE_DELAY, fill) == shown, (
        f"{browser_name} shows {fill!r} differently during the delay of an effect"
    )


@pytest.mark.parametrize("fill", ["none", "backwards"])
def test_an_effect_that_fills_backwards_is_still_dropped_when_it_finishes(target, fill):
    """Why the fill mode can be written on every effect and not only on the delayed ones.

    A finished effect that fills backwards is not in effect any more, so the animation is
    no longer relevant and leaves `getAnimations()`, exactly as one that fills nothing
    does. That is what lets a page be asked whether anything is still in flight.
    """
    assert target.evaluate(AFTER_IT_FINISHES, fill) == 0
