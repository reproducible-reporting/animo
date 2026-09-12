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

```typst
#import "@preview/animo:0.1.0": *

#slide(
  animation: {
    import anim: *
    sub(reveal("claim"))
    sub(move("claim", y: 1cm))
  },
)[
  #tag("claim", hidden: true)[Content and animation are separated.]
]
```

One source file compiles to four outputs:
an HTML presentation that animates in a browser,
a presentation PDF with one page per step,
a handout PDF with one page per slide,
and the same handout pages as SVG for embedding elsewhere.

**This is work in progress.**
The package resolves and compiles, and does nothing else yet.

## Documentation

- The site: <https://reproducible-reporting.github.io/animo/>
- The specification, including the reasoning behind every decision:
  [planning/design.md](planning/design.md)
- The order in which it is being built:
  [planning/impl_00_first_version/](planning/impl_00_first_version/)
- How to get from a clone to a green test suite: [CONTRIBUTING.md](CONTRIBUTING.md)
- The three test tiers and the behaviour probes:
  <https://reproducible-reporting.github.io/animo/testing/>

## License

Apache-2.0. See [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).
