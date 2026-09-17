# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Read geometry out of a browser page, without the harness's deck abstraction.

A probe reports on typst and on a browser, so it queries the document directly.
`harness.Deck` addresses an animo presentation and assumes the runtime's contract,
which a probe document deliberately does not implement.

The measurement itself is the harness's, because reading the box of an SVG group is the
one piece of browser geometry that is not obvious, and a probe that read it its own way
would be probing the wrong thing.
"""

from harness import MEASURE, Rect

__all__ = ("rect", "rects")


def rects(page, selector: str) -> list[Rect]:
    """The bounding boxes of every element matching the selector, in document order."""
    found = page.evaluate(
        f"() => Array.from(document.querySelectorAll({selector!r}), {MEASURE})",
    )
    return [Rect(**box) for box in found]


def rect(page, selector: str) -> Rect:
    """The bounding box of the first element matching the selector."""
    found = rects(page, selector)
    if not found:
        raise AssertionError(f"nothing matches {selector!r}")
    return found[0]
