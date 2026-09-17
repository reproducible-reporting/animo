# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Element identity in the output: `data-typst-label`*.

The keystone of the whole design.
Labelled content appears in SVG output as `<g data-typst-label="name">`,
and only for labelled `box` and `block` elements.
If any of this stops holding, animo has no handle on anything.
"""

import re

import pytest
from harness import CETZ, FLETCHER, TypstRunner, require

PAGE = "#set page(width: 300pt, height: 200pt, margin: 10pt)\n"


def labels(markup: str) -> list[str]:
    """Every `data-typst-label` value in an SVG or HTML document, in document order."""
    return re.findall(r'data-typst-label="([^"]*)"', markup)


def test_a_labelled_box_and_block_become_groups(typst: TypstRunner):
    """A labelled `box` and a labelled `block` each emit a group carrying the name."""
    markup = typst.svg(PAGE + '#box[boxed]#label("as-box")\n\n#block[blocked]#label("as-block")\n')
    assert labels(markup) == ["as-box", "as-block"]


def test_a_label_on_anything_else_emits_nothing(typst: TypstRunner):
    """Only `box` and `block` are addressable.

    In 0.15.1 the attribute has exactly one emission site, `crates/typst-svg/src/lib.rs`,
    and it fires for `group.label` alone.
    That source-tree fact is not observable, but its consequence is:
    a label on a `rect` or on a text span produces no group at all.
    This is what decides that `tag` has to wrap its body.
    """
    markup = typst.svg(
        PAGE
        + '#rect(width: 20pt, height: 10pt)#label("as-rect")\n\n'
        + '#text[spanned]#label("as-text")\n'
    )
    assert labels(markup) == []


def test_it_works_inside_an_html_frame(typst: TypstRunner):
    """The attribute survives `html.frame`, which is what makes browser animation possible."""
    path = typst.html('#html.frame[#box[framed]#label("inframe")]\n')
    assert labels(path.read_text()) == ["inframe"]


def test_duplicate_labels_each_get_their_own_group(typst: TypstRunner):
    """Typst permits duplicate labels, and every occurrence becomes a group of its own.

    This is what makes "one tag, several elements" work,
    and what lets one CSS rule reach the same tag in every epoch frame of a slide.
    """
    markup = typst.svg(PAGE + '#box[twice]#label("dup") and #box[twice]#label("dup")\n')
    assert labels(markup) == ["dup", "dup"]


def test_it_works_inside_math_when_the_label_is_attached_in_markup(typst: TypstRunner):
    """Inside math, the label has to be attached within a markup block.

    This is narrower than *Findings* states.
    In markup, `#box(body)#label(name)` attaches; inside math it does not,
    and the label renders as literal math content, exactly like the `<name>` form.
    The form that does work is a markup block around the pair,
    which is what a `tag` function returns anyway.
    """
    markup = typst.svg(PAGE + '$ a + #[#box[b]#label("in-math")] = c $\n')
    assert labels(markup) == ["in-math"]


def test_a_bare_label_after_a_box_inside_math_does_not_attach(typst: TypstRunner):
    """The negative half of the previous probe, kept separate because it is a trap.

    Nothing fails: the document compiles, no group is emitted,
    and the label ends up as visible text in the equation.
    """
    markup = typst.svg(PAGE + '$ a + #box(box[b])#label("lost") = c $\n')
    assert labels(markup) == []


def test_it_works_inside_a_cetz_canvas(typst: TypstRunner):
    """A cetz `content()` element is ordinary content, so a tag inside it is addressable."""
    package = require(typst, CETZ)
    markup = typst.svg(
        f'#import "{package}"\n'
        + PAGE
        + "#cetz.canvas({\n"
        + "  import cetz.draw: *\n"
        + "  circle((0, 0), radius: 1)\n"
        + '  content((0, 0), [#box[in canvas]#label("in-cetz")])\n'
        + "})\n"
    )
    assert labels(markup) == ["in-cetz"]


def test_it_works_inside_a_fletcher_node(typst: TypstRunner):
    """A fletcher node is ordinary content too, and carries its label into the output."""
    package = require(typst, FLETCHER)
    markup = typst.svg(
        f'#import "{package}": diagram, edge, node\n'
        + PAGE
        + "#diagram(\n"
        + '  node((0, 0), [#box[A]#label("in-fletcher")]),\n'
        + "  node((1, 0), [B]),\n"
        + '  edge("->"),\n'
        + ")\n"
    )
    assert labels(markup) == ["in-fletcher"]


@pytest.mark.parametrize("name", ["with-dash", "with.dot", "with_underscore", "digits123"])
def test_the_name_reaches_the_attribute_unchanged(typst: TypstRunner, name):
    """Whatever a tag is called is what a CSS selector has to match on."""
    markup = typst.svg(PAGE + f'#box[x]#label("{name}")\n')
    assert labels(markup) == [name]
