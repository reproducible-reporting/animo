// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

#import "@preview/animo:0.1.1": *
#import "@preview/oxifmt:1.0.0": strfmt
#import "@preview/cetz:0.5.2"

// The deck's shape is written once, as a document-level show rule.
// It is also what emits the HTML page, its stylesheet and its runtime,
// and what sets the page size of the two paged outputs.
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

// Use standard typst machinery to style the deck.
#show heading: set block(below: 1em)
#let dark = rgb("#001122")
#let bgrb = rgb("#ddeeff")
#show raw.where(block: true): it => block(
  fill: bgrb,
  inset: 0.3cm,
  radius: 0.1cm,
  it,
)
#show raw.where(block: false): it => highlight(
  fill: bgrb,
  stroke: bgrb + 0.1cm,
  radius: 0.1cm,
  it,
)

// The number this deck carries: the slide's number followed by a letter for the subslide,
// as in "3b". `numbering("a", ..)` is what turns the subslide's number into that letter,
// and `per-subslide` is what gives a number finer than a slide, because one rendering of
// the slide covers a whole run of subslides.
//
// The badge sits in the overlay rather than in the body, because an overlay is one
// rendering per slide where the body is one per epoch, and because the overlay belongs to
// the viewport, so a `pan` leaves the badge where it is. The semi-transparent white plate
// keeps it readable over a dark background as well as over a light one.
#let number-badge = context {
  let number = slide-number()
  if number != none {
    place(bottom + right, dx: -0.3cm, dy: -0.3cm, box(
      fill: white.transparentize(30%),
      inset: 0.15cm,
      radius: 0.1cm,
      text(size: 0.7em, fill: dark, {
        [#number]
        per-subslide(it => {
          if it.count > 2 [#numbering("a", it.number)]
        })
      }),
    ))
  }
}

// Animo has no footer machinery, so a recurring element is a wrapper around `#slide`.
// Shadowing the name is what keeps the slides below written the way the manual writes
// them, and the wrapper folds the badge into whatever overlay a slide writes for itself.
#let plain-slide = slide
#let slide(overlay: none, ..arguments) = plain-slide(
  overlay: {
    overlay
    number-badge
  },
  ..arguments,
)

// Then just a bunch of slides.

#slide(numbered: false, animation: {
  import anim: *
  sub(reveal("gloss"))
  sub(reveal("thesis"))
})[
  #set align(center + horizon)
  #v(0.5fr)

  A short tour of \
  #text(size: 2em)[*Animo*]

  #v(1fr)

  #tag("gloss")[
    #align(center, box(align(left, text(fill: luma(100), size: 0.9em)[
      _Latin:_ \
      #h(1em) 1st pers. of _animare_ "I bring to life" \
      #h(1em) ablative of _animus_ "with intent"
    ])))
  ]

  #v(1fr)

  #tag("thesis")[
    Everything on a slide competes for attention. \
    Animate what earns it.
  ]

  #v(0.5fr)
]

#slide(animation: {
  import anim: *
  sub(reveal("disclaimer1"))
  sub(reveal("disclaimer2"))
})[
  = Disclaimers

  #tag("disclaimer1")[
    1. Animo is *experimental* and *work in progress*.

      API stability is not strictly guaranteed before a 1.0 release, but no major breaking changes are planned.
  ]
  #v(0.5cm)

  #tag("disclaimer2")[
    2. Only the smallest examples are explained with source code in the slides.

      The full source code of this deck can be found in `examples/tour.typ`
      in the Animo Git repository.
  ]
]

// `hold: 0` sends the deck on the moment this step is triggered, so the circle's growth
// and the crossfade into the next slide run together and the two slides read as one build.
// It is written here rather than as `wait: 0` on the slide that follows because the
// sentence is about the motion on this slide.
#slide(animation: {
  import anim: *
  sub(hold: 0, reveal("circle"), scale("circle", f: 10), handout: true)
})[
  = You can keep things simple ...

  #v(1fr)

  ````typst
  #import "@preview/animo:0.1.1": *
  #show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

  #slide[
    = You can keep things simple ...

    ```typst
    ...
    ```
  ]
  ````

  #v(2fr)

  #place(center + horizon)[
    #tag("circle", circle(radius: 1cm, fill: dark))
  ]
]

#slide(background: dark)[
  #align(center + horizon, text(size: 2em, fill: white, weight: "bold")[
    ... but you don't have to!
  ])
]

