# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Transforms inside a tag's wrappers are layout-neutral*.

The presentation PDF renders one page per state and applies the display state of that
state with typst's own `move`, `scale` and `hide`.
That is only honest if the page laid out the same way it would have without them,
because the invariant of the output is that nothing moves between two states
except what the timeline moved.

`move` and `scale` are block-level elements, so the wrapper around them is what makes this
work, and both halves of that are asserted here.
"""

from harness import TypstRunner

PRELUDE = """\
#set page(width: 12cm, height: 6cm)
#set text(size: 11pt)

// What a tag site emits, with the parameters the resolved display state puts in.
#let slot(body, dx: 0pt, dy: 0pt, factor: 100%, hidden: false) = box(box(move(
  dx: dx,
  dy: dy,
  scale(factor, reflow: false, if hidden { hide(body) } else { body }),
)))

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
#let fill(body, dx: 0pt) = block(width: 100%, block(width: 100%, move(dx: dx, body)))
#context {
  assert.eq(
    repr(measure(fill([word]), width: 8cm)),
    repr(measure(fill([word], dx: 20pt), width: 8cm)),
  )
}
"""
    )


def test_the_wrapper_is_what_contains_the_block_level_transforms(typst: TypstRunner):
    """`move` and `scale` are block-level, so without the box they would break the line.

    This is the reason the transforms go inside the tag's own wrapper
    rather than around it.
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
