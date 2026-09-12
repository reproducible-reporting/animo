// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The timeline vocabulary, meant to be star-imported inside the `animation` argument
// of a slide, where shadowing the built-in `hide`, `move` and `scale` is harmless.
//
// Every primitive returns a plain description and performs no action itself.
// `sub` groups the operations that happen together in one subslide step.
//
// Placeholders. The plan model that gives these descriptions meaning arrives in phase 04,
// panning in phase 06 and the structural primitives in phase 07.

#let sub(handout: false, ..ops) = (
  kind: "sub",
  handout: handout,
  ops: ops.pos(),
)

// Continuous primitives: they change how already-rendered content is displayed.

#let reveal(name) = (kind: "reveal", name: name)

#let hide(name) = (kind: "hide", name: name)

#let move(name, x: 0pt, y: 0pt) = (kind: "move", name: name, x: x, y: y)

#let scale(name, factor) = (kind: "scale", name: name, factor: factor)

#let pan(x: 0pt, y: 0pt, relto: none) = (kind: "pan", x: x, y: y, relto: relto)

// Structural primitives: they change what typst has to lay out, and so start a new epoch.

#let replace(name, body) = (kind: "replace", name: name, body: body)

#let remove(name) = (kind: "remove", name: name)

#let apply(name, ..fns) = (kind: "apply", name: name, fns: fns.pos())

#let reset(name) = (kind: "reset", name: name)
