// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The published import form, exactly as every example and every documentation snippet
// shows it. It resolves through the repository-local package directory.
#import "@preview/animo:0.1.1": *

#show: animo.with(width: 16cm, height: 9cm)

// The vocabulary is only checked to be reachable:
// a star import of the package has to carry the `anim` module along as a name.
#assert.eq(type(anim), module)

#slide[
  = Hello from the working tree

  #tag("greeting")[A tag site, which does nothing yet.]
]
