# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: what happens between two slides.

A boundary crossfades the two slide containers or cuts between them, and the `init` of the
slide a forward step *enters* is what decides which, in both directions.
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

# What a comparison of a midpoint with the two endpoints around it carries on its own,
# out of 255, as `test_epochs_html.py` derives it.
# Chromium 151 is the engine that needs most of it.
# The container it fades out is sampled one step inside the boundary rather than at full
# opacity, and it rasterises up to 2/255 from the same container at rest.
ROUNDING = 3

# How far the blended midpoint of a slide boundary may sit from the average of the two
# slides, per engine, as a deviation out of 255 and a number of pixels allowed to exceed the
# rounding above.
# Chromium 151 and firefox 153 are held to that rounding, which stays far below the 64/255 a
# plain opacity crossfade dips by.
# The probe for *Crossfading two slide containers* is where the exactness of the blend is
# measured, on rasters with no animation running in them.
# Webkit's allowance is the one from *Crossfading epoch frames*, which it shares.
BLEND = {"chromium": (ROUNDING, 0), "firefox": (ROUNDING, 0), "webkit": (48, 512)}

# Three slides of three grounds, the middle one cutting and the outer two crossfading.
# The ground is what the blend is really about, and a heading is what says the slide
# arrived at all.
GROUNDS = ("#204080", "#a06020", "#207040")

