---
description: >-
  A slide is a viewport onto a canvas that may be larger than it.
  How `pan` moves the viewport, how large the canvas is,
  and what panning becomes in each output type.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# The Viewport

The example deck for this page is
[`pan.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/pan.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/pan.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/pan-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/pan-handouts.pdf)).
It shows a canvas two screens wide.

A slide has two rectangles.
The **viewport** is what the audience sees: one HTML slide container, one page.
It is the size of the deck, and it clips.
The **canvas** is what the body is laid out on.
It is at least as large as the viewport and may be larger.

Content on the canvas but outside the viewport is **clipped, never carried over** to a next
slide or a next page.
A slide is a fixed rectangle, so there is no next page for it to flow onto.
What brings the rest of the canvas into view is `pan`.

```typst
#slide(
  animation: {
    import anim: *
    sub(pan(relto: "details"))
    sub(pan(dy: 4cm))
  },
)[
  = An overview
  The details are to the right, beyond the edge of the slide.

  #place(dx: 18cm, tag("details")[
    = The details
    #lorem(80)
  ])
]
```

## Panning

`pan` is a special case of a continuous animation primitive.
It addresses no tag, and moves the viewport over the canvas.
Positive values move the viewport right and down, so the content moves left and up.

It says where the viewport goes in two ways, and each axis takes one of them:

| Argument             | The viewport goes                                     |
| -------------------- | ----------------------------------------------------- |
| `x`, `y`             | to that distance from the anchor                      |
| `dx`, `dy`           | that far from wherever it already is                  |
| `relto`              | names the tag that is the anchor                      |
| neither, on one axis | nowhere on that axis, unless `relto` asks for the tag |

[`move`](continuous.md#where-move-puts-things) reads the same table one layer in:
it puts the *element* where `pan` would put the viewport's own corner.

The **anchor** is the canvas origin, or with `relto` the tag of that name,
placed where the body of a fresh slide starts, which is at the deck's margin.
So `pan(relto: "details")` shows the tag the way a new slide would show its first line,
and `pan(x: 0cm, y: 0cm)` goes back to where the slide started.

The two ways combine, one per axis:

```typst
animation: {
  import anim: *
  sub(pan(relto: "details"))           // bring the tag into view
  sub(pan(dy: 4cm))                    // scroll down, and stay on the tag horizontally
  sub(pan(relto: "summary", x: -1cm))  // the next tag, with a centimetre to its left
  sub(pan(x: 0cm, dy: -2cm))           // back to the left edge, and up a little
}
```

`x` and `dx` on the same axis are refused, since they are measured from different places.
Idem for `y` and `dy`.
A pan is state, like everything else on the timeline:
it holds until the next `pan`, and stepping back undoes it.

The viewport is **not clamped** to the canvas.
A pan that reaches past the edge of the canvas shows the slide's background there,
which is also how a slide brings a tag to the middle of the viewport rather than to its
corner.

### What `relto` Reads

The anchor of a tag is the **top-left corner of its wrapper**, as the body laid it out.
The same mechanism serves both `pan` and `move`:

- It is the corner of the box around the tag, not of its ink.
  A tagged phrase is anchored at the top of its line, not at the top of its letters.
- The tag's own `move` and `scale` do not enter it,
  so an anchor means the same in every state.
- Where one name tags several places, the first one in the body is the anchor.

Three things are refused rather than resolved, each because a deck would otherwise get a
subslide that means one thing on paper and another on screen.

- A `relto` that **names no tag of the slide**, since it is almost certainly a misspelt
  name. A tag of that name on another slide does not count.
- A `relto` to a tag with **`wrap: none`**, because such a tag has no box to have a corner.
- An anchor read **inside a tag the timeline moves or scales**.
  A transform around a tag moves the very corner the anchor is,
  so the anchor would stop being the corner the body gave it.
  Read the anchor of the outer tag instead, or take the inner one out of it.
  Nesting itself is fine, and so is a tag inside one that is merely revealed or hidden.

## How Large the Canvas Is

`canvas: auto`, the default, sizes the canvas to the content of a slide whose timeline pans:
the union of the body's in-flow extent and the extent of every `#place`d element,
clamped to at least the viewport.
So a slide that places nothing outside the viewport has a canvas equal to its viewport,
and a slide whose body is simply longer than its viewport gets a taller canvas that `pan`
reaches the rest of.
Nothing has to be placed for that to work.

A slide with no `pan` in its timeline just draws inside the viewport, without any canvas at all, lowering the cost of a slide that does not need to pan.
See [Performance](performance.md) for what that costs when a slide does pan.

Neither the `background:` nor the `overlay:` enters the extent,
whatever either of them holds,
so a full-bleed image in the background cannot make the body pannable by accident.

The union is computed from content alone rather than from positions, which do not exist in
the HTML target, so the canvas comes out the same in the browser and on paper.
It is exact for a placement written directly in the slide body, with a body that has a size
of its own. Everywhere else it is an approximation:

| Written                                    | Counted                                                      |
| ------------------------------------------ | ------------------------------------------------------------ |
| `#place` nested in another container       | from the canvas origin, so short by where the container sits |
| an alignment inside such a container       | against the body, which is wider, so too large               |
| a ratio-sized body, as `rect(width: 100%)` | as nothing at all, wherever it is written                    |

None of the three has to be anticipated.
A canvas that comes out too large has no cost unless something pans onto the empty part of
it, and one that comes out too small becomes apparent the first time a pan goes nowhere.
`canvas: (width: .., height: ..)` states the canvas explicitly and is the escape hatch for
all three. An explicit canvas is still clamped to at least the viewport.

A body that runs off the viewport is laid out in a box as tall as its own flow,
and that box is what a `#place` inside it resolves against.
On such a slide `place(bottom + right)` means the bottom right of the whole flow rather
than of the first screenful, so a mark that belongs on the first screenful needs an
explicit `dy:`.

## What Panning Means in Each Output

| Output type         | A pan is                                                    |
| ------------------- | ----------------------------------------------------------- |
| HTML presentation   | a `translate` of the canvas, animated like every other step |
| Static presentation | a page per state, each showing its own part of the canvas   |
| Static handouts     | the viewport of each state the handout keeps                |

In the browser the pan moves the element holding the whole rendering of the slide,
so everything on the canvas moves together and nothing on it moves relative to anything
else. A pan is a percentage of the canvas, so it stays the same part of the slide at any
window size.

**The handout does not show the canvas.**
A handout page is the viewport of one state.
By default that is the last state of the slide, so a slide that pans away from something
and never comes back leaves it out of the handout.
Keep a view with `handout: true` on the subslide that shows it:

```typst
sub(handout: true, pan(relto: "details"))
```
