#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The StepUp plan of animo.

Everything that takes more than one command belongs here.
`pytest`, `pre-commit` and `typst watch` stay directly invocable,
so a contributor who only wants to run the tests or preview a deck never has to learn StepUp.
"""

from stepup.core.api import glob, static, step
from stepup.reprep.api import compile_typst

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

# The example decks, each built to all four outputs.
# This is the design's "one compile per output" claim, expressed as steps rather than
# asserted in prose, so that it is tested on every build instead of being believed.
# Rendering has to be reproducible between a contributor's machine and CI,
# so every compilation uses only the fonts typst embeds.
# The built decks go outside `examples/`, because StepUp 4.0.1 refuses a build product
# inside a static tree: a static tree is the sole owner of the files under it.
static("examples/", "src/", "typst.toml")
paths_examples = glob("examples/*.typ")
# The package itself, so that editing a source file rebuilds every deck.
# The symlink that makes it resolve as `@preview/animo:0.1.0` is not listed:
# StepUp refuses a directory as the input of a step, and `static` above already fails
# the build when it goes missing.
paths_package = glob("src/*")
for path_example in paths_examples:
    name = path_example.stem
    common = {"inp": paths_package, "typst_args": ("--ignore-system-fonts",)}
    # The HTML presentation. `compile_typst` adds `--features=html` for an HTML destination.
    compile_typst(path_example, f"build/examples/{name}.html", **common)
    # The presentation PDF, one page per subslide.
    compile_typst(
        path_example,
        f"build/examples/{name}-presentation.pdf",
        sysinp={"animo": "presentation"},
        **common,
    )
    # The handout PDF, one page per slide, which is animo's default paged output.
    compile_typst(path_example, f"build/examples/{name}-handout.pdf", **common)
    # The same handout pages as SVG, which needs a page number template in the path.
    compile_typst(path_example, f"build/examples/{name}-handout-{{p}}.svg", **common)
