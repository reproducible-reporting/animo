# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Nested Context Blocks Can Cost a Pass of Layout per Level*.

Typst stops after five passes of layout and warns that the document did not converge.
Two patterns delay every level of a nesting of `context` blocks by one pass,
so the depth at which a document stops converging counts those levels.

A check that fails in the block holding the next level empties that block,
and a state read in the first pass reads the initial value,
so each level is laid out a pass after the level around it.
The same check in a separate block beside the marker costs nothing.

A `context` block that captures a value read from a counter in the block around it
settles a pass after that block.
The same value emitted beside the block, outside its closure, costs nothing.
"""

import pytest
from harness import TypstRunner

CHECKED = """\
#let s = state("inside", false)
#let ask-label = <ask>
#let provide(body) = {{ show ask-label: it => (it.value)(); body }}
#let site(body) = {site}
#s.update(true)
#provide({nested})
#s.update(false)
"""

# The check and the marker in one block, as a site that checks where it is laid out.
IN_BLOCK = (
    'context { assert(s.get(), message: "outside"); [#metadata(() => block(body))#ask-label] }'
)

# The check in a separate block beside the marker.
APART = '{ context assert(s.get(), message: "outside"); [#metadata(() => block(body))#ask-label] }'

COUNTED = """\
#let c = counter("level")
#let level(n, parent) = {{
  c.step()
  {beside}
  context {{
    let id = c.get().first()
    {inside}
    if n > 1 {{ level(n - 1, id) }}
  }}
}}
#level({depth}, none)
"""


def checked(site: str, depth: int) -> str:
    """Sites nested `depth` deep, each asking a provider at the top for its content."""
    nested = "[C]"
    for _ in range(depth):
        nested = f"site({nested})"
    return CHECKED.format(site=site, nested=nested)


def counted(depth: int, *, captured: bool) -> str:
    """Levels nested `depth` deep, each numbered by a counter and told the number above it.

    `captured` puts the number above in the closure of the context block,
    and otherwise it is emitted beside that block.
    """
    if captured:
        beside, inside = "", "[#metadata((id, parent))<id>]"
    else:
        beside, inside = "[#metadata(parent)<parent>]", "[#metadata(id)<id>]"
    return COUNTED.format(beside=beside, inside=inside, depth=depth)


def converges(typst: TypstRunner, source: str) -> bool:
    """Whether a document compiles without a convergence warning."""
    result = typst.compile(source)
    return result.ok and "did not converge" not in result.stderr


def test_a_check_in_the_block_of_a_nested_marker_costs_a_pass_per_level(typst: TypstRunner):
    """Four levels converge, and five are refused although every site is inside.

    Every level costs one of the five passes, and the last pass still fails the check of the
    innermost site, so typst reports that failure beside the convergence warning.
    """
    assert converges(typst, checked(IN_BLOCK, 4))
    result = typst.fails(checked(IN_BLOCK, 5), "outside")
    assert "did not converge" in result.stderr, result.report()


def test_a_check_apart_from_a_nested_marker_costs_nothing(typst: TypstRunner):
    """The control. The same check beside the marker converges eight levels deep."""
    assert converges(typst, checked(APART, 8))


def test_the_check_of_a_nested_marker_reports_a_site_outside(typst: TypstRunner):
    """A check apart from the marker still refuses a site that is outside for good."""
    source = checked(APART, 3).replace("#s.update(true)\n", "")
    typst.fails(source, "outside")


@pytest.mark.parametrize(("depth", "expected"), [(5, True), (6, False)])
def test_a_captured_counter_value_costs_a_pass_per_level(
    typst: TypstRunner, depth: int, expected: bool
):
    """Five levels converge and six do not when each closure captures the number above it."""
    assert converges(typst, counted(depth, captured=True)) == expected


def test_a_counter_value_emitted_beside_the_block_costs_nothing(typst: TypstRunner):
    """The control. The number above, emitted outside the closure, converges eight deep."""
    assert converges(typst, counted(8, captured=False))
