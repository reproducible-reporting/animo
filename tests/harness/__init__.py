# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The test harness of animo: the three tiers, under one runner.

It is imported as `harness` from both `tests/` and `probes/`,
through the `pythonpath` setting in `pyproject.toml`,
so that a probe and a feature test share every fixture.

- `harness.typst` compiles a document and asserts that it did or did not compile.
- `harness.raster` renders the paged outputs and compares them as arrays.
- `harness.browser` drives the HTML output in the chromium `playwright` bundles.
- `harness.references` implements the stored-image policy and its regeneration path.
- `harness.fixtures` is the pytest plugin that ties them to fixture names.
"""

from .browser import Deck, Rect, open_local, screenshot, state_hash
from .raster import (
    Box,
    PagedRunner,
    assert_differs,
    assert_identical,
    assert_identical_outside,
    decode,
    difference_box,
    difference_report,
    load_image,
    pdf_pages,
)
from .references import Reference
from .typst import ROOT, TypstResult, TypstRunner, compile_typst, manifest, write_typst

__all__ = (
    "ROOT",
    "Box",
    "Deck",
    "PagedRunner",
    "Rect",
    "Reference",
    "TypstResult",
    "TypstRunner",
    "assert_differs",
    "assert_identical",
    "assert_identical_outside",
    "compile_typst",
    "decode",
    "difference_box",
    "difference_report",
    "load_image",
    "manifest",
    "open_local",
    "pdf_pages",
    "screenshot",
    "state_hash",
    "write_typst",
)
