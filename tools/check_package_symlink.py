#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Check the repository-local package directory against the manifest.

The working tree resolves as `@preview/animo:X.Y.Z` through a symlink whose name is the
version, so a version bump that leaves the name behind makes every document that imports
the package fail to compile.
The test suite asserts the same invariant, and this script brings the failure forward to
the commit that bumps the version.
"""

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PACKAGES = ROOT / ".typst-packages" / "preview" / "animo"


def main():
    """Report every disagreement between the manifest and the package directory."""
    with open(ROOT / "typst.toml", "rb") as handle:
        version = tomllib.load(handle)["package"]["version"]

    expected = PACKAGES / version
    problems = []

    problems = [
        f"{entry.relative_to(ROOT)} is named after a version that is not in the manifest. "
        f"Rename it with `git mv` to {expected.relative_to(ROOT)}."
        for entry in sorted(PACKAGES.iterdir())
        if entry.name != version
    ]

    # A stale name is reported with the rename that repairs it,
    # so the entry it has to become is not reported as missing on top of that.
    if expected.is_symlink():
        if expected.resolve() != ROOT:
            problems.append(
                f"{expected.relative_to(ROOT)} resolves to {expected.resolve()} "
                f"instead of the root of the repository. Run ./setup.sh."
            )
    elif not problems:
        problems.append(
            f"{expected.relative_to(ROOT)} is missing or is not a symlink. Run ./setup.sh."
        )

    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
