// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The timeline vocabulary, meant to be star-imported inside the `animation` argument
// of a slide, where shadowing the built-in `hide`, `move` and `scale` is harmless.
//
// Every primitive returns a plain description and performs no action itself.
// `sub` groups the operations that happen together in one subslide step,
// and validates them, which is what closes the footgun of the star import:
// `import ..: *` falls through to the standard library for every name this module does
// not define, so `rotate("b", 45deg)` would quietly call `std.rotate` and return content.
//
// Panning arrives in a later version, and so do the structural primitives.
// They are named here and panic when used,
// because a timeline the resolver silently ignores is worse than one that does not compile.

// The operations that change only how already-rendered content is displayed.
#let continuous-kinds = ("reveal", "hide", "move", "scale")

// Every kind of operation a step may hold.
#let op-kinds = continuous-kinds

// Say what a value is, in a message a reader can act on.
//
// `repr` of a paragraph of content is the whole paragraph, which buries the message it
// is part of, and the type alone is what the footgun is about.
#let describe(value) = (
  if type(value) == content { "content" } else {
    str(type(value)) + " " + repr(value)
  }
)

// Check that a tag name is one.
#let check-name(kind, name) = {
  assert(
    type(name) == str,
    message: kind
      + " takes the name of a tag as a string, got "
      + describe(name),
  )
  name
}

// Check that an offset is a length, and not a ratio of something it cannot know.
#let check-length(kind, axis, value) = {
  assert(
    type(value) == length,
    message: kind + " takes " + axis + " as a length, got " + describe(value),
  )
  value
}

// A scale factor as a plain number, whether it was written as a number or as a ratio.
//
// Factors multiply along the timeline, so one form has to win, and a number is the form
// that survives that multiplication without turning into a ratio of a ratio.
#let check-factor(value) = {
  if type(value) == ratio {
    value / 100%
  } else if type(value) in (int, float) {
    float(value)
  } else {
    panic("scale takes a factor as a number or a ratio, got " + describe(value))
  }
}

// Continuous primitives: they change how already-rendered content is displayed.

#let reveal(name) = (kind: "reveal", name: check-name("reveal", name))

#let hide(name) = (kind: "hide", name: check-name("hide", name))

#let move(name, x: 0pt, y: 0pt) = (
  kind: "move",
  name: check-name("move", name),
  x: check-length("move", "x", x),
  y: check-length("move", "y", y),
)

#let scale(name, factor) = (
  kind: "scale",
  name: check-name("scale", name),
  factor: check-factor(factor),
)

// The slide primitive, which addresses the viewport rather than a tag.

#let pan(x: 0pt, y: 0pt, relto: none) = panic(
  "pan is not implemented yet; it arrives with panning",
)

// Structural primitives: they change what typst has to lay out, and so start a new epoch.

#let replace(name, body) = panic(
  "replace is not implemented yet; it arrives with the structural primitives",
)

#let remove(name) = panic(
  "remove is not implemented yet; it arrives with the structural primitives",
)

#let apply(name, ..fns) = panic(
  "apply is not implemented yet; it arrives with the structural primitives",
)

#let reset(name) = panic(
  "reset is not implemented yet; it arrives with the structural primitives",
)

// Check that a value is an operation of one of the primitives above.
//
// This is the footgun, and the message has to name it:
// the failure a star import produces is a value that looks like nothing in particular,
// several lines away from the call that made it.
#let check-op(value, position) = {
  let ok = (
    type(value) == dictionary and value.at("kind", default: none) in op-kinds
  )
  if not ok {
    panic(
      "argument "
        + str(position)
        + " of sub is not an animo operation, but "
        + describe(value)
        + "; `import anim: *` leaves every name animo does not define bound to the "
        + "standard library, so a primitive that does not exist, such as `rotate`, "
        + "quietly returns content instead of an operation",
    )
  }
  value
}

// `sub(..ops)` groups the operations that happen together in one subslide step.
//
// It returns a one-element array, never a bare dictionary:
// a code block joins arrays and *merges* dictionaries,
// so a timeline of bare dictionaries would silently collapse into one step.
//
// `handout: auto` asks for a handout page at the final state of the slide and at no other,
// which is the page the handout shows anyway.
// `true` adds a page that the handout would otherwise lose, and `false` takes one away.
#let sub(handout: auto, ..ops) = {
  assert(
    ops.named().len() == 0,
    message: "sub takes no named argument besides handout, got "
      + repr(ops.named().keys()),
  )
  assert(
    handout == auto or type(handout) == bool,
    message: "the handout argument of sub takes auto, true or false, got "
      + describe(handout),
  )
  (
    (
      kind: "sub",
      handout: handout,
      ops: ops.pos().enumerate(start: 1).map(((i, op)) => check-op(op, i)),
    ),
  )
}

// Check that a timeline is one, and hand back its steps.
//
// The `animation` argument is a code block of `sub(..)` calls, which joins into an array.
// Everything else is a mistake with a recognisable shape, so each gets its own message.
#let check-timeline(animation) = {
  if animation == none {
    // A code block that joined nothing, which is a timeline with no steps.
    ()
  } else if (
    type(animation) == dictionary
      and animation.at("kind", default: none) == "sub"
  ) {
    panic(
      "the animation argument received the inside of a sub(..) call; "
        + "sub returns its step as a one-element array, so pass the call itself",
    )
  } else if type(animation) != array {
    panic(
      "the animation argument takes a code block of sub(..) calls, got "
        + describe(animation)
        + "; a content block is the slide body, not its timeline",
    )
  } else {
    for (position, step) in animation.enumerate(start: 1) {
      assert(
        type(step) == dictionary and step.at("kind", default: none) == "sub",
        message: "step "
          + str(position)
          + " of the animation argument is not a sub(..) call, but "
          + describe(step),
      )
    }
    animation
  }
}
