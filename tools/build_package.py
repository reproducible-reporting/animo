#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Build the subtree that would be copied into the `typst/packages` repository.

Some choices are hard-coded in this script to comply with the requirements of that repository.
This is not meant to be pretty, elegant or reusable code.
"""

import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# Paths of tracked files or directories, which are copied recursively.
# Git refuses a path that matches no tracked file, so a renamed source fails the build.
SOURCES = [
    "src",
    "README.md",
    "CHANGELOG.md",
    "typst.toml",
]


def main():
    """Build the package subtree."""
    with open(ROOT / "typst.toml", "rb") as f:
        config = tomllib.load(f)
    version = config["package"]["version"]

    target = ROOT / "build" / "package" / version
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    # Copy only tracked files, so that a stray file in the working tree is never published.
    paths = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "-z", "--", *SOURCES],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    for path in filter(None, paths):
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, destination)

    # Manually copy LICENSE file to comply with Typst Universe conventions
    shutil.copy2(ROOT / "LICENSES" / "Apache-2.0.txt", target / "LICENSE")


if __name__ == "__main__":
    main()
