# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A Discrete Keyframe Equal at Both Ends Holds Its Value for the Whole Effect*.

A crossfade holds `mix-blend-mode: plus-lighter` on the renderings it carries and
`isolation: isolate` on their container, as keyframes with the same value at both ends,
while the inline style of both elements is the value at rest.
Both properties animate discretely, so the probes ask two questions:
whether the engine computes the held value at every moment of the effect and the value at
rest once it is over, and whether it paints the held value as it paints the same value written
as style.
Whether the fade beside a held value is drawn is a question for `test_frame_drawing.py`.
"""

import io

import numpy as np
import pytest
from PIL import Image

# A dark red mark at half opacity over a dark green ground, in one inline SVG that isolates.
# A blend that reaches the ground comes back with more green in it than a plain composite,
# and an isolating container around the mark keeps the ground out of the blend.
PAGE = """<!doctype html>
<style>body { margin: 0; background: #ffffff }</style>
<svg width="200" height="100" style="isolation: isolate; display: block">
  <rect width="200" height="100" fill="#006400"/>
  <g id="container" style="isolation: auto">
    <g id="mark" style="mix-blend-mode: normal; opacity: 0.5">
      <rect x="50" y="10" width="100" height="80" fill="#800000"/>
    </g>
  </g>
</svg>
"""

# How long an effect runs, long enough that a paused one is never over by accident.
DURATION = 10000

# Each property, as the element that carries it, the value held and the value at rest.
HELD = {
    "mix-blend-mode": ("mark", "plus-lighter", "normal"),
    "isolation": ("container", "isolate", "auto"),
}

READ = """([id, name, held, duration, delay]) => {
    const element = document.getElementById(id);
    const read = () => getComputedStyle(element).getPropertyValue(name);
    const camel = name.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    const animation = element.animate(
        [{[camel]: held}, {[camel]: held}],
        {duration, delay, fill: delay > 0 ? "backwards" : "none"},
    );
    animation.pause();
    const seen = [];
    for (const moment of [0, delay / 2, delay, delay + duration / 2, delay + duration - 1]) {
        animation.currentTime = moment;
        seen.push(read());
    }
    animation.finish();
    return {during: seen, after: read()};
}"""


@pytest.mark.parametrize("name", list(HELD))
@pytest.mark.parametrize("delay", [0, DURATION], ids=["undelayed", "delayed"])
def test_a_discrete_keyframe_equal_at_both_ends_holds_for_the_whole_effect(
    page, browser_name, name, delay
):
    """The held value from the first moment to the last, and the value at rest afterwards.

    A delayed effect fills backwards, as the runtime's delayed effects do, so it holds the
    value through the delay as well.
    Measured in chromium 153, firefox 155 and webkit 26.6.
    """
    element, held, rest = HELD[name]
    page.set_content(PAGE)
    found = page.evaluate(READ, [element, name, held, DURATION, delay])
    assert found["during"] == [held] * 5, f"{browser_name} let go of the held {name}: {found}"
    assert found["after"] == rest, f"{browser_name} kept {name} after the effect: {found}"


# How the mark is set up for one raster: no setup, or the blend and the isolation written as
# style or held by a paused effect.
SETUP = """(how) => {
    const mark = document.getElementById("mark");
    const container = document.getElementById("container");
    const hold = (element, keyframe) => {
        const animation = element.animate([keyframe, keyframe], {duration: 100000});
        animation.pause();
        animation.currentTime = 50000;
    };
    if (how.blend === "style") mark.style.mixBlendMode = "plus-lighter";
    if (how.blend === "held") hold(mark, {mixBlendMode: "plus-lighter"});
    if (how.isolation === "style") container.style.isolation = "isolate";
    if (how.isolation === "held") hold(container, {isolation: "isolate"});
    return new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
}"""


def mark_pixel(browser, how: dict[str, str]) -> tuple[int, ...]:
    """The color in the middle of the mark, under the setup named, in a new page."""
    page = browser.new_page()
    try:
        page.set_content(PAGE)
        page.evaluate(SETUP, how)
        shot = page.screenshot(clip={"x": 100, "y": 50, "width": 1, "height": 1})
        return tuple(int(value) for value in np.asarray(Image.open(io.BytesIO(shot)))[0, 0, :3])
    finally:
        page.close()


def test_a_held_blend_and_isolation_paint_as_written_ones(browser, browser_name):
    """The held values paint exactly as the same values written as style.

    Two controls say that each property has an effect on this page.
    The blend sums the mark into the green ground, which a plain composite does not,
    and the isolation keeps the ground out of the sum again.
    """
    plain = mark_pixel(browser, {})
    blended = mark_pixel(browser, {"blend": "style"})
    isolated = mark_pixel(browser, {"blend": "style", "isolation": "style"})
    assert blended[1] > plain[1] + 20, f"the blend did not reach the ground: {blended}"
    assert isolated[1] < blended[1] - 20, f"the isolation did not stop the blend: {isolated}"
    assert mark_pixel(browser, {"blend": "held"}) == blended, browser_name
    assert mark_pixel(browser, {"blend": "held", "isolation": "held"}) == isolated, browser_name
