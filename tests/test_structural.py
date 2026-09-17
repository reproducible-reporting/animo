# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tiers 1 and 2: content that changes, at the tag site and on the page.

The resolver's half of the epoch model is asserted in `test_plan.py`.
This module asserts the tag's half:
that every state lays out the content of its epoch, that a tag whose content changes
reserves the largest extent over its epochs as an actual length, and that it measures each
epoch once.
Then it asserts the claim all of that exists for, in pixels:
nothing outside such a tag moves when its content changes.

The content a state lays out is recognised by `metadata` markers inside it,
which `query` finds on the pages where that content was laid out and nowhere else,
since a measurement lays content out without putting it in the document.
That asserts which content is where without comparing any content.
"""

import pytest
from decks import deck
from harness import PagedRunner, TypstRunner, assert_identical, assert_identical_outside
from test_subslides import GREEN, RED, Box, color_box, timeline

BLUE = (0, 0, 255)

PRESENTATION = {"sysinp": {"animo": "presentation"}}

# Readers for the documents below.
# `pages` is the list of pages a marker was laid out on, in the presentation mode, where
# page i + 1 is state i of a one-slide deck.
READERS = """
#let footprints(name) = (
  query(label("animo-footprint")).map(it => it.value).filter(it => it.name == name)
)
#let pages(target) = query(target).map(it => it.location().page())
// A `box` reports its size as a relative length, whose length part is the one set here.
#let absolute(x) = if type(x) == relative { x.length.to-absolute() } else { x.to-absolute() }
#let close(a, b) = calc.abs(absolute(a) - absolute(b)) < 0.01pt
"""


def check(*assertions: str) -> str:
    """A context block asserting about the laid-out document."""
    body = "\n  ".join(assertions)
    return f"{READERS}\n#context {{\n  {body}\n}}\n"


def marker(value: str) -> str:
    """A marker that says where a piece of content was laid out."""
    return f'#metadata("{value}")<{value}>'


# Which content each state lays out.


def test_every_state_lays_out_the_content_of_its_epoch(typst: TypstRunner):
    """Replaced, kept across a continuous step, removed, and brought back by `reset`."""
    animation = timeline(
        "sub()",
        f'sub(replace("t")[new {marker("new")}])',
        'sub(move("t", dx: 1cm))',
        'sub(remove("t"))',
        'sub(reset("t"))',
    )
    source = deck(f'slide(animation: {animation})[#tag("t")[old {marker("old")}]]') + check(
        "assert.eq(pages(<old>), (1, 2, 6))",
        "assert.eq(pages(<new>), (3, 4))",
    )
    typst.ok(source, **PRESENTATION)


def test_a_tag_the_timeline_resets_is_not_laid_out_until_it_is(typst: TypstRunner):
    """A `reset` is what says the tag starts removed, and it is the step that brings it in."""
    animation = timeline("sub()", 'sub(reset("t"))')
    body = f'#tag("t")[late {marker("late")}]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "assert.eq(pages(<late>), (3,))",
    )
    typst.ok(source, **PRESENTATION)


def test_a_tag_that_lays_nothing_out_on_a_page_still_reports_that_page(typst: TypstRunner):
    """A handout may keep only a state that removed the tag, and the name must still resolve.

    The site emits its report where it lays no content out, which is what keeps a name the
    timeline addresses from looking like a name the slide has no tag of.
    """
    animation = timeline('sub(remove("t"), hide("t"))')
    typst.ok(deck(f'slide(animation: {animation})[#tag("t")[a]]'))


def test_a_wrap_none_tag_changes_its_content_too(typst: TypstRunner):
    """Structural primitives reach a tag site that becomes no group."""
    animation = timeline(f'sub(replace("t")[{marker("new")}])', 'sub(remove("t"))')
    source = deck(
        f'slide(animation: {animation})[#tag("t", wrap: none)[{marker("old")}]]'
    ) + check(
        "assert.eq(pages(<old>), (1,))",
        "assert.eq(pages(<new>), (2,))",
    )
    typst.ok(source, **PRESENTATION)


def test_a_tag_inside_a_replacement_is_a_tag_of_the_slide(typst: TypstRunner):
    """Replacement content is laid out under the slide's view, so the tags in it are addressable."""
    animation = timeline(
        f'sub(replace("t")[around #tag("inner")[{marker("inner-body")}]])',
        'sub(move("inner", dx: 1cm))',
    )
    source = deck(f'slide(animation: {animation})[#tag("t")[plain]]') + check(
        "assert.eq(pages(<inner-body>), (2, 3))",
        "assert.eq(pages(<inner>), (2, 3))",
    )
    result = typst.ok(source, **PRESENTATION)
    assert "converge" not in result.stderr, result.stderr


