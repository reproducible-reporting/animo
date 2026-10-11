# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Read geometry out of a browser page, without the harness's deck abstraction.

A probe reports on typst and on a browser, so it queries the document directly.
`harness.Deck` addresses an animo presentation and assumes the runtime's contract,
which a probe document deliberately does not implement.

The measurement itself is the harness's, because reading the box of an SVG group is the
one piece of browser geometry that is not obvious, and a probe that read it differently
would be probing the wrong thing.
"""

from harness import MEASURE, Rect, open_local, screenshot

__all__ = ("rect", "rects", "settled_screenshot")


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


def settled_screenshot(context, path, inspect=None, **kwargs):
    """Open a document in a new page of `context` and take a screenshot of it.

    The screenshot is taken after the browser has painted two animation frames.
    Playwright's webkit 26.6 at a device scale of 2 sometimes paints a group that is drawn
    through a layer twice after a load, and a screenshot taken at once can catch the first
    raster. Measured on 2026-10-11, as 6/255 on 16 pixels in about half of the loads.
    Two animation frames later the raster is the same on every load.

    Each document gets a new page, which is closed afterwards.
    In firefox 155 under parallel load, a screenshot after a second navigation of the same
    page sometimes waited for fonts until it timed out, and a new page never did.

    Parameters
    ----------
    context
        The browser context to open the page in.
    path
        The document to open.
    inspect
        A function of the page, called before it is closed, whose result is returned beside
        the pixels.
    kwargs
        Passed on to the screenshot.

    Returns
    -------
    pixels
        The screenshot as an RGB array.
    inspected
        What `inspect` returned, or `None`.
    """
    page = context.new_page()
    try:
        open_local(page, path)
        page.evaluate(
            "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
        )
        pixels = screenshot(page, **kwargs)
        return pixels, None if inspect is None else inspect(page)
    finally:
        page.close()
