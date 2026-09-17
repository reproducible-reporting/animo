# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Regions: fixed footprints across epochs*.

The mechanism is `layout(size => ..)` plus `measure` once per epoch,
with the footprint taken as the per-axis maximum.
Two things have to hold for it to be worth anything:
the footprint keeps everything after the region in place,
and a footprint measured in the HTML target is the footprint the paged target produces.

These probes build the mechanism by hand, with no animo in sight,
so that a failure here names the typst behaviour and not a region bug.
"""

import re

from harness import TypstRunner
from htmldoc import stacked
from measuring import rects

FOOTPRINT = """\
// Two content states that really do differ, so that the probe is not vacuous.
#let states = (
  [A short claim.],
  [A claim long enough to wrap onto a second line, which is what makes the footprint grow.],
)

// The footprint rule of the design: the per-axis maximum over the epochs.
#let footprint(states, width) = {
  let w = 0pt
  let h = 0pt
  for state in states {
    let m = measure(state, width: width)
    w = calc.max(w, m.width)
    h = calc.max(h, m.height)
  }
  (width: w, height: h)
}

#let region(states, index) = layout(size => {
  let f = footprint(states, size.width)
  box(width: f.width, height: f.height, align(top + left, states.at(index)))
})
"""


def test_the_two_states_of_the_probe_really_differ(typst: TypstRunner):
    """Without this, every other assertion in this module is vacuously true."""
    typst.ok(
        FOOTPRINT
        + """
#context {
  assert.ne(
    measure(states.at(0), width: 280pt).height,
    measure(states.at(1), width: 280pt).height,
    message: "the two states measure the same, so nothing below proves anything",
  )
}
"""
    )


def test_a_fixed_footprint_keeps_what_follows_in_place(typst: TypstRunner):
    """Content after the region sits at the same position in every epoch.

    Both epochs are laid out in one document, one per page,
    so the comparison needs no second compilation and no stored numbers.
    """
    typst.ok(
        "#set page(width: 300pt, height: 200pt, margin: 10pt)\n"
        + FOOTPRINT
        + """
#for index in range(states.len()) {
  region(states, index)
  [#box[after]#label("after")]
  pagebreak(weak: true)
}

#context {
  let positions = query(label("after")).map(it => it.location().position())
  assert.eq(positions.len(), states.len(), message: "expected one label per epoch")
  let first = positions.first()
  for position in positions {
    assert.eq(position.y, first.y, message: "y moved between epochs: " + repr(positions))
    assert.eq(position.x, first.x, message: "x moved between epochs: " + repr(positions))
  }
}
"""
    )


def test_the_footprint_is_the_maximum_and_every_epoch_fits_in_it(typst: TypstRunner):
    """The per-axis maximum is an upper bound for every epoch, which is what bounds the reflow."""
    typst.ok(
        FOOTPRINT
        + """
#context {
  let width = 280pt
  let f = footprint(states, width)
  for state in states {
    let m = measure(state, width: width)
    assert(m.width <= f.width, message: "state wider than the footprint: " + repr(m))
    assert(m.height <= f.height, message: "state taller than the footprint: " + repr(m))
  }
  assert(
    states.any(state => measure(state, width: width).height == f.height),
    message: "the footprint is not attained by any epoch, so it is not a maximum",
  )
}
"""
    )


MEASURE_ACROSS_TARGETS = """\
// `measure` internally sets `Target::Paged`, so this number may not depend on the target.
#let probe = [A claim long enough to wrap onto a second line, which is what makes it grow.]

#context {
  let m = measure(probe, width: 200pt)
  let seen = repr((width: m.width, height: m.height))
  let expected = sys.inputs.at("expected", default: none)
  if expected == none [MEASURED #seen] else {
    assert.eq(seen, expected, message: "measure disagrees between the two targets")
  }
}
"""


def test_a_footprint_measured_in_html_is_the_footprint_paged_produces(typst: TypstRunner):
    """One footprint rule serves both targets, which is what gives one source three output types.

    The number is taken out of the HTML compilation and handed to the paged one through
    `--input`, so nothing is hardcoded and a change in font metrics cannot make this pass
    for the wrong reason.
    """
    source = typst.source(MEASURE_ACROSS_TARGETS)
    html = typst.html(source).read_text()
    match = re.search(r"MEASURED (\(.*?\))", html)
    assert match is not None, f"the HTML compilation printed no measurement:\n{html}"
    typst.ok(source, sysinp={"expected": match[1]})


EPOCH_FRAMES = (
    """
  #box(width: 240pt)[
    #box(width: 240pt, height: 24pt)[A short claim.]
    #box[after]#label("after")
  ]
""",
    """
  #box(width: 240pt)[
    #box(width: 240pt, height: 24pt)[A different claim, of a different length.]
    #box[after]#label("after")
  ]
""",
)


def test_a_label_after_the_region_lands_identically_in_both_epoch_frames(
    typst: TypstRunner, open_page, page
):
    """The browser half of the fixed-footprint invariant.

    Both epoch frames are stacked in one grid cell, so their coordinates are comparable,
    and a label after the region has to report the same rectangle and the same
    typst transform in both. This is the assertion the region machinery is built on.
    """
    open_page(typst.html(stacked(list(EPOCH_FRAMES))))
    found = rects(page, '[data-typst-label="after"]')
    assert len(found) == 2, "expected the label once per epoch frame"
    assert found[0].approx(found[1]), f"the label moved between epochs: {found}"
    transforms = page.evaluate(
        """() => Array.from(
            document.querySelectorAll('[data-typst-label="after"]'),
            node => node.getAttribute("transform"),
        )"""
    )
    assert transforms[0] == transforms[1], f"typst placed the label differently: {transforms}"
