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
One source file compiles to three output types:
an HTML presentation, a static presentation and static handouts.
The two static types are paged modes rather than file formats,
so either of them exports to PDF, SVG or PNG.

## Where the Specification Lives

The specification is two documents under `planning/`, and the first is the entry point.

- [planning/design.md](planning/design.md) specifies Animo 0.1.0 and is the reference
  for any change in behaviour.
  Read it before changing anything in `src/`.
  Two of its sections carry more weight than the rest.
  *Resolved Design Decisions* records questions that are settled, and why;
  reopening one needs a reason that is not in that section already.
  *Open Questions* records what is deliberately undecided.
- [planning/findings.md](planning/findings.md), referred to as *Findings*,
  records verified behaviour of typst 0.15.1 and of the browsers Animo drives
  that the whole design rests on.
  Every entry there is expensive to rediscover,
  and every entry gets a probe under `probes/` that asserts the behaviour itself
  rather than a feature that happens to depend on it.
  An observation that was expensive to make belongs in this document.

Further development is tracked on GitHub as issues and pull requests,
not as a phase plan kept in this repository.

Never edit these documents silently.
When a finding contradicts one of them, say so and ask.

## Non-Negotiables

- The version lives in `typst.toml` and nowhere else.
  Snipwise copies it into every file that repeats it, as `snipwise.md` spells out,
  so a version number is never edited by hand outside the manifest.
  The same holds for the typst release, which is the manifest's `compiler` field.
- Every example, snippet and test document imports `@preview/animo:0.1.1`,
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
the two typst import paths, the test suite and the documentation build.
The commands that matter:

