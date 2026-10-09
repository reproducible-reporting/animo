# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tiers 1 and 2: the tag sites that are hardest, and the ones that are refused.

The claim that makes animo worth building is that anything typst can lay out as content can
be tagged. This module is where that claim is either true or not in the three places it is
hardest, and where the places it does not reach are pinned down rather than left for a
reader to discover. A cetz draw command is not content and is refused at the tag site. A
`grid.cell` and an item of a list are content, and are refused because the container reads
them from its own children and never sees one behind a tag site.

Two third-party packages are compiled here, so these tests skip when Universe cannot be
reached with a cold package cache, which is the only network dependency in the suite.
"""

from decks import deck
from harness import (
    CETZ,
    FLETCHER,
    Box,
    PagedRunner,
    TypstRunner,
    assert_identical_outside,
    difference_box,
    require,
)
from test_structural import PRESENTATION, check, marker
from test_subslides import timeline

# A figure with one tagged label on it, as a function of what it draws.
# The circle, the line and the mesh are geometry, which no tag can address,
# while the label is content, which every primitive can address.
# Being a function of `mesh` is what makes the geometry changeable after all,
# because the timeline replaces the whole canvas with the same function called differently.
SCENE = """#let scene(mesh: true, label: LABEL) = cetz.canvas({
  import cetz.draw: *
  circle((0, 0), radius: 1)
  line((0, 0), (4, 0))
  if mesh { grid((-2, -2), (2, 2), stroke: gray) }
  content((4, 0), label, anchor: "west")
})

