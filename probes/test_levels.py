# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Inline versus block, decided by measurement*.

A tag has to wrap its body, and the wrapper it may use depends on whether the body is
inline-level or block-level.
Typst answers that question for nobody: there is no predicate, and the element functions
only tell what an element is, not what a `context` block will turn into.
Measuring does answer it, by putting a zero-sized box on each side of the body
and seeing whether they are pushed onto lines of their own.

These probes pin the decision procedure itself, and the blind spot it has,
so that a failure here names the typst behaviour and not a `wrap: auto` bug.
"""

import pytest
from harness import TypstRunner

PRELUDE = """\
#set page(width: 30cm, height: 30cm)
#set text(size: 10pt)

// The decision procedure, written out as the implementation will use it.
#let nothing = box(width: 0pt, height: 0pt)
#let breaks(body, ..args) = (
  measure([#nothing#body#nothing], ..args).height - measure(body, ..args).height
)
"""

# The body, its name for the test id, and whether it is block-level.
# Everything a slide is likely to hold.
SAMPLES = (
    ("[word]", False),
    ("box[word]", False),
    ("box(width: 2cm, height: 2cm, fill: red)", False),
    ("box(baseline: 50%, width: 1cm, height: 1cm, fill: blue)", False),
    ("$x^2$", False),
    ("[`code`]", False),
    ("text(red)[word]", False),
    ("[*word*]", False),
    ("hide[word]", False),
    ("footnote[f]", False),
    ("metadata(3)", False),
    ("[]", False),
    ("[a stretch of words long enough to wrap when the space is tight indeed]", False),
    ("block[word]", True),
    ("[= Head]", True),
    ("list([one], [two])", True),
    ("table(columns: 2)[a][b]", True),
    ("grid(columns: 2)[a][b]", True),
    ("rect[r]", True),
    ("par[word]", True),
    ("$ x^2 $", True),
    ("figure(rect(), caption: [c])", True),
    ("columns(2)[a]", True),
    ("stack(dir: ltr)[a][b]", True),
    ("place(dx: 1cm)[p]", True),
    ("line(length: 1cm)", True),
)


@pytest.mark.parametrize(("body", "is_block"), SAMPLES, ids=lambda v: str(v)[:40])
def test_the_break_test_says_what_the_body_is(typst: TypstRunner, body, is_block):
    """One case per body, so that a failure names the construct it disagrees about."""
    comparison = ">" if is_block else "=="
    typst.ok(
        PRELUDE
        + f"""
#context {{
  let d = breaks({body})
  assert(d {comparison} 0pt, message: "{body.replace('"', "'")}: " + repr(d))
}}
"""
    )


def test_the_separation_needs_no_tolerance(typst: TypstRunner):
    """Inline is exactly zero and block is at least twelve points, over the whole table.

    A decision procedure with a threshold in it would be a guess;
    this one has a gap of twelve points and a difference that is bit-for-bit zero.
    """
    inline = ", ".join(body for body, is_block in SAMPLES if not is_block)
    block = ", ".join(body for body, is_block in SAMPLES if is_block)
    typst.ok(
        PRELUDE
        + f"""
#context {{
  for body in ({inline},) {{
    assert.eq(breaks(body), 0pt, message: "inline body moved by " + repr(breaks(body)))
  }}
  for body in ({block},) {{
    assert(breaks(body) >= 12pt, message: "block body moved by only " + repr(breaks(body)))
  }}
}}
"""
    )


def test_it_sees_through_a_context_block(typst: TypstRunner):
    """This is what inspection cannot do, and it is the reason the decision is measured.

    A `context` element has no fields at all, so its contents are invisible until laid out,
    and `measure` lays them out.
    """
    typst.ok(
        PRELUDE
        + """
#context {
  let opaque = context [word]
  assert.eq(opaque.fields(), (:), message: "a context block became inspectable")
  assert.eq(breaks(context [word]), 0pt)
  assert(breaks(context block[word]) > 0pt)
}
"""
    )


def test_it_needs_no_available_width(typst: TypstRunner):
    """`layout` is block-level, so an inline tag site cannot ask for its container's width.

    An unbounded `measure` resolves a `100%` width to zero rather than to infinity,
    and every verdict comes out the same as with a width given.
    """
    typst.ok(
        PRELUDE
        + """
#context {
  let bodies = (
    [a stretch of words long enough to wrap when the space is tight indeed],
    block(width: 100%)[w],
    columns(2)[a],
    grid(columns: (1fr, 1fr))[a][b],
    figure(rect(), caption: [c]),
  )
  for body in bodies {
    assert.eq(
      breaks(body) > 0pt,
      breaks(body, width: 6cm) > 0pt,
      message: "the verdict depends on the width it was measured at",
    )
  }
}
"""
    )


def test_several_paragraphs_are_the_blind_spot(typst: TypstRunner):
    """The one case the measurement gets wrong, and the scan that covers it.

    The neighbours merge into the first and the last paragraph instead of being pushed off,
    so a body that is itself several paragraphs measures as inline.
    A `parbreak` among the body's own children says what the measurement cannot.
    """
    typst.ok(
        PRELUDE
        + """
#let two = [one

two]
#context {
  assert.eq(breaks(two), 0pt, message: "the blind spot closed on its own")
  assert.eq(repr(two.func()), "sequence")
  assert(
    two.children.any(child => child.func() == parbreak),
    message: "the scan that covers the blind spot found nothing",
  )
}
"""
    )


def test_what_inspection_reports(typst: TypstRunner):
    """The element identities a reader expects to reach for first, and what they are.

    Recorded because they are surprising, not because animo depends on them.
    """
    typst.ok(
        PRELUDE
        + """
#context {
  // A markup list is a sequence of items, and the three kinds of item share a name.
  let items = [- one
- two]
  assert.eq(repr(items.func()), "sequence")
  assert.eq(items.children.map(child => repr(child.func())), ("item", "space", "item"))
  assert.eq(repr(list.item), "item")
  assert.eq(repr(enum.item), "item")
  assert.eq(repr(terms.item), "item")

  // A set rule and a text call both arrive as `styled`, with the real element one level down.
  let styled-call = text(red)[word]
  let styled-set = [#set text(red)
word]
  assert.eq(repr(styled-call.func()), "styled")
  assert.eq(repr(styled-set.func()), "styled")
  assert.eq(repr(styled-call.child.func()), "text")

  // Elements that are block-level without looking it.
  let svg = bytes("<svg xmlns='http://www.w3.org/2000/svg' width='8' height='8'></svg>")
  for body in (image(svg, format: "svg", width: 1cm),
               rect(), line(length: 1cm), stack[a], columns(2)[a],
               move(dx: 1pt)[x], scale(50%)[x], layout(size => [x])) {
    assert(breaks(body) > 0pt, message: repr(body.func()) + " turned out to be inline")
  }
}
"""
    )
