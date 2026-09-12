// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The plan of a slide: what its timeline resolves to, and how that result reaches its tags.
//
// A slide with S `sub` calls has S+1 states.
// State 0 is the body as declared, state i is state i-1 with the i-th step applied,
// and continuous operations accumulate: `move` adds, `scale` multiplies,
// `reveal` and `hide` overwrite.
//
// The result is *provided* to the body, not published to a state.
// A state cannot carry a value that has to vary inside `measure`,
// because `state.get()` there resolves at the location of the enclosing context block,
// and varying a value inside `measure` is exactly what a region has to do
// to size its footprint over its epochs.
// A marker element plus a show rule does reach inside `measure`, providers nest with the
// innermost winning, and the marker's own label does not reach the output.
// See *Findings* in the design document.

#import "anim.typ": check-timeline, continuous-kinds

// The display state of a tag that nothing has addressed yet.
//
// `hidden: none` means that no `reveal` and no `hide` has happened,
// which is what lets the tag fall back to its own `hidden:` argument.
// The resolver never sees that argument: it is written in the body, not in the timeline.
#let identity = (hidden: none, x: 0pt, y: 0pt, scale: 1.0)

// The display state of one tag after one operation.
#let apply-op(display, op) = {
  let current = display.at(op.name, default: identity)
  display.insert(
    op.name,
    if op.kind == "reveal" {
      (..current, hidden: false)
    } else if op.kind == "hide" {
      (..current, hidden: true)
    } else if op.kind == "move" {
      (..current, x: current.x + op.x, y: current.y + op.y)
    } else if op.kind == "scale" {
      (..current, scale: current.scale * op.factor)
    } else {
      panic("the resolver does not know the operation " + repr(op.kind))
    },
  )
  display
}

// Resolve a timeline into the per-state display state of a slide.
//
// The `epoch` fields are placeholders, since a slide has exactly one epoch as long as
// there are no structural primitives.
// They are in the shape from the start, so that the phase which adds epochs extends this
// resolver rather than replacing it.
#let resolve(animation) = {
  let steps = check-timeline(animation)
  let display = (:)
  let states = ((display: display, epoch: 0, handout: auto),)
  for step in steps {
    for op in step.ops {
      display = apply-op(display, op)
    }
    states.push((display: display, epoch: 0, handout: step.handout))
  }
  // `handout: auto` asks for the page the handout shows anyway, which is the final state,
  // so a timeline that says nothing about the handout gets one page per slide.
  // Stating `true` or `false` overrides it in either direction,
  // including a final state the author would rather not hand out.
  let last = states.len() - 1
  (
    states: states
      .enumerate()
      .map(((index, state)) => (
        ..state,
        handout: if state.handout == auto { index == last } else {
          state.handout
        },
      )),
    epochs: ((:),),
  )
}

// The tag names that the timeline addresses with a continuous primitive, anywhere.
//
// A tag has to know this in every state, and not only in the state that moves it,
// because a tag site that cannot be animated at all has to say so at the first
// opportunity rather than in the state where the browser would silently do nothing.
#let continuous-names(animation) = {
  let names = ()
  for step in check-timeline(animation) {
    for op in step.ops {
      if op.kind in continuous-kinds and op.name not in names {
        names.push(op.name)
      }
    }
  }
  names.sorted()
}

// What a tag site is handed: everything about the rendering it is part of.
//
// A dictionary rather than the display state alone, because later phases add the content
// state and a real epoch number to the same value.
#let view-of(plan, names, index) = (
  state: index,
  epoch: plan.states.at(index).epoch,
  display: plan.states.at(index).display,
  continuous: names,
)

// The view of the HTML target, which applies no display state.
//
// `state: none` says "not one of the S+1 states": an HTML frame covers a whole run of
// them, and the browser is what puts a state's display state on the groups.
#let html-view(names) = (state: none, epoch: 0, display: (:), continuous: names)

// The label of the marker a tag emits to ask for the view of its slide.
#let ask-label = label("animo-ask")

// Whether a body is being laid out inside a slide.
//
// This is the one thing about a slide that is published rather than provided, because it
// is the one thing that has to be readable where no provider ran: a marker that nobody
// replaced is indistinguishable from one that was, so a tag outside any slide cannot be
// diagnosed after the fact and is diagnosed at the tag site.
#let inside = state("animo-inside", false)

// Hand `view` to every tag in `body`, and to every tag those tags contain.
#let provide(view, body) = {
  show ask-label: it => (it.value)(view)
  body
}

// Ask the enclosing slide for its view, and render `f` with it.
//
// Must be called in a context, for the diagnosis above.
#let ask(name, f) = {
  assert(
    inside.get(),
    message: "the tag "
      + name
      + " is not inside a #slide, so there is no timeline that could address it",
  )
  [#metadata(f)#ask-label]
}
