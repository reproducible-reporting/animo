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


def ls_files(*arguments: str) -> list[Path]:
    """The files `git ls-files` reports, as paths relative to the repository root.

    Parameters
    ----------
    arguments
        Further arguments for `git ls-files`.

    Returns
    -------
    paths
        The reported files, in the order git reports them.
    """
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", *arguments],
        capture_output=True,
        check=True,
        text=True,
    )
    return [Path(name) for name in result.stdout.split("\0") if name]


def tracked() -> list[Path]:
    """Every file git tracks, as paths relative to the repository root.

    Tracked files rather than a directory walk, because a build product is never part of a
    release and a directory walk would have to learn `.gitignore` to know that.
    """
    return ls_files()


def excluded(patterns: list[str]) -> set[Path]:
    """The tracked files that the `exclude` list of the manifest matches.

    Parameters
    ----------
    patterns
        The `exclude` list of the manifest.

    Returns
    -------
    excluded
        The matching files, relative to the repository root.

    Notes
    -----
    An entry of that list is a glob with the semantics of a line of a `.gitignore` file, as
    the manifest format of typst defines it.
    A pattern matches at any depth, and a leading slash anchors it to the repository root,
    so the matching is left to git rather than reimplemented here.
    The standard exclude sources are left out, because a file that `.gitignore` covers is
    untracked and therefore already absent.
    """
    if len(patterns) == 0:
        return set()
    arguments = ["--cached", "--ignored", *(f"--exclude={pattern}" for pattern in patterns)]
    return set(ls_files(*arguments))


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
    dropped = excluded(manifest().get("exclude", []))
    files = [path for path in tracked() if path not in dropped]
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
