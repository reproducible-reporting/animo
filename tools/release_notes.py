#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Extract the notes of one release from `CHANGELOG.md`.

The changelog is where a release is described, and a GitHub release that restated it would
be a second copy to keep in step. So the workflow reads the section out of the file rather
than being handed a text of its own.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A version heading of Keep a Changelog, as `## [0.1.0] - 2026-09-16`.
HEADING = re.compile(r"^## \[(?P<version>[^\]]+)\]")


def notes(text: str, version: str) -> str:
    """The body of one version's section, without its heading.

    Parameters
    ----------
    text
        The whole changelog.
    version
        The version to look for, without a `v` prefix.

    Returns
    -------
    notes
        Everything between that version's heading and the next one, stripped.

    Raises
    ------
    KeyError
        When the changelog has no section for that version.
    """
    lines = text.split("\n")
    starts = [
        (index, match["version"])
        for index, line in enumerate(lines)
        if (match := HEADING.match(line))
    ]
    for position, (index, found) in enumerate(starts):
        if found != version:
            continue
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        return "\n".join(lines[index + 1 : end]).strip()
    raise KeyError(version)


def main() -> int:
    """Print the notes of the requested version and return a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "version",
        help="the version, with or without a `v` prefix or a `refs/tags/` prefix",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        default=ROOT / "CHANGELOG.md",
        help="the changelog to read",
    )
    args = parser.parse_args()
    version = args.version.removeprefix("refs/tags/").removeprefix("v")
    try:
        print(notes(args.changelog.read_text(), version))
    except KeyError:
        print(f"{args.changelog} has no section for {version}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
