# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: what happens between two slides.

A boundary crossfades the two slide containers or cuts between them, and `transition:`
on the slide a forward step *enters* is what decides which, in both directions.
The deck below is what makes that sharp: slide 2 cuts and slide 3 crossfades, so the two
boundaries around slide 2 behave differently and neither can be explained by the
direction the presenter happens to be walking in.

The crossfade itself is measured rather than raced, by pausing what is in flight and
stating the moment, exactly as the epoch crossfade is in `test_epochs_html.py`.
The two slides carry different background colours, because that is the case a plain
opacity crossfade gets wrong: two opaque grounds dip to something darker than either at
the midpoint, where `plus-lighter` sums them to the average.
"""

import numpy as np
import pytest
from decks import deck
from harness import Deck, TypstRunner, assert_identical, screenshot

# How long a boundary takes in these tests, in milliseconds, and the moment sampled in it.
# Slowed down from animo's own 400 ms so that a paused animation cannot already have
# ended, and linear so that the moment sampled is the fraction of the step it looks like.
DURATION = 4000
MIDPOINT = DURATION / 2

SLOW = f":root {{ --animo-transition-duration: {DURATION}ms; --animo-easing: linear }}"

# How far the blended midpoint of a slide boundary may sit from the exact average of the
# two slides, per engine, as a deviation out of 255 and a number of pixels allowed to
# exceed one. These are the allowances the probe for *Crossfading two slide containers*
# measured; webkit's is the one from *Crossfading epoch frames*, which it shares.
BLEND = {"chromium": (1, 0), "firefox": (1, 0), "webkit": (48, 512)}

# Three slides of three grounds, the middle one cutting and the outer two crossfading.
# The ground is what the blend is really about, and a heading is what says the slide
# arrived at all.
GROUNDS = ("#204080", "#a06020", "#207040")

DECK = deck(
    *(
        f'slide(background: rgb("{ground}"){extra})[= Slide {index}]'
        for index, (ground, extra) in enumerate(
            zip(GROUNDS, ("", ", transition: none", ""), strict=True), start=1
        )
    )
)


@pytest.fixture
def three_slides(typst: TypstRunner):
    """A compiled three-slide deck whose middle slide is entered with a cut."""
    return typst.html(DECK, name="transitions.html")


def flight(presentation: Deck) -> list[float]:
    """How long each animation now in flight runs for, in milliseconds."""
    return presentation.page.evaluate(
        "() => document.getAnimations().map(a => a.effect.getTiming().duration)"
    )


# Which boundary animates, and which of the two slides decides it.


def test_a_step_into_a_crossfading_slide_animates(page, deck_at, three_slides):
    """The default, and the two containers are what it addresses.

    Two animations and no more: the slide being entered and the slide being left, each
    driving nothing but `opacity`, which is what makes the two halves add rather than
    one of them cover the other.
    """
    presentation: Deck = deck_at(three_slides).goto(2)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert presentation.position == (3, 0)
    assert presentation.animating == [{"opacity"}, {"opacity"}]


def test_a_step_into_a_cutting_slide_does_not_animate(page, deck_at, three_slides):
    """`transition: none`, which is the same code path a duration of zero takes."""
    presentation: Deck = deck_at(three_slides)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert presentation.position == (2, 0)
    assert presentation.animating == []


def test_a_cut_shows_the_slide_it_lands_on_whole(page, deck_at, three_slides):
    """One container's visibility handed to the other, with nothing in between.

    The picture a cut arrives at is the picture a deep link to the same slide gives,
    which is what says the cut left nothing of the slide it came from behind.
    """
    presentation: Deck = deck_at(three_slides)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    stepped = screenshot(presentation.current)
    linked = screenshot(deck_at(three_slides).goto(2).current)
    assert_identical(stepped, linked, what="a cut and a deep link to the same slide")


def test_a_boundary_takes_the_setting_of_the_slide_a_forward_step_enters(
    page, deck_at, three_slides
):
    """The reading the design asks to be confirmed, and this is where it is sharp.

    Slide 2 cuts and slide 3 crossfades, so the boundary below slide 2 cuts and the one
    above it crossfades. Walking backwards over each of them has to do the same thing as
    walking forwards did, which is what makes a boundary reversible: were each direction
    to take the setting of whichever slide it happens to enter, stepping back from 3 to 2
    would cut and stepping back from 2 to 1 would crossfade, which is the opposite of
    both assertions below.
    """
    presentation: Deck = deck_at(three_slides).goto(3)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowLeft")
    assert presentation.position == (2, 0)
    assert presentation.animating == [{"opacity"}, {"opacity"}], (
        "stepping back over a crossfading boundary did not crossfade"
    )
    presentation.settle().press("ArrowLeft")
    assert presentation.position == (1, 0)
    assert presentation.animating == [], "stepping back over a cutting boundary animated"


def test_a_boundary_takes_the_same_length_in_both_directions(page, deck_at, three_slides):
    """A boundary that is longer one way round would not be an undo of the other."""
    presentation: Deck = deck_at(three_slides).goto(2)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    forward = flight(presentation)
    presentation.settle().press("ArrowLeft")
    assert flight(presentation) == forward == [DURATION, DURATION]


def test_a_boundary_has_a_duration_of_its_own(page, deck_at, three_slides):
    """A deck of hard cuts is one line, and it leaves the motion inside a slide alone.

    `--animo-transition-duration` at zero is the same code path as `transition: none`, and the
    subslide duration beside it is untouched, which is what the two names are for.
    """
    presentation: Deck = deck_at(three_slides).goto(2)
    page.add_style_tag(content=":root { --animo-transition-duration: 0ms }")
    presentation.press("ArrowRight")
    assert presentation.position == (3, 0)
    assert presentation.animating == []


def test_reduced_motion_snaps_a_boundary(page, browser_name, deck_at, typst: TypstRunner):
    """A reader who asked for less motion gets the cut, by that same code path.

    The stylesheet zeroes both durations under the media query, so this is the assertion
    that animo's own rule names the slide duration too and not only the subslide one.
    """
    page.emulate_media(reduced_motion="reduce")
    presentation: Deck = deck_at(typst.html(DECK, name="reduced.html")).goto(2)
    assert page.evaluate(
        "() => getComputedStyle(document.documentElement)"
        ".getPropertyValue('--animo-transition-duration').trim()"
    ) == "0s"
    presentation.press("ArrowRight")
    assert presentation.position == (3, 0)
    assert presentation.animating == []


# What still snaps.


@pytest.mark.parametrize("key", ["Home", "End"])
def test_home_and_end_snap(page, deck_at, three_slides, key):
    """Neither is a step across one boundary, so neither is a transition to animate."""
    presentation: Deck = deck_at(three_slides).goto(2)
    page.add_style_tag(content=SLOW)
    presentation.press(key)
    assert presentation.animating == []


def test_a_deep_link_across_a_boundary_snaps(page, deck_at, three_slides):
    """A deep link shows the picture and not the transition, boundaries included."""
    presentation: Deck = deck_at(three_slides).goto(2)
    page.add_style_tag(content=SLOW)
    presentation.goto(3)
    assert presentation.animating == []


def test_the_first_paint_snaps(page, deck_at, three_slides):
    """The first paint is a deep link to wherever the fragment points."""
    presentation: Deck = deck_at(three_slides)
    assert presentation.position == (1, 0)
    assert presentation.animating == []


# What the boundary looks like halfway through.


def crossing(presentation: Deck, *moments: float) -> list[np.ndarray]:
    """One raster per moment of a step across a slide boundary, each taken in flight.

    Every raster is taken with the same animation in flight, the ones standing for the
    endpoints included, because chromium 151 rasterises a frame differently while an
    `opacity` animation runs in it. See *Findings*. The endpoints are sampled just inside
    the step, since an animation at its end time is finished and rasterises as at rest.
    """
    shots = []
    for moment in moments:
        presentation.scrub(moment)
        shots.append(screenshot(presentation.current, animations="allow"))
    return shots


def test_the_midpoint_of_a_boundary_is_the_sum_of_the_two_slides(
    page, deck_at, three_slides, browser_name
):
    """Nothing dips halfway through, which is what `plus-lighter` is there for.

    The two slides carry opaque grounds of different colours, so a plain opacity
    crossfade would put the deck's own black surround through the half-transparent pair
    and land the midpoint far below the average of the two. The assertion is on the whole
    slide rather than on a band of it, because a slide boundary scopes nothing: the whole
    container is the unit.
    """
    presentation: Deck = deck_at(three_slides).goto(2)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    before, halfway, after = (
        shot.astype(int) for shot in crossing(presentation, 1, MIDPOINT, DURATION - 1)
    )
    difference = abs((before + after) / 2 - halfway)
    deviation, pixels = BLEND[browser_name]
    assert difference.max() <= deviation, (
        f"the midpoint of the boundary is {difference.max()}/255 from the exact sum"
    )
    assert int((difference > 1).any(axis=2).sum()) <= pixels, (
        "more of the slide dipped than this engine was measured to"
    )


def test_an_interrupted_boundary_continues_from_where_it_is(page, deck_at, three_slides):
    """The boundary is a state written as style with the animation only the route to it.

    Turning round halfway through has to start from the picture on the screen rather than
    from either endpoint, which is what keeps a presenter who changes their mind from
    seeing a jump. Both containers are halfway when the step turns round, so the keyframes
    the new step starts from are halfway too, and the slide it returns to is the one it
    left, to the pixel.
    """
    presentation: Deck = deck_at(three_slides).goto(2)
    at_rest = screenshot(presentation.current)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    presentation.scrub(MIDPOINT)
    presentation.press("ArrowLeft")
    assert presentation.position == (2, 0)
    resumed = presentation.page.evaluate(
        "() => document.getAnimations().map(a => a.effect.getKeyframes()[0].opacity)"
    )
    assert sorted(resumed) == ["0.5", "0.5"], (
        f"the boundary restarted rather than turning round: {resumed}"
    )
    presentation.settle()
    assert_identical(at_rest, screenshot(presentation.current), what="the slide and its return")


def test_the_slide_being_entered_is_shown_in_the_state_it_comes_up_on(
    page, deck_at, typst: TypstRunner
):
    """The display state of the slide being entered is written before it comes up.

    The tag is hidden in the body and revealed by the timeline, so a slide whose state
    were written after the fade would show it and then take it away. Stepping onto the
    slide lands on state 0, where it is still hidden, and the midpoint of the boundary
    has to agree with the end of it about that.
    """
    source = deck(
        "slide[= First]",
        'slide(animation: { import anim: *\n  sub(reveal("t")) })'
        '[= Second\n  #tag("t")[A line that starts out hidden.]]',
    )
    presentation: Deck = deck_at(typst.html(source, name="entering.html"))
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert presentation.position == (2, 0)
    presentation.scrub(MIDPOINT)
    assert [style["opacity"] for style in presentation.styles("t")] == ["0"]
