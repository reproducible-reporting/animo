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
However, this does not mean that Animo is vibe-coded AI slop: its design has been carefully iterated and tested with considerable human oversight.

The main reasons for not writing Animo completely by hand include:

- Animo relies heavily on Typst's work-in-progress HTML features,
  which are not guaranteed to be stable.
  It would be unwise to spend extensive human efforts into something that may need a major overhaul in the near future.
- Animo is primarily a proof of concept,
  a prototype, to showcase the kind of animated presentations that can be created using Typst.
- Supporting different web browsers and working around their quirks is extremely tedious and error-prone.
  Generative AI is ideal for iterating through bizarre edge cases.
  (All relevant findings are documented in the [Probes](probes.md) section and can be reused.)
