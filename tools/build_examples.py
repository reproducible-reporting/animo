#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Compile every example deck to every output type, for the documentation site.

The decks land in `docs/examples/`, which the site build copies to `site/examples/`,
so that the example table can link to a deck a reader opens in a browser.
They are build products in a source tree, which `.gitignore` covers.

Compiling here rather than in a task runner keeps the documentation to two commands,
and it is also a test: a deck that the manual points at has to compile to all three
output types, and this script is what fails when one does not.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Where the site publishes a deck from, and where the multi-page export is exercised.
# The SVG pages are not published: they are one file per page, which is clutter beside
# the three products a reader follows a link to, and the format is what is being tested.
PUBLISHED = ROOT / "docs" / "examples"
SCRATCH = ROOT / "build" / "examples"

# Rendering has to be reproducible between a contributor's machine and continuous
# integration, so every compilation uses only the fonts typst embeds.
COMMON = ("--root", str(ROOT), "--ignore-system-fonts")


def products(name: str) -> list[tuple[list[str], Path]]:
    """The four compilations of one deck, as compiler arguments and a destination.

    Parameters
    ----------
    name
        The stem of the deck, which every destination is named after.

    Returns
    -------
    products
        One pair per compilation: the arguments that select the output,
        and the path typst writes.
    """
    return [
        # The HTML presentation.
        (["--format", "html", "--features", "html"], PUBLISHED / f"{name}.html"),
        # The static presentation, one page per subslide.
        (
            ["--input", "animo=presentation"],
            PUBLISHED / f"{name}-presentation.pdf",
        ),
        # The static handouts, one page per slide, which is animo's default paged mode.
        ([], PUBLISHED / f"{name}-handouts.pdf"),
        # The same handout pages as SVG. The paged mode and the file format are
        # independent, so this is a second format of the third output type rather than a
        # fourth type. It is here because the multi-page export path needs a page number
        # template in the destination and so is the one path a PDF run does not cover.
        (["--format", "svg"], SCRATCH / f"{name}-handouts-{{p}}.svg"),
    ]


def compile_deck(source: Path) -> bool:
    """Compile one deck to every output type and report whether all of them succeeded.

    Parameters
    ----------
    source
        The `.typ` file of the deck.

    Returns
    -------
    ok
        Whether every compilation of this deck exited zero.
    """
    ok = True
    for selection, destination in products(source.stem):
        destination.parent.mkdir(parents=True, exist_ok=True)
        args = ["typst", "compile", *COMMON, *selection, str(source), str(destination)]
        # The working tree resolves as `@preview/animo:0.1.0` through a repository-local
        # package directory, so that the deck the site shows is the deck a reader copies.
        env = dict(os.environ)
        env["TYPST_PACKAGE_PATH"] = str(ROOT / ".typst-packages")
        proc = subprocess.run(args, check=False, env=env)
        if proc.returncode != 0:
            ok = False
    return ok


def main() -> int:
    """Compile every deck under `examples/` and return a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "sources",
        nargs="*",
        type=Path,
        help="the decks to compile, defaulting to every deck under examples/",
    )
    args = parser.parse_args()
    sources = args.sources or sorted((ROOT / "examples").glob("*.typ"))
    if not sources:
        print("no example decks found", file=sys.stderr)
        return 1
    failed = [source for source in sources if not compile_deck(source)]
    for source in failed:
        print(f"failed to compile {source}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
