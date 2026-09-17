# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Transforms between a tag's slots are layout-neutral*.

The presentation PDF renders one page per state and applies the display state of that
state with typst's own `move`, `scale` and `hide`.
That is only honest if the page laid out the same way it would have without them,
because the invariant of the output is that nothing moves between two states
except what the timeline moved.

`move` and `scale` are block-level elements, so the slot around them is what makes this
work, and both halves of that are asserted here.
The size a slot takes is not the whole of the claim, though.
A `move` is laid out as an inline element,
so a block-level payload inside one is laid out in a paragraph,
which is what decides where the display state sits relative to the wrapper it applies to.
That second measurement is made on the centred bodies of *Wrapping a tag site*.
A rendering is also measured on its own, by the footprint of a region on a line,
and the ascent and the descent it reports there are the third measurement.
"""

import pytest
from harness import PagedRunner, TypstRunner, assert_differs, assert_identical
from test_wrapping import CENTRED, flow

PRELUDE = """\
#set page(width: 12cm, height: 6cm)
#set text(size: 11pt)

// The display state of one rendering, with the parameters the resolved state puts in.
#let displayed(body, dx: 0pt, dy: 0pt, factor: 100%, hidden: false) = move(
  dx: dx,
  dy: dy,
  scale(factor, reflow: false, if hidden { hide(body) } else { body }),
)

// What a tag site emits: the display state between the two slots.
#let slot(body, ..args) = box(displayed(box(body), ..args))

// The same measurement the layout around a tag site performs.
#let inline(body) = measure([Aa#body#h(0pt)Aa], width: 8cm)
"""


def test_a_transform_inside_the_wrapper_changes_no_layout(typst: TypstRunner):
    """Every display state a tag can be in occupies the space of the untouched body.

    Moved, scaled and hidden all measure as the plain box does,
    in the box itself and in the line that holds it.
    """
    typst.ok(
        PRELUDE
        + """
#context {
  let plain = slot([word])
  for variant in (
    slot([word], dx: 5pt, dy: 3pt),
    slot([word], factor: 200%),
    slot([word], hidden: true),
    slot([word], dx: 5pt, factor: 50%, hidden: true),
  ) {
    assert.eq(repr(measure(variant)), repr(measure(plain)), message: "the slot resized")
    assert.eq(repr(inline(variant)), repr(inline(plain)), message: "the line around it moved")
  }
}
"""
    )


def test_the_same_holds_for_the_filling_wrapper(typst: TypstRunner):
    """Block-level tag sites use `block(width: 100%)`, and the transforms are as quiet there."""
    typst.ok(
        PRELUDE
        + """
#let fill(body, dx: 0pt) = block(width: 100%, move(dx: dx, block(width: 100%, body)))
#context {
  assert.eq(
    repr(measure(fill([word]), width: 8cm)),
    repr(measure(fill([word], dx: 20pt), width: 8cm)),
  )
}
"""
    )


def test_the_slots_are_what_contain_the_block_level_transforms(typst: TypstRunner):
    """`move` and `scale` are block-level, so without a slot they would break the line.

    This is the reason the transforms sit inside the tag's own slots
    rather than around them.
    """
    typst.ok(
        PRELUDE
        + """
#let nothing = box(width: 0pt, height: 0pt)
#let breaks(body) = measure([#nothing#body#nothing]).height - measure(body).height
#context {
  assert(breaks(move(dx: 1pt)[word]) > 0pt, message: "move stopped being block-level")
  assert(breaks(scale(50%)[word]) > 0pt, message: "scale stopped being block-level")
  assert.eq(breaks(box(move(dx: 1pt)[word])), 0pt, message: "the box did not contain it")
}
"""
    )


def test_a_rendering_reports_its_baseline_only_inside_a_slot(typst: TypstRunner):
    """The pole that a descent is read off shares a line with inline content alone.

    A footprint on a line reserves an ascent and a descent over its renderings,
    and each rendering carries a display state.
    `measure` reports a height and no baseline,
    so the descent is read off a line that holds the content beside a zero-width pole
    taller than it.
    A `move` is block-level and pushes that pole onto a line of its own,
    so a rendering measured with no slot around it reports a descent of a whole line
    and an ascent below zero.
    The height is the same either way, which is what keeps this out of sight
    until one rendering of the footprint lays nothing out.
    """
    typst.ok(
        PRELUDE
        + """
#let pole = 10000pt
#let extent(body) = {
  let whole = measure(body)
  let descent = measure([#body#box(width: 0pt, height: pole)]).height - pole
  (height: whole.height, ascent: whole.height - descent, descent: descent)
}
#context {
  let plain = extent(box[hidden])
  let inside = extent(slot([hidden]))
  let bare = extent(displayed(box[hidden]))
  assert.eq(repr(inside), repr(plain), message: "the slot stopped holding the move")
  assert.eq(repr(bare.height), repr(plain.height), message: "the height changed as well")
  assert(bare.ascent < 0pt, message: "the ascent stayed on the line: " + repr(bare))
  assert(
    bare.descent > plain.descent + 10pt,
    message: "the pole shared the line after all: " + repr(bare),
  )
}
"""
    )


# The display state a tag site puts on its content, at the identity, which is what a state
# that moves nothing emits and what the HTML target emits everywhere.
# `X` is where the payload goes.
DISPLAYED = "move(dx: 0pt, dy: 0pt, scale(x: 100%, y: 100%, reflow: false, X))"

# Where the display state sits relative to the filling wrapper, with both slots around it.
ORDERS = {
    "inside": "block(width: 100%, block(width: 100%, " + DISPLAYED + "))",
    "around": "block(width: 100%, " + DISPLAYED.replace("X", "block(width: 100%, X)") + ")",
}


def transformed(body: str, order: str) -> str:
    """The same page with the body in the two slots and the display state at one of them."""
    return flow(ORDERS[order].replace("X", body))


@pytest.mark.parametrize("body", CENTRED)
def test_a_move_inside_the_filling_wrapper_left_aligns_centred_content(
    paged: PagedRunner,
    body,
):
    """A `move` is laid out as an inline element.

    A block-level payload inside one is laid out in a paragraph rather than as a block,
    so it is aligned to the paragraph's start and the filling block outside the `move` has
    nothing left to centre.
    """
    assert_differs(
        paged.png(flow(body), ppi=144)[0],
        paged.png(transformed(body, "inside"), ppi=144)[0],
        what=f"a move inside the filling wrapper, around {body}",
    )


@pytest.mark.parametrize("body", CENTRED)
def test_a_move_around_the_filling_wrapper_keeps_centred_content_centred(
    paged: PagedRunner,
    body,
):
    """The display state of a site therefore goes around its inner slot.

    The filling block is then inside the `move` and fills the paragraph the `move` opened,
    so the content sits where it did without any wrapper at all.
    """
    assert_identical(
        paged.png(flow(body), ppi=144)[0],
        paged.png(transformed(body, "around"), ppi=144)[0],
        # The same one greyscale step on a few pixels that a filling wrapper alone costs,
        # which is the rounding of a fractional position and not a shift.
        tol=1,
        what=f"a move around the filling wrapper, around {body}",
    )
