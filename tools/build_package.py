#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Build the subtree that would be copied into `typst/packages`.

The published archive is the tracked files of this repository minus the `exclude` list of
`typst.toml`, and the Universe package checker reads that subtree rather than the working
tree. Those are not the same directory, so the checker has to be pointed at a copy of it.

This script writes that copy and prints where it went.
"""

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def manifest() -> dict:
    """The `[package]` table of `typst.toml`."""
    with (ROOT / "typst.toml").open("rb") as handle:
        return tomllib.load(handle)["package"]


def tracked() -> list[Path]:
    """Every file git tracks, as paths relative to the repository root.

    Tracked files rather than a directory walk, because a build product is never part of a
    release and a directory walk would have to learn `.gitignore` to know that.
    """
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
        text=True,
    )
    return [Path(name) for name in result.stdout.split("\0") if name]


def included(path: Path, exclude: list[str]) -> bool:
    """Whether a tracked file belongs in the published archive.

    Parameters
    ----------
    path
        The file, relative to the repository root.
    exclude
        The `exclude` list of the manifest, whose entries are files or directories.

    Returns
    -------
    included
        Whether the file is neither excluded itself nor inside an excluded directory.
    """
    parts = path.parts
    return not any(
        path == Path(entry) or parts[: len(Path(entry).parts)] == Path(entry).parts
        for entry in exclude
    )


def build(destination: Path) -> list[Path]:
    """Write the publishable subtree and return the files it holds.

    Parameters
    ----------
    destination
        The directory to write, which is emptied first.

    Returns
    -------
    files
        The files that were copied, relative to the repository root.
    """
    exclude = manifest().get("exclude", [])
    files = [path for path in tracked() if included(path, exclude)]
    if destination.exists():
        shutil.rmtree(destination)
    for path in files:
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    return files


def main() -> int:
    """Build the subtree and return a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--destination",
        type=Path,
        default=ROOT / "build" / "package",
        help="where to write the subtree, emptied first",
    )
    args = parser.parse_args()

    files = build(args.destination)
    entrypoint = args.destination / manifest()["entrypoint"]
    if not entrypoint.is_file():
        print(f"the entrypoint {entrypoint} is not in the subtree", file=sys.stderr)
        return 1
    print(f"{len(files)} files in {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
