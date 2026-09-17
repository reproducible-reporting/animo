# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the epoch renderings of a slide, and the boundary between two of them.

A slide is one frame holding one rendering per content state, placed at one point, of
which one is shown. This is where the two invariants that the whole region design rests on
are either true or not, and both are comparisons within one page load, so neither needs a
stored image:

- every label outside a region has the same box in every epoch rendering;
- the slide is pixel-identical outside the changed region between two epochs,
  and stays so halfway through the crossfade.

The second one is asserted at a stated moment rather than at whatever point a transition
happened to have reached, by pausing what is in flight, which is also how the crossfade's
own arithmetic is measured: the midpoint of an exact crossfade is the average of the two
renderings it runs between.
"""

import numpy as np
import pytest
from decks import deck
from harness import (
    Box,
    Deck,
    TypstRunner,
    assert_identical,
    assert_identical_outside,
    screenshot,
)

# How long a step takes in these tests, in milliseconds, and the moment sampled in it.
# Slowed down from animo's own 400 ms so that a paused animation cannot already have ended,
# and linear so that the moment sampled is the fraction of the step it looks like.
DURATION = 4000
MIDPOINT = DURATION / 2

SLOW = f":root {{ --animo-primitive-duration: {DURATION}ms; --animo-easing: linear }}"

# How far the blended midpoint of a crossfade may sit from the exact sum of the two
# renderings, per engine, as a deviation out of 255 and a number of pixels allowed to
# exceed one.
#
# Exact is the claim, and chromium 151 and firefox 153 meet it to within rounding: two
# half-opacity layers add back to one opaque layer through `plus-lighter`.
# Playwright's webkit 26.5 does not, and the allowance is the one the probe for
# *Crossfading epoch frames* measured for it: a few dozen pixels on antialiased glyph
# edges drift by up to 42 out of 255.
# This is about the inside of the region only. Outside it, no allowance is given in any
# engine, because the outgoing rendering paints nothing there at all.
BLEND = {"chromium": (1, 0), "firefox": (1, 0), "webkit": (48, 512)}


def timeline(*steps: str) -> str:
    """The animation argument of a slide, with the primitives imported inside it."""
    return "{ import anim: *\n  " + "\n  ".join(steps) + " }"


def animated(typst: TypstRunner, body: str, *steps: str, name: str = "deck.html", **slide):
    """Compile a one-slide deck with a timeline, as a file the browser can open."""
    extra = "".join(f", {key}: {value}" for key, value in slide.items())
    source = deck(f"slide(animation: {timeline(*steps)}{extra})[\n  {body}\n]")
    return typst.html(source, name=name)


# A region whose content reflows, with a tagged line above it and one below it.
# The lines outside are what the containment invariant is asserted on, and the tag inside
# the region below the changing one is what says the assertion is not vacuous:
# that one does move between the renderings, because the region relays its interior out.
REFLOWING = """
  #tag("head", wrap: block)[A line above the region.]

  #region(name: "r")[
    #tag("claim", wrap: block)[A short claim.]

    #tag("inside", wrap: block)[A line after the claim, inside the region.]
  ]

  #tag("foot", wrap: block)[A line below the region.]
