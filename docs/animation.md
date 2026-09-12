---
description: >-
  The timeline of a slide: subslide steps, the four continuous primitives,
  the state model they resolve into, and what the handout keeps.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Animation

The `animation` argument of a slide is its timeline.
It says when and how the [tagged](tags.md) parts of the body appear, move and scale,
while the body says only what is on the slide.

```typst
#import "@preview/animo:0.1.0": *
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)

#slide(
  animation: {
    // The primitives live in the `anim` module and are imported inside this block.
    import anim: *
    sub(reveal("second"))
    sub(move("first", x: 2cm), scale("second", 1.3))
  },
)[
  #tag("first")[This line slides to the right on the last step.]

  #tag("second", hidden: true)[This one starts out invisible.]
]
```

## Why the Timeline Is an Argument

The timeline is read **before the body is laid out**, and that is why it is an argument of
`#slide` rather than a marker at the end of the body.
The body's layout depends on it:
a tag has to know whether it is addressed at all before it can decide what to emit,
and an area whose content changes has to know every state it will take on before it can
reserve room for the largest.

A marker collected at the end of the body would be discovered rather than passed,
which is one introspection pass more and one ordering guarantee less.

## Steps

`sub(..ops)` groups the operations that happen together in one subslide step.
The animation argument is a code block of such calls, which joins them into a list:

```typst
animation: {
  import anim: *
  sub(reveal("a"))
  sub()
  sub(hide("a"), move("b", y: 1cm))
}
```

An empty `sub()` advances one step without changing anything,
which is how an author asks for a click that only paces the talk.

`sub` takes one keyword argument of its own, `handout:`, which the last section is about.
Every other argument is an operation, and `sub` checks that it is one.
That check matters more than it looks:
a star import leaves every name the module does not define bound to the standard library,
so a primitive that does not exist, `rotate("b", 45deg)` for instance,
would quietly call typst's own `rotate` and return content.
`sub` names the offending argument instead.

## The Block-Scoped Import

The primitives are imported **inside** the animation block, in the style of cetz.
Three of them, `hide`, `move` and `scale`, share a name with a typst built-in,
and the import is scoped to the block,
so those names mean animo's primitives in the timeline
and typst's own elements everywhere else, the slide body included.

`#tag`, `#region` and `#slide` are body-level names and are imported at the top as usual.
A star import of the package brings in the `anim` module as a name,
so `anim.reveal("a")` works as well, with no inner import at all.

## The Continuous Primitives

These four change only how already-rendered content is *displayed*,
which is what makes them smooth in the browser and free on paper.

| Primitive             | Meaning                                       |
| --------------------- | --------------------------------------------- |
| `reveal(name)`        | make the element visible                      |
| `hide(name)`          | make the element invisible, keeping its space |
| `move(name, x:, y:)`  | translate the element                         |
| `scale(name, factor)` | scale the element about its own centre        |

`x` and `y` are lengths.
`factor` is a number or a ratio, so `scale("a", 2)` and `scale("a", 200%)` are the same.

The element keeps the space it had in every case:
a display state never reflows the slide, which is what keeps a `move` in flight from
jumping when something else on the slide changes.

## The State Model

A slide with *S* `sub` calls has **S+1 states**, numbered 0 to *S*.
State 0 is the slide exactly as the body declares it,
and state *i* is state *i-1* with the operations of the *i*-th `sub` applied.

Operations accumulate:

- `move` adds to the displacement, so two moves of 1 cm are a move of 2 cm;
- `scale` multiplies the factor, so 2 after 3 is 6;
- `reveal` and `hide` overwrite each other, since visibility is a flag.

A tag the timeline never reveals or hides keeps the visibility its own `hidden:` argument
gave it.

The presentation PDF renders **one page per state**, which is the whole model on paper:
`move` and `scale` become discrete jumps between pages.
The HTML presentation steps through the same states in the browser.

## What the Handout Keeps

The handout shows one page per slide, and `handout:` on a step is what says which one.

- `handout: auto`, the default, asks for a page at the **final state** of the slide
  and at no other, which is the page the handout shows anyway.
- `handout: true` adds a page at that step.
- `handout: false` takes one away, including the final state.

The reason to state it is that a later version can destroy content:
a replacement overwrites what it replaces, and the handout would lose it.
Animo cannot warn about that, because typst offers packages no way to emit a warning,
so it is said here instead.

## What Is Not Here Yet

The HTML output carries the state count and steps through it,
and **applies no display state**:
nothing moves in the browser yet, and a `hidden: true` tag is visible there.
The browser runtime is the next version.
The presentation PDF is the output that shows the state model today.

`pan`, which moves the viewport over the canvas,
and the structural primitives `replace`, `remove`, `apply` and `reset`,
which change what typst has to lay out,
are named in the `anim` module and say so when they are used.
