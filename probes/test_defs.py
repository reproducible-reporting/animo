# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *SVG `<defs>` ids are content hashes*.

Relevant because stacking several epoch frames in one document puts duplicate ids
in one DOM, and a browser resolves `<use xlink:href="#g..">` to the first match.
That is harmless only as long as equal ids always mean equal content.

The last probe here is about `gzip` rather than about typst, and it belongs beside these
because it is what decides whether the redundancy the others describe costs anything on
the wire. It does: a deck is served compressed, and the repetition survives compression.
"""

import gzip
import os
import re
from base64 import b64encode

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


# What the redundancy costs on the wire.

# Deflate's sliding window, which no `zlib` setting raises: a repeat further back than this
# cannot be encoded as a back-reference and is stored again in full.
WINDOW = 32 * 1024


def compressed(text: str) -> int:
    """How many bytes `gzip` takes this text to, at its highest setting."""
    return len(gzip.compress(text.encode(), 9))


def incompressible(size: int) -> str:
    """Text with no structure of its own, so that only repetition can compress it."""
    return b64encode(os.urandom(size * 3 // 4)).decode()[:size]


def test_gzip_deduplicates_a_repeat_inside_its_window():
    """The control: within the window a second copy is nearly free."""
    chunk = incompressible(WINDOW // 3)
    assert compressed(chunk + chunk) < 1.1 * compressed(chunk)


def test_gzip_does_not_deduplicate_a_repeat_beyond_its_window():
    """The claim: past the window, the same bytes are stored a second time in full.

    The filler compresses to nothing, so it adds no bytes of its own,
    and what is left in the difference is the distance between the two copies.
    """
    chunk = incompressible(WINDOW // 3)
    filler = "ab" * WINDOW
    assert compressed(filler) < 1024, "the filler was supposed to compress to nothing"
    assert compressed(chunk + filler + chunk) > 1.9 * compressed(chunk)


def test_an_epoch_frame_is_larger_than_the_gzip_window(typst: TypstRunner):
    """Which puts the duplication across epoch frames out of gzip's reach entirely.

    A definition repeated in the next frame is further back than the window whatever sits
    between the two, so whether compression recovers the redundancy is decided by the size
    of one frame and not by the shape of the deck.
    It is not close: a frame carrying a heading and one sentence already clears the window,
    and a frame carrying a whole slide clears it several times over.

    This is the step from *equal ids mean equal content* to *compression does not recover
    it*, and it is measured on real output rather than reasoned about.
    """
    body = "#html.frame[= A heading\n\nThe quick brown fox jumps over the lazy dog.]\n"
    markup = typst.html(body).read_text()
    frame = re.search(r"<svg\b.*?</svg>", markup, re.S)
    assert frame is not None, "no frame in the output at all"
    assert len(frame.group(0).encode()) > WINDOW
