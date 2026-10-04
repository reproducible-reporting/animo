<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to Animo are documented on this page.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Effort-based Versioning](https://jacobtomlinson.dev/effver/).

## [Unreleased]

### Fixes

- Draw a gradient and a clip path on every slide of the HTML presentation.
  A slide reached by a deep link, a reload or a step back lost them
  when an earlier slide used the same gradient or clip path,
  which turned the gradient background recipe into white slides.

## [0.1.1] - 2026-09-18

### Fixes

- Reduce the typst dependency from 0.15.1 to 0.15.0.
- Simplify package build script.

## [0.1.0] - 2026-09-17

This is the initial release of Animo.

[0.1.0]: https://github.com/reproducible-reporting/animo/releases/tag/v0.1.0
[unreleased]: https://github.com/reproducible-reporting/animo
