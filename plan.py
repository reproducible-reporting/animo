#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The StepUp plan of animo.

Everything that takes more than one command belongs here.
`pytest`, `pre-commit` and `typst watch` stay directly invocable,
so a contributor who only wants to run the tests or preview a deck never has to learn StepUp.
"""

from stepup.core.api import glob, static, step

# The repository-local package directory that makes the working tree resolve as
# `@preview/animo:0.1.0`. It is committed, and `setup.sh` repairs it,
# because StepUp 4.0.1 refuses a directory as the output of a step
# and the symlink points at a directory.
# Declaring it static is what lets a later step that compiles a deck depend on it,
# and what makes a lost symlink fail the build here rather than inside typst.
static(".typst-packages/", ".typst-packages/preview/", ".typst-packages/preview/animo/")
static(".typst-packages/preview/animo/0.1.0")

# The documentation site.
# Zensical writes a whole directory, which StepUp cannot express as an output either,
# so the step is tracked through a stamp file written after a successful build.
static("zensical.toml", "docs/")
paths_docs = glob("docs/**/*.md")
step(
    "zensical build --strict && touch site/.stamp",
    inp=["zensical.toml", *paths_docs],
    out="site/.stamp",
    shell=True,
)
