// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// How a boundary is crossed: the transition functions an author writes, and the checks that
// read their values back where a transition is taken.
//
// A transition says what a crossing looks like and nothing about time.
// The call that causes the change states the time, which is `init` for a slide and the
// structural primitive for a region, so no transition takes a duration.
//
// Each transition is a function rather than a name, so that typst refuses a misspelt
// parameter at the call that wrote it and an editor shows the parameters each one takes.
// The values are checked here rather than only in the runtime, because a value the runtime
// did not recognise would be a boundary that quietly took a default.

#import "site.typ": describe

// A transition as the value its function returns.
//
// A one-element array rather than a bare dictionary, for the reason `sub` gives:
// a code block joins arrays and merges dictionaries, so a transition written at the top of
// a timeline would merge with nothing and fail to join with the `sub` calls beside it.
// `args` holds the parameters as the JSON values the runtime reads.
#let transition-value(name, args) = (
  (kind: "transition", name: name, args: args),
)

// Check a `direction`, which is the direction of travel on a forward step.
#let check-direction(name, value) = {
  assert(
    value in (ltr, rtl, ttb, btt),
    message: name
      + " takes direction as one of ltr, rtl, ttb and btt, got "
      + describe(value),
  )
  repr(value)
}

/// Fade the outgoing content out while the incoming content fades in.
///
/// Usable in `init`, as the `transition:` of a structural primitive and as the
/// `transition:` of the deck.
///
/// -> array
#let crossfade() = transition-value("crossfade", (:))

/// Move the incoming slide in from one edge while it moves the outgoing slide out at the
/// opposite one.
///
/// Usable in `init` and as the `transition:` of the deck.
///
/// - direction (direction): The direction of travel on a forward step, one of `ltr`, `rtl`,
///   `ttb` and `btt`. A backward step travels the other way.
/// -> array
#let push(direction: rtl) = transition-value(
  "push",
  (direction: check-direction("push", direction)),
)

/// Move the incoming slide in from one edge over the outgoing slide, which stays where it is.
///
/// Usable in `init` and as the `transition:` of the deck.
///
/// - direction (direction): The direction of travel on a forward step, one of `ltr`, `rtl`,
///   `ttb` and `btt`. A backward step travels the other way.
/// -> array
#let cover(direction: rtl) = transition-value(
  "cover",
  (direction: check-direction("cover", direction)),
)

/// Uncover the incoming slide behind an edge that travels across the outgoing one.
///
/// Usable in `init` and as the `transition:` of the deck.
///
/// - direction (direction): The direction in which the edge travels on a forward step, one
///   of `ltr`, `rtl`, `ttb` and `btt`. A backward step travels the other way.
/// -> array
#let wipe(direction: ltr) = transition-value(
  "wipe",
  (direction: check-direction("wipe", direction)),
)

// The transitions a region can take across an epoch boundary.
// A slide can take every transition above.
#let region-transitions = ("crossfade",)

// Whether a value is what a transition function returned.
#let is-transition(value) = (
  type(value) == array
    and value.len() == 1
    and type(value.first()) == dictionary
    and value.first().at("kind", default: none) == "transition"
)

// A transition as it is written, for a diagnosis.
#let written(value) = {
  if value == auto { return "auto" }
  let args = value.args.pairs().map(((key, arg)) => key + ": " + arg)
  value.name + "(" + args.join(", ", default: "") + ")"
}

// Check that a value is a transition and give back its record.
//
// `who` names the call that took it, and `where` the argument, in the diagnosis.
#let transition-of(who, where, value) = {
  assert(
    is-transition(value),
    message: who
      + " takes "
      + where
      + " as a transition, such as crossfade() or push(direction: btt), got "
      + describe(value),
  )
  value.first()
}

// Check the transition of a structural primitive, which carries a region across an epoch
// boundary.
//
// `auto` is the crossfade, whatever the deck's `transition:` says, because that argument is
// about slide boundaries.
// It stays `auto` rather than becoming the crossfade, so the plan carries nothing for it.
#let check-region-transition(kind, value) = {
  if value == auto { return auto }
  let record = transition-of(kind, "transition", value)
  assert(
    record.name in region-transitions,
    message: kind
      + " cannot carry a region with "
      + written(record)
      + ", because a region takes "
      + region-transitions.map(name => name + "()").join(", ", last: " or ")
      + " and the other transitions move a whole slide",
  )
  record
}
