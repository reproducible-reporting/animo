// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The background of the social cards of the documentation site.
// The custom layout in `social-card.yml` draws the text of each card on top of this image,
// because zensical leaves out the text elements of an SVG that it uses as a card layer.
// Zensical has to render the cards without typst, so the compiled SVG is committed.
// After a change, recompile it from the root of the repository:
//
//   typst compile --ignore-system-fonts logo/social-card.typ logo/social-card.svg

#let teal = rgb("#008BA8")
#let orange = rgb("#C9600A")
#let night = rgb("#0A1A1F")

// The size GitHub recommends for the social preview of a repository.
#let width = 1280pt
#let height = 640pt

// The position and the height of the logo.
#let size = 340pt
#let x = 880pt
#let y = 140pt

// A soft teal glow, centered on the logo, lights up the dark background.
// The glow is relative to the page, so a shape with the same fill blends into the page.
#let glow = gradient.radial(
  (rgb(color.mix((teal, 30%), (night, 70%))), 0%),
  (night, 100%),
  center: ((x + size / 2) / width * 100%, (y + size / 2) / height * 100%),
  radius: 45%,
  relative: "parent",
)
#set page(width: width, height: height, margin: 0pt, fill: glow)

// The logo is a single path, so a different color only needs a different fill.
#let logo-source = read("animo-white.svg")
#let logo(fill, height) = image(
  bytes(logo-source.replace("#FFFFFF", fill.to-hex())),
  format: "svg",
  height: height,
)

// The outline of the logo, without the holes of the face.
// It retraces the last three subpaths of the logo path,
// with the top semicircle as two cubic quarter arcs.
// A typst curve, unlike an SVG image, accepts a gradient that matches the page fill.
#let silhouette(fill, height) = {
  let p(x, y) = (x * height / 32, y * height / 32)
  // The magic number of a cubic quarter arc, times the radius of the head.
  let k = 0.5523 * 14
  let bump(x) = (
    curve.move(p(x, 27)),
    curve.cubic(p(x, 31), p(x - 6, 31), p(x - 6, 27)),
    curve.close(),
  )
  curve(
    fill: fill,
    ..bump(22.67),
    ..bump(15.33),
    curve.move(p(8, 27)),
    curve.cubic(p(8, 31), p(2, 31), p(2, 27)),
    curve.line(p(2, 16)),
    curve.cubic(p(2, 16 - k), p(16 - k, 2), p(16, 2)),
    curve.cubic(p(16 + k, 2), p(30, 16 - k), p(30, 16)),
    curve.line(p(30, 27)),
    curve.cubic(p(30, 31), p(24, 31), p(24, 27)),
    curve.close(),
  )
}

// A motion trail of earlier positions, which fade into the background.
// The text area on the left ends where the faintest copy starts.
#for (i, amount) in ((3, 18%), (2, 36%), (1, 62%)) {
  // Typst writes a mixed color to SVG in oklab, which the renderer of zensical reads as black.
  let fill = rgb(color.mix((teal, amount), (night, 100% - amount)))
  place(dx: x - i * 96pt, dy: y, silhouette(fill, size))
}
// The silhouette behind the logo hides the trail behind the holes of the face.
// It has the same fill as the page, so the holes show the glow.
#place(dx: x, dy: y, silhouette(glow, size))
#place(dx: x, dy: y, logo(teal, size))

#place(bottom, rect(width: 100%, height: 16pt, fill: orange))
