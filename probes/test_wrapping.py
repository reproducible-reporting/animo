# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Wrapping a tag site: what it changes and what it does not*.

A tag has to wrap its body to become an addressable group,
and the wrapper must not move the slide around it.
Rasterising the same page with and without the wrapper says exactly what a wrapper costs,
and the answer is not the expected one:
a `box` and a `block` are interchangeable in a flow, and what matters is the width.
"""

import pytest
from harness import PagedRunner, TypstRunner, assert_differs, assert_identical

PAGE = """\
#set page(width: 12cm, height: 9cm, margin: 1cm)
#set text(size: 11pt)
"""

# One body between two paragraphs, which is where tagged block-level content sits.
FLOW = "Before.\n\nBODY\n\nAfter the body there is a paragraph of text that says something."

# The three wrappers a tag could use, each applied twice, as the two nested slots.
WRAPPERS = {
    "box": "box(box(X))",
    "block": "block(block(X))",
    "fill": "block(width: 100%, block(width: 100%, X))",
}

# Bodies whose rendering does not depend on the width they are given.
WIDTH_BLIND = ("list([one], [two])", "grid(columns: 2, gutter: 4pt)[a][b]", "table(columns: 2)[a][b]")

# Bodies the container was centring, which only a filling wrapper keeps centred.
CENTRED = ("figure(rect(width: 2cm, height: 1cm), caption: [cap])", "$ x^2 + y^2 = z^2 $", "align(center)[centred]")


def flow(body: str) -> str:
    """A page holding the body between two paragraphs."""
    return PAGE + FLOW.replace("BODY", "#" + body)


def wrapped(body: str, wrapper: str) -> str:
    """The same page with the body inside the wrapper, twice."""
    return flow(WRAPPERS[wrapper].replace("X", body))


@pytest.mark.parametrize("body", WIDTH_BLIND)
@pytest.mark.parametrize("wrapper", list(WRAPPERS))
def test_every_wrapper_is_invisible_around_width_blind_content(paged: PagedRunner, body, wrapper):
    """A box and a block render identically for content that sits between paragraph breaks.

    This is the measurement that says `box` versus `block` is the wrong question to ask.
    """
    plain = paged.png(flow(body), ppi=144)[0]
    assert_identical(plain, paged.png(wrapped(body, wrapper), ppi=144)[0], what=f"{wrapper} {body}")


@pytest.mark.parametrize("body", CENTRED)
def test_only_a_filling_wrapper_keeps_centred_content_centred(paged: PagedRunner, body):
    """A wrapper at `width: auto` hugs, and hugging left-aligns what the container centred.

    So the choice a tag makes is hugging versus filling,
    and the filling wrapper is `block(width: 100%)` rather than a bare `block`.
    """
    plain = paged.png(flow(body), ppi=144)[0]
    # A block equation comes back to within one greyscale step on five pixels rather than
    # bit-exact, which is the rounding of a fractional position and not a shift.
    assert_identical(
        plain,
        paged.png(wrapped(body, "fill"), ppi=144)[0],
        tol=1,
        what=f"fill {body}",
    )
    for hugging in ("box", "block"):
        assert_differs(
            plain,
            paged.png(wrapped(body, hugging), ppi=144)[0],
            what=f"{hugging} {body}",
        )


@pytest.mark.parametrize("wrapper", list(WRAPPERS))
def test_a_heading_shifts_under_every_wrapper(paged: PagedRunner, wrapper):
    """The one construct no wrapper reproduces, because it carries its own block spacing.

    The spacing sits at the wrapper's edge and is trimmed there,
    and the wrapper contributes the generic one instead.
    Tagging the heading's text rather than the heading is the way around it.
    """
    assert_differs(
        paged.png(flow("[= A Heading]"), ppi=144)[0],
        paged.png(wrapped("[= A Heading]", wrapper), ppi=144)[0],
        what=f"{wrapper} heading",
    )


def test_tagging_the_text_of_a_heading_does_not_shift_it(paged: PagedRunner):
    """The remedy the manual gives, verified rather than assumed."""
    assert_identical(
        paged.png(flow("[= A Heading]"), ppi=144)[0],
        paged.png(PAGE + FLOW.replace("BODY", "= #box(box[A Heading])"), ppi=144)[0],
        what="a heading tagged through its text",
    )


def test_a_tagged_inline_phrase_stops_breaking_across_lines(paged: PagedRunner):
    """The cost of tagging inline content, and it is inherent rather than a choice.

    A group that CSS can translate cannot be split over two lines,
    so a phrase long enough to straddle a line break makes its paragraph reflow.
    """
    paragraph = (
        "Some text before PHRASE and after it, with enough words to force a line break here."
    )
    phrase = "a much longer tagged phrase that may well straddle a line break in the paragraph"
    plain = paged.png(PAGE + paragraph.replace("PHRASE", phrase), ppi=144)[0]
    tagged = paged.png(
        PAGE + paragraph.replace("PHRASE", f"#box(box[{phrase}])"),
        ppi=144,
    )[0]
    assert_differs(plain, tagged, what="a boxed phrase")


def test_the_spacing_a_wrapper_would_have_to_restore_cannot_be_read(typst: TypstRunner):
    """Which is why the heading shift is documented rather than corrected.

    Most settable fields are readable from a context block, and these two are not.
    """
    typst.ok("#context { let _ = (text.size, par.spacing, heading.numbering) }")
    typst.fails(
        "#context { let _ = heading.above }",
        "function `heading` does not contain field `above`",
    )
    typst.fails(
        "#context { let _ = block.spacing }",
        "function `block` does not contain field `spacing`",
    )
