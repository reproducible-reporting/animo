---
description: >-
  Animo was developed in large part with the help of generative AI.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Generative AI Disclaimer

Animo was largely developed with the help of generative AI.
Its design was nevertheless iterated carefully and tested under considerable human oversight,
so Animo is not vibe-coded AI slop.

The main reasons for not writing Animo entirely by hand are:

- Animo relies heavily on the HTML export of typst,
  which is a work in progress and is not guaranteed to be stable.
  Spending extensive human effort on code that may need a major overhaul soon would be unwise.
- Animo is primarily a proof of concept,
  which shows what kind of animated presentations typst can produce.
- Supporting several web browsers and working around their quirks is tedious and error-prone.
  Generative AI is well suited to iterating through bizarre edge cases.
  Every behaviour of typst or a browser that Animo depends on is recorded in a document
  called *Findings* and checked by a probe, so that other projects can reuse these results.
  See [Behaviour Probes](probes.md) for the list.