# How the structural primitives compose, as laid out.

WRAPPERS = """
#let first(it) = [#metadata("first")<wrapper>#it]
#let second(it) = [#metadata("second")<wrapper>#it]
"""


def test_a_replacement_is_laid_out_inside_the_wrappers_applied_before_it(typst: TypstRunner):
    """The wrapper lays out on the replacement's page, around the replacement."""
    animation = timeline('sub(apply("t", first))', f'sub(replace("t")[{marker("new")}])')
    source = (
        WRAPPERS
        + deck(f'slide(animation: {animation})[#tag("t")[old]]')
        + check(
            "assert.eq(pages(<wrapper>), (2, 3))",
            "assert.eq(pages(<new>), (3,))",
        )
    )
    typst.ok(source, **PRESENTATION)


def test_wrappers_apply_outermost_last(typst: TypstRunner):
    """`apply("t", first, second)` is `second(first(body))`, so `second` comes first in order."""
    animation = timeline('sub(apply("t", first, second))')
    source = (
        WRAPPERS
        + deck(f'slide(animation: {animation})[#tag("t")[old]]')
        + check('assert.eq(query(<wrapper>).map(it => it.value), ("second", "first"))')
    )
    typst.ok(source, **PRESENTATION)


def test_reset_after_remove_lays_out_the_body_without_its_wrappers(typst: TypstRunner):
    """The body comes back as the body declares it."""
    animation = timeline('sub(apply("t", first))', 'sub(remove("t"))', 'sub(reset("t"))')
    source = (
        WRAPPERS
        + deck(f'slide(animation: {animation})[#tag("t")[{marker("old")}]]')
        + check(
            "assert.eq(pages(<wrapper>), (2,))",
            "assert.eq(pages(<old>), (1, 2, 4))",
        )
    )
    typst.ok(source, **PRESENTATION)


def test_a_structural_and_a_continuous_step_on_one_tag_both_land(typst: TypstRunner):
    """The replacement is laid out moved, in the state that does both.

    The control is a second tag replaced in the same step and not moved,
    which sits at the same place in the flow.
    """
    animation = timeline(
        f'sub(replace("t")[{marker("moved")}], move("t", dx: 1cm), '
        f'replace("u")[{marker("control")}])'
    )
    body = '#tag("t", wrap: block)[old]\n\n#tag("u", wrap: block)[old]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "assert.eq(pages(<moved>), (2,))",
        "let moved = query(<moved>).first().location().position()",
        "let control = query(<control>).first().location().position()",
        "assert(close(moved.x - control.x, 1cm), message: repr((moved, control)))",
    )
    typst.ok(source, **PRESENTATION)


# Footprints, as actual lengths, and what measuring them costs.


def test_a_slide_without_structural_steps_measures_nothing(typst: TypstRunner):
    """One epoch is exactly as cheap as before epochs existed: no footprint anywhere."""
    animation = timeline('sub(move("a", dx: 1cm))', 'sub(hide("b"))')
    body = '#tag("a")[a] #tag("b", wrap: block)[b]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'assert.eq(query(label("animo-footprint")).len(), 0)',
    )
    typst.ok(source, **PRESENTATION)


def test_a_tag_whose_content_never_changes_is_not_measured(typst: TypstRunner):
    """Only the tags a structural operation addresses pay for the slide's epochs."""
    animation = timeline('sub(replace("changing")[new])')
    body = '#tag("changing")[old] #tag("still")[still]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'assert.eq(footprints("still"), ())',
        'assert.eq(footprints("changing").len(), 2)',
    )
    typst.ok(source, **PRESENTATION)


