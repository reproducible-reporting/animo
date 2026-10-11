<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# CLAUDE.md

## Overview

Animo is a proof-of-concept presentation package for typst 0.15.0,
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

- [planning/design.md](planning/design.md) specifies how Animo works and is the reference
  for any change in behaviour.
  Read it before changing anything in `src/`.
  Two of its sections carry more weight than the rest.
  *Resolved Design Decisions* records questions that are settled, and why;
  reopening one needs a reason that is not in that section already.
  *Open Questions* records what is deliberately undecided.
- [planning/findings.md](planning/findings.md), referred to as *Findings*,
  records verified behaviour of typst 0.15.0 and of the browsers Animo drives
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
- Every demo deck, documentation snippet and test document imports `@preview/animo:0.2.0`,
  never a relative path, so that a reader can copy any of them and compile it unchanged.
  Only the internal tests import `/src/lib.typ`.
  A demo deck may also import an auxiliary file from `demos/`,
  such as `_common.typ`, which holds what several decks share.
  The name of an auxiliary file starts with an underscore, so that `tools/build_demos.py`
  and the tests do not treat it as a deck.
  An auxiliary file imports the published package as well,
  so that a reader who copies a deck together with its auxiliary files compiles it unchanged.
- Rendering has to be reproducible between a contributor's machine and CI,
  so every compilation uses `--ignore-system-fonts` and only the fonts typst embeds.
  No font files are vendored.
- Content that falls outside the viewport is clipped, never carried over to a next slide.
- Animo emits only the individual `translate` and `scale` CSS properties as transforms,
  never the `transform` shorthand, which would clobber typst's own positioning.
  A morph also animates `d` and `stroke-width` on a path it resizes or turns into another shape,
  and never writes either as inline style.
- Animo has no templating or styling features, and no header or footer machinery.
  A recurring element is `#place` inside a wrapper around `#slide`.

## Development

[docs/environment.md](docs/environment.md) covers `./setup.sh`, the `uv` environment,
the two typst import paths, the test suite and the documentation build.
The commands that matter:

```bash
pytest                        # the test suite
pre-commit run --all-files    # formatting and hygiene, including reuse and snipwise
./tools/build_demos.py     # every demo deck, to every output type
zensical build --strict       # the documentation site, decks included
```

Run `pre-commit run --all-files` and `pytest` before considering work done,
and `zensical build --strict` after changing the documentation.

A generated typst document has to be written inside the repository,
because typst refuses a source file outside its project root.
The `scratch` fixture in `tests/conftest.py` is that directory.

## Coding Conventions

### Prose That Reads on the First Pass

A reader who is new to Animo should understand each sentence on the first reading.
This is the main criterion for all prose in this repository,
and the other prose rules in this file yield to it.
A clear sentence is often longer than a dense one, and the clear sentence is preferred.

- **Make something concrete the subject, with a concrete verb.**
  The reader, the presenter, Animo, typst, a browser, a page and a file can act.
  A state, a flag or a timeline rarely should.
  "Animo adds a handout page for each subslide with `handout: true`"
  is easier to follow than "the flag keeps the state".
  Where a mechanism exists, describe the mechanism rather than a metaphor for it.
- **Give a noun at most one relative clause.**
  When a second one is needed, split the sentence.
  Keep chains of "of" short as well.
  "The slide's final state" reads more easily than "the final state of the timeline of the slide".
- **Introduce a term or an identifier at its first use on a page.**
  Say what the identifier is, as in "The `clip` argument defaults to `true`".
  A short gloss in parentheses is fine, as in "the default page (the final state of the slide)".
- **Give the reason** with "because" when the reader would otherwise ask why.
  When a fact follows from two others, state the intermediate one.
- **Say what is there.**
  Prefer "visible" and "hidden" over "no longer shows" and "lacks",
  and state a rule in its positive form rather than as a list of what does not happen.
- **Name the quantity,** as in "needs an extra page" rather than "needs more".
- **Keep the items of a list parallel,** so that all of them are things or all are actions.
- **Repeat a noun rather than use a distant pronoun.**
  When another noun stands between "it" and the noun it refers to,
  or when the referent was not the subject of the previous sentence, repeat the noun.
  Repeating a term is always allowed, also in consecutive sentences.

After drafting, reread each sentence as a newcomer would.
A sentence that has to be read twice is rewritten, usually as two sentences.

Each example below pairs a sentence that takes effort to read with the preferred phrasing.

- Hard to read:
  "It shows the default page of a slide, content that the final state of a slide no longer shows,
  and a slide left out of the handout."
  Preferred:
  "It shows the default handout of a slide (its final state),
  examples requiring additional intermediate handout pages
  because some content is no longer visible in the final state,
  and a slide left out of the handout."
