---
description: >-
  How to get from a clone of Animo to a green test suite:
  the uv environment, the local package directory, and the commands.
render_macros: true
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Development Environment

## Prerequisites

The development setup requires typst version {{ config.extra.typst_version }},
which is the version pinned in the `typst.toml` manifest.
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
runs `uv sync`, downloads the browsers the browser tests drive,
repairs the local package directory and installs the `pre-commit` hook.
Removing `.venv/` undoes all of it, the browsers included.

Chromium and firefox are always downloaded.
Webkit is downloaded only where playwright has a build that can run,
which is macOS and the debian family, because the 300 MB download could not be launched
anywhere else.
The script ends by printing which engines run on your machine.
Where webkit is absent the browser tier skips it and continuous integration covers it,
as [Testing](testing.md) explains.

Animo is a typst package, not a Python package.
Nothing in `pyproject.toml` is ever built or published:
the `[project]` table only gives `uv` a name and an interpreter floor,
and the development environment lives in `[dependency-groups]`.

| Group   | Holds                                           |
| ------- | ----------------------------------------------- |
| `tests` | `pytest` and its plugins, and nothing more      |
| `docs`  | `zensical`, pinned below its next minor release |
| `dev`   | the two above, plus `pre-commit` and `reuse`    |

`uv sync` installs `dev`.
A continuous integration job that only runs the test suite uses
`uv sync --no-default-groups --group tests` instead,
so it does not build tools it never invokes.

The resolution `uv` arrives at is recorded in `uv.lock`, which is committed.
The browser tier compares rendered pixels, and the browser a rendering comes from is the
one the pinned playwright release bundles,
so a resolution that drifted would move the pixels a test compares.
Run `uv lock` after editing a dependency, and commit the result with it.
The `uv-lock` hook fails a commit that leaves the two out of step.

## The Two Import Paths

Both of these resolve from a single working tree, at the same time.

**`@preview/animo:0.1.1`** is what every example, documentation snippet and README shows,
so that a reader can copy any of them and compile it unchanged.
It resolves to the working tree through a repository-local package directory:

```text
.typst-packages/preview/animo/0.1.1 -> ../../..
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

Everything a contributor normally needs is a single command:

```bash
pytest                        # the test suite
pre-commit run --all          # formatting and hygiene, from ruff to reuse and snipwise
./tools/build_examples.py     # every example deck, to every output type
zensical build --strict       # the documentation site, decks included
zensical serve                # the same site, with live reload
```

`pytest` runs the tests in parallel through `pytest-xdist`, with one worker per CPU.
A worker has no terminal, so `--pdb`, `breakpoint()` and output printed by a test
all need a run in a single process:

```bash
pytest -n0 tests/test_tags.py
```

[Testing](testing.md) describes the three tiers, how to run one of them,
and the policy on stored reference images.

Previewing a deck is typst's own job.
It serves the HTML and reloads the browser itself, so Animo ships nothing for live preview:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

## The Documentation Site

The site is two commands, in this order.

`tools/build_examples.py` compiles every deck under `examples/` to all three output types
and writes the results into `docs/examples/`, which is a build product in a source tree and
is covered by `.gitignore`.
`zensical build --strict` then copies them to `site/examples/`, beside the pages that link
to them. Compiling them there rather than in a task runner keeps the site to two commands,
and it is also a test: a deck the manual points at has to compile to every output type.

The site alone builds without the decks, which is enough for a contributor who only wants
to read the pages. The links to the decks are absolute, so `--strict` does not chase them;
the test suite asserts that every one of them has a file after a full build.

## Benchmarks

The benchmarks are a script rather than a build target,
because a measurement is only meaningful when it is requested explicitly, on an idle machine:

```bash
./benchmarks/run.py --output benchmarks/results/$(hostname).json
```

It takes a few minutes and writes a different file every time, since seconds are not
reproducible. The results are committed, one file per machine, because a number is only
interpretable together with the machine it was measured on.
`benchmarks/README.md` says what is measured and why.

## Version Numbers

`typst.toml` is the single source of the version of the package
and of the typst release it is compiled with.
[Snipwise](https://reproducible-reporting.github.io/snipwise/) copies both
into every file that repeats them, as `snipwise.md` in the repository root spells out.
Bumping a release is therefore an edit of the manifest followed by
`pre-commit run --all-files`.

One version number sits in a file name rather than in text.
The package directory under `.typst-packages` carries the version in the name of its symlink,
which Snipwise cannot rewrite, so `git mv` renames it in the same commit.
A rename that is forgotten fails the `package symlink matches the manifest` hook,
which `pre-commit` runs on the commit that bumps the version.
It also fails `test_package_symlink_points_at_the_working_tree`.
