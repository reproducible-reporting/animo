<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to Animo are documented on this page.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Effort-based Versioning](https://jacobtomlinson.dev/effver/).

## [Unreleased]

### Added

- Announce the position of the HTML presentation as events on the root element:
  `animo:position`, `animo:leave`, `animo:enter` and `animo:mode`.
  They are sent after the page, the URL fragment and the clock have been updated.
  The root element also carries the active input mode as `data-animo-mode`.
- Ignore key presses and clicks inside an element with the attribute `data-animo-control`.
- Add the `push`, `cover` and `wipe` slide transitions beside the crossfade.
  Each takes a `direction`, which is `ltr`, `rtl`, `ttb` or `btt`.
- Add a transition function per transition to the `anim` module:
  `crossfade()`, `push(direction:)`, `cover(direction:)` and `wipe(direction:)`.
  Typst refuses a misspelt parameter at the call, and an editor shows the parameters.
- Add `init(..)` to the timeline, which is about the initial state of a slide.
  It takes the transition into the slide as its first argument, and `duration:`, `wait:`,
  `hold:` and `handout:` as keywords.
  It is written at most once, before the first `sub`.
- Add a `transition:` argument to the show rule, which is the transition of every slide whose
  `init` names none, `anim.crossfade()` by default.
- Add a `transition:` argument to `replace`, `remove`, `apply` and `reset`,
  which names the transition that carries the changed region across the boundary.
  It takes `auto` or `crossfade()`, and the plan carries the name per changed tag.
- Add the `morph()` transition for a region, written as the `transition:` of a structural
  primitive. It moves the content that both versions of the region share to its new place
  and fades the rest. A tag moves as one unless the primitive changes it, and letters are
  matched by their shape, so a reflowing paragraph needs no tags.
  `init` and the show rule refuse it.
  The example deck `morph.typ` shows it.
- Match shapes and images in a morph beside the letters, in reading order.
  A shape is matched when its outline and its stroke width are the same in both versions,
  whatever its colour, and an image when it is the same image at the same size.
  What sits inside a clipped box is matched only when the box stays where it is.
- Resize a shape in a morph when its size changes and its kind stays, such as the bar of a
  fraction that widens, a box that grows around its words or a circle that becomes an ellipse.
  Its outline and the width of its stroke change on the way, and rounded corners keep their
  shape. A shape is resized only into one between the same two matched neighbours and inside
  the same tags. Webkit, which does not animate the outline of a shape, fades it instead.
- Turn a shape into another of a different outline in a morph, such as a square into a circle,
  a star into a pentagon or an arrow into a line, when a tag that the primitive changes holds
  exactly one shape that is not matched otherwise before and after the step.
  The outline, the colours and the width of the stroke change on the way.
  Webkit fades the two shapes instead.
- Write the `<title>`, the `lang` and the `<meta>` elements of the HTML presentation
  from `set document(..)` and `set text(lang: ..)`.
- Carry the resolved `handout` flag of every state in the plan of the HTML presentation,
  and the settings of the deck in a `data-animo-config` attribute on `.animo-deck`.
- Add a `handout` key to the dictionary a `per-subslide` callback receives,
  which says whether the handout keeps that subslide, in every output type.
- Add `output-type()`, which returns `"html"`, `"presentation"` or `"handout"`
  and gives the same answer inside a slide as outside one.

### Changes

- **Breaking:** remove the `transition:`, `wait:`, `hold:` and `handout:` arguments of `slide`.
  They are written on `init(..)` in the timeline instead,
  as in `#slide(animation: anim.init(anim.push(), wait: 2))[..]`.
- **Breaking:** write a hard cut as a duration of zero, as in `init(duration: 0)`,
  rather than as `transition: none`.
  A duration of zero on a structural primitive is a hard cut of its region.
- **Breaking:** refuse a structural primitive on a `wrap: none` tag that no region holds,
  in every output type. The HTML presentation used to crossfade the whole slide for it.
  Give the tag a wrapper, as in `wrap: auto`, `box` or `block`, or put a region around it.
- **Breaking:** cross an epoch boundary with the outermost region around what changed.
  Two operations of one step that change two regions inside one region now have to agree
  about their timing and their transition, as two operations inside one region do.
- **Breaking:** make `primitive-duration:` and `transition-duration:` of the show rule defaults.
  A primitive or an `init` that states a `duration:` of its own now moves when the deck's
  duration is zero.
  In a deck with `transition-duration: 0`, a slide that names a transition has to state its
  `duration:` as well to be seen moving.
- Signal reduced motion with the custom property `--animo-motion: none` instead of zeroing
  the two durations of the deck, so that it still stops every duration written in a deck.
- Place the slides of the HTML presentation in a `.animo-stage` element inside `.animo-deck`.
  The stage is the visible rectangle, and it clips and isolates the crossfade between slides.
- Match the content of a tag in its place in a morph when the tag holds a tag that the
  boundary changes, as for the changed tag itself, rather than carrying it as one.
- Split the runtime of the HTML presentation into files under `src/js`,
  which are joined into the one script of the page.
- Plan every effect of a step before writing any of them, and accept any CSS property in an
  effect, so that a transition can read the page as it was before the step.
- Build the epoch renderings of a slide and the renderings of a `per-subslide` as stacks of one
  kind each, labelled `animo-<kind>-<index>`, with one implementation in typst and one in the
  runtime, which chooses the rendering of every stack by its kind.
- Lay the body of a slide out once in the HTML presentation, and place an epoch stack of one
  rendering per epoch in every region whose content changes, instead of one rendering of the
  whole slide per epoch.
  A slide with several epochs is smaller, compiles faster and loads faster in the browser,
  most of all when little of it changes.
  The paged outputs are unchanged.

### Fixes

- Draw a gradient and a clip path on every slide of the HTML presentation.
  A slide reached by a deep link, a reload or a step back lost them
  when another slide used the same gradient or clip path,
  which turned the gradient background recipe into white slides.
- Give pointer events only to the slide that is shown in the HTML presentation.
  After a step back, the slide that was just left stayed on top of the one shown
  and received the clicks meant for it.
- Pause and resume only the animations that Animo started.
  The pause key used to pause every animation of the page, including the author's own.
- Choose the transition of a slide boundary from the slide that owns it on a backward step too.
  A step back used to take the transition of the slide it entered.

## [0.1.1] - 2026-09-18

### Fixes

- Reduce the typst dependency from 0.15.1 to 0.15.0.
- Simplify package build script.

## [0.1.0] - 2026-09-17

This is the initial release of Animo.

[0.1.0]: https://github.com/reproducible-reporting/animo/releases/tag/v0.1.0
[unreleased]: https://github.com/reproducible-reporting/animo
