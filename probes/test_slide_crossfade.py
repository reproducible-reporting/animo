# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Crossfading two slide containers*
and for *Chromium rasterises a frame differently while an opacity animation runs in it*.

The epoch crossfade blends two inline SVGs inside the canvas, which is a container with no
ground of its own. A slide boundary blends two *HTML* elements that each carry an opaque
background, inside the deck, which is the element that centres a slide on a surround.
Two things are different there and both are measured here: whether `plus-lighter` still
sums two opaque grounds to their average, and where the surround's own colour has to sit
so that it does not join that sum.

The second is the one that cost the time. The ground of the element that isolates a blend
is inside the group it isolates, so a surround written on the deck is added to both slides
at every moment of a crossfade. A black surround hides that completely, because zero is
what adding nothing looks like, and a deck that restated it would have found out the hard
way.

*Chromium rasterises a frame differently while an opacity animation runs in it* is asserted
at the end of the module, on those same two containers. A slide boundary is where animo drives
an opacity animation, and the rounding that finding measures is what decides how exact a
mid-flight comparison in a feature test may be.
"""

import numpy as np
import pytest
from harness import TypstRunner, screenshot
from htmldoc import document

# Two slides of different opaque grounds, which is the case a crossfade gets wrong when it
# covers rather than adds: at the midpoint a plain opacity crossfade lands well below the
# average of the two, because the surround shows through the half-transparent pair.
GROUNDS = ("#204080", "#a06020")

# The deck and its two slides, as animo builds them: the slides stacked in one grid cell of
# an isolated parent, each a positioned box with a ground and an inline SVG of typst ink.
# The surround is a parameter, because where it sits is half of what is probed.
DECK_CSS = """\
html, body {{ margin: 0; padding: 0; background: {page}; }}
.deck {{
  display: grid;
  place-items: center;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  isolation: isolate;
  background: {deck};
}}
.deck > * {{ grid-row: 1; grid-column: 1; }}
.slide {{ position: relative; overflow: hidden; width: 300pt; height: 169pt; }}
.slide > svg {{ display: block; width: 100% !important; height: 100% !important; }}
.slide:nth-child(1) {{ background: {first}; }}
.slide:nth-child(2) {{ background: {second}; }}
{extra}"""

INK = (
    "#block(width: 300pt, height: 169pt)[\n"
    "  #place(top + left, dx: 20pt, dy: {dy}pt)[Slide {index}]\n"
    "]"
)


def deck(extra: str, page: str = "#000000", ground: str = "transparent") -> str:
    """A two-slide deck, with the surround on the page and not on the deck by default."""
    css = DECK_CSS.format(
        page=page,
        deck=ground,
        first=GROUNDS[0],
        second=GROUNDS[1],
        extra=extra,
    )
    inner = "\n".join(
        f'  #html.elem("div", attrs: (class: "slide"), html.frame[{INK.format(index=i, dy=20 + 40 * i)}])'
        for i in (1, 2)
    )
    return document(f'#html.elem("div", attrs: (class: "deck"))[\n{inner}\n]', css)


ONLY_FIRST = ".slide:nth-child(2) { opacity: 0; }\n"
ONLY_SECOND = ".slide:nth-child(1) { opacity: 0; }\n"
HALF = ".slide { opacity: 0.5; }\n"
LIGHTER = HALF + ".slide { mix-blend-mode: plus-lighter; }\n"


def shot(typst: TypstRunner, open_page, source: str, name: str) -> np.ndarray:
    """Render one deck and return its pixels."""
    return screenshot(open_page(typst.html(source, name=name)))


def deviation(reference: np.ndarray, image: np.ndarray) -> tuple[int, int]:
    """How far two images sit apart, as a maximum out of 255 and a count of pixels."""
    difference = abs(reference.astype(int) - image.astype(int))
    return int(difference.max()), int((difference > 1).any(axis=2).sum())


# How far a blended midpoint may sit from the average of the two slides, per engine, as a
# deviation out of 255 and a count of pixels allowed to exceed one.
#
# Exact is the claim, and chromium 151 and firefox 153 meet it to within rounding.
# Playwright ships no webkit build for the distribution these were written on, so webkit
# keeps the allowance *Crossfading epoch frames* measured for it, and continuous
# integration is what holds it to that.
EXACT = {"chromium": (1, 0), "firefox": (1, 0), "webkit": (48, 512)}


def halves(typst: TypstRunner, open_page, name: str, **ground) -> np.ndarray:
    """The average of the two slides shown alone, which is what a crossfade has to hit."""
    first = shot(typst, open_page, deck(ONLY_FIRST, **ground), f"{name}-first.html")
    second = shot(typst, open_page, deck(ONLY_SECOND, **ground), f"{name}-second.html")
    return (first.astype(int) + second.astype(int)) / 2


def test_a_plain_crossfade_of_two_slides_dips(typst: TypstRunner, open_page):
    """The reason `plus-lighter` is not a nicety here either.

    Two opaque grounds at half opacity do not come to their average: each is composited
    over what is behind it, so the surround shows through both and the midpoint lands far
    below either slide. Asserted for every engine rather than tabulated per engine,
    because an engine that does not dip here would mean something about `opacity` changed.
    """
    average = halves(typst, open_page, "plain")
    plain = shot(typst, open_page, deck(HALF), "plain-half.html")
    measured, _ = deviation(average, plain)
    assert measured > 32, f"the plain crossfade did not dip: {measured}/255"


def test_plus_lighter_sums_two_slide_containers(typst: TypstRunner, open_page, browser_name):
    """What animo does, and the whole of why a boundary is a crossfade at all.

    The blend is on the containers and reaches across them, unlike the blend on a region's
    group inside an inline SVG, because these are two siblings in one stacking context and
    not two roots of two SVGs.
    """
    average = halves(typst, open_page, "lighter")
    blended = shot(typst, open_page, deck(LIGHTER), "lighter-half.html")
    measured, pixels = deviation(average, blended)
    allowed_deviation, allowed_pixels = EXACT[browser_name]
    assert measured <= allowed_deviation, (
        f"the midpoint drifted from the average of the two slides: {measured}/255"
    )
    assert pixels <= allowed_pixels, f"{pixels} pixels dipped during the crossfade"


def test_one_slide_added_to_the_isolated_backdrop_is_that_slide(
    typst: TypstRunner, open_page, browser_name
):
    """The blend may therefore stay on every slide rather than be turned on per boundary.

    A slide carrying `plus-lighter` while nothing else in the group paints has to render
    as the same slide without it, or a deck would look different for having a transition
    it is not currently taking.
    """
    plain = shot(typst, open_page, deck(ONLY_SECOND), "single-plain.html")
    blended = shot(
        typst,
        open_page,
        deck(ONLY_SECOND + ".slide { mix-blend-mode: plus-lighter; }\n"),
        "single-blended.html",
    )
    measured, pixels = deviation(plain, blended)
    allowed_deviation, allowed_pixels = EXACT[browser_name]
    assert measured <= allowed_deviation, f"one blended slide is not that slide: {measured}/255"
    assert pixels <= allowed_pixels, f"{pixels} pixels changed under the blend"


@pytest.mark.parametrize("surround", ["#000000", "#ffffff"])
def test_the_ground_of_the_isolating_element_joins_the_sum(
    typst: TypstRunner, open_page, surround
):
    """Where the surround's colour has to sit, which is not on the element that isolates.

    The same two slides are crossfaded twice, with the surround on the page and with it on
    the deck. On the page it is outside the isolated group and the midpoint is the average
    of the two slides whatever the colour. On the deck it is inside, and a white surround
    is added to both halves and blows the midpoint out. Black is the one colour that hides
    the mistake, which is why both are probed and why the black case is not the assertion.
    """
    average = halves(typst, open_page, f"ground-{surround[1:]}", page=surround)
    on_the_page = shot(
        typst, open_page, deck(LIGHTER, page=surround), f"page-{surround[1:]}.html"
    )
    measured, _ = deviation(average, on_the_page)
    assert measured <= 1, f"a surround on the page reached the sum: {measured}/255"
    on_the_deck = shot(
        typst,
        open_page,
        deck(LIGHTER, page=surround, ground=surround),
        f"deck-{surround[1:]}.html",
    )
    measured, _ = deviation(average, on_the_deck)
    if surround == "#000000":
        assert measured <= 1, "black is the identity of plus-lighter and should add nothing"
    else:
        assert measured > 32, (
            f"a light surround on the isolating element did not reach the sum: {measured}/255"
        )


# Sampling a crossfade while it runs, for *Chromium rasterises a frame differently while an
# opacity animation runs in it*.
#
# The cases above state an opacity in a stylesheet and rasterise the result.
# A slide boundary states it in an animation instead,
# and what an engine rasterises while that animation runs is not always what it rasterises at
# rest.
# The difference is the rounding that every mid-flight comparison in the feature tests carries.

# How long the crossfade these cases pause runs for, in milliseconds,
# and how far inside it the two rasters that stand for its ends are taken.
# One step leaves the container being faded out at an opacity of 0.99975 rather than at rest,
# which is as close to the slide alone as a raster taken in flight comes.
DURATION = 4000
STEP = 1

# The two slides blended, with the second one hidden until the animation moves it.
FADING = ONLY_FIRST + ".slide { mix-blend-mode: plus-lighter; }\n"

# How far a raster taken one step inside a crossfade sits from the same page at rest, per
# engine, as a deviation out of 255 and whether the two rasters differ at all.
#
# Chromium 151 is the engine that differs, which is the finding.
# It promotes the container it is fading and rasterises the ground of that container a unit
# below the ground at rest, over the whole slide rather than on glyph edges.
# Measured at 1/255 on 2026-09-17.
# The allowance is a step above the 2/255 that a deck of animo's own implies, whose midpoint
# comparison came to 1.5/255 on a continuous integration runner.
# Firefox 153 shows none of it.
# Playwright ships no webkit build for the distribution this was measured on, so webkit has no
# row and the case skips with the number that fills one in.
IN_FLIGHT = {"chromium": (3, True), "firefox": (0, False), "webkit": None}

# How far the midpoint of a paused crossfade sits from the average of the two rasters that
# stand for its ends, per engine, out of 255, every raster taken with the animation in flight.
# This is the rounding the mid-flight comparisons of `tests/` allow for, measured on the
# mechanism alone: 1/255 in chromium 151 and 0.5/255 in firefox 153 on 2026-09-17.
MID_FLIGHT = {"chromium": 3, "firefox": 3, "webkit": None}


def crossfade(page) -> None:
    """Start the crossfade of the two slides and pause it where it began."""
    page.evaluate(
        """duration => {
            const opacities = [["1", "0"], ["0", "1"]];
            document.querySelectorAll(".slide").forEach((slide, index) => {
                const animation = slide.animate(
                    opacities[index].map((opacity) => ({opacity})),
                    {duration, easing: "linear"},
                );
                animation.pause();
            });
        }""",
        DURATION,
    )


def at(page, moment: float) -> np.ndarray:
    """The raster of one moment of the paused crossfade, taken with it in flight."""
    page.evaluate(
        """moment => {
            for (const animation of document.getAnimations()) animation.currentTime = moment;
        }""",
        moment,
    )
    return screenshot(page, animations="allow").astype(int)


def test_a_raster_taken_in_flight_is_not_the_page_at_rest(
    typst: TypstRunner, open_page, browser_name
):
    """The finding, and the reason a mid-flight comparison takes every raster in flight.

    One page is rasterised twice: at rest, and with a crossfade paused one step inside it.
    The slide the crossfade starts from is at an opacity of 0.99975 there and the slide it
    ends on at 0.00025, so the picture is the first slide in both rasters.
    A difference between them is the rendering path rather than the transition.
    """
    page = open_page(typst.html(deck(FADING), name="fading.html"))
    at_rest = screenshot(page)
    crossfade(page)
    measured, _ = deviation(at_rest, at(page, STEP))
    row = IN_FLIGHT[browser_name]
    if row is None:
        # A real skip, reported by `pytest -rs`, carrying the number that fills the row in.
        pytest.skip(
            f"{browser_name} has no measured row: one step into a crossfade it rasterised "
            f"{measured}/255 from the page at rest"
        )
    allowed, differs = row
    assert measured <= allowed, (
        f"{browser_name} rasterised the first step of a crossfade {measured}/255 from the "
        f"page at rest"
    )
    assert (measured > 0) == differs, (
        f"{browser_name} rasterised the first step of a crossfade {measured}/255 from the "
        f"page at rest, where its row says {'a difference' if differs else 'none'}"
    )


def test_the_midpoint_in_flight_is_the_average_of_the_two_ends_in_flight(
    typst: TypstRunner, open_page, browser_name
):
    """What a feature test asserts about a slide boundary, on the mechanism alone.

    Three rasters of one paused crossfade: one step inside each end, and the midpoint.
    The blend sums, so the average of the two ends is the midpoint, and what is left over is
    the rounding of three eight-bit rasters and of the end that is not the slide at rest.
    The two ends are checked against each other first, since a crossfade between two equal
    pictures would meet the claim without summing anything.
    """
    page = open_page(typst.html(deck(FADING), name="fading-midpoint.html"))
    crossfade(page)
    before, halfway, after = (at(page, moment) for moment in (STEP, DURATION / 2, DURATION - STEP))
    apart, _ = deviation(before, after)
    assert apart > 32, f"the two ends of the crossfade are {apart}/255 apart"
    measured = float(abs((before + after) / 2 - halfway).max())
    allowed = MID_FLIGHT[browser_name]
    if allowed is None:
        # A real skip, reported by `pytest -rs`, carrying the number that fills the row in.
        pytest.skip(
            f"{browser_name} has no measured row: its midpoint sat {measured}/255 from the "
            f"average of the two ends"
        )
    assert measured <= allowed, (
        f"the midpoint of the crossfade is {measured}/255 from the average of its two ends"
    )
