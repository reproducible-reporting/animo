# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tiers 1 and 2: explicit regions, their footprints, and what stays still around them.

A region is laid out afresh for every epoch inside a footprint that never changes.
Tier 1 asserts the footprint as actual lengths, what it costs to measure, how nested regions
compose, and which regions a content change redraws.
Tier 2 asserts the claim all of that exists for, in pixels:
everything outside a region is identical between epochs, while its inside genuinely reflows.

The content a state lays out is recognised by `metadata` markers inside it,
and the corner of a tag site by the anchor marker animo places there on paper.
"""

from decks import deck
from harness import (
    Box,
    PagedRunner,
    TypstRunner,
    assert_identical,
    assert_identical_outside,
    difference_box,
)
from test_subslides import CM, GREEN, RED, assert_close, color_box, timeline

BLUE = (0, 0, 255)

PRESENTATION = {"sysinp": {"animo": "presentation"}}

READERS = """
#import "/src/member.typ": changed-members, members-of
#import "/src/plan.typ": resolve
#let footprints(id) = (
  query(label("animo-footprint"))
    .map(it => it.value)
    .filter(it => it.at("region", default: none) == (kind: "region", id: id))
)
#let tag-footprints(name) = (
  query(label("animo-footprint"))
    .map(it => it.value)
    .filter(it => it.name == name and it.region.kind == "tag")
)
#let ys(target) = query(target).map(it => it.location().position().y)
#let corners(name) = (
  query(label("animo-site"))
    .filter(it => it.value.name == name and it.value.corner)
    .map(it => it.location().position())
)
#let close(a, b) = calc.abs(a.to-absolute() - b.to-absolute()) < 0.01pt
"""


def check(*assertions: str) -> str:
    """A context block asserting about the laid-out document."""
    body = "\n  ".join(assertions)
    return f"{READERS}\n#context {{\n  {body}\n}}\n"


def with_timeline(animation: str, *slides: str) -> str:
    """A deck whose timeline is bound to `animation`, so that the checks can resolve it too."""
    return deck(*slides).replace("#show:", f"#let animation = {animation}\n#show:", 1)


def colored(color: str, width: str, height: str) -> str:
    """A filled rectangle, which is what the pixel assertions find."""
    return f'rect(width: {width}, height: {height}, fill: rgb("{color}"))'


# The footprint, as actual lengths.


def test_a_footprint_is_the_container_width_and_the_tallest_epoch(typst: TypstRunner):
    """Three epochs of 1 cm, 3 cm and nothing reserve 3 cm at the body's width of 14 cm."""
    animation = timeline('sub(replace("t", rect(height: 3cm)))', 'sub(remove("t"))')
    body = '#region[#tag("t", rect(height: 1cm))]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "let found = footprints(1)",
        "assert.eq(found.len(), 3)",
        "for it in found {",
        "  assert(close(it.width, 14cm), message: repr(it))",
        "  assert(close(it.height, 3cm), message: repr(it))",
        "  assert.eq(it.measured.map(m => m.height), (1cm, 3cm, 0pt).map(h => h.to-absolute()))",
        "}",
    )
    typst.ok(source, **PRESENTATION)


def test_a_region_with_a_width_measures_its_epochs_at_that_width(typst: TypstRunner):
    """Text that wraps more at 4 cm than at 14 cm makes the footprint taller."""
    animation = timeline('sub(replace("t")[a replacement that wraps in a narrow region])')
    body = '#region(width: 4cm)[#tag("t", wrap: block)[short]]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "let found = footprints(1)",
        "let narrow = measure([a replacement that wraps in a narrow region], width: 4cm)",
        "assert(found.all(it => close(it.width, 4cm)), message: repr(found))",
        "assert(found.all(it => close(it.height, narrow.height)), message: repr(found))",
        "assert(narrow.height > measure([short]).height * 2)",
    )
    typst.ok(source, **PRESENTATION)


def test_a_ratio_width_is_a_ratio_of_the_container(typst: TypstRunner):
    """Half of the body's 14 cm."""
    body = '#region(width: 50%)[#tag("t")[x]]'
    source = deck(f"slide(animation: {timeline('sub(remove(\"t\"))')})[{body}]") + check(
        "assert(footprints(1).all(it => close(it.width, 7cm)))",
    )
    typst.ok(source, **PRESENTATION)


