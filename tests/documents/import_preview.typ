// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The published import form, exactly as every example and every documentation snippet
// shows it. It resolves through the repository-local package directory.
#import "@preview/animo:0.1.0": *

#slide(animation: {
  import anim: *
  sub(reveal("greeting"))
})[
  #tag("greeting", hidden: true)[Hello from the working tree.]
]
