---
description: >-
  How to get from a clone of Animo to a passing test suite:
  the uv environment, the local package directory, and the commands.
render_macros: true
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Development Environment

## Prerequisites

The development setup supports linux and macOS on x86-64 and arm64,
because typst publishes a build for these platforms only.
On any other platform, `setup.sh` stops with a message,
because the rest of the setup would produce a tree in which no test can compile.

The development setup uses typst {{ config.extra.typst_version }},
which is the release pinned in the `compiler` field of the `typst.toml` manifest.
`setup.sh` downloads that release into `.venv/bin/`,
so activating the environment puts this typst ahead of any other typst on `PATH`.
The test suite asserts that `typst --version` matches the `compiler` field,
so a mismatched compiler fails one clear test instead of causing confusing errors elsewhere.

[direnv](https://direnv.net/) is recommended but not required.
Without it, activate the virtual environment by hand with `source .venv/bin/activate`.

## From a Clone to a Passing Test Suite

```bash
git clone https://github.com/reproducible-reporting/animo.git
cd animo
./setup.sh
direnv allow    # or: source .venv/bin/activate
pytest
```

`setup.sh` takes these steps:

- it installs `uv` and a pinned Python interpreter under `.venv/`;
- it runs `uv sync`;
- it downloads the pinned typst release and the browsers that the browser tests drive;
- it restores the symlink of the local package directory if the symlink is missing;
- it installs the `pre-commit` hook.

Removing `.venv/` undoes all of it, including the downloaded compiler and browsers.
Running `setup.sh` a second time downloads neither again.

Chromium and firefox are always downloaded,
and webkit only where playwright has a webkit build that runs.
The script ends by printing which browser engines run on your machine.
See [Which Engines Run Where](testing.md#which-engines-run-where)
for how the tests handle a missing webkit.

Animo is a typst package.
Python serves only the tests, the `pre-commit` hooks, the documentation build and the scripts,
so nothing in `pyproject.toml` is ever built or published.
The `[project]` table only gives `uv` a name and a minimum interpreter version,
and the development environment lives in `[dependency-groups]`:

| Group   | Holds                                        |
| ------- | -------------------------------------------- |
| `tests` | `pytest` and its plugins, and nothing more   |
| `docs`  | `zensical`, pinned to one exact release      |
| `dev`   | the two above, plus `pre-commit` and `reuse` |

`uv sync` installs the `dev` group.
A continuous integration job that only runs the test suite uses
`uv sync --no-default-groups --group tests` instead,
so that it installs no tool that it does not run.

`uv.lock` records the exact version of every Python dependency, and it is committed.
The pinned playwright release decides which browser builds render the pages in the browser tests.
A different playwright release could therefore change the pixels that those tests compare.
Run `uv lock` after editing a dependency, and commit `uv.lock` together with `pyproject.toml`.
The `uv-lock` hook fails a commit in which the two files disagree.

## The Two Import Paths

A typst file can import Animo in two ways, and both resolve to the same working tree.

**`@preview/animo:0.1.1`** is the import in every demo deck, documentation snippet and README,
so that a reader can copy any of them and compile it unchanged.
Typst resolves this import to the working tree through a package directory inside the repository:

```text
.typst-packages/preview/animo/0.1.1 -> ../../..
```

The symlink is committed, and `.envrc` points typst at the directory that contains it:

```bash
export TYPST_PACKAGE_PATH="${PWD}/.typst-packages"
```

Typst picks up edits to `src/` immediately, because the symlink points at the working tree itself.
The alternatives were to rewrite the imports of the demo decks in continuous integration,
or to install Animo into the user-wide package directory.
The first alternative would test a file other than the one that is published.
The second would shadow the published `animo` for every other project on the machine.

**`/src/lib.typ`** is the import in the internal tests,
which compile with the repository as the typst root.
This import needs no package directory and no environment variable.

The test suite uses both imports.
Its compile helper sets `TYPST_PACKAGE_PATH` itself, as an absolute path,
so `pytest` passes without `direnv` as well.

## Commands

Each everyday task is a single command:

```bash
pytest                        # the test suite
pre-commit run --all-files    # formatting and hygiene, from ruff to reuse and snipwise
./tools/build_demos.py        # every demo deck, to every output type
zensical build --strict       # the documentation site, decks included
zensical serve                # the same site, with live reload
```

`pytest` runs the tests in parallel through `pytest-xdist`, with one worker per CPU.
The workers have no terminal,
so `--pdb`, `breakpoint()` and output printed by a test need a run in a single process,
which `-n0` selects:

```bash
pytest -n0 tests/test_tags.py
```

See [Testing](testing.md) for the three tiers, how to run one of them,
and the policy on stored reference images.

To preview a deck while editing it, use `typst watch`,
which serves the HTML and reloads the browser after every change.
Animo therefore ships no live preview tool:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

## The Documentation Site

Building the site takes two commands, run in this order.

1. `tools/build_demos.py` compiles every deck under `demos/` to all three output types
   and writes the results into `docs/demos/`.
   This directory is a build product inside the source tree, so `.gitignore` excludes it.
   The script skips a file under `demos/` whose name starts with an underscore,
   such as `demos/_common.typ`, because such a file holds what several decks import
   and is not a deck itself.
1. `zensical build --strict` builds the pages
   and copies the compiled decks to `site/demos/`, beside the pages that link to them.

Because the decks are compiled by a plain script, building the site needs no task runner.
The script also serves as a test, because every deck that the manual links to has to compile
to every output type.

`zensical build --strict` also succeeds without the compiled decks,
which is enough for a contributor who only wants to read the pages.
The links to the decks are absolute, so `--strict` does not check them.
Instead, the test suite asserts that every one of these links points at a file after a full build.

Zensical also renders a social card for every page.
A social card is the preview image that social media and chat clients show beside a link.
`logo/social-card.yml` defines the layout of the cards,
which draws the title and the description of a page in the Inter font.
The first build downloads Inter from Google Fonts into `.cache/plugin/social/`,
and `.gitignore` excludes `.cache/`.
The image behind the text is `logo/social-card.svg`, which typst compiles from
`logo/social-card.typ`.
The SVG is committed, because zensical renders the cards without typst.
The test suite fails when the committed SVG differs from what its source compiles to.
After changing the source, recompile the SVG from the root of the repository:

```bash
typst compile --ignore-system-fonts logo/social-card.typ logo/social-card.svg
```

The card of the home page, `site/assets/images/social/index.png`,
is also the social preview of the GitHub repository.
GitHub has no API for the social preview,
so a maintainer uploads that file by hand under *Settings*, *General*, *Social preview*.

## Benchmarks

The benchmarks are a script that you run on request rather than part of a build,
because a timing is only meaningful on an idle machine:

```bash
./benchmarks/run.py --output benchmarks/results/$(hostname).json
```

A run takes a few minutes.
The output file differs after every run, because timings vary from one run to the next.
The results are committed, one file per machine,
because a timing can only be interpreted together with the machine it was measured on.
See [`benchmarks/README.md`](https://github.com/reproducible-reporting/animo/blob/main/benchmarks/README.md)
for what is measured and why.

## Version Numbers

`typst.toml` holds the version of the package and the typst release it is compiled with,
and no other file is edited by hand to change either of them.
[Snipwise](https://reproducible-reporting.github.io/snipwise/) copies both
into every file that repeats them, as `snipwise.md` in the root of the repository spells out.
Bumping a release is therefore an edit of the manifest followed by
`pre-commit run --all-files`.

The typst release also appears in prose.
Every claim about the behaviour of typst names the release on which it was observed.
Such claims appear in `src/`, `probes/` and `tests/`,
and in the specification (see [Developing Animo](development.md#where-the-specification-lives)).
A claim is written as `typst X.Y.Z`, with the word "typst" before the number,
because Snipwise rewrites exactly this pattern from the `compiler` field.
Bumping the field therefore restates every such claim for the new release.
The probes check whether these claims still hold, and `pytest` runs `probes/` beside `tests/`.
Commit a bump of the typst release only once that run passes.

A number measured by a benchmark is written as `with typst X.Y.Z` instead.
Snipwise leaves this pattern alone,
because only a new run of the benchmark can update the number beside it.
See [Performance](performance.md) for those numbers.

The package version also appears in a file name, which Snipwise cannot rewrite.
The symlink `.typst-packages/preview/animo/0.1.1` carries the version in its name,
so rename it with `git mv` in the commit that bumps the version.
A forgotten rename fails the `package symlink matches the manifest` hook,
which `pre-commit` runs on that commit,
and the test `test_package_symlink_points_at_the_working_tree`.
