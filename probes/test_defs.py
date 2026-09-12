# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *SVG `<defs>` ids are content hashes*.

Relevant because stacking several epoch frames in one document puts duplicate ids
in one DOM, and a browser resolves `<use xlink:href="#g..">` to the first match.
That is harmless only as long as equal ids always mean equal content.
"""

import re

from harness import TypstRunner

PAGE = "#set page(width: 200pt, height: 100pt, margin: 10pt)\n"


def def_ids(markup: str) -> list[str]:
    """Every deduplicated definition id in the markup, in document order."""
    return re.findall(r'id="([A-Za-z][0-9A-F]+)"', markup)


def test_a_definition_id_is_a_kind_character_and_a_hash(typst: TypstRunner):
    """The `Deduplicator` in `typst-svg` writes a kind character and a 128-bit hash."""
    ids = def_ids(typst.svg(PAGE + "AA\n"))
    assert ids, "no deduplicated definitions in the output at all"
    for name in ids:
        assert re.fullmatch(r"[a-zA-Z][0-9A-F]{32}", name), name


def test_equal_content_gets_one_definition_and_two_references(typst: TypstRunner):
    """Two occurrences of the same glyph share a definition, which is what dedup means."""
    markup = typst.svg(PAGE + "AA\n")
    assert len(def_ids(markup)) == 1
    assert markup.count(f'xlink:href="#{def_ids(markup)[0]}"') == 2


def test_equal_content_in_two_frames_gets_the_same_id(typst: TypstRunner):
    """The case that matters: stacked epoch frames in one document.

    The duplication is therefore pure redundancy,
    which is also what makes hoisting shared defs sound as a later optimisation.
    """
    markup = typst.html("#html.frame[A]\n#html.frame[A]\n#html.frame[B]\n").read_text()
    ids = def_ids(markup)
    assert len(ids) == 3
    assert ids[0] == ids[1], "the same glyph in two frames got two different ids"
    assert ids[2] != ids[0], "two different glyphs got the same id"
