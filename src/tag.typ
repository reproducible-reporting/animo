// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// A tag site: content the timeline can address by name.
//
// The same name may be used several times in one slide, and the timeline then addresses
// all of them together, as if they were one element.
// The same name in two slides does not interfere, because a tag reads the view of the
// slide it sits in and nothing else.
//
// A tag emits the same structure in every state and in both targets, and only the
// parameters inside it change: `move`, `scale` and `hide` inside the tag's own wrapper are
// layout-neutral, which is what makes "nothing moves between two states except what the
// timeline moves" an invariant rather than a hope.
// In the HTML target no display state is applied at all;
// the browser runtime of a later version is what puts it on the groups as CSS.

#import "plan.typ": ask, identity
#import "wrap.typ": choose-wrapper, slots

// What a tag site is in one rendering: the state's display state, or its own `hidden:`.
//
// A resolved `hidden` of `none` means that no `reveal` and no `hide` has addressed the
// tag yet, which is when the tag's own argument decides.
#let display-of(name, hidden, view) = {
  if view.state == none {
    // The HTML target, where the display state belongs to the browser.
    (..identity, hidden: false)
  } else {
    let resolved = view.display.at(name, default: identity)
    (
      ..resolved,
      hidden: if resolved.hidden == none { hidden } else { resolved.hidden },
    )
  }
}

// One rendering of a tag site, for the view it is handed.
#let render(name, body, hidden, wrapper, view) = {
  if wrapper == none {
    if name in view.continuous {
      panic(
        "the timeline addresses the tag "
          + name
          + " with a continuous primitive, but its wrap is none, "
          + "so it becomes no group that a browser could move, scale, reveal or hide",
      )
    }
    body
  } else {
    let current = display-of(name, hidden, view)
    slots(
      name,
      wrapper,
      move(
        dx: current.x,
        dy: current.y,
        // `move` is outside `scale` because CSS composes its individual properties
        // in that order, and the paged output has to agree with the browser.
        scale(
          current.scale * 100%,
          reflow: false,
          if current.hidden { hide(body) } else { body },
        ),
      ),
    )
  }
}

#let tag(
  name,
  body,
  hidden: false,
  removed: false,
  wrap: auto,
) = {
  assert(
    type(name) == str,
    message: "a tag takes its name as a string, got " + repr(name),
  )
  assert(
    type(hidden) == bool,
    message: "the hidden argument of the tag " + name + " takes true or false",
  )
  assert(
    type(removed) == bool,
    message: "the removed argument of the tag " + name + " takes true or false",
  )
  if removed {
    panic(
      "the removed argument of the tag "
        + name
        + " is not implemented yet; it arrives with the structural primitives",
    )
  }
  if wrap == none and hidden {
    panic(
      "the tag "
        + name
        + " is hidden and has no wrapper; hiding is a display state, "
        + "and a tag site that becomes no group has nothing to hide in the browser",
    )
  }
  if type(body) != content {
    if wrap != none {
      panic(
        "the body of the tag "
          + name
          + " is not content, but "
          + str(type(body))
          + "; a stream of draw commands is tagged with wrap: none, inside a region",
      )
    }
    // Nothing animo can do here: the value is handed back exactly as it came in, so there
    // is no marker that could reach the view and no diagnosis of a timeline that
    // addresses this tag.
    body
  } else {
    context {
      let wrapper = choose-wrapper(name, body, wrap)
      ask(name, view => render(name, body, hidden, wrapper, view))
    }
  }
}

// A region: an area whose layout may change, with a footprint fixed across epochs.
//
// Placeholder. Footprints, nesting, sizing and clipping arrive with the regions.
#let region(body) = body
