# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Media elements in the HTML output*.

These belong to the narrated-audio entry under *Potential Future Features*,
not to 0.1.0. They are probed anyway, because the finding is what makes that entry
look cheap, and a finding that quietly stops holding makes a plan quietly wrong.

The clip is a half-second sine wave, generated here rather than stored,
so the repository carries no media asset.
That is a deliberate narrowing: the finding measured an Opus file,
and what is reproduced is the mechanism (a `data:` URI decodes and reports its own length),
not the codec.
"""

import base64
import io
import math
import struct
import wave

import pytest
from harness import TypstRunner

RATE = 8000
DURATION = 0.5


def clip() -> str:
    """A half-second 440 Hz sine wave, as a `data:` URI."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(
            b"".join(
                struct.pack("<h", int(16000 * math.sin(2 * math.pi * 440 * i / RATE)))
                for i in range(int(RATE * DURATION))
            )
        )
    return "data:audio/wav;base64," + base64.b64encode(buffer.getvalue()).decode()


def document(wrapped: bool) -> str:
    """A slide frame with an audio element beside it, with or without a block wrapper."""
    audio = f'#html.elem("audio", attrs: (id: "clip", src: "{clip()}"))[]'
    if wrapped:
        audio = f'#html.elem("div", attrs: (style: "display: contents"))[\n  {audio}\n]'
    return f"{audio}\n#html.frame[#box[slide]]\n"


def test_an_audio_element_lives_beside_the_frame(typst: TypstRunner):
    """`html.elem` is dropped inside a frame, so a clip has to be a sibling of one.

    A `div` with `display: contents` is enough to keep it out of a paragraph
    without adding a box to the layout.
    """
    markup = typst.html(document(wrapped=True)).read_text()
    assert '<div style="display: contents">' in markup
    assert "<audio" in markup
    assert "<p><audio" not in markup


def test_without_a_block_wrapper_typst_puts_it_in_a_paragraph(typst: TypstRunner):
    """`audio` is phrasing content, so typst wraps it, which is why the wrapper is needed."""
    markup = typst.html(document(wrapped=False), name="bare.html").read_text()
    assert "<p><audio" in markup


def test_a_data_uri_clip_decodes_and_reports_its_length(typst: TypstRunner, open_page):
    """The browser supplies the timing that typst cannot, which is what `wait: auto` needs."""
    page = open_page(typst.html(document(wrapped=True)))
    state = page.evaluate(
        """async () => {
            const audio = document.getElementById("clip");
            await new Promise(resolve => {
                if (audio.readyState >= 4) resolve();
                else audio.addEventListener("canplaythrough", resolve, {once: true});
            });
            return {ready: audio.readyState, duration: audio.duration};
        }"""
    )
    assert state["ready"] == 4
    assert state["duration"] == pytest.approx(DURATION, abs=0.01)


def test_autoplay_is_gated_on_a_user_gesture():
    """Recorded as unprobeable rather than faked.

    The finding is that `play()` rejects with `NotAllowedError` until the user has
    interacted with the document, which is why a self-playing deck needs one click.
    Measured on 2026-09-12 with playwright 1.62 and its bundled headless chromium 151:
    `play()` resolves regardless, over `file://` and over `http://`,
    with playwright's own `--autoplay-policy=no-user-gesture-required` removed and the
    gesture requirement asked for explicitly.
    The headless shell simply does not apply the gate, so a probe here would assert
    the opposite of the finding and prove nothing about a real browser.
    """
    pytest.skip("playwright's headless chromium does not apply chromium's autoplay gate")


def test_typst_exposes_no_base64_to_scripts(typst: TypstRunner):
    """Embedding a clip needs an encoder written in typst, which is what makes it cost anything.

    `to_base64_url` exists only on the Rust side, for images.
    """
    typst.ok(
        """
#let names = dictionary(std).keys().filter(name => name.contains("base") or name.contains("64"))
#assert.eq(names, (), message: "the standard library grew " + repr(names))
"""
    )


def test_a_while_loop_is_capped(typst: TypstRunner):
    """The first trap in writing that encoder: the loop has to be a `for` over a `range`."""
    typst.fails(
        """
#{
  let i = 0
  while i < 10001 { i += 1 }
}
""",
        "loop seems to be infinite",
    )