def test_explicit_sizes_override_the_measurement_and_clip(typst: TypstRunner):
    """A given height measures nothing, and a given size clips unless told otherwise."""
    animation = timeline('sub(replace("a", rect(height: 5cm)), remove("b"), remove("c"))')
    body = (
        '#region(width: 5cm, height: 2cm)[#tag("a", rect(height: 1cm))]\n'
        '#region(height: 2cm, clip: false)[#tag("b")[b]]\n'
        '#region[#tag("c")[c]]'
    )
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "let (sized, unclipped, measured) = (footprints(1), footprints(2), footprints(3))",
        "assert(sized.all(it => close(it.width, 5cm) and close(it.height, 2cm)))",
        "assert(sized.all(it => it.measured == () and it.clip))",
        "assert(unclipped.all(it => close(it.height, 2cm) and not it.clip))",
        "assert(measured.all(it => it.measured.len() == 2 and not it.clip))",
    )
    typst.ok(source, **PRESENTATION)


def test_align_places_a_smaller_state_inside_the_footprint(typst: TypstRunner):
    """At the bottom, the 1 cm state sits 2 cm lower than the 3 cm state starts."""
    animation = timeline('sub(replace("t", rect(height: 3cm)))')
    body = '#region(align: bottom)[#tag("t", wrap: block, rect(height: 1cm))]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let (short, tall) = corners("t")',
        "assert(close(short.y - tall.y, 2cm), message: repr((short, tall)))",
    )
    typst.ok(source, **PRESENTATION)


# Tags inside a region.


def test_a_tag_inside_a_region_reserves_no_footprint_of_its_own(typst: TypstRunner):
    """The region reflows around it instead."""
    animation = timeline('sub(replace("t")[longer])')
    body = '#region[Text with #tag("t")[a phrase] in it.]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'assert.eq(tag-footprints("t"), ())',
        "assert.eq(footprints(1).len(), 2)",
    )
    typst.ok(source, **PRESENTATION)


def test_removed_frees_its_space_inside_a_region_and_hidden_does_not(typst: TypstRunner):
    """What follows a removed tag sits higher until `reset` brings the tag in.

    One timeline gives the two tags their two initial states: `r` starts removed because
    `reset` is the first thing said about it, and `h` starts hidden because `reveal` is.
    """
    animation = timeline('sub(reset("r"), reveal("h"))')
    tagged = '#tag("{}", wrap: block, rect(height: 1cm))'
    body = (
        f"#region[{tagged.format('r')}\n#metadata(none)<after-r>After.]\n"
        f"#region[{tagged.format('h')}\n#metadata(none)<after-h>After.]"
    )
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "let (r0, r1) = ys(<after-r>)",
        "let (h0, h1) = ys(<after-h>)",
        "assert(r1 - r0 > 1cm, message: repr((r0, r1)))",
        "assert.eq(h0, h1)",
    )
    typst.ok(source, **PRESENTATION)


# Nesting and cost.


def test_an_outer_footprint_does_not_depend_on_an_inner_regions_state(typst: TypstRunner):
    """Footprints compose: the inner region's epochs differ, the outer region's do not."""
    long = "a replacement long enough to wrap onto several lines of the inner region " * 3
    animation = timeline(f'sub(replace("inner")[{long}])', 'sub(remove("inner"))')
    body = '#region[Outer text.\n#region[#tag("inner")[short]]\nMore outer text.]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "let outer = footprints(1).first().measured.map(it => it.height)",
        "let inner = footprints(2).first().measured.map(it => it.height)",
        "assert.eq(outer.len(), 3)",
        "assert.eq(outer.dedup().len(), 1, message: repr(outer))",
        "assert.eq(inner.dedup().len(), 3, message: repr(inner))",
    )
    typst.ok(source, **PRESENTATION)


def test_measurements_are_linear_in_epochs(typst: TypstRunner):
    """Four tags in two nested regions over three epochs: three renderings per region."""
    animation = timeline(
        'sub(replace("a")[aa], remove("b"))',
        'sub(move("a", dx: 1cm))',
        'sub(apply("c", emph), reset("d"))',
    )
    body = (
        '#region[#tag("a")[a] #tag("b")[b]\n'
        '#region[#tag("c")[c] #tag("d")[d]]]'
    )
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        "for id in (1, 2) {",
        "  let found = footprints(id)",
        "  assert.eq(found.len(), 4, message: str(id))",
        "  assert(found.all(it => it.measured.len() == 3), message: str(id))",
        "}",
    )
    typst.ok(source, **PRESENTATION)


def test_a_slide_with_one_epoch_measures_no_region(typst: TypstRunner):
    """There is nothing to choose between, so a region costs one layout of its body."""
    animation = timeline('sub(move("a", dx: 1cm))')
    body = '#region[#tag("a")[a] #region[b]]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'let found = query(label("animo-footprint")).map(it => it.value)',
        "assert.eq(found.len(), 4)",
        "assert(found.all(it => it.measured == ()))",
    )
    typst.ok(source, **PRESENTATION)


