// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// A slide: a viewport onto a canvas, plus the timeline that animates it.
//
// Placeholder. The viewport, the canvas and the four output modes arrive in phase 03,
// the timeline in phase 04.
#let slide(
  body,
  animation: (),
  canvas: auto,
  background: none,
  numbered: true,
) = body