#slide[
  = Animations

  ```typst
  #slide(animation: {
    import anim: *
    sub(reveal("first"))
    sub(reveal("second"))
    sub(hide("first"), scale("first", f: 2))
  })[
    = A slide with three "sub"slides

    #tag("first")[Appears first, will go out with a bang.]

    #tag("second")[Appears second and stays.]
  ]
  ```
]

#slide(animation: {
  import anim: *
  sub(reveal("first"))
  sub(reveal("second"))
  sub(hide("first"), scale("first", f: 2))
})[
  = A slide with three "sub"slides

  #tag("first")[Appears first, will go out with a bang.]

  #tag("second")[Appears second and stays.]
]

#slide(handout: true, animation: {
  import anim: *
  // Each step reveals the next piece of the derivation and pans so that the piece
  // just finished sits at the top of the viewport, which is how a long argument
  // stays readable on a slide that is four times as tall as the screen.
  // Every step is kept in the handout, because the last view shows the conclusion
  // and nothing of the derivation that leads to it.
  sub(hide("intro"), pan(relto: "problem"), reveal("step1"))
  sub(handout: true, reveal("step2"))
  sub(handout: true, pan(y: -1.5cm, relto: "step2"), reveal("step3"))
  sub(pan(relto: "step3"), reveal("step4"), hide("step2"))
  sub(handout: true, pan(relto: "step4"), reveal("mathnames"), hide("step3"))
  sub(reveal("step5"))
  sub(pan(relto: "step5"), reveal("step6"), hide("step4"))
  sub(reveal("extra"))
})[
  = All the Space You Need

  #tag("intro")[
    Consider the following fun mathematical problem:
  ]

  #tag("problem", box(
    width: 1fr,
    fill: bgrb,
    inset: 0.3cm,
    radius: 0.1cm,
  )[
    Find three real values, ${x_1, x_2, x_3}$, with given population statistics: mean $mu$, standard deviation $sigma$ and skewness $gamma$ (if the solution exists).
  ])

  #tag("step1")[
    #tag("sol")[*The solution*]

    1. Eliminate the mean by writing $u_k = x_k - mu$.
      The three given statistics translate into the following equations:

      $
        cases(
          p_1 = u_1 + u_2 + u_3 = 0,
          p_2 = u_1^2 + u_2^2 + u_3^2 = 3 sigma^2,
          p_3 = u_1^3 + u_2^3 + u_3^3 = 3 gamma sigma^3
        )
      $
  ]

  #tag("step2")[
    2. The three unknowns are the roots of a cubic polynomial in $t$:

      $
        (t - u_1) (t - u_2) (t - u_3) & = t^3 - a t^2 + b t - c
      $
  ]

  #tag("step3")[
    3. One can show this by simply constructing the coefficients:

      $
        a & = u_1 + u_2 + u_3 = p_1 = 0 \
        b & = u_1 u_2 + u_2 u_3 + u_3 u_1 = (p_1^2 - p_2) / 2 = -3 / 2 sigma^2 \
        c & = u_1 u_2 u_3 = p_1^3/6 - (p_2 p_1)/2 + p_3/3 = p_3/3 = gamma sigma^3
      $
  ]

  #tag("step4")[
    4. The polynomial is now known and we just have to solve it:

      $ t^3 - 3 / 2 sigma^2 t - gamma sigma^3 = 0 $

      #tag("mathnames")[
        #underline[Note:]
        This equation was derived here from scratch, but mathematicians have names for the trick and the intermediate quantities involved:

        - The sums $p_1$, $p_2$ and $p_3$ of step 1 are the power sums.
        - The coefficients $a$, $b$ and $c$ are the elementary symmetric polynomials of the roots.
        - The little computation is referred to as Newton's identities for three variables.
      ]
  ]

  #tag("step5")[
    5. Substitute $t = sqrt(2) sigma cos theta$ and divide by $sigma^3$.
      The left-hand side is then the triple angle identity
      $cos 3 theta = 4 cos^3 theta - 3 cos theta$ in disguise:

      $
        sqrt(2) / 2 (4 cos^3 theta - 3 cos theta) = gamma
        quad <==> quad
        cos 3 theta = sqrt(2) gamma
      $
  ]

  #tag("step6")[
    6. The cosine takes that value at three angles, one per root:

      $
        x_k = mu + sqrt(2) sigma cos((arccos(sqrt(2) gamma) + 2 pi k) / 3),
        quad k = 0, 1, 2
      $

      #tag("extra")[
        The angle is real only for $abs(gamma) <= 1 / sqrt(2)$,
        and that bound is no accident:
        it is the largest population skewness three real values can have.
      ]

  ]
]

