# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The harness testing itself.

A comparison helper that returns the wrong answer would make every probe and every feature
test agree with whatever the code happens to do, silently.
So each helper is exercised on a case whose answer is known in advance,
including the negative case: a comparison that must fail, and does.
"""

from io import BytesIO

import numpy as np
import pytest
from harness import (
    Box,
    Reference,
    TypstRunner,
    assert_differs,
    assert_identical,
    assert_identical_outside,
    decode,
    difference_box,
    difference_report,
    pdf_pages,
    screenshot,
    state_hash,
)
from harness.typst import ROOT
from PIL import Image

STAND_IN_DECK = ROOT / "tests" / "documents" / "stand_in_deck.html"


def canvas(value: int = 255) -> np.ndarray:
    """A uniform RGB image of 40 by 30 pixels."""
    return np.full((30, 40, 3), value, dtype=np.uint8)


# Tier 1: the compile-only runner.


def test_a_document_full_of_assertions_passes(typst: TypstRunner):
    """The ordinary case: everything the document has to say, it says with `#assert`."""
    typst.ok("#assert.eq(1 + 1, 2)\n")


def test_a_failing_assertion_is_reported_with_the_source(typst: TypstRunner):
    """A failure quotes the compiler and the numbered document, because both are needed."""
    with pytest.raises(AssertionError) as caught:
        typst.ok('#assert(false, message: "boom")\n')
    assert "boom" in str(caught.value)
    assert "1 | #assert" in str(caught.value)


def test_a_document_that_must_fail_is_checked_on_its_message(typst: TypstRunner):
    """This is the shape the `import *` footgun gets tested with later."""
    typst.fails('#(1 + "a")\n', "cannot add integer and string")


def test_a_document_that_must_fail_but_compiles_is_an_error(typst: TypstRunner):
    """Otherwise a negative test would pass the day the behaviour it guards disappears."""
    with pytest.raises(AssertionError, match="compiled but should not have"):
        typst.fails("ordinary content\n")


def test_the_wrong_failure_is_not_the_expected_one(typst: TypstRunner):
    """A document may fail for a reason that has nothing to do with the claim."""
    with pytest.raises(AssertionError, match="expected 'cannot add'"):
        typst.fails('#assert(false, message: "boom")\n', "cannot add")


# Tier 2: the raster comparisons.


def test_identical_rasters_compare_identical():
    """The trivial case, which has to stay trivial."""
    assert difference_box(canvas(), canvas()) is None
    assert_identical(canvas(), canvas())
    assert "identical" in difference_report(canvas(), canvas())


def test_differing_rasters_are_located_not_only_detected():
    """The animation tests assert "identical outside this band" repeatedly.

    A bare boolean makes those failures unreadable, so the box is part of the answer.
    """
    changed = canvas()
    changed[10:20, 5:15] = 0
    box = difference_box(canvas(), changed)
    assert box == Box(5, 10, 15, 20)
    report = difference_report(canvas(), changed)
    assert "100 of 1200 pixels" in report
    assert "255/255" in report
    assert "x 5..15, y 10..20" in report


def test_a_comparison_that_must_fail_does_fail():
    """The negative half: a broken helper that passed everything would be invisible."""
    changed = canvas()
    changed[0, 0] = 0
    with pytest.raises(AssertionError, match="differ"):
        assert_identical(canvas(), changed)
    with pytest.raises(AssertionError, match="should differ"):
        assert_differs(canvas(), canvas())


def test_a_tolerance_is_per_channel():
    """Rounding of one unit is what `plus-lighter` leaves behind, and has to be tolerable."""
    changed = canvas()
    changed[5, 5] = 254
    assert_identical(canvas(), changed, tol=1)
    with pytest.raises(AssertionError):
        assert_identical(canvas(), changed, tol=0)


def test_differences_inside_a_band_are_allowed_and_outside_are_not():
    """The invariant the region design rests on, in its harness form."""
    band = Box(0, 10, 40, 20)
    inside = canvas()
    inside[12:18, 3:9] = 0
    assert_identical_outside(canvas(), inside, band)

    outside = canvas()
    outside[25, 30] = 0
    with pytest.raises(AssertionError, match="differ outside"):
        assert_identical_outside(canvas(), outside, band)


def test_mismatched_shapes_say_so():
    """Comparing a 4:3 page with a 16:9 one is a mistake worth naming."""
    with pytest.raises(AssertionError, match="shapes differ"):
        assert_identical(canvas(), np.zeros((10, 10, 3), dtype=np.uint8))


def test_transparency_is_flattened_onto_white():
    """A transparent pixel is the page a projector shows, and an opaque one is left alone."""
    rgba = np.zeros((1, 4, 4), dtype=np.uint8)
    rgba[0, 1] = (0, 0, 0, 128)
    rgba[0, 2] = (0, 0, 0, 255)
    rgba[0, 3] = (0, 0, 255, 255)
    buffer = BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buffer, format="PNG")
    decoded = decode(buffer.getvalue())
    assert decoded[0, 0].tolist() == [255, 255, 255]
    assert 120 <= decoded[0, 1, 0] <= 135
    assert decoded[0, 2].tolist() == [0, 0, 0]
    assert decoded[0, 3].tolist() == [0, 0, 255]


def test_text_on_a_page_without_a_fill_is_visible_to_a_comparison(paged):
    """Typst writes such a page transparent, which must not decode as black as its text."""
    blank = paged.png("#set page(width: 2cm, height: 1cm)\n")[0]
    text = paged.png("#set page(width: 2cm, height: 1cm)\nText\n")[0]
    assert blank[0, 0].tolist() == [255, 255, 255]
    assert_differs(blank, text, what="a blank page and a page with text")


def test_a_page_with_a_fill_keeps_it(paged):
    """A slide background paints every pixel, so the flattening changes nothing there."""
    page = paged.png('#set page(width: 2cm, height: 1cm, fill: rgb("#0000ff"))\n')[0]
    assert page[0, 0].tolist() == [0, 0, 255]


def test_a_page_is_rasterised_at_one_pixel_per_point(paged):
    """The default resolution makes a box measured in points a box of the same numbers."""
    pages = paged.png("#set page(width: 100pt, height: 60pt, margin: 0pt)\n#rect()\n")
    assert len(pages) == 1
    assert pages[0].shape == (60, 100, 3)


def test_every_page_comes_back_in_order(paged):
    """Multi-page export needs a page number template, and the pages have to stay in order."""
    pages = paged.png(
        "#set page(width: 40pt, height: 30pt, margin: 0pt)\n"
        '#rect(width: 100%, height: 100%, fill: rgb("#ff0000"))\n'
        "#pagebreak()\n"
        '#rect(width: 100%, height: 100%, fill: rgb("#0000ff"))\n'
    )
    assert len(pages) == 2
    assert tuple(pages[0][15, 20]) == (255, 0, 0)
    assert tuple(pages[1][15, 20]) == (0, 0, 255)


def test_the_output_mode_reaches_the_document_as_an_input(paged, typst: TypstRunner):
    """`--input animo=presentation` selects the mode exactly as an ordinary user would."""
    body = """\
