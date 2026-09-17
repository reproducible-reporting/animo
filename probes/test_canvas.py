# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for the automatic canvas sizing finding.

*Automatic canvas sizing: `#place` is invisible to `auto`, but visible to a show rule*.

An animo slide is a two-dimensional canvas built with `#place`,
so how typst sees a placement decides how the canvas can be sized at all.
Three routes are closed and one is open, and each of the four is a probe.

Two probes at the end are about how far the open route can be trusted,
because the union it computes is not exact even where it looks exact:
an unbounded `measure` of a ratio-sized body reports nothing,
and no cheap mechanism separates a top-level placement from a nested one.
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


# How far the open route can be trusted.


RATIO_SIZED = """\
#set page(width: 400pt, height: 300pt, margin: 0pt)
#context {
  assert.eq(
    repr(measure(rect(width: 100%, height: 100%))),
    repr((width: 0pt, height: 0pt)),
    message: "an unbounded measure resolved a ratio: "
      + repr(measure(rect(width: 100%, height: 100%))),
  )
  assert(
    measure(rect(width: 4cm, height: 2cm)).width > 0pt,
    message: "the control measured nothing either, so the claim above says nothing",
  )
}
"""


def test_an_unbounded_measure_resolves_a_ratio_size_to_zero(typst: TypstRunner):
    """Why the union is not exact even for a top-level placement.

    A show rule over a placement can measure its body, but only without a container to
    resolve a ratio against, so a full-bleed `rect(width: 100%, height: 100%)` reports
    nothing at all and contributes nothing to the union. The second assertion is the
    control: an absolutely sized body does measure, so the first is about the ratio.
    """
    typst.ok(RATIO_SIZED)


NESTING_DEPTH = """\
#set page(width: 400pt, height: 300pt, margin: 0pt)
#let depth = state("depth", 0)
#let step(it) = { depth.update(d => d + 1); it; depth.update(d => d - 1) }

// Each placement is identified by its own offset, so that what the rule reports can be
// matched to where the placement was written without depending on document order.
#let watch(body) = {
  show box: step
  show block: step
  show grid: step
  show place: it => {
    context [#metadata((at: it.dx.length.pt(), depth: depth.get()))<seen>]
    it
  }
  body
}

#watch[
  #place(dx: 10pt)[top level]
  #box(width: 4cm, height: 2cm)[#place(dx: 20pt)[in a box]]
  #grid(columns: (4cm,), [#place(dx: 30pt)[in a grid cell]])
  #place(dx: 40pt)[#place(dx: 50pt)[in a placement]]
  #figure[#place(dx: 60pt)[in a figure]]
]

#context {
  let seen = (:)
  for it in query(<seen>) { seen.insert(str(calc.round(it.value.at)), it.value.depth) }
  assert.eq(seen.len(), 6, message: "the rule saw " + repr(seen))
  let depth-of(at) = seen.at(str(at))
  // A top-level placement is at depth zero, which is what the others are read against.
  assert.eq(depth-of(10), 0, message: "a top-level placement is not at depth zero")
  // The mechanism does see every container it was given a rule for, which is what makes
  // the one case below a blind spot rather than a mechanism that reports nothing at all.
  for (at, what) in ((20, "a box"), (30, "a grid cell"), (60, "a figure")) {
    assert(
      depth-of(at) > 0,
      message: "the mechanism does not see " + what + ": " + repr(seen),
    )
  }
  // And it is blind to the one shape that has no container in it.
  assert.eq(
    depth-of(50),
    0,
    message: "a placement inside a placement became distinguishable: " + repr(seen),
  )
}
"""


def test_a_nesting_depth_does_not_separate_a_top_level_placement_from_a_nested_one(
    typst: TypstRunner,
):
    """Why the union stays approximate rather than dropping what it cannot attribute.

    A depth kept in a state and stepped by show rules on the containers is the one
    mechanism left after `layout(size => ..)` is ruled out for breaking the paragraph the
    placement sits in. It does see a box, a grid cell and a figure, and it reports
    **zero** for a placement inside another placement, which has no container in it to
    step the depth. That is the shape both decks beside this repository are written in,
    and it is the shape a slide takes when a group of placements is positioned as a whole.
    The other half is not probed here because a probe imports no animo: a tag site and a
    region are a box and a block, so a mechanism that counts containers would read every
    placement inside a tag as nested. So "count only the placements that can be attributed
    to the slide body" has no mechanism behind it.
    """
    typst.ok(NESTING_DEPTH)
