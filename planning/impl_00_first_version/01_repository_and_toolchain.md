<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 01: Repository and Toolchain

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant part of the design document is *Development Infrastructure*,
in particular *Repository layout and manifest*, *The working tree as `@preview/animo`*,
*Task layer*, *Documentation*, *Version numbers* and *Formatting and hygiene*.

## Goal

A development environment in which every later phase can work without touching infrastructure:
the working tree resolves as `@preview/animo:0.1.0`, a trivial package compiles through it,
`pytest`, `pre-commit`, `stepup` and `zensical` all run and are green.

Nothing about animo's features is built here.
The package is a placeholder whose only job is to prove that the loop closes.

## Prerequisites

None. This is the first phase.

## Scope

### In Scope

- `typst.toml`: name, version `0.1.0`, `entrypoint = "src/lib.typ"`, `compiler = "0.15.1"`,
  authors, `license = "Apache-2.0"`, description, keywords, `categories = ["presentation"]`,
  repository URL and the `exclude` list.
  The manifest is the authoritative source of the version and of the typst pin,
  so get it right before anything copies from it.
- `src/lib.typ` as the entrypoint, with the module layout the design implies:
  body-level names (`slide`, `tag`, `region`) exported at the top level,
  and an `anim` submodule that a star import re-exports.
  For this phase the implementations are stubs, deliberately trivial.
- The local package directory: `.typst-packages/preview/animo/0.1.0` as a relative symlink
  to the repository root, and `.envrc` exporting `TYPST_PACKAGE_PATH=.typst-packages`.
  The `check-symlinks` and `destroyed-symlinks` hooks must accept it.
- The Python side: `pyproject.toml`, a `uv` lock file, and a `.venv` bootstrap
  in the style of the sibling repositories.
  Animo is a typst package, not a Python package,
  so Python is present only for `pytest`, `pre-commit`, `stepup` and `zensical`.
- `plan.py`: the StepUp plan.
  For this phase it only needs to create the package symlink and build the documentation site,
  but it is where the example decks and reference rasters land later.
- `.pre-commit-config.yaml`: add `typstyle` (through `typstyle-rs/pre-commit-typstyle`),
  `check-toml`, `check-github-workflows` and `snipwise` to the hooks already configured.
- `snipwise.md` with the source rule on `typst.toml` and the target rules from the design
  document, so that `@preview/animo:X.Y.Z` strings stay correct everywhere.
  Run `snipwise check --diff` before the first `fix`:
  the `regex` scanner has no end marker, so an under-anchored expression can eat too much.
