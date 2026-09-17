# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Introspection: positions*.

Positions are available in the paged target and dead in the HTML one.
That asymmetry is why the HTML output animates with CSS rather than with typst-computed
offsets, and why regions are sized by `measure` rather than placed by coordinates.
"""

from harness import TypstRunner

PAGED = """\
#set page(width: 300pt, height: 200pt, margin: 20pt)
#v(40pt)
$ a + #[#box[b]#label("in-math")] = c $

#box[plain]#label("in-flow")
"""


def test_paged_positions_are_real(typst: TypstRunner):
    """`query` plus `location().position()` returns real coordinates in the paged target.

    This is how `pan(relto:)` and element geometry are resolved for the PDF outputs.
    """
    typst.ok(
        PAGED
        + """
#context {
  let p = query(label("in-flow")).first().location().position()
  assert(p.x >= 20pt, message: "x is " + repr(p.x))
  assert(p.y >= 40pt, message: "y is " + repr(p.y))
}
"""
    )


def test_paged_positions_work_inside_math(typst: TypstRunner):
    """The same, for a tag site inside an equation, which animo has to support."""
    typst.ok(
        PAGED
        + """
#context {
  let p = query(label("in-math")).first().location().position()
  assert(p.x > 20pt, message: "x is " + repr(p.x))
  assert(p.y > 40pt, message: "y is " + repr(p.y))
}
"""
    )


def test_html_positions_are_all_zero(typst: TypstRunner):
    """In the HTML target, `here().position()` reports the origin of page one and nothing else."""
    typst.ok(
        """
#context {
  assert.eq(repr(here().position()), repr((page: 1, x: 0pt, y: 0pt)))
}
""",
        html=True,
    )


def test_html_positions_are_zero_inside_a_frame_too(typst: TypstRunner):
    """Even inside `html.frame`, where the content really is laid out on a paged frame."""
    typst.ok(
        """
#html.frame[
  #context {
    assert.eq(repr(here().position()), repr((page: 1, x: 0pt, y: 0pt)))
  }
  #box[x]#label("inner")
]
""",
        html=True,
    )


def test_query_does_see_inside_a_frame(typst: TypstRunner):
    """Introspection is not gone in HTML, only positions are.

    A tag inside a frame is still discoverable, and its position is still useless.
    """
    typst.ok(
        """
#html.frame[#box[x]#label("inner")]
#context {
  let found = query(label("inner"))
  assert.eq(found.len(), 1, message: "query did not see into the frame")
  assert.eq(repr(found.first().location().position()), repr((page: 1, x: 0pt, y: 0pt)))
}
""",
        html=True,
    )


def test_measure_works_in_the_html_target(typst: TypstRunner):
    """`measure` is the one piece of layout information the HTML target does give.

    Everything about regions rests on this.
    """
    typst.ok(
        """
#context {
  let m = measure(box[Hello])
  assert(m.width > 0pt, message: "width is " + repr(m.width))
  assert(m.height > 0pt, message: "height is " + repr(m.height))
}
""",
        html=True,
    )
