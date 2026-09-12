# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Introspection: the fields of a nested structure, and one occurrence per page*.

A tag site emits two nested wrappers around a `move` around a `scale` around the body.
Whether that structure can be read back from the label that names it decides how much of
animo is assertable without exporting anything: if it can, the display state a state
actually applied is a compile-time assertion rather than a raster comparison.

These probes build the structure by hand, with no animo in sight, and pin the two field
values that are easy to guess wrong along with the per-page occurrence rule.
"""

from harness import TypstRunner

PRELUDE = """\
#set page(width: 10cm, height: 6cm)

// The shape a tag site emits, written out as the implementation builds it.
#let slot(body, dx: 0pt, dy: 0pt, factor: 100%, hidden: false) = [#box(box(move(
  dx: dx,
  dy: dy,
  scale(factor, reflow: false, if hidden { hide(body) } else { body }),
)))<probe-slot>]
"""


def test_the_fields_of_the_structure_are_readable_all_the_way_down(typst: TypstRunner):
    """`query` hands back the element, and every wrapper's body is the next element."""
    typst.ok(
        PRELUDE
        + """
#slot([word], dx: 3pt, dy: -2pt, factor: 200%, hidden: true)
#context {
  let outer = query(<probe-slot>).first()
  assert.eq(outer.func(), box, message: repr(outer.func()))
  let inner = outer.body
  assert.eq(inner.func(), box, message: repr(inner.func()))
  let moved = inner.body
  assert.eq(moved.func(), move)
  assert.eq(moved.dx, 3pt)
  assert.eq(moved.dy, -2pt)
  let scaled = moved.body
  assert.eq(scaled.func(), scale)
  assert.eq(scaled.reflow, false)
  assert.eq(scaled.body.func(), hide)
  assert.eq(scaled.body.body, [word])
}
"""
    )


def test_a_scale_reports_ratios_and_has_no_factor_field(typst: TypstRunner):
    """A factor of 2 reads back as `200%`, on `x` and `y` rather than on `factor`.

    The constructor takes `factor` positionally, so the absence of the field is the
    surprise, and a test that asserts on it fails with "does not have field".
    """
    typst.ok(
        PRELUDE
        + """
#slot([word], factor: 200%)
#context {
  let scaled = query(<probe-slot>).first().body.body.body
  assert.eq(scaled.x, 200%)
  assert.eq(scaled.y, 200%)
  assert.eq(scaled.fields().keys().contains("factor"), false, message: repr(scaled.fields()))
}
"""
    )


def test_an_unset_stroke_on_a_box_reads_back_as_an_empty_dictionary(typst: TypstRunner):
    """Not `none` and not `auto`, which is how a plain wrapper is told from an inked one.

    A `wrap` function may give the inner slot ink of its own, and the outer slot animo
    matches to it may not have any, so the difference has to be assertable.
    """
    typst.ok(
        PRELUDE
        + """
#[#box(box(stroke: red, [word]))<probe-inked>]
#context {
  let outer = query(<probe-inked>).first()
  assert.eq(outer.stroke, (:), message: repr(outer.stroke))
  assert.ne(outer.body.stroke, (:), message: repr(outer.body.stroke))
}
"""
    )


def test_query_returns_one_occurrence_per_page(typst: TypstRunner):
    """Content laid out on several pages is several elements, in page order.

    This is what makes the whole timeline readable from one compilation:
    the presentation renders one page per state, so the n-th occurrence of a label is its
    rendering in state n.
    """
    typst.ok(
        PRELUDE
        + """
#let body = [word]
#for dx in (0pt, 5pt, 10pt) {
  page(slot(body, dx: dx))
}
#context {
  let found = query(<probe-slot>)
  assert.eq(found.len(), 3, message: repr(found.len()))
  assert.eq(found.map(it => it.body.body.dx), (0pt, 5pt, 10pt))
}
"""
    )
