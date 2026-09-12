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

### What Was Built

The frame everything later sits in, and the first deck anyone can look at.

- **`src/deck.typ`**: the document-level show rule `animo(body, width:, height:, margin:)`,
  the state that carries the deck's shape to the slides, the paged mode selection,
  and the HTML page shell with its stylesheet and its runtime.
- **`src/canvas.typ`**: the automatic canvas.
  A `show place:` rule records every placement as `metadata` under one label,
  and `query` turns it back into data that the union is computed from.
- **`src/slide.typ`**: `slide(body, animation: (), canvas: auto, background: none, numbered: true)`, in both targets, with the viewport, the canvas, the background and the
  two counters.
- **`src/animo.css`** and **`src/animo.js`**: the page shell and the runtime,
  inlined with `read()` as the design requires.
- **`examples/tour.typ`**, built by `plan.py` to all four outputs under `build/examples/`.
- **`docs/slides.md`** and **`docs/outputs.md`**, in the `nav`, with the example included
  from the real file through `pymdownx.snippets`.
- Tests: `tests/test_slides.py` (tier 1), `tests/test_outputs.py` (tier 2),
  `tests/test_deck_html.py` (tier 3) and `tests/test_cross_target.py` (the invariant),
  with `tests/decks.py` holding the sources the tiers share.
  `probes/test_place_rule.py` is the new probe module.
  161 passed, 2 skipped; `pre-commit run --all-files` and `zensical build --strict` green.

`tests/documents/import_preview.typ` and `import_root.typ` had to be rewritten:
they passed a non-empty `animation:`, which this phase refuses.

### Decisions

**Asked, and answered by the author.**

1. *The deck entry point is `#show: animo.with(width: .., height: .., margin: ..)`*,
   a document-level show rule named after the package, which is exactly what `slipst`
   does. A show rule rather than an init call because it receives the whole document,
   which is what lets it be the HTML page, the stylesheet, the runtime and the paged
   `set page` at once. Verified before asking that this works in both targets.
1. *Its arguments are `width`, `height` and `margin`, with a non-zero margin default of
   1 cm.* There is no `paper:` argument: typst does not expose its paper-size table to
   scripts, so a paper name cannot be resolved to two lengths in the HTML target, and an
   argument that works in three outputs out of four is worse than no argument.
1. *The automatic canvas counts every placement*, resolving offsets from the canvas
   origin, rather than counting only the placements animo can attribute to the slide body.

**Taken in the session.**

- **A deck without the show rule still has slides**, at the defaults.
  A forgotten show rule is then a cosmetic mistake rather than a broken deck,
  and `#slide` stays usable on its own.
- **The canvas size never reaches CSS.** The canvas element is scaled as a whole by a
  factor computed in CSS from the deck's slide width, so a typst point is the unit of
  everything inside it at any window size, and `pan` will later be a translate in points
  with no unit conversion. Only the slide width, the aspect ratio and that factor are
  emitted as custom properties.
- **Every slide publishes its canvas as `metadata` under `<animo-canvas>`.**
  Introspection is the only channel that reaches both targets, tier 1 asserts through it,
  and phase 06 needs the number as well.
- **A background is a colour or content, and nothing else.** A colour is a page fill on
  paper and CSS in the browser; content is drawn into the slide behind the body, covering
  the viewport, which is the only form an image can take since typst has no image page
  fill either. A gradient or a tiling is refused with a message naming the form that
  works in all four outputs, rather than silently working in one target only.
- **`numbered:` and the position are two counters.** `animo-slide` is what `numbered:`
  counts; `animo-position` counts every slide and is what addresses a slide in the URL and
  in the DOM, because a presenter walks through a title slide whether or not it is
  numbered.
- **The runtime already carries the state half of the position.** The fragment is
  `#<slide>.<state>` as the tier-3 contract requires, every slide carries
  `data-animo-states="1"`, and stepping crosses a slide boundary when the state runs out.
  With one state per slide this is slide-to-slide navigation, and phase 05 only has to
  raise the count.

### Open Questions Answered

**How exact is the automatic canvas?** Every placement counts, with its offsets taken
from the canvas origin and its ratios and alignment resolved against the slide body.
For a placement written directly in the body this is exact. For one nested inside another
container it is short by wherever that container sits, because a container never sits at a
negative coordinate: the canvas comes out **too small rather than too large**, which is
the failure `canvas:` can fix. Documented in `docs/slides.md` with the failure case
spelled out, and pinned by a tier-1 test.

The phase file offered a second option, counting only the placements animo can attribute
to the slide body. **That option turned out not to be implementable**, which is the most
important thing this session measured; see the first finding below.

**Where does the deck's shape come from?** The show rule above.

### New Findings

Three new sections in the design document's *Findings*, and one measurement that retires
an idea rather than confirming one. None of them contradicts the design document.