"""


def cetz_deck(typst: TypstRunner, *slides: str, label: str = 'tag("lab")[Hi]', **kwargs) -> str:
    """A deck whose preamble defines `scene(mesh: ..)` around one tagged label."""
    require(typst, CETZ)
    preamble = f'#import "{CETZ}"\n\n' + SCENE.replace("LABEL", label)
    return deck(*slides, preamble=preamble, **kwargs)


# Tier 1: the sites resolve, and what they reserve.


def test_a_tag_inside_math_is_one_addressable_site(typst: TypstRunner):
    """A box in an equation becomes a group, which is what the browser addresses.

    The trap this rules out is the parsing one.
    `#box[b] <bb>` with a space is literal math content and attaches to nothing.
    A tag returns a markup block holding the box and the label together, which attaches
    inside math as it does outside it.
    """
    source = deck('slide[$ a + #tag("b")[$b$] = c $]') + check(
        "assert.eq(query(<b>).len(), 1)",
        'assert.eq(repr(query(<b>).first().func()), "box")',
    )
    typst.ok(source)


def test_a_tag_inside_math_lays_out_the_content_of_its_epoch(typst: TypstRunner):
    """Replacing part of an equation is a structural step like any other."""
    animation = timeline(
        f'sub(replace("b")[{marker("new")}$beta + gamma$])',
        'sub(remove("b"))',
    )
    body = f'$ a + #tag("b")[{marker("old")}$b$] = c $'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "assert.eq(pages(<old>), (1,))",
        "assert.eq(pages(<new>), (2,))",
    )
    typst.ok(source, **PRESENTATION)


def test_the_implicit_region_inside_math_is_the_widest_epoch(typst: TypstRunner):
    """A tag inside math is its own region, and an inline one, as it is in a paragraph.

    Math is not a flow, so nothing around the tag could absorb a change. The footprint is
    what keeps the equation the same size in every epoch, and the price is the gap the
    smaller epochs show inside it.
    """
    animation = timeline('sub(replace("b", box(width: 3cm, height: 4mm)))')
    body = '$ a + #tag("b", box(width: 5mm, height: 2mm)) = c $'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let found = footprints("b")',
        'assert(found.all(it => it.kind == "inline"), message: repr(found))',
        "assert(found.all(it => close(it.width, 3cm)), message: repr(found))",
        "assert(query(<b>).all(it => close(it.width, 3cm)))",
    )
    typst.ok(source, **PRESENTATION)


def test_a_tag_on_a_cetz_content_element_lays_out_the_content_of_its_epoch(
    typst: TypstRunner,
):
    """A cetz `content()` element holds ordinary content, so it is an ordinary tag site."""
    animation = timeline(f'sub(replace("lab")[{marker("new")}Replaced])')
    source = cetz_deck(
        typst,
        f"slide(animation: {animation})[#scene()]",
        label=f'tag("lab")[{marker("old")}Hi]',
    ) + check(
        "assert.eq(pages(<old>), (1,))",
        "assert.eq(pages(<new>), (2,))",
        "assert.eq(query(<lab>).len(), 2)",
    )
    typst.ok(source, **PRESENTATION)


def test_a_tag_on_a_fletcher_node_lays_out_the_content_of_its_epoch(typst: TypstRunner):
    """A fletcher node label is content too, and nothing about the tag site differs."""
    require(typst, FLETCHER)
    animation = timeline(f'sub(replace("n")[{marker("new")}Bee])')
    body = (
        "#diagram(\n"
        f'    node((0, 0), tag("n")[{marker("old")}A]),\n'
        "    node((1, 0), [B]),\n"
        '    edge("->"),\n'
        "  )"
    )
    source = deck(
        f"slide(animation: {animation})[\n  {body}\n]",
        preamble=f'#import "{FLETCHER}": diagram, edge, node\n\n',
    ) + check(
        "assert.eq(pages(<old>), (1,))",
        "assert.eq(pages(<new>), (2,))",
    )
    typst.ok(source, **PRESENTATION)


def test_a_tag_over_cetz_draw_commands_is_refused(typst: TypstRunner):
    """The real case, with the real value, and not a stand-in array.

    A draw command is a stream of closures built where it is written, before any show rule
    or `context` exists that could resolve it for an epoch, so no primitive could ever
    reach it. Handing it back untouched is the silent no-op this refusal exists to prevent,
    and a message three tools away from its cause is what it would otherwise cost.
    """
    body = (
        "#cetz.canvas({\n"
        "    import cetz.draw: *\n"
        '    tag("g", wrap: none, grid((0, 0), (4, 2)))\n'
        "  })"
    )
    result = typst.fails(
        cetz_deck(typst, f"slide[\n  {body}\n]"),
        "the body of the tag g is not content, but array",
    )
    assert "tag a cetz content() element" in result.stderr
    assert "tag the whole canvas" in result.stderr


def test_a_region_inside_a_cetz_canvas_is_refused(typst: TypstRunner):
    """The boundary the manual states: a region bounds content, a canvas consumes commands.

    The message names the way out, which is a region around the canvas rather than in it.
    """
    body = "#cetz.canvas({\n    import cetz.draw: *\n    region(grid((0, 0), (4, 2)))\n  })"
    result = typst.fails(
        cetz_deck(typst, f"slide[\n  {body}\n]"),
        "is not content, but array",
    )
    assert "goes inside a canvas that the region is put around" in result.stderr


def test_a_tag_around_a_grid_cell_is_refused(typst: TypstRunner):
    """The container reads the cell, and a tag site is a context block between the two.

    Rebuilding the cell around the tag would restore the fill and leave every continuous
    primitive reaching the cell's content, so the message names both ways out: the tag goes
    inside the cell, and the fill goes on a block the tag holds.
    """
    body = '#grid(\n    columns: (1fr,),\n    tag("cell", grid.cell(fill: aqua)[x]),\n  )'
    result = typst.fails(
        deck(f"slide[\n  {body}\n]"),
        "the body of the tag cell is a grid.cell",
    )
    assert 'grid.cell(.., tag("cell")[..])' in result.stderr
    assert "block(fill: .., width: 100%, height: 100%)" in result.stderr


def test_a_tag_around_a_cell_that_carries_no_settings_is_left_alone(typst: TypstRunner):
    """Such a cell lays out the same either way, so the refusal would cost and gain nothing.

    A label on the cell is not one of the settings, since a label does not stop the grid
    from reading the cell.
    """
    body = (
        "#grid(\n"
        "    columns: (1fr, 1fr),\n"
        '    tag("plain", grid.cell[x]),\n'
        '    tag("labelled", [#grid.cell[y]<cell-label>]),\n'
        "  )"
    )
    typst.ok(deck(f"slide[\n  {body}\n]"))


def test_a_tag_around_a_list_item_is_refused_whatever_it_carries(typst: TypstRunner):
    """What a list drops is the item's place in it, which no setting on the item restores."""
    body = '#list(list.item[a], tag("second", list.item[b]))'
    result = typst.fails(
        deck(f"slide[\n  {body}\n]"),
        "the body of the tag second is a list.item",
    )
    assert "becomes a nested list" in result.stderr
    assert 'list.item(.., tag("second")[..])' in result.stderr


def test_a_region_around_a_grid_cell_is_refused_in_the_same_words(typst: TypstRunner):
    """A region becomes a container the same way a tag site does, so it loses the same fill."""
    body = "#grid(\n    columns: (1fr,),\n    region(grid.cell(fill: aqua)[x]),\n  )"
    result = typst.fails(
        deck(f"slide[\n  {body}\n]"),
        "the body of a region is a grid.cell",
    )
    assert "grid.cell(.., region[..])" in result.stderr


def test_the_documented_ways_around_a_tagged_cell_compile(typst: TypstRunner):
    """Both forms the refusal names, checked so that the message cannot go stale.

    The second is the one a timeline that moves the filled box needs, since a grid paints
    the fill in its own frame and no tag ever covers it.
    """
    body = (
        "#grid(\n"
        "    columns: (1fr, 1fr),\n"
        '    grid.cell(fill: aqua, tag("inside")[x]),\n'
        '    grid.cell(tag("held", block(\n'
        "      fill: gradient.linear(aqua, orange),\n"
        "      width: 100%,\n"
        "      height: 100%,\n"
        "    )[y])),\n"
        "  )"
    )
    animation = timeline('sub(move("held", dx: 1cm), reveal("inside"))')
    typst.ok(deck(f"slide(animation: {animation})[\n  {body}\n]"), **PRESENTATION)


