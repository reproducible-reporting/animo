# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Probes for *The head of a page that a package builds itself*.

A deck builds the `<html>` element itself, because the stylesheet and the runtime go into its
head, and typst then leaves the head to it.
These probes assert what that leaves the package to do and what it can read to do it.
"""

from harness import TypstRunner

# What typst writes into a head it builds itself, from the settings a document states.
SETTINGS = """\
#set document(title: [A *bold* "title"], author: "A. Author", description: [About it.])
#set text(lang: "nl", region: "be")
"""


def test_typst_writes_the_title_and_the_language_into_a_head_it_builds(typst: TypstRunner):
    """The reference: a document that builds no head gets both from typst.

    The title is the plain text of the content it was set to.
    Typst 0.15.0 names the authors `authors`, where the name HTML defines is `author`.
    """
    markup = typst.html(SETTINGS + "Text\n").read_text()
    assert '<html lang="nl-BE">' in markup
    assert '<title>A bold "title"</title>' in markup
    assert '<meta name="authors" content="A. Author">' in markup
    assert '<meta name="description" content="About it.">' in markup


def test_typst_writes_neither_into_a_head_a_package_builds(typst: TypstRunner):
    """A root `html` element is taken as it is, so the package has to write both itself."""
    markup = typst.html(
        SETTINGS + '#html.html({ html.head(html.meta(charset: "utf-8")); html.body[Text] })\n'
    ).read_text()
    assert "<html>" in markup
    assert "<title>" not in markup
    assert 'name="author"' not in markup


def test_a_package_reads_the_settings_in_a_context(typst: TypstRunner):
    """Both are settable fields of an element, so a context block reads them where it is."""
    typst.ok(
        SETTINGS
        + """#context {
  assert.eq(document.title, [A *bold* "title"])
  assert.eq(document.author, ("A. Author",))
  assert.eq(text.lang, "nl")
  assert.eq(text.region, "BE")
}
""",
        html=True,
    )


def test_a_title_element_takes_text_and_not_markup(typst: TypstRunner):
    """`html.title` refuses content with markup in it, so a title has to be made plain first."""
    typst.fails(
        "#html.html({ html.head(html.title([A *bold* title])); html.body[Text] })\n",
        "HTML raw text element cannot have non-text children",
        html=True,
    )


def test_a_document_rule_inside_a_show_rule_for_everything_is_refused(typst: TypstRunner):
    """In HTML the settings an author states therefore precede a show rule that builds the page.

    A show rule that hands the document back as it is, or in a context block, leaves a later
    rule at the top level. One that puts it in an element, as a deck's show rule does in the
    HTML target, makes it a rule inside a container.
    """
    for rule in ("body => body", "body => context body"):
        typst.ok(f"#show: {rule}\n#set document(title: [Late])\nText\n", html=True)
    typst.fails(
        '#show: body => html.elem("div", body)\n#set document(title: [Late])\nText\n',
        "document set rules are not allowed inside of containers",
        html=True,
    )
