// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// A slide: a viewport onto a canvas, plus the timeline that animates it.
//
// The two rectangles are what makes panning mean anything.
// The viewport is what the audience sees, and it clips: one HTML slide container,
// one presentation-PDF page, one handout page.
// The canvas is what the body is laid out on, at least as large as the viewport,
// with its origin at the viewport's origin and the body inset by the deck's margin.
// A slide that places nothing outside the viewport is indistinguishable from a slide
// with no canvas concept at all.
//
// The timeline is resolved before the body is laid out, because the body's layout depends
// on it, and the result is provided to the body rather than published to a state.
// A slide with S `sub` calls has S+1 states:
// the presentation renders one page each, the handout renders the states that asked for a
// page, and the HTML target renders one frame for the whole run of them.

#import "canvas.typ": (
  auto-extent, canvas-label, explicit-extent, record-placements,
)
#import "deck.typ": css-color, deck-shape, paged-mode, unit-length
#import "plan.typ": (
  continuous-names, html-view, inside, provide, resolve, view-of,
)

// Where a slide sits in the deck, counting every slide.
// This is what addresses a slide in the URL and in the DOM, so it counts the slides
// the presenter walks through, not the ones that carry a number.
#let position = counter("animo-position")

// What `numbered:` counts. Nothing displays it yet.
#let slide-number = counter("animo-slide")

// Split a background into the two things it can be.
//
// A colour is a page fill on paper and a CSS background in the browser,
// because `set page` is unavailable in the HTML target.
// Content is neither, and is drawn into the slide behind the body instead,
// which is the only form an image can take: typst has no image page fill either.
// A gradient or a tiling is refused rather than silently dropped in one of the targets,
// and the message says the form that does work in all four outputs.
#let split-background(background) = {
  if background == none {
    (fill: none, ink: none)
  } else if type(background) == color {
    (fill: background, ink: none)
  } else if type(background) == content {
    (fill: none, ink: background)
  } else {
    panic(
      "background takes a colour or content, got "
        + str(type(background))
        + "; wrap a gradient or a tiling in a `rect` of the slide size to use it",
    )
  }
}

#let slide(
  body,
  animation: (),
  canvas: auto,
  background: none,
  numbered: true,
) = {
  let (fill, ink) = split-background(background)
  let plan = resolve(animation)
  let names = continuous-names(animation)
  position.step()
  if numbered {
    slide-number.step()
  }
  // A tag outside any slide has to be diagnosed at the tag site, and this is what says so.
  // It is published rather than provided because it has to be readable where no provider
  // ran, and it is set around the enclosing context block rather than inside it, because
  // a state read inside `measure` resolves at that block's own location.
  inside.update(true)
  context {
    let shape = deck-shape.get()
    let index = position.get().first()
    let viewport = (width: shape.width, height: shape.height)
    let inner = (
      width: viewport.width - 2 * shape.margin,
      height: viewport.height - 2 * shape.margin,
    )

    // One rendering of the slide, for one view of its plan.
    // The body is laid out at the inner size whatever the canvas turns out to be,
    // so the recorded placements do not move when the canvas grows around them.
    let laid-out(view) = {
      if ink != none {
        place(top + left, box(
          width: viewport.width,
          height: viewport.height,
          clip: true,
          ink,
        ))
      }
      place(
        top + left,
        dx: shape.margin,
        dy: shape.margin,
        block(width: inner.width, height: inner.height, provide(
          view,
          record-placements(index, body),
        )),
      )
    }

    // The canvas is a property of the slide and not of a state, so it is measured once,
    // and with a view that exists whatever the outputs ask for.
    // Any view gives the same answer, because a display state is layout-neutral.
    let measuring = if target() == "html" {
      html-view(names)
    } else {
      view-of(plan, names, 0)
    }
    let extent = if canvas == auto {
      auto-extent(index, provide(measuring, body), viewport, shape.margin)
    } else {
      explicit-extent(canvas)
    }
    let size = (
      width: calc.max(viewport.width, extent.width),
      height: calc.max(viewport.height, extent.height),
    )

    [#metadata((
        slide: index,
        width: size.width,
        height: size.height,
      ))#canvas-label]

    if target() == "html" {
      let style = if fill == none { none } else {
        "background: " + css-color(fill)
      }
      html.elem(
        "div",
        attrs: (
          class: "animo-slide",
          data-animo-slide: str(index),
          data-animo-states: str(plan.states.len()),
          ..if style == none { (:) } else { (style: style) },
        ),
        html.elem(
          "div",
          attrs: (
            class: "animo-canvas",
            style: "width: "
              + unit-length(size.width)
              + "; height: "
              + unit-length(size.height),
          ),
          html.frame(block(
            width: size.width,
            height: size.height,
            laid-out(measuring),
          )),
        ),
      )
    } else {
      // The pages this paged output asks for, in page order:
      // every state in the presentation, and the states that asked for a page in the
      // handout. A handout whose timeline turns every page down is empty, and that is
      // the author's decision to make: `handout:` is the only thing that says what a
      // handout holds.
      let views = if paged-mode() == "presentation" {
        range(plan.states.len()).map(index => view-of(plan, names, index))
      } else {
        plan
          .states
          .enumerate()
          .filter(((index, state)) => state.handout)
          .map(((index, state)) => view-of(plan, names, index))
      }
      for view in views {
        page(
          width: viewport.width,
          height: viewport.height,
          margin: 0pt,
          fill: fill,
          place(top + left, block(
            width: size.width,
            height: size.height,
            laid-out(view),
          )),
        )
      }
    }
  }
  inside.update(false)
}
