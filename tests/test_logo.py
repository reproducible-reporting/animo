# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 1: the logo of Animo, alone and as the "made with Animo" badge.

The package holds the path of the logo as a typst string,
and the SVG files under `logo/` hold the same path for the documentation site and the
social cards.
Nothing derives one from the other, so a test keeps them in step.
"""

import re

import pytest
from decks import deck
from harness import ROOT, TypstRunner

# The pieces of the typst string that holds the path, which `src/logo.typ` concatenates.
PATH_DEFINITION = re.compile(r"(?s)#let logo-path = \((.*?)\n\)")


def package_path() -> str:
    """The path of the logo, as `src/logo.typ` spells it."""
    definition = PATH_DEFINITION.search((ROOT / "src" / "logo.typ").read_text()).group(1)
    return "".join(re.findall(r'"([^"]*)"', definition))


@pytest.mark.parametrize("path", sorted((ROOT / "logo").glob("animo-*.svg")), ids=lambda p: p.name)
def test_logo_file_holds_the_path_of_the_package(path):
    """A change to the logo has to reach the package and every file under `logo/`."""
    files = re.findall(r' d="([^"]*)"', path.read_text())
    assert files == [package_path()], f"{path.name} and src/logo.typ hold different paths"


@pytest.mark.parametrize("html", [False, True])
def test_the_logo_and_the_badge_compile_in_both_targets(typst: TypstRunner, html):
    """Both forms are images inside a slide, which the HTML target renders as a frame."""
    body = "#animo-logo(height: 1cm) #made-with-animo(fill: red.transparentize(50%))"
    typst.ok(deck(f"slide[{body}]"), html=html)


def test_the_badge_is_as_tall_as_its_logo(typst: TypstRunner):
    """The words take less height than the logo, so the logo sets the height of the badge."""
    check = "#context assert.eq(measure(made-with-animo(height: 1cm)).height, 1cm)"
    typst.ok(deck("slide[]", preamble=check + "\n"))


@pytest.mark.parametrize("call", ["animo-logo", "made-with-animo"])
def test_a_fill_that_is_not_a_color_is_refused(typst: TypstRunner, call):
    """An SVG fill attribute holds one color, so a gradient would otherwise vanish silently."""
    body = f"#{call}(fill: gradient.linear(red, blue))"
    typst.fails(deck(f"slide[{body}]"), "the fill of the Animo logo must be a color")
