# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *`hide()` cannot be undone in the browser*.

Typst's `hide()` lays content out but paints nothing,
so the labelled group is there and empty.
No CSS can bring back ink that was never emitted,
which is why an initially hidden element has to be rendered normally in the HTML output
and hidden with `opacity: 0`, and why only the paged outputs may use `hide()`.
"""

from harness import TypstRunner
from svgtools import SVG, group, parse

DOCUMENT = """\
#set page(width: 200pt, height: 100pt, margin: 10pt)
#box(hide[Hello])#label("hidden")

#box[Hello]#label("shown")
"""


def glyphs(root, label: str) -> int:
    """How many glyph references a labelled group contains."""
    return len(group(root, label).findall(f".//{SVG}use"))


def test_a_hidden_group_is_present_and_empty(typst: TypstRunner):
    """The group exists, so it is addressable, and it holds nothing to reveal."""
    root = parse(typst.svg(DOCUMENT))
    assert glyphs(root, "shown") > 0, "the visible control emitted no glyphs either"
    assert glyphs(root, "hidden") == 0


def test_hidden_content_still_takes_its_space(typst: TypstRunner):
    """`hide` is the initial-state counterpart of the `hide` primitive, not of `remove`.

    The two boxes measure the same, so the space is reserved either way.
    """
    typst.ok(
        """
#context {
  assert.eq(
    repr(measure(box(hide[Hello]))),
    repr(measure(box[Hello])),
    message: "hidden content does not occupy the same space as visible content",
  )
}
"""
    )