# Tier 2: what changes on the page, and what does not.


def band_of(pages, changed: Box) -> Box:
    """The full-width band that holds every pixel that changed, one pixel proud of it."""
    return Box(0, changed.y0 - 1, pages[0].shape[1], changed.y1 + 1)


def test_replacing_part_of_an_equation_reflows_only_that_equation(paged: PagedRunner):
    """The equation keeps its width, so it stays centred and nothing else on the slide moves.

    This is the max-footprint rule doing the only thing it can do inside math.
    The room the replacement needs is reserved in every epoch,
    which is why a longer right-hand side does not shift the equation it sits in.
    """
    animation = timeline('sub(replace("b")[$beta + gamma + delta$])')
    body = (
        "A paragraph above the equation.\n\n"
        '  $ a + #tag("b")[$b$] = c $\n\n'
        "  A paragraph below the equation."
    )
    pages = paged.png(deck(f"slide(animation: {animation})[\n  {body}\n]"), mode="presentation")
    assert len(pages) == 2
    changed = difference_box(*pages)
    assert_identical_outside(pages[0], pages[1], band_of(pages, changed), what="the two states")
    assert changed.y1 - changed.y0 < 30, f"more than the equation changed: {changed}"


def test_replacing_a_whole_canvas_redraws_the_figure_and_nothing_else(paged: PagedRunner):
    """The way to change the geometry of a cetz figure, since draw commands cannot be tagged.

    The figure is a function of what it draws, the tag holds the whole canvas, and the
    timeline replaces it with the same function called differently. The tag reserves the
    larger of the two canvases, so the paragraph below it does not move.
    """
    animation = timeline('sub(replace("fig")[#scene(mesh: false)])')
    source = cetz_deck(
        paged.typst,
        f"slide(animation: {animation})[\n"
        '  #tag("fig")[#scene()]\n\n'
        "  A paragraph below the figure.\n"
        "]",
    )
    pages = paged.png(source, mode="presentation")
    assert len(pages) == 2
    changed = difference_box(*pages)
    assert_identical_outside(pages[0], pages[1], band_of(pages, changed), what="the two states")


def test_a_region_around_a_canvas_relays_the_figure_out(paged: PagedRunner):
    """Inside an explicit region the tag reserves nothing, so cetz lays the figure out afresh.

    The label grows, the canvas grows with it, and a centred canvas therefore moves inside
    the region.
    The region keeps the paragraph below it where it is, although everything in the figure
    moved.
    """
    animation = timeline('sub(replace("lab")[A much longer label indeed])')
    source = cetz_deck(
        paged.typst,
        f"slide(animation: {animation})[\n"
        "  #region[#align(center, scene(mesh: false))]\n\n"
        "  A paragraph below the region.\n"
        "]",
    )
    pages = paged.png(source, mode="presentation")
    changed = difference_box(*pages)
    assert_identical_outside(pages[0], pages[1], band_of(pages, changed), what="the two states")
    # The circle sits at the left of the figure and the label at its right, so a figure
    # that had merely been relabelled would change over a band at the right instead.
    assert changed.x0 < pages[0].shape[1] // 3, f"the figure did not move: {changed}"


def sites_deck(typst: TypstRunner) -> str:
    """One slide holding all three tag sites, with a timeline that addresses each of them.

    The deck carries one of each: a tagged term in an equation, a tagged label on a cetz
    figure, a tagged fletcher node, and the whole canvas tagged as well, so that the
    geometry change has somewhere to happen.
    """
    require(typst, FLETCHER)
    animation = timeline(
        'sub(move("lab", x: 5mm))',
        'sub(replace("fig")[#scene(mesh: false)])',
        'sub(apply("b", text.with(fill: red)), replace("node")[Bee])',
    )
    return cetz_deck(
        typst,
        f"slide(animation: {animation})[\n"
        '  #tag("fig")[#scene()]\n\n'
        '  $ a + #tag("b")[$b$] = c $\n\n'
        "  #diagram(\n"
        '    node((0, 0), tag("node")[A]),\n'
        "    node((1, 0), [B]),\n"
        '    edge("->"),\n'
        "  )\n"
        "]",
    ).replace("#slide", f'#import "{FLETCHER}": diagram, edge, node\n\n#slide', 1)


def test_a_deck_of_all_three_sites_reaches_every_output(paged: PagedRunner):
    """The definition of done, compiled the four ways an author compiles a deck.

    The SVG and the HTML are also read back for the groups, since a tag site that laid out
    but emitted no group would animate in neither.
    """
    source = paged.typst.source(sites_deck(paged.typst))
    assert len(paged.png(source, mode="presentation")) == 4
    assert len(paged.png(source)) == 1
    exported = paged.svg(source)
    assert len(exported) == 1
    for markup in (exported[0].read_text(), paged.typst.html(source).read_text()):
        for name in ("fig", "lab", "b", "node"):
            assert f'data-typst-label="{name}"' in markup, name
