# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tiers 1 and 2: what a slide is called, and what one of its subslides is called.

A slide number is a counter and is asserted as one.
The subslide numbers a `per-subslide` callback is handed are asserted inside the callback,
which is the only place they exist: the stack is built while the slide is laid out,
and the numbers it is built from never leave it.

Both are asserted in both targets, because one number serving all three output types is
what the whole construct is for. The HTML target is the one where the value cannot be
chosen when the frame is rendered, so it is the one that has to agree by construction.

The paged tier asserts which rendering a page shows, and does so in colour rather than in
glyphs: what is being checked is that a page carries the rendering of its own state, and a
filled square says that where a rasterised numeral would need to be read.
"""

import numpy as np
import pytest
from decks import deck
from harness import PagedRunner, TypstRunner, assert_differs

# What every assertion here is wrapped in: a callback that checks the numbers it is handed
# and lays out nothing, so that the deck compiles whatever the numbers turn out to be.
CHECKS = """
#let expect(wanted) = per-subslide(it => {
  assert.eq(it, wanted.at(it.number - 1), message: "subslide " + repr(it))
  []
})
"""


def numbered(*slides: str) -> str:
    """A deck whose preamble defines the `expect` callback the assertions are written with."""
    return deck(*slides, preamble=CHECKS)


def numbers(*states: tuple[int, int, int, int]) -> str:
    """The subslide numbers a stack expects, as a typst array of one dictionary per state."""
    entries = ", ".join(
        f"(number: {number}, count: {count}, step: {step}, steps: {steps})"
        for number, count, step, steps in states
    )
    return f"#expect(({entries},))"


def timeline(count: int) -> str:
    """A timeline of `count` steps that changes nothing, so a slide has `count + 1` states."""
    return "animation: { import anim: *\n" + "sub()\n" * count + "}"


# The slide counter.


@pytest.mark.parametrize("html", [False, True])
def test_a_slide_number_is_the_counter_and_a_count_is_its_total(typst: TypstRunner, html):
    """The pair reads as "3 of 12", which is the whole of the slide-level surface."""
    source = deck(
        "slide[#context assert.eq((slide-number(), slide-count()), (1, 2))]",
        "slide[#context assert.eq((slide-number(), slide-count()), (2, 2))]",
    )
    typst.ok(source, html=html)


@pytest.mark.parametrize("html", [False, True])
def test_a_slide_that_is_not_numbered_has_no_number(typst: TypstRunner, html):
    """`none` rather than the number of the slide before it, which is what a counter holds.

    A title slide is the case, and a deck that shows a number unconditionally would
    otherwise print the previous slide's number on it.
    """
    source = deck(
        "slide[#context assert.eq(slide-number(), 1)]",
        "slide(numbered: false)[#context assert.eq(slide-number(), none)]",
        "slide[#context assert.eq(slide-number(), 2)]",
    )
    typst.ok(source, html=html)


@pytest.mark.parametrize("html", [False, True])
def test_a_slide_number_reads_the_same_in_a_layer_as_in_the_body(typst: TypstRunner, html):
    """An overlay is where a shown number goes, so the number has to be readable there."""
    read = "#context assert.eq(slide-number(), 2)"
    source = deck(
        "slide[first]",
        f"slide(background: [{read}], overlay: [{read}])[{read}]",
    )
    typst.ok(source, html=html)


# The subslide numbers of a subslide.


@pytest.mark.parametrize("html", [False, True])
def test_a_subslide_is_numbered_from_one_within_its_slide(typst: TypstRunner, html):
    """The number an audience reads, which is why it counts from one where a state does not.

    The URL fragment addresses state 0 of a slide, and the first subslide is number 1 of
    however many the slide has.
    """
    source = numbered(
        f"slide({timeline(2)})[{numbers((1, 3, 1, 3), (2, 3, 2, 3), (3, 3, 3, 3))}]",
    )
    typst.ok(source, html=html)


@pytest.mark.parametrize("html", [False, True])
def test_a_step_counts_every_state_of_every_slide_before_it(typst: TypstRunner, html):
    """The deck-wide pair, which is what a progress bar spanning the talk is measured on.

    It counts the states a presenter walks through and not the slides that carry a number,
    so a slide left out of the numbering still takes its own share of the talk.
    """
    source = numbered(
        f"slide(numbered: false, {timeline(1)})[{numbers((1, 2, 1, 5), (2, 2, 2, 5))}]",
        f"slide({timeline(2)})[{numbers((1, 3, 3, 5), (2, 3, 4, 5), (3, 3, 5, 5))}]",
    )
    typst.ok(source, html=html)


@pytest.mark.parametrize("html", [False, True])
def test_a_slide_without_a_timeline_has_one_subslide(typst: TypstRunner, html):
    """State 0 is a state like any other, so the ordinary slide reads "1 of 1"."""
    typst.ok(numbered(f"slide[{numbers((1, 1, 1, 1))}]"), html=html)


@pytest.mark.parametrize("html", [False, True])
def test_the_numbers_of_a_layer_are_the_numbers_of_the_body(typst: TypstRunner, html):
    """A stack in an overlay is the same stack, which is the point of putting it there.

    An overlay is one rendering per slide where the body is one per epoch, so the overlay
    is the cheaper place for a stack, and it may not be the poorer one.
    """
    expected = numbers((1, 2, 1, 2), (2, 2, 2, 2))
    source = numbered(f"slide(overlay: [{expected}], {timeline(1)})[{expected}]")
    typst.ok(source, html=html)


# What is refused.


@pytest.mark.parametrize("html", [False, True])
def test_a_per_subslide_outside_a_slide_is_refused(typst: TypstRunner, html):
    """It has no slide whose subslides it could be laid out for, and says so where written.

    A marker nobody replaced is indistinguishable from one that was, so the diagnosis
    cannot come afterwards, which is the reason a tag outside a slide is refused this way.
    """
    typst.fails(
        deck("slide[body]") + "\n#per-subslide(it => [#it.number])\n",
        "not inside a #slide",
        html=html,
    )


@pytest.mark.parametrize("html", [False, True])
def test_a_callback_that_returns_something_other_than_content_is_refused(
    typst: TypstRunner, html
):
    """Every rendering is laid out and stacked, so a value that is not content reaches none."""
    typst.fails(
        deck("slide[#per-subslide(it => it.number)]"),
        "per-subslide callback returns content",
        html=html,
    )


@pytest.mark.parametrize("html", [False, True])
def test_a_wrap_that_is_neither_auto_nor_a_container_is_refused(typst: TypstRunner, html):
    """A stack is animo's own container, so it takes neither a function nor `none`.

    Every rendering in it has to become a group the runtime can address, which is what a
    tag site may decline and a stack may not.
    """
    typst.fails(
        deck("slide[#per-subslide(it => [#it.number], wrap: none)]"),
        "wrap argument of per-subslide",
        html=html,
    )


@pytest.mark.parametrize("html", [False, True])
def test_a_tag_in_a_layer_is_still_refused(typst: TypstRunner, html):
    """The layers serve a stack and refuse a tag, and the second half has not moved.

    A stack addresses nothing in the timeline and is rendered by the slide for itself,
    where a tag in a layer is a name no timeline could reach.
    """
    typst.fails(
        deck('slide(overlay: [#tag("a")[x]])[body]'),
        "is in the overlay of slide 1",
        html=html,
    )


# Which rendering a page shows.

# One colour per subslide, so that a page says which state it is without being read.
# They are primaries, because a rasteriser has to agree about them exactly.
SWATCHES = ("#ff0000", "#00ff00", "#0000ff")

# The stack the paged tests place in the overlay: a filled square in the state's colour.
# It goes in the overlay because that is where a shown number belongs, and because the
# overlay is the layer the paged outputs place once per page.
SWATCH = (
    "per-subslide(it => rect(width: 1cm, height: 1cm, "
    "fill: rgb((" + ", ".join(f'"{colour}"' for colour in SWATCHES) + ").at(it.number - 1))))"
)


def swatched(*steps: str, **arguments: str) -> str:
    """A one-slide deck whose overlay carries the colour of the state being shown."""
    timeline = "{ import anim: *\n" + "\n".join(steps) + " }"
    extra = "".join(f", {key}: {value}" for key, value in arguments.items())
    return deck(
        f"slide(animation: {timeline}, overlay: place(top + left, {SWATCH}){extra})"
        "[\n  = A slide\n  With a line of text.\n]"
    )


def swatch_of(page: np.ndarray) -> tuple[int, int, int]:
    """The colour of the square the overlay places in the top left corner of a page."""
    return tuple(int(value) for value in page[14, 14])


def rgb(colour: str) -> tuple[int, int, int]:
    """A hexadecimal colour as the triple a raster holds."""
    return tuple(int(colour[index : index + 2], 16) for index in (1, 3, 5))


def box_of(page: np.ndarray, colour: tuple[int, int, int]) -> tuple[int, int, int, int] | None:
    """Where a raster holds this exact colour, as `(x0, y0, x1, y1)`, or `None`."""
    found = (page == np.array(colour, dtype=np.uint8)).all(axis=2)
    if not found.any():
        return None
    rows = np.flatnonzero(found.any(axis=1))
    cols = np.flatnonzero(found.any(axis=0))
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def test_the_presentation_shows_the_rendering_of_the_state_of_each_page(paged: PagedRunner):
    """One page per state, each carrying the rendering built for that state and no other."""
    pages = paged.png(swatched("sub()", "sub()"), mode="presentation")
    assert len(pages) == 3
    assert [swatch_of(page) for page in pages] == [rgb(colour) for colour in SWATCHES]


def test_the_handout_shows_the_rendering_of_the_state_it_kept(paged: PagedRunner):
    """The handout renders a subset of the states, and numbers them as the states they are.

    Its page numbering is not the subslide numbering, and this is where the two are most
    easily confused: the second page of this handout is the third subslide of the slide.
    """
    pages = paged.png(swatched("sub(handout: true)", "sub()"))
    assert len(pages) == 2
    assert [swatch_of(page) for page in pages] == [rgb(SWATCHES[1]), rgb(SWATCHES[2])]


def test_a_stack_reserves_the_same_footprint_in_every_state(paged: PagedRunner):
    """A number that grows a digit may not move what is beside it.

    The renderings are stacked in a container the size of the largest of them, which is
    the footprint rule an implicit region already follows, taken over the states rather
    than over the epochs. What is beside the stack is a square, so where it landed is read
    off the raster rather than guessed.
    """
    stack = 'per-subslide(it => [#("9" * it.number)])'
    source = deck(
        "slide(animation: { import anim: *\n  sub()\n  sub()\n })"
        f'[\n  #{stack} #box(fill: rgb("#ff0000"), width: 1cm, height: 1cm)\n]'
    )
    pages = paged.png(source, mode="presentation")
    assert len(pages) == 3
    boxes = [box_of(page, rgb("#ff0000")) for page in pages]
    assert all(box is not None for box in boxes), "the square is missing from a page"
    assert len(set(boxes)) == 1, f"the square moved between subslides: {boxes}"


def test_a_stack_whose_renderings_differ_really_renders_each_of_them(paged: PagedRunner):
    """The guard on the test above: the pages differ, so the stack is not laid out once.

    A footprint that holds still is only worth asserting about a stack whose content moves
    inside it.
    """
    stack = 'per-subslide(it => [#("9" * it.number)])'
    source = deck(
        "slide(animation: { import anim: *\n  sub()\n  sub()\n })"
        f"[\n  #{stack}\n]"
    )
    pages = paged.png(source, mode="presentation")
    assert_differs(pages[0], pages[1], what="subslide 1 and subslide 2")
    assert_differs(pages[1], pages[2], what="subslide 2 and subslide 3")
