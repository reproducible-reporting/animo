<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Contributing to Animo

Animo is a proof of concept under construction.
Reports of things that do not work, and of decks that Animo cannot express,
are therefore the most useful contributions at this stage.

## Setting Up

The development environment is described in one place,
[Development Environment](https://reproducible-reporting.github.io/animo/environment/),
which covers `./setup.sh`, `direnv`, the two typst import paths and the commands.
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
./tools/build_examples.py
zensical build --strict
```

[Testing](https://reproducible-reporting.github.io/animo/testing/) describes the three tiers,
how to run one of them, and the policy on stored reference images.

`pre-commit` formats as well as checks,
so a run that changes files has to be repeated until it reports no further changes.

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

[planning/design.md](planning/design.md) is the specification.
A change in behaviour is described in the design document before it is implemented.
Further development is tracked on GitHub as issues and pull requests.
Beside it, [planning/findings.md](planning/findings.md) records verified behaviour of typst
that Animo depends on, and every entry there has a probe under `probes/` that asserts the
behaviour itself, or a recorded reason why it cannot have one.
An observation that was expensive to make belongs in that document, and then in a probe;
[Behaviour Probes](https://reproducible-reporting.github.io/animo/probes/) says how.
