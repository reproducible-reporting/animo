# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tiers 1 and 2: how many renderings a deck costs, and that the benchmark decks still build.

The recorded numbers under `benchmarks/results/` are seconds and bytes, and seconds belong
to a machine rather than to a repository, so nothing here asserts on them.
What does belong here is the cost model those numbers are divided by: how many times animo
asks typst to lay a deck out. That count follows from the timeline alone, is the same on
every machine, and is exactly what would change if a refactoring made animo slower.

The benchmark decks themselves are compiled here as well, without timing anything, so that
a change to the package breaks in the test suite rather than the next time somebody runs
the benchmark.
"""

import re

import pytest
from decks import deck
from harness import CETZ, PagedRunner, TypstRunner, compile_typst, require
from harness.typst import ROOT

# A deck whose three counts are all different, which is what makes the test say something:
# one rendering per epoch in HTML, one per state in the presentation, and one per state
# that asked for a page in the handout.
SLIDES = {
    # name: (slide source, states, epochs, handout pages)
    "static": ("slide[nothing happens]", 1, 1, 1),
    "continuous": (
        "slide(animation: {import anim: *\n"
        'sub(reveal("a"))\nsub(move("a", x: 1cm))\nsub(hide("a"))})'
        '[#tag("a")[a]]',
        4,
        1,
        1,
    ),
    "structural": (
        'slide(animation: {import anim: *\nsub(replace("b")[bb])\nsub(remove("b"))})[#tag("b")[b]]',
        3,
        3,
        1,
    ),
    "mixed": (
        "slide(animation: {import anim: *\n"
        'sub(move("c", x: 1cm))\nsub(handout: true, apply("c", emph))\nsub(hide("c"))})'
        '[#tag("c")[c]]',
        4,
        2,
        2,
    ),
    "unwanted": (
        "slide(animation: {import anim: *\n"
        'sub(handout: false, reveal("d"))})[#tag("d")[d]]',
        2,
        1,
        0,
    ),
}

DECK = deck(*(source for source, _, _, _ in SLIDES.values()))
STATES = sum(states for _, states, _, _ in SLIDES.values())
EPOCHS = sum(epochs for _, _, epochs, _ in SLIDES.values())
HANDOUT = sum(pages for _, _, _, pages in SLIDES.values())


def renderings_per_slide(markup: str) -> list[int]:
    """How many epoch renderings each slide of a compiled HTML deck holds, in slide order.

    A rendering is a labelled group inside the slide's canvas element, and a slide has one
    per epoch, all of them in one frame. Counting the labels rather than the frames is what
    keeps this a reading of the cost model: the frames are what the merge changed, and the
    renderings are what the model is about.
    """
    canvases = re.findall(r'<div class="animo-canvas"[^>]*>(.*?)</div>', markup, re.S)
    return [len(re.findall(r'data-typst-label="animo-epoch-\d+"', canvas)) for canvas in canvases]


def frames_per_slide(markup: str) -> list[int]:
    """How many inline SVGs each slide's canvas element holds, in slide order."""
    canvases = re.findall(r'<div class="animo-canvas"[^>]*>(.*?)</div>', markup, re.S)
    return [canvas.count("<svg") for canvas in canvases]


# The cost model, one output type at a time.


def test_the_html_output_renders_one_rendering_per_epoch(typst: TypstRunner):
    """Epochs and not states: a run of continuous steps shares one rendering."""
    markup = typst.html(DECK).read_text()
    assert renderings_per_slide(markup) == [epochs for _, _, epochs, _ in SLIDES.values()]
    assert sum(renderings_per_slide(markup)) == EPOCHS


def test_the_html_output_lays_every_epoch_of_a_slide_out_in_one_frame(typst: TypstRunner):
    """What the page weight follows: typst defines a glyph once per frame that uses it.

    The renderings of a slide therefore share one set of definitions, which no arrangement
    of several frames can reach from inside typst. See *Findings*.
    """
    markup = typst.html(DECK).read_text()
    assert frames_per_slide(markup) == [1] * len(SLIDES)


def test_the_presentation_renders_one_page_per_state(paged: PagedRunner):
    """Every step is a page, structural or not, because a page is a snapshot of a state."""
    assert len(paged.png(DECK, mode="presentation")) == STATES


def test_the_handout_renders_one_page_per_state_that_asked_for_one(paged: PagedRunner):
    """`handout:` is the only thing that says what a handout holds, in both directions."""
    assert len(paged.png(DECK)) == HANDOUT