- The remaining repository files the design document lists as missing:
  `.gitignore`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CITATION.cff`, `.zenodo.json`.
- `CLAUDE.md`, in the style of the sibling repositories:
  what the repository is, where the specification lives, the common commands,
  the prose and formatting conventions.
  Every later phase session reads it, so it pays for itself immediately.
- `docs/` and `zensical.toml`: the site skeleton, building with `--strict`.
  Two pages are enough for now, `index.md` and `environment.md`,
  the latter describing exactly the setup this phase produces.
- `tests/` with one test that compiles a document importing `@preview/animo:0.1.0`
  and one that compiles a document importing `/src/lib.typ`, both through a subprocess helper.

### Out of Scope

- Any animo feature. `slide` may be `body => body`.
- The test tiers for rasters and the browser, the probes, and continuous integration:
  those are phase 02.
- Example decks and the manual: phase 13, grown incrementally from phase 03 onwards.

## Open Questions in Focus

1. **Two import paths, and which one CI compiles.**
   The design document has tests importing `/src/lib.typ` by absolute path
   with the repository as typst root, while every example and every documentation snippet
   imports `@preview/animo:0.1.0` so that a reader can copy and compile it.
   Confirm that both resolve simultaneously from a single working tree,
   and decide which one the documentation examples are compiled with in the test suite
   and later in CI.
   Compiling them through `@preview` tests the string the reader copies
   but makes the suite depend on `TYPST_PACKAGE_PATH` being set;
   compiling them through the root path removes that dependency
   but no longer tests the published form.
   Whatever is chosen has to hold for a contributor without `direnv` as well.
1. **The shape of the Python environment for a repository that is not a Python package.**
   The sibling repositories declare a real distribution in `pyproject.toml`.
   Animo has no Python code to ship, only a development environment to pin.
   Decide between a `[project]` table with a `dev` extra,
   a `[dependency-groups]` table with no distribution at all,
   and a plain requirements pin, and make sure `uv sync` and the CI workflows agree with it.

No other open question from the design document is in scope for this phase.

## Tests

Thin on purpose. Enough to prove the environment exists:

- a helper that runs `typst compile` in a subprocess with `--ignore-system-fonts`,
  returning the exit status and stderr, which phase 02 will build the tier-1 runner on;
- one test per import path, as listed above;
- a test asserting that the `compiler` field of `typst.toml`
  matches the typst version on `PATH`, so that a mismatched toolchain fails loudly
  instead of producing confusing errors three phases later.

## Documentation

- `docs/index.md`: what animo is, in a paragraph, linking to the design document on GitHub.
- `docs/environment.md`: how to get from a clone to a green `pytest`,
  including `direnv allow`, `uv sync`, the package symlink,
  and the fact that `pytest`, `pre-commit` and `typst watch` are directly invocable
  without learning StepUp.
- `CONTRIBUTING.md` pointing at it rather than repeating it.

## Definition of Done

- `uv sync` produces a working environment from a clean clone.
- `typst compile` of a document importing `@preview/animo:0.1.0` succeeds.
- `pytest` is green.
- `pre-commit run --all-files` is green, including `reuse` and `snipwise`.
- `stepup build --no-watch` succeeds.
- `zensical build --strict` succeeds.

## Hand-Off

Later phases rely on:
the manifest as the single source of the version and the typst pin,
the two import paths,
the subprocess compile helper,
and `plan.py` as the place where anything that takes more than one command belongs.

## Session Log

### What Was Built

The development environment described in *Scope*, in full:

- `typst.toml` with the manifest fields, the `exclude` list and `compiler = "0.15.1"`.
- `src/` as `lib.typ` plus `slide.typ`, `tag.typ` and `anim.typ`.
  `lib.typ` does `#import "anim.typ"` without a name list, which binds the module under
  its file stem and re-exports it through a star import,
  so `import anim: *` inside an animation block works with no extra plumbing.
  Every implementation is a deliberately trivial stub with the signature the design states.
- `.typst-packages/preview/animo/0.1.0` as a relative symlink to the repository root,
  committed, plus `.envrc` exporting `TYPST_PACKAGE_PATH` and activating `.venv`.
- `pyproject.toml`, `setup.sh` and `uv.lock`, with `.gitignore`, `CHANGELOG.md`,
  `CONTRIBUTING.md`, `CITATION.cff`, `.zenodo.json`, `CLAUDE.md` and a rewritten `README.md`.
- `plan.py`, `zensical.toml`, `docs/index.md` and `docs/environment.md`.
- `snipwise.md`, and `typstyle`, `check-toml`, `check-github-workflows` and `snipwise`
  added to `.pre-commit-config.yaml`.
- `tests/helpers.py` with the subprocess compile helper, `tests/conftest.py`,
  `tests/documents/` with one document per import path, and `tests/test_environment.py`.

All six items of the *Definition of Done* are green,
and `./setup.sh` was verified from a deleted `.venv/`.

### Decisions

**Both import paths, each for what it is good at.**
Verified that `@preview/animo:0.1.0` and `/src/lib.typ` resolve simultaneously
from one working tree, in the paged and the HTML target.
Examples, README snippets, documentation snippets and any test that stands in for a reader
use `@preview/animo:0.1.0`; the internal tests use `/src/lib.typ`.
The dependency on `TYPST_PACKAGE_PATH` that this would normally create is removed
by having the compile helper export the variable itself, as an absolute path,
so the suite is green for a contributor without `direnv`.
`TYPST_PACKAGE_PATH` was verified to work as an absolute path from any working directory.

**The Python side is a `[project]` stub with `[dependency-groups]`.**
`[tool.uv] package = false`, so nothing is ever built.
The groups are `tests` (pytest only), `docs` (zensical only) and `dev` (everything),
so a continuous integration job that runs only the suite can use
`uv sync --no-default-groups --group tests`.
`cache-dir` and `python-downloads` are set so that `setup.sh` keeps its promise
that removing `.venv/` undoes the whole bootstrap.
Zensical is pinned exactly (`zensical==0.0.61`) rather than with a range:
every zensical release so far is a `0.0.x`, so a range pins nothing,
and `uv.lock` is not committed, following the sibling repositories.

