// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The entrypoint of the stand-in module, shaped like animo's:
// a body-level name and a submodule that a star import has to carry along.

#import "anim.typ"

#let mark(name, body) = [#box(body)#label(name)]
