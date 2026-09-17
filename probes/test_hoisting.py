# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Hoisting shared `<defs>`: sound in the browser, out of reach in typst*.

Every epoch frame carries its own glyph definitions, and the repeats are the larger half of
an animo page. Whether they can be dropped is two questions, and the probes here answer
both in the order the answers matter.

The browser half is the mechanism: a `<use>` resolves the first matching id in the
document, whatever inline `<svg>` that id sits in, so a page whose repeats are gone renders
as the page that carried them.

The typst half is what makes the mechanism unreachable from a package. A frame is content
until the document is encoded, and a text node is escaped, so nothing animo writes can be
markup and nothing it holds is the markup a frame became.

What is reachable is the last probe: the deduplicator is per frame, so several renderings
laid out in *one* frame share one set of definitions, and each of them is still the
labelled group the runtime addresses.
"""

import re

from harness import TypstRunner, assert_identical, drop_repeated_defs, screenshot
from htmldoc import STACK_CSS, document, stacked

# A frame with enough prose to carry a decent number of glyph definitions, laid out twice.
# The two are the same content, which is the case an epoch frame makes of a slide whose
# structural step changed one region and left the rest alone.
SENTENCE = (
    "= A heading\n\n"
    "The quick brown fox jumps over the lazy dog, and then some more prose, "
    "so that the frame carries a definition for most of the alphabet."
)

# The second frame is the one that is shown, because it is the one whose definitions the
# hoisting drops: what it renders is what an earlier frame defined.
SHOW_LAST = ".stack > svg:not(:last-child) { visibility: hidden; }\n"


def definitions(markup: str) -> list[str]:
    """The id of every deduplicated definition in the markup, in document order."""
    return re.findall(
        r'<\w+ id="([^"]+)"', "".join(re.findall(r"<defs\b[^>]*>(.*?)</defs>", markup, re.S))
    )


def test_a_use_resolves_a_definition_that_lives_in_an_earlier_frame(
    typst: TypstRunner, open_page, scratch
):
    """The whole mechanism, on real typst output, in each engine.

    The page is rendered as it comes out of typst, then again with every repeated
    definition dropped, and the two rasters are compared. The frame that is shown is the
    one that lost its definitions, so a `<use>` that did not reach out of its own `<svg>`
    would render blank glyphs and the two rasters would differ everywhere there is ink.
    """
    path = typst.html(stacked([SENTENCE, SENTENCE], SHOW_LAST))
    markup = path.read_text()
    before = screenshot(open_page(path))

    hoisted, weights = drop_repeated_defs(markup)
    assert weights["repeated_defs_bytes"] > 0, "the second frame repeated nothing to drop"
    assert len(definitions(hoisted)) == weights["distinct_defs"]
    target = scratch / "hoisted.html"
    target.write_text(hoisted)

    after = screenshot(open_page(target))
    assert_identical(before, after, what="the page and the page with its repeats dropped")


def test_dropping_the_repeats_is_what_gzip_cannot_do(typst: TypstRunner):
    """The size half of the same page, which is why the mechanism is worth anything.

    The saving is stated as a fraction rather than as a byte count, because the count is a
    property of this sentence and the fraction is the one that carries over to a deck.
    """
    markup = typst.html(stacked([SENTENCE, SENTENCE])).read_text()
    hoisted, weights = drop_repeated_defs(markup)
    assert weights["repeated_defs_bytes"] > 0.3 * len(markup.encode())
    assert len(hoisted.encode()) < 0.7 * len(markup.encode())


def test_a_frame_is_content_until_the_document_is_encoded(typst: TypstRunner):
    """Why a package cannot hoist anything itself: it never holds the markup.

    `html.frame` has one field and that field is content. The SVG is produced when the
    document is written out, by one deduplicator per frame, so there is no moment at which
    a package could read a frame's definitions or hand back a frame without them.
    """
    source = """
    #context {
      let frame = html.frame[A]
      assert.eq(frame.fields().keys(), ("body",))
      assert.eq(type(frame.fields().body), content)
    }
    """
    typst.ok(source, html=True)


def test_markup_cannot_be_written_as_text(typst: TypstRunner):
    """And the other way round: even markup a package computed could not be emitted.

    A text node is escaped, so an ordinary element cannot carry an `<svg>`.
    The two raw-text elements are the exception, which is how the stylesheet and the
    runtime reach the page, and neither of them is a place a definition can be defined in.
    """
    markup = typst.html(
        '#html.elem("div", "<svg>")\n#html.elem("style", "a > b { color: red }")\n'
    ).read_text()
    assert "<div>&lt;svg></div>" in markup
    assert "<style>a > b { color: red }</style>" in markup


def test_one_frame_defines_a_glyph_once_however_often_it_lays_it_out(typst: TypstRunner):
    """The reachable half: the deduplicator is per frame, not per rendering.

    Several renderings placed at one point in a single frame therefore carry one set of
    definitions between them, which is the hoisting that typst itself will do. Every
    reference is still written, so the count of `<use>` elements says that the renderings
    are all there.
    """
    placed = "\n".join(
        f"  place(top + left, [#box(width: 300pt, [{SENTENCE}])<animo-epoch-{i}>])"
        for i in range(3)
    )
    separate = typst.html(f"#html.frame[{SENTENCE}]\n" * 3, name="separate.html").read_text()
    merged = typst.html(
        f"#html.frame(block(width: 300pt, {{\n{placed}\n}}))\n", name="merged.html"
    ).read_text()

    assert len(set(definitions(separate))) == len(set(definitions(merged)))
    assert len(definitions(separate)) == 3 * len(definitions(merged))
    assert separate.count("xlink:href") == merged.count("xlink:href")
    assert len(merged.encode()) < 0.6 * len(separate.encode())


# The two renderings of the merged frame, as the crossfade would address them: a labelled
# box each, placed at one point, so that they overlap exactly as stacked frames do.
MERGED = """
#html.elem("div", attrs: (class: "stack"), html.frame(block(width: 120pt, height: 60pt, {
  place(top + left, [#box(width: 120pt, height: 60pt, fill: rgb("#804000"))[]<animo-epoch-0>])
  place(top + left, [#box(width: 120pt, height: 60pt, fill: rgb("#004080"))[]<animo-epoch-1>])
})))
"""


def test_a_rendering_inside_a_merged_frame_is_addressed_as_a_frame_is(
    typst: TypstRunner, open_page
):
    """And the renderings stay addressable, which is what the runtime needs of them.

    `visibility` scopes one of them away exactly as it scopes a frame away today, and
    `plus-lighter` sums the two, which on a *group* works because the two are the outermost
    groups of one frame and so are ink beside each other (see the crossfade finding).
    The sum lands on the frame's own isolated backdrop, which `STACK_CSS` writes, because a
    group's blend reaches the page in webkit 26.5 when no frame confines it.
    Measured in each engine, on the two opaque colours below.
    """
    scoped = STACK_CSS + '[data-typst-label="animo-epoch-1"] { visibility: hidden; }\n'
    page = open_page(typst.html(document(MERGED, scoped)))
    assert tuple(screenshot(page)[10, 10]) == (0x80, 0x40, 0x00)

    blended = STACK_CSS + (
        '[data-typst-label^="animo-epoch-"] { mix-blend-mode: plus-lighter; opacity: 0.5; }\n'
    )
    page = open_page(typst.html(document(MERGED, blended), name="blended.html"))
    # Half of each colour, added: the midpoint of the crossfade, with nothing dipping.
    assert tuple(screenshot(page)[10, 10]) == (0x40, 0x40, 0x40)
