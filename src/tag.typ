// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// A tag site: content the timeline can address by name.
//
// Placeholder. The labelled group, the initial-state flags and the wrapping rules
// arrive in phase 04.
#let tag(
  name,
  body,
  hidden: false,
  removed: false,
  block: false,
  draw: false,
) = body

// A region: an area whose layout may change, with a footprint fixed across epochs.
//
// Placeholder. Footprints, nesting, sizing and clipping arrive in phase 08.
#let region(body) = body