def test_each_tag_measures_every_epoch_once(typst: TypstRunner):
    """Linear in epochs: four tags over three epochs measure three renderings each, not 3^4."""
    animation = timeline(
        'sub(replace("a")[aa], remove("b"))',
        'sub(move("a", dx: 1cm))',
        'sub(apply("c", emph), reset("d"))',
    )
    body = '#tag("a")[a] #tag("b")[b] #tag("c", wrap: block)[c] #tag("d")[d]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "for name in (\"a\", \"b\", \"c\", \"d\") {",
        "  let found = footprints(name)",
        "  assert.eq(found.len(), 4, message: name)",
        "  assert(found.all(it => it.measured.len() == 3), message: name)",
        "}",
    )
    typst.ok(source, **PRESENTATION)


def test_an_inline_footprint_is_the_widest_width_and_the_tallest_line(typst: TypstRunner):
    """Per axis, over the epochs: 2 cm from the second, 8 mm of ascent from the third.

    The boxes stand on the baseline and reach nothing below it, so the height is the ascent.
    """
    animation = timeline(
        'sub(replace("t", box(width: 2cm, height: 3mm)))',
        'sub(replace("t", box(width: 5mm, height: 8mm)))',
    )
    body = 'Before #tag("t", box(width: 1cm, height: 5mm)) after.'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let found = footprints("t")',
        'assert(found.all(it => it.kind == "inline"))',
        "assert(found.all(it => close(it.width, 2cm)), message: repr(found.first()))",
        "assert(found.all(it => close(it.height, 8mm)), message: repr(found.first()))",
        "for it in query(<t>) {",
        "  assert(close(it.width, 2cm))",
        "  assert(close(it.height, 8mm))",
        "}",
    )
    typst.ok(source, **PRESENTATION)


def test_an_epoch_that_lays_nothing_out_adds_nothing_to_an_inline_footprint(typst: TypstRunner):
    """The shared box is the line of the epochs that hold content, and of no other.

    An extent is read around the baseline of a rendering, and a rendering carries the
    display state of its epoch, which is a `move`.
    A `move` is block-level, so one that is measured without a box around it lays its
    payload out in a paragraph of its own and reports the baseline of the line below it.
    The descent then covers a whole line and the ascent turns negative.
    An epoch that lays nothing out has an extent of zeroes, so the shared box becomes a
    line taller than the content it holds.
    """
    animation = timeline('sub(remove("t"))')
    body = 'Before #tag("t", box(width: 1cm, height: 5mm)) after.'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let found = footprints("t")',
        'assert(found.all(it => it.kind == "inline"))',
        "assert(found.all(it => close(it.width, 1cm)), message: repr(found.first()))",
        "assert(found.all(it => close(it.height, 5mm)), message: repr(found.first()))",
        "for it in query(<t>) {",
        "  assert(close(it.width, 1cm))",
        "  assert(close(it.height, 5mm))",
        "}",
    )
    typst.ok(source, **PRESENTATION)


def test_a_tag_that_an_epoch_removes_holds_its_text_on_the_line_around_it(typst: TypstRunner):
    """The baseline inside the footprint is the baseline of the text beside it.

    The height of the footprint says how much room the line gives the tag, and the position
    of the content inside it says where the baseline of that room lies.
    Both follow from the extent of a rendering, so both are asserted.
    The body is the word `pages` rather than a box, because a descender is what makes the
    ascent and the descent differ.
    """
    animation = timeline('sub(remove("t"))')
    body = f'{marker("beside")}Before #tag("t")[{marker("inside")}pages] after.'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let found = footprints("t")',
        "assert(found.all(it => close(it.height, measure([pages]).height)), "
        "message: repr(found.first()))",
        "let beside = query(<beside>).first().location().position()",
        "let inside = query(<inside>).first().location().position()",
        "assert(close(beside.y, inside.y), message: repr((beside.y, inside.y)))",
    )
    typst.ok(source, **PRESENTATION)


def test_a_block_footprint_fills_its_container_and_is_the_tallest_epoch(typst: TypstRunner):
    """The width is the slide body's, 14 cm here, and the height the tallest epoch's."""
    animation = timeline(
        'sub(replace("t", rect(height: 3cm)))',
        'sub(remove("t"))',
    )
    body = '#tag("t", rect(height: 1cm))'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let found = footprints("t")',
        'assert(found.all(it => it.kind == "block"))',
        "assert(found.all(it => close(it.width, 14cm)), message: repr(found.first()))",
        "assert(found.all(it => close(it.height, 3cm)), message: repr(found.first()))",
        "assert(query(<t>).all(it => close(it.height, 3cm)))",
    )
    typst.ok(source, **PRESENTATION)


