// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The deck: the document-level show rule that gives every slide of a document its shape.
//
//     #show: animo.with(width: 16cm, height: 9cm)
//
// A show rule rather than a call, because it receives the whole document,
// which is what lets it carry the HTML shell and the stylesheet in the HTML target
// and leave the paged targets alone.
// The shape reaches the slides through a state rather than through an argument,
// because the slides are already content by the time the rule runs.

#let deck-defaults = (width: 16cm, height: 9cm, margin: 1cm)

// The shape of the deck, as a dictionary with `width`, `height` and `margin`.
// A document without the show rule still has slides, and they take these defaults.
#let deck-shape = state("animo-deck", deck-defaults)

// Which paged output is being compiled.
//
// The HTML target is detected with `target()`; the paged modes are selected explicitly
// with `--input animo=presentation`, and default to the handout.
#let paged-mode() = {
  let mode = sys.inputs.at("animo", default: "handout")
  assert(
    mode in ("handout", "presentation"),
    message: "--input animo= takes `handout` or `presentation`, got "
      + repr(mode),
  )
  mode
}

// A CSS colour for a typst colour.
#let css-color(value) = value.to-hex()

// A length as a bare number of typst points, rounded to a tenth of a thousandth.
// Typst's own numbers run to fifteen digits, which no renderer can tell apart
// and which makes the emitted page hard to read and hard to diff.
#let pt-number(value) = str(calc.round(value.to-absolute().pt(), digits: 4))

// A length as a CSS length that covers that many typst points at any window size.
//
// `--animo-unit` is one typst point as the window currently renders it, so every length
// animo emits is that unit times a number and never one length divided by another.
// Chromium computes `calc(<length> / <length>)` to a number and firefox 153 does not,
// dropping the whole declaration, so nothing may lean on it. See *Findings*.
#let unit-length(value) = "calc(var(--animo-unit) * " + pt-number(value) + ")"

// The custom properties that turn a deck's shape into the geometry of the HTML page.
//
// The viewport is the slide's visible box, as large as the window allows at the deck's
// aspect ratio, and `--animo-unit` is that width divided by the slide width in points:
// one typst point, as a CSS length, at whatever size the window currently has.
// Dividing a length by a *number* is the oldest arithmetic CSS has, so this resolves the
// pt of a frame against the px of a window in every engine,
// and without the runtime having to measure anything or listen for a resize.
#let properties(shape) = {
  let aspect = shape.width.to-absolute() / shape.height.to-absolute()
  (
    "--animo-aspect": str(calc.round(aspect, digits: 6)),
    "--animo-viewport": "min(100vw, 100vh * " + str(aspect) + ")",
    "--animo-unit": "calc(var(--animo-viewport) / "
      + pt-number(shape.width)
      + ")",
  )
}

// The stylesheet of one deck: the static rules, followed by the deck's own geometry.
#let stylesheet(shape) = {
  let declarations = properties(shape)
    .pairs()
    .map(((name, value)) => "  " + name + ": " + value + ";")
    .join("\n")
  read("animo.css") + "\n:root {\n" + declarations + "\n}\n"
}

// The HTML page a deck becomes: the stylesheet, the runtime and one container for the slides.
#let html-shell(shape, body) = html.html({
  html.head({
    html.meta(charset: "utf-8")
    html.elem("meta", attrs: (
      name: "viewport",
      content: "width=device-width, initial-scale=1",
    ))
    html.elem("style", stylesheet(shape))
    // A module script is deferred by default, so the runtime finds the slides in place.
    html.elem("script", attrs: (type: "module"), read("animo.js"))
  })
  html.body(html.elem("div", attrs: (class: "animo-deck"), body))
})

#let animo(body, width: 16cm, height: 9cm, margin: 1cm) = {
  assert(
    margin * 2 < width and margin * 2 < height,
    message: "the margin leaves no room for the body of a slide",
  )
  let shape = (width: width, height: height, margin: margin)
  context {
    if target() == "html" {
      html-shell(shape, {
        deck-shape.update(shape)
        body
      })
    } else {
      deck-shape.update(shape)
      body
    }
  }
}
