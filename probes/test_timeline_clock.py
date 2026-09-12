# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *The document timeline is not a clock*.

`document.timeline.currentTime` is the time of the last frame the browser drew, and a
browser that has nothing to draw draws nothing. A page that has sat still therefore reads
a time from the past, and an animation handed that time as its `startTime` is already
partway through, or over, before it is first drawn.

The behaviour animo relies on instead is the one it gets by saying nothing: an animation
created without a start time is pending until the next frame, and every animation created
in the same task is started at that frame with the same time.
"""

import pytest

# How long the page is left alone before the measurement, in milliseconds.
# Long enough to dwarf a frame, short enough to pay for in three engines.
PAUSE = 500

# How far the head start of a stamped animation may be read from the lag it was taken off,
# in milliseconds, which is a frame at the 60 Hz the engines run headless at.
# The two are either the same instant or a whole pause apart, so they are never in danger
# of being confused and the allowance can be generous.
FRAME = 100

# How much further into itself an animation may report than the time that really passed
# since it was created, in milliseconds.
# It cannot have begun before it existed, so real time is the bound, and the allowance
# covers the rounding of the two clocks that bound is read from.
# A budget for the frames instead would measure the machine rather than the engine:
# a loaded continuous integration runner spent 111 ms on the two frames of a deck test.
SLACK = 50

# Whether an engine's document timeline stands still while the page draws no frames.
#
# Freezing is what the specification describes, since it says the time is updated once per
# frame, so firefox 153 is the one that follows it. Chromium 151 refreshes the time on a
# read from outside a frame, and so does playwright's webkit 26.5, measured in a container
# because no webkit build runs on every contributor's distribution: it reported a lag of
# exactly zero after a 500 ms pause and after a 3 s one alike.
# A changed value here is a finding that changed, not a probe that needs fixing.
FREEZES_WHILE_IDLE = {"chromium": False, "firefox": True, "webkit": False}

# Start an animation after a pause, twice: once left to the browser, and once told to have
# begun at the document timeline's current time, which is what this finding is about.
#
# Both are read after a frame has been drawn. Before that they read the same, because an
# animation's current time is measured against the timeline rather than against real time,
# so a stale timeline hides its own staleness until it is refreshed.
#
# The real time those two frames took is measured alongside them, because it is what the
# scheduled animation's own reading is held against.
MEASURE = """async () => {
    const target = document.body;
    const began = performance.now();
    const lag = began - document.timeline.currentTime;
    const scheduled = target.animate([{opacity: 1}, {opacity: 0}], 10000);
    const stamped = target.animate([{opacity: 1}, {opacity: 0}], 10000);
    stamped.startTime = document.timeline.currentTime;
    await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
    return {
        lag,
        elapsed: performance.now() - began,
        scheduled: scheduled.currentTime,
        stamped: stamped.currentTime,
    };
}"""


@pytest.fixture
def measured(page, open_page):
    """The four numbers, taken after the page has been left alone for `PAUSE`."""
    page.set_content("<!doctype html><p>still</p>")
    page.wait_for_timeout(PAUSE)
    return page.evaluate(MEASURE)


def test_an_animation_the_browser_schedules_begins_at_its_beginning(measured):
    """The behaviour the runtime leans on, and the reason it names no start time.

    A pending animation is started at the next frame, which is a fresh one however long
    the page stood still, so a step taken after a pause plays from the beginning.
    How far in it is by the time it is read is bounded by the time that really passed
    since it was created, and not by what a frame is expected to cost.
    """
    assert measured["scheduled"] < measured["elapsed"] + SLACK, (
        f"an animation created without a start time was {measured['scheduled']:.0f} ms in, "
        f"{measured['elapsed']:.0f} ms after it was created"
    )


def test_a_start_time_from_the_document_timeline_can_lie_in_the_past(measured, browser_name):
    """The finding itself, in the two halves that matter.

    The first half is the mechanism and holds in every engine: an animation stamped with
    the timeline's current time begins exactly as far in as that time lags real time.
    The second half is how large that lag gets, which is where the engines differ.
    """
    behind = measured["stamped"] - measured["scheduled"]
    assert behind == pytest.approx(measured["lag"], abs=FRAME), (
        f"a stamped animation began {behind:.0f} ms in, "
        f"where the timeline lagged {measured['lag']:.0f} ms"
    )
    freezes = FREEZES_WHILE_IDLE[browser_name]
    if freezes is None:
        # The lower bound sits below zero because an engine that refreshes the time on a
        # read can report it a tick ahead of `performance.now()`, which is not a third
        # behaviour.
        assert -FRAME <= measured["lag"] <= PAUSE + FRAME, (
            f"{browser_name} lags the timeline by {measured['lag']:.0f} ms after a "
            f"{PAUSE} ms pause, which is neither engine's behaviour"
        )
    elif freezes:
        assert measured["lag"] > PAUSE - FRAME, (
            f"{browser_name} now advances its timeline while the page is idle, "
            f"lagging {measured['lag']:.0f} ms after a {PAUSE} ms pause"
        )
    else:
        # One-sided on purpose. Webkit rounds both clocks to whole milliseconds and reads a
        # lag of zero, so a tick falling between the two reads in `MEASURE` reports -1, as
        # it did in continuous integration.
        assert measured["lag"] < FRAME, (
            f"{browser_name} now freezes its timeline while the page is idle, "
            f"lagging {measured['lag']:.0f} ms after a {PAUSE} ms pause"
        )
