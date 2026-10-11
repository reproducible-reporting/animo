---
description: >-
  The timeline of a slide: subslides, the four continuous primitives,
  and the four timing keywords.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Continuous Animations

The demo deck for this page is
[`continuous.typ`](https://github.com/reproducible-reporting/animo/blob/main/demos/continuous.typ)
([HTML](https://reproducible-reporting.github.io/animo/demos/continuous.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/demos/continuous-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/demos/continuous-handouts.pdf)).
It shows subslides, the block-scoped import, moving and scaling,
and the four timing keywords.

The `animation` argument of a slide is its timeline.
It says when and how the [tagged](tags.md) parts of the body appear, move and scale.

```typst
#slide(
  animation: {
    // The primitives live in the `anim` module and are imported inside this block.
    import anim: *
    sub(reveal("second"))
    sub(move("first", dx: 2cm), scale("second", f: 1.3))
  },
)[
  #tag("first")[This line moves to the right on the last subslide.]

  #tag("second")[This one starts out invisible, because the timeline reveals it.]
]
```

Animo reads the timeline **before typst lays out the body**.
For this reason, the timeline is an argument of `#slide` rather than a marker at the end of the
body.

## Subslides

A `sub(..ops)` call groups the operations that happen together
when the presenter proceeds to the next subslide.
The `animation` argument is a code block of such calls,
and typst joins the values of these calls into a list:

```typst
#slide(
  animation: {
    import anim: *
    sub(reveal("a"))
    sub(hide("a"), move("b", dy: 1cm))
  }
)[...]
```

A slide with *S* `sub` calls has **S+1 states**, numbered 0 to *S*.
State 0 is the slide as the body declares it.
State *i* is state *i-1* with the operations of the *i*-th `sub` applied.
The static presentation has one page per state,
and the HTML deck steps through the same states in a browser.

`sub` treats every argument as an operation,
except [`wait:`](#timing), [`hold:`](#timing) and [`handout:`](handouts.md#the-handout-flag).
`sub` checks that each of these arguments really is an operation, for the following reason.
The star import `import anim: *` only adds the names that `anim` defines.
Every other name still refers to the standard library of typst,
so a misspelled or unsupported primitive calls a standard library function instead.
For instance, Animo has no `rotate` primitive,
so `rotate("b", 45deg)` calls typst's `rotate`, which returns content.
Without the check, that content would cause a confusing error much later.
With the check, `sub` stops with an error message that gives the position of the argument
in the `sub` call.

## The Block-Scoped Import

The primitives are imported inside the animation block, in the style of cetz.
Three primitives, `hide`, `move` and `scale`, have the same name as a typst built-in.
Because the import is scoped to the block, these names refer to Animo's primitives only inside
the timeline.
Everywhere else, including the slide body, they refer to typst's own elements.

`#tag`, `#region` and `#slide` are used in the body,
so they are imported at the top of the file as usual.
A star import of the package also imports the `anim` module,
so `anim.reveal("a")` works without the import inside the block.

## Continuous Animation Primitives

The continuous primitives change only how content is *displayed* after typst has laid it out.
A browser can therefore animate them smoothly,
and the paged outputs need no extra [rendering](performance.md) of the slide for them.

| Primitive                              | Meaning                                        |
| -------------------------------------- | ---------------------------------------------- |
| `reveal(name)`                         | make the element visible                       |
| `hide(name)`                           | make the element invisible, keeping its space  |
| `move(name, x:, y:, dx:, dy:, relto:)` | translate the element                          |
| `scale(name, f:, fx:, fy:)`            | scale the element, in place or from its anchor |

In every case, the element keeps the space that the body gave it,
so the rest of the slide stays where it is.

Each primitive changes one part of the display state of its tag:

- `reveal` and `hide` set whether the tag is visible.
- `move` sets the position of the tag.
  `x` and `y` replace the position, and `dx` and `dy` add to it.
- `scale` sets the factor of each axis that the call names.

A tag that the timeline never reveals or hides stays visible.
A tag whose first `reveal` or `hide` operation is a `reveal` starts hidden instead
(see [Tags](tags.md#initial-state-of-tagged-content)).

A tag that starts hidden and a tag that `hide` has hidden are in the same state.
The paged outputs and the HTML output draw this state in different ways.
In the paged outputs, Animo wraps a hidden element in typst's own `hide`,
which lays the element out without drawing it.
In the HTML output, typst renders the element normally, and the runtime hides it with
`opacity: 0`, so that a later `reveal` can show it again.
The text of a hidden element is therefore in the HTML file,
where a reader who searches the page can find it.
Do not use a hidden element for content that has to stay secret,
because the HTML output contains it.

### Where `move` Puts Things

`move` sets the position of an element in one of two ways,
and it chooses between them separately for the x and y directions:

| Argument   | Effect                                                         |
| ---------- | -------------------------------------------------------------- |
| `x`, `y`   | places the element at that position, measured from the anchor  |
| `dx`, `dy` | moves the element over that distance from its current position |
| `relto`    | names the tag whose anchor `x` and `y` are measured from       |

The **anchor** of a tag is the **top-left corner of its wrapper**,
at the place where the body laid the tag out.
`x` and `y` are measured from the canvas origin (where the body of the slide starts),
or from the anchor of the tag that `relto` names.
`move` puts the anchor of the moved tag on the point that `x` and `y` give.

```typst
animation: {
  import anim: *
  sub(move("label", relto: "node"))   // put the label on the node
  sub(move("label", dy: -5mm))        // and lift it a little from there
  sub(move("label", x: 1cm, y: 1cm))  // or put it in the corner of the canvas
}
```

All four offsets are lengths.
Animo refuses a `move` that combines `x` with `dx`, or `y` with `dy`,
because the two offsets of such a pair are measured from different places.
Animo also refuses a `move` that has none of the arguments `x`, `y`, `dx`, `dy` and `relto`.

The anchor comes from the *body*, which has two consequences.

- **The anchor of a tag is the same in every state**,
  whatever a `move` or a `scale` did to that tag.
  A `move` with `x` and `y` therefore gives the same position every time it is applied,
  and `move("b", relto: "a")` gives the same position whatever moved `a` before.
- **A name that tags several places moves as one.**
  The first tag site of that name lands on the target,
  and every other site moves over the same distance.

When the moved tag is also scaled, its scaled top-left corner lands on the target,
because a scale grows a placed element from its anchor
(see [What `scale` Sets](#what-scale-sets)).

See [What `relto` Reads](viewport.md#what-relto-reads) for more details.

### What `scale` Sets

`scale` takes `f`, which sets the factor of both axes,
or `fx` and `fy`, which each set the factor of one axis.
Animo refuses a `scale` that combines `f` with `fx` or `fy`.
Each factor is a number or a ratio, so `f: 2` and `f: 200%` are the same.

**`scale` sets a factor and does not multiply it with the factor that is already there.**
After `scale("a", f: 2)` in one subslide and again in the next, `a` is twice its size,
not four times.
`scale("a", f: 1)` restores the original size of `a`, whatever came before.
An axis that the call does not mention keeps the factor it had.

**A scaled element grows about its centre, unless a `move` has placed the element.**
By default, the element grows about the centre of its box,
so it stays where the body and any `dx` or `dy` put it.
A `move` with `x`, `y` or `relto` places the element on the axes it addresses.
On a placed axis, the element grows from its anchor instead,
so the corner that the `move` put on the target stays there at any factor.
An axis stays placed in the subslide of the `move` and in every later subslide,
also when a later `dx` or `dy` moves the element along that axis.
Animo decides this for each axis separately.
After `move("a", x: 2cm)`, for example, `a` grows rightwards from 2 cm,
and it grows about its centre in the vertical direction.

```typst
animation: {
  import anim: *
  sub(scale("label", f: 1.5))                     // grows about its centre, in place
  sub(move("label", relto: "node"))               // its scaled corner lands on the node
  sub(scale("label", f: 2))                       // and stays there while it grows
}
```

## Timing

Four arguments decide *when* and *how long* rather than *what*.
Each of them is a plain number of **seconds**, because typst has no literal for time.
For example, `2s` is a syntax error in typst.

| Argument    | Says                                        | Written on            |
| ----------- | ------------------------------------------- | --------------------- |
| `wait:`     | when a subslide comes up                    | `sub`, `init`         |
| `hold:`     | how long a subslide stays up                | `sub`, `init`         |
| `delay:`    | when one operation inside a subslide starts | any primitive         |
| `duration:` | how long that operation then takes          | any primitive, `init` |

All four arguments affect only the HTML output.
The paged outputs have one page per state and no motion between the pages,
so they ignore all four.

### `wait:` and `hold:`

With `wait:` or `hold:`, the deck brings up the next subslide after a fixed time,
instead of waiting for a click of the presenter.
Both arguments set the gap between two subslides,
but they are written on different sides of that gap.
`wait:` is the delay before the subslide that it is written on.
`hold:` is the delay after the subslide that it is written on, before the next subslide.
Both are written on a `sub`, and on [`init`](slides.md#slide-transitions) for the initial
state, which has no `sub`:

```typst
#slide(animation: {
  import anim: *
  init(wait: 2)              // entered two seconds after the slide before it
  sub(reveal("a"))           // waits for the presenter
  sub(wait: 3, reveal("b"))  // comes up three seconds after the previous subslide
  sub(hold: 4, reveal("c"))  // waits for presenter and stays up for four seconds
})[...]
```

The default of both is `none`, in which case the presenter has to click to proceed.
A deck that sets a `wait:` or a `hold:` for every gap plays itself from the first state to the
last.

The deck measures both arguments from the moment the earlier subslide of the gap was
**triggered**, not from the moment the motion of that subslide finished.
A `hold: 0` therefore starts the next subslide at the same moment as the subslide it is
written on.
When the next subslide is on the next slide,
the motion of the last subslide and the slide transition play at the same time.

**Each gap takes one number.**
Animo refuses a gap that has a `hold:` on the subslide before it and a `wait:` on the subslide
after it, also when the gap lies between two slides.
The error message names both subslides.
Choose the argument by the subslide that your intent is about.
`init(wait: 0)` on a slide says that the deck enters this slide without a click.
`hold: 0` on a subslide says that the deck does not stop at that subslide.

The presenter keeps control of a deck that plays itself.
See [Presenting](presenting.md#a-deck-that-plays-itself)
for how a presenter can control animations that start automatically.

### `delay:` and `duration:`

Every primitive takes both arguments.
`delay:` holds one operation back within its subslide, and defaults to zero.
`duration:` sets how long the operation takes, and defaults to `auto`,
which stands for the `primitive-duration` of the deck.
A duration of zero makes the operation jump to its new state.

```typst
animation: {
  import anim: *
  sub(
    reveal("first"),
    reveal("second", delay: 0.2),
    reveal("third", delay: 0.4, duration: 1.5),
  )
}
```

All delays of a subslide are measured from the same moment, which is when the subslide is
triggered.
The runtime passes each delay to the browser as the delay of an animation,
and it starts no separate timer.
A subslide ends when its last operation ends.

A backward step plays this schedule **mirrored** in time.
In the example above, the three lines leave in the order `third`, `second`, `first`,
which is the reverse of the order in which the audience saw them arrive.
Every operation keeps its duration, and only its start time changes.
The operation that ended last in the forward step starts first in the backward step.

Changing [`primitive-duration`](presenting.md#motion) on the deck changes the duration of every
primitive that leaves `duration:` at `auto`.
A primitive that states a duration keeps it.
This also holds for a `primitive-duration` of zero.
The primitives that state a duration then still animate, and all other primitives jump.

**A duration may run past the subslide it is in.**
The next subslide may be triggered while an operation is still running,
and the runtime does not cut that operation short.
Instead, the runtime animates the element from wherever the running operation has brought it
to its state in the next subslide.
