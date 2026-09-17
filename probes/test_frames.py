# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *The frame is the smallest unit of DOM addressability*.

This is the finding that forces the whole epoch model.
If a sub-area of a frame could be given its own DOM node, animo would swap regions
instead of re-rendering slides, and epochs would not exist.
Every probe here is a way in which that is not possible.
"""

from harness import TypstRunner, compile_typst


def test_html_elem_inside_a_frame_is_dropped(typst: TypstRunner):
    """A region cannot be its own HTML element inside a slide frame.

    The compiler warns and carries on, which is worse than an error:
    the element is simply not there.
    """
    result = typst.warns(
        '#html.frame[#html.elem("span", "hi") text]\n',
        "elem may not occur inside of a paragraph and was ignored",
        html=True,
    )
    assert result.ok


def test_a_nested_frame_contributes_no_second_svg(typst: TypstRunner):
    """Nesting frames is not a route to independently swappable sub-frames either.

    It compiles without complaint, which again hides the failure,
    so the assertion is on the output and not on a diagnostic.
    """
    path = typst.html("#html.frame[outer #html.frame[inner]]\n")
    assert path.read_text().count("<svg") == 1


def test_set_page_inside_a_frame_is_an_error(typst: TypstRunner):
    """A slide is a sized `block` in the HTML target, never a page."""
    typst.fails(
        "#html.frame[#set page(width: 5cm); x]\n",
        "page configuration is not allowed inside of containers",
        html=True,
    )


def test_set_page_at_document_level_is_ignored_in_html(typst: TypstRunner):
    """Slide size, background colour and background image have to be emitted as CSS.

    This is the document-level half of the previous probe,
    and it is a warning rather than an error, so a deck that sets a page silently loses it.
    """
    typst.warns(
        "#set page(width: 10cm, height: 6cm)\nbody\n",
        "page set rule was ignored during HTML export",
        html=True,
    )


def test_html_export_needs_the_feature_flag(typst: TypstRunner):
    """HTML export is still behind `--features html` in this release.

    The flag goes through `compile_typst` rather than the runner,
    because the runner adds the feature itself for every HTML compilation.
    """
    source = typst.source("#html.frame[x]\n")
    result = compile_typst(source, output="-", fmt="html")
    assert not result.ok
    assert "html export is only available when `--features html` is passed" in result.stderr


def test_the_html_target_still_warns_that_it_is_incomplete(typst: TypstRunner):
    """The residual risk of the whole design, stated by the compiler on every compilation."""
    typst.warns(
        "body\n",
        "html export is under active development and incomplete",
        html=True,
    )
