# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Read geometry out of a browser page, without the harness's deck abstraction.

A probe reports on typst and on chromium, so it queries the document directly.
`harness.Deck` addresses an animo presentation and assumes the runtime's contract,
which a probe document deliberately does not implement.
"""

from harness import Rect

__all__ = ("rect", "rects")

_READ = """node => {
    const r = node.getBoundingClientRect();
    return {x: r.x, y: r.y, width: r.width, height: r.height};
}"""


def rects(page, selector: str) -> list[Rect]:
    """The bounding boxes of every element matching the selector, in document order."""
    found = page.evaluate(
        f"() => Array.from(document.querySelectorAll({selector!r}), {_READ})",
    )
    return [Rect(**box) for box in found]


def rect(page, selector: str) -> Rect:
    """The bounding box of the first element matching the selector."""
    found = rects(page, selector)
    if not found:
        raise AssertionError(f"nothing matches {selector!r}")
    return found[0]
