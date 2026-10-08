# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the alignment of two paths, on numbers, in a page with no deck in it.

`src/js/paths.js` reads no DOM, so it is loaded alone as a classic script and its functions
are globals of the page. The page draws each path only to ask the engine what it covers,
with `isPointInFill` and `isPointInStroke` on a grid, which is how the tests check that the
alignment rewrote a path without changing its shape.
"""

import pytest
from harness import ROOT

PATHS = (ROOT / "src" / "js" / "paths.js").read_text()

# Paths as typst 0.15.0 writes them, apart from the ones that exercise commands typst does not
# write, all inside a box of 60 by 60 user units.
SQUARE = "M 0 0v 56.692913386h 56.692913386v -56.692913386Z "
CIRCLE = (
    "M 0 0m 0 28.346456693c 0 -15.64112126 12.705335433 -28.346456693 28.346456693 "
    "-28.346456693c 15.64112126 0 28.346456693 12.705335433 28.346456693 28.346456693c 0 "
    "15.64112126 -12.705335433 28.346456693 -28.346456693 28.346456693c -15.64112126 0 "
    "-28.346456693 -12.705335433 -28.346456693 -28.346456693"
)
STAR = (
    "M 0 0m 28.346456693 0l 6.66465168 19.173350615l 20.294430672 0.41356923l -16.175449411 "
    "12.263351588l 5.877996258 19.428950456l -16.661629199 -11.594182518l -16.661629199 "
    "11.594182518l 5.877996258 -19.428950456l -16.175449411 -12.263351588l 20.294430672 "
    "-0.41356923Z "
)
PENTAGON = (
    "M 0 0m 43.620711551 51.279221888h -33.323258398l -10.297453153 -31.692302043l "
    "26.959082352 -19.586919844l 26.959082352 19.586919844l -10.297453153 31.692302043Z "
)
# A ring as two subpaths, an outline and a hole that runs the other way round.
RING = (
    "M 0 28 C 0 12 12 0 28 0 C 44 0 56 12 56 28 C 56 44 44 56 28 56 C 12 56 0 44 0 28 Z "
    "M 14 28 C 14 36 20 42 28 42 C 36 42 42 36 42 28 C 42 20 36 14 28 14 C 20 14 14 20 14 28 Z"
)
LINE = "M 0 0h 56.692913386"
WAVE = "M 0 0c 4.72 4.72 18.9 28.3 28.3 28.3c 9.45 0 23.6 -23.6 28.3 -28.3"
ZIGZAG = "M 0 40 C 5 10 15 0 20 20 C 25 40 35 50 40 20 C 45 0 50 10 56 30"
# Every command typst does not write but an SVG drawn elsewhere might, without arcs.
SHORTHANDS = "M 4 4 Q 30 -10 52 4 T 52 52 S 20 60 4 52 L 4 30 H 10 V 20 z"

PAIRS = {
    "square into circle": (SQUARE, CIRCLE),
    "star into pentagon": (STAR, PENTAGON),
    "ring into disc": (RING, CIRCLE),
    "line into circle": (LINE, CIRCLE),
    "two open curves": (WAVE, ZIGZAG),
    "shorthands into square": (SHORTHANDS, SQUARE),
}


@pytest.fixture
def engine(page):
    """A page with the alignment as globals and an SVG to measure paths in."""
    page.set_content(
        '<!DOCTYPE html><html><body><svg width="80" height="80">'
        '<path id="p" stroke-width="2"/></svg></body></html>'
    )
    page.add_script_tag(content=PATHS)
    return page


def aligned(engine, pair: str) -> list[str]:
    """The two paths of a pair, aligned, with neither filled."""
    return engine.evaluate("([a, b]) => alignPaths(a, b)", list(PAIRS[pair]))


# What a path covers, as two strings of one character per point of a grid, for its fill and
# its stroke. The grid avoids round numbers, so that no point sits exactly on an edge.
COVERS = """data => {
    const path = document.getElementById("p");
    path.setAttribute("d", data);
    let fill = "";
    let stroke = "";
    for (let y = -3.37; y < 62; y += 1.9) {
        for (let x = -3.37; x < 62; x += 1.9) {
            const point = new DOMPoint(x, y);
            fill += path.isPointInFill(point) ? "#" : ".";
            stroke += path.isPointInStroke(point) ? "#" : ".";
        }
    }
    return [fill, stroke];
}"""


def differences(a: str, b: str) -> int:
    """The number of points of a grid that one path covers and the other does not."""
    return sum(x != y for x, y in zip(a, b, strict=True))


@pytest.mark.parametrize("pair", PAIRS)
def test_two_paths_get_one_structure(engine, pair):
    """The command letters agree, which is what the engine interpolates `d` between."""
    one, other = aligned(engine, pair)
    letters = engine.evaluate("([a, b]) => [pathCommands(a), pathCommands(b)]", [one, other])
    assert letters[0] == letters[1]
    assert set(letters[0]) <= {"M", "C", "Z"}


@pytest.mark.parametrize("pair", PAIRS)
def test_each_path_keeps_its_shape(engine, pair):
    """The rewritten path covers the points the original covers, fill and stroke alike.

    A point near an edge may fall either way after the numbers are rounded, so a few of the
    grid's 1156 points may differ.
    """
    for original, rewritten in zip(PAIRS[pair], aligned(engine, pair), strict=True):
        before = engine.evaluate(COVERS, original)
        after = engine.evaluate(COVERS, rewritten)
        assert differences(before[0], after[0]) <= 2, "the fill changed"
        assert differences(before[1], after[1]) <= 2, "the stroke changed"


# The subpaths of path data with the sign of their area and their vertices, read one by one,
# so that a subpath of one point, which `parsePath` drops, is `null` rather than missing.
SUBPATHS = """data => data.split(/(?=M)/).map((part) => {
    const [subpath] = parsePath(part);
    if (subpath === undefined) {
        return null;
    }
    return {
        area: signedArea(measure(subpath)),
        closed: subpath.closed,
        vertices: subpath.segments.map((segment) => segment.slice(0, 2)),
    };
})"""


@pytest.mark.parametrize("pair", ["square into circle", "star into pentagon", "ring into disc"])
def test_paired_subpaths_run_the_same_way_round(engine, pair):
    """A closed subpath winds as its partner does, or it turns inside out on the way."""
    one, other = (engine.evaluate(SUBPATHS, data) for data in aligned(engine, pair))
    assert len(one) == len(other)
    for a, b in zip(one, other, strict=True):
        if a is not None and b is not None:
            assert a["area"] * b["area"] > 0


def travel(a: list[list[float]], b: list[list[float]], shift: int) -> float:
    """The squared distance the vertices of one subpath travel to another's, shifted."""
    count = len(a)
    return sum(
        (a[i][0] - b[(i + shift) % count][0]) ** 2 + (a[i][1] - b[(i + shift) % count][1]) ** 2
        for i in range(count)
    )