# Which regions a content change redraws.

CHANGES = timeline(
    'sub(replace("a")[A2])',
    'sub(replace("b")[B2])',
    'sub(replace("a")[A3], replace("b")[B3])',
    'sub(replace("free")[F2])',
    'sub(replace("slot")[#region[#tag("deep")[d]]])',
    'sub(replace("deep")[d2])',
)

CHANGES_BODY = (
    '#region[#tag("a")[A] #region[#tag("b")[B]]]\n'
    '#tag("free")[F]\n'
    '#tag("slot", wrap: block)[]\n'
    '#region[#tag("c")[C]]'
)

CHANGED_REGIONS = (
    "let plan = resolve(animation)",
    "let members = members-of(1)",
    "let holders(e) = changed-members(plan.epochs, e, members)",
    "let changed = range(1, 7).map(e => holders(e).map(it => it.key))",
    "let region(id) = (kind: \"region\", id: id)",
    "let implicit(name) = (kind: \"tag\", name: name)",
    "assert.eq(changed.at(0), (region(1),))",
    "assert.eq(changed.at(1), (region(2),))",
    "assert.eq(changed.at(2), (region(1),), message: \"the inner region is redrawn by the outer\")",
    'assert.eq(changed.at(3), (implicit("free"),))',
    'assert.eq(changed.at(4), (implicit("slot"),))',
)


def test_a_boundary_redraws_the_regions_that_hold_what_it_changes(typst: TypstRunner):
    """Explicit, nested, implicit, and a region inside content that changes."""
    source = with_timeline(CHANGES, f"slide(animation: animation)[{CHANGES_BODY}]") + check(
        *CHANGED_REGIONS,
        'assert.eq(changed.at(5), (implicit("slot"),), message: "a changing region has no number")',
        'let c = members.filter(it => it.name == "c").map(it => it.key).dedup()',
        'assert.eq(c, (region(3),), message: "a region inside a replacement shifted a number")',
    )
    typst.ok(source, **PRESENTATION)


def test_regions_have_the_same_numbers_in_the_html_target(typst: TypstRunner):
    """The HTML frame lays out the first epoch, which is enough for the first four boundaries."""
    source = with_timeline(CHANGES, f"slide(animation: animation)[{CHANGES_BODY}]") + check(
        *CHANGED_REGIONS,
        'let c = members.filter(it => it.name == "c").map(it => it.key).dedup()',
        "assert.eq(c, (region(3),))",
    )
    result = typst.ok(source, html=True)
    assert "converge" not in result.stderr, result.stderr


# Names, and the places a region cannot go.


def test_a_named_region_is_a_site_the_timeline_can_address(typst: TypstRunner):
    """It moves, and a pan can be relative to it, in both targets."""
    animation = timeline('sub(move("r", dx: 1cm), pan(relto: "r"))', 'sub(replace("t")[longer])')
    body = 'Above.\n#region(name: "r")[#tag("t")[short]]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'assert.eq(query(<r>).len(), 3)',
        # The outer slot holds the anchor, the footprint report and then the display state.
        "assert.eq(query(<r>).map(it => it.body.children.last().dx), (0pt, 1cm, 1cm))",
    )
    typst.ok(source, **PRESENTATION)
    typst.ok(deck(f"slide(animation: {animation})[{body}]"), html=True)


def test_a_region_outside_a_slide_is_refused(typst: TypstRunner):
    """The diagnosis names the region."""
    typst.fails(deck("slide[x]") + '#region(name: "lost")[x]', "the region lost is not inside a #slide")


def test_a_region_around_something_that_is_not_content_is_refused(typst: TypstRunner):
    """Such as a stream of draw commands, which belongs inside a canvas."""
    typst.fails(deck("slide[#region(((x: 1),))]"), "is not content")


def test_a_structural_step_on_a_region_name_is_refused(typst: TypstRunner):
    """A region's name is for the continuous primitives; its content is changed through tags."""
    animation = timeline('sub(replace("r")[new])')
    typst.fails(
        deck(f'slide(animation: {animation})[#region(name: "r")[old]]'), "names a region"
    )


def test_region_arguments_are_checked(typst: TypstRunner):
    """Each mistake gets a message that names the argument."""
    typst.fails(deck('slide[#region(width: "wide")[x]]'), "takes auto or a length")
    typst.fails(deck('slide[#region(align: "top")[x]]'), "takes an alignment")
    typst.fails(deck("slide[#region(clip: 1)[x]]"), "takes auto, true or false")
    typst.fails(deck("slide[#region(name: 1)[x]]"), "takes its name as a string")