- Hard to read:
  "A state is kept by the flag of the subslide that brings it about,
  and not by the flag of the subslide that later takes its content away."
  Preferred:
  "The `handout:` argument of a `sub` call decides whether the handout gets a page
  for the subslide that this call creates.
  To keep content that a later subslide removes, set `handout: true` on the `sub` call before it."
- Hard to read:
  "A timeline that reveals or resets content that the body hides or removes ends in a state
  where that content is shown."
  Preferred:
  "Some slides start with hidden content and reveal it later.
  At the end of the timeline, that content is visible."
- Hard to read:
  "A color fills the viewport. As a background it is the page fill on paper."
  (The word "it" first reads as "the background".)
  Preferred:
  "A color used as a background is the page fill on paper."

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

Write sentences without en or em dashes, neither as UTF-8 glyphs nor in ASCII form.
This holds for all prose, including code comments.
A dash usually joins a claim to an elaboration.
Write the elaboration as a separate sentence,
as a clause with "which", "because" or "that",
or as a short gloss in parentheses.
A colon used in the same way reads like a dash,
so a colon is kept for introducing a list, a table, a code block or a quoted term.

### One Term per Concept

The vocabulary of Animo is what [planning/design.md](planning/design.md)
and [docs/reference.md](docs/reference.md) define.
A concept that has a name there is called by that name everywhere,
and a synonym is never introduced for variety.
A reader who meets two words assumes there are two things.
Repeating the term in the next sentence is fine, and usually clearer than a pronoun.

A word already taken by one concept is not reused for another.
A *subslide* is a state of a slide, and a *step* is what the presenter does to reach the next one,
so a subslide is never called a step.
A call such as `reveal("a")` or `replace("a")[..]` is a *primitive*.

This rule covers the names of concepts.
Ordinary verbs and adjectives, such as "visible", "add" or "include", are not vocabulary,
and a plain word may replace an abstract one.
One verb is not used with two different subjects in the same sentence,
as in "It shows content that the final state no longer shows".

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

### Prose Written for Effect

Prose here is written for a reader who is looking for a fact,
not for one whose attention has to be held.
The habits below make a sentence sound better without making it say more.
They are points to check when rereading a draft.

- **A superlative used as a hook,**
  as in "the slowest thing the suite does" or "the one construct that is genuinely expensive".
  A superlative that was measured is a fact and stays,
  as in "the most expensive construct in an Animo deck".
- **A punchline in a trailing clause,**
  typically introduced by "and that is", "and that is what makes" or "which is where".
- **A denial followed by a reveal,** as in "X is not Y, it is Z",
  where the plain form says what X is.
- **A value judgement standing in for the fact,**
  as in "worse than a red one" instead of saying what actually goes wrong.
- **A count used as a name,** as in "The Four Primitives",
  because a count goes stale when the set changes.
  Name the category instead.
- **A document or a tool as the speaker,**
  as in "[Performance](docs/performance.md) has the number".
  A cross reference is written as "See [Performance](docs/performance.md) for the numbers."
- **The word "own" where nothing is contrasted,** as in "the deck's own transition",
  which is "the deck's transition".
  The word "own" is needed only when two owners are set against each other,
  as in "typst's own `hide`" beside the `hide` primitive of Animo.
- **A sentence without a verb,** as in "One source file, one compile per output type."

Each example below pairs a sentence written for effect with the preferred phrasing.

- Written for effect:
  "Compiling a typst document in a subprocess is the slowest thing the suite does."
  Preferred:
  "The slowest part of the test suite is the compilation of typst documents in a subprocess."
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
`https://github.com/reproducible-reporting/animo/blob/main/demos/hello.typ`.

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
A function an author calls carries a `///` doc comment,
because tinymist shows it as hover documentation and signature help.
These are the names `lib.typ` exports and the functions of the `anim` module.
The comment follows the syntax that
[tinymist documents](https://myriad-dreamin.github.io/tinymist/feature/docs.html):

- the description is typst markup, not Markdown;
- each parameter gets a line of the form `/// - name (type): description`;
- the returned value gets a line of the form `/// -> type`.

Every other comment is a plain `//` comment,
because the manual is a Markdown site rather than a `tidy` document.

### Python

Python exists in this repository only for `pytest`, `pre-commit`, Zensical
and the scripts under `tools/` and `benchmarks/`.
Nothing is ever built or published from `pyproject.toml`.
Docstrings are NumPy-style and written in Markdown, and line length is 100.
