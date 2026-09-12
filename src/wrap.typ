// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// What container a tag site becomes.
//
// A tag has to wrap its body, because only a labelled `box` or `block` becomes a
// `<g data-typst-label>` in the SVG output, and that group is what the browser addresses.
// The wrapper is decided from the body alone and never from the timeline,
// so that adding an animation step cannot reflow a paragraph,
// and so that the four outputs and all of a slide's states lay out the same.
//
// The axis that decides the wrapper is not inline versus block but hugging versus filling.
// A `box` and a `block` render identically for content that already sits between paragraph
// breaks, while a wrapper at `width: auto` left-aligns whatever the container was centring,
// so the two candidates are `box` and `block(width: 100%)`.
// See *Findings* in the design document.

// The wrapper that fills its container, which is what keeps centred content centred.
#let filling = block.with(width: 100%)

// A neighbour with no size of its own, for the measurement below.
#let nothing = box(width: 0pt, height: 0pt)

// Look through the `styled` elements a `set` rule or a `text(..)` call wraps content in.
#let peel(value) = {
  while type(value) == content and repr(value.func()) == "styled" {
    value = value.child
  }
  value
}

// Whether content pushes a neighbour onto a line of its own.
//
// This is the decision procedure for `wrap: auto`, and it is a measurement rather than an
// inspection of element kinds, because a `context` block reports nothing about what it
// will produce and `measure` lays it out.
// Over the constructs a slide is likely to hold, the separation is exactly zero for every
// inline body and at least twelve points for every block-level one,
// so the comparison needs no tolerance.
// It needs no available width either:
// an unbounded `measure` resolves a `100%` width to zero rather than to infinity.
//
// Must be called in a context.
#let breaks-the-line(body) = {
  measure([#nothing#body#nothing]).height > measure(body).height
}

// Whether content is itself several paragraphs.
//
// This is the blind spot of the measurement: the neighbours merge into the first and the
// last paragraph instead of being pushed off, so such a body measures as inline.
// Its own children say what the measurement cannot.
#let several-paragraphs(body) = {
  let inner = peel(body)
  (
    repr(inner.func()) == "sequence"
      and inner.children.any(child => child.func() == parbreak)
  )
}

// The wrapper of one tag site, as a function from the inner content to the inner slot.
//
// `none` is the answer for a tag site that becomes no container at all, which is the only
// form a tag can take around something that is not content, such as a stream of raw cetz
// draw commands.
//
// Must be called in a context, because `auto` measures.
#let choose-wrapper(name, body, wrap) = {
  if wrap == none {
    none
  } else if wrap == box {
    box
  } else if wrap == block {
    filling
  } else if type(wrap) == function {
    wrap
  } else if wrap == auto {
    if breaks-the-line(body) or several-paragraphs(body) { filling } else {
      box
    }
  } else {
    panic(
      "the wrap argument of the tag "
        + name
        + " takes auto, box, block, none or a function, got "
        + repr(wrap),
    )
  }
}

// The two nested slots of a tag site, with the label on the outer one.
//
// Continuous state and boundary state each get a slot of their own, because CSS gives an
// element one `translate` and one `scale` and the two classes would clobber each other.
// The labelled outer group is the boundary slot, since a boundary effect is measured in
// the frame's own coordinates and has to sit above the continuous transforms.
//
// The kind of the outer slot follows the inner one, which is how a `wrap` function that
// carries ink of its own keeps the outer wrapper from changing the layout it chose.
#let slots(name, wrapper, payload) = {
  let inner = wrapper(payload)
  let kind = peel(inner).func()
  let outer = if kind == box {
    box
  } else if kind == block {
    filling
  } else {
    panic(
      "the wrap function of the tag "
        + name
        + " produced a "
        + repr(kind)
        + "; a tag site has to be a box or a block, "
        + "because nothing else becomes an addressable group in the output",
    )
  }
  [#outer(inner)#label(name)]
}
