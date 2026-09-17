// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The internal import form, by absolute path with the repository as the typst root.
// It needs neither the package directory nor `TYPST_PACKAGE_PATH`.
#import "/src/lib.typ": *

#show: animo.with(width: 16cm, height: 9cm)

// The vocabulary is only checked to be reachable:
// a star import of the package has to carry the `anim` module along as a name.
#assert.eq(type(anim), module)

#slide[
  = Hello from the working tree

  #tag("greeting")[A tag site, which does nothing yet.]
]
