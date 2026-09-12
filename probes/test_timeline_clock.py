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

# What a single frame may cost, in milliseconds, at the 60 Hz the engines run headless at.
# Every measurement here is either "this frame" or "a whole pause ago", so the two are
# never in danger of being confused and the allowance can be generous.
FRAME = 100

# Whether an engine's document timeline stands still while the page draws no frames,
# measured on chromium 151 and firefox 153. Freezing is what the specification describes,
# since it says the time is updated once per frame; chromium is the one that updates it on
# a read from outside a frame. Webkit has no row because it cannot be launched on the
# machine this was measured on: either behaviour passes below until someone fills it in.
FREEZES_WHILE_IDLE = {"chromium": False, "firefox": True, "webkit": None}

# Start an animation after a pause, twice: once left to the browser, and once told to have
# begun at the document timeline's current time, which is what this finding is about.
#
# Both are read after a frame has been drawn. Before that they read the same, because an
# animation's current time is measured against the timeline rather than against real time,
# so a stale timeline hides its own staleness until it is refreshed.
MEASURE = """async () => {
    const target = document.body;
    const lag = performance.now() - document.timeline.currentTime;
    const scheduled = target.animate([{opacity: 1}, {opacity: 0}], 10000);
    const stamped = target.animate([{opacity: 1}, {opacity: 0}], 10000);
    stamped.startTime = document.timeline.currentTime;
    await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
    return {lag, scheduled: scheduled.currentTime, stamped: stamped.currentTime};
}"""


@pytest.fixture
def measured(page, open_page):
    """The three numbers, taken after the page has been left alone for `PAUSE`."""
    page.set_content("<!doctype html><p>still</p>")
    page.wait_for_timeout(PAUSE)
    return page.evaluate(MEASURE)


def test_an_animation_the_browser_schedules_begins_at_its_beginning(measured):
    """The behaviour the runtime leans on, and the reason it names no start time.

    A pending animation is started at the next frame, which is a fresh one however long
    the page stood still, so a step taken after a pause plays from the beginning.
    """
    assert measured["scheduled"] < FRAME, (
        "an animation created without a start time did not begin at its beginning"
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
        assert 0 <= measured["lag"] <= PAUSE + FRAME, (
            f"{browser_name} lags the timeline by {measured['lag']:.0f} ms after a "
            f"{PAUSE} ms pause, which is neither engine's behaviour"
        )
    elif freezes:
        assert measured["lag"] > PAUSE - FRAME, (
            f"{browser_name} now advances its timeline while the page is idle, "
            f"lagging {measured['lag']:.0f} ms after a {PAUSE} ms pause"
        )
    else:
        assert measured["lag"] < FRAME, (
            f"{browser_name} now freezes its timeline while the page is idle, "
            f"lagging {measured['lag']:.0f} ms after a {PAUSE} ms pause"
        )
