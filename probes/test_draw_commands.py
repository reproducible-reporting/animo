# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A cetz draw command is a value, not content*.

This is what decides that a tag over raw cetz draw commands is refused rather than
supported. A tag reaches its slide's plan through a marker element and a show rule over
the slide body, so a tag site that cannot hold content cannot be reached at all.

The three probes together are the argument: a draw command is an array of closures, a
canvas body refuses content outright, and what a canvas *does* lay out as content, a
`content()` element, is reached by a show rule installed outside the canvas.

Measured against cetz 0.5.2 on typst 0.15.1.
"""

import re

from harness import CETZ, TypstRunner, require

PAGE = "#set page(width: 300pt, height: 200pt, margin: 10pt)\n"


def labels(markup: str) -> list[str]:
    """Every `data-typst-label` value in an SVG document, in document order."""
    return re.findall(r'data-typst-label="([^"]*)"', markup)


def test_a_draw_command_is_an_array_of_closures(typst: TypstRunner):
    """`grid(..)` is a value, built where it is written, and not content.

    Which means it carries no marker, so a tag around it reaches no view and could never
    resolve its content for an epoch. The geometry-emitting and the state-changing commands
    have the same shape, so neither is a special case of the other.
    """
    package = require(typst, CETZ)
    typst.ok(
        f'#import "{package}"\n'
        + "#let commands = {\n"
        + "  import cetz.draw: *\n"
        + "  grid((0, 0), (4, 2))\n"
        + "}\n"
        + "#let state-change = {\n"
        + "  import cetz.draw: *\n"
        + "  stroke(red)\n"
        + "}\n"
        + "#assert.eq(type(commands), array)\n"
        + "#assert(commands.all(it => type(it) == function), "
        + 'message: "a draw command is not a stream of closures")\n'
        + "#assert.eq(type(state-change), array)\n"
        + "#assert(state-change.all(it => type(it) == function))\n"
    )


def test_a_canvas_body_cannot_hold_content(typst: TypstRunner):
    """The stream is an array, so content beside a draw command is a join error.

    There is therefore no way to put a marker, or a `context` block, inside the stream and
    have it survive to where a show rule could act on it.
    This is also why a region cannot go inside a canvas.
    """
    package = require(typst, CETZ)
    typst.fails(
        f'#import "{package}"\n'
        + PAGE
        + "#cetz.canvas({\n"
        + "  import cetz.draw: *\n"
        + "  circle((0, 0), radius: 1)\n"
        + "  context [a context block is content]\n"
        + "})\n",
        "cannot join array with content",
    )


def test_a_show_rule_outside_a_canvas_reaches_a_content_element_inside_it(
    typst: TypstRunner,
):
    """The positive half, and the reason a tag on a cetz `content()` resolves per epoch.

    A `content()` element holds real content, laid out with the show rules in force where
    the canvas sits, so the mechanism that hands a tag its slide's view reaches into a
    canvas as it reaches anywhere else.
    The replacement carries a label of its own, which is what says the rule really fired:
    the marker's own label reaches no group, and the replacement's does.
    """
    package = require(typst, CETZ)
    markup = typst.svg(
        f'#import "{package}"\n'
        + PAGE
        + '#let marker = [#metadata("ask")#label("marker")]\n'
        + "#{\n"
        + '  show label("marker"): it => [#box[resolved]#label("resolved")]\n'
        + "  cetz.canvas({\n"
        + "    import cetz.draw: *\n"
        + "    circle((0, 0), radius: 1)\n"
        + "    content((0, 0), marker)\n"
        + "  })\n"
        + "}\n"
    )
    assert labels(markup) == ["resolved"]
