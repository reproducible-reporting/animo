# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Typst writes a shape from a local origin*.

A morph pairs a shape or an image in one rendering with one in the other by what it draws,
and leaves out where it is drawn. That rests on how typst writes the SVG of a frame:
the place of every shape and image in a transform and not in the path data,
and the paint in attributes beside the geometry.
"""

import re
import xml.etree.ElementTree as ET

import pytest
from harness import TypstRunner
from PIL import Image

SVG = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}"

# Two copies of each shape at two places, one of them recoloured, an image twice, a
# fraction, a clipped box and a gradient fill.
BODY = """\
#html.frame(block(width: 300pt, height: 200pt, {
  place(dx: 10pt, dy: 10pt, rect(width: 20pt, height: 10pt, fill: blue))
  place(dx: 90pt, dy: 47.3pt, rect(width: 20pt, height: 10pt, fill: red))
  place(dx: 10pt, dy: 30pt, circle(radius: 5pt, fill: blue))
  place(dx: 90pt, dy: 61.7pt, circle(radius: 5pt, fill: blue))
  place(dx: 10pt, dy: 50pt, line(length: 20pt, stroke: 2pt))
  place(dx: 90pt, dy: 81.1pt, line(length: 20pt, stroke: 2pt + green))
  place(dx: 10pt, dy: 70pt, polygon.regular(size: 12pt, vertices: 5))
  place(dx: 90pt, dy: 99.9pt, polygon.regular(size: 12pt, vertices: 5))
  place(dx: 10pt, dy: 100pt, image("pattern.png", width: 30pt))
  place(dx: 90pt, dy: 130.4pt, image("pattern.png", width: 30pt))
  place(dx: 180pt, dy: 10pt, $ a / b $)
  place(dx: 180pt, dy: 60pt, box(clip: true, width: 30pt, height: 20pt, circle(radius: 20pt)))
  place(dx: 180pt, dy: 100pt, rect(width: 40pt, height: 20pt, fill: gradient.linear(red, blue)))
}))
"""


@pytest.fixture
def frame(typst: TypstRunner) -> ET.Element:
    """The `<svg>` of the frame, parsed."""
    Image.new("RGB", (6, 3), (200, 40, 40)).save(typst.scratch / "pattern.png")
    markup = typst.html(BODY, name="shapes.html").read_text()
    return ET.fromstring(re.search(r"<svg\b.*</svg>", markup, re.S).group(0))


def drawn(frame: ET.Element, tag: str) -> list[ET.Element]:
    """The elements of one kind that are drawn where they sit, outside every definition."""
    hidden = {
        id(element)
        for container in frame.iter()
        if container.tag in {f"{SVG}defs", f"{SVG}clipPath", f"{SVG}symbol"}
        for element in container.iter()
    }
    return [element for element in frame.iter(f"{SVG}{tag}") if id(element) not in hidden]


def test_every_path_starts_at_its_own_origin(frame):
    """The place of a shape is in a transform, so its `d` is the same wherever it is."""
    paths = drawn(frame, "path")
    # The eight shapes, the bar of the fraction, the clipped circle and the gradient rectangle.
    assert len(paths) == 11
    assert all(path.get("d").startswith("M 0 0") for path in paths)


def test_two_copies_of_a_shape_at_two_places_have_one_d(frame):
    """The rectangles, circles, lines and polygons each come in pairs of one `d`.

    Recolouring one of a pair changes its `fill` or `stroke` and leaves its `d` alone.
    """
    shapes = {}
    for path in drawn(frame, "path"):
        shapes.setdefault(path.get("d"), []).append(path)
    pairs = [found for found in shapes.values() if len(found) == 2]
    assert len(pairs) == 4
    assert {pair[0].get("fill") for pair in pairs} | {pair[1].get("fill") for pair in pairs} >= {
        "#0074d9",
        "#ff4136",
    }


def test_the_paint_of_a_path_is_in_attributes_beside_its_d(frame):
    """Fill, stroke and the stroke's shape are attributes, and typst's shapes are `nonzero`."""
    paths = drawn(frame, "path")
    stroked = [path for path in paths if path.get("stroke") not in (None, "none")]
    assert stroked
    for path in stroked:
        for name in ("stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit"):
            assert path.get(name) is not None, f"a stroked path has no {name}"
    assert {path.get("fill-rule") for path in paths if path.get("fill") != "none"} == {"nonzero"}


def test_an_image_has_no_place_of_its_own(frame):
    """An image is written without `x` and `y`, so its place is the transform above it."""
    images = drawn(frame, "image")
    assert len(images) == 2
    for image in images:
        assert image.get("x") is None
        assert image.get("y") is None
        assert image.get(f"{XLINK}href").startswith("data:image/png;base64,")
        assert image.get("preserveAspectRatio") == "none"
    assert len({(image.get(f"{XLINK}href"), image.get("width")) for image in images}) == 1


def test_a_fraction_bar_is_a_stroked_path(frame):
    """The bar beside the glyphs of a fraction is a line whose `d` has the bar's length."""
    bars = [path for path in drawn(frame, "path") if re.fullmatch(r"M 0 0h [\d.]+", path.get("d"))]
    assert any(bar.get("stroke-width") not in (None, "2") for bar in bars)


def test_a_clipped_box_is_a_group_with_a_clip_path(frame):
    """The group carries the clip and the translation, and holds what it clips."""
    groups = [group for group in frame.iter(f"{SVG}g") if group.get("clip-path") is not None]
    assert len(groups) == 1
    assert groups[0].get("transform", "").startswith("translate(")
    assert groups[0].find(f"{SVG}path") is not None


def test_a_gradient_is_in_the_user_space_of_the_shape(frame):
    """The gradient's units are `userSpaceOnUse`, scaled to the size of the shape."""
    gradients = list(frame.iter(f"{SVG}linearGradient"))
    assert any(gradient.get("gradientUnits") == "userSpaceOnUse" for gradient in gradients)
    assert any(gradient.get("gradientTransform") == "scale(40 20)" for gradient in gradients)


def test_a_circle_ends_at_its_start_without_closing(frame):
    """A circle is four relative cubic Béziers after an `m`, without a `Z`, back to its start.

    Whether a subpath is closed is therefore read from where it ends as well as from `Z`.
    """
    circles = [path.get("d") for path in drawn(frame, "path") if path.get("d").count("c") == 4]
    assert circles
    for d in circles:
        assert "Z" not in d
        assert "z" not in d
        numbers = [float(value) for value in re.findall(r"-?[\d.]+", d.split("c", 1)[1])]
        ends = [numbers[k : k + 6][4:] for k in range(0, len(numbers), 6)]
        assert sum(end[0] for end in ends) == pytest.approx(0, abs=1e-6)
        assert sum(end[1] for end in ends) == pytest.approx(0, abs=1e-6)


def test_a_curve_writes_the_fill_rule_it_asks_for(typst: TypstRunner):
    """The even-odd rule of a `curve` is `fill-rule="evenodd"` on its path."""
    body = """\
#html.frame(block(width: 40pt, height: 40pt, curve(
  fill: blue,
  fill-rule: "even-odd",
  curve.move((0pt, 0pt)),
  curve.line((20pt, 0pt)),
  curve.line((10pt, 20pt)),
  curve.close(),
)))
"""
    markup = typst.html(body, name="rule.html").read_text()
    svg = ET.fromstring(re.search(r"<svg\b.*</svg>", markup, re.S).group(0))
    assert [path.get("fill-rule") for path in drawn(svg, "path")] == ["evenodd"]
