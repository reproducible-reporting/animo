# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The environment itself: the toolchain pin and the two import paths.

These tests assert nothing about animo's behaviour.
They fail when the development environment is broken,
which is the failure that is otherwise the hardest to recognise.
"""

import re
import shutil
import subprocess

import pytest
from harness import ROOT, compile_typst, manifest, write_typst


def test_typst_on_path_matches_the_manifest():
    """A mismatched toolchain must fail here rather than in an unrelated test later."""
    binary = shutil.which("typst")
    assert binary is not None, "typst is not on PATH"
    proc = subprocess.run([binary, "--version"], capture_output=True, text=True, check=True)
    match = re.search(r"\btypst (\d+\.\d+\.\d+)\b", proc.stdout)
    assert match is not None, f"unexpected version banner: {proc.stdout!r}"
    assert match.group(1) == manifest()["compiler"]


def test_package_symlink_points_at_the_working_tree():
    """`@preview/animo:X.Y.Z` may only ever resolve to this working tree."""
    version = manifest()["version"]
    link = ROOT / ".typst-packages" / "preview" / "animo" / version
    assert link.is_symlink()
    assert link.resolve() == ROOT


@pytest.mark.parametrize("name", ["import_preview.typ", "import_root.typ"])
def test_import_path_compiles(name, tmp_path):
    """Both import paths resolve from a single working tree, at the same time."""
    source = ROOT / "tests" / "documents" / name
    compile_typst(source, tmp_path / "out.pdf").check()


@pytest.mark.parametrize("name", ["import_preview.typ", "import_root.typ"])
def test_import_path_compiles_to_html(name, tmp_path):
    """The HTML target is behind a feature flag, and the helper has to pass it."""
    source = ROOT / "tests" / "documents" / name
    compile_typst(source, tmp_path / "out.html", fmt="html", features=["html"]).check()


def test_compile_helper_reports_failure_instead_of_raising(scratch):
    """The tier-1 runner is built on this: a failure is a value, not an exception."""
    source = write_typst(scratch, '#import "/src/lib.typ": *\n#assert(false, message: "boom")\n')
    result = compile_typst(source, scratch / "out.pdf")
    assert not result.ok
    assert "boom" in result.stderr