1. **`layout(size => ..)` inside a `show place:` rule reveals the placement's own
   container, and cannot be used.** It reports `400 x 300pt` for a top-level placement,
   `113.39 x 56.69pt` for one inside a 4 cm box and `200 x 300pt` for one in a grid
   column, so it is exactly the discriminator the open question wanted. But it is
   block-level and breaks the paragraph the placement sits in: the same body measures
   `76.89pt` tall without it and `103.29pt` with it. The price is a body that lays out
   differently from the one the author wrote, which no canvas is worth. A `context` block
   holding nothing but `metadata` is inline and changes no measurement, and that is what
   animo uses. Probed both ways, including the negative case, because it looks like the
   obvious fix and is not.
1. **A show rule cannot return a value, so the placements travel as introspection**, and
   this works inside `html.frame`: `query` sees into a frame even though positions do not
   exist there. **A block sized from its own `query` converges**, because the body is laid
   out at a width that does not depend on the answer, so typst's introspection loop
   settles on the second pass. Measured: a block whose width is the maximum of `200pt` and
   a placement at `dx: 400pt` comes out at 419.4pt in the emitted frame.
1. **`html.frame` sizes its `<svg>` in `em` as an inline style**, dividing the frame's
   size in points by the text size in effect: a 200pt block is `18.181818182em` at 11pt
   text and `9.090909091em` at 22pt. An inline style outranks a stylesheet rule, so the
   first version of the HTML shell rendered every frame 16/11 too large, which looked like
   a scaling bug and was a specificity bug. Animo sizes the canvas element itself and
   overrides the frame with `width: 100% !important`. The frame also carries
   `overflow: visible`, so ink outside its viewBox paints and the viewport is what clips.
1. **`calc()` divides a length by a length and yields a number** in chromium 151:
   `calc(100px / 40px)` computes to `2.5`. That is what lets the window fit be a plain CSS
   expression over the slide width, with no resize listener and no measuring in the
   runtime.
1. **The two targets agree to 0.0017 of the slide** on every edge of a placed square,
   comparing a 454-pixel handout raster with a 908-pixel browser screenshot. That is one
   pixel of the coarser raster, so the invariant is exact to the limit of the measurement.
   `tests/test_cross_target.py` asserts it at a tolerance of 0.0025, which is that limit.

Two tooling observations, which do not belong in the design document:

- **StepUp 4.0.1 refuses a build product inside a static tree**
  ("a static tree is the sole owner of the files under it"), so the example decks cannot
  be built into `examples/`. They go to `build/examples/`, which `.gitignore` covers.
- **`stepup.core.api` has no `mkdir` in 4.0.1**, unlike the sibling deck repositories,
  and output directories are created by the step itself.

### A Refinement the Design Document Does Not State

*Canvas and viewport* says "the canvas origin is the body's origin" and "the viewport
starts at `(0pt, 0pt)`". With the `margin:` argument this session added, those two cannot
both hold, because the body's origin is inset by the margin. What is implemented, and what
`docs/slides.md` documents: **the canvas origin is the viewport origin, and the body sits
inside the canvas at the deck's margin.** The canvas extent therefore counts the margin as
well. Nothing else changes, and `pan` in phase 06 still moves the viewport over a canvas
whose origin is `(0pt, 0pt)`.

Two smaller points in the same paragraph: a negative `dx` or `dy` does not extend the
canvas, since the canvas is anchored at the origin, so content at a negative offset is out
of reach of `pan`; and the in-flow extent counts as well, so a body taller than the
viewport makes the canvas taller rather than being silently clipped.

**Should `planning/design.md` be updated to say this?** It is a consequence of an API
decision taken in this session, not a contradiction of a finding, so it is recorded here
and left for the author.

### What a Follow-Up Phase Should Know

- **Phase 04** fills in `animation:`, which `slide` currently asserts is empty, and `tag`
  and `region`, which are still the phase-01 stubs. The plan can be published next to
  `deck-shape` in `src/deck.typ`, which is the same mechanism and the same open question.
- **Phase 05** raises `data-animo-states` above `"1"` and animates inside the frames.
  The runtime's `step`, `clamp` and `show` already treat the state as a real coordinate,
  and `tests/test_deck_html.py` covers navigation, so what is missing is the animation
  and nothing about the addressing. The self-tests of the harness still run against
  `tests/documents/stand_in_deck.html`, as phase 02 asked, and now also against a real
  deck.
- **Phase 06** moves `.animo-canvas`, which has neither a `transform-origin` nor a
  `scale` of its own, so both `translate` and `scale` are free for the pan and a future
  zoom. See the follow-up below: this is not what this phase built. A pan offset is
  written as `calc(var(--animo-unit) * <points>)`, which is what `unit-length` in
  `src/deck.typ` produces. The canvas size is readable from `<animo-canvas>` metadata in
  both targets.
