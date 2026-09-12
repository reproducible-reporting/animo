# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *A keyframe property that does not change suppresses the ones that do*.

An effect that animates `opacity` alongside a `translate` or a `scale` holding the same
value at both ends is not drawn while it runs in chromium 151: the element stays as it was
and appears in one frame at the end. Every value the animation computes is correct
throughout, so nothing in the DOM shows this and only the drawing is missing.

That is also why these probes record a video instead of taking screenshots. A screenshot
repaints the page, which is exactly what the failure needs to disappear, so it reports a
flawless fade in both the affected and the unaffected case. A recorded video is the frames
the browser drew of its own accord.
"""

import subprocess
from pathlib import Path

import numpy as np
import pytest
from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image

# A single black square in an SVG group, which is the shape of a tag's continuous slot.
PAGE = """<!doctype html>
<style>body { margin: 0; background: #fff }</style>
<svg width="300" height="120">
  <g id="target" style="opacity: 0"><rect x="0" y="0" width="200" height="80"/></g>
</svg>
"""

# How long the animation runs. Video is recorded at 25 frames per second, so this is
# twenty frames to find intermediate values in, and losing a few of them changes nothing.
DURATION = 800

# How many frames strictly between the two end states count as "drawn".
# The claim is roughly twenty frames against none, so the line sits far from both ends.
# It is not exactly zero on the suppressed side, because anything that makes the page draw
# brings one frame of the fade back, and a machine running the rest of the suite beside
# this occasionally does, which is the same sensitivity the finding is about.
DRAWN = 4

# Whether an engine draws an effect that carries a property equal at both ends, measured
# on chromium 151 and firefox 153. Webkit has no row because it cannot be launched on the
# machine this was measured on: either behaviour passes below until someone fills it in.
DRAWS_A_STANDING_PROPERTY = {"chromium": False, "firefox": True, "webkit": None}


def intermediate(browser, folder: Path, keyframes: list[dict[str, str]]) -> int:
    """Record one animation and count the frames drawn between its two end states."""
    page_path = folder / "page.html"
    page_path.write_text(PAGE)
    context = browser.new_context(
        viewport={"width": 300, "height": 120},
        record_video_dir=str(folder),
        record_video_size={"width": 300, "height": 120},
    )
    page = context.new_page()
    page.goto(page_path.as_uri())
    page.wait_for_timeout(500)
    # The end state is written as style before the animation starts, as the runtime writes
    # it, so the element is visible once the step is over whether or not it was drawn
    # during the step. That is what makes "never drawn" and "drawn throughout" tell apart.
    page.evaluate(
        """([frames, duration]) => {
            const target = document.getElementById("target");
            Object.assign(target.style, frames[frames.length - 1]);
            target.animate(frames, {duration, easing: "linear", fill: "none"});
        }""",
        [keyframes, DURATION],
    )
    page.wait_for_timeout(DURATION + 700)
    video = page.video.path()
    context.close()

    images = folder / "frames"
    images.mkdir()
    subprocess.run(
        [get_ffmpeg_exe(), "-loglevel", "error", "-i", video, "-vsync", "0",
         str(images / "f%04d.png")],
        check=True,
    )
    ink = [
        float(255 - np.asarray(Image.open(frame).convert("L")).mean())
        for frame in sorted(images.glob("*.png"))
    ]
    assert ink, "the recording holds no frames at all"
    span = max(ink) - min(ink)
    assert span > 1, "the element looks the same at both ends, so nothing can be counted"
    return len([value for value in ink if min(ink) + 0.05 * span < value < max(ink) - 0.05 * span])


def test_an_effect_whose_properties_all_change_is_drawn_while_it_runs(browser, tmp_path):
    """The control, without which the probe below would be about video recording.

    Every engine draws a plain fade, and the recording is able to see it.
    """
    count = intermediate(browser, tmp_path, [{"opacity": "0"}, {"opacity": "1"}])
    assert count >= DRAWN, f"a plain fade was drawn in {count} frames"


@pytest.mark.parametrize("standing", ["translate", "scale"])
def test_a_property_equal_at_both_ends_suppresses_the_drawing(
    browser, tmp_path, browser_name, standing
):
    """The finding. The same fade, with one property that does not move, is not drawn.

    Both spellings of the standing value are the identity, so the element's geometry is the
    same in every engine and in every frame. Only whether the fade beside it is drawn differs.
    """
    value = "0px" if standing == "translate" else "1"
    count = intermediate(
        browser,
        tmp_path,
        [{"opacity": "0", standing: value}, {"opacity": "1", standing: value}],
    )
    draws = DRAWS_A_STANDING_PROPERTY[browser_name]
    if draws is None:
        # A real skip, reported by `pytest -rs`, carrying the number that fills the row in.
        pytest.skip(
            f"{browser_name} has no measured row: it drew the fade beside a standing "
            f"{standing} in {count} of the recording's frames"
        )
    elif draws:
        assert count >= DRAWN, (
            f"{browser_name} now suppresses a fade beside a standing {standing}, "
            f"drawing it in {count} frames"
        )
    else:
        assert count < DRAWN, (
            f"{browser_name} now draws a fade beside a standing {standing}, "
            f"in {count} frames, so the runtime may stop filtering its keyframes"
        )
