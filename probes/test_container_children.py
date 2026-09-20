# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *What a container resolves from its own children*.

This is what decides that a tag or a region around a `grid.cell` or an `item` element is
refused rather than supported. A site is a `context` block between the container and the
element, and a container that reads its own children never sees the element behind one.

The probes are the argument in three parts. A container keeps the settings of a direct
child and drops those of a child behind a `context` block, a `box` or a `styled`, while a
label leaves them alone. An item behind one is taken as the content of an item with default
settings, so it renders as a nested list or enum. A container paints the fill in its own
frame, outside any group a label inside the cell produces, which is why rebuilding the cell
around the site would restore the picture and leave the continuous primitives reaching only
the cell's content.
The element functions are distinguishable under `==` though `repr` collapses them, which is
what a refusal has to detect with.

Measured on typst 0.15.0.
"""

from harness import TypstRunner
from svgtools import SVG, group, parse

PAGE = "#set page(width: 300pt, height: 120pt, margin: 2pt)\n"

FILL = "#ffdc00"
"""What typst prints for `yellow`, which is the fill every probe here looks for."""


def fills(markup: str) -> list[str]:
    """Every fill a path in the SVG paints, in document order."""
    root = parse(markup)
    return [path.get("fill") for path in root.iter(f"{SVG}path") if path.get("fill")]


def test_a_grid_keeps_the_fill_of_a_direct_cell_and_of_a_labelled_one(typst: TypstRunner):
    """The comparison the next probe needs, so that a missing fill means something.

    The labelled cell is the half that is easy to assume away. A label does not stop the
    grid from reading the cell, so the loss the next probe measures is about the element
    that sits between the two and not about touching the cell at all.
    """
    markup = typst.svg(
        PAGE
        + """
#grid(
  columns: (1fr, 1fr),
  inset: 5pt,
  grid.cell(fill: yellow)[direct],
  [#grid.cell(fill: yellow)[labelled]<probe-cell>],
)
"""
    )
    assert fills(markup).count(FILL) == 2, "a direct or a labelled cell lost its fill"


def test_an_element_between_a_grid_and_its_cell_drops_the_cell_settings(typst: TypstRunner):
    """A `context` block, a `box` and a `styled` all hide the cell from the grid.

    The `styled` case is the one that is guessed wrong, and it is why a package must not
    look through `styled` on this path: typst does not look through it either. Without this,
    a refusal written against `context` alone would let `text(red, grid.cell(..))` past.
    """
    for between in (
        "context grid.cell(fill: yellow)[x]",
        "box(grid.cell(fill: yellow)[x])",
        "text(red, grid.cell(fill: yellow)[x])",
        "{ set text(blue); grid.cell(fill: yellow)[x] }",
    ):
        markup = typst.svg(
            PAGE + f"#grid(columns: (1fr,), inset: 5pt, {between})\n",
            name="between.svg",
        )
        assert FILL not in fills(markup), f"the grid still saw the cell behind {between}"


def test_a_table_loses_the_same_settings(typst: TypstRunner):
    """The claim is about containers that resolve their children, not about `grid` alone."""
    direct = typst.svg(
        PAGE + "#table(columns: (1fr,), table.cell(fill: yellow)[x])\n",
        name="table-direct.svg",
    )
    assert FILL in fills(direct), "a direct table cell lost its fill"
    behind = typst.svg(
        PAGE + "#table(columns: (1fr,), context table.cell(fill: yellow)[x])\n",
        name="table-context.svg",
    )
    assert FILL not in fills(behind), "the table still saw the cell behind a context block"


def test_colspan_goes_the_way_the_fill_does(typst: TypstRunner):
    """The loss is the whole of the cell's settings, and not the fill alone.

    Asserted as two comparisons rather than as one absence. A `colspan` the grid reads
    changes the rendering, and a `colspan` behind a `context` block changes nothing, so the
    setting reached the grid in the first case and was dropped in the second.
    """
    source = PAGE + "#grid(columns: (1fr, 1fr), inset: 5pt, CELL, [y])\n"

    def render(cell: str, name: str) -> str:
        return typst.svg(source.replace("CELL", cell), name=name)

    spanning = render("grid.cell(fill: yellow, colspan: 2)[x]", "span-direct.svg")
    single = render("grid.cell(fill: yellow)[x]", "single-direct.svg")
    assert spanning != single, "a colspan the grid reads changed nothing, so the probe is vacuous"

    behind_spanning = render("context grid.cell(fill: yellow, colspan: 2)[x]", "span-context.svg")
    behind_single = render("context grid.cell(fill: yellow)[x]", "single-context.svg")
    assert behind_spanning == behind_single, "the colspan survived the context block"


def test_an_item_behind_a_context_block_loses_its_place_in_its_container(typst: TypstRunner):
    """A list takes the item as content, and a terms list refuses outright.

    The list half is asserted from the document, where the structure is, rather than from
    the rendering: the container still has two children, and the second one holds the item
    instead of being it.
    """
    typst.ok(
        PAGE
        + """