def test_hiding_and_removing_reserve_the_same_footprint(typst: TypstRunner):
    """Inside a tag's own box the two cannot be told apart, which the manual says.

    `h` starts hidden, because `reveal` is the first thing said about it, and is removed
    later; `r` starts removed, because `reset` is the first thing said about it. Both
    therefore hold the same text in some states and nothing in others.
    """
    animation = timeline('sub(reveal("h"), reset("r"))', 'sub(remove("h"))')
    body = '#tag("h")[Initial text] #tag("r")[Initial text]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let h = footprints("h").map(it => (it.width, it.height))',
        'let r = footprints("r").map(it => (it.width, it.height))',
        "assert.eq(h, r)",
        "assert(close(r.first().first(), measure([Initial text]).width))",
    )
    typst.ok(source, **PRESENTATION)


def test_a_nested_tag_that_changes_leaves_its_outer_tag_unmeasured_and_still(typst: TypstRunner):
    """The inner footprint is fixed, so the outer tag lays out the same in every epoch."""
    animation = timeline(
        'sub(replace("inner")[a much longer replacement of the inner phrase])',
        'sub(remove("inner"))',
    )
    body = (
        '#tag("outer", wrap: block)[Text with #tag("inner")[a phrase] in it.]\n\n'
        "#metadata(none)<after>After."
    )
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'assert.eq(footprints("outer"), ())',
        "let ys = query(<after>).map(it => it.location().position().y)",
        "assert.eq(ys.len(), 3)",
        "assert.eq(ys.dedup().len(), 1, message: repr(ys))",
    )
    typst.ok(source, **PRESENTATION)


# The HTML target, which renders one frame per epoch.


def test_a_deck_with_structural_steps_compiles_to_html(typst: TypstRunner):
    """One frame per epoch, each laid out with every footprint and its own content state."""
    animation = timeline(
        f'sub(replace("t")[{marker("new")}])', 'sub(apply("u", emph))', 'sub(remove("t"))'
    )
    body = f'#tag("t")[{marker("old")}] #tag("u", wrap: block)[u]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "// Four epochs: the body, the replacement, the restyling of u, and the removal.",
        "assert.eq(query(<old>).len(), 1)",
        "assert.eq(query(<new>).len(), 2)",
        'assert.eq(footprints("t").len(), 4)',
    )
    result = typst.ok(source, html=True)
    assert "converge" not in result.stderr, result.stderr


def test_an_inline_footprint_in_the_html_target_is_the_line_it_holds(typst: TypstRunner):
    """The same footprint is reserved in both targets, so both are asserted.

    The browser shows the frames of a slide in one place, and a frame that reserves a line
    too much moves the line there exactly as it does on paper.
    """
    animation = timeline('sub(remove("t"))')
    body = 'Before #tag("t", box(width: 1cm, height: 5mm)) after.'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let found = footprints("t")',
        'assert.eq(found.len(), 2)',
        "assert(found.all(it => close(it.height, 5mm)), message: repr(found.first()))",
        "assert(found.all(it => close(it.width, 1cm)), message: repr(found.first()))",
    )
    typst.ok(source, html=True)


# Tier 2: the pages.


def colored(color: str, width: str, height: str) -> str:
    """A filled rectangle, which is what the pixel assertions find."""
    return f'rect(width: {width}, height: {height}, fill: rgb("{color}"))'


def union(*boxes: Box, pad: int = 1) -> Box:
    """The smallest box around all the boxes, one pixel larger for the antialiased edge."""
    return Box(
        min(b.x0 for b in boxes) - pad,
        min(b.y0 for b in boxes) - pad,
        max(b.x1 for b in boxes) + pad,
        max(b.y1 for b in boxes) + pad,
    )


def test_nothing_outside_a_replaced_block_tag_changes(paged: PagedRunner):
    """Everything but the red content is pixel-identical between the two states."""
    animation = timeline(f'sub(replace("t", {colored("#ff0000", "5cm", "2cm")}))')
    body = (
        f"#{colored('#0000ff', '2cm', '1cm')}\n"
        f'#tag("t", {colored("#ff0000", "3cm", "1cm")})\n'
        f"#{colored('#00ff00', '2cm', '1cm')}\n"
        "A paragraph after the tag."
    )
    pages = paged.png(deck(f"slide(animation: {animation})[{body}]"), mode="presentation")
    assert len(pages) == 2
    red = union(color_box(pages[0], RED), color_box(pages[1], RED))
    assert_identical_outside(pages[0], pages[1], red, what="the two states")
    assert color_box(pages[0], GREEN) == color_box(pages[1], GREEN)


