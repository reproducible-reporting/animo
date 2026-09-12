// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// A submodule that shadows three typst built-ins, exactly as animo's `anim` does.
// It is a stand-in, deliberately not animo,
// so that the probes around it report on typst's import rules and on nothing else.

#let sub(..ops) = ((kind: "sub", ops: ops.pos()),)

#let reveal(name) = (kind: "reveal", name: name)

#let hide(name) = (kind: "hide", name: name)

#let move(name, x: 0pt, y: 0pt) = (kind: "move", name: name, x: x, y: y)

#let scale(name, factor) = (kind: "scale", name: name, factor: factor)
