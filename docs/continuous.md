---
description: >-
  The timeline of a slide: subslides, the four continuous primitives,
  the four timing keywords, and what the handout keeps.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Continuous Animations

The example deck for this page is
[`motion.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/motion.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/motion.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/motion-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/motion-handouts.pdf)).
It illustrates moving, scaling and the four timing keywords.

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

The timeline is read **before the body is laid out**, which is why it is an argument
rather than a marker at the end of the body.

## Subslides

`sub(..ops)` groups the operations that happen together when the presenter proceeds to the next subslide,
and the animation argument is a code block of such calls, which joins them into a list:

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
State 0 is the slide as the body declares it,
and state *i* is state *i-1* with the operations of the *i*-th `sub` applied.
The static presentation renders one page per state;
the HTML deck steps through the same states in a browser.

Every argument of `sub` that is not [`wait:`](#timing), [`hold:`](#timing) or
[`handout:`](#selecting-states-for-handouts) is an operation, and `sub` checks that it is one.
A star import from `anim` leaves every name the module does not define bound to the standard library,
so a misspelled or unsupported primitive resolves to a standard library function.
Animo defines no `rotate`, for instance, so `rotate("b", 45deg)` calls typst's `rotate`
and returns content, which without the check would surface much later as a confusing error.
`sub` names the offending argument where it is passed.

## The Block-Scoped Import

The primitives are imported inside the animation block, in the style of cetz.
Three of them, `hide`, `move` and `scale`, share a name with a typst built-in,
and the import is scoped to the block,
so those names mean Animo's primitives in the timeline and typst's own elements everywhere
else, the slide body included.

`#tag`, `#region` and `#slide` are body-level names and are imported at the top as usual.
A star import of the package brings in `anim` as a name,
so `anim.reveal("a")` works with no inner import at all.

## Continuous Animation Primitives

These change only how already-rendered content is *displayed*,
so they are smooth in the browser and add no renderings in the paged outputs.

| Primitive                              | Meaning                                       |
| -------------------------------------- | --------------------------------------------- |
| `reveal(name)`                         | make the element visible                      |
| `hide(name)`                           | make the element invisible, keeping its space |
| `move(name, x:, y:, dx:, dy:, relto:)` | translate the element                         |
| `scale(name, f:, fx:, fy:)`            | scale the element about its own centre        |

The element keeps the space it had in every case:
a display state never reflows the slide.

Each primitive modifies the state of its tagged subject:
`reveal` and `hide` change visibility,
`move` keeps a position that `x` and `y` overwrite and `dx` and `dy` add to,
and `scale` sets the factors of the axes the call names.
A tag the timeline never reveals or hides stays visible.
A tag whose first display operation is `reveal` starts hidden instead
(see [Tags](tags.md#initial-state-of-tagged-content)).

Starting hidden and being hidden by `hide` are the same state,
reached differently in the two targets.
On paper an invisible element is typst's own `hide()`, laid out and not drawn.
The browser needs ink it can bring back, so the HTML output renders the element normally
and the runtime hides it with `opacity: 0`.
The text of a hidden element is therefore in the HTML file,
where a reader who searches the page can find it.
Do not use a hidden element for contents that should be kept secret without any trace in the output.

### Where `move` Puts Things

`move` says where an element goes in two ways, with x and y directions treated separately:

| Argument   | The element goes                                 |
| ---------- | ------------------------------------------------ |
| `x`, `y`   | to that position (relative to the anchor)        |
| `dx`, `dy` | displacement relative to the current position    |
| `relto`    | names the tag that is the anchor for `x` and `y` |

The **anchor** is the canvas origin, or with `relto` the tag of that name,
and what lands on it is the moved element's own anchor,
which is the **top-left corner of its wrapper** as the body laid it out.

```typst
animation: {
  import anim: *
  sub(move("label", relto: "node"))   // put the label on the node
  sub(move("label", dy: -5mm))        // and lift it a little from there
  sub(move("label", x: 1cm, y: 1cm))  // or put it in the corner of the canvas
}
```

All four offsets have a unit of length.
`x` together with `dx` on one axis is refused, because the two are measured from different
places, and so is a `move()` that says nothing at all.
Idem for `y` and `dy`.

Three consequences follow from the anchor being the corner the *body* gave the tag.

- **It excludes the tag's own display state**, so it means the same in every state.
  An absolute move is idempotent, and `move("b", relto: "a")` is unaffected by whatever
  moved `a`.
- **A name with several sites moves as one.**
  The first site lands on the target and every other site takes the same translation.
- **An anchor is a layout corner and a scale is about a centre**,
  so an element that is both moved and scaled lands its *unscaled* corner on the target.
  The exact form there is a `dx`/`dy` shift.

See [What `relto` Reads](viewport.md#what-relto-reads) for more details.

### What `scale` Sets

`scale` takes `f` for one factor on both axes and `fx`/`fy` for one axis each,
and `f` cannot be combined with either.
Each is a number or a ratio, so `f: 2` and `f: 200%` are the same.

**A factor is set, not multiplied into what is already there.**
`scale("a", f: 2)` in one subslide and again in the next leaves `a` at twice its size, not four
times, and `scale("a", f: 1)` restores it whatever came before.
An axis the call does not mention keeps the factor it had.

## Timing

Four arguments decide *when* and *how long* rather than *what*.
All of them are plain numbers of **seconds**, because typst has no time literal of its own,
e.g. `2s` does not parse.

| Argument    | Says                                        | Written on      |
| ----------- | ------------------------------------------- | --------------- |
| `wait:`     | when a subslide comes up                    | `sub`, `#slide` |
| `hold:`     | how long a subslide stays up                | `sub`, `#slide` |
| `delay:`    | when one operation inside a subslide starts | any primitive   |
| `duration:` | how long that operation then takes          | any primitive   |

All four are HTML only.
The paged outputs are one page per state with nothing between them,
so there is no clock for any of them to be measured on.

### `wait:` and `hold:`

Both arguments can be used to start the next animation without waiting for the presenter click.
They control the gap between two subslides, but do so in slightly different ways.
`wait:` is the delay before the subslide it is specified in;
`hold:` is the delay before the next subslide.
Both are written on a `sub`, and on `#slide` for the initial state, which has no `sub`:

```typst
#slide(
  wait: 2,                     // entered two seconds after the slide before it
  animation: {
    import anim: *
    sub(reveal("a"))           // waits for the presenter
    sub(wait: 3, reveal("b"))  // comes up three seconds later
    sub(hold: 4, reveal("c"))  // waits for presenter and stays up for four seconds
  },
)[...]
```

The default of both is `none`, in which case the presenter must click to proceed.
A deck in which every gap states one of the two plays itself from the first state to the
last.

Both are measured from the moment the subslide they are timed against was **triggered**,
not from the moment its motion finished.
A `hold:` of zero therefore starts the next subslide at the same time as the one it is
written on, so a build that runs over two slides keeps its motion and the slide transition
together.

**One gap takes one number.**
A gap that both its neighbours time is refused, and the message names them both,
across a slide boundary as well.
Which of the two to use depends on which subslide the statement is about:
`wait: 0` on a slide says that this slide needs no click,
and `hold: 0` on the subslide before says that the deck does not stop there.

Timing does not take the deck away from the presenter.
See [Presenting](presenting.md#a-deck-that-plays-itself)
for how a presenter can control animations that start automatically.

### `delay:` and `duration:`

Every primitive takes both.
`delay:` defaults to zero and when set to a positive value, it delays that one operation within its subslide.
`duration:` defaults to `auto`, which is the deck's own `primitive-duration`.

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

The subslide still has exactly **one clock**.
A delay becomes the browser animation's own delay rather than a timer of its own,
so every operation of the subslide is measured from the same instant,
and a subslide ends when the last of its operations does.

A backward step plays that schedule **mirrored**:
the three lines above leave in the order `third`, `second`, `first`,
which is the order the audience saw them arrive, backwards.
Every operation keeps its own duration; only the moment it starts at is turned around.

The number `auto` stands for is the deck's [`primitive-duration`](presenting.md#motion),
so a deck that sets the global `primitive-duration` reaches every primitive with the default
and leaves alone the ones that asked for something else.

A duration **may run past the subslide it is in**.
An operation still running when the next subslide is triggered is overtaken rather than cut
short, and an interrupted subslide continues from where it was paused.

## Selecting States for Handouts

The handout shows one page per slide, and `handout:` says which state that is.

- `handout: auto`, the default, asks for a page at the **final state** of the slide and at
  no other, which is the page the handout shows anyway.
- `handout: true` adds a page at that state.
- `handout: false` takes one away, including the final state.

Every state carries the flag.
The initial state has no `sub` of its own, so its flag is written on the slide:

```typst
#slide(handout: true, animation: {
  import anim: *
  sub(reset("gap"))
})[
  This sentence reserves room for a #tag("gap")[word] the `reset` brings in.
]
```

The reason to state any of this is that an animation can destroy content, which
[Structural Animations](structural.md#selecting-states-for-handouts) picks up.

A deck in which every state declines its page would leave the handout with no page at all.
Animo refuses that deck rather than letting typst emit a blank page of its own.