def test_the_three_counts_are_genuinely_different():
    """Guards the three tests above: three equal numbers would make all of them vacuous."""
    assert len({STATES, EPOCHS, HANDOUT}) == 3


# The benchmark decks, compiled but not timed.

BENCHMARK = ROOT / "benchmarks" / "scaling.typ"

# A few points of the controlled deck, kept small so that the suite stays quick.
# The knobs are the ones `benchmarks/run.py` sweeps, and `slides` is turned down because
# what is under test is that the deck builds, not how long twelve of them take.
VARIANTS = {
    "base": {"slides": "2"},
    "epochs": {"slides": "2", "epochs": "3"},
    "regions": {"slides": "2", "epochs": "3", "regions": "2"},
    "sized": {"slides": "2", "epochs": "3", "regions": "2", "height": "3cm"},
    "figure": {"slides": "2", "epochs": "2", "regions": "1", "figure": "on"},
    "plain": {"slides": "2", "epochs": "3", "regions": "2", "plain": "on"},
}


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("mode", ["html", "presentation", "handout"])
def test_the_benchmark_deck_compiles(typst: TypstRunner, variant: str, mode: str):
    """Every knob of the controlled deck, in every output type.

    The benchmark is run rarely and by hand, so nothing else would notice that a change to
    the package stopped it compiling until somebody wanted a number from it.
    """
    require(typst, CETZ)
    sysinp = dict(VARIANTS[variant])
    if mode == "presentation":
        sysinp["animo"] = "presentation"
    if variant == "plain" and mode == "html":
        pytest.skip("the plain floor has no animo in it, so it has no HTML deck to build")
    result = compile_typst(
        BENCHMARK,
        output="-",
        fmt="html" if mode == "html" else "pdf",
        features=["html"] if mode == "html" else (),
        sysinp=sysinp,
    )
    result.check()


def test_the_controlled_deck_has_the_epochs_its_knobs_ask_for(typst: TypstRunner):
    """What the recorded seconds and bytes are divided by, asserted rather than assumed.

    A per-epoch cost is a measured time divided by a rendering count, so a benchmark that
    quietly stopped producing the epochs it was asked for would report a per-epoch cost
    that is not one.
    """
    require(typst, CETZ)
    markup = compile_typst(
        BENCHMARK,
        output=typst.scratch / "scaling.html",
        fmt="html",
        features=["html"],
        sysinp={"slides": "3", "epochs": "4", "regions": "2", "states": "2"},
    ).check()
    assert renderings_per_slide(markup.output.read_text()) == [4, 4, 4]
    assert frames_per_slide(markup.output.read_text()) == [1, 1, 1]
    # Two continuous steps and three structural ones, on top of the initial state.
    assert markup.output.read_text().count('data-animo-states="6"') == 3


PLACEMENTS = ROOT / "benchmarks" / "placements.typ"

# The four shapes of the placement deck, with few marks and few states, because what is
# under test is that the deck builds and not what a scatter of ten thousand marks costs.
PLACEMENT_VARIANTS = {
    "no-pan": {},
    "pan": {"pan": "on"},
    "pan-canvas": {"pan": "on", "canvas": "stated"},
    "pan-image": {"pan": "on", "marks": "image"},
}

PLACEMENT_KNOBS = {"points": "50", "states": "3"}


@pytest.mark.parametrize("variant", PLACEMENT_VARIANTS)
@pytest.mark.parametrize("mode", ["html", "presentation"])
def test_the_placement_deck_compiles(variant: str, mode: str):
    """Every shape of the placement deck, in the output types its numbers are taken in."""
    sysinp = {**PLACEMENT_KNOBS, **PLACEMENT_VARIANTS[variant]}
    if mode == "presentation":
        sysinp["animo"] = "presentation"
    compile_typst(
        PLACEMENTS,
        output="-",
        fmt="html" if mode == "html" else "pdf",
        features=["html"] if mode == "html" else (),
        sysinp=sysinp,
    ).check()


def test_the_placement_deck_renders_one_rendering_whatever_its_states(typst: TypstRunner):
    """What makes the recorded seconds the cost of the canvas rather than of the epochs.

    The slide holds continuous steps alone, so it has one epoch and one rendering however
    many states it is given, and the difference between two variants is the placements.
    """
    markup = compile_typst(
        PLACEMENTS,
        output=typst.scratch / "placements.html",
        fmt="html",
        features=["html"],
        sysinp={**PLACEMENT_KNOBS, "pan": "on"},
    ).check()
    text = markup.output.read_text()
    assert renderings_per_slide(text) == [1]
    assert text.count('data-animo-states="3"') == 1
