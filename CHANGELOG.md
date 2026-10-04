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

### Changes

- Place the slides of the HTML presentation in a `.animo-stage` element inside `.animo-deck`.
  The stage is the visible rectangle, and it clips and isolates the crossfade between slides.
- Split the runtime of the HTML presentation into files under `src/js`,
  which are joined into the one script of the page.

### Fixes

- Draw a gradient and a clip path on every slide of the HTML presentation.
  A slide reached by a deep link, a reload or a step back lost them
  when an earlier slide used the same gradient or clip path,
  which turned the gradient background recipe into white slides.
- Give pointer events only to the slide that is shown in the HTML presentation.
  After a step back, the slide that was just left stayed on top of the one shown
  and received the clicks meant for it.
- Pause and resume only the animations that Animo started.
  The pause key used to pause every animation of the page, including the author's own.

## [0.1.1] - 2026-09-18

### Fixes

- Reduce the typst dependency from 0.15.1 to 0.15.0.
- Simplify package build script.

## [0.1.0] - 2026-09-17

This is the initial release of Animo.

[0.1.0]: https://github.com/reproducible-reporting/animo/releases/tag/v0.1.0
[unreleased]: https://github.com/reproducible-reporting/animo
