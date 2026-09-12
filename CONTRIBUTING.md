<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Contributing to Animo

Animo is a proof of concept under construction,
so the most useful contribution today is a report of something that does not work,
or a deck that animo cannot express.

## Setting Up

The development environment is described in one place,
[Development Environment](https://reproducible-reporting.github.io/animo/environment/),
which covers `./setup.sh`, `direnv`, the two typst import paths,
and the commands that run without StepUp.
The short version:

```bash
git clone https://github.com/reproducible-reporting/animo.git
cd animo
./setup.sh
direnv allow    # or: source .venv/bin/activate
pytest
```

## Before Opening a Pull Request

```bash
pytest
pre-commit run --all-files
zensical build --strict
```

`pre-commit` formats as well as checks,
so a run that changes files is a run that has to be repeated until it is quiet.

## Conventions

- Every file carries a [REUSE](https://reuse.software/) header, under `Apache-2.0`.
- English prose is wrapped with [semantic line breaks](https://sembr.org/),
  with a hard cap of 100 characters, and avoids en and em dashes.
- Markdown headings use Title Case.
- Indentation follows `.editorconfig`:
  two spaces for `.typ`, `.md`, `.yaml` and `.json`, four spaces for Python.
- The version lives in `typst.toml` and nowhere else.
  Snipwise copies it into every file that repeats it,
  so a version number is never edited by hand outside the manifest.

## Design Before Code

[planning/design.md](planning/design.md) is the specification,
and [planning/impl_00_first_version/](planning/impl_00_first_version/) is the order
in which it is being built.
A change in behaviour is a change to the design document first.
Its *Findings* section records verified behaviour of typst that animo depends on,
and every entry there has, or will have, a probe under `probes/` that asserts it.
An observation that was expensive to make belongs in that section.