#context {
  // A direct item is kept, so the list has two items and neither is a list.
  let direct = list(list.item[a], list.item[b])
  assert.eq(direct.children.len(), 2, message: repr(direct))
  assert(direct.children.all(it => it.func() == list.item), message: repr(direct))
  // An item behind a context block is content, so the list has one item holding the rest.
  let behind = list(list.item[a], context list.item[b])
  assert.eq(behind.children.len(), 2, message: repr(behind))
  assert.ne(behind.children.at(1).body.func(), list.item, message: repr(behind))
}
"""
    )
    typst.fails(
        PAGE + "#terms(terms.item[a][x], context terms.item[b][y])\n",
        "expected term item or array",
    )


def test_an_enum_item_behind_a_context_block_is_nested_rather_than_renumbered(
    typst: TypstRunner,
):
    """The explicit number survives into the nested enum, and the item's place does not.

    This is the half that is easy to state the other way round. The enclosing enum numbers
    the item that holds the nested one from its own count, so the direct form renders two
    numbers and the nested form renders three, with the explicit one still among them.
    """

    def runs(second: str, name: str) -> int:
        markup = typst.svg(PAGE + f"#enum(enum.item(7)[a], {second})\n", name=name)
        return len(parse(markup).findall(f".//{SVG}g"))

    direct = runs("enum.item(9)[b]", "enum-direct.svg")
    behind = runs("context enum.item(9)[b]", "enum-context.svg")
    assert behind > direct, f"the context block added no number: {direct} and {behind} groups"


def test_a_cell_fill_is_painted_outside_every_group_a_label_produces(typst: TypstRunner):
    """The container paints the fill, so no group inside the cell can ever contain it.

    This is what decides the refusal over a rebuild. Rebuilding the cell around the site
    restores the fill in the rendering and leaves the group holding only the cell's content,
    so `move`, `scale`, `reveal` and `hide` on it would reach the content and leave the fill
    standing.
    """
    markup = typst.svg(
        PAGE
        + """
#grid(
  columns: (1fr,),
  inset: 5pt,
  grid.cell(fill: yellow)[#box[inside]<probe-cell>],
)
"""
    )
    root = parse(markup)
    labelled = group(root, "probe-cell")
    inside = [path.get("fill") for path in labelled.iter(f"{SVG}path")]
    assert FILL not in inside, "the fill is inside the group after all"
    assert FILL in fills(markup), "the fill was not painted at all, so the probe is vacuous"


def test_the_container_children_are_told_apart_by_function_and_not_by_repr(typst: TypstRunner):
    """`repr` collapses them to `cell` and `item`, while `==` separates every pair.

    A refusal that matched on `repr` would refuse a `table.cell` in the name of `grid.cell`
    and could never say which container drops what. A refusal also reads `fields()` to see
    whether anything beside the body was set, and a label adds a key there.
    """
    typst.ok(
        PAGE
        + """
#assert.eq(repr(grid.cell), repr(table.cell))
#assert.eq(repr(list.item), repr(enum.item))
#assert.ne(grid.cell, table.cell)
#assert.ne(list.item, enum.item)
#assert.ne(list.item, terms.item)
#assert.eq((grid.cell(fill: red)[x]).func(), grid.cell)
#assert.eq((table.cell(fill: red)[x]).func(), table.cell)
#assert.ne((table.cell(fill: red)[x]).func(), grid.cell)

// `fields()` reports only what was set, and a label is reported as one of them.
#assert.eq((grid.cell[x]).fields().keys(), ("body",))
#assert.eq((grid.cell(fill: red)[x]).fields().keys(), ("body", "fill"))
#assert.eq([#grid.cell[x]<l>].fields().keys(), ("body", "label"))
#assert.eq((terms.item[a][b]).fields().keys(), ("term", "description"))
"""
    )
