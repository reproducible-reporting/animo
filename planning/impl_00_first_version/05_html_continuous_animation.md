<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 05: HTML Continuous Animation

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Architecture*, especially rules 1, 3 and 4,
*Live preview*, and the findings on `data-typst-label`, on CSS animation of typst SVG groups,
on what CSS can and cannot reach, and on `hide()` being irreversible in the browser.

## Goal

The deck animates.
Stepping through subslides in the browser reveals, hides, moves and scales tagged elements
smoothly, and the state is addressable by URL.

This is the phase where animo's central claim is either true or not.

## Prerequisites

Phases 01 to 04.

## Scope

### In Scope

- **The runtime**: plain JavaScript, inlined with `read()`, plus a stylesheet the same way.
  No node toolchain, because the package is installed from Universe.
  `slipst`'s runtime is roughly 214 lines of TypeScript and 68 lines of CSS,
  which is the order of magnitude to expect.
- **Emitting the plan into the page.**
  The resolved per-state display state has to reach the browser.
  Decide how, and keep it inspectable: a `data-` attribute or a JSON script element
  is easier to debug and to test than generated CSS.
- **Subslide stepping**: forward and backward, keyboard and click,
  with the slide and subslide in `location.hash` and written with `history.replaceState`.
  Restoring from the hash on load must **snap** to the state, not animate into it.
  `typst watch` reloads with `location.reload()`, which keeps the fragment,
  so this is what puts the author back on the same subslide after every recompile.
- **The four primitives in CSS**, following the findings exactly:
  - `reveal` and `hide` animate `opacity` on the tag's **inner** group;
  - `move` animates the CSS `translate` property;
  - `scale` animates the CSS `scale` property, with `transform-box: fill-box`
    and `transform-origin: center`;
  - the `transform` shorthand is never emitted, because it clobbers typst's own positioning.
- **Initially hidden elements are rendered normally and hidden with `opacity: 0`.**
  Typst's `hide()` emits nothing to draw, so CSS can never bring it back.
  Only the paged outputs may use `hide()`.
  This asymmetry between the targets is worth a test of its own.
- **Selectors scoped to the slide container**, so `[data-typst-label="line1"]` in one slide
  cannot reach another, and so one rule reaches every occurrence of a tag within a slide.
- **Applying continuous state to all frames of a slide, not only the visible one.**
  There is one frame per slide until phase 09, so this costs nothing now and is free to get
  right; it is rule 1 of *Architecture* and it is what keeps phase 09 simple.
- Units: CSS lengths inside a group are user units scaled by the SVG's rendered size,
  so a move expressed in typst lengths stays the same fraction of the slide at any window size.
  Verify this holds at two window sizes rather than assuming it.

### Out of Scope

- Epoch frames, crossfades and structural steps: phases 07 and 09.
- `pan`: phase 06.
- Slide-to-slide transitions, permanently for 0.1.0.

## Open Questions in Focus

1. **Is the Web Animations API the right driver, and what are the easing and duration defaults?**
   The design document's open question, and the reason this phase exists as a unit.
   Paused animations with an explicit `currentTime` would give reversible stepping,
   correct snap-to-state on deep links, and a clock that phase 09's crossfades can share.
   CSS transitions handle all three poorly.
   It is also what makes a mid-transition assertion reproducible,
   because a test sets `currentTime` instead of racing a transition.
   Decide it here, with the tests that depend on it,
   and record what backward stepping and deep-linking actually do under the choice.
   Defaults for duration and easing are part of the same decision
   and should be stated in the documentation as values, not as adjectives.
1. **How do CSS-animated typst SVG groups actually look in motion?**
   Also the design document's open question:
   stroke scaling under `scale`, text rendering during transforms,
   and antialiasing seams at subslide boundaries.
   This one is answered by looking, not by asserting.
   Build a small deck that exercises it, look at it, and record what you see in the session log,
   including anything that suggests a default should change,
   for example whether `scale` on text is usable at all.

No other open question from the design document is in scope for this phase.

## Tests

Tier 3 carries this phase, and the tests should be numeric rather than pictorial:

- the geometry of a tagged element at each subslide, read with `getBoundingClientRect`,
  matches what the plan says;
- typst's own `transform` attribute survives every animation, as the findings require;
- mid-flight sampling at a fixed `currentTime` gives the expected interpolated values;
- a deep link lands on the right subslide with the right geometry and without animating;
- an initially hidden element has ink in the DOM and `opacity: 0`,
  which is what distinguishes the HTML path from the paged one;
- stepping backwards returns to exactly the earlier geometry;
- the hash updates without growing the history.

Tier 2 must keep passing unchanged: the paged outputs are not touched by this phase,
and a regression there means the display state was accidentally rewritten.

## Documentation

- `docs/animation.md` gains the browser half: what animates, how, and with what defaults.
- `docs/presenting.md`: keys, deep links, and the live preview loop with `typst watch`.
- Document the `hide` versus `hidden:` asymmetry between targets explicitly,
  because an author who reads only the paged behaviour will be surprised.

## Definition of Done

- A deck steps through subslides in chromium with smooth motion, forwards and backwards.
- Deep links land on the right state without animating.
- Tier-3 assertions cover geometry, interpolation and navigation.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 06 adds the canvas translate on top of this runtime.
Phase 09 adds a second animation class that must share this phase's clock
and must sit in the outer transform slot, above everything this phase writes.
Keep the runtime's structure ready for that: the two slots are already emitted by phase 04,
and this phase must use only the inner one.

## Session Log

To be written at the end of the session, per the rules in [README.md](README.md).