def test_a_region_measured_without_a_width_takes_its_natural_size(typst: TypstRunner):
    """A tag around a region measures it unbounded to decide its wrapper, and that works."""
    animation = timeline('sub(replace("t")[longer content])')
    body = '#tag("outer")[#region[#tag("t")[short]]]'
    source = deck(f"slide(animation: {animation})[{body}]") + check(
        'assert.eq(query(<outer>).first().func(), block)',
    )
    typst.ok(source, **PRESENTATION)


# Tier 2: the pages.


def test_nothing_outside_a_region_changes_while_its_inside_reflows(paged: PagedRunner):
    """A replacement that wraps pushes the red mark down, and nothing moves outside the band."""
    long = "A replacement long enough to wrap onto a second and a third line of the slide. " * 2
    animation = timeline(f'sub(replace("t")[{long}])', 'sub(remove("t"))')
    body = (
        f"#{colored('#0000ff', '2cm', '5mm')}\n"
        f'#region[#tag("t", wrap: block)[A short paragraph.]\n#{colored("#ff0000", "2cm", "5mm")}]\n'
        f"#{colored('#00ff00', '2cm', '5mm')}\n"
        "A paragraph after the region."
    )
    pages = paged.png(deck(f"slide(animation: {animation})[{body}]"), mode="presentation")
    assert len(pages) == 3
    above, below = color_box(pages[0], BLUE), color_box(pages[0], GREEN)
    band = Box(0, above.y1, pages[0].shape[1], below.y0)
    for state, page in enumerate(pages[1:], start=1):
        assert color_box(page, BLUE) == above, f"state {state}"
        assert color_box(page, GREEN) == below, f"state {state}"
        assert_identical_outside(pages[0], page, band, what=f"states 0 and {state}")
    reds = [color_box(page, RED).y0 for page in pages]
    # One more line of text is about 15 points, which is 15 pixels here.
    assert reds[1] - reds[0] > 10, f"the replacement did not push the region's inside down: {reds}"
    assert reds[2] < reds[0], f"the removal did not free the tag's space: {reds}"


def test_a_nested_region_redraws_only_its_own_band(paged: PagedRunner):
    """The outer region's own content after the inner region holds still."""
    long = "An inner replacement that wraps onto more lines than the short one does. " * 2
    animation = timeline(f'sub(replace("t")[{long}])')
    body = (
        "#region[Outer text.\n"
        f"#{colored('#0000ff', '2cm', '5mm')}\n"
        '#region[#tag("t", wrap: block)[Short.]]\n'
        f"#{colored('#ff0000', '2cm', '5mm')}\n"
        "More outer text.]"
    )
    pages = paged.png(deck(f"slide(animation: {animation})[{body}]"), mode="presentation")
    above, below = color_box(pages[0], BLUE), color_box(pages[0], RED)
    assert color_box(pages[1], RED) == below
    band = Box(0, above.y1, pages[0].shape[1], below.y0)
    assert_identical_outside(pages[0], pages[1], band, what="the two states")
    changed = difference_box(pages[0], pages[1])
    assert changed is not None and changed.y1 - changed.y0 > 20, f"nothing reflowed: {changed}"


def test_a_region_with_a_height_clips_what_does_not_fit(paged: PagedRunner):
    """A 3 cm rectangle in a 1 cm region shows 1 cm of itself, unless clipping is off."""
    red = colored("#ff0000", "2cm", "3cm")
    heights = []
    for clip in ("auto", "false"):
        pages = paged.png(deck(f"slide[#region(height: 1cm, clip: {clip})[#{red}]]"))
        found = color_box(pages[0], RED)
        heights.append(found.y1 - found.y0)
    assert_close(heights[0], CM, "the clipped height")
    assert_close(heights[1], 3 * CM, "the unclipped height")


def test_a_named_region_moves_as_a_whole(paged: PagedRunner):
    """The footprint and everything in it, a centimetre to the right."""
    animation = timeline('sub(move("r", dx: 1cm))')
    body = f'#region(name: "r")[#{colored("#ff0000", "2cm", "1cm")}]'
    pages = paged.png(deck(f"slide(animation: {animation})[{body}]"), mode="presentation")
    first, second = color_box(pages[0], RED), color_box(pages[1], RED)
    assert_close(second.x0 - first.x0, CM, "the move")
    assert second.y0 == first.y0


def test_a_region_lays_out_as_its_body_when_nothing_changes(paged: PagedRunner):
    """Paragraphs under a centred alignment, with and without a region around them."""
    content = "#set align(center)\nA first paragraph.\n\nA second, which is longer than the first."
    plain = paged.png(deck(f"slide[{content}]"))
    wrapped = paged.png(deck(f"slide[#region[{content}]]"))
    assert_identical(plain[0], wrapped[0], what="the body with and without a region")