@pytest.mark.parametrize("step", ["replace(\"w\", box(fill: rgb(\"#ff0000\"), width: 2cm, height: 6mm))", 'remove("w")'])
def test_the_line_around_an_inline_tag_holds_still(paged: PagedRunner, step):
    """Taller, wider or gone, the rest of the line and the next paragraph do not move."""
    animation = timeline(f"sub({step})")
    body = (
        'Before #tag("w", box(fill: rgb("#ff0000"), width: 1cm, height: 3mm)) the line runs on.\n\n'
        f"#{colored('#00ff00', '2cm', '1cm')}"
    )
    pages = paged.png(deck(f"slide(animation: {animation})[{body}]"), mode="presentation")
    red = union(*(found for found in (color_box(page, RED) for page in pages) if found))
    assert_identical_outside(pages[0], pages[1], red, what="the two states")
    assert color_box(pages[0], GREEN) == color_box(pages[1], GREEN)


def test_a_tag_an_epoch_removes_costs_its_paragraph_nothing(paged: PagedRunner):
    """The control is the same paragraph with no tag in it.

    The test above holds the two states of one tag against each other, and a footprint that
    is a line too tall moves both of them by the same amount.
    The state that lays the body out is held against the untagged paragraph instead.
    """
    word = "pages"
    plain = paged.png(deck(f"slide[Before {word} after.]"))[0]
    animation = timeline('sub(remove("t"))')
    body = f'Before #tag("t")[{word}] after.'
    pages = paged.png(deck(f"slide(animation: {animation})[{body}]"), mode="presentation")
    assert len(pages) == 2
    # The one greyscale step a fractional position rounds to, as *Findings* records.
    assert_identical(plain, pages[0], tol=1, what="the paragraph around a removable tag")


def test_a_replacement_that_wraps_reflows_inside_its_footprint(paged: PagedRunner):
    """The change is several lines tall, and sits between the marks above and below."""
    long = "A replacement long enough to wrap onto a second and a third line of the slide. " * 3
    animation = timeline(f'sub(replace("t")[{long}])')
    body = (
        f"#{colored('#0000ff', '2cm', '5mm')}\n"
        '#tag("t", wrap: block)[A short paragraph.]\n\n'
        f"#{colored('#00ff00', '2cm', '5mm')}"
    )
    pages = paged.png(deck(f"slide(animation: {animation})[{body}]"), mode="presentation")
    above = color_box(pages[0], BLUE)
    below = color_box(pages[0], GREEN)
    assert above == color_box(pages[1], BLUE)
    assert below == color_box(pages[1], GREEN)
    band = Box(0, above.y1, pages[0].shape[1], below.y0)
    assert_identical_outside(pages[0], pages[1], band, what="the two states")
    from harness import difference_box

    changed = difference_box(pages[0], pages[1])
    assert changed.y1 - changed.y0 > 30, f"the replacement did not wrap: {changed}"


def test_handout_true_adds_exactly_one_page_in_its_place(paged: PagedRunner):
    """The step a later step destroys is kept, beside the final state every slide contributes."""
    animation = timeline(
        f'sub(replace("t", {colored("#00ff00", "2cm", "2cm")}))',
        f'sub(handout: true, replace("t", {colored("#0000ff", "2cm", "2cm")}))',
        'sub(remove("t"))',
    )
    source = paged.typst.source(
        deck(
            f'slide(animation: {animation})[#tag("t", {colored("#ff0000", "2cm", "2cm")})]',
            "slide[plain]",
        )
    )
    presentation = paged.png(source, mode="presentation")
    handout = paged.png(source)
    assert len(presentation) == 5
    assert len(handout) == 3
    assert_identical(handout[0], presentation[2], what="the kept page and state 2")
    assert_identical(handout[1], presentation[3], what="the final page and state 3")
    assert color_box(handout[0], BLUE) is not None
