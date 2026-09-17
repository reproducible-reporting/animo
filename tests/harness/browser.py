# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the HTML output, in the browsers that `playwright` bundles.

Every test here runs in each engine of `fixtures.ENGINES`, because a deck that only works
in one of them is not a presentation format.
The bundled browsers are what keep the pixels identical on every machine,
so `setup.sh` downloads them into `.venv/` and a missing one is an error rather than a skip:
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

__all__ = ("MEASURE", "Deck", "Rect", "open_local", "screenshot", "state_hash")


EPOCH_GROUPS = '.animo-canvas [data-typst-label^="animo-epoch-"]'
"""The epoch renderings of a slide, which are groups inside the slide's single frame.

Animo lays the epochs of a slide out in one `html.frame`, so that typst's deduplicator,
whose scope is the frame, defines each glyph they share once between them. A rendering is
therefore a labelled group and not an `<svg>` of its own.
"""

# How the geometry of an SVG group is read, as a `playwright` argument expression.
#
# `getBBox()` gives the box in the group's own user units, which are typst points, and
# `getScreenCTM()` maps that onto the page, so the result is in CSS pixels either way.
# `getBoundingClientRect()` cannot be used on a group: firefox 153 inflates it to roughly
# the width of the whole frame where chromium returns the tight box. See *Findings*.
# All four corners are mapped, so the box stays right under a matrix that rotates.
MEASURE = """node => {
    if (typeof node.getBBox !== "function") {
        // Not an SVG graphics element, so there is no user space to map out of and
        // no disagreement between the engines to avoid.
        const r = node.getBoundingClientRect();
        return {x: r.x, y: r.y, width: r.width, height: r.height};
    }
    const box = node.getBBox();
    const m = node.getScreenCTM();
    const corners = [
        [box.x, box.y],
        [box.x + box.width, box.y],
        [box.x, box.y + box.height],
        [box.x + box.width, box.y + box.height],
    ];
    const xs = corners.map(([x, y]) => m.a * x + m.c * y + m.e);
    const ys = corners.map(([x, y]) => m.b * x + m.d * y + m.f);
    const x = Math.min(...xs);
    const y = Math.min(...ys);
    return {x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y};
}"""