DECK = deck(
    *(
        f'slide(background: rgb("{ground}"){extra})[= Slide {index}]'
        for index, (ground, extra) in enumerate(
            zip(GROUNDS, ("", ", animation: anim.init(duration: 0)", ""), strict=True), start=1
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
    """`init(duration: 0)`, which is a cut whatever the transition."""
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

    `--animo-transition-duration` at zero is the same code path as `init(duration: 0)`, and
    the subslide duration beside it is untouched, which is what the two names are for.
    """
    presentation: Deck = deck_at(three_slides).goto(2)
    page.add_style_tag(content=":root { --animo-transition-duration: 0ms }")
    presentation.press("ArrowRight")
    assert presentation.position == (3, 0)
    assert presentation.animating == []


def test_reduced_motion_snaps_a_boundary(page, browser_name, deck_at, typst: TypstRunner):
    """A reader who asked for less motion gets the cut, by that same code path.

    The stylesheet sets `--animo-motion` under the media query, so this is the assertion
    that the runtime reads it at a slide boundary too and not only inside a slide.
    """
    page.emulate_media(reduced_motion="reduce")
    presentation: Deck = deck_at(typst.html(DECK, name="reduced.html")).goto(2)
    assert (
        page.evaluate(
            "() => getComputedStyle(document.documentElement)"
            ".getPropertyValue('--animo-motion').trim()"
        )
        == "none"
    )
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
    assert int((difference > ROUNDING).any(axis=2).sum()) <= pixels, (
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


# Transitions that move, cover and clip.
#
# Each boundary of the deck below takes another transition, so a step that looked up the
# transition of the wrong slide would show it as the wrong motion and not only as the wrong
# length. Slide 3 pushes, slide 4 cuts, slide 5 wipes and slide 6 covers, and slides 1 and 2
# take the deck's own crossfade.
# The grounds are opaque and differ, because two of them that overlapped under the
# `plus-lighter` of a crossfade would add to a third colour where a push, a cover or a wipe
# has to show one of the two.

MIXED_GROUNDS = ("#204080", "#a06020", "#207040", "#802060", "#606020", "#205060")

MIXED_TRANSITIONS = (
    "",
    "",
    "animation: anim.init(anim.push()), ",
    "animation: anim.init(duration: 0), ",
    "animation: anim.init(anim.wipe(direction: ttb)), ",
    "animation: anim.init(anim.cover(direction: btt), duration: 2), ",
)

MIXED = deck(
    *(
        f'slide({extra}background: rgb("{ground}"))[= Slide {index}]'
        for index, (ground, extra) in enumerate(
            zip(MIXED_GROUNDS, MIXED_TRANSITIONS, strict=True), start=1
        )
    )
)


@pytest.fixture
def mixed(typst: TypstRunner):
    """A compiled six-slide deck whose boundaries take every transition there is."""
    return typst.html(MIXED, name="mixed.html")


def stage(presentation: Deck):
    """The stage, which is the rectangle a slide fills and clips at."""
    return presentation.page.locator(".animo-stage")


def offsets(presentation: Deck, *slides: int) -> list[list[float]]:
    """Where each slide container sits, as a fraction of the stage along each axis."""
    return presentation.page.evaluate(
        """slides => {
            const stage = document.querySelector(".animo-stage").getBoundingClientRect();
            return slides.map((number) => {
                const box = document
                    .querySelector(`[data-animo-slide="${number}"]`)
                    .getBoundingClientRect();
                return [(box.x - stage.x) / stage.width, (box.y - stage.y) / stage.height];
            });
        }""",
        list(slides),
    )


def blends(presentation: Deck, *slides: int) -> list[str]:
    """The `mix-blend-mode` each slide container computes."""
    return presentation.page.evaluate(
        """slides => slides.map((number) => getComputedStyle(
            document.querySelector(`[data-animo-slide="${number}"]`)).mixBlendMode)""",
        list(slides),
    )


def test_each_boundary_takes_the_transition_of_the_slide_with_the_higher_number(
    page, deck_at, mixed
):
    """The two directions of one boundary take one transition, whichever slide is entered.

    Stepping back from slide 3 to slide 2 enters slide 2, which takes the crossfade, and
    crosses the boundary that belongs to slide 3, which pushes. A push both ways round is
    what says the transition is looked up on the boundary's owner.
    """
    presentation: Deck = deck_at(mixed)
    page.add_style_tag(content=SLOW)
    walk = [
        ("ArrowRight", (2, 0), [{"opacity"}, {"opacity"}]),
        ("ArrowRight", (3, 0), [{"translate"}, {"translate"}]),
        ("ArrowLeft", (2, 0), [{"translate"}, {"translate"}]),
        ("ArrowLeft", (1, 0), [{"opacity"}, {"opacity"}]),
    ]
    for key, position, animating in walk:
        presentation.press(key)
        assert presentation.position == position
        assert sorted(presentation.animating, key=sorted) == animating, (
            f"{key} into {position} animated {presentation.animating}"
        )
        presentation.settle()


def test_a_cut_beside_a_push_cuts_in_both_directions(page, deck_at, mixed):
    """`init(duration: 0)` on slide 4 is a cut, though the boundary below it pushes."""
    presentation: Deck = deck_at(mixed).goto(3)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert presentation.position == (4, 0)
    assert presentation.animating == []
    presentation.press("ArrowLeft")
    assert presentation.position == (3, 0)
    assert presentation.animating == []


# Where the two slides are halfway through, in both directions. A forward step and the
# backward one over the same boundary pass through the same midpoint, because the backward
# step is the forward one played from the other end.


@pytest.mark.parametrize(
    ("direction", "travel"),
    [("ltr", (1, 0)), ("rtl", (-1, 0)), ("ttb", (0, 1)), ("btt", (0, -1))],
)
@pytest.mark.parametrize("name", ["push", "cover"])
@pytest.mark.parametrize("key", ["ArrowRight", "ArrowLeft"])
def test_the_midpoint_of_a_moving_transition(
    page, deck_at, typst: TypstRunner, name, direction, travel, key
):
    """The owner is half way in from the edge it travels from, and the other slide is half
    way out at the opposite edge for a push and in place for a cover.
    """
    source = deck(
        'slide(background: rgb("#204080"))[= One]',
        f"slide(animation: anim.init(anim.{name}(direction: {direction})), "
        'background: rgb("#a06020"))[= Two]',
    )
    presentation: Deck = deck_at(typst.html(source, name=f"{name}-{direction}.html"))
    if key == "ArrowLeft":
        presentation.goto(2)
    page.add_style_tag(content=SLOW)
    presentation.press(key)
    presentation.scrub(MIDPOINT)
    owner, other = offsets(presentation, 2, 1)
    assert owner == pytest.approx((-travel[0] / 2, -travel[1] / 2), abs=1e-3)
    moved = (travel[0] / 2, travel[1] / 2) if name == "push" else (0, 0)
    assert other == pytest.approx(moved, abs=1e-3)
    assert blends(presentation, 1, 2) == ["normal", "normal"]


@pytest.mark.parametrize(
    ("direction", "revealed"),
    [("ltr", "left"), ("rtl", "right"), ("ttb", "top"), ("btt", "bottom")],
)
@pytest.mark.parametrize("key", ["ArrowRight", "ArrowLeft"])
def test_the_midpoint_of_a_wipe(
    page, deck_at, typst: TypstRunner, browser_name, direction, revealed, key
):
    """Half the stage shows the owner and the other half the slide under it, as at rest.

    The comparison is with each slide at rest, half by half, which also says that the two
    slides cover rather than add where they overlap.
    """
    source = deck(
        'slide(background: rgb("#204080"))[= One]',
        f"slide(animation: anim.init(anim.wipe(direction: {direction})), "
        'background: rgb("#a06020"))[= Two]',
    )
    path = typst.html(source, name=f"wipe-{direction}.html")
    first = screenshot(stage(deck_at(path).goto(1))).astype(int)
    second = screenshot(stage(deck_at(path).goto(2))).astype(int)
    presentation: Deck = deck_at(path).goto(2 if key == "ArrowLeft" else 1)
    page.add_style_tag(content=SLOW)
    presentation.press(key)
    presentation.scrub(MIDPOINT)
    halfway = screenshot(stage(presentation), animations="allow").astype(int)
    height, width = halfway.shape[:2]
    owner = {
        "left": np.s_[:, : width // 2],
        "right": np.s_[:, width // 2 :],
        "top": np.s_[: height // 2],
        "bottom": np.s_[height // 2 :],
    }
    other = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}[revealed]
    assert abs(halfway[owner[revealed]] - second[owner[revealed]]).max() <= ROUNDING
    assert abs(halfway[owner[other]] - first[owner[other]]).max() <= ROUNDING


def test_a_cover_covers_rather_than_adds(page, deck_at, typst: TypstRunner):
    """Where the owner of a cover overlaps the slide under it, only the owner shows.

    The owner of a rightward cover is half way in at the midpoint, so the left half of the
    stage shows the right half of the owner, and the right half shows the slide under it.
    Under the `plus-lighter` of a crossfade the left half would be the sum of the two.
    """
    source = deck(
        'slide(background: rgb("#204080"))[]',
        'slide(animation: anim.init(anim.cover(direction: ltr)), background: rgb("#a06020"))[]',
    )
    path = typst.html(source, name="cover-blend.html")
    first = screenshot(stage(deck_at(path).goto(1))).astype(int)
    second = screenshot(stage(deck_at(path).goto(2))).astype(int)
    presentation: Deck = deck_at(path).goto(1)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    presentation.scrub(MIDPOINT)
    halfway = screenshot(stage(presentation), animations="allow").astype(int)
    half = halfway.shape[1] // 2
    assert abs(halfway[:, :half] - second[:, half:]).max() <= ROUNDING
    assert abs(halfway[:, half:] - first[:, half:]).max() <= ROUNDING


@pytest.mark.parametrize("slide", [3, 5, 6])
def test_both_ends_of_a_transition_are_the_slides_at_rest(page, deck_at, mixed, slide):
    """A boundary that has been crossed shows the slide it arrived at and nothing else.

    The slide being left is still laid out when the boundary ends, pushed out of the stage
    or covered, so this is the assertion that the stage clips it and that it does not join
    the picture. Both ends are compared with a deep link, which snaps.
    """
    entered = screenshot(stage(deck_at(mixed).goto(slide)))
    left = screenshot(stage(deck_at(mixed).goto(slide - 1)))
    presentation: Deck = deck_at(mixed).goto(slide - 1)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert presentation.animating != []
    presentation.scrub(DURATION).settle()
    assert_identical(entered, screenshot(stage(presentation)), what="the end of a step forward")
    presentation.press("ArrowLeft")
    assert presentation.animating != []
    presentation.scrub(DURATION).settle()
    assert_identical(left, screenshot(stage(presentation)), what="the end of a step backward")


def test_a_slide_off_a_boundary_is_at_rest(page, deck_at, mixed):
    """Once the deck moves on, no slide is moved, clipped or blended by a transition.

    The slides a wipe crossed keep the blend of the wipe for as long as the deck stays where
    the wipe left it, because the slide it covered is still laid out under the other one.
    The next position that crosses no boundary takes the blend away.
    """
    presentation: Deck = deck_at(mixed).goto(2)
    page.add_style_tag(content=SLOW)
    for _ in range(4):
        presentation.press("ArrowRight").scrub(DURATION).settle()
    assert presentation.position == (6, 0)
    assert blends(presentation, 5, 6) == ["normal", "normal"]
    presentation.goto(1)
    inline = presentation.page.evaluate(
        """() => [...document.querySelectorAll(".animo-slide")].map((slide) => [
            slide.style.translate, slide.style.clipPath, slide.style.mixBlendMode])"""
    )
    assert inline == [["", "", ""]] * len(MIXED_GROUNDS)


def test_an_interrupted_push_turns_round_where_it_is(page, deck_at, mixed):
    """Turning round half way through a push starts from the two slides as they are."""
    presentation: Deck = deck_at(mixed).goto(2)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    presentation.scrub(MIDPOINT)
    presentation.press("ArrowLeft")
    assert presentation.position == (2, 0)
    presentation.scrub(0)
    owner, other = offsets(presentation, 3, 2)
    assert owner == pytest.approx([0.5, 0], abs=1e-3)
    assert other == pytest.approx([-0.5, 0], abs=1e-3)
    presentation.scrub(DURATION).settle()
    assert offsets(presentation, 2) == [[0, 0]]


def test_a_slide_states_the_duration_of_its_boundary(page, deck_at, mixed):
    """Slide 6 takes two seconds in both directions, and the deck's own easing."""
    presentation: Deck = deck_at(mixed).goto(5)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    timings = presentation.page.evaluate(
        """() => document.getAnimations().map((animation) => {
            const timing = animation.effect.getTiming();
            return [timing.duration, timing.easing];
        })"""
    )
    assert timings == [[2000, "linear"]]
    presentation.settle().press("ArrowLeft")
    assert flight(presentation) == [2000]


@pytest.mark.parametrize("how", ["property", "reduced"])
def test_a_reader_without_motion_cuts_every_transition(page, deck_at, how, mixed):
    """A reader who asked for less motion gets a cut at every boundary, the ones that state
    a duration of their own included.

    The two ways in are the media query and the property it sets.
    """
    if how == "reduced":
        page.emulate_media(reduced_motion="reduce")
    presentation: Deck = deck_at(mixed)
    if how == "property":
        page.add_style_tag(content=":root { --animo-motion: none }")
    for slide in range(2, len(MIXED_GROUNDS) + 1):
        presentation.press("ArrowRight")
        assert presentation.position == (slide, 0)
        assert presentation.animating == [], f"the boundary into slide {slide} animated"


def test_a_zero_deck_duration_cuts_the_boundaries_that_state_none(page, deck_at, mixed):
    """The deck's duration is a default, so slide 6, which states two seconds, still moves."""
    presentation: Deck = deck_at(mixed)
    page.add_style_tag(content=":root { --animo-transition-duration: 0ms }")
    for slide in range(2, len(MIXED_GROUNDS)):
        presentation.press("ArrowRight")
        assert presentation.position == (slide, 0)
        assert presentation.animating == [], f"the boundary into slide {slide} animated"
    presentation.press("ArrowRight")
    assert presentation.position == (6, 0)
    assert flight(presentation) == [2000]


# The deck's own transition, which a slide that says `auto` takes.


def test_the_deck_states_the_transition_auto_takes(page, deck_at, typst: TypstRunner):
    """A slide that names no transition follows the deck, and one that names one keeps it."""
    source = deck(
        "slide[= One]",
        "slide[= Two]",
        "slide(animation: anim.init(anim.crossfade()))[= Three]",
        timing="transition: anim.push(direction: ttb)",
    )
    presentation: Deck = deck_at(typst.html(source, name="deck-push.html"))
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    owner, other = offsets(presentation, 2, 1)
    assert owner == pytest.approx([0, -0.5], abs=1e-3)
    assert other == pytest.approx([0, 0.5], abs=1e-3)
    presentation.scrub(DURATION).settle().press("ArrowRight")
    assert presentation.animating == [{"opacity"}, {"opacity"}]


def test_a_deck_of_cuts_pushes_the_slide_that_states_a_duration(page, deck_at, typst: TypstRunner):
    """The case the manual warns about, from both sides.

    A deck with `transition-duration: 0` cuts by default. A slide in it that is to be pushed
    in states the duration as well, and a slide that names the push alone takes the deck's
    zero and is a cut.
    """
    source = deck(
        "slide[= One]",
        f"slide(animation: anim.init(anim.push(), duration: {DURATION / 1000}))[= Two]",
        "slide(animation: anim.init(anim.push()))[= Three]",
        timing="transition-duration: 0",
    )
    presentation: Deck = deck_at(typst.html(source, name="deck-cuts.html"))
    presentation.press("ArrowRight")
    assert presentation.animating == [{"translate"}, {"translate"}]
    presentation.scrub(DURATION).settle().press("ArrowRight")
    assert presentation.position == (3, 0)
    assert presentation.animating == []


def test_a_duration_without_a_transition_times_the_decks_own(page, deck_at, typst: TypstRunner):
    """`init(duration: ..)` alone keeps the deck's transition and gives it a length."""
    source = deck(
        "slide[= One]",
        "slide(animation: anim.init(duration: 2))[= Two]",
        timing="transition: anim.push(direction: ttb)",
    )
    presentation: Deck = deck_at(typst.html(source, name="deck-timed.html"))
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight")
    assert presentation.animating == [{"translate"}, {"translate"}]
    assert flight(presentation) == [2000, 2000]
