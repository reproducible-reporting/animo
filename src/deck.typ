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

// A length as a CSS or an HTML length, rounded to a tenth of a thousandth of a point.
// Typst's own numbers run to fifteen digits, which no renderer can tell apart
// and which makes the emitted page hard to read and hard to diff.
#let pt-string(value) = (
  str(calc.round(value.to-absolute().pt(), digits: 4)) + "pt"
)

// The custom properties that turn a deck's shape into the geometry of the HTML page.
//
// Only the slide size ever reaches CSS. The canvas size stays in typst, because the
// canvas element is scaled as a whole and every length inside it is then a typst point.
// The scale is a plain length-by-length division, which resolves the pt of the frame
// against the px of the window without the runtime having to measure anything.
#let properties(shape) = {
  let aspect = shape.width.to-absolute() / shape.height.to-absolute()
  (
    "--animo-aspect": str(calc.round(aspect, digits: 6)),
    "--animo-width": pt-string(shape.width),
    "--animo-viewport": "min(100vw, 100vh * " + str(aspect) + ")",
    "--animo-fit": "calc(var(--animo-viewport) / var(--animo-width))",
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
