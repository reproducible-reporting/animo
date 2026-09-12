# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Recording placements: what a `show place:` rule may and may not do*.

The finding that `show place:` sees every placement is probed in `test_canvas.py`.
What is probed here is the step from seeing a placement to having its numbers as data,
which is what the automatic canvas actually needs.
A show rule returns content and not a value, so the numbers travel as `metadata` and come
back through `query`, and the rule may not disturb the layout it is watching.

Both halves are load-bearing: without the first there is no canvas at all,
and without the second every slide with a placement inside a paragraph lays out wrongly.
"""

import re

from harness import TypstRunner

BODY = """\
#let body = [
  Lorem ipsum dolor sit amet, consectetur #place(dx: 3cm, dy: 1cm)[P] adipiscing elit,
  sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
  #place(top + right)[Q]
  Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
]
"""


def perturbation(inside: str) -> str:
    """A document that compares the body with and without a recording rule around it."""
    return (
        BODY
        + """
#let recorded = {
  show place: it => {
    RECORD
    it
  }
  body
}

#context {
  assert.eq(
    repr(measure(body, width: 300pt)),
    repr(measure(recorded, width: 300pt)),
    message: "the recording changed the layout: "
      + repr(measure(body, width: 300pt)) + " became " + repr(measure(recorded, width: 300pt)),
  )
}
""".replace("RECORD", inside)
    )


def test_a_context_block_holding_metadata_does_not_disturb_the_layout(typst: TypstRunner):
    """This is what makes the recording safe to leave in the real body of a slide.

    `metadata` draws nothing and takes no space, and a `context` block around it is
    inline, so the paragraph the placement sits in breaks where it would have anyway.
    """
    typst.ok(perturbation('context [#metadata((size: measure(it.body)))#label("animo-place")]'))


def test_a_layout_block_inside_the_rule_does_disturb_the_layout(typst: TypstRunner):
    """`layout(size => ..)` would reveal the placement's own container, and cannot be used.

    It is the one way to tell a top-level placement from one nested in a box, which is
    the known limit of the automatic canvas. It is block-level, so it breaks the
    paragraph the placement sits in: measured on typst 0.15.1, the same body comes out
    76.89pt tall without the rule and 103.29pt with it.
    Recorded as a probe rather than as a comment, because it looks like the obvious fix
    and is not, and the next reader will reach for it again.
    """
    typst.fails(
        perturbation('layout(size => context [#metadata((c: size))#label("animo-place")])'),
        "the recording changed the layout",
    )


QUERIED = """\
#context {
  let seen = query(<animo-place>).map(it => it.value)
  assert.eq(seen.len(), 2, message: "recorded " + str(seen.len()) + " placements")
  assert.eq(repr(seen.at(0).dx), "0% + 85.04pt")
  assert.eq(repr(seen.at(1).alignment), "right + top")
}
"""


def test_the_recorded_placements_come_back_through_query(typst: TypstRunner):
    """A show rule cannot return a value, so the numbers travel as introspection."""
    source = (
        BODY
        + """
#let recorded = {
  show place: it => {
    context [#metadata((dx: it.dx, alignment: it.alignment))#label("animo-place")]
    it
  }
  body
}

#block(width: 300pt, recorded)
"""
        + QUERIED
    )
    typst.ok(source)


def test_the_recording_is_queryable_from_inside_an_html_frame(typst: TypstRunner):
    """The half that matters for the HTML target, where nothing else about layout works.

    `query` sees inside a frame even though positions do not exist there,
    which is what lets one canvas rule serve both targets.
    """
    source = (
        BODY
        + """
#let recorded = {
  show place: it => {
    context [#metadata((dx: it.dx, alignment: it.alignment))#label("animo-place")]
    it
  }
  body
}

#html.frame(block(width: 300pt, height: 200pt, recorded))
"""
        + QUERIED
    )
    typst.ok(source, html=True)


def test_a_block_sized_from_its_own_query_converges(typst: TypstRunner):
    """The canvas depends on the layout of the very block it sizes, and typst resolves it.

    The first pass records nothing and the block comes out at its floor;
    the introspection loop then runs the document again with the placements in reach.
    It terminates because the body is laid out at a width that does not depend on the
    answer, so the second pass sees exactly what the first one recorded.
    The claim is checked on the emitted frame rather than with an assertion inside the
    document, because an assertion would fail on the first pass and stop the loop.
    """
    path = typst.html(
        """
#let recorded = {
  show place: it => {
    context [#metadata((dx: it.dx, w: measure(it.body).width))#label("animo-place")]
    it
  }
  [#place(dx: 400pt)[far] in flow]
}

#context {
  let seen = query(<animo-place>).map(it => it.value)
  let width = calc.max(200pt, ..seen.map(it => it.dx.length + it.w))
  html.frame(block(width: width, height: 100pt, recorded))
}
""",
        name="converge.html",
    )
    found = re.search(r'viewBox="0 0 ([0-9.]+) ', path.read_text())
    assert found is not None, "no frame in the output"
    assert float(found[1]) > 400.0, f"the block did not grow to its content: {found[1]}"


def test_a_frame_is_sized_in_em_against_the_document_text_size(typst: TypstRunner):
    """Why animo's stylesheet overrides the frame's own size with `!important`.

    `html.frame` writes `width` and `height` on the `<svg>` as an inline style in `em`,
    dividing the frame's size in points by the text size in effect.
    An inline style outranks a stylesheet rule, so a deck that sizes its frames from CSS
    silently renders them at the ratio between the page's font size and typst's text size.
    Measured on typst 0.15.1: a 200pt block is `18.181818182em` at the default 11pt text
    and `9.090909091em` at 22pt.
    """
    for size, expected in (("11pt", "18.181818182em"), ("22pt", "9.090909091em")):
        path = typst.html(
            f"#set text(size: {size})\n#html.frame(block(width: 200pt, height: 50pt))\n",
            name=f"frame{size}.html",
        )
        assert f"width: {expected}" in path.read_text()