// The one slide of this deck that is entered with a cut rather than a crossfade.
// A dark full-bleed ground arriving out of a light slide reads better as a change of
// chapter than as a dissolve, and `transition:` is written on the slide it is about.
#slide(
  transition: none,
  background: rect(
    fill: tiling(
      size: (1cm, 1cm),
      {
        place(square(fill: black, size: 1cm))
        place(polygon(
          (0.5cm, 0cm),
          (1cm, 0.5cm),
          (0.5cm, 1cm),
          (0cm, 0.5cm),
          fill: dark,
          stroke: none,
        ))
      },
    ),
    width: 16cm,
    height: 9cm,
  ),
  overlay: place(center + horizon, rect(
    stroke: (paint: white, dash: "dashed"),
    width: 8cm,
    height: 4.5cm,
    inset: 1cm,
    radius: 0.2cm,
    align(top, text(fill: white)[*A slide is a view onto a canvas.*]),
  )),
  animation: {
    import anim: *
    sub(reveal("canvas"))
    sub(pan(dy: 6cm))
    sub(reveal("clipped"))
  },
)[
  #text(fill: white)[
    = Animo Slide Anatomy
  ]

  #place(center + horizon, dx: 1cm, dy: 3.5cm)[
    #tag("canvas")[
      #rect(
        fill: color.oklch(80%, 80%, 270deg),
        width: 12cm,
        height: 12cm,
        inset: 1cm,
        radius: 0.2cm,
      )
    ]
  ]

  #place(center + horizon, dx: 1cm, dy: 3cm)[
    #tag("canvas")[The canvas can extend beyond the viewport.]
  ]

  #place(center + horizon, dy: 5.7cm)[
    #tag("canvas")[You can pan the viewport to look around.]
  ]

  #place(center + horizon, dy: 7cm)[
    #tag("clipped")[
      Anything outside the viewport gets clipped.

      Nothing flows onto the next slide.
    ]
  ]
]

#let ncirc = 12

#slide(animation: {
  import anim: *
  // The ring is the state the handout keeps, and the scattered one is the state it drops:
  // the last step carries every circle past the viewport, so a page of it is a bare title.
  for (radius, keep) in ((2.7cm, true), (10cm, false)) {
    sub(
      handout: keep,
      ..for icirc in range(ncirc) {
        let name = strfmt("c{}", icirc)
        let angle = 360deg * icirc / ncirc + 90deg * int(keep)
        (
          reveal(name),
          move(
            name,
            dx: radius * calc.cos(angle),
            dy: radius * calc.sin(angle),
          ),
          replace(name, circle(radius: radius / 5, fill: color.oklch(
            80%,
            80%,
            icirc / ncirc * 360deg,
          ))),
        )
      },
    )
  }
})[
  #align(center + horizon, text(weight: "bold", size: 1.7em)[
    Code your \
    animations \
    in typst
  ])

  #{
    for icirc in range(ncirc) {
      place(
        center + horizon,
        tag(strfmt("c{}", icirc), circle(
          radius: 0.3cm,
          fill: color.oklch(10%, 80%, icirc / ncirc * 360deg),
        )),
      )
    }
  }
]

// `handout: true` keeps the initial state, which is the one that shows the reserved gap.
// Without it the handout would keep only the final state, where the sentence is complete
// and the slide makes no point.
//
// `wait: 0.3` enters this slide a third of a second after the circles scatter, so the deck
// crosses this boundary on its own, and one press back plays the scatter in reverse.
// It is written here rather than as `hold: 0.3` on the slide before, whose timeline is
// written by a loop that would need a condition to time its last step alone.
#slide(handout: true, wait: 0.3, animation: {
  import anim: *
  sub(reset("1"))
})[
  = Space Is Reserved

  ```typst
  This sentence contains a #tag("1")[hidden]
  word and *reserves space* for it.
  ```

  #block(stroke: dark, inset: 0.2cm)[
    This sentence contains a #tag("1")[hidden]
    word and *reserves space* for it.
  ]

  ```typst
  #region[
    This sentence contains a #tag("1")[hidden]
    word and will *reflow* because it is *replaced* as a whole.
  ]
  ```

  #block(stroke: dark, inset: 0.2cm)[
    #region[
      This sentence contains a #tag("1")[hidden]
      word and will *reflow* because it is *replaced* as a whole.
    ]
  ]
]