```bash
pytest                        # the test suite
pre-commit run --all-files    # formatting and hygiene, including reuse and snipwise
./tools/build_examples.py     # every example deck, to every output type
zensical build --strict       # the documentation site, decks included
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

A colon or a comma is not a substitute for a dash.
"A subslide overwrites what it addresses: `reveal` and `hide` overwrite each other"
joins a claim to its elaboration in the way a dash would,
and so does an apposition such as "`pan.typ`, a canvas two screens wide".
Write the second part as its own sentence.
A colon is for introducing a list, a table, a code block or a quoted term.

### One Term per Concept

The vocabulary of Animo is what [planning/design.md](planning/design.md)
and [docs/reference.md](docs/reference.md) define.
A concept that has a name there is called by that name everywhere,
and a synonym is never introduced for variety.
A reader who meets two words assumes there are two things.

A word already taken by one concept is not reused for another.
A *subslide* is a state of a slide, and a *step* is what the presenter does to reach the next one,
so a subslide is never called a step.
A call such as `reveal("a")` or `replace("a")[..]` is a *primitive*.

When a change of behaviour needs a word the specification does not have,
the word goes into the specification first, as *Where the Specification Lives* says.

### Prose That Ages Well

Prose that no longer matches the code misleads the reader.
Most habits below are about code comments,
which sit next to the code and are read with it.
*Timeless phrasing for point-in-time claims* is about any prose in this repository.

- **Describing callers.** That is the caller's concern, and the remark rots when it changes.
- **Describing history of this repository.** The current code should speak for itself;
  history belongs in commit messages and in the changelog.
- **Line-number references.** Point to a function, a name or a file instead.
- **Restating the code.** A comment should say the reason, the invariant
  or the non-obvious constraint, not paraphrase the next line.
- **Timeless phrasing for point-in-time claims.**
  An observation about typst, chromium or a tool can stop being true after an upgrade.
  Say what was observed and, when it matters, on what.
  This is about software outside this repository and not about the repository's own past.

A page under `docs/` is read by someone who does not have the code in front of them,
so *Describing callers* and *Restating the code* do not carry over to it.
State plainly what a function, an argument or a default does,
and only then what follows from it.
The reader of the Presentation Author Guide is the caller,
and addressing that reader as "you" is the clearest way to say what they can do.

### Prose Written to Inform

Prose here is written for a reader who is looking for a fact,
not for one whose attention has to be held.
Name the subject, state the fact, and end the sentence when the fact is complete.

Habits to avoid:

- **A superlative used as a hook,**
  as in "the slowest thing the suite does" or "the one construct that is genuinely expensive".
  A superlative that was measured is a fact and stays,
  as in "the most expensive construct in an Animo deck".
- **A punchline in a trailing clause,**
  typically introduced by "and that is", "and that is what makes" or "which is where".
- **A denial followed by a reveal,** as in "X is not Y, it is Z",
  where the plain form says what X is.
  The same applies across two sentences:
  a rule is stated in its positive form rather than as a list of what does not happen.
- **A value judgement standing in for the fact,**
  as in "worse than a red one" instead of saying what actually goes wrong.
- **A bare identifier as the subject,** as in "`clip` defaults to `true`".
  Name what the identifier is: "The `clip` argument defaults to `true`".
- **A count used as a name,** as in "The Four Primitives"
  or "`pan` is the fifth continuous primitive".
  Name the category instead, because a count goes stale when the set changes
  and the reader has to count to check it.
  Announcing a count ahead of a list, as in "Three things follow.", says nothing either.
- **A document or a tool as the speaker,**
  as in "[Performance](docs/performance.md) has the number".
  A cross reference is written as "See [Performance](docs/performance.md) for the numbers."
- **A metaphor where the mechanism fits,**
  as in "the browser needs ink it can bring back" instead of saying that the element is rendered
  and then hidden with `opacity: 0`.
- **A sentence without a verb,** as in "One source file, one compile per output type."
- **A chain of reasoning compressed into a clause.**
  When a fact follows from two others, state the intermediate one.

Each example below pairs a sentence written for effect with the preferred phrasing.

- Written for effect:
  "Compiling a typst document in a subprocess is the slowest thing the suite does."
  Preferred:
  "The slowest step in the test suite is the compilation of typst documents in a subprocess."
- Written for effect:
  "Animo asks typst to lay a slide out more than once, and that is the whole of what it costs."
  Preferred:
  "The cost of Animo is that it asks typst to lay out a slide more than once."
- Written for effect:
  "A failing probe is a finding that changed, and that is the news the job exists to deliver."
  Preferred:
  "A failing probe indicates that a documented behaviour of typst or a browser has changed."
- Written for effect:
  "A suite that is green because a third of it never ran is worse than a red one."
  Preferred:
  "A suite that passes while a third of its tests are skipped does not show whether those
  tests would pass."
- Written for effect:
  "The order is not a matter of taste:"
  Preferred:
  "The order follows from how a boundary effect is measured:"
- Written for effect:
  "A subslide overwrites what it addresses: `reveal` and `hide` overwrite each other."
  Preferred:
  "Each primitive modifies the state of its tagged subject.
  `reveal` and `hide` change visibility."
- Written for effect:
  "They do not clip the body and the body does not clip them."
  Preferred:
  "The viewport clips all three layers alike."

### Markdown

Section headings use **Title Case**
(capitalize nouns, verbs, adjectives and adverbs; lowercase articles,
coordinating conjunctions and prepositions regardless of length).
Inline code spans keep their own casing and are never title-cased.

A heading names the subject of its section,
as in "Initial State of Tagged Content" rather than "Where a Tag Starts",
and "Slide Transitions" rather than "Between Two Slides".

A page added to `docs/` has to be added to the `nav` list of `zensical.toml`,
and a link that leaves `docs/` has to be written as a link to GitHub,
because the site has no copy of the rest of the repository.
Such a link points at `main`, as in
`https://github.com/reproducible-reporting/animo/blob/main/examples/hello.typ`.

The file `README.md`, which `docs/index.md` is a symlink to, is the one exception.
Its links into the repository point at the tag of the release,
because the Universe package checker asks a README to link to a resource
that matches the version of the package.
Snipwise copies that tag from `typst.toml`, so it is never edited by hand.

A page of the Presentation Author Guide opens with the deck it draws on,
in the form the other pages use:
the source on GitHub, then the three built outputs in parentheses,
then one sentence saying what the deck shows.

`docs/` describes what Animo does today.
What it could do later belongs in a GitHub issue.

### Typst

`typstyle` formats every `.typ` file through `pre-commit`, so formatting is not a judgement call.
Indentation is two spaces, as `.editorconfig` says.
Doc comments are plain `//` comments:
the manual is a Markdown site rather than a `tidy` document,
so nothing would read a `///` comment.

### Python

Python exists in this repository only for `pytest`, `pre-commit`, Zensical
and the scripts under `tools/` and `benchmarks/`.
Nothing is ever built or published from `pyproject.toml`.
Docstrings are NumPy-style and written in Markdown, and line length is 100.
