<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 03: Static Slides and the Four Outputs

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Slides*, *Canvas and viewport*, *Architecture*,
*Output mode selection*, and the findings on `set page`, on automatic canvas sizing
and on the live preview server.

## Goal

The first version anyone can actually look at:
a deck of static slides that compiles to all four outputs from one source,
with a viewport, a canvas larger than the viewport, background colours and images,
and slide-to-slide navigation in the browser.

No tags, no animation, no regions.
This phase is about the frame that everything later sits in, and about proving
the invariant the whole design rests on: the HTML and paged targets lay out identically.

## Prerequisites

Phases 01 and 02.

## Scope

### In Scope

- `slide(body, background: none, canvas: auto, numbered: true)`.
  The `animation:` argument may already exist and be required to be empty,
  so that phase 04 does not change the signature.
- **The deck entry point.**
  See the open questions below: the slide size has to come from somewhere,
  and `set page` is unavailable in the HTML target.
- **The viewport and the canvas** as two distinct rectangles.
  The viewport is the slide's visible box and clips (`overflow: hidden` in HTML).
  The canvas is what the body is laid out on, at least as large as the viewport,
  with its origin at the body's origin and the viewport at `(0pt, 0pt)`.
  A slide that places nothing outside the viewport must be indistinguishable
  from a slide with no canvas concept at all.
- **Automatic canvas sizing** through a `show place:` rule over the body,
  taking the union of the in-flow extent and every placement's extent,
  clamped to at least the viewport.
  Ratios come back unresolved (`50% + 0pt`), so the union is computed inside
  `layout(size => ..)`.
  `canvas: (width: .., height: ..)` is the explicit override.
- **Backgrounds**: a colour or an image, as CSS on the slide container in HTML
  and as a page fill in the paged targets.
- **The HTML document shell**: one container per slide, the viewport element,
  the canvas element inside it, and one `html.frame` inside that.
  The structure must already be the one *Architecture* describes,
  a grid cell with `isolation: isolate` holding what will later be several stacked frames,
  even though there is exactly one frame per slide today.
  Getting this wrong is expensive to fix in phase 09.
- **Slide-to-slide navigation** in the browser: keyboard and click,
  current slide in `location.hash`, restored on load, written with `history.replaceState`.
  This is what makes `typst watch` usable as a live preview
  and what the tier-3 fixtures deep-link through.
- **Output mode selection**: `target()` for HTML,
  `--input animo=presentation` versus the `handout` default for paged,
  and multi-page SVG with a `{p}` template.
- `numbered:` counting slides. Only counting. Nothing displays a number yet.

### Out of Scope

- Tags, animation, subslides, regions, epochs, panning.
  Every output in this phase has exactly one page or frame per slide.
- Displaying a slide number: phase 12.
- Header, footer and templating features, permanently.

## Open Questions in Focus

1. **How exact is the automatic canvas?**
   This is the design document's open question verbatim.
   `show place:` fires for every placement, including one nested inside a box or a grid cell,
   where `dx`/`dy` resolve against that container and the rule cannot tell the difference.
   The union is therefore exact for top-level placements and approximate below that.
   Decide whether that is good enough,
   or whether animo should count only placements it can attribute to the slide body,
   and document the failure mode either way.
   `canvas:` is the escape hatch whatever is decided,
   so the decision is about the default, not about capability.
1. **Where does the deck's shape come from?**
   The design document says a slide has the deck's slide size,
   but names no place where that size is set,
   and rules out `set page` for the HTML target.
   So this phase has to invent the deck-level entry point:
   a document-level show rule, an init function, a set rule on `slide`, or arguments on `slide`.
   The same decision covers the HTML page shell, the global stylesheet,
   and how the viewport scales to the browser window,
   which is the one piece of runtime behaviour that cannot be deferred,
   because a deck that does not fit the window is not a presentation.
   This is a lasting API decision: ask before building it.

No other open question from the design document is in scope for this phase.

## Tests

- Tier 1: `canvas: auto` computes the expected extent for a body with in-flow content only,
  with a top-level placement outside the viewport,
  and with a placement nested in a box, which is the approximate case above.
- Tier 2: the presentation and handout rasters of a static deck are identical to each other
  and show the viewport, clipped, with the background applied.
  Content outside the viewport does not appear.
  SVG export produces one file per page through the `{p}` template.
- Tier 3: the HTML deck renders one frame per slide inside the viewport element,
  navigation moves between slides, the hash reflects the current slide and restores on reload,
  and stepping does not accumulate browser history entries.
- **The cross-target invariant, tested directly:**
  a slide rasterised from the paged output and screenshotted from the HTML output
  agree on the geometry of the content.
  Express this numerically where possible rather than as a stored image.

## Documentation

- `docs/slides.md`: `slide`, its arguments, the viewport and the canvas,
  backgrounds, and what `numbered:` does and does not do.
- `docs/outputs.md`: the four outputs, the exact command lines,
  and the live preview with `typst watch --format html --features html --open`.
- The first real example deck under `examples/`, built by `plan.py` to all four outputs.

## Definition of Done

- A deck of several static slides compiles to HTML, presentation PDF, handout PDF and SVG.
- The HTML deck is navigable in a browser and survives a reload on the same slide.
- The automatic canvas behaves as documented, including its approximate case.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 04 adds the plan and tags inside this body.
Phase 05 animates inside this HTML shell.
Phase 06 moves the canvas element this phase creates.
Phase 09 stacks more frames in the grid cell this phase creates,
so the isolation and stacking context must already be right.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