#slide(animation: {
  import anim: *
  sub(reset("ft"))
})[
  = Animated Equations

  #align(horizon)[
    #region[
      $
        D = 1 / (2 d)
        #tag("ft", box(fill: yellow, inset: 0.2cm, $lim_(f -> 0)$))
        integral_(-infinity)^infinity
        lr(chevron.l vec(v)(t) dot vec(v)(0) chevron.r, size: #1.5em)
        #tag("ft", box(fill: yellow, inset: 0.2cm, $e^(i 2 pi f t)$))
        thin dif t
      $
    ]
    #v(1cm)
  ]
]

#slide(animation: {
  import anim: *
  sub(move("home", dy: -1cm), reveal("sweet"))
})[
  = Animated Content Inside a Cetz Figure

  #region[
    #align(center + horizon)[
      #cetz.canvas({
        import cetz.draw: *
        line(
          (0, 0),
          (5, 0),
          (5, 4),
          (2.5, 6),
          (0, 4),
          close: true,
          fill: dark,
          stroke: none,
        )
        content((2.5, 2), tag("home", text(size: 4em, fill: white)[*Home*]))
        content((2.5, 1.6), tag("sweet", text(
          size: 2em,
          fill: white,
        )[sweet home]))
      })
    ]
  ]
]


// Timing is the one thing the timeline says that no page can show,
// so the slide that explains it is also the slide that does it.
#slide(animation: {
  import anim: *
  // `wait:` brings a step up on a timer instead of on a click.
  sub(wait: 1.5, hold: 1.5, reveal("timed1"))
  sub(reveal("timed2"))
  // `delay:` holds one operation back inside its step,
  // so the three lines below arrive in the order they are written,
  // and `duration:` gives the last of them a tempo of its own.
  sub(
    reveal("d1"),
    reveal("d2", delay: 0.3),
    reveal("d3", delay: 0.6, duration: 1),
  )
})[
  = Timer controls (in HTML)

  #tag("timed1")[
    1. `wait:` on a `sub` or on a `#slide` autoplays its animation after waiting the given number of seconds.
  ]

  #tag("timed2")[
    2. `hold:` on a `sub` or on a `#slide` has the same autoplay effect on the *next* (sub)slide.
  ]

  #tag("d1")[
    3. `delay:` delays an animation primitive, e.g. `reveal`, `move`, `scale`, etc.

    #tag("d2")[This sentence was shown with 0.3 seconds of delay.]
  ]

  #tag("d3")[
    4. `duration:` controls the speed of an animation primitive.
      (This item had a `duration` of 1 second.)
  ]

  #v(1fr)

  A presenter can always step ahead of a timer. \
  Travelling back plays the deck backwards, and `Space` stops it where it is.
]

#slide(animation: {
  import anim: *
  sub(reveal("1"))
  sub(reveal("2"))
  sub(reveal("3"))
  sub(reveal("remark"))
})[
  = Output Types

  #v(1fr)

  #grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 0.2cm,
    row-gutter: 0.5cm,
    align: center + horizon,
    tag("1", box(
      fill: bgrb,
      width: 1fr,
      inset: 0.5cm,
      radius: 0.5cm,
    )[
      #circle(radius: 0.5cm, fill: dark, text(size: 1.5em, fill: white)[*1*])

      *HTML presentation*

      The animated deck

      To be presented with a browser
    ]),
    tag("2", box(
      fill: bgrb,
      width: 1fr,
      inset: 0.5cm,
      radius: 0.5cm,
    )[
      #circle(radius: 0.5cm, fill: dark, text(size: 1.5em, fill: white)[*2*])

      *Static presentation*

      One page per step

      For a venue without a browser
    ]),
    tag("3", box(
      fill: bgrb,
      width: 1fr,
      inset: 0.5cm,
      radius: 0.5cm,
    )[
      #circle(radius: 0.5cm, fill: dark, text(size: 1.5em, fill: white)[*3*])

      *Static handouts*

      One page per slide

      For printing or distributing
    ]),
    [],
    grid.cell(colspan: 2, tag("remark")[
      The two static types are paged modes \
      and can be exported to PDF, SVG or PNG.
    ]),
  )
]

#slide(animation: {
  import anim: *
  sub(reveal("last"))
})[
  #place(center + horizon)[
    Whenever your present ...

    #tag("last")[... present _Animo_.]
  ]
]

#slide[
  #place(center + horizon, text(size: 1.2em, fill: dark, weight: "bold")[
    Thank you for watching!
  ])
]
