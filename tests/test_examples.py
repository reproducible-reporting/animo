# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""What every deck under `examples/` has to have in common.

The decks are the unit of documentation: a page shows one by including the file,
so a reader who copies one has to get the same result as the reader who copied another.
That needs a shared shape and nothing but the fonts typst embeds.
`plan.py` already compiles each of them to all three output types,
so a broken example fails there.
These tests are about the agreement between the outputs.
"""

import re

import pytest
from harness import ROOT, manifest

# The deck's shape, as `examples/tour.typ` declares it.
SHAPE = "animo.with(width: 16cm, height: 9cm, margin: 1cm)"

PATHS = sorted((ROOT / "examples").glob("*.typ"))


def test_there_are_examples():
    """A glob that silently matches nothing would make every test below vacuous."""
    assert PATHS


@pytest.mark.parametrize("path", PATHS, ids=lambda path: path.name)
def test_example_declares_the_shared_shape(path):
    """One slide size across the decks, so that two of them read as one set."""
    assert f"#show: {SHAPE}" in path.read_text()


@pytest.mark.parametrize("path", PATHS, ids=lambda path: path.name)
def test_example_leaves_the_fonts_alone(path):
    """A deck that names a font renders differently for a reader who lacks it.

    The fonts typst embeds are the only ones every reader has,
    and they are what a deck gets by setting no font at all.
    """
    assert re.search(r"\bfont\s*:", path.read_text()) is None


@pytest.mark.parametrize("path", PATHS, ids=lambda path: path.name)
def test_example_imports_the_published_package(path):
    """A reader copies an example and compiles it unchanged, so the import is the real one."""
    version = manifest()["version"]
    assert f'#import "@preview/animo:{version}"' in path.read_text()
