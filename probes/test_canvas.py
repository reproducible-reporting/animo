# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for the automatic canvas sizing finding.

*Automatic canvas sizing: `#place` is invisible to `auto`, but visible to a show rule*.

An animo slide is a two-dimensional canvas built with `#place`,
so how typst sees a placement decides how the canvas can be sized at all.
Three routes are closed and one is open, and each of the four is a probe.
"""

import re

from harness import PagedRunner, TypstRunner, assert_identical

AUTO_PAGE = "#set page(width: auto, height: auto, margin: 0pt)\n"
PLACED = "#place(dx: 8cm, dy: 4cm)[OUT] in-flow\n"


def test_a_placement_does_not_enlarge_an_automatically_sized_page(paged: PagedRunner):
    """Typst's own `auto` machinery cannot size an animo canvas.

    The placement lands 8 cm to the right of a page that is 32 pt wide,
    and the page does not grow by a single pixel.
    """
    plain = paged.png(AUTO_PAGE + "in-flow\n")
    placed = paged.png(AUTO_PAGE + PLACED)
    assert len(plain) == len(placed) == 1
    assert_identical(plain[0], placed[0], what="the page with and without the placement")


def test_measure_does_not_see_a_placement_either(typst: TypstRunner):
    """The same blindness through `measure`, which is the API a region would use."""
    typst.ok(
        """
#context {
  let plain = block[in-flow]
  let placed = block[#place(dx: 8cm, dy: 4cm)[OUT] in-flow]
  assert.eq(
    repr(measure(plain)),
    repr(measure(placed)),
    message: "the placement changed the measurement",
  )
}
"""
    )


def test_a_placement_cannot_be_queried(typst: TypstRunner):
    """The placements cannot be discovered after the fact either."""
    typst.fails("#context { query(selector(place)) }\n", "place is not locatable")


SHOW_PLACE = """\
#set page(width: 400pt, height: 300pt, margin: 10pt)
#show place: it => {
  [SEEN dx=#repr(it.dx) dy=#repr(it.dy) align=#repr(it.alignment) size=#repr(measure(it.body)) ]
  it
}
#place(dx: 5cm, dy: 3cm)[OUT]
#place(bottom + right, dx: 50%)[BR]
#box(width: 4cm, height: 2cm)[#place(dx: 1cm)[IN]]
"""


def placements(typst: TypstRunner) -> list[str]:
    """What a `show place:` rule reports, one string per placement, in document order."""
    html = typst.html(SHOW_PLACE).read_text()
    return re.findall(r"SEEN ([^<]*)", html)


def test_a_show_rule_fires_for_every_placement_and_exposes_its_offsets(typst: TypstRunner):
    """The one route that is open, and the one the automatic canvas uses.

    It needs neither position introspection nor the paged target,
    so the canvas comes out the same in HTML and on paper,
    which is the invariant the whole design rests on.
    """
    seen = placements(typst)
    assert len(seen) == 3
    assert "dx=0% + 141.73pt" in seen[0]
    assert "dy=0% + 85.04pt" in seen[0]
    assert "align=start" in seen[0]
    assert "align=right + bottom" in seen[1]


def test_a_ratio_offset_stays_unresolved(typst: TypstRunner):
    """Ratios have to be resolved against the container, inside `layout(size => ..)`."""
    seen = placements(typst)
    assert "dx=50% + 0pt" in seen[1]


def test_a_nested_placement_is_reported_like_a_top_level_one(typst: TypstRunner):
    """The known limit of the rule, and the reason `canvas:` exists as an override.

    The third placement sits inside a 4 cm box and reports `1cm` relative to that box,
    exactly as a top-level placement 1 cm from the canvas origin would.
    The rule cannot tell the two apart.
    """
    seen = placements(typst)
    assert "dx=0% + 28.35pt" in seen[2]
    assert "align=start" in seen[2]
