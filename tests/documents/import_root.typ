// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The internal import form, by absolute path with the repository as the typst root.
// It needs neither the package directory nor `TYPST_PACKAGE_PATH`.
#import "/src/lib.typ": *

#slide(animation: {
  import anim: *
  sub(reveal("greeting"))
})[
  #tag("greeting", hidden: true)[Hello from the working tree.]
]