@attrs.frozen
class Rect:
    """The box of an SVG group on the page, in CSS pixels.

    Measured with `MEASURE`, not with `getBoundingClientRect`.
    """

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

    This is the single place that spells the format out,
    and the whole of tier 3 deep-links through it rather than clicking its way to a state.
    The fragment is the position and nothing else: a paused deck is not addressable,
    which is what the runtime's `data-animo-paused` attribute exists for instead.

    Slides are counted from one and states from zero,
    because state 0 of a slide is the slide exactly as its body declares it.
    """
    return f"#{slide}.{state}"


@attrs.frozen
class Deck:
    """An animo HTML presentation, open in a browser page.

    The contract with the runtime is five lines long:

    - the current position lives in `location.hash` as `#<slide>.<state>`,
      is restored on load and followed on `hashchange`, and the restore *snaps*
      rather than animating into the state;
    - the position the runtime has actually reached is mirrored in the
      `data-animo` attribute of the root element, so that a test can wait for the snap
      instead of racing it;
    - every slide container carries `data-animo-slide="<slide>"`, which is what scopes
      a tag name to one slide, in the tests as in the runtime's own CSS;
    - that container also carries the resolved plan, as JSON, in `data-animo-plan`;
    - the root element carries `data-animo-paused` while the deck's own clock is stopped,
      which is the one thing the runtime knows that the fragment does not carry.

    The first three are also what `tests/documents/stand_in_deck.html` implements,
    which is what the harness's own tests are exercised against.
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
    def paused(self) -> bool:
        """Whether the runtime's clock is stopped, as the root element publishes it.

        A pause is the one thing the runtime knows that the fragment does not carry,
        so it is read here rather than off the URL.
        """
        return self.page.evaluate(
            "() => document.documentElement.hasAttribute('data-animo-paused')"
        )

    def run_for(self, milliseconds: float) -> Deck:
        """Let that much time pass for the page's timers, and fire the ones that are due.

        Only meaningful on a page whose clock was stopped before it was loaded, which is
        what the `timed_deck_at` fixture does. A `wait:` is a `setTimeout` in the runtime,
        and a `setTimeout` is exactly what the animation harness cannot scrub, so a timed
        step is driven rather than raced. The document timeline is untouched by this, so
        the motion a step starts still runs in real time and is still scrubbable.
        """
        self.page.clock.run_for(milliseconds)
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
        One tag may sit at several places in that slide and appears in every epoch
        rendering, so this returns a list and never a single rectangle.
        `frame` restricts the search to the n-th epoch rendering of the slide.
        """
        slide, _ = self.position
        scope = f"document.querySelector('[data-animo-slide=\"{slide}\"]')"
        if frame is not None:
            scope = f"{scope}.querySelectorAll({EPOCH_GROUPS!r})[{frame}]"
        selector = f'[data-typst-label="{label}"]'
        boxes = self.page.evaluate(
            f"""() => Array.from(
                {scope}.querySelectorAll({selector!r}),
                {MEASURE},
            )"""
        )
        return [Rect(**box) for box in boxes]

    @property
    def current(self) -> Locator:
        """The container of the slide being shown, which is exactly the viewport.

        Screenshotting this rather than the page leaves out the surround the deck centres
        the slide on, so a comparison is about the slide and not about its letterbox.
        """
        return self.page.locator(".animo-slide[data-animo-current]")

    @property
    def frames(self) -> Locator:
        """The epoch renderings of the slide being shown, in epoch order.

        One rendering per content state of the slide, placed at one point in the slide's
        single frame, which is what a structural step steps between.
        """
        slide, _ = self.position
        return self.page.locator(f'[data-animo-slide="{slide}"] {EPOCH_GROUPS}')

    @property
    def canvas_frames(self) -> int:
        """How many `html.frame` renderings the canvas of the slide being shown holds.

        One, whatever the epochs: the renderings are groups inside it. This is the count
        the page weight follows, since typst defines a glyph once per frame that uses it.
        """
        slide, _ = self.position
        return self.page.locator(f'[data-animo-slide="{slide}"] > .animo-canvas > svg').count()

    @property
    def painting(self) -> list[bool]:
        """Which epoch renderings of the slide being shown contribute ink, in epoch order.

        A rendering that is not the current epoch's is hidden rather than taken away, so
        that it stays laid out and its geometry readable while contributing nothing.
        A boundary that hands the whole rendering over fades it instead, and leaves it
        visible at zero until the next boundary, so the opacity is read as well.
        """
        slide, _ = self.position
        return self.page.evaluate(
            f"""() => Array.from(
                document.querySelectorAll('[data-animo-slide="{slide}"] {EPOCH_GROUPS}'),
                node => {{
                    const style = getComputedStyle(node);
                    return style.visibility === "visible" && Number(style.opacity) > 0;
                }},
            )"""
        )

    def styles(self, label: str) -> list[dict[str, str]]:
        """The three properties the runtime writes, per occurrence of a tag.

        They are read from the inner group, which is the continuous slot,
        and computed rather than inline, so a value an animation is currently
        driving is the one that comes back.
        """
        slide, _ = self.position
        return self.page.evaluate(
            f"""() => Array.from(
                document.querySelectorAll(
                    '[data-animo-slide="{slide}"] [data-typst-label="{label}"] > g'
                ),
                node => {{
                    const computed = getComputedStyle(node);
                    return {{
                        opacity: computed.opacity,
                        translate: computed.translate,
                        scale: computed.scale,
                    }};
                }},
            )"""
        )

    @property
    def plan(self) -> dict:
        """The resolved plan the slide being shown carries, as the runtime reads it."""
        slide, _ = self.position
        return self.page.evaluate(
            f"""() => JSON.parse(
                document.querySelector('[data-animo-slide="{slide}"]').dataset.animoPlan
            )"""
        )

    @property
    def unit(self) -> float:
        """CSS pixels per typst point, on the slide being shown.

        A length animo writes inside a frame is a user unit of that frame's SVG,
        which is a typst point, so this is what turns a length in the source into the
        displacement a test can assert, at whatever size the window happens to be.
        """
        slide, _ = self.position
        return self.page.evaluate(
            f"""() => {{
                const svg = document.querySelector(
                    '[data-animo-slide="{slide}"] > .animo-canvas > svg'
                );
                return svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
            }}"""
        )

    @property
    def pan(self) -> tuple[float, float]:
        """How far the viewport has panned over the canvas, in typst points.

        Read off the geometry rather than off the `translate` the runtime wrote,
        because a computed percentage is spelled differently by each engine
        while a box on the page is a number in all of them.
        """
        slide, _ = self.position
        x, y = self.page.evaluate(
            f"""() => {{
                const slide = document.querySelector('[data-animo-slide="{slide}"]');
                const canvas = slide.querySelector(':scope > .animo-canvas');
                const outer = slide.getBoundingClientRect();
                const inner = canvas.getBoundingClientRect();
                return [outer.x - inner.x, outer.y - inner.y];
            }}"""
        )
        return x / self.unit, y / self.unit

    @property
    def subslides(self) -> list[float]:
        """How opaque the rendering of each state is, in the stacks of the slide shown.

        A `per-subslide` lays its callback out once per state and labels every rendering
        with the state it belongs to, and the runtime shows the one the deck is on.
        One slide may carry several stacks, and every rendering of a state is shown or
        hidden together, so this reports one number per state and asserts they agree.
        """
        slide, _ = self.position
        opacities = self.page.evaluate(
            f"""() => {{
                const found = [];
                const groups = document.querySelectorAll(
                    '[data-animo-slide="{slide}"] [data-typst-label^="animo-subslide-"]'
                );
                for (const group of groups) {{
                    const state = Number(
                        group.dataset.typstLabel.slice("animo-subslide-".length)
                    );
                    (found[state] ??= []).push(Number(getComputedStyle(group).opacity));
                }}
                return found;
            }}"""
        )
        for state, values in enumerate(opacities):
            assert len(set(values)) == 1, f"the renderings of subslide {state} disagree"
        return [values[0] for values in opacities]

    def press(self, key: str, times: int = 1) -> Deck:
        """Press a key, which is how a presenter steps through the deck."""
        for _ in range(times):
            self.page.keyboard.press(key)
        return self

    @property
    def animating(self) -> list[set[str]]:
        """The properties each animation now in flight is driving, one set per animation.

        What a step animates is not the same question as what it changes: a property that
        holds still in the keyframes is invisible in every state and still costs the step
        its motion in chromium 151. See *Findings*.
        """
        timing = ("offset", "computedOffset", "easing", "composite")
        return [
            set(names)
            for names in self.page.evaluate(
                """timing => document.getAnimations().map((animation) => {
                    const properties = new Set();
                    for (const frame of animation.effect.getKeyframes()) {
                        for (const name of Object.keys(frame)) {
                            if (!timing.includes(name)) {
                                properties.add(name);
                            }
                        }
                    }
                    return [...properties];
                })""",
                timing,
            )
        ]

    @property
    def flight(self) -> list[float]:
        """How far into the step each animation now in flight is, in milliseconds.

        Read after a frame has been drawn, because an animation measures its own current
        time against the document timeline and not against real time, and firefox 153
        refreshes that timeline only when it draws. Read any sooner and an animation that
        was told it began long ago still reports zero. See *Findings*.
        """
        return self.page.evaluate(
            """async () => {
                await new Promise((done) =>
                    requestAnimationFrame(() => requestAnimationFrame(done)));
                return document.getAnimations().map((animation) => animation.currentTime);
            }"""
        )

    def settle(self, timeout: float = 5000) -> Deck:
        """Wait until nothing is in flight any more.

        A step animates, so a test that asserts about the state it lands in has to wait
        for the motion to end rather than measure halfway through it.
        """
        self.page.wait_for_function("() => document.getAnimations().length === 0", timeout=timeout)
        return self

    def scrub(self, moment: float) -> Deck:
        """Pause everything in flight at one moment of the transition, in milliseconds.

        This is what makes a mid-flight assertion reproducible:
        the test states the moment instead of racing the animation to it.
        """
        self.page.evaluate(
            """moment => {
                for (const animation of document.getAnimations()) {
                    animation.pause();
                    animation.currentTime = moment;
                }
            }""",
            moment,
        )
        return self

    def screenshot(self, **kwargs) -> np.ndarray:
        """A screenshot of the whole page, as an RGB array."""
        return screenshot(self.page, **kwargs)


def open_local(page: Page, path: Path) -> Page:
    """Open a file from the working tree, which is how every compiled deck is loaded."""
    page.goto(path.resolve().as_uri())
    return page
