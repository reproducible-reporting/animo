# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the morph, which carries what two epochs of a region share to its new place.

The primary assertion is geometric. At the midpoint of a step, every glyph the morph moves in
the outgoing region sits where a glyph of the same shape in the incoming region sits, and
both are halfway between the places the two are laid out at. That is what makes the pair sum
to one opaque glyph under the crossfade's `plus-lighter`, which the probe for *A morph keeps
the `plus-lighter` sum* measures on rasters.

The motion is measured rather than raced, by pausing what is in flight and stating the
moment, as `test_epochs_html.py` does for the crossfade.
"""

import math

import pytest
from decks import deck
from harness import UNDER, Box, Deck, TypstRunner, assert_identical_outside, screenshot

# How long a step takes in these tests, in milliseconds, and the moment sampled in it.
# Slowed down from animo's own 400 ms so that a paused animation cannot already have ended,
# and linear so that the moment sampled is the fraction of the route it looks like.
DURATION = 4000
MIDPOINT = DURATION / 2

SLOW = f":root {{ --animo-primitive-duration: {DURATION}ms; --animo-easing: linear }}"

# How far apart, in CSS pixels, two positions the morph puts at one point may be.
# The two are computed through two chains of matrices, which agree to a millionth of a pixel
# in chromium 151 and firefox 153, and the allowance is far below anything visible.
CLOSE = 0.05

# A glyph that moved less than this, in CSS pixels, is one the morph did not move.
STILL = 0.5


def timeline(*steps: str) -> str:
    """The animation argument of a slide, with the primitives imported inside it."""
    return "{ import anim: *\n  " + "\n  ".join(steps) + " }"


def animated(typst: TypstRunner, body: str, *steps: str, name: str = "deck.html"):
    """Compile a one-slide deck with a timeline, as a file the browser can open."""
    source = deck(f"slide(animation: {timeline(*steps)})[\n  #set text(size: 14pt)\n  {body}\n]")
    return typst.html(source, name=name)


# A paragraph in a region that reflows when a clause is inserted into it, with a recoloured
# word, a tag with a box of its own that the reflow carries along, and a tag whose content is
# replaced. The lines outside the region are what the containment is asserted on.
REFLOWING = """
  #tag("head", wrap: block)[A line above the region.]

  #region(name: "r")[
    #tag("eq")[Hello world]

    The quick brown fox #tag("ins", wrap: none)[] jumps over the #tag("w", wrap: none)[lazy]
    dog #tag("mark")[#box(width: 0.6cm, height: 0.3cm, fill: blue)] and the rest of this
    paragraph wraps onto another line.
  ]

  #tag("foot", wrap: block)[A line below the region.]
