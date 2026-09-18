#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Build the subtree that would be copied into the `typst/packages` repository.

Some choices are hard-coded in this script to comply with the requirements of that repository.
This is not meant to be pretty, elegent, nor reusable code.
"""

import shutil
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


SOURCES = [
    "src/*.typ",
    "src/*.js",
    "src/*.css",
    "README.md",
    "CHANGELOG.md",
    "typst.toml",
]


def main():
    """Build the package subtree."""
    with open(ROOT / "typst.toml", "rb") as f:
        config = tomllib.load(f)
    version = config["package"]["version"]

    target = Path(ROOT / "build" / "package" / version)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    # Copy all source files
    for pattern in SOURCES:
        for source in ROOT.glob(pattern):
            destination = target / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.copy(destination)

    # Manually copy LICENSE file to comply with Typst Universe conventions
    Path(ROOT / "LICENSES" / "Apache-2.0.txt").copy(target / "LICENSE")

    return 0


if __name__ == "__main__":
    main()
