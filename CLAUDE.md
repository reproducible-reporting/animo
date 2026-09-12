<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# CLAUDE.md

## Overview

Animo is a proof-of-concept presentation package for typst 0.15.1,
in which the content of a slide and its animation are separated.
The body of a slide declares what is on it, tags the parts a timeline may address,
and marks the areas that may be relaid out.
The `animation` argument declares when and how those parts appear, move, scale,
change style and change content.
One source file compiles to four outputs:
an HTML presentation, a presentation PDF, a handout PDF and handout SVG pages.

## Where the Specification Lives

[planning/design.md](planning/design.md) is the specification and the reference
for any change in behaviour.
Read it before changing anything in `src/`.
Three of its sections carry more weight than the rest:

- *Findings* records verified behaviour of typst 0.15.1 that the whole design rests on.
  Every entry there is expensive to rediscover,
  and every entry gets a probe under `probes/` that asserts the behaviour itself
  rather than a feature that happens to depend on it.
  An observation that was expensive to make belongs in this section.
- *Resolved Design Decisions* records questions that are settled, and why.
  Reopening one needs a reason that is not in that section already.
- *Open Questions* records what is deliberately undecided.
  The implementation plan says which phase answers each of them.

[planning/impl_00_first_version/](planning/impl_00_first_version/) turns the design
into an ordered series of phases.
[planning/impl_00_first_version/README.md](planning/impl_00_first_version/README.md)
states the rules that govern a phase session, and each phase file ends in a session log.
Read the README before starting a phase.

Never edit the design document silently.
When a finding contradicts it, say so and ask.

## Non-Negotiables

- The version lives in `typst.toml` and nowhere else.
  Snipwise copies it into every file that repeats it, as `snipwise.md` spells out,
  so a version number is never edited by hand outside the manifest.
  The same holds for the typst release, which is the manifest's `compiler` field.
- Every example, snippet and test document imports `@preview/animo:0.1.0`,
  never a relative path, so that a reader can copy any of them and compile it unchanged.
  Only the internal tests import `/src/lib.typ`.
- Rendering has to be reproducible between a contributor's machine and CI,
  so every compilation uses `--ignore-system-fonts` and only the fonts typst embeds.
  No font files are vendored.
- Content that falls outside the viewport is clipped, never carried over to a next slide.
- Animo emits only the individual `translate` and `scale` CSS properties,
  never the `transform` shorthand, which would clobber typst's own positioning.
- Animo has no templating or styling features, and no header or footer machinery.
  A recurring element is `#place` inside a wrapper around `#slide`.

## Development

[docs/environment.md](docs/environment.md) covers `./setup.sh`, the `uv` environment,
the two typst import paths, the test suite and the StepUp plan.
The commands that matter:

```bash
pytest                        # the test suite
pre-commit run --all-files    # formatting and hygiene, including reuse and snipwise
zensical build --strict       # the documentation site
stepup build --no-watch       # everything the plan drives
```

Run `pre-commit run --all-files` and `pytest` before considering work done,
and `zensical build --strict` after changing the documentation.

A generated typst document has to be written inside the repository,
because typst refuses a source file outside its project root.
The `scratch` fixture in `tests/conftest.py` is that directory.

## Coding Conventions

### Semantic Line Breaks

All English text in this repository is wrapped using **semantic line breaks**:
break after sentences or logical units, not at a fixed character count.
This covers comments, Markdown documentation and commit messages.
See <https://sembr.org/>.
Prose diffs then stay small, because editing one sentence never reflows its neighbours.

- **Every sentence starts on a new line.**
- **Break inside a sentence only where a break is needed, and then at a clause boundary.**
  A sentence that fits within the 100-character line length stays on a single line.
  A longer one is broken before a conjunction or a relative pronoun
  ("and", "but", "because", "which", "if", ...),
  or after a leading subordinate clause.
- **Not every comma is a break.**
  Enumerated items, appositions and short parentheticals stay on the line they started on.

The 100-character line length is a hard cap, not a target to fill.

### Avoid En and Em Dashes

Write sentences without en or em dashes.
They should never be used in any prose (code comments, Markdown, ...),
neither in their UTF-8 glyph form nor in ASCII form.
Subclauses should be made explicit (e.g. "which", "because", "that")
or split into separate sentences.

### Prose That Ages Well

Stale prose is worse than no prose. When writing comments or other prose, avoid:

- **Describing callers.** That is the caller's concern, and the remark rots when it changes.
- **Describing history.** The current code should speak for itself;
  history belongs in commit messages and in the changelog.
- **Line-number references.** Point to a function, a name or a file instead.
- **Restating the code.** A comment should say the reason, the invariant
  or the non-obvious constraint, not paraphrase the next line.
- **Timeless phrasing for point-in-time claims.**
  An observation about typst, chromium or a tool can stop being true after an upgrade.
  Say what was observed and, when it matters, on what.

### Markdown

Section headings use **Title Case**
(capitalize nouns, verbs, adjectives and adverbs; lowercase articles,
coordinating conjunctions and prepositions regardless of length).
Inline code spans keep their own casing and are never title-cased.

A page added to `docs/` has to be added to the `nav` list of `zensical.toml`,
and a link that leaves `docs/` has to be written as a link to GitHub,
because the site has no copy of the rest of the repository.

### Typst

`typstyle` formats every `.typ` file through `pre-commit`, so formatting is not a judgement call.
Indentation is two spaces, as `.editorconfig` says.
Doc comments are plain `//` comments:
the manual is a Markdown site, not a `tidy` document,
so a `///` comment would be read by nothing.

### Python

Python exists in this repository only for `pytest`, `pre-commit`, StepUp and Zensical.
Nothing is ever built or published from `pyproject.toml`.
Docstrings are NumPy-style and written in Markdown, and line length is 100.
