# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Read the deduplicated definitions of an HTML page, and drop the ones that repeat.

Typst's definition ids are content hashes, so an id that occurs in two frames is one
definition twice, and a browser resolves `<use>` to the first match in the document.
Dropping every repeat therefore leaves a page that renders identically and is smaller,
which is what both consumers of this module ask about:
a probe loads the result in three engines, and the benchmark weighs it.
"""

import re

__all__ = ("drop_repeated_defs",)

DEFS = re.compile(r"<defs\b[^>]*>(.*?)</defs>", re.S)
"""One `<defs>` block, with its children as the first group."""

DEFINITION = re.compile(r'<\w+ id="([^"]+)"')
"""The opening tag of one definition, with its id as the first group."""


def drop_repeated_defs(markup: str) -> tuple[str, dict]:
    """Drop every definition whose id an earlier one already carried.

    Parameters
    ----------
    markup
        A page, a fragment of one, or a single frame.
        Whatever is handed in is one deduplication scope,
        which is how a caller asks what a narrower scope would save.

    Returns
    -------
    deduplicated
        The same markup with the repeated definitions removed and nothing else touched.
    weights
        The bytes inside `<defs>`, the bytes of the definitions that repeated, and how
        many distinct ones are left.
    """
    inside = 0
    repeated = 0
    seen = set()
    pieces = []
    end = 0
    for block in DEFS.finditer(markup):
        inside += len(block.group(1).encode())
        pieces.append(markup[end : block.start(1)])
        kept = []
        # The children of `<defs>` are a flat sequence of elements that each open with
        # their own id, so splitting before every such opening tag cuts the block into
        # exactly one chunk per definition, whatever the element kinds turn out to be.
        for chunk in re.split(r'(?=<\w+ id=")', block.group(1)):
            found = DEFINITION.match(chunk)
            if found is None:
                kept.append(chunk)
            elif found.group(1) in seen:
                repeated += len(chunk.encode())
            else:
                seen.add(found.group(1))
                kept.append(chunk)
        pieces.append("".join(kept))
        end = block.end(1)
    pieces.append(markup[end:])
    weights = {
        "defs_bytes": inside,
        "repeated_defs_bytes": repeated,
        "distinct_defs": len(seen),
    }
    return "".join(pieces), weights