"""

# The step into the second epoch, and the one into a third for the tests of two boundaries.
INSERT = (
    'sub(replace("eq", transition: morph())[Oh, Hello world], '
    'replace("ins", transition: morph())[and an inserted clause], '
    'apply("w", text.with(fill: red), transition: morph()))'
)
SHORTEN = 'sub(replace("ins", transition: morph())[then], reset("eq", transition: morph()))'


@pytest.fixture
def reflowing(typst: TypstRunner):
    """A slide of three epochs, each crossed by a morph of the region `r`."""
    return animated(typst, REFLOWING, INSERT, SHORTEN)


# Where every glyph below a label is displayed, per epoch rendering of the slide shown, as
# `[href, x, y]` in CSS pixels. `getScreenCTM()` includes a running `translate`, so this is
# what the page shows. See *Findings*.
GLYPHS = (
    """label => {
    const slide = document.querySelector('.animo-slide[data-animo-current]');
    return ("""
    + UNDER
    + """)(slide, label).map(
        (groups) => groups.flatMap((group) => Array.from(
            group.querySelectorAll('use'),
            (use) => {
                const point = new DOMPoint(use.x.baseVal.value, use.y.baseVal.value)
                    .matrixTransform(use.getScreenCTM());
                return [use.href.baseVal, point.x, point.y];
            },
        )),
    );
}"""
)


def glyphs(presentation: Deck, label: str = "r") -> list[list[tuple[str, float, float]]]:
    """Where each glyph of a region is displayed, per epoch rendering."""
    return [
        [(href, x, y) for href, x, y in rendering]
        for rendering in presentation.page.evaluate(GLYPHS, label)
    ]


def distance(a: tuple[str, float, float], b: tuple[str, float, float]) -> float:
    """How far apart two displayed glyphs are, in CSS pixels."""
    return math.hypot(a[1] - b[1], a[2] - b[2])


def partners(outgoing, incoming, moved):
    """Every glyph of `outgoing` that moved, with the glyph of `incoming` displayed with it.

    `moved` is where the outgoing glyphs were laid out, so a glyph that sits elsewhere now is
    one the morph is carrying. Its partner is the glyph of the same shape at the same point,
    and a glyph with none is reported as `None`.
    """
    found = []
    for index, glyph in enumerate(outgoing):
        if distance(glyph, moved[index]) < STILL:
            continue
        partner = next(
            (
                other
                for other, candidate in enumerate(incoming)
                if candidate[0] == glyph[0] and distance(candidate, glyph) < CLOSE
            ),
            None,
        )
        found.append((index, partner))
    return found


def test_a_boundary_that_morphs_names_the_tags_it_changes(deck_at, reflowing):
    """The plan tells the morph which tags changed, which the next test rests on."""
    presentation: Deck = deck_at(reflowing)
    changed = presentation.plan["epochs"][1]["changed"]
    morph = {"transition": "morph"}
    assert changed == {"eq": morph, "ins": morph, "w": morph}


def test_every_moving_glyph_has_a_partner_halfway_along_its_route(page, deck_at, reflowing):
    """The claim the morph rests on, at the midpoint of the step.

    Every glyph that the outgoing region moves is displayed where a glyph of the same shape in
    the incoming region is displayed, and that point is halfway between where the two are
    laid out, which is where a linear route puts it.
    The count is what says the assertion is not vacuous: the inserted clause moves every
    glyph after it, and the replacement moves `Hello world`.
    """
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    rest = glyphs(presentation)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    halfway = glyphs(presentation)
    found = partners(halfway[0], halfway[1], rest[0])
    assert len(found) >= 40, f"only {len(found)} glyphs moved"
    for index, partner in found:
        assert partner is not None, f"outgoing glyph {index} has no partner at its position"
        start, end = rest[0][index], rest[1][partner]
        middle = ((start[1] + end[1]) / 2, (start[2] + end[2]) / 2)
        glyph = halfway[0][index]
        assert math.hypot(glyph[1] - middle[0], glyph[2] - middle[1]) < CLOSE, (
            f"outgoing glyph {index} is off its route"
        )


def test_every_moving_incoming_glyph_has_a_partner_too(page, deck_at, reflowing):
    """The same from the other side, so neither half of a pair travels alone."""
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    rest = glyphs(presentation)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    halfway = glyphs(presentation)
    found = partners(halfway[1], halfway[0], rest[1])
    assert len(found) >= 40
    assert all(partner is not None for _, partner in found)


def translating(presentation: Deck, label: str) -> list[bool]:
    """Whether each group of a label, in document order, has a `translate` animation running."""
    return presentation.page.evaluate(
        """label => Array.from(
            document.querySelectorAll(
                `.animo-slide[data-animo-current] [data-typst-label="${label}"]`
            ),
            (group) => group.getAnimations().some((animation) =>
                animation.effect.getKeyframes().some((frame) => "translate" in frame)),
        )""",
        label,
    )


def test_a_tag_the_boundary_leaves_alone_moves_as_one(page, deck_at, reflowing):
    """The box of `mark` has no glyph to match, and its tag carries it along the reflow.

    Its outer slot in each rendering is what moves, and the two copies are at one place at
    the midpoint.
    """
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    assert translating(presentation, "mark") == [True, True, False]
    outgoing, incoming = (presentation.rects("mark", frame=frame)[0] for frame in (0, 1))
    assert math.hypot(outgoing.x - incoming.x, outgoing.y - incoming.y) < CLOSE


def test_a_tag_the_boundary_changes_is_matched_by_its_glyphs(page, deck_at, reflowing):
    """`eq` is replaced, so its box is not carried as one, and its letters are.

    The tag keeps its box, which reserves the room of its wider version, so the group itself
    stays where it is. What moves is `Hello world` inside it, which the replacement shifts
    to the right of `Oh,`.
    """
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    rest = glyphs(presentation, "eq")
    presentation.press("ArrowRight").scrub(MIDPOINT)
    assert translating(presentation, "eq") == [False, False, False]
    halfway = glyphs(presentation, "eq")
    found = partners(halfway[0], halfway[1], rest[0])
    assert len(found) == len("Helloworld")
    assert all(partner is not None for _, partner in found)


def band(presentation: Deck) -> Box:
    """The rows of the slide that the region covers, as a full-width band."""
    box = presentation.current.bounding_box()
    found = presentation.rects("r")
    top = min(rect.y for rect in found) - box["y"]
    bottom = max(rect.y + rect.height for rect in found) - box["y"]
    return Box(0, max(0, int(top) - 1), int(box["width"]), int(bottom) + 2)


def test_nothing_outside_the_region_changes_during_the_morph(page, deck_at, reflowing):
    """The containment of the crossfade holds for the morph, which moves only inside it.

    Every raster is taken in flight, for the reason `test_epochs_html.py` gives.
    """
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    region = band(presentation)
    presentation.press("ArrowRight")
    shots = []
    for moment in (1, MIDPOINT, DURATION - 1):
        presentation.scrub(moment)
        shots.append(screenshot(presentation.current, animations="allow"))
    assert_identical_outside(shots[0], shots[1], region, what="the step and its midpoint")
    assert_identical_outside(shots[0], shots[2], region, what="the step and its end")


def resting(presentation: Deck) -> bool:
    """Whether no element of the slide shown carries a `translate` the runtime did not plan.

    A morph translation is an animation and never inline style, so once a step is over
    nothing below a region is translated.
    """
    return presentation.page.evaluate(
        """() => Array.from(
            document.querySelectorAll('.animo-slide[data-animo-current] .animo-canvas use'),
        ).every((use) => getComputedStyle(use).translate === 'none'
            && getComputedStyle(use.parentElement).translate === 'none')"""
    )


def test_a_step_at_rest_carries_no_morph_translation(deck_at, reflowing):
    """After the motion, the layout is what is shown, in every rendering."""
    presentation: Deck = deck_at(reflowing)
    presentation.press("ArrowRight").settle()
    assert resting(presentation)
    assert translating(presentation, "mark") == [False, False, False]


def test_a_deep_link_morphs_nothing(deck_at, reflowing):
    """A step that snaps creates no route, and the slide shows its layout at once."""
    presentation: Deck = deck_at(reflowing).goto(1, 1)
    assert presentation.page.evaluate("() => document.getAnimations().length") == 0
    assert resting(presentation)


def test_a_hard_cut_morphs_nothing(deck_at, typst: TypstRunner):
    """`duration: 0` is a cut, whatever the transition."""
    cut = INSERT.replace("transition: morph()", "transition: morph(), duration: 0")
    presentation: Deck = deck_at(animated(typst, REFLOWING, cut, name="cut.html"))
    presentation.press("ArrowRight")
    assert presentation.page.evaluate("() => document.getAnimations().length") == 0


def test_a_backward_step_morphs_back(page, deck_at, reflowing):
    """Stepping back plays the morph from the other end, with the same pairs."""
    presentation: Deck = deck_at(reflowing).goto(1, 1)
    page.add_style_tag(content=SLOW)
    rest = glyphs(presentation)
    presentation.press("ArrowLeft").scrub(MIDPOINT)
    halfway = glyphs(presentation)
    found = partners(halfway[1], halfway[0], rest[1])
    assert len(found) >= 40
    assert all(partner is not None for _, partner in found)
    presentation.scrub(DURATION).settle()
    assert presentation.position == (1, 0)
    assert resting(presentation)


def test_an_interrupted_morph_turns_back_from_where_it_is(page, deck_at, reflowing):
    """A backward step halfway through starts from what the page shows, so nothing jumps.

    The glyphs are displayed in the same place just after the second press as just before
    it, in both renderings, and the step back ends with the slide at rest.
    """
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    before = glyphs(presentation)
    presentation.press("ArrowLeft").scrub(0)
    after = glyphs(presentation)
    for rendering in (0, 1):
        for index, glyph in enumerate(before[rendering]):
            assert distance(glyph, after[rendering][index]) < CLOSE, (
                f"glyph {index} of rendering {rendering} jumped when the step turned back"
            )
    presentation.scrub(DURATION).settle()
    assert presentation.position == (1, 0)
    assert resting(presentation)


def test_two_quick_steps_across_two_boundaries_move_nothing_abruptly(page, deck_at, reflowing):
    """A second boundary of the region crossed while the first one's morph is still moving.

    The rendering the first step left is still fading out, and its glyphs go on to where
    they were going on the new clock. The rendering it entered is left in turn and starts
    from where it is displayed. Nothing jumps, and the slide ends at rest.
    """
    presentation: Deck = deck_at(reflowing)
    page.add_style_tag(content=SLOW)
    presentation.press("ArrowRight").scrub(MIDPOINT)
    before = glyphs(presentation)
    presentation.press("ArrowRight").scrub(0)
    after = glyphs(presentation)
    for rendering in (0, 1):
        for index, glyph in enumerate(before[rendering]):
            assert distance(glyph, after[rendering][index]) < CLOSE, (
                f"glyph {index} of rendering {rendering} jumped at the second boundary"
            )
    presentation.scrub(DURATION).settle()
    assert presentation.position == (1, 2)
    assert resting(presentation)


# A tag that is moved by a `move` in the same step as its content is replaced with a morph.
# The `move` drives the inner slot of the tag in both renderings, and the morph the glyphs
# below it, so the two compose.
MOVED = '#tag("t")[Hello world]'


def test_a_move_in_the_same_step_composes_with_the_morph(page, deck_at, typst: TypstRunner):
    """The two slots of a tag site at work: the copies stay together while both move."""
    presentation: Deck = deck_at(
        animated(
            typst,
            MOVED,
            'sub(replace("t", transition: morph())[Oh, Hello world], move("t", dx: 2cm))',
            name="moved.html",
        )
    )
    page.add_style_tag(content=SLOW)
    rest = glyphs(presentation, "t")
    presentation.press("ArrowRight").scrub(MIDPOINT)
    halfway = glyphs(presentation, "t")
    found = partners(halfway[0], halfway[1], rest[0])
    assert len(found) == len("Helloworld")
    assert all(partner is not None for _, partner in found)
    presentation.scrub(DURATION).settle()
    shift = 2 / 2.54 * 72 * presentation.unit
    final = glyphs(presentation, "t")
    for index, glyph in enumerate(final[1]):
        assert abs(glyph[1] - rest[1][index][1] - shift) < CLOSE
