# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *Introspection: the corner of an element, in both targets*.

`pan(relto:)` needs the top-left corner of a tag's wrapper, and the two targets can only
read it by different means: typst from a position on paper, the browser from the origin of
a group in the frame. These probes assert the three behaviours that make those two agree.

- Typst records a box that sits on a line at the line's baseline, not at its corner,
  in the middle of the line and at the start of a paragraph alike,
  while the same box as the only content of a placement is recorded at its corner.
  So an element's own position does not say where it starts.
- A zero-size marker placed at `top + left` inside the box is recorded at the box's corner,
  wherever the box sits, and it changes no pixel of the page.
- That corner is the origin of the box's labelled group in the SVG of an `html.frame`.
"""

from harness import PagedRunner, TypstRunner, assert_identical

# A body with a box in the middle of a line, a box that opens a paragraph, a box inside an
# equation and a box in a list item, each labelled, with an optional corner marker inside.
# The squares are taller than the text, so the top of each line is the top of its square.
SITES = """
#let corner(name) = if MARKED { place(top + left, [#metadata(name)<corner>]) }
#let site(name, body) = [#box({ corner(name); box(body) })#label(name)]
#let body = block(width: 400pt, height: 300pt, inset: 10pt)[
  Words #site("mid", rect(width: 12pt, height: 12pt)) and more words.

  #site("opening", rect(width: 12pt, height: 12pt)) opens this paragraph.

  $ x = #site("math", $y^2$) + z $

  - one
  - #site("item")[two]
]
"""

PAGED = "#set page(width: 400pt, height: 300pt, margin: 0pt)\n#body\n"

NAMES = ("mid", "opening", "math", "item")


def sites(marked: bool = True) -> str:
    """The body above, with or without the corner markers."""
    return SITES.replace("MARKED", "true" if marked else "false")


def test_a_box_in_the_middle_of_a_line_is_located_at_the_baseline(typst: TypstRunner):
    """An element's own position is one box height below its corner here.

    That is the disagreement a `relto` read off the tag's own position would have with the
    browser, which reads the group's origin, and it is a whole line for text.
    """
    typst.ok(
        sites()
        + PAGED
        + """
#context {
  let at(name) = query(label(name)).first().location().position()
  let corner(name) = query(<corner>).find(it => it.value == name).location().position()
  assert.eq(at("mid").x, corner("mid").x)
  assert.eq(at("mid").y - corner("mid").y, 12pt, message: repr((at("mid"), corner("mid"))))
}
"""
    )


def test_a_box_that_opens_its_paragraph_is_located_at_the_baseline_too(typst: TypstRunner):
    """The start of a paragraph is still a line, so it is no way around the baseline."""
    typst.ok(
        sites()
        + PAGED
        + """
#context {
  let at = query(<opening>).first().location().position()
  let corner = query(<corner>).find(it => it.value == "opening").location().position()
  assert.eq(at.y - corner.y, 12pt, message: repr((at, corner)))
}
"""
    )


def test_a_box_that_is_all_a_placement_holds_is_located_at_its_corner(typst: TypstRunner):
    """The same box, placed on its own, is recorded at its corner after all.

    So no correction by the box's own height recovers the corner from the position:
    whether one applies depends on what the box happens to sit in.
    """
    typst.ok(
        sites()
        + PAGED
        + """
#place(dx: 200pt, dy: 200pt, site("placed", rect(width: 12pt, height: 12pt)))
#context {
  let at = query(<placed>).first().location().position()
  let corner = query(<corner>).find(it => it.value == "placed").location().position()
  assert.eq(at, corner, message: repr((at, corner)))
}
"""
    )


def test_a_placed_marker_is_located_at_its_containers_corner_even_off_the_page(
    typst: TypstRunner,
):
    """A position may be negative, which is what a panned page puts the canvas origin at."""
    typst.ok(
        """
#set page(width: 100pt, height: 100pt, margin: 0pt)
#place(top + left, dx: -30pt, dy: -20pt, block(width: 300pt, height: 300pt)[
  #place(top + left, [#metadata(none)<origin>])
  #place(dx: 50pt, dy: 40pt, box(width: 10pt, height: 10pt)[
    #place(top + left, [#metadata(none)<inside>])
  ])
])
#context {
  assert.eq(query(<origin>).first().location().position(), (page: 1, x: -30pt, y: -20pt))
  assert.eq(query(<inside>).first().location().position(), (page: 1, x: 20pt, y: 20pt))
}
"""
    )


def test_a_corner_marker_changes_no_pixel(paged: PagedRunner):
    """The marker takes no room, in a line, in an equation and in a list alike."""
    assert_identical(
        paged.png(sites(marked=False) + PAGED, ppi=144)[0],
        paged.png(sites() + PAGED, ppi=144)[0],
        what="the page with and without the corner markers",
    )


def test_the_corner_on_paper_is_the_group_origin_in_the_browser(page, typst: TypstRunner):
    """The two targets read the same point by different means, and agree on it.

    The browser's numbers are handed to the paged compilation of the same source, which
    asserts the agreement where its own positions are.
    """
    source = typst.source(
        sites()
        + """
#context if target() == "html" { html.frame(body) } else {
  page(width: 400pt, height: 300pt, margin: 0pt, body)
}
#context if target() == "paged" {
  for name in NAMES {
    let at = query(<corner>).find(it => it.value == name).location().position()
    for (axis, value) in (("x", at.x), ("y", at.y)) {
      let browser = float(sys.inputs.at(name + "-" + axis))
      assert(
        calc.abs(value.pt() - browser) < 0.01,
        message: name + " " + axis + ": paper " + repr(value) + ", browser " + repr(browser),
      )
    }
  }
}
""".replace("NAMES", repr(NAMES).replace("'", '"'))
    )
    page.goto(typst.html(source).resolve().as_uri())
    origins = page.evaluate(
        """() => Object.fromEntries(Array.from(
            document.querySelectorAll('[data-typst-label]'),
            (group) => {
                const frame = group.ownerSVGElement.getScreenCTM().inverse();
                const corner = frame.multiply(group.getScreenCTM());
                return [group.dataset.typstLabel, [corner.e, corner.f]];
            },
        ))"""
    )
    assert sorted(origins) == sorted(NAMES)
    inputs = {}
    for name, (x, y) in origins.items():
        inputs[f"{name}-x"], inputs[f"{name}-y"] = repr(x), repr(y)
    typst.ok(source, sysinp=inputs)
