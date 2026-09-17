---
description: >-
  What the development guide covers, and where the specification of Animo lives.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Developing Animo

This guide is for somebody changing Animo itself.
Somebody writing a deck with Animo wants the
[Presentation Author Guide](slides.md) and the [Reference](reference.md) instead.

| Page                                               | Covers                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------- |
| [Development Environment](environment.md)          | a clone, the `uv` environment, the two import paths, the commands |
| [Testing](testing.md)                              | the three test tiers, the engines, the reference images           |
| [Architecture of the HTML Output](architecture.md) | how a slide reaches the browser and what the runtime does         |
| [Behaviour Probes](probes.md)                      | what a probe asserts, and what to do when one fails               |

## Where the Specification Lives

The specification is not on this site.
It is two documents in the `planning/` directory of the
[repository](https://github.com/reproducible-reporting/animo).

`planning/design.md` specifies Animo and is the reference for any change in behaviour.
Read it before changing anything under `src/`.
Two of its sections carry more weight than the rest:
*Resolved Design Decisions* records questions that are settled and why,
and *Open Questions* records what is deliberately undecided.

`planning/findings.md`, referred to as *Findings*, records verified behaviour of typst and
of the browsers Animo drives that the whole design rests on.
Every entry there is expensive to rediscover, and every entry gets a probe under `probes/`
that asserts the behaviour itself rather than a feature that happens to depend on it.

Further development is tracked on GitHub as issues and pull requests,
not as a phase plan kept in the repository.

This is the one place on this site that names those documents.
A page that rests on a specific finding names it in prose, as
"*Findings* records that the document timeline is not a clock",
and leaves you to search the document,
because a link to a heading inside it would rot without failing.

## Contributing

A change in behaviour is described in the design document before it is implemented.
An observation about typst or a browser that was expensive to make belongs in *Findings*,
and then in a probe.

The conventions, and what to run before opening a pull request, are in
[CONTRIBUTING.md](https://github.com/reproducible-reporting/animo/blob/main/CONTRIBUTING.md).