@pytest.mark.parametrize("pair", ["square into circle", "star into pentagon"])
def test_a_closed_subpath_starts_where_its_points_travel_least(engine, pair):
    """No other vertex of the partner as the start makes the vertices travel less."""
    one, other = (engine.evaluate(SUBPATHS, data)[0] for data in aligned(engine, pair))
    a, b = one["vertices"], other["vertices"]
    best = travel(a, b, 0)
    assert all(best <= travel(a, b, shift) + 1e-6 for shift in range(len(b)))


def test_a_square_is_cut_at_the_middle_of_its_sides_against_a_circle(engine):
    """The corners go to the diagonals of the circle, so the square does not twist on the way."""
    square, circle = (
        engine.evaluate(SUBPATHS, data)[0] for data in aligned(engine, "square into circle")
    )
    assert len(square["vertices"]) == len(circle["vertices"]) == 8
    middle = 56.692913386 / 2
    for (x, y), (u, v) in zip(square["vertices"], circle["vertices"], strict=True):
        corner = abs(x - middle) > 1 and abs(y - middle) > 1
        if corner:
            # A corner goes to the point of the circle on its diagonal.
            assert abs(abs(u - middle) - abs(v - middle)) < 0.1
        else:
            # The middle of a side goes to the point of the circle at the end of an axis.
            # The start is found on samples of the two outlines, which puts it within a
            # tenth of a point of the exact one.
            assert (u, v) == pytest.approx((x, y), abs=0.1)


def test_a_hole_without_partner_grows_from_a_point(engine):
    """The disc gets a second subpath, which is one point in the middle of the hole."""
    _, disc = aligned(engine, "ring into disc")
    outline, hole = disc.split("M")[1:]
    assert engine.evaluate(SUBPATHS, "M" + outline)[0] is not None
    numbers = [float(value) for value in hole.replace("C", " ").replace("Z", " ").split()]
    # The hole of the ring is centred in the ring, and the disc lies in the same box.
    assert numbers == pytest.approx([28.346] * len(numbers), abs=1e-3)


@pytest.mark.parametrize("filled", [False, True])
def test_an_open_subpath_closes_like_its_fill(engine, filled):
    """Without a fill a line runs back along itself, and with one a line closes it."""
    one, _ = engine.evaluate(
        "([a, b, filled]) => alignPaths(a, b, [filled, false])", [WAVE, CIRCLE, filled]
    )
    [subpath] = engine.evaluate(SUBPATHS, one)
    assert subpath["closed"]
    # Running back along itself encloses nothing, and a closing line encloses the bowl.
    assert (abs(subpath["area"]) > 100) == filled


@pytest.mark.parametrize("data", ["M 0 0 A 10 10 0 0 1 20 0", "M 0 0 L 10", "", "M 5 5"])
def test_data_that_cannot_be_aligned_is_refused(engine, data):
    """An arc, a missing number and a path without a segment give no alignment."""
    assert engine.evaluate("([a, b]) => alignPaths(a, b)", [data, SQUARE]) is None


def test_a_computed_path_is_read_as_its_data(engine):
    """A computed `d` wraps the data in `path(..)`, as the engine reports it mid-flight."""
    found = engine.evaluate("([a, b]) => alignPaths(a, b)", [f'path("{SQUARE.strip()}")', CIRCLE])
    assert found == aligned(engine, "square into circle")
