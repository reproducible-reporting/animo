# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the HTML output, in the chromium that `playwright` bundles.

The bundled browser is what keeps the pixels identical on every machine,
so `setup.sh` downloads it into `.venv/` and a missing one is an error rather than a skip:
a suite that is green because a third of it never ran is worse than a red one.

Geometry comes from `page.evaluate` and is preferred over pixels wherever it can say the same
thing, because a number survives a glyph rasterisation change and a screenshot does not.
Images come from `locator.screenshot(animations="disabled")`.
"""

from pathlib import Path

import attrs
import numpy as np
from playwright.sync_api import Locator, Page

from .raster import decode

__all__ = ("Deck", "Rect", "open_local", "screenshot", "state_hash")


@attrs.frozen
class Rect:
    """A `getBoundingClientRect`, in CSS pixels."""

    x: float = attrs.field()
    y: float = attrs.field()
    width: float = attrs.field()
    height: float = attrs.field()

    @property
    def center(self) -> tuple[float, float]:
        """The centre of the rectangle.

        Centres are what a transform about `transform-origin: center` leaves invariant,
        so they compare between two renderings where corners and extents do not.
        """
        return (self.x + self.width / 2, self.y + self.height / 2)

    def approx(self, other: Rect, tol: float = 0.01) -> bool:
        """Whether two rectangles agree to within `tol` CSS pixels on every number."""
        return all(
            abs(getattr(self, name) - getattr(other, name)) <= tol
            for name in ("x", "y", "width", "height")
        )


def screenshot(target: Page | Locator, **kwargs) -> np.ndarray:
    """Take a PNG screenshot and decode it into an RGB array.

    Animations are disabled, so a screenshot is taken at a defined moment
    rather than at whatever point a transition happened to have reached.
    PNG rather than WebP: `playwright`'s own `type="webp"` is lossy.
    """
    kwargs.setdefault("animations", "disabled")
    return decode(target.screenshot(type="png", **kwargs))


def state_hash(slide: int, state: int = 0) -> str:
    """The URL fragment that addresses one subslide state of one slide.

    This is the single place that spells the format out.
    The runtime of phase 05 has to agree with it, and the whole of tier 3 deep-links
    through it rather than clicking its way to a state.

    Slides are counted from one and states from zero,
    because state 0 of a slide is the slide exactly as its body declares it.
    """
    return f"#{slide}.{state}"


@attrs.frozen
class Deck:
    """An animo HTML presentation, open in a browser page.

    The contract with the runtime, which phase 05 implements, is three lines long:

    - the current position lives in `location.hash` as `#<slide>.<state>`,
      is restored on load and followed on `hashchange`, and the restore *snaps*
      rather than animating into the state;
    - the position the runtime has actually reached is mirrored in the
      `data-animo` attribute of the root element, so that a test can wait for the snap
      instead of racing it;
    - every slide container carries `data-animo-slide="<slide>"`, which is what scopes
      a tag name to one slide, in the tests as in the runtime's own CSS.

    Until that runtime exists, the harness is exercised against a stand-in document
    that implements exactly these three lines.
    """

    page: Page = attrs.field()
    """The browser page the deck is open in."""

    def goto(self, slide: int, state: int = 0, timeout: float = 5000) -> Deck:
        """Deep-link to one subslide state and wait until the runtime has snapped to it."""
        target = state_hash(slide, state)
        self.page.evaluate("hash => { location.hash = hash }", target)
        self.page.wait_for_function(
            "expected => document.documentElement.dataset.animo === expected",
            arg=target.removeprefix("#"),
            timeout=timeout,
        )
        return self

    @property
    def position(self) -> tuple[int, int]:
        """The slide and state the runtime is currently showing."""
        value = self.page.evaluate("() => document.documentElement.dataset.animo")
        slide, state = value.split(".")
        return int(slide), int(state)

    def rects(self, label: str, frame: int | None = None) -> list[Rect]:
        """The bounding boxes of every group carrying this tag, in document order.

        The search is scoped to the slide the runtime is currently showing,
        because a tag name means nothing outside its own slide.
        One tag may sit at several places in that slide and appears in every epoch frame,
        so this returns a list and never a single rectangle.
        `frame` restricts the search to the n-th epoch frame of the slide.
        """
        slide, _ = self.position
        scope = f"document.querySelector('[data-animo-slide=\"{slide}\"]')"
        if frame is not None:
            scope = f"{scope}.querySelectorAll('svg')[{frame}]"
        selector = f'[data-typst-label="{label}"]'
        boxes = self.page.evaluate(
            f"""() => Array.from(
                {scope}.querySelectorAll({selector!r}),
                node => {{
                    const r = node.getBoundingClientRect();
                    return {{x: r.x, y: r.y, width: r.width, height: r.height}};
                }},
            )"""
        )
        return [Rect(**box) for box in boxes]

    def screenshot(self, **kwargs) -> np.ndarray:
        """A screenshot of the whole page, as an RGB array."""
        return screenshot(self.page, **kwargs)


def open_local(page: Page, path: Path) -> Page:
    """Open a file from the working tree, which is how every compiled deck is loaded."""
    page.goto(path.resolve().as_uri())
    return page
