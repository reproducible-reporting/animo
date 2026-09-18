# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A fixed-height container stacks the block-level content that does not fit*.

The height of the box a slide body is laid out in is decided by this behaviour.
A body whose flow is taller than the viewport is what `pan` is for,
and it only reaches the content below the fold if that content was laid out there at all.

The trap is that prose and blocks part ways: a paragraph runs past the bottom edge and keeps
its line spacing, while every block that does not fit is painted at the edge, on top of the
previous one. A slide of running text therefore pans correctly and the same slide with its
steps in blocks comes out as a pile, which is why this is a probe and not a comment.
"""

from harness import TypstRunner

PAGE = """\
#set page(width: 300pt, height: 600pt, margin: 0pt)
#set text(size: 10pt)
#set block(spacing: 0pt)
"""

FILLER = '#let filler = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 20\n'


def blocks(kind: str = "block", height: str = "100pt", count: int = 24) -> str:
    """A container holding more one-line blocks than fit, each labelled with its position."""
    return (
        PAGE
        + """
#place(top + left, KIND(width: 200pt, height: HEIGHT, {
  for i in range(COUNT) {
    block(width: 100%)[#metadata(i)#label("blk")Block #i]
  }
}))
""".replace("KIND", kind)
        .replace("HEIGHT", height)
        .replace("COUNT", str(count))
    )


STACKED = """\
#context {
  let ys = query(<blk>).map(it => it.location().position().y)
  let over = ys.filter(y => y >= 100pt)
  assert(
    over.len() >= 8,
    message: "only " + str(over.len()) + " blocks reached the bottom edge",
  )
  assert(
    over.all(y => calc.abs(y - over.first()) < 0.01pt),
    message: "the blocks past the bottom edge are not stacked: " + repr(over),
  )
  assert(
    calc.abs(over.first() - 100pt) < 0.01pt,
    message: "they stacked somewhere other than the bottom edge: " + repr(over.first()),
  )
}
"""


def test_a_block_that_does_not_fit_is_stacked_at_the_bottom_edge(typst: TypstRunner):
    """The behaviour that decides how tall a slide body's box has to be.

    Twenty-four one-line blocks go into a container 100 pt tall that holds sixteen of them.
    Measured on typst 0.15.0, the sixteen land 6.58 pt apart and the remaining eight are all
    at exactly 100 pt, the bottom edge, each drawn over the one before it.
    """
    typst.ok(blocks() + STACKED)


def test_a_box_container_stacks_them_in_the_same_way(typst: TypstRunner):
    """Reaching for a `box` instead of a `block` is the obvious escape, and it is not one.

    Recorded because the two containers differ in so much else that the difference is easy
    to expect here as well.
    """
    typst.ok(blocks(kind="box") + STACKED)


def test_a_paragraph_runs_past_the_bottom_edge_instead(typst: TypstRunner):
    """The contrast that makes the stacking easy to miss.

    The same container, filled with running text rather than with blocks, lays every line out
    where it belongs and simply paints past its own bottom edge: measured on typst 0.15.0, the
    end of a paragraph that is 100 pt of container tall sits at 333.58 pt.
    """
    source = (
        PAGE
        + FILLER
        + """
#place(top + left, block(width: 200pt, height: 100pt, [#filler#metadata(0)#label("end")]))

#context {
  let y = query(<end>).first().location().position().y
  assert(
    y > 300pt,
    message: "the paragraph did not run past the bottom edge, it ended at " + repr(y),
  )
}
"""
    )
    typst.ok(source)


def test_a_container_tall_enough_for_the_flow_lays_every_block_out_in_order(typst: TypstRunner):
    """The remedy, which is the one animo applies to the box it lays a slide body out in.

    The height comes from an unbounded measurement of the body, so the container is never the
    one that is too short, whatever the canvas around it turns out to be.
    """
    source = (
        blocks(height="400pt")
        + """
#context {
  let ys = query(<blk>).map(it => it.location().position().y)
  for (before, after) in ys.zip(ys.slice(1)) {
    assert(
      after > before,
      message: "two blocks stacked at " + repr(before) + " in a container tall enough",
    )
  }
}
"""
    )
    typst.ok(source)