#set page(width: 40pt, height: 30pt, margin: 0pt)
#context {
  let mode = sys.inputs.at("animo", default: "handout")
  let fill = if mode == "presentation" { rgb("#0000ff") } else { rgb("#ff0000") }
  rect(width: 100%, height: 100%, fill: fill)
}
"""
    source = typst.source(body)
    assert tuple(paged.png(source)[0][15, 20]) == (255, 0, 0)
    assert tuple(paged.png(source, mode="presentation")[0][15, 20]) == (0, 0, 255)


def test_the_pdf_writer_path_renders_the_same_pages(paged, typst: TypstRunner):
    """`pypdfium2` is only for assertions about the PDF itself, and has to agree on the pixels."""
    body = (
        "#set page(width: 40pt, height: 30pt, margin: 0pt)\n"
        '#rect(width: 100%, height: 100%, fill: rgb("#ff0000"))\n'
    )
    source = typst.source(body)
    rendered = pdf_pages(paged.pdf(source))
    assert len(rendered) == 1
    assert tuple(rendered[0][15, 20]) == (255, 0, 0)


# The stored reference images.


def test_a_reference_round_trips_losslessly(tmp_path):
    """WebP defaults to lossy, so the policy is only worth anything if this holds."""
    image = np.random.default_rng(0).integers(0, 256, (12, 9, 3), dtype=np.uint8)
    store = Reference(tmp_path, update=False)
    store.write("noise", image)
    with Image.open(store.path("noise")) as stored:
        assert stored.format == "WEBP"
    assert np.array_equal(decode(store.path("noise").read_bytes()), image)


def test_a_missing_reference_writes_one_and_says_how_to_regenerate(tmp_path):
    """A policy without a regeneration command decays into hand-edited binaries."""
    store = Reference(tmp_path, update=False)
    with pytest.raises(AssertionError, match="--update-references"):
        store.check("fresh", canvas(), reason="the harness has to be able to bootstrap one")
    assert store.path("fresh").exists()
    store.check("fresh", canvas(), reason="the harness has to be able to bootstrap one")


def test_a_reference_that_differs_is_reported_with_its_box(tmp_path):
    """The same locating report as every other comparison."""
    store = Reference(tmp_path, update=False)
    store.write("flat", canvas())
    changed = canvas()
    changed[2:4, 6:8] = 0
    with pytest.raises(AssertionError, match=r"x 6\.\.8, y 2\.\.4"):
        store.check("flat", changed, reason="a difference has to be locatable here too")


def test_a_reference_must_say_why_it_is_stored(tmp_path):
    """Stored pixels are the exception, and the exception has to justify itself."""
    store = Reference(tmp_path, update=True)
    with pytest.raises(ValueError, match="say why"):
        store.check("flat", canvas(), reason="")


def test_the_update_flag_rewrites_without_failing(tmp_path):
    """`pytest --update-references` is the regeneration path, and it is not an assertion."""
    store = Reference(tmp_path, update=True)
    store.write("flat", canvas(255))
    store.check("flat", canvas(0), reason="regenerating replaces whatever was there")
    assert np.array_equal(decode(store.path("flat").read_bytes()), canvas(0))


# Tier 3: the browser.


def test_the_browser_tier_actually_launches_every_engine(page, browser_name):
    """If this skips or fails, a third of the suite is not running.

    The engine is asserted rather than assumed, because a parametrisation that silently
    collapsed onto one browser would leave the suite green and half blind.
    """
    agent = page.evaluate("() => navigator.userAgent")
    # Every one of these strings claims to be `AppleWebKit`, and chromium's claims to be
    # `Safari` as well, so the token has to be the one only that engine writes.
    expected = {"chromium": "Chrome/", "firefox": "Firefox/", "webkit": "Version/"}[browser_name]
    assert expected in agent, f"asked for {browser_name}, got {agent}"


def test_a_deck_is_addressed_by_url(deck_at, page):
    """Tests deep-link instead of clicking their way to a state.

    The stand-in deck implements the contract of the deck runtime and nothing else.
    """
    deck = deck_at(STAND_IN_DECK)
    assert deck.position == (1, 0)
    deck.goto(2, 1)
    assert deck.position == (2, 1)
    assert page.url.endswith(state_hash(2, 1))


def test_a_tag_is_found_once_per_occurrence(deck_at):
    """One tag may sit at several places in a slide, so geometry comes back as a list."""
    deck = deck_at(STAND_IN_DECK).goto(1, 1)
    rects = deck.rects("alpha")
    assert len(rects) == 2
    assert rects[0].x < rects[1].x
    assert deck.rects("beta") == []


def test_a_screenshot_decodes_into_an_array(deck_at, page):
    """Images come back as arrays, so the storage format never enters an assertion."""
    deck = deck_at(STAND_IN_DECK).goto(1, 0)
    hidden = screenshot(page)
    deck.goto(1, 1)
    shown = screenshot(page)
    assert hidden.shape == shown.shape
    assert_differs(hidden, shown, what="the slide with and without its tags revealed")


def test_geometry_is_preferred_over_pixels(deck_at):
    """A number survives a glyph rasterisation change, and a screenshot does not.

    This is not an assertion about the harness so much as a worked example of the rule,
    kept here because the rule is easier to follow when something follows it.
    """
    deck = deck_at(STAND_IN_DECK).goto(1, 1)
    first = deck.rects("alpha")
    deck.goto(2, 1).goto(1, 1)
    assert all(a.approx(b) for a, b in zip(first, deck.rects("alpha"), strict=True))


def test_the_reference_fixture_is_wired_to_the_test_module(references, request):
    """References live beside the module that uses them, and the flag reaches them.

    There is deliberately no stored reference image in this repository yet.
    Everything the three tiers assert so far is a comparison within one run,
    so no part of the suite genuinely needs stored pixels.
    """
    assert references.directory == ROOT / "tests" / "references"
    assert references.update is request.config.getoption("--update-references")
    assert not references.directory.exists()
