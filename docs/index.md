---
description: >-
  Animo is a proof-of-concept presentation package for typst
  that keeps the content of a slide separate from its animation.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Animo

Animo is a proof-of-concept presentation package for
[typst](https://typst.app/) 0.15.1 or newer,
in which **content and animation are separated**.
The body of a slide declares what is on it,
tags the parts the timeline is allowed to address,
and marks the areas that may be relaid out.
The `animation` argument declares when and how those parts appear, move, scale,
change style and change content.
One source file compiles to four outputs:
an HTML presentation that animates in a browser,
a presentation PDF with one page per step,
a handout PDF with one page per slide,
and the same handout pages as SVG for embedding elsewhere.

Animo is under construction and nothing here is stable yet.
The full specification, including the reasoning behind every decision
and the verified typst behaviour the package rests on,
is the design document in the repository:
[planning/design.md](https://github.com/reproducible-reporting/animo/blob/main/planning/design.md).

## Status

The package resolves and compiles, and does nothing else yet.
[Development Environment](environment.md) describes how to get from a clone to a green test suite.
