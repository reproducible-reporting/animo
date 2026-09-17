# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Regions: an inline footprint has to pin its baseline*.

A tag on a line whose content changes between epochs reserves a fixed box,
and a fixed box is expected to hold its line still.
It does not, because a box takes its baseline from its content,
and a line is aligned on baselines rather than on boxes.
What does hold the line still is a box whose content is placed, which gives it no baseline,
lowered by the deepest descent over the epochs.
That needs the ascent and the descent of each epoch, which `measure` does not report,
so the probes also pin down how they are read.

These probes build the mechanism by hand, with no animo in sight.
"""

import pytest
from harness import TypstRunner

PRELUDE = """\
#set page(width: 300pt, height: 200pt, margin: 10pt)

// Epochs that differ in each way a line can notice:
// a short word, a taller first line, nothing at all, a second line, and math below the baseline.
#let epochs = (
  [short],
  text(size: 2em)[Tall],
  none,
  [x#linebreak()two lines],
  $sum_(i=1)^n x_i$,
)

#let pole-height = 10000pt
#let extent(c) = {
  if c == none { return (width: 0pt, ascent: 0pt, descent: 0pt) }
  let whole = measure(box(c))
  let descent = measure([#box(c)#box(width: 0pt, height: pole-height)]).height - pole-height
  (width: whole.width, ascent: whole.height - descent, descent: descent)
}

#let fixed(c, extents, e) = {
  let W = calc.max(..extents.map(m => m.width))
  let A = calc.max(..extents.map(m => m.ascent))
  let D = calc.max(..extents.map(m => m.descent))
  (
    plain: box(width: W, height: A + D, c),
    pinned: box(width: W, height: A + D, baseline: D, if c != none {
      place(top + left, dy: A - extents.at(e).ascent, box(c))
    }),
  )
}

#context {
  let extents = epochs.map(extent)
  [#metadata(extents)<extents>]
  for kind in ("plain", "pinned") {
    for (e, c) in epochs.enumerate() {
      page[
        Before #fixed(c, extents, e).at(kind)#metadata((kind: kind, e: e))<after> after.

        #metadata((kind: kind, e: e))<next>Next paragraph.
      ]
    }
  }
  for (e, c) in epochs.enumerate() {
    page[Before #box(c)#metadata((kind: "untouched", e: e))<after> after.]
  }
}

#let ys(label, kind) = query(label).filter(it => it.value.kind == kind).map(it => (
  it.location().position().y
))
"""


def test_a_fixed_size_box_still_takes_its_baseline_from_its_content(typst: TypstRunner):
    """The same box, at the same size, puts the rest of its line at different heights.

    This is the failure a fixed inline footprint would have.
    """
    typst.ok(
        PRELUDE
        + """
#context {
  let found = ys(<after>, "plain")
  assert(found.dedup().len() > 1, message: "the line held still after all: " + repr(found))
}
"""
    )


@pytest.mark.parametrize("label", ["after", "next"])
def test_a_box_with_placed_content_and_a_pinned_baseline_holds_its_line(typst: TypstRunner, label):
    """The rest of the line and the next paragraph are where they are in every epoch."""
    typst.ok(
        PRELUDE
        + f"""
#context {{
  let found = ys(<{label}>, "pinned")
  assert.eq(found.dedup().len(), 1, message: "the line moved: " + repr(found))
}}
"""
    )


def test_the_pinned_line_sits_where_the_tallest_epoch_puts_it(typst: TypstRunner):
    """The epoch with the tallest first line lays out as if nothing were pinned."""
    typst.ok(
        PRELUDE
        + """
#context {
  assert.eq(ys(<after>, "pinned").first(), ys(<after>, "untouched").at(1))
}
"""
    )


def test_the_descent_is_the_line_beside_a_tall_pole_less_the_pole(typst: TypstRunner):
    """Text ends at its baseline, and a second line or a subscript reaches below it.

    Text reaching nothing below the baseline is typst's default `bottom-edge`,
    which is why a word and a taller word have a descent of zero.
    """
    typst.ok(
        PRELUDE
        + """
#context {
  let extents = query(<extents>).first().value
  assert.eq(extents.at(0).descent, 0pt)
  assert.eq(extents.at(1).descent, 0pt)
  assert(extents.at(1).ascent > extents.at(0).ascent)
  assert(calc.abs(extents.at(3).ascent - extents.at(0).ascent) < 0.001pt)
  assert(extents.at(3).descent > 10pt)
  assert(extents.at(4).descent > 0pt)
}
"""
    )
