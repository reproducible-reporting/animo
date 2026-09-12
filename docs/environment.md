---
description: >-
  How to get from a clone of animo to a green test suite:
  the uv environment, the local package directory,
  and the commands that run without StepUp.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Development Environment

## Prerequisites

A typst binary, of exactly the release the manifest pins:

<!-- snipwise.md BEGIN typst-version -->

```text
0.15.1
```

<!-- snipwise.md END typst-version -->

The test suite asserts that `typst --version` agrees with the `compiler` field of `typst.toml`,
so a mismatched toolchain fails loudly instead of producing confusing errors much later.

[direnv](https://direnv.net/) is recommended but not required.
Everything below works without it, as long as the virtual environment is activated by hand.

## From a Clone to a Green Test Suite

```bash
git clone https://github.com/reproducible-reporting/animo.git
cd animo
./setup.sh
direnv allow    # or: source .venv/bin/activate
pytest
```

`setup.sh` installs `uv` and a pinned interpreter under `.venv/`,
runs `uv sync`, downloads the chromium the browser tests drive,
repairs the local package directory and installs the `pre-commit` hook.
Removing `.venv/` undoes all of it, the browser included.

Animo is a typst package, not a Python package.
Nothing in `pyproject.toml` is ever built or published:
the `[project]` table only gives `uv` a name and an interpreter floor,
and the development environment lives in `[dependency-groups]`.

| Group   | Holds                                             |
| ------- | ------------------------------------------------- |
| `tests` | `pytest` and its plugins, and nothing more        |
| `docs`  | `zensical`, pinned below its next minor release   |
| `dev`   | the two above, plus `pre-commit`, `reuse`, StepUp |

`uv sync` installs `dev`.
A continuous integration job that only runs the test suite uses
`uv sync --no-default-groups --group tests` instead,
so it does not build tools it never invokes.

## The Two Import Paths

Both of these resolve from a single working tree, at the same time.

**`@preview/animo:0.1.0`** is what every example, documentation snippet and README shows,
so that a reader can copy any of them and compile it unchanged.
It resolves to the working tree through a repository-local package directory:

```text
.typst-packages/preview/animo/0.1.0 -> ../../..
```

The symlink is committed, and `.envrc` points typst at it:

```bash
export TYPST_PACKAGE_PATH="${PWD}/.typst-packages"
```

Edits to `src/` are picked up immediately, because the target is the working tree itself.
This is preferred over the two alternatives.
Rewriting the imports of the examples in continuous integration
would mean the file that is tested is not the file that is shipped,
and installing into the user-wide package directory would shadow
the published `animo` for every other project on the machine.

**`/src/lib.typ`** is what the internal tests import,
with the repository as the typst root.
It needs no package directory and no environment variable.

The test suite exercises both.
Its compile helper exports `TYPST_PACKAGE_PATH` itself, as an absolute path,
so `pytest` is green for a contributor without `direnv` as well.

## Commands

Everything a contributor normally needs is a single command,
and none of them require StepUp:

```bash
pytest                        # the test suite
pre-commit run --all-files    # formatting and hygiene, including reuse and snipwise
zensical serve                # the documentation site, with live reload
```

[Testing](testing.md) describes the three tiers, how to run one of them,
and the policy on stored reference images.

Previewing a deck is typst's own job.
It serves the HTML and reloads the browser itself, so animo ships nothing for live preview:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

## StepUp

`plan.py` drives everything that takes more than one command:
today the local package directory and the documentation site,
later the example decks in all four outputs, the reference rasters and the benchmarks.

```bash
stepup build --no-watch    # build everything once
stepup boot                # build and keep watching
```

## Version Numbers

`typst.toml` is the single source of the version of the package
and of the typst release it is compiled with.
[Snipwise](https://reproducible-reporting.github.io/snipwise/) copies both
into every file that repeats them, as `snipwise.md` in the repository root spells out.
Bumping a release is therefore an edit of the manifest followed by
`pre-commit run --all-files`.
