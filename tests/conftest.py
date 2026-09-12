# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Fixtures shared by the whole test suite."""

import shutil

import pytest
from helpers import ROOT


@pytest.fixture
def scratch(request):
    """An empty directory, inside the repository, for a document that a test compiles.

    Typst refuses a source file outside its project root,
    so a generated document cannot live in `tmp_path`.
    """
    path = ROOT / "tmp" / "pytest" / request.node.name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path
