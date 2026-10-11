---
description: >-
  What the development guide covers, and where the specification of Animo lives.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Developing Animo

This guide is for someone who wants to change Animo itself.
To write a deck with Animo, read the [Presentation Author Guide](slides.md)
and the [Reference](reference.md) instead.

| Page                                      | Covers                                                                   |
| ----------------------------------------- | ------------------------------------------------------------------------ |
| [Development Environment](environment.md) | setting up a clone, the `uv` environment, the two import paths, commands |
| [Testing](testing.md)                     | the three test tiers, the browser engines, continuous integration        |
| [The Browser Runtime](architecture.md)    | the page structure, the runtime files, the controller and its events     |
| [Behaviour Probes](probes.md)             | what a probe asserts, how to add one, and what to do when one fails      |
| [Generative AI Disclaimer](genai.md)      | why much of Animo was written with the help of generative AI             |

## Repository Layout

| Directory          | Holds                                                                    | Covered by                                                      |
| ------------------ | ------------------------------------------------------------------------ | --------------------------------------------------------------- |
| `src/`             | the typst package, with `lib.typ` as its entry point                     | the design document                                             |
| `src/js/`          | the browser runtime, which `src/deck.typ` joins into the HTML output     | [The Browser Runtime](architecture.md)                          |
| `tests/`           | the feature tests, and the test harness under `tests/harness/`           | [Testing](testing.md)                                           |
| `probes/`          | one probe module per entry in *Findings*, or per group of entries        | [Behaviour Probes](probes.md)                                   |
| `demos/`           | the demo decks that the Presentation Author Guide draws on               | [The Documentation Site](environment.md#the-documentation-site) |
| `docs/`            | the pages of this site                                                   | [The Documentation Site](environment.md#the-documentation-site) |
| `planning/`        | the design document and *Findings*                                       | [Where the Specification Lives](#where-the-specification-lives) |
| `tools/`           | scripts that build the demo decks and the package, and check the package | [Continuous Integration](testing.md#continuous-integration)     |
| `benchmarks/`      | the benchmark script, its documents and the committed results            | [Benchmarks](environment.md#benchmarks)                         |
| `logo/`            | the logos, and the source of the social cards                            | [The Documentation Site](environment.md#the-documentation-site) |
| `.typst-packages/` | the symlink that resolves `@preview/animo:0.2.0` to the working tree     | [The Two Import Paths](environment.md#the-two-import-paths)     |

## Where the Specification Lives

This site does not include the specification.
The specification consists of two documents in the `planning/` directory of the
[repository](https://github.com/reproducible-reporting/animo).

[`planning/design.md`](https://github.com/reproducible-reporting/animo/blob/main/planning/design.md),
the design document, specifies how Animo works
and is the reference for any change in behaviour.
Read it before changing anything under `src/`.
Two of its sections carry more weight than the rest.
*Resolved Design Decisions* records questions that are settled, and why.
*Open Questions* records what is deliberately undecided.

[`planning/findings.md`](https://github.com/reproducible-reporting/animo/blob/main/planning/findings.md),
referred to as *Findings*,
records verified behaviour of typst and of the browsers that Animo drives.
The design of Animo depends on each of these behaviours, and each was expensive to establish.
Every entry in *Findings* therefore has a probe under `probes/`,
which asserts the behaviour itself rather than a feature that happens to depend on it.
See [Behaviour Probes](probes.md) for how the probes work.

Planned work is tracked as [issues](https://github.com/reproducible-reporting/animo/issues)
and pull requests on GitHub.

The other pages of this site refer to these documents as "the design document" and *Findings*.
A page that relies on a specific finding quotes the heading of its entry in prose, as in
"*Findings* records that the document timeline is not a clock".
To read the entry, search *Findings* for that heading.
The pages do not link to the heading,
because the documentation build does not check links into GitHub,
so such a link would break unnoticed when the heading is renamed.

## Contributing

Describe a change in behaviour in the design document before implementing it.
When an observation about typst or a browser was expensive to make,
record it in *Findings* and add a probe that asserts it.

See [CONTRIBUTING.md](https://github.com/reproducible-reporting/animo/blob/main/CONTRIBUTING.md)
for the conventions and for the commands to run before opening a pull request.
