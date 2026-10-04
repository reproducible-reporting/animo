# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for the second half of *SVG `<defs>` ids are content hashes*.

Typst names a gradient, a clip path and a tiling by a hash of its content, so two slides that
use the same one define the same id twice, in two separate frames.
A reference such as `fill="url(#id)"` resolves to the first element of that id in the
document, and a browser does not resolve a reference into a subtree that is not laid out.
The slide that holds the first definition is `display: none` unless it is one of the two
slides the runtime lays out, so the fill of a later slide is dropped and its clip path is
not applied.

The documents here are built by hand, in the shape of the page animo emits:
the first `<svg>` defines a gradient and a clip path, and the second one references them.
The control has the first `<svg>` displayed, which is what makes the claim meaningful.
The repair is an always rendered `<svg>` that comes first in the document and holds copies,
which is what the runtime builds at load.
"""

import numpy as np
from harness import screenshot

# The content of the first `<svg>`: a horizontal gradient, a clip path of the left half of
# the box that the second `<svg>` clips, and a tiling of vertical stripes.
DEFINITIONS = """\
<defs>
  <linearGradient id="g">
    <stop offset="0" stop-color="#ff0000"/>
    <stop offset="1" stop-color="#0000ff"/>
  </linearGradient>
  <clipPath id="c"><rect x="100" y="0" width="50" height="100"/></clipPath>
  <pattern id="p" width="10" height="10" patternUnits="userSpaceOnUse">
    <rect width="5" height="10" fill="#ff00ff"/>
  </pattern>
</defs>"""

# The holder the runtime builds, written out. It is `position: absolute` and has no size, so
# it takes no space in the layout.
HOLDER = f"""\
<svg width="0" height="0" aria-hidden="true" style="position: absolute; overflow: hidden">
{DEFINITIONS}
</svg>"""

# A gradient box on the left, a green box in the middle that the clip path cuts to its left
# half, and a striped box on the right. Every reference is to an id that is defined only in the
# first `<svg>`.
USER = """\
<svg width="300" height="100" style="display: block">
  <rect x="0" y="0" width="100" height="100" fill="url(#g)"/>
  <rect x="100" y="0" width="100" height="100" fill="#00ff00" clip-path="url(#c)"/>
  <rect x="200" y="0" width="100" height="100" fill="url(#p)"/>
</svg>"""

WHITE = np.array([255, 255, 255])
GREEN = np.array([0, 255, 0])
MAGENTA = np.array([255, 0, 255])


def document(*, first: str, holder: str = "") -> str:
    """A page whose first `<svg>` is wrapped in `first` and may be preceded by a holder.

    The wrapper is out of the flow, so that the second `<svg>` sits at the origin however the
    first one is hidden.
    """
    return (
        "<!doctype html><style>html, body { margin: 0; background: #ffffff; }</style>"
        f"<body>{holder}<div style='position: absolute; {first}'>"
        f"<svg width='300' height='100'>{DEFINITIONS}</svg></div>{USER}</body>"
    )


def paint(page, markup: str) -> tuple[bool, bool, bool]:
    """Whether the gradient is drawn, the clip path applied and the tiling drawn, in one page.

    The gradient is red at its left edge and blue at its right edge, and a dropped fill
    leaves the white of the page. The green box is cut at x = 150 by the clip path, and a clip
    that is not applied leaves all of it green.
    The tiling is magenta for its first five pixels in ten, and a dropped fill leaves white.
    """
    page.set_viewport_size({"width": 400, "height": 200})
    page.set_content(markup)
    image = screenshot(page)
    left, right = image[50, 10], image[50, 90]
    gradient = left[0] > 200 > left[2] and right[2] > 200 > right[0] and left[1] < 50
    clipped = bool((image[50, 175] == WHITE).all()) and bool((image[50, 125] == GREEN).all())
    tiled = bool((image[50, 202] == MAGENTA).all()) and bool((image[50, 207] == WHITE).all())
    return gradient, clipped, tiled


def test_a_displayed_definition_serves_a_later_reference(page):
    """The control: the first element of each id is laid out, so both references resolve."""
    assert paint(page, document(first="")) == (True, True, True)


def test_a_definition_in_a_hidden_subtree_serves_no_reference(page):
    """The claim: the same ids, with the first definition in a `display: none` element.

    The fills are dropped, so the gradient box and the striped box are the white of the page,
    and the clip path is not applied, so the green box is green to its right edge.
    """
    assert paint(page, document(first="display: none")) == (False, False, False)


def test_an_always_rendered_holder_first_in_the_document_serves_the_reference(page):
    """The repair: the holder is the first match of both ids and is laid out.

    The original definitions stay where they were, hidden, and are shadowed by the copies.
    """
    assert paint(page, document(first="display: none", holder=HOLDER)) == (True, True, True)


def test_a_glyph_definition_in_a_hidden_subtree_serves_a_use(page):
    """The half that does not fail, which is why text is intact on a slide with a missing fill.

    Typst defines a glyph as a `<symbol>` and draws it through `<use>`, and a `<use>` into an
    element that is not laid out is drawn, so *Findings* judged the first match harmless
    when it measured glyphs alone.
    """
    page.set_viewport_size({"width": 400, "height": 200})
    page.set_content(
        "<!doctype html><style>html, body { margin: 0; background: #ffffff; }</style>"
        "<body><div style='position: absolute; display: none'><svg width='20' height='20'>"
        "<defs><symbol id='s' overflow='visible'><path d='M 0 0 h 20 v 20 h -20 Z'/></symbol>"
        "</defs></svg></div>"
        "<svg width='100' height='100' style='display: block'>"
        "<use xlink:href='#s' x='10' y='10' fill='#00ff00'/></svg></body>"
    )
    image = screenshot(page)
    assert (image[20, 20] == GREEN).all()
    assert (image[50, 50] == WHITE).all()


def test_a_subtree_hidden_with_visibility_empties_a_clip_and_a_tiling(page):
    """The other way to scope a slide away, which resolves the ids and still draws nothing.

    A `visibility: hidden` subtree is laid out, so the gradient resolves.
    The children of a clip path and of a tiling inherit the visibility, so the clip is empty
    and clips the whole box, and the tile has nothing to draw.
    Typst writes the definitions of a frame in a `<defs>` under the root of the frame, so no
    group that animo scopes with `visibility` contains one.
    """
    gradient, clipped, tiled = paint(page, document(first="visibility: hidden"))
    assert gradient
    image = screenshot(page)
    assert (image[50, 125] == WHITE).all(), "the clip path was not empty"
    assert not clipped
    assert not tiled


def test_a_holder_that_is_not_laid_out_repairs_nothing(page):
    """Why the holder must not be `display: none`: it would be the first match and be dropped."""
    hidden = HOLDER.replace("position: absolute", "display: none; position: absolute")
    assert paint(page, document(first="display: none", holder=hidden)) == (False, False, False)


def test_the_holder_takes_no_space_and_paints_no_ink(page):
    """A holder first in the body must not move the content behind it or draw on it."""
    page.set_viewport_size({"width": 400, "height": 200})
    page.set_content(document(first="display: none", holder=HOLDER))
    box = page.evaluate(
        "() => { const r = document.querySelector('svg').getBoundingClientRect();"
        " return [r.x, r.y, r.width, r.height]; }"
    )
    assert box == [0, 0, 0, 0]
    user = page.evaluate(
        "() => { const r = document.body.lastElementChild.getBoundingClientRect();"
        " return [r.x, r.y]; }"
    )
    assert user == [0, 0]
