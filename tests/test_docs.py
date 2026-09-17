# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""What the documentation site has to hold, whatever anybody writes into it.

Three things are asserted rather than reviewed.
The site serves two readers and the split between their guides erodes one convenient
pointer at a time, so the rule about which way a link may point is a test.
The reference is written by hand, because nothing reads a `//` comment, so the test suite
is what keeps a new primitive from shipping undocumented.
And the example table is written twice, in `README.md` and on the front page of the site,
because the version inside it belongs to `snipwise` and a snippet cannot hold a snippet.
"""

import re

import pytest
from harness import ROOT

DOCS = ROOT / "docs"

# The pages of each guide, which is also the nav of `zensical.toml` read as two sets.
# The reference counts as part of the author guide for the link rule,
# whatever nav section it ends up in.
AUTHOR_GUIDE = (
    "slides.md",
    "tags.md",
    "continuous.md",
    "structural.md",
    "viewport.md",
    "regions.md",
    "numbering.md",
    "outputs.md",
    "presenting.md",
    "performance.md",
    "reference.md",
)
DEVELOPMENT_GUIDE = (
    "development.md",
    "environment.md",
    "testing.md",
    "architecture.md",
    "probes.md",
)

# The front door is outside both guides and is the one page that may link anywhere.
FRONT_DOOR = "index.md"

# A Markdown inline link, whose destination is what every rule below is about.
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)")

# The public names of `src/lib.typ` and `src/anim.typ`, as the reference has to spell them.
# A `#let` at the start of a line is a definition; a name starting with an underscore or
# holding a hyphen that the module does not export is not in the import lists below.
DEFINITION = re.compile(r"(?m)^#let ([a-z][a-z0-9-]*)\s*[=(]")


def pages(names):
    """Yield `(name, text)` for the given pages under `docs/`."""
    for name in names:
        yield name, (DOCS / name).read_text()


def links(text):
    """Every inline link destination in a Markdown text."""
    return LINK.findall(text)


def exported_names():
    """The public names of the package, as a reader of the manual would write them.

    Returns
    -------
    names
        The body-level names of `src/lib.typ`, and the primitives of `src/anim.typ`
        prefixed with `anim.`, which is how the reference lists them.
    """
    names = set()
    for line in (ROOT / "src" / "lib.typ").read_text().split("\n"):
        match = re.match(r'#import "[a-z]+\.typ": (.*)', line)
        if match:
            names.update(part.strip() for part in match.group(1).split(","))
        elif re.match(r'#import "anim\.typ"$', line):
            names.add("anim")
    names.discard("anim")
    # The timeline vocabulary, which is every primitive and `sub`, and nothing else:
    # the module's checkers and its tables are internal and carry no entry.
    primitives = ("sub", "reveal", "hide", "move", "scale", "pan")
    primitives += ("replace", "remove", "apply", "reset")
    defined = set(DEFINITION.findall((ROOT / "src" / "anim.typ").read_text()))
    missing = set(primitives) - defined
    assert not missing, f"the reference lists primitives that anim.typ does not define: {missing}"
    return sorted(names) + [f"anim.{name}" for name in primitives]


# --------------------------------------------------------------------------------------
# Which way a link may point
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", AUTHOR_GUIDE)
def test_author_guide_stays_inside_itself(name):
    """A reader of the author guide never has to leave it to understand a page."""
    text = (DOCS / name).read_text()
    for destination in links(text):
        page = destination.split("#")[0]
        if not page or page.startswith(("http://", "https://")):
            continue
        assert page in AUTHOR_GUIDE or page == FRONT_DOOR, (
            f"{name} links to {page}, which is not in the author guide"
        )


@pytest.mark.parametrize("name", AUTHOR_GUIDE)
def test_author_guide_never_reaches_planning(name):
    """The reasoning belongs to the design document, which the author guide never cites."""
    text = (DOCS / name).read_text()
    assert "planning/" not in text, f"{name} names planning/, which only the front door may"


def test_development_guide_names_planning_once():
    """One page of the development guide holds the reference, and at document level."""
    holders = [name for name, text in pages(DEVELOPMENT_GUIDE) if "planning/" in text]
    assert holders == ["development.md"], (
        f"planning/ is named by {holders}, and the guide refers to it exactly once"
    )


def test_no_page_links_to_a_heading_inside_planning():
    """Such headings move, and a link to one rots without ever failing a build."""
    for path in sorted(DOCS.glob("*.md")):
        for destination in links(path.read_text()):
            assert not re.search(r"planning/.*\.md#", destination), (
                f"{path.name} links to a heading inside {destination}"
            )


# --------------------------------------------------------------------------------------
# The reference covers the public surface
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", exported_names())
def test_reference_has_an_entry(name):
    """A new primitive cannot ship undocumented."""
    text = (DOCS / "reference.md").read_text()
    assert f"### `{name}`\n" in text, f"{name} has no entry in the reference"


@pytest.mark.parametrize("name", exported_names())
def test_reference_entry_points_at_the_guide(name):
    """The reference states and the guide teaches, so an entry says where it is taught."""
    text = (DOCS / "reference.md").read_text()
    parts = text.split(f"### `{name}`\n", 1)
    if len(parts) == 1:
        pytest.skip("the entry is missing, which test_reference_has_an_entry reports")
    body = parts[1].split("\n### ", 1)[0]
    assert "Taught in [" in body, f"the entry for {name} does not say where it is taught"


# --------------------------------------------------------------------------------------
# The example table
# --------------------------------------------------------------------------------------


def table_of(path):
    """The rows of the example table of a Markdown file, in order."""
    rows = []
    inside = False
    for line in path.read_text().split("\n"):
        if line.startswith("## Examples"):
            inside = True
        elif inside and line.startswith("## "):
            break
        elif inside and line.startswith("|"):
            rows.append(line)
    assert rows, f"{path} has no example table"
    return rows


def test_every_example_is_in_the_table():
    """A deck that the build compiles and that nothing points at is a deck nobody reads."""
    rows = "\n".join(table_of(ROOT / "README.md"))
    for path in sorted((ROOT / "examples").glob("*.typ")):
        assert f"`{path.name}`" in rows, f"{path.name} is not in the example table"


@pytest.mark.parametrize("kind", ["source", "deck", "handout"])
def test_every_row_has_its_three_links(kind):
    """Each row offers the source, the animated deck and the handout."""
    suffix = {
        "source": "/examples/{stem}.typ",
        "deck": "/examples/{stem}.html",
        "handout": "/examples/{stem}-handouts.pdf",
    }[kind]
    rows = table_of(ROOT / "README.md")[2:]
    stems = sorted(path.stem for path in (ROOT / "examples").glob("*.typ"))
    assert len(rows) == len(stems)
    for row in rows:
        stem = re.search(r"`([a-z]+)\.typ`", row).group(1)
        assert suffix.format(stem=stem) in row, f"the {stem} row has no {kind} link"


@pytest.mark.parametrize("kind", ["deck", "handout", "presentation"])
def test_every_link_target_exists_after_a_full_build(kind):
    """The site publishes what the table points at, once the decks have been compiled."""
    published = DOCS / "examples"
    if not published.is_dir():
        pytest.skip("run tools/build_examples.py first")
    suffix = {"deck": ".html", "handout": "-handouts.pdf", "presentation": "-presentation.pdf"}
    for path in sorted((ROOT / "examples").glob("*.typ")):
        target = published / f"{path.stem}{suffix[kind]}"
        assert target.is_file(), f"{target} is missing"
