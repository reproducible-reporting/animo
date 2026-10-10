---
description: >-
  The morph transition of the structural primitives, which moves what two versions of a region
  share and fades only what differs: what it matches, how it is timed, and its limitations.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Morphs

The example deck for this page is
[`morph.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/morph.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/morph.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/morph-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/morph-handouts.pdf)).
It shows a paragraph that reflows, a paragraph whose shapes move with its words,
a crossfade and a morph of the same change side by side, an equation that grows,
a box that grows around its words, shapes that change their outline,
and a clipped box that moves as one piece because a tag surrounds it.

A structural primitive changes the content of a region,
so the region has an old version and a new version.
With `transition: morph()`, the content that both versions share moves
from its old place to its new place.
Only the content that differs between the two versions fades out or in:

```typst
#slide(animation: {
  import anim: *
  sub(replace("aside", transition: morph())[and a clause inserted near the start])
})[
  #region[
    The quick brown fox #tag("aside", wrap: none)[] jumps over the lazy dog,
    and every word after the insertion moves to its new place.
  ]
]
```

## What a Morph Matches

The morph compares what the two versions of the region show,
and pairs each element of the old version with an equal element of the new version.
Each pair moves from the old place to the new place.
The rules below decide which elements the morph pairs:

- **Letters** are matched by their shape, in reading order,
  so a paragraph that reflows needs no tags.
  A letter that changes color moves and changes color on the way.
  A letter that changes size or weight gets a different shape.
  The old letter then fades out at its old place, and the new letter fades in at its new place.
- **Shapes and images** are matched by their geometry.
  Letters, shapes and images are matched together in one sequence, in reading order,
  so a box beside a word moves with the word.
  A rectangle, a circle, a line, a fraction bar or a mark of a plot is matched
  when its outline and its stroke width are the same in both versions.
  An image is matched when it is the same image at the same size.
  A shape that changes color moves and changes color on the way.
- **A shape that changes size** is resized on the way when it keeps the same kind of outline.
  For example, the bar of a fraction widens when its numerator grows, a box grows around its
  words, and a circle becomes an ellipse.
  Two shapes have the same kind of outline when typst draws both with the same commands.
  This holds for two rectangles, two rectangles with rounded corners, two ellipses or two lines.
  The two shapes also need the same stroke, apart from its width,
  and the morph changes the width of the stroke on the way.
  The corners of a rounded rectangle keep their shape,
  while their radius changes to the new radius along with the size.
  The morph resizes a shape only into a shape that sits between the same two matched neighbours,
  such as the letters on either side of it, and inside the same tags.
  For this reason, a box removed in one place is not resized into a box added in another place.
  A tag around one of two shapes prevents the morph from pairing these two shapes.
- **A shape that changes its kind of outline** turns into the new shape on the way
  when three conditions hold:
  a tag holds the shape, the primitive changes that tag,
  and in each version the tag holds exactly one shape that none of the rules above matches.
  On `#tag("s")[#square(size: 2cm)]`, the primitive
  `replace("s", transition: morph())[#circle(radius: 1cm)]` turns the square into the circle.
  In the same way, a star becomes a pentagon, a rectangle gets rounded corners,
  an arrow folds onto a line, and the hole of a ring closes.
  When a filled shape turns into a shape with only a stroke,
  the outline changes while the fill fades out and the stroke fades in.
  When the tag holds two such shapes in either version, the morph cannot tell which shape
  becomes which, so these shapes fade out and in.
- **A tag** moves as one piece, so a tag around a figure or a drawing moves it as a whole.
  When one name tags several sites, the morph pairs the sites in the order they appear:
  the first site in the old version with the first site in the new version, and so on.
  The tag that the primitive changes does not move as one piece, and neither does a tag
  around it, because the content of these tags differs between the two versions.
  The morph matches the content inside these tags instead.
- **Everything else** fades out at its old place and fades in at its new place,
  as in a crossfade.
  This includes an image that changes size.
  It also includes a shape that changes its kind of outline
  when no tag holds that shape alone, as the previous item requires.
  For example, the rectangles of a paragraph that all get rounded corners fade out and in.

A box with `clip: true` hides the content outside its edges.
The morph moves the content inside such a box, and leaves the edges of the box where typst
laid them out in each version.
If the box moved, the moving content would be cut off at edges that are in the wrong place.
The morph therefore matches the content of a clipped box only when the box sits at the same place
in both versions, and the content fades out and in when the box moves.
A tag around the clipped box moves the box and its content as one piece.

A plot draws all of its marks as equal shapes,
and the morph pairs equal shapes in the order the plot draws them.
When a point is added at the start of the data, the first old mark is paired with the first new
mark, which belongs to the added point.
Each mark therefore moves to the place of the next point, even though the old points did not
change.

## Timing of a Morph

The morph takes the `delay:` and `duration:` of the primitive, as the crossfade does.
A `duration:` of zero is a hard cut.
When the presenter steps backwards, the morph plays in reverse.
A deep link shows the state of the slide at once, without motion.

One subslide may contain several primitives that change the same region.
These primitives have to name the same transition, so `morph()` is written on each of them:

```typst
sub(
  replace("aside", transition: morph())[and a clause],
  apply("word", text.with(fill: red), transition: morph()),
)
```

## Morph Limitations

The morph moves content and never scales it.
When the morph resizes a shape, it redraws the outline at the size of each moment,
and the width of the stroke changes from the old width to the new width.
Scaling the shape would instead make its stroke thicker or thinner along with the size.

Webkit, the browser engine of Safari, does not animate the outline of a shape.
In webkit, the morph therefore fades out and in every shape that changes its size or its kind
of outline, as a crossfade does, and moves everything else.

Typst writes a letter as a reference to a glyph of the font, and not as a shape,
so the morph never turns one letter into another letter.
A letter drawn as a shape, with typst's `curve` or with cetz,
turns into another shape like any other shape.

When the letters of the two versions of a region differ in more than 400 places,
the morph matches none of these letters and fades all of them out and in,
because the matching would take too long.
A morph of a few hundred letters adds a few tens of milliseconds to the start of a step.
See [Performance](performance.md#what-a-morph-costs) for the numbers.

Only a structural primitive accepts `morph()`.
The `init` call and the `transition:` argument of the deck refuse `morph()`,
because those two set the transition between two slides,
and a morph moves content inside one region of one slide.

The static output types show one state per page, with nothing in between,
so a morph has no effect there.
