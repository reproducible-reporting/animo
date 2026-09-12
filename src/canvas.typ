// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The automatic canvas: how large the rectangle is that a slide body is laid out on.
//
// Typst's own `auto` sizing cannot answer this, because `#place` is out of flow and
// contributes nothing to it, and position introspection is dead in the HTML target.
// What is available in both targets is a `show place:` rule over the body.
// It fires for every placement and can read `dx`, `dy`, `alignment` and a measurable `body`,
// so the union is computed from content alone and comes out the same in HTML and on paper.
//
// The rule cannot return a value, so each placement is recorded as a `metadata` element
// carrying a label, and the union is taken from `query`.
// That makes the canvas size depend on the layout of the very block it sizes,
// which typst resolves by iterating the document until introspection converges.
// The iteration terminates because the body is always laid out at the same inner size,
// whatever the canvas around it turns out to be.

// The label every recorded placement carries.
// One label serves the whole document and the slide index in the value does the scoping,
// because a tag name means nothing outside its own slide.
#let place-label = label("animo-place")

// The label a slide's computed canvas carries.
// The canvas is a property of the slide that panning and the tests both have to read,
// and introspection is the only channel that reaches both targets.
#let canvas-label = label("animo-canvas")

// Record every placement of a slide body, so that the canvas can be sized from it.
//
// The recording has to be invisible to typst's own layout, which rules out `layout(size => ..)`
// inside the rule: it is block-level and breaks the paragraph the placement sits in.
// A `context` block holding nothing but `metadata` is inline and changes no measurement.
#let record-placements(index, body) = {
  show place: it => {
    context [#metadata((
        slide: index,
        dx: it.dx,
        dy: it.dy,
        alignment: it.alignment,
        size: measure(it.body),
      ))#place-label]
    it
  }
  body
}

// Resolve a `relative` offset against the length its ratio is a fraction of.
#let resolve(offset, full) = offset.length + offset.ratio * full

// The horizontal component of an alignment, or `none` when it has none.
#let x-of(value) = if type(value) == alignment { value.x }

// The vertical component of an alignment, or `none` when it has none.
#let y-of(value) = if type(value) == alignment { value.y }

// How far right a recorded placement reaches, measured from the origin of `container`.
#let x-extent(placement, container) = {
  let dx = resolve(placement.dx, container.width)
  let width = placement.size.width
  let align = x-of(placement.alignment)
  if align == center {
    (container.width + width) / 2 + dx
  } else if align == right or align == end {
    container.width + dx
  } else {
    dx + width
  }
}

// How far down a recorded placement reaches, measured from the origin of `container`.
#let y-extent(placement, container) = {
  let dy = resolve(placement.dy, container.height)
  let height = placement.size.height
  let align = y-of(placement.alignment)
  if align == horizon {
    (container.height + height) / 2 + dy
  } else if align == bottom {
    container.height + dy
  } else {
    dy + height
  }
}

// The canvas of one slide, as a dictionary with `width` and `height`.
//
// The union covers the body's in-flow extent and every placement animo saw,
// each offset by the deck's margin, and is clamped to at least the viewport.
// It is a lower bound on the ink of the slide rather than an exact bounding box:
// a placement nested inside another container reports offsets against *that* container,
// which the rule cannot tell apart from the slide body.
// Since a container never sits at a negative coordinate on the canvas,
// such a placement is counted short rather than long, and `canvas:` is the override.
//
// Must be called in a context, and only after `record` has run over the same body,
// which is what puts the placements in reach of `query`.
#let auto-extent(index, body, viewport, margin) = {
  let inner = (
    width: viewport.width - 2 * margin,
    height: viewport.height - 2 * margin,
  )
  let flow = measure(body, width: inner.width)
  let placements = query(place-label)
    .map(it => it.value)
    .filter(it => it.slide == index)
  (
    width: calc.max(
      viewport.width,
      margin + flow.width,
      ..placements.map(it => margin + x-extent(it, inner)),
    ),
    height: calc.max(
      viewport.height,
      margin + flow.height,
      ..placements.map(it => margin + y-extent(it, inner)),
    ),
  )
}

// Check the `canvas` argument of a slide and hand back its two lengths.
#let explicit-extent(value) = {
  assert(
    type(value) == dictionary and value.keys().sorted() == ("height", "width"),
    message: "canvas must be `auto` or a dictionary with `width` and `height`, got "
      + repr(value),
  )
  (width: value.width, height: value.height)
}
