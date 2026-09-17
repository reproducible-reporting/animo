# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A counter reads the same everywhere a slide lays content out*.

A slide number is a counter and nothing else, which is only true because a counter read
gives the same answer inside an `html.frame` as outside one, and because `final()` works in
the HTML target at all. If either stopped holding, a slide number would need the same
machinery a subslide number needs.

Every assertion is inside the document, because a number leaves a frame as glyph references
rather than as text, so a wrong value is a failed compile rather than a string to match.
"""

import pytest
from harness import TypstRunner

PAGE = "#set page(width: 300pt, height: 200pt, margin: 10pt)\n"

# A counter stepped twice, and a check that reads it two ways.
COUNTED = """\
#let n = counter("probe")
#let check(where) = context {
  assert.eq(n.get().first(), 2, message: "get in " + where)
  assert.eq(n.final().first(), 2, message: "final in " + where)
}
#n.step()
#n.step()
"""


def test_a_counter_reads_the_same_in_and_out_of_a_frame(typst: TypstRunner):
    """A frame is a container and not a document, so a counter read inside one is not reset.

    The three sites are the three places a slide lays content out: its body, which the HTML
    target puts inside a frame, and each of the two outer layers, which are frames of their
    own beside it.
    """
    typst.ok(
        COUNTED + '#check("the document")\n\n#html.frame[#check("a frame")]\n\n'
        '#html.frame[#check("a second frame")]\n',
        html=True,
    )


@pytest.mark.parametrize("html", [False, True])
def test_the_total_is_available_before_the_counter_reaches_it(typst: TypstRunner, html):
    """`final()` resolves in both targets, which is what a count of the deck's slides needs.

    It is read here *at* the second step rather than after the document, which is the
    position a slide reads it from.
    """
    source = COUNTED + '#check("before the end")\n#n.step()\n#n.update(2)\n'
    typst.ok(source if html else PAGE + source, html=html)


def test_it_holds_in_the_paged_target(typst: TypstRunner):
    """The paged half of one number serving all three output types."""
    typst.ok(PAGE + COUNTED + '#check("a page")\n')


def test_a_counter_may_be_read_while_content_is_being_measured(typst: TypstRunner):
    """A footprint measurement is where a number in a stack is read from.

    The value is the enclosing context's, which is what a number constant over a slide
    wants and what a value varying per epoch may not be built on: *Providing a value down
    the tree* is that other half.
    """
    typst.ok(PAGE + COUNTED + '#context {\n  let _ = measure([#check("a measurement")])\n}\n')
