# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Read the SVG that typst emits, as a tree rather than with a regular expression.

Several probes are about what is *inside* a labelled group,
which nesting makes awkward to express as a pattern.
The SVG itself is well-formed XML, so it parses;
the HTML around it is not, so the fragments are cut out first.
"""

import re
import xml.etree.ElementTree as ET

__all__ = ("SVG", "group", "groups", "parse", "svg_fragments")

SVG = "{http://www.w3.org/2000/svg}"
"""The SVG namespace, as `ElementTree` spells it in a tag name."""


def svg_fragments(markup: str) -> list[str]:
    """Every `<svg>..</svg>` fragment of a document, in document order.

    An SVG export is one fragment; an HTML export is one per `html.frame`.
    """
    return re.findall(r"<svg\b.*?</svg>", markup, re.S)


def parse(markup: str, index: int = 0) -> ET.Element:
    """Parse the n-th SVG fragment of a document into an element tree."""
    fragments = svg_fragments(markup)
    if not fragments:
        raise AssertionError("the document contains no SVG at all")
    return ET.fromstring(fragments[index])


def groups(root: ET.Element, label: str) -> list[ET.Element]:
    """Every group carrying this tag, in document order."""
    return root.findall(f".//{SVG}g[@data-typst-label='{label}']")


def group(root: ET.Element, label: str) -> ET.Element:
    """The single group carrying this tag, asserting that there is exactly one."""
    found = groups(root, label)
    if len(found) != 1:
        raise AssertionError(f"expected one group labelled {label!r}, found {len(found)}")
    return found[0]