- **Phase 09** stacks its epoch frames in `.animo-canvas`, which is a single grid cell
  with `isolation: isolate` and `grid-row: 1 / grid-column: 1` on its children, asserted
  in `tests/test_deck_html.py`. The `!important` override on the frame size applies to
  every frame in the cell.
- **Every phase**: `tests/decks.py` builds the deck sources the tiers share, and
  `PagedRunner.svg` is new next to `png` and `pdf`.
- `ruff` is still not a `pre-commit` hook. All Python written in this phase is
  `ruff check` and `ruff format` clean, by hand, as in phase 02.

## Follow-Up: Firefox

Out of phase, after the author tested a built deck in firefox by hand and found the slide
rendered at about half size in the top-left corner of the window, with the content beyond
the viewport visible because the element that clips had nothing left to clip.

### What Was Wrong

The fit this phase built was `scale: calc(var(--animo-viewport) / var(--animo-width))` on
`.animo-canvas`, a length divided by a length. Chromium 151 computes that to a number.
Firefox 153 does not parse it at all, so it dropped the whole declaration, silently:
`CSS.supports("scale", "calc(100px / 40px)")` is false there.

This contradicted the *Fitting the slide to the browser window* finding, which recorded
the division as usable and had been measured in chromium only. The author was asked before
anything was changed, and chose the replacement below.

### What Changed

- **The fit is a length over a number.** `--animo-unit` is
  `calc(var(--animo-viewport) / <slide width in points>)`, one typst point as a CSS length
  at the current window size, and the canvas is *sized* in it rather than scaled.
  Every length animo emits is now that unit times a compile-time number.
  The runtime still measures nothing and listens for no resize.
  This also frees `scale` on the canvas, which *Architecture* rule 5 had asked for and
  this phase had occupied.
- **The browser tier runs in chromium, firefox and webkit**, parametrised on the engine
  through a `browser_name` fixture, so a failure names the engine and `-k firefox` selects
  one. The first two are required everywhere. Playwright builds webkit for ubuntu only, so
  it is best effort locally, where it skips with a reason, and required in continuous
  integration, which is ubuntu. Naming an engine with `--browser` makes it required, which
  is both how the workflows ask for all three and how a contributor gets playwright's own
  diagnosis instead of a skip.
- **Geometry is read with `getBBox` and `getScreenCTM`**, never with
  `getBoundingClientRect`, which is not the same box in the two engines. `harness.MEASURE`
  is the single expression, used by `Deck.rects` and by the probes' `measuring.rects`.

### New Findings, All Recorded in the Design Document

1. *Fitting the slide to the browser window*, rewritten: the division is chromium-only and
   fails silently, a length over a number is portable, and the canvas is sized rather than
   scaled. Probed by the new `probes/test_fitting.py`, which had no probe before.
1. *Cross-frame geometry is readable*, extended: `getBoundingClientRect` on a labelled
   group gives `19.57 x 13.86` in chromium and `358 x 13.90` in firefox, because typst
   writes `overflow: visible` on the `<svg>`. `getBBox` agrees exactly in both, and
   through `getScreenCTM` the two engines agree to 0.02 CSS pixels.
1. *CSS animation of typst SVG groups*, extended: firefox agrees on every row of the
   table, but resolves `transform-box: fill-box` to a centre about 0.7 CSS pixels from the
   one `getBBox` reports.
1. *Crossfading epoch frames*, extended: `mix-blend-mode: plus-lighter` is exact in
   chromium and firefox and not in webkit, where ten pixels on antialiased glyph edges
   drift by up to 42/255. This does not change the choice of blend mode, because the plain
   crossfade moves every pixel outside the region rather than ten, but it does make the
   exactness claim engine-dependent, and phase 09 should know that before it leans on it.
   The region-scoped variant *Architecture* prefers would settle it by not blending at
   all.

### What a Follow-Up Phase Should Know

- Three probe failures in firefox all traced to `getBoundingClientRect`, not to three
  separate engine differences. A probe that reads geometry should go through
  `harness.MEASURE` rather than query the DOM its own way.
- `tests/test_cross_target.py` now takes its tolerance as two pixels of the raster an edge
  is read out of, per axis, instead of one number for both. The old single tolerance was
  tighter than one pixel of the *vertical* floor and passed in chromium by luck.
- `probes/test_watch.py` had a race that only showed up under the load of three engines:
  it waited for `typst watch` to *serve* and then read the file from disk, which the
  server answers before the first compilation has written. It now waits for the file too.
- Webkit was measured by mounting the working tree into an `ubuntu:24.04` container at the
  same absolute path, because the virtual environment holds absolute symlinks, with a musl
  typst binary because the host's is built against a newer glibc than the image has.
  The recipe is in `docs/testing.md`. In that container the full suite is 255 passed and
  4 skipped, where the four are the two documented skips plus the two Typst Universe
  packages, which the container cannot download and continuous integration can.
- The changelog was left alone. Nothing here changes a released version, and the phase
  entries are not tracked there yet.
