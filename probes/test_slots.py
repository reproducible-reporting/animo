# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Cross-frame geometry is readable, so morphing is possible*.

Two things are recorded under that heading.
The geometry of a label is readable in both epoch frames, which is what makes a FLIP morph
implementable without help from typst.
And a tag site needs *two* nested groups, because CSS gives each element only one `translate`
and one `scale`, so the continuous primitives and anything belonging to an epoch boundary
need a slot each.
"""

from harness import TypstRunner
from htmldoc import stacked
from measuring import rects
from svgtools import SVG, group, parse

PAGE = "#set page(width: 200pt, height: 60pt, margin: 10pt)\n"


def test_a_nested_box_gives_a_second_untransformed_slot(typst: TypstRunner):
    """`#box(box[..])#label(..)` emits a labelled outer group and a bare inner one.

    The inner group carries no transform of its own,
    which is what makes `[data-typst-label="x"] > g` a slot animo may write to.
    """
    element = group(parse(typst.svg(PAGE + '#box(box[Hello world])#label("outer")\n')), "outer")
    assert "transform" in element.attrib, "typst's own placement transform is gone"
    children = list(element)
    assert len(children) == 1
    assert children[0].tag == f"{SVG}g"
    assert "transform" not in children[0].attrib, "the inner slot is not free after all"


def test_a_single_box_has_no_slot_to_rely_on(typst: TypstRunner):
    """The reason `tag` has to wrap twice rather than once.

    With a single box the child of the labelled group carries a content-dependent transform,
    so writing CSS to it would clobber whatever typst put there.
    """
    element = group(parse(typst.svg(PAGE + '#box[Hello world]#label("single")\n')), "single")
    children = list(element)
    assert len(children) == 1
    assert "transform" in children[0].attrib


REFLOW = (
    '#box(width: 240pt)[Short prefix #box(box[EQ])#label("eq") and a tail.]',
    "#box(width: 240pt)[A considerably longer prefix that pushes it along "
    '#box(box[EQ])#label("eq") and a tail.]',
)


def test_a_label_reports_its_geometry_in_both_epoch_frames(typst: TypstRunner, open_page, page):
    """Both frames are in the DOM and laid out, so both geometries are readable.

    The label moves because the content before it reflows,
    and it keeps its size, which is what a FLIP morph would pair on.
    """
    open_page(typst.html(stacked(list(REFLOW))))
    found = rects(page, '[data-typst-label="eq"]')
    assert len(found) == 2, "expected the tag once per epoch frame"
    first, second = found
    assert first.x != second.x, "the reflow did not move the label at all"
    assert abs(first.width - second.width) < 0.5
    assert abs(first.height - second.height) < 0.5