**The public home is `github.com/reproducible-reporting/animo`,** with the site at
`https://reproducible-reporting.github.io/animo/`.

### Findings Collected

New observations, none of which contradict the design document.
They are tooling behaviour rather than typst behaviour,
so none of them belongs in the design document's *Findings* section as it stands.
The first one is the exception worth considering, because it constrains every later test.

1. **Typst refuses a source file outside its project root**
   (`error: source file must be contained in project root`),
   while the *output* path may be anywhere.
   A generated test document therefore cannot live in pytest's `tmp_path`.
   The `scratch` fixture in `tests/conftest.py` is the answer:
   a per-test directory under `tmp/`, inside the repository and git-ignored.
   Phase 02 will lean on this for every generated document.
1. **Compiling a one-slide document takes about 15 ms** with typst 0.15.1
   and `--ignore-system-fonts`, on this machine, measured on the two import-path documents.
   That is the floor the benchmarks of phase 11 will measure against,
   and it is low enough that a subprocess per assertion is affordable for tier 1.
1. **StepUp 4.0.1 refuses a directory as the output of a step**
   (`PathError: Directories are not allowed`), and a symlink to a directory counts as one.
   So `plan.py` cannot create the package symlink as an output.
   It declares it with `static()` instead, which still fails the build loudly if it goes missing,
   and `setup.sh` creates it on a fresh clone.
   The same limit applies to the Zensical site, which is tracked through a stamp file
   (`site/.stamp`) written after a successful build.
1. **Snipwise refuses a rule whose pattern matches no file**, and refuses two narrowed rules
   that claim the same snippet in the same file, even when their expressions cannot overlap.
   Both bit while writing `snipwise.md`.
   The version rule is therefore a single rule with an alternation over the two textual forms
   (`@preview/animo:X.Y.Z` and `.typst-packages/preview/animo/X.Y.Z`),
   and the pattern list holds only directories that exist today.
   `snipwise check --diff` after a deliberate bump to `9.9.9` confirmed that it reaches all
   ten files it should and none that it should not.
1. **`reuse lint` reports git-ignored files inside a directory that is itself untracked.**
   With `tests/` untracked, it flagged `tests/__pycache__/*.pyc`,
   which `.gitignore` covers.
   `git add -N` on the new files makes it compliant.
   The work is therefore left in the working tree with intent-to-add marks set,
   so that `pre-commit run --all-files` is green as it stands.
   This disappears once the phase is committed.
1. **`typstyle` collapses a single trailing keyword argument onto the call line.**
   It rewrote `#slide(\n  animation: {..},\n)[..]` into `#slide(animation: {..})[..]`
   in both test documents.
   Worth knowing before phase 03 writes examples whose formatting is meant to be read:
   the formatter, not the author, decides.

### Open Questions Answered

The two in this phase's focus list, as recorded under *Decisions*.
No open question of the design document was touched.

### For Later Phases

- The compile helper is `compile_typst` in `tests/helpers.py`.
  It returns a `TypstResult` rather than raising, which is what phase 02's tier-1 runner needs,
  and it already takes `fmt`, `sysinp` and `features`,
  so `--input animo=presentation` and `--features html` need no change to it.
- `snipwise.md` has to grow patterns for `examples/`, `probes/` and `benchmarks/` as those
  directories appear, and for `.github/workflows/*.yaml` in phase 02.
  The typst version pin is a `markers` rule, so a workflow receives it through a
  `# snipwise.md BEGIN typst-version` block rather than through an expression.
  Adding a directory to a pattern list is not optional: a snippet that is not copied
  is a stale version string that nothing catches.
- `plan.py` is the place for anything that takes more than one command.
  It currently holds the static declaration of the package directory and the site build.
- Two repository files are still missing for a Universe submission and are not in this phase:
  a top-level `LICENSE` file, which `typst/package-check` requires,
  and the `.github/workflows/` that phase 02 brings.
- `docs/` has two pages and a `nav` list with room for the manual.
  `pymdownx.snippets` is configured with `check_paths = true` and `base_path = ["."]`,
  so a documented example can be included from the real `.typ` file from phase 03 onwards.