"""

LONGER = (
    "Actually the opposite holds, and this replacement is long enough to wrap onto a "
    "second line, which pushes the rest of the region down."
)


@pytest.fixture
def reflowing(typst: TypstRunner):
    """A slide of three epochs: the claim, a replacement that wraps, and the claim back."""
    return animated(
        typst,
        REFLOWING,
        f'sub(replace("claim")[{LONGER}])',
        'sub(reset("claim"))',
    )


# The same slide with both outer layers, each ink of its own in a corner the region does not
# reach, so that the comparisons below stay about the region.
MARKER = '#place(bottom + right, rect(width: 1cm, height: 1cm, fill: rgb("#0000ff")))'


@pytest.fixture
def reflowing_layered(typst: TypstRunner):
    """The same three epochs, with a background frame and an overlay frame beside them."""
    return animated(
        typst,
        REFLOWING,
        f'sub(replace("claim")[{LONGER}])',
        'sub(reset("claim"))',
        name="layered.html",
        background='[#place(top + right, rect(width: 1cm, height: 1cm, fill: rgb("#ff0000")))]',
        overlay=f"[{MARKER}]",
    )


def band(presentation: Deck) -> Box:
    """The rows of the slide that the region covers, as a full-width band.

    It is read off the rendered region rather than assumed, over every epoch rendering, so
    the band contains the region in each of them and the comparison outside it stays
    honest.
    """
    box = presentation.current.bounding_box()
    found = presentation.rects("r")
    assert found, "the region emitted no group to read the band off"
    top = min(rect.y for rect in found) - box["y"]
    bottom = max(rect.y + rect.height for rect in found) - box["y"]
    return Box(0, max(0, int(top) - 1), int(box["width"]), int(bottom) + 2)


# How many renderings a slide has, and how many frames they sit in.


def test_a_slide_has_one_rendering_per_epoch_in_one_frame(deck_at, reflowing):
    """Three epochs, three groups, placed at one point of a single frame in epoch order.

    One frame and not three is what shares their glyph definitions, because typst's
    deduplicator has the frame for its scope. See *Findings*.
    """
    presentation: Deck = deck_at(reflowing)
    assert presentation.frames.count() == 3
    assert presentation.canvas_frames == 1
    assert len(presentation.plan["epochs"]) == 3


def test_a_slide_without_structural_steps_has_exactly_one_rendering(
    deck_at, typst: TypstRunner
):
    """The cost claim: a deck that changes no content pays nothing for epochs existing."""
    presentation: Deck = deck_at(
        animated(typst, REFLOWING, 'sub(move("claim", x: 1cm))', 'sub(hide("foot"))')
    )
    assert presentation.frames.count() == 1
    assert presentation.painting == [True]


def test_only_the_current_epochs_rendering_paints(deck_at, reflowing):
    """One rendering at a time, and stepping inside an epoch does not change which."""
    presentation: Deck = deck_at(reflowing)
    assert presentation.painting == [True, False, False]
    assert presentation.goto(1, 1).painting == [False, True, False]
    assert presentation.goto(1, 2).painting == [False, False, True]


def test_the_plan_names_the_region_each_boundary_redraws(deck_at, reflowing):
    """Both boundaries change the claim, which the region around it is what redraws.

    A region carries its own timing beside its group, which a boundary that says nothing
    about when it happens leaves out entirely.
    """
    presentation: Deck = deck_at(reflowing)
    epochs = presentation.plan["epochs"]
    assert [epoch["regions"] for epoch in epochs] == [
        [],
        [{"group": "r"}],
        [{"group": "r"}],
    ]
    assert [state["epoch"] for state in presentation.plan["states"]] == [0, 1, 2]


# The first invariant: what the renderings agree about.


def test_every_label_outside_a_region_has_the_same_box_in_every_rendering(deck_at, reflowing):
    """Nothing outside a region moves between epochs, measured rather than looked at.

    The control is the tag inside the region, which does move, because that is the reflow
    the region exists to contain.
    """
    presentation: Deck = deck_at(reflowing)
    for name in ("head", "foot"):
        boxes = [presentation.rects(name, frame=frame)[0] for frame in range(3)]
        assert boxes[0].approx(boxes[1]), f"{name} moved between the first two renderings"
        assert boxes[0].approx(boxes[2]), f"{name} moved between the outer two renderings"
    inside = [presentation.rects("inside", frame=frame)[0] for frame in range(3)]
    assert not inside[0].approx(inside[1]), "the region did not relay its interior out"
    assert inside[0].approx(inside[2]), "the reset did not return the earlier layout"


def test_a_region_starts_at_the_same_corner_in_every_rendering(deck_at, reflowing):
    """The region itself is asserted on its corner and not on its box.

    `MEASURE` reads the ink of a group, and the ink inside a region is exactly what an
    epoch changes, so the region's own box grows with its content while its footprint does
    not. What the fixed footprint promises is the corner the next thing is laid out from,
    which is why the tag below the region is where the promise is really tested.
    """
    presentation: Deck = deck_at(reflowing)
    corners = [presentation.rects("r", frame=frame)[0] for frame in range(3)]
    for frame, box in enumerate(corners[1:], start=1):
        assert abs(box.x - corners[0].x) <= 0.01, f"the region moved sideways in epoch {frame}"
        assert abs(box.y - corners[0].y) <= 0.01, f"the region moved down in epoch {frame}"
    assert corners[1].height > corners[0].height, "the replacement did not fill more of the region"


# The second invariant: what the pixels agree about, at rest and mid-crossfade.


def test_the_slide_is_identical_outside_the_region_between_epochs(deck_at, reflowing):
    """At rest, which is the endpoint of the claim the crossfade has to keep."""
    presentation: Deck = deck_at(reflowing)
    region = band(presentation)
    first = screenshot(presentation.current)
    second = screenshot(presentation.goto(1, 1).current)
    assert_identical_outside(first, second, region, what="the two epochs")


def crossing(presentation: Deck, *moments: float) -> list[np.ndarray]:
    """One raster per moment of a step across an epoch boundary, each taken in flight.

    Every raster of a mid-flight comparison is taken with the same animation in flight,
    including the ones that stand for the endpoints, because chromium 151 rasterises the
    glyphs of a frame differently while a group inside it has a running `opacity`
    animation. See *Findings*. A raster taken at rest and one taken mid-step therefore
    come off two different rendering paths, and comparing them would measure the path and
    not the transition. The endpoints are sampled just inside the step rather than at its
    ends, since an animation at its end time is finished and rasterises as at rest again.
    """
    shots = []
    for moment in moments:
        presentation.scrub(moment)
        shots.append(screenshot(presentation.current, animations="allow"))
    return shots


def test_it_is_still_identical_outside_the_region_mid_crossfade(page, deck_at, reflowing):
    """The claim during the transition, which is what the containment is really about.

    The outgoing rendering is scoped down to the region it is handing over, so it paints
    nothing anywhere else and the pixels outside are the incoming one's own, exactly.
    This and the test above are what chain the claim together: the two epochs agree
    outside the region at rest, and the step between them moves nothing outside it either.
    """
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    region = band(presentation)
    presentation.press("ArrowRight")
    opening, halfway, closing = crossing(presentation, 1, MIDPOINT, DURATION - 1)
    assert_identical_outside(opening, halfway, region, what="the step and its midpoint")
    assert_identical_outside(opening, closing, region, what="the step and its end")


def test_the_crossfade_midpoint_is_the_sum_of_the_two_renderings(
    page, deck_at, reflowing, browser_name
):
    """Inside the region, nothing dips: the midpoint is the average of the two epochs.

    This is the arithmetic `mix-blend-mode: plus-lighter` is there for. A plain opacity
    crossfade would wash the region out to about a quarter grey at this moment, which is
    62 out of 255 away from the average. See *Findings*.
    """
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    region = band(presentation)
    presentation.press("ArrowRight")
    shots = crossing(presentation, 1, MIDPOINT, DURATION - 1)
    before, halfway, after = (shot.astype(int) for shot in shots)
    rows = slice(region.y0, region.y1)
    assert (before[rows] != after[rows]).any(), (
        "the region showed the same thing at both ends of the step, so a cut would pass "
        "the comparison below as well"
    )
    difference = abs((before[rows] + after[rows]) / 2 - halfway[rows])
    deviation, pixels = BLEND[browser_name]
    assert difference.max() <= deviation, (
        f"the midpoint of the crossfade is {difference.max()}/255 from the exact sum"
    )
    assert int((difference > 1).any(axis=2).sum()) <= pixels, (
        "more of the region dipped than this engine was measured to"
    )


def test_the_crossfade_is_unchanged_with_a_background_and_an_overlay(
    page, deck_at, reflowing_layered, browser_name
):
    """The two layers are siblings of the canvas, so neither joins the blend inside it.

    Both halves of the region invariant are asserted again with them present: nothing
    outside the region moves while the step is in flight, and inside it the midpoint is
    still the exact sum of the two renderings rather than a washed-out quarter grey.
    The overlay's own ink is checked first, so that neither claim can hold because the
    layers are not there.
    """
    presentation: Deck = deck_at(reflowing_layered)
    page.add_style_tag(content=SLOW)
    assert presentation.frames.count() == 3
    at_rest = screenshot(presentation.current)
    corner = tuple(int(value) for value in at_rest[-2, -2])
    assert corner == (0, 0, 255), f"the overlay is not on the slide: its corner is {corner}"
    region = band(presentation)
    presentation.press("ArrowRight")
    shots = crossing(presentation, 1, MIDPOINT, DURATION - 1)
    before, halfway, after = shots
    assert_identical_outside(before, halfway, region, what="the step and its midpoint")
    assert_identical_outside(before, after, region, what="the step and its end")
    rows = slice(region.y0, region.y1)
    first, middle, last = (shot.astype(int)[rows] for shot in shots)
    difference = abs((first + last) / 2 - middle)
    deviation, pixels = BLEND[browser_name]
    assert difference.max() <= deviation, (
        f"the midpoint of the crossfade is {difference.max()}/255 from the exact sum"
    )
    assert int((difference > 1).any(axis=2).sum()) <= pixels


def test_stacked_renderings_render_as_a_single_one_does(deck_at, typst: TypstRunner):
    """Two renderings of identical content look like one, which is two claims at once.

    Stacking them puts every label of the slide in the DOM twice, and a browser resolves a
    `<use>` to the first matching id; that is harmless only because typst's def ids are
    content hashes, so equal ids mean equal content. And the `plus-lighter` the stylesheet
    puts on the renderings has to be the identity while one of them is showing on its own.
    Both are asserted against a control deck of one epoch with the same body, which is the
    deck that carries no blend at all, since a lone rendering is exempted.
    """
    body = '#tag("claim", wrap: block)[A claim.]\n\n  A paragraph after the claim.'
    stacked: Deck = deck_at(
        animated(typst, body, 'sub(replace("claim")[A claim.])', name="stacked.html")
    )
    assert stacked.frames.count() == 2
    first = screenshot(stacked.current)
    second = screenshot(stacked.goto(1, 1).current)
    single: Deck = deck_at(animated(typst, body, "sub()", name="single.html"))
    assert single.frames.count() == 1
    control = screenshot(single.current)
    # One rendering added to a transparent backdrop is that rendering, to within the
    # rounding the finding on *Crossfading epoch frames* allows `plus-lighter`: firefox 153
    # lands a single pixel of an antialiased glyph edge one step off.
    assert_identical(first, control, tol=1, what="the first of two renderings and a lone one")
    assert_identical(second, control, tol=1, what="the second of two renderings and a lone one")


# A mark of an exact colour on the canvas, at the top left of the body, which is one deck
# margin in from the corner of the viewport. A blend that reached the slide's own white
# ground would sum the two and take the mark to white.
GROUND = (
    '#place(top + left, rect(width: 2cm, height: 2cm, fill: rgb("#ff0000")))\n\n  '
    + REFLOWING
)


def test_the_blend_does_not_reach_the_ground_the_slide_is_painted_on(deck_at, typst: TypstRunner):
    """The containment the canvas is isolated for, now that the blend is on a group.

    `plus-lighter` on the epoch renderings adds them to their backdrop, and the opaque
    white of the slide container must not be in it: an opaque mark on the canvas would
    then be summed with white and come out white, which is what this reads.
    How far a group's blend reaches without the isolation differs between the engines,
    which is why animo states the containment rather than inheriting it. See *Findings*.
    """
    presentation: Deck = deck_at(
        animated(typst, GROUND, 'sub(replace("claim")[Another claim.])', name="ground.html")
    )
    assert presentation.frames.count() == 2
    shot = screenshot(presentation.current)
    # The deck is 16 by 9 cm with a 1 cm margin, so the mark spans 1 cm to 3 cm on both
    # axes; this is inside it whatever the window the screenshot was taken at.
    rows, columns = shot.shape[:2]
    mark = tuple(int(value) for value in shot[int(0.22 * rows), int(0.12 * columns)])
    assert mark == (255, 0, 0), f"the blend summed the slide ground into the canvas: {mark}"


# How a boundary composes with the continuous primitives, and with stepping.


def test_a_step_that_replaces_and_moves_animates_in_lockstep(page, deck_at, typst: TypstRunner):
    """Rule 1: continuous state goes on every rendering, not only on the one being shown.

    Entering an epoch then needs no initialisation, and the composite of a `replace` and a
    `move` reads correctly, because the tag is at the same place in the rendering that is
    fading out and in the one that is fading in.
    """
    presentation: Deck = deck_at(
        animated(
            typst,
            REFLOWING,
            f'sub(replace("claim")[{LONGER}], move("claim", x: 2cm))',
        )
    )
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    halfway = presentation.styles("claim")
    assert len(halfway) == 2, "the tag is not in both renderings"
    assert halfway[0] == halfway[1], f"the two renderings moved apart: {halfway}"
    presentation.scrub(DURATION)
    landed = presentation.styles("claim")
    assert landed[0] == landed[1], f"the two renderings landed apart: {landed}"


def test_a_deep_link_into_a_later_epoch_shows_it_without_animating(deck_at, reflowing):
    """A restore snaps, here into the middle of the stack rather than into its first entry."""
    presentation: Deck = deck_at(reflowing)
    presentation.goto(1, 2)
    assert presentation.painting == [False, False, True]
    assert presentation.page.evaluate("() => document.getAnimations().length") == 0


def test_stepping_back_across_a_boundary_returns_to_the_earlier_rendering(deck_at, reflowing):
    """Exactly the earlier pixels, which is what makes a boundary as reversible as a step."""
    presentation: Deck = deck_at(reflowing)
    before = screenshot(presentation.current)
    presentation.press("ArrowRight").settle()
    presentation.press("ArrowLeft").settle()
    assert presentation.position == (1, 0)
    assert_identical(before, screenshot(presentation.current), what="the state and its return")


# A tag that becomes no group and sits in no explicit region. Its content change is bounded
# by nothing, so the whole rendering is what the boundary hands over.
UNBOUNDED = '#tag("claim", wrap: none)[A short claim.] Text after the tag.'


@pytest.fixture
def unbounded(typst: TypstRunner):
    """A slide of two epochs whose change no region bounds."""
    return animated(
        typst,
        UNBOUNDED,
        f'sub(replace("claim")[{LONGER}])',
        name="unbounded.html",
    )


def test_a_change_no_region_bounds_redraws_the_whole_rendering(deck_at, unbounded):
    """A `wrap: none` tag outside a region has no box, so nothing smaller can be handed over.

    The plan names no group for it, which is how it says the rendering itself.
    """
    presentation: Deck = deck_at(unbounded)
    assert [epoch["regions"] for epoch in presentation.plan["epochs"]] == [
        [],
        [{"group": None}],
    ]


def test_the_whole_rendering_crossfades_rather_than_cutting(
    page, deck_at, unbounded, browser_name
):
    """Both renderings paint while the boundary runs, and the midpoint is their sum.

    This is the arithmetic the region crossfade is measured by, over the whole slide
    rather than over a band, because a change no region bounds leaves nothing still to
    compare outside.
    """
    presentation: Deck = deck_at(unbounded)
    page.add_style_tag(content=SLOW)
    assert presentation.painting == [True, False]
    presentation.press("ArrowRight")
    presentation.scrub(MIDPOINT)
    assert presentation.painting == [True, True], (
        "the outgoing rendering stopped painting, so the boundary cut"
    )
    shots = crossing(presentation, 1, MIDPOINT, DURATION - 1)
    before, halfway, after = (shot.astype(int) for shot in shots)
    assert (before != after).any(), (
        "the slide showed the same thing at both ends of the step"
    )
    difference = abs((before + after) / 2 - halfway)
    deviation, pixels = BLEND[browser_name]
    assert difference.max() <= deviation, (
        f"the midpoint of the crossfade is {difference.max()}/255 from the exact sum"
    )
    assert int((difference > 1).any(axis=2).sum()) <= pixels, (
        "more of the slide dipped than this engine was measured to"
    )


def test_a_region_of_its_own_is_crossfaded_by_the_tags_own_name(deck_at, typst: TypstRunner):
    """A tag with no explicit region around it is its own region, so its own group fades."""
    presentation: Deck = deck_at(
        animated(
            typst,
            '#tag("claim", wrap: block)[A short claim.]\n\n  Text after the tag.',
            f'sub(replace("claim")[{LONGER}])',
        )
    )
    assert [epoch["regions"] for epoch in presentation.plan["epochs"]] == [
        [],
        [{"group": "claim"}],
    ]
