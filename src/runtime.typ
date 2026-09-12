// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The seam between the resolved plan and the browser runtime.
//
// In the paged outputs a state is a page, and typst applies its display state itself.
// In the HTML target one frame covers every state of the slide, so the display state has
// to travel to the browser as data: `animo.js` is what puts it on the groups as CSS.
//
// The channel is one `data-animo-plan` attribute per slide, holding compact JSON.
// An attribute rather than a `<script>` element, because the HTML parser escapes and
// unescapes an attribute value, so no tag name can break the page,
// and because a browser's element inspector shows it beside the slide it belongs to.
//
// One thing the resolved plan cannot know travels the other way.
// `hidden:` is written at the tag site and not in the timeline, and typst's `hide()` emits
// nothing to draw, so an initially hidden element is rendered normally in the HTML target
// and hidden by the runtime with `opacity: 0`.
// Each tag site therefore reports its own initial visibility as a `metadata` element,
// which `query` carries back out of the frame, and the slide folds the report into the
// plan it emits, so that the runtime applies what it is given and resolves nothing.

#import "plan.typ": identity

// The label every reported tag site carries.
// One label serves the whole document and the slide index in the value does the scoping,
// exactly as the recorded placements of the canvas do.
#let site-label = label("animo-site")

// Report one tag site, so that the slide can tell the browser what starts out hidden.
//
// A `metadata` element is layout-neutral wherever it sits: measured, a body with a marker
// before, after or inside a block-level tag site measures exactly as the body without one.
#let record-site(view, name, hidden) = [#metadata((
    slide: view.slide,
    name: name,
    hidden: hidden,
  ))#site-label]

// The tags of one slide that start out hidden, as a sorted array of names.
//
// A name is hidden if *any* of its sites is, because in the browser one rule addresses
// every site of a name at once and the two cannot differ there.
// Hiding the lot is the safe half of that: the other resolution would show content the
// author asked to be hidden, and would leak a punchline rather than withhold a caveat.
// It is a divergence from the paged outputs, where each site honours its own argument,
// so the manual says to give two sites of one name the same `hidden:`, or two names.
//
// Refusing the disagreement is not available. This runs under `query`, so it runs once
// per introspection pass, and a panic raised in a pass that is not the last one is
// swallowed: the document stops converging, the compiler warns about an element count
// that does not stabilise, and nothing says why (measured; see *Findings*).
//
// Must be called in a context, and only after the slide has been laid out,
// which is what puts the reports in reach of `query`.
#let hidden-names(index) = {
  let names = ()
  for site in query(site-label)
    .map(it => it.value)
    .filter(it => it.slide == index) {
    if site.hidden and site.name not in names { names.push(site.name) }
  }
  names.sorted()
}

// A length as a number of typst points, rounded to a tenth of a thousandth.
//
// Typst's own numbers run to fifteen digits, which no renderer can tell apart and which
// makes the emitted page hard to read and hard to diff.
//
// Must be called in a context, because a length may be relative to the text size,
// which is resolved here at the slide rather than at the tag site.
#let pt-of(value) = calc.round(value.to-absolute().pt(), digits: 4)

// The display state of every addressed tag in one state, as the browser needs it.
//
// Every state holds every name, even the ones it leaves at the identity.
// The browser keeps a display state as inline style until something overwrites it, so a
// state that said nothing about a tag would leave the previous state's style in place,
// and stepping backwards would not undo what stepping forwards did.
//
// Every fallback is taken here: a tag the timeline never revealed or hid falls back to
// its own `hidden:` argument, which the reports above supplied.
// Lengths become numbers of typst points, which are the user units of the frame's SVG,
// so the runtime writes them as CSS lengths and the browser scales them with the slide.
#let tags-of(display, names, hidden) = {
  let entries = (:)
  for name in names + hidden.filter(name => name not in names) {
    let current = display.at(name, default: identity)
    entries.insert(
      name,
      (
        hidden: if current.hidden == none { name in hidden } else {
          current.hidden
        },
        x: pt-of(current.x),
        y: pt-of(current.y),
        scale: current.scale,
      ),
    )
  }
  entries
}

// The whole plan of a slide, as the runtime reads it.
//
// A state is a dictionary rather than its tags alone, because panning adds a slide-level
// value to the same state, and an array of tag dictionaries would have nowhere to put it.
//
// Must be called in a context.
#let browser-plan(plan, names, hidden) = (
  states: plan.states.map(state => (
    tags: tags-of(state.display, names, hidden),
  )),
)
