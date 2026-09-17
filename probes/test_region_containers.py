# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Regions: what a region learns from its container*.

A region at `width: auto` is as wide as `layout(size => ..)` says its container is,
and it measures its epochs at that width.
Where the answer is the width the author sees, the footprint is right;
where it is wider, the region silently reserves the wrong amount of space.
These probes pin down which containers are which, what an unbounded `measure` reports,
what `align` does to an inherited alignment, and that a counter numbers regions the same way
in every rendering and in both targets.

These probes build the mechanism by hand, with no animo in sight.
"""

import pytest
from harness import TypstRunner

PAGE = "#set page(width: 400pt, height: 600pt, margin: 20pt)\n"

# A stand-in for a region: a filling block that records the width it was handed.
PROBE = """\
#let probe = layout(size => {
  [#metadata(size.width)<width>]
  block(width: 100%, height: 10pt, fill: red)
})
"""


@pytest.mark.parametrize(
    ("container", "expected"),
    [
        ("#grid(columns: (1fr, 2fr), probe, [x])", "120pt"),
        ("#grid(columns: (100pt, 1fr), probe, [x])", "100pt"),
        ("#table(columns: (1fr, 1fr), probe, [x])", "170pt"),
        ("#columns(2, probe)", "172.8pt"),
        ("#place(dy: 300pt, box(width: 120pt, probe))", "120pt"),
        ("#block(inset: 10pt, probe)", "340pt"),
        ("#block(width: 50%, probe)", "180pt"),
    ],
)
def test_a_container_with_a_width_hands_that_width_to_layout(
    typst: TypstRunner, container, expected
):
    """Grid and table cells, columns, and a placed or inset box of a known width."""
    typst.ok(
        PAGE
        + PROBE
        + container
        + "\n#context {\n"
        + "  let found = query(<width>).map(it => it.value)\n"
        + "  assert.eq(found.len(), 1)\n"
        + f"  assert(calc.abs(found.first() - {expected}) < 0.001pt, message: repr(found))\n"
        + "}\n"
    )


@pytest.mark.parametrize(
    "container",
    [
        "#grid(columns: (auto, 1fr), probe, [x])",
        "#stack(dir: ltr, probe, [x])",
        "#box(probe) after",
        "#place(dy: 300pt, probe)",
        "$ x = #probe $",
    ],
)
def test_a_container_that_sizes_to_its_content_hands_over_the_whole_width(
    typst: TypstRunner, container
):
    """An auto grid column, a stack, an auto-sized box, a bare placement, and math.

    Each of them lays the block out at the width of the page body, so a region there takes
    all of it and pushes whatever sits beside it off the edge.
    Nothing at the region's end can tell this apart from a container that really is that wide.
    """
    typst.ok(
        PAGE
        + PROBE
        + container
        + "\n#context assert.eq(query(<width>).map(it => it.value), (360pt,))\n"
    )


def test_an_unbounded_measure_hands_layout_an_infinite_size(typst: TypstRunner):
    """Which is what a region has to survive, since a tag measures its body that way."""
    typst.fails(
        PAGE + "#context measure(layout(size => panic(repr(size))))\n",
        "(width: float.inf * 1pt, height: float.inf * 1pt)",
    )


def test_align_with_a_horizontal_component_overrides_an_inherited_alignment(typst: TypstRunner):
    """`top + left` left-aligns centred content, `top` alone leaves it centred."""
    typst.ok(
        PAGE
        + """\
#set align(center)
#let line(name) = [A short line #box[x]#label(name)]
#block(width: 100%, height: 30pt, line("plain"))
#block(width: 100%, height: 30pt, align(top, line("top")))
#block(width: 100%, height: 30pt, align(top + left, line("top-left")))
#context {
  let x(name) = query(label(name)).first().location().position().x
  assert.eq(x("top"), x("plain"))
  assert(x("top-left") < x("plain") - 100pt, message: repr((x("top-left"), x("plain"))))
}
"""
    )


COUNTER = """\
#let c = counter("probe-region")
#let region(body) = {
  c.step()
  context {
    let id = c.get().first()
    layout(size => {
      let _ = measure(body, width: size.width)
      [#metadata(id)<id>]
      body
    })
  }
}
#let rendering = {
  c.update(0)
  region[outer #region[inner a] #region[inner b]]
  region[second]
}
#block(rendering)
#block(rendering)
#context assert.eq(query(<id>).map(it => it.value), (1, 2, 3, 4, 1, 2, 3, 4))
"""


@pytest.mark.parametrize("html", [False, True], ids=["paged", "html"])
def test_a_counter_reset_per_rendering_numbers_regions_alike_in_each(typst: TypstRunner, html):
    """Document order, nested regions included, and a `measure` inside steps nothing."""
    source = PAGE + COUNTER if not html else COUNTER.replace("#block(", "#html.frame(")
    typst.ok(source, html=html)
