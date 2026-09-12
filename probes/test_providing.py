# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Providing a value down the tree: a show rule reaches into `measure`*.

A slide has to hand its plan to the tags inside its body,
and a region has to hand a different epoch to the same tags once per epoch while it measures.
A state cannot do the second job, because a state resolves at a document position
and `measure` has no position of its own.
A marker element plus a show rule can, and that is what decides the mechanism.

These probes build the mechanism by hand, with no animo in sight.
"""

from harness import PagedRunner, TypstRunner, assert_identical
from svgtools import parse

PRELUDE = """\
#set page(width: 10cm, height: 10cm)

// The mechanism: the child emits a marker carrying a function,
// an ancestor installs the rule that calls it with the value.
#let ask(f) = context [#metadata(f)<probe-ask>]
#let provide(value, body) = {
  show <probe-ask>: it => (it.value)(value)
  body
}
#let shown = ask(v => [E=#v])

// The alternative that does not work, for comparison.
#let epoch = state("probe-epoch", "none")
#let from-state = context [E=#epoch.get()]
"""


def test_a_state_cannot_vary_inside_measure(typst: TypstRunner):
    """Two measurements in one context block see the same state, whatever happens between them.

    `state.get()` inside `measure` resolves at the location of the enclosing context block,
    so there is no way to measure one epoch and then another.
    """
    typst.ok(
        PRELUDE
        + """
#epoch.update("AAAA")
#context {
  let first = measure(from-state).width
  epoch.update("B")
  let second = measure(from-state).width
  assert.eq(first, second, message: "a state became variable inside measure after all")
}
"""
    )


def test_a_provided_value_does_vary_inside_measure(typst: TypstRunner):
    """The same two measurements, through a provider, do differ.

    This is the whole reason the plan is provided rather than published.
    """
    typst.ok(
        PRELUDE
        + """
#context {
  assert.ne(
    measure(provide("A", shown)).width,
    measure(provide("BBBB", shown)).width,
    message: "the provided value did not reach the measured content",
  )
}
"""
    )


def test_providers_nest_and_the_innermost_wins(typst: TypstRunner):
    """A region provides an epoch inside a slide that has already provided its plan."""
    typst.ok(
        PRELUDE
        + """
#context {
  assert.eq(
    measure(provide("A", [#provide("BBBB", shown)])).width,
    measure(provide("BBBB", shown)).width,
    message: "the outer provider won",
  )
}
"""
    )


def test_a_marker_produced_inside_a_context_block_is_still_replaced(typst: TypstRunner):
    """The marker is emitted from a `context`, because a tag has measuring of its own to do."""
    typst.ok(
        PRELUDE
        + """
#context {
  assert.ne(measure(provide("A", context shown)).width, 0pt)
  assert.eq(
    measure(provide("A", context shown)).width,
    measure(provide("A", shown)).width,
  )
}
"""
    )


def test_the_markers_own_label_does_not_reach_the_output(typst: TypstRunner):
    """A tag built this way emits one `data-typst-label`, its own.

    The marker is labelled too, and a label on the content a show rule produces would
    be indistinguishable from the tag's in the browser.
    """
    tagged = (
        PRELUDE
        + """
#let tagged(name, body) = ask(v => [#box(box[#body#v])#label(name)])
#provide("V", [outer #tagged("a")[A #tagged("b")[B] tail]])
"""
    )
    labels = [
        element.get("data-typst-label")
        for element in parse(typst.svg(tagged)).iter()
        if element.get("data-typst-label") is not None
    ]
    assert sorted(labels) == ["a", "b"], labels


def test_query_cannot_tell_a_replaced_marker_from_a_leftover(typst: TypstRunner):
    """So a tag outside any slide has to be diagnosed at the tag site.

    Sweeping the document at the end for markers nobody replaced would report every tag.
    """
    typst.ok(
        PRELUDE
        + """
#provide("V", [replaced: #shown])
#shown
#context {
  assert.eq(
    query(<probe-ask>).len(),
    2,
    message: "a leftover marker became distinguishable, which would be good news",
  )
}
"""
    )


def test_a_replaced_marker_costs_no_layout(paged: PagedRunner):
    """The channel is invisible to the layout, which a tag that emits no wrapper needs.

    A tag may hand its body back untouched, and "untouched" has to mean untouched:
    the `context` block, the `metadata` element and the show-rule replacement that carry
    the value may contribute no spacing of their own.
    Measured on a heading between two paragraphs, which is the case that betrays a
    wrapper, since a wrapper trims a heading's own block spacing at its edge.
    """
    flow = (
        "= A Heading\n\nBefore.\n\nBODY\n\n"
        "After the body there is a paragraph of text that says something."
    )
    document = PRELUDE + "#let pass-through(body) = ask(v => body)\n#provide(\"V\", [\n" + flow
    plain = document.replace("BODY", "= Another Heading") + "\n])\n"
    routed = document.replace("BODY", "#pass-through[= Another Heading]") + "\n])\n"
    assert_identical(
        paged.png(plain, ppi=144)[0],
        paged.png(routed, ppi=144)[0],
        what="a body routed through the provider",
    )
