# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Other verified behaviour*.

The short entries: target detection, the HTML element API, multi-page export,
and the import rules that decide how animo's names are spelled.
The import probes go through a stand-in module under `documents/toy/`,
which is shaped like animo but is not animo, so that a failure names typst's rule.
"""

import pytest
from harness import TypstRunner, compile_typst
from PIL import Image

TOY = '#import "/probes/documents/toy/lib.typ": *\n'


def test_target_names_the_two_targets(typst: TypstRunner):
    """`target()` is the clean way to branch, and animo branches on it everywhere."""
    typst.ok('#context { assert.eq(target(), "paged") }\n')
    typst.ok('#context { assert.eq(target(), "html") }\n', html=True)


def test_html_elem_takes_attributes_and_html_div_does_not(typst: TypstRunner):
    """Anything carrying a data attribute has to be built with `html.elem`."""
    path = typst.html('#html.elem("div", attrs: (class: "x", "data-animo": "1"))[hi]\n')
    assert '<div class="x" data-animo="1">' in path.read_text()
    typst.fails('#html.div(attrs: (class: "x"))[hi]\n', "unexpected argument: attrs", html=True)


def test_multi_page_export_needs_a_page_number_template(typst: TypstRunner):
    """Handout SVG is one file per page, so the destination has to carry `{p}`."""
    source = typst.source(
        "#set page(width: 100pt, height: 60pt)\na #pagebreak() b\n",
    )
    result = compile_typst(source, typst.scratch / "out.svg", fmt="svg")
    assert not result.ok
    assert "page number template" in result.stderr


def test_a_document_without_pages_becomes_one_blank_default_page(typst: TypstRunner):
    """Typst does not refuse a document that lays nothing out.

    This is what makes animo refuse a handout whose every state gave up its page:
    left to typst, such a deck compiles to one blank page at typst's own default size,
    which reads as a rendering failure rather than as the flag doing what it was told.
    Measured on typst 0.15.0.
    """
    source = typst.source("#context { let _ = 1 }\n")
    compile_typst(source, typst.scratch / "blank-{p}.png", fmt="png", ppi=36).check()
    pages = sorted(typst.scratch.glob("blank-*.png"))
    assert len(pages) == 1, pages
    # A4 at 36 dots per inch, which is typst's default page and not a size the deck asked for.
    assert Image.open(pages[0]).size == (298, 421)


def test_a_code_block_joins_array_returning_calls(typst: TypstRunner):
    """This is what makes `animation: { sub(..) sub(..) }` a list of steps.

    No accumulator, no side effects, and an empty call yields an empty step.
    """
    typst.ok(
        TOY
        + """
#let steps = {
  import anim: *
  sub(reveal("a"))
  sub()
  sub(move("a", x: 1pt))
}
#assert.eq(steps.len(), 3)
#assert.eq(steps.at(1).ops, ())
#assert.eq(steps.at(2).ops.first().kind, "move")
"""
    )


def test_a_star_import_carries_the_submodule_along(typst: TypstRunner):
    """One `#import "@preview/animo:x.y.z": *` has to provide the `anim` module as a name."""
    typst.ok(TOY + "#assert.eq(type(anim), module)\n#assert.eq(type(mark), function)\n")


def test_all_three_usage_forms_work(typst: TypstRunner):
    """A star import, a named import and fully-qualified calls, side by side."""
    typst.ok(
        """
#import "/probes/documents/toy/lib.typ": *
#import "/probes/documents/toy/lib.typ": anim, mark
#assert.eq(anim.reveal("a").kind, "reveal")
#let inner = {
  import anim: *
  reveal("a")
}
#assert.eq(inner.kind, "reveal")
"""
    )


def test_the_block_scoped_import_does_not_leak(typst: TypstRunner):
    """Inside the block the primitives win; outside it the built-ins are untouched.

    This is the whole reason the timeline vocabulary is imported inside the animation
    argument rather than at the top of the file.
    """
    typst.ok(
        TOY
        + """
#let inner = {
  import anim: *
  (move: move, hide: hide, scale: scale)
}
#assert.ne(inner.move, std.move)
#assert.ne(inner.hide, std.hide)
#assert.ne(inner.scale, std.scale)
#assert(move == std.move)
#assert(hide == std.hide)
#assert(scale == std.scale)
"""
    )


def test_an_unknown_primitive_silently_falls_through_to_the_standard_library(
    typst: TypstRunner,
):
    """The footgun that forces `sub` to validate its own arguments.

    A star import falls through to the standard library for every name the module does not
    define, so a mistyped or unsupported primitive does not error.
    It returns content, which surfaces much later as a confusing "does not have field" error.
    """
    typst.ok(
        TOY
        + """
#let footgun = {
  import anim: *
  rotate("b", 45deg)
}
#assert.eq(type(footgun), content)
"""
    )


def test_the_package_name_is_still_free():
    """Recorded as unprobeable rather than faked.

    `packages/preview/animo` returned 404 on Typst Universe when the design was written,
    which is why the name was chosen.
    Asserting it would make the test suite depend on the network and on a third party's
    repository, and the answer only matters once, at submission time,
    where the release path checks it anyway.
    """
    pytest.skip("checking Typst Universe would make the suite depend on the network")
