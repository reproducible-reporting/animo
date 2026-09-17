---
description: >-
  Every public name of Animo, its signature, its arguments and their defaults,
  with a link to the page of the guide that teaches it.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Reference

The whole public surface of Animo.
The guide explains these names, and this page states their signatures.

```typst
#import "@preview/animo:0.1.0": *
```

A star import brings in the body-level names and the `anim` module as a name.
The timeline vocabulary is imported inside an `animation` block with `import anim: *`,
where shadowing typst's own `hide`, `move` and `scale` is harmless.

| Name                            | Kind               | Written in           |
| ------------------------------- | ------------------ | -------------------- |
| [`animo`](#animo)               | document show rule | the top of the file  |
| [`slide`](#slide)               | element            | the document         |
| [`tag`](#tag)                   | element            | a slide body         |
| [`region`](#region)             | element            | a slide body         |
| [`per-subslide`](#per-subslide) | element            | a body or a layer    |
| [`slide-number`](#slide-number) | context function   | anywhere             |
| [`slide-count`](#slide-count)   | context function   | anywhere             |
| [`anim.sub`](#animsub)          | subslide           | an `animation` block |
| [`anim.reveal`](#animreveal)    | continuous         | a `sub` call         |
| [`anim.hide`](#animhide)        | continuous         | a `sub` call         |
| [`anim.move`](#animmove)        | continuous         | a `sub` call         |
| [`anim.scale`](#animscale)      | continuous         | a `sub` call         |
| [`anim.pan`](#animpan)          | continuous, slide  | a `sub` call         |
| [`anim.replace`](#animreplace)  | structural         | a `sub` call         |
| [`anim.remove`](#animremove)    | structural         | a `sub` call         |
| [`anim.apply`](#animapply)      | structural         | a `sub` call         |
| [`anim.reset`](#animreset)      | structural         | a `sub` call         |

## The Document

### `animo`

```typst
animo(body, width: 16cm, height: 9cm, margin: 1cm,
      primitive-duration: 0.4, transition-duration: 0.4, easing: "ease-in-out")
```

The shape and the tempo of the deck, applied as a document show rule.

| Argument              | Type    | Default         | Meaning                                             |
| --------------------- | ------- | --------------- | --------------------------------------------------- |
| `body`                | content |                 | the document, given by the show rule                |
| `width`               | length  | `16cm`          | the width of a slide, which is the viewport's width |
| `height`              | length  | `9cm`           | the height of a slide                               |
| `margin`              | length  | `1cm`           | the inset of the body inside the viewport           |
| `primitive-duration`  | number  | `0.4`           | seconds one animation primitive takes               |
| `transition-duration` | number  | `0.4`           | seconds a transition into a slide takes             |
| `easing`              | string  | `"ease-in-out"` | the timing function both of them follow             |

```typst
#show: animo.with(width: 16cm, height: 9cm, margin: 1cm)
```

The two durations are HTML only, because the paged outputs put every state on a page of its
own with nothing in between.
A duration of zero means that kind of motion is not animated.

`easing` takes one of five names, which are the CSS timing functions of the same name:

| Name            | Moves                                        |
| --------------- | -------------------------------------------- |
| `"linear"`      | at one speed from beginning to end           |
| `"ease"`        | off quickly, then slows down towards the end |
| `"ease-in"`     | off slowly and arrives at full speed         |
| `"ease-out"`    | off at full speed and slows down to a stop   |
| `"ease-in-out"` | off slowly, speeds up, and slows to a stop   |

Taught in [Slides](slides.md) and [Presenting](presenting.md#motion).

## Slides

### `slide`

```typst
slide(body, animation: (), canvas: auto, background: none, overlay: none,
      transition: auto, wait: none, hold: none, handout: auto, numbered: true)
```

One slide of the deck.

| Argument     | Type                            | Default | Meaning                                                       |
| ------------ | ------------------------------- | ------- | ------------------------------------------------------------- |
| `body`       | content                         |         | what is on the slide                                          |
| `animation`  | block of `sub` calls            | `()`    | the timeline                                                  |
| `canvas`     | `auto` or `(width:, height:)`   | `auto`  | the canvas, sized to the content or stated                    |
| `background` | `none`, colour or content       | `none`  | the layer behind everything                                   |
| `overlay`    | `none`, colour or content       | `none`  | the layer in front of everything                              |
| `transition` | `auto`, `none` or `"crossfade"` | `auto`  | how the boundary into this slide is crossed                   |
| `wait`       | `none` or number                | `none`  | seconds before this slide is entered, or a presenter's click  |
| `hold`       | `none` or number                | `none`  | seconds the initial state stands before the subslide after it |
| `handout`    | `auto`, `true` or `false`       | `auto`  | whether the handout keeps the initial state                   |
| `numbered`   | `bool`                          | `true`  | whether the slide counter counts this slide                   |

```typst
#slide(transition: none, background: navy)[= A slide]
```

Taught in [Slides](slides.md), and `canvas:` in [The Viewport](viewport.md#how-large-the-canvas-is).

### `tag`

```typst
tag(name, body, wrap: auto)
```

Mark a part of a slide so that the timeline can address it by name.

| Argument | Type                                        | Default | Meaning                            |
| -------- | ------------------------------------------- | ------- | ---------------------------------- |
| `name`   | `str`                                       |         | what the timeline refers to        |
| `body`   | content                                     |         | what is marked                     |
| `wrap`   | `auto`, `box`, `block`, `none`, or function | `auto`  | the container the tag site becomes |

A tag's initial state is not an argument.
A tag whose first display operation is `reveal` starts hidden, and one whose first content
operation is `reset` starts removed (see [Tags](tags.md#initial-state-of-tagged-content)).

```typst
#tag("claim")[A claim that a later reveal brings in.]
```

Which primitives reach which kind of tag site:

| Tag site                                    | Structural | Continuous |
| ------------------------------------------- | ---------- | ---------- |
| ordinary content                            | yes        | yes        |
| inside math                                 | yes        | yes        |
| a cetz `content()` element or fletcher node | yes        | yes        |
| content tagged with `wrap: none`            | yes        | refused    |
| raw cetz draw commands                      | refused    | refused    |

The structural primitives are resolved by typst when it renders the slide,
so they work wherever a tag can wrap something at all.
The continuous primitives are resolved by the browser and need a group to address,
which typst emits only for labelled boxes and blocks.
A `pan(relto: ..)` reads a corner of that group, so it is refused on a `wrap: none` tag too.

Taught in [Tags](tags.md).

### `region`

```typst
region(body, width: auto, height: auto, align: top, clip: auto, name: none)
```

An area laid out afresh whenever its content changes, inside a footprint that never changes.

| Argument | Type                    | Default | Meaning                                                    |
| -------- | ----------------------- | ------- | ---------------------------------------------------------- |
| `body`   | content                 |         | what is laid out afresh                                    |
| `width`  | `auto`, length or ratio | `auto`  | the footprint's width, measured when `auto`                |
| `height` | `auto`, length or ratio | `auto`  | the footprint's height, measured when `auto`               |
| `align`  | alignment               | `top`   | where a state smaller than the footprint sits              |
| `clip`   | `auto` or `bool`        | `auto`  | `true` when a size is given, `false` otherwise             |
| `name`   | `none` or `str`         | `none`  | makes the footprint a site the continuous primitives reach |

```typst
#region(height: 3cm)[#tag("claim")[A short claim.]]
```

Taught in [Regions](regions.md).

## Numbering

### `per-subslide`

```typst
per-subslide(f, wrap: auto)
```

Content laid out once per subslide, of which the one belonging to the subslide on screen
is shown.

| Argument | Type                     | Default | Meaning                                     |
| -------- | ------------------------ | ------- | ------------------------------------------- |
| `f`      | function                 |         | called with one dictionary, returns content |
| `wrap`   | `auto`, `box` or `block` | `auto`  | the container the stack becomes             |

The **subslide numbers** the callback receives:

| Key      | Type  | What it is                                                     |
| -------- | ----- | -------------------------------------------------------------- |
| `number` | `int` | the subslide's number within its slide, counting from one      |
| `count`  | `int` | how many subslides that slide has                              |
| `step`   | `int` | the subslide's number within the whole deck, counting from one |
| `steps`  | `int` | how many subslides the whole deck has                          |

`step` and `steps` are named for the presenter's steps, which is how a progress indicator reads
them.
A step is the transition from one subslide to the next, so `steps` counts subslides rather than
transitions.

```typst
#per-subslide(it => if it.count > 1 [(#it.number/#it.count)])
```

Taught in [Numbering](numbering.md).

### `slide-number`

```typst
slide-number()
```

The number of the slide it is called on, or `none` on a slide that `numbered: false`
leaves out. A context function.

```typst
#context slide-number()
```

Taught in [Numbering](numbering.md).

### `slide-count`

```typst
slide-count()
```

How many slides of the deck carry a number. A context function.

```typst
#context [#slide-number() of #slide-count()]
```

Taught in [Numbering](numbering.md).

## Steps

### `anim.sub`

```typst
sub(wait: none, hold: none, handout: auto, ..ops)
```

One subslide: the operations that happen together, and the three things a subslide says
about itself.

| Argument  | Type                      | Default | Meaning                                                         |
| --------- | ------------------------- | ------- | --------------------------------------------------------------- |
| `wait`    | `none` or number          | `none`  | seconds before this subslide is entered, or a presenter's click |
| `hold`    | `none` or number          | `none`  | seconds this subslide stands before the one after it            |
| `handout` | `auto`, `true` or `false` | `auto`  | whether the handout keeps the state this subslide brings about  |
| `..ops`   | operations                |         | what the subslide does                                          |

```typst
sub(wait: 2, handout: true, reveal("a"), move("b", dx: 1cm))
```

Taught in [Continuous Animations](continuous.md).

## Continuous Primitives

They change how already-rendered content is displayed, so they are smooth in the browser
and add no renderings in the paged outputs.
Every one of them takes `delay:` and `duration:`.

| Argument   | Type             | Default | Meaning                                                   |
| ---------- | ---------------- | ------- | --------------------------------------------------------- |
| `delay`    | number           | `0`     | seconds this operation is held back inside its subslide   |
| `duration` | `auto` or number | `auto`  | seconds it then takes, or the deck's `primitive-duration` |

### `anim.reveal`

```typst
reveal(name, delay: 0, duration: auto)
```

Make the tag visible. It keeps the space it had either way.

```typst
sub(reveal("claim"))
```

Taught in [Continuous Animations](continuous.md#continuous-animation-primitives).

### `anim.hide`

```typst
hide(name, delay: 0, duration: auto)
```

Make the tag invisible, keeping its space.

```typst
sub(hide("claim", duration: 1))
```

Taught in [Continuous Animations](continuous.md#continuous-animation-primitives).

### `anim.move`

```typst
move(name, x: none, y: none, dx: none, dy: none, relto: none,
     delay: 0, duration: auto)
```

Translate the tag. Each axis takes an absolute position or a shift, never both.

| Argument   | Type            | Default | Meaning                                            |
| ---------- | --------------- | ------- | -------------------------------------------------- |
| `name`     | `str`           |         | the tag to move                                    |
| `x`, `y`   | length          | `none`  | to that distance from the anchor                   |
| `dx`, `dy` | length          | `none`  | that far from wherever it already is               |
| `relto`    | `none` or `str` | `none`  | the tag that is the anchor, else the canvas origin |

```typst
sub(move("label", relto: "node", dy: -5mm))
```

Taught in [Continuous Animations](continuous.md#where-move-puts-things).

### `anim.scale`

```typst
scale(name, f: none, fx: none, fy: none, delay: 0, duration: auto)
```

Scale the tag about its own centre. The factor is set rather than multiplied into what is
already there, and an axis the call does not mention keeps the factor it had.

| Argument   | Type            | Default | Meaning                           |
| ---------- | --------------- | ------- | --------------------------------- |
| `name`     | `str`           |         | the tag to scale                  |
| `f`        | number or ratio | `none`  | one factor on both axes           |
| `fx`, `fy` | number or ratio | `none`  | one factor per axis, not with `f` |

```typst
sub(scale("figure", f: 1.5))
```

Taught in [Continuous Animations](continuous.md#what-scale-sets).

### `anim.pan`

```typst
pan(x: none, y: none, dx: none, dy: none, relto: none, delay: 0, duration: auto)
```

Move the viewport over the canvas. It addresses the slide rather than a tag, and reads the
same arguments `move` does. Positive values move the viewport right and down, so the
content moves left and up.

```typst
sub(pan(relto: "details"))
```

Taught in [The Viewport](viewport.md#panning).

## Structural Primitives

They change what typst lays out, so each of them starts a new
[epoch](structural.md#epochs). All four take the same `delay:` and `duration:` as the
continuous primitives, where they time the crossfade of the region that changed.

### `anim.replace`

```typst
replace(name, body, delay: 0, duration: auto)
```

Lay out `body` at the tag site instead of what is there, keeping the wrappers `apply` put
around it. The body may be a trailing content block.

```typst
sub(replace("claim")[The second answer.])
```

Taught in [Structural Animations](structural.md#structural-animation-primitives).

### `anim.remove`

```typst
remove(name, delay: 0, duration: auto)
```

Lay out nothing at the tag site, keeping the wrappers.

```typst
sub(remove("caveat"))
```

Taught in [Structural Animations](structural.md#structural-animation-primitives).

### `anim.apply`

```typst
apply(name, delay: 0, duration: auto, ..fns)
```

Wrap what is laid out at the tag site in each function, the last one outermost.
Functions only: a named style property, as in `apply("x", fill: red)`, is refused.

```typst
sub(apply("claim", text.with(fill: red), strong))
```

Taught in [Structural Animations](structural.md#structural-animation-primitives).

### `anim.reset`

```typst
reset(name, delay: 0, duration: auto)
```

Back to the body as written, with every wrapper dropped.

```typst
sub(reset("claim"))
```

Taught in [Structural Animations](structural.md#structural-animation-primitives).

## Command Lines

```bash
typst compile --format html --features html talk.typ talk.html
typst compile --input animo=presentation talk.typ talk-presentation.pdf
typst compile talk.typ talk-handout.pdf
```

Taught in [Output Types](outputs.md).
