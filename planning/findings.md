<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Animo Findings

This document records the verified behaviour of typst 0.15.0, and of the browsers Animo drives,
that [the design](design.md) relies on, so that it does not have to be rediscovered.
The behaviour was checked against the installed `typst 0.15.0` binary,
with chromium 151, firefox 153 and playwright's webkit 26.5 for the browser measurements.
Where the engines differ, the entry says so, because a deck has to work in all of them.
Webkit is measured in a container, for the reason under [Testing](../docs/testing.md).

Every entry is a **point-in-time claim** and is written as one.
Almost every one of them also has a probe under `probes/` that asserts the behaviour itself
rather than a feature that happens to depend on it,
and the few that cannot have one say so in [Behaviour Probes](../docs/probes.md),
which also maps each entry to the module that guards it.
A probe that fails indicates that a finding has changed:
the entry below is rewritten first, saying what now holds and on which release it was observed,
and the probe follows in the same commit.

The other documents refer to this one as *Findings*.
A reference in italics here, *Architecture* or *Regions* for instance,
is a section of [design.md](design.md) unless it names an entry below.

## Element identity in the output: `data-typst-label`

This attribute is what the whole design rests on.

- Labelled content appears in SVG output as `<g data-typst-label="name">`.
  In all of typst 0.15.0 there is exactly **one** emission site,
  `crates/typst-svg/src/lib.rs:348`,
  and it fires only for `group.label`,
  which means only for **labelled `box` and `block` elements**.
  A label on a bare `rect`, or on a text span, emits nothing.
- It works **inside `html.frame`**, which is what makes browser animation possible.
- It works for content inside **math** and inside **cetz** canvases.
- **Duplicate labels are permitted** and each occurrence gets a separate group, which is what
  makes "one tag, several elements" work
  and what makes one CSS rule reach the same tag in every epoch frame of a slide.

The attribute was added by PR
[#4822 "Animation-friendly export"](https://github.com/typst/typst/pull/4822) (merged
2024-09-03), resolving issue
[#4384](https://github.com/typst/typst/issues/4384), whose stated purpose was
"exposing some way to generate groups with well-known identifiers in SVG export, **which
external tools can pick up**".
That is precisely this use case. It shipped in **v0.12.0** and is
documented in the 0.12.0 changelog ("Exported SVGs now contain the `data-typst-label`
attribute on groups resulting from labelled boxes and blocks").
It has survived 0.12, 0.13 and 0.14 unchanged, and typst 0.15.0 still emits it.
No open issue proposes changing or removing it.
It is not mentioned in the reference documentation, only in that changelog entry.

The residual risk lies in the HTML wrapper rather than in the attribute itself.
HTML export remains behind `--features html`, warns that "behaviour may change at any time",
and its tracking issue
[#5512](https://github.com/typst/typst/issues/5512) gives no stabilisation timeline.
"Frame API for embedded layout-as-SVG" and "Linking to a label, with derived ID" are
already ticked there, but "Share printing code between SVG and HTML export" is not, so the
SVG-inside-HTML emission path may still be refactored.

## The frame is the smallest unit of DOM addressability

This is what forces typst to render every content state of a region ahead of time,
and therefore the whole epoch model.

- `html.elem` **inside** `html.frame` is dropped, with the warning "elem may not occur inside
  of a paragraph and was ignored". There is no way to give a sub-area of a frame a separate DOM
  node, so a region cannot be a separate HTML element inside a slide frame.
- `html.frame` inside `html.frame` compiles without error but contributes no second `<svg>`,
  so nesting frames is not a route to independently swappable sub-frames either.
- `set page(..)` inside `html.frame` is an error ("page configuration is not allowed inside of
  containers"), so a slide is a sized `block`, not a page, in the HTML target.
- Positions cannot be read in HTML output (see below),
  so Animo cannot place per-region frames itself either,
  because it does not know where the region is.

The only mechanism available is therefore to lay out every content state inside the one frame
of the slide, and let the browser choose which of them is shown.
Each region lays its body out once per epoch, and places the renderings on top of each other at
the corner of its footprint.
Each rendering is a labelled box, so it becomes a group that the runtime can address
(see *Element identity in the output: `data-typst-label`* and *Architecture*).
That is also why the vertical-flow alternative is not usable here.
That alternative cuts the slide into a stack of separate frames,
the way `slipst` cuts a document into slips.
It supports only content that flows top to bottom,
whereas an Animo slide is a fixed-size 2D canvas with `#place`.

## Regions: fixed footprints across epochs

Measured on a region with two epochs, i.e. two content states (a short line and a version long
enough to wrap), with the footprint taken as the per-axis maximum of
`measure(epoch, width: avail)` inside `layout(size => ..)`:

| Check                                                      | Result                                             |
| ---------------------------------------------------------- | -------------------------------------------------- |
| footprint chosen for both epochs (paged)                   | `w=233.88pt h=21.63pt`, identical                  |
| y position of the content after the region (paged)         | identical in both epochs                           |
| `data-typst-label` transform after the region (HTML)       | `translate(41.613 40.876)` in both epochs          |
| `getBoundingClientRect` of a label after the region (HTML) | `{x:0.05, y:58.81, w:100.61, h:14.98}` in both     |
| pixel diff between the two epoch frames, full window       | 2958 px, all inside the region's band (y 29 to 43) |
| pixel diff below the region                                | none                                               |

`measure` internally sets `Target::Paged`
(`crates/typst-library/src/layout/measure.rs`, "let style = TargetElem::target.set(Target::Paged)"),
so a footprint measured in the HTML target is the footprint `html.frame` will produce. This is
what makes one footprint rule serve both targets.

Consequently, `layout` and `measure` per epoch are a sufficient and verified mechanism for
footprints.
The region only needs the epochs the slide actually has,
so the cost is linear in epochs rather than combinatorial in tags.

## Regions: an inline footprint has to pin its baseline

Measured on typst 0.15.0, while building the implicit region of an inline tag, over five epochs: a
word, a word at 2em, nothing, two lines, and an equation with a subscript.

- **A box takes its baseline from its content, even at a fixed size.**
  `box(width: W, height: H, c)`, sized to the per-axis maximum,
  puts the rest of its line at 17.24, 24.48 or 31.63 pt
  when `c` is a word, a word at 2em or nothing,
  since a box with no baseline in its content sits on its bottom edge.
  A fixed inline footprint therefore does not hold its line still.
- **A box whose content is placed has no baseline**, so its `baseline` argument
  alone decides where it sits.
  Placing each epoch at `dy: A - a`, with `A` the tallest ascent and `a` the ascent of the epoch,
  and lowering the box by `baseline: D`, the deepest descent,
  puts the rest of the line and the next paragraph at the same height in every epoch
  (24.48 and 52.06 pt), the empty one included.
  The epoch with the tallest ascent lays out exactly as its untagged control.
- **`measure` reports no baseline, but the descent is readable.**
  The height of `[#body#box(width: 0pt, height: 10000pt)]` minus the 10000 pt pole
  is how far the body reaches below its first baseline.
  Text reaches nothing below the baseline at the default `bottom-edge`
  (a word and a word at 2em measure 0 pt), while a second line and a subscript do.
- In the SVG of an `html.frame`, the labelled group's first child is still the inner slot, which
  now carries the `transform="translate(0 dy)"` that typst writes; the CSS `translate` and `scale`
  properties compose with that attribute (see *CSS animation of typst SVG groups*).

## Regions: what a region learns from its container

Measured on typst 0.15.0 with a filling block inside `layout(size => ..)`
on a 360 pt wide page body.

| Container                                                             | Width handed to `layout` |
| --------------------------------------------------------------------- | ------------------------ |
| grid column `1fr` of `(1fr, 2fr)`, fixed `100pt` column               | 120 pt, 100 pt           |
| table cell of `(1fr, 1fr)`, `columns(2)`                              | 170 pt, 172.8 pt         |
| placed `box(width: 120pt)`, `block(width: 50%)`, inset 10pt           | 120 pt, 180 pt, 340 pt   |
| `auto` grid column, `stack(dir: ltr)`, auto `box`, bare `place`, math | 360 pt                   |
| unbounded `measure`                                                   | `float.inf * 1pt`        |

- The rows of 360 pt are indistinguishable at the region from a container that is that wide.
- `align(top + left, ..)` left-aligns content under `set align(center)`,
  while `align(top, ..)` does not.
- A counter stepped per region and reset before a rendering numbers nested regions in document
  order, identically in every rendering, in both targets, and a `measure` inside steps nothing.

## Crossfading epoch frames

Two epoch frames were stacked in one grid cell
(`display: grid`, both children in `grid-row: 1 / grid-column: 1`,
`isolation: isolate` on the parent).
At the midpoint of a transition, with both frames at `opacity: 0.5`,
they were compared against the single frame at `opacity: 1`:

| Mid-transition blending        | Max deviation outside the region |
| ------------------------------ | -------------------------------- |
| plain `opacity` crossfade      | 62/255 (text visibly washes out) |
| `mix-blend-mode: plus-lighter` | 1/255 (rounding only)            |

`plus-lighter` is therefore what makes the containment claim true *during* the transition
and not only at its endpoints. `slipst` uses the same blend mode for its
whole-slip crossfades.

**The sum is exact in all three engines, once the frame is the element that isolates.**
Chromium 151 and firefox 153 add the two half-opacity layers back to one opaque layer bit for
bit. Playwright's webkit 26.5 does not while the isolation sits on an HTML ancestor of the
frame: ten pixels on antialiased glyph edges drift by up to 42/255, measured in a container
on 2026-09-17.
With `isolation: isolate` on the frame itself, the deviation in webkit is rounding only as well.
See the entry on where a blend stops, further down, for why.

**A group's blend reaches ink beside it and not ink in another frame.** Measured on
chromium 151 and firefox 153 on 2026-09-15 and on playwright's webkit 26.5 on 2026-09-17,
with two stacked frames of identical content and the region's labelled group at
`opacity: 0.5` in each. Every row has the frame isolating, as the entry below requires:

| `mix-blend-mode: plus-lighter` on            | chromium 151 and firefox 153 | webkit 26.5          |
| -------------------------------------------- | ---------------------------- | -------------------- |
| two groups overlaid in the *same* frame      | 1/255 (rounding only)        | 1/255                |
| the region's group, one frame to the other   | 64/255 (a plain crossfade)   | 64/255               |
| the frames, region scoped by `visibility`    | 1/255 (rounding only)        | a plain crossfade    |
| the epoch renderings of one frame, so scoped | 1/255 (rounding only)        | one row of 95 pixels |

The first row is the control.
It shows that `plus-lighter` on a `<g>` has an effect,
and that a group does add to the ink beside it in the same frame.
The second row shows that the group did not add to the frame below,
so a blend on a region's group degraded to exactly the plain opacity crossfade of the table
above.

The third and fourth rows test the same mechanism on two structures,
and the engines do not treat them alike.
In both rows, the blend sits where it does reach,
and `visibility` scopes the outgoing side down to the regions it hands over,
which a descendant can take back. On one frame per
epoch, which is the structure a slide had first, webkit leaves the glyph cores of the whole
region at half, across 473 pixels of twelve rows, and the result is the plain opacity
crossfade. On one frame holding a rendering per epoch, which is the structure a slide has,
all three engines sum the halves. Webkit rasterises the blended group into a buffer whose
bounds it rounds, so the bottom row of the region comes back white where the single copy
carries the antialiasing of the glyphs below their baseline: 95 pixels of one row, by up to
128/255.
The pixel count tells the two failures apart,
because a wash-out changes the glyph cores of every row,
while this rounding changes the edge of one row.

The region-scoped crossfade of *Architecture* is therefore built,
and the whole-frame fallback is not needed.
The merged frame also does more than save on `<defs>`,
because it is what makes the crossfade add up in webkit at all.
The epoch renderings are the outermost groups of one frame, so they are ink beside each other,
and the first row shows that the blend reaches such ink.
A region's group is not beside the group of the other rendering,
which is why the blend stays on the rendering.

The stacking, the grid cell and the isolation are common to all of these measurements.
The isolation is essential, because `plus-lighter` sums inside the isolated group,
against a transparent backdrop rather than against the page.
The entry below says which element has to carry that isolation.

**How far a group's blend reaches past the frame that holds it is not the same in every engine.**
Measured on 2026-09-15 for chromium and firefox and on 2026-09-17 for webkit, on a
handwritten stack rather than on typst's output: one inline SVG on an opaque ground, a dark
red mark inside it and a dark green ground, so that a blend reaching the ground comes back
with green in it.

| What is under the frame of the mark        | chromium 151 | firefox 153  | webkit 26.5 |
| ------------------------------------------ | ------------ | ------------ | ----------- |
| the element the SVG is painted on          | summed in    | out of reach | summed in   |
| an inline SVG stacked below that frame     | summed in    | out of reach | summed in   |
| the page, behind the element that isolates | out of reach | out of reach | summed in   |
| the same page, with `isolation: auto`      | summed in    | out of reach | summed in   |

Firefox stops a group's blend at the root of the inline SVG. Chromium does not, and stops at
the element that carries `isolation: isolate`.
An earlier reading of the second row of the table above took that firefox behaviour for the
rule, and gave it as the reason that a region-scoped blend cannot work.
The firefox behaviour is not the rule,
but the two engines agreed on that row, so the design decided on it still stands.
What makes chromium contain the
blend in the output of typst and not in the handwritten stack was not pinned down, and the
difference is recorded here rather than explained.

**An isolating HTML ancestor does not confine a group's blend in webkit.**
The last two rows of the table test the isolation.
In chromium, the blend reaches the page when the isolation is removed,
and stops at the isolating element when the isolation is written.
The third row therefore shows the isolation working,
rather than a boundary at which chromium would have stopped anyway.
Webkit gives the same answer either way:
a blend on a group inside an inline SVG reaches the page whatever an HTML ancestor declares.

The consequence is clearly visible, because `plus-lighter` adds.
Black ink adds nothing to the ground it lands on,
so a slide whose epoch renderings blend against the page renders **blank** in webkit,
showing the ground instead of the text.

**The element that confines it in every engine is the inline SVG that holds the group.**
Measured on 2026-09-17. With `isolation: isolate` on the epoch frame, the blend stops there
in chromium 151, firefox 153 and webkit 26.5 alike. Animo therefore writes the rule on the
frame rather than on the canvas, and the canvas carries no isolation.
Moving the isolation to the frame also took webkit's whole-frame midpoint
from ten pixels at 42/255 to rounding only.
The engine-dependent exactness in the first entry above was therefore caused
by the failing isolation of the ancestor rather than by webkit's arithmetic.

`probes/test_crossfade.py` holds each engine to the answer measured for it,
so one that changes its mind says so by failing rather than by rendering differently.

## Choosing between stacked renderings: `opacity`, not `visibility`

Measured on chromium 151 and firefox 153, while building the subslide numbering.

A value finer than a slide number is rendered once per subslide,
and one of the renderings is shown.
The property that shows the rendering cannot be chosen freely, because of the entry above.
An epoch frame that is not being shown is `visibility: hidden`,
and a descendant may take that back,
which is exactly what scopes the outgoing frame of a region crossfade.

`visibility` therefore cannot also select a rendering.
With two frames stacked as epoch frames are and
the second hidden, a `visibility: visible` on a group inside that second frame computes to
`visible` and **paints**: the pixel that should show the front frame's red shows the hidden
frame's blue. An `opacity: 1` on the same group computes to `opacity: 1` and
`visibility: hidden`, and the pixel stays red.

`opacity` still selects a rendering within the frame that is shown.
With two groups in the visible frame, one at `opacity: 0`, only the ink of the other group
shows.

A rendering of a stack is therefore chosen with `opacity`, and each property has one job.
`visibility` says which frame the slide is on, `opacity` says which rendering of a stack the
position is on, and neither can undo the other.

## Crossfading two slide containers

Measured on chromium 151 and firefox 153, for the slide boundary under *Architecture*.
The case above concerns two inline SVGs inside the canvas, which carries no ground.
A slide boundary is two HTML elements that each carry an opaque background,
stacked inside an element that isolates and that is centred on a surround.
The probe stacks them in one grid cell of that element.
Animo's stage is that element, and it stacks its slides by absolute positioning instead.
The probe asserts the midpoint for the grid cell,
and `tests/test_transitions_html.py` asserts it for an Animo deck.

| Midpoint of a boundary between two opaque grounds | Deviation from their average |
| ------------------------------------------------- | ---------------------------- |
| plain `opacity` crossfade                         | 64/255                       |
| `mix-blend-mode: plus-lighter` on the containers  | 0 to 1/255 (rounding only)   |

The mechanism therefore carries over unchanged,
and slides add a reason for it that frames never needed.
A plain crossfade handles two opaque grounds incorrectly,
since each ground is composited over what is behind it,
and the surround shows through the half-transparent pair.
One slide blended against the transparent backdrop of the isolating element is that slide, to
within the same rounding, so the blend may sit on every slide rather than be turned on for the
length of a boundary.

**The ground of the isolating element is inside the group it isolates.**
With the surround written on the element that carries `isolation: isolate`, a white
surround is added to both halves and takes the midpoint 239/255 away from the average of the
two slides.
With the same colour written on the page instead, the midpoint is exact.
A black surround hides the mistake completely, because black adds nothing,
which is why this was found by reasoning rather than by inspection.
Animo therefore writes its surround on
`body` and leaves the deck and the stage without a background.

## What keeping every slide laid out costs

Measured on chromium 151 through the devtools protocol, on an i7-1260P, while choosing how a
slide that is not being shown is hidden.
A crossfade needs both containers laid out,
so `display: none` cannot hide the two slides that a boundary involves.
The question was whether it has to hide any of the other slides.

The table compares every slide laid out for the whole session
against `display: none` on all slides but the ones in use:

| Deck                                   | First paint    | Layout objects     |
| -------------------------------------- | -------------- | ------------------ |
| the tour, 13 slides, 17 frames, 1.1 MB | 72 to 86 ms    | 531 to 12 043      |
| 60 slides, one epoch each, 5.5 MB      | 0.43 to 0.96 s | 1 361 to 113 482   |
| 60 slides, three epochs each, 19 MB    | 4.2 to 10.2 s  | 5 594 to 1 397 520 |

Keeping every slide laid out is nearly free on a deck of the tour's size,
and doubles the first paint of an ordinary long deck.
The cost is paid at every load, and `typst watch` reloads the browser after every
edit that compiles, so it is paid throughout the writing of a deck and not only once at a talk.
Animo lays out two slides and no more: the one being shown, and the one a boundary is crossing
from. Stepping was not measurably affected either way, at 24 to 43 ms per step on every deck
and under both regimes, which shows the cost is layout at load and not interaction.

**`content-visibility: hidden` is not cheaper than `display: none`**,
as measured on the same three decks: 0.076, 0.44 and 4.39 s against 0.076, 0.40 and 4.31 s.
That is within the noise on the first deck and slightly slower on the other two,
so no third way of hiding a slide is worth using.

**What is left of the first paint is style recalculation and not layout.** With `display: none`
the heaviest deck spends 3.0 s of its 4.3 s recalculating style over 2.07 million DOM nodes and
3 ms laying anything out, so the remaining lever is the number of nodes typst emits rather than
anything the runtime does with them. Dropping the definitions that an earlier epoch frame
already carried, which is what a shared `<defs>` hoisting would do, takes that deck from
4.34 s to **0.55 s** and its nodes from 2.07 million to 407 thousand,
and the deck with one epoch a slide from 0.42 s to 0.16 s.
Slides 1, 30 and 60 of both decks render pixel-identically before and after,
which shows that the deduplicated page is the same page.
Typst's def ids are content hashes, so an id that occurs twice is one definition written twice.
The hoisting is therefore worth a factor of eight on the first paint of a deck with structural
subslides, which is a second reason for it beside the factor of two it is worth on the gzipped
page.

This is a cost rather than a behaviour, so it has no probe.
`docs/probes.md` records it among the entries that cannot have one.

## Chromium rasterises a frame differently while an opacity animation runs in it

Measured on chromium 151 and firefox 153, while asserting the containment claim above
*during* a transition rather than at its endpoints.

Chromium promotes a group with a running `opacity` animation to a compositing layer of its
own, and the glyphs of the frame it sits in are then rasterised along a different path. A
raster taken mid-step and one taken at rest therefore differ on antialiased edges, whether or
not anything about the slide actually moved: 10 pixels by up to 22/255 outside a crossfading
region, and up to 79/255 on the glyph edges inside it.
Firefox 153 shows none of this.
The cause is neither the blend nor the isolation,
because forcing `mix-blend-mode: normal` and `isolation: auto` leaves the difference unchanged,
and a step that animates only `translate` is exact.

This has consequences for the measurement of a transition, and for the obvious remedy:

- Any comparison between a raster taken with an animation in flight and one taken at rest
  measures the rendering path and not the transition. **Every raster of a mid-flight
  comparison has to be taken with the same animation in flight**, the ones standing for the
  endpoints included, sampled just inside the step rather than at its ends, since an animation
  at its end time is finished and rasterises as at rest again. Compared that way the
  containment is exact in both engines.
- **A raster sampled just inside the step is not the slide at rest**,
  so a mid-flight comparison carries more rounding than a comparison of stated opacities.
  The container being faded out is at an opacity of just under one there.
  Chromium 151 rasterises it 1/255 below the same container at rest,
  over the whole ground rather than on glyph edges, and firefox 153 rasterises it exactly.
  The end that stands for the container being faded in is exact in both engines.
  Half of that offset reaches the average of the two ends,
  and the midpoint raster adds half a unit from its quantisation.
  The midpoint of a mid-flight comparison is therefore the sum of its two ends to within
  1.5/255, where a comparison of stated opacities is exact to 1/255.
  Measured on 2026-09-17, on the mechanism by hand and in an Animo deck.
  The deck came to 1.0/255 on a workstation and to 1.5/255 on a continuous integration runner,
  which takes an end 2/255 from the slide at rest.
  Which way an end rounds differs between machines,
  and an allowance of 1/255 on a mid-flight comparison passes on one machine and fails on
  another.
- `will-change: opacity` on the carried groups removes the difference, because a group that is
  always promoted rasterises the same at rest and in flight.
  It is not worth it, because the promoted text then differs from unpromoted text
  *permanently*, and by more (643 of 3600 ink pixels, 285 of them by over 16/255).
  The remedy is therefore larger and more visible than the problem,
  which lasts 400 ms and changes ten pixels.

## Automatic canvas sizing: `#place` is invisible to `auto`, but visible to a show rule

Measured on typst 0.15.0, for the canvas rule under *Canvas and viewport*.

- **`#place` contributes nothing to automatic sizing.**
  With `#set page(width: auto, height: auto, margin: 0pt)`
  and a body of `#place(dx: 8cm, dy: 4cm)[OUT] in-flow`,
  the page comes out `32.285 x 7.238 pt`, which is the size of the in-flow text alone.
  `measure()` agrees,
  because a block measures `32.29pt x 7.24pt` both with and without the same placement.
  Typst's own `auto` machinery therefore cannot size an Animo canvas,
  because an Animo slide is a 2D canvas built with `#place`.

- **`place` is not locatable**: `query(selector(place))` is a compile error ("place is not
  locatable"), so the placements cannot be discovered by query either.

- **But `show place:` does fire, and exposes everything needed.** A rule
  `#show place: it => { ..; it }` sees every placement and can read `it.dx`, `it.dy`,
  `it.alignment` and `it.body`. Measured on three placements:

  | Source                                  | `dx`            | `dy`           | `alignment`      | `measure(body)`   |
  | --------------------------------------- | --------------- | -------------- | ---------------- | ----------------- |
  | `place(dx: 5cm, dy: 3cm)[OUT]`          | `0% + 141.73pt` | `0% + 85.04pt` | `start`          | `21.97 x 7.24 pt` |
  | `place(bottom + right, dx: 50%)[BR]`    | `50% + 0pt`     | `0% + 0pt`     | `right + bottom` | `12.93 x 7.24 pt` |
  | `place(dx: 1cm)` inside a 4cm x 2cm box | `0% + 28.35pt`  | `0% + 0pt`     | `start`          | `29.21 x 7.24 pt` |

  Ratios stay unresolved (`50% + 0pt`), so they must be resolved against the container inside
  `layout(size => ..)`. This needs neither position introspection nor the paged target, so the
  canvas comes out the same in HTML and on paper,
  which is the invariant the whole design rests on.

- **The limit is the third row.** A placement nested inside another container is reported
  exactly like a top-level one, with offsets relative to *that* container. The rule cannot
  distinguish them, so the automatic union is approximate below the top level.
  *Open Questions* records this limit, and `canvas:` is the explicit override.

- **The union errs in both directions, and it is not exact at the top level either.**
  Measured on typst 0.15.0 against where the ink really lands, by laying the same body out twice:
  once as an Animo slide, and once as a plain block of the same inner size on a page large
  enough to hold everything, with a marker inside the placed content.

  | Placement                                   | Union    | Ink      | Error |
  | ------------------------------------------- | -------- | -------- | ----- |
  | top level, absolute offset                  | 24.00 cm | 24.00 cm | exact |
  | top level, right-aligned                    | 18.00 cm | 18.00 cm | exact |
  | top level, ratio-sized body                 | 16.00 cm | 16.82 cm | short |
  | inside a box at the body origin             | 24.00 cm | 24.00 cm | exact |
  | inside a box 6 cm in                        | 24.00 cm | 30.00 cm | short |
  | inside a 2 cm box, right-aligned, `dx: 5cm` | 20.00 cm | 8.00 cm  | long  |
  | inside a grid cell                          | 16.00 cm | 18.00 cm | short |
  | inside a placement                          | 16.00 cm | 17.00 cm | short |

  Two of these are worth stating as rules rather than as rows.
  A nested placement stated as an **offset** is counted short by wherever its container
  sits, which is the direction the design expects.
  A nested placement stated as an **alignment** is counted from the body box instead,
  which is *long*, since the body is wider than the container the author aligned to.
  A **ratio-sized body contributes nothing at all**,
  because the rule measures it without a container.
  `measure(rect(width: 100%, height: 100%))` is `0pt x 0pt`,
  while the same rectangle at an absolute size measures what it says.
  The union is therefore exact only for top-level placements whose body has an intrinsic size.

- **No mechanism can drop the placements that cannot be attributed to the body.**
  `layout(size => ..)` is ruled out above, because it breaks the paragraph.
  The one candidate left is a nesting depth kept in a `state` and stepped by show rules on the
  containers.
  As measured, it reports a positive depth inside a `box`, inside a grid cell and inside a
  `figure`, and **zero** for a placement inside another placement.
  A placement has no container to step the depth,
  and placements inside placements are what both real decks beside this repository write.
  The depth also cannot tell apart the containers that Animo itself wraps content in,
  since a tag site is a box and a region is a block,
  so every placement inside a tag would read as nested.
  The approximation therefore stays, and the error is documented in both directions.

## Recording placements: what a `show place:` rule may and may not do

Measured on typst 0.15.0 while building the automatic canvas, which needs the placements as
*data* and not merely as content the rule passes through.

- **A show rule cannot return a value, so the numbers travel as introspection.** The rule
  emits a `metadata` element carrying a label beside the placement it sees, and the union
  is taken from `query`. This works **inside `html.frame`** as well: `query` sees into a
  frame even though positions do not exist there, which is what lets one canvas rule serve
  both targets.
- **A block sized from a `query` of its layout converges.** The canvas depends on the layout of
  the very block it sizes.
  The first pass records nothing, so the block comes out at its minimum size,
  and typst's introspection loop then runs the document again with the placements known.
  It terminates because the body is laid out at a width that does not depend on the answer.
  As measured, a block whose width is the maximum of `200pt` and a placement at `dx: 400pt`
  comes out at 419.4pt in the emitted frame.
- **The recording may not disturb the layout it is watching.** A `context` block holding
  nothing but `metadata` is inline and changes no measurement. `layout(size => ..)` is
  block-level and breaks the paragraph the placement sits in.
  The same body measures `76.89pt` tall without it and `103.29pt` with it.
- **That last point closes the one route to telling a nested placement apart.**
  `layout(size => ..)` inside the rule does report the containing block of the placement
  (`400 x 300pt` at top level, `113.39 x 56.69pt` inside a 4 cm box, `200 x 300pt` in a
  grid column), which would make the automatic union exact. It cannot be used, because
  the price is a body that lays out differently from the one the author wrote.
  The union therefore stays approximate below the top level, as *Open Questions* says.
  Typst does expose the container, but asking for it changes the layout.
- **A `show place:` rule inside another one does not suppress the rule around it.** Both
  fire, so a rendering cannot decline to be recorded by installing a rule that returns
  its element untouched.
  Declining would be useful where a rendering is measured rather than laid out,
  since a `metadata` element inside a `measure` never reaches `query`,
  and the recording there costs a `context` and a `measure` per placement for nothing.
- **The inner rule runs first, and the outer one is handed what it produced.** A rule
  that attaches a label, `show place: it => [#it<unrecorded>]`, therefore gives the rule
  outside it a placement whose `label` field is that label, which is the channel the two
  rules use instead.
  A label on a placement changes no layout,
  so a rendering measures the same with the label as without it.
  The footprint that a region reserves therefore stays the size that was measured.

## A fixed-height container stacks the block-level content that does not fit

Measured on typst 0.15.0.
This behaviour is the reason that a slide body is not always laid out at the viewport's inner
height.
A container with a fixed height lays its content out in a single region of that height.
What does not fit is neither clipped nor allowed to grow the container, and what becomes of it
depends on what it is.

- **A paragraph runs past the bottom edge.** In a `block(width: 200pt, height: 100pt)` holding
  running text at 10 pt, every line lands where its line spacing puts it and the paragraph
  simply paints outside the container, ending at `333.58pt`.
- **Every block that does not fit is painted at the bottom edge.** The same container, given
  twenty-four one-line blocks with no spacing between them, lays out sixteen at `6.58pt` apart
  and reports a position of exactly `100pt` for each of the remaining eight, so they arrive as
  a pile, each drawn over the one before it.
- **A `box` container behaves exactly like a `block` one here**, so the kind of container
  makes no difference.

This is easy to miss, because the two cases differ.
A slide of running text pans correctly,
while the same slide with its steps in blocks, which is what a multi-paragraph tag site becomes,
comes out as a pile.

Consequently, a body whose flow is taller than the viewport cannot be laid out in a box of the
viewport's inner height, so Animo sizes that box to the flow instead, as *Canvas and viewport*
describes. The height comes from an unbounded measurement of the body, which no `#place`
contributes to, so the box is decided before the canvas and independently of it, and the
introspection that sizes the canvas still terminates.

## `html.frame` sizes its SVG in `em`, as an inline style

Measured on typst 0.15.0. `html.frame` writes `width` and `height` on the `<svg>` as an inline
style in `em`, dividing the frame's size in points by the text size in effect: a 200pt
block is `18.181818182em` at the default 11pt text and `9.090909091em` at 22pt.

This has two consequences for the HTML shell.
An inline style outranks a stylesheet rule, so a deck
that sizes its frames from CSS renders them at the ratio between the page's font size and
typst's text size, which is 16/11 by default and looks like an 8% scaling bug.
The size of the frame is also not a reliable unit for anything, since it moves with a `set text` the
author is free to write. Animo therefore sizes the canvas element itself and overrides the
frame with `width: 100% !important`.

The SVG also carries `overflow: visible`, so ink outside the frame's viewBox is painted
rather than clipped. The viewport element is what clips a slide.

## Fitting the slide to the browser window

Measured in playwright's chromium 151 and firefox 153.

- **`calc()` does not divide a length by a length in firefox.**
  `calc(100px / 40px)` computes to `2.5` in chromium 151 and in playwright's webkit 26.5,
  which is what CSS Values 4 type checking asks for,
  so firefox is the outlier rather than chromium the exception.
  Firefox 153 does not parse it, because `CSS.supports("scale", "calc(100px / 40px)")` is false,
  and the declaration it appears in is dropped whole, with nothing on the console.
  A deck whose fit was written that way rendered unscaled in the top-left corner of the
  window in firefox, at roughly half size, with the content beyond the viewport visible
  because the element that clips had nothing left to clip.
  The fit therefore may not be expressed as one length over another.
- **A length over a number is portable**, and that is what Animo emits.
  `--animo-unit` is `calc(var(--animo-viewport) / <slide width in points>)`,
  which is one typst point as a CSS length, at whatever size the window currently has.
  Every length Animo writes is then that unit times a number computed at compile time,
  and the runtime still never has to measure the window or listen for a resize.
- **Sizing the canvas, rather than scaling it,** is what makes a typst point the unit of
  everything inside it at any window size.
  The first version scaled the canvas element as a whole.
  Sizing it instead also keeps both the `translate` and the `scale` of the canvas free,
  which rule 5 of *Architecture* asks for when it reserves `scale` on that element for a
  future zoom.
- The two targets then agree to **0.0017 of the slide** on every edge of a placed square,
  comparing a 454-pixel handout raster with a 908-pixel browser screenshot. That is one
  pixel of the coarser raster, which is the floor of the measurement rather than a layout
  difference. Chromium and firefox agree with each other to **0.01 CSS pixel** on the
  canvas box at a 1280 by 720 window.

## SVG `<defs>` ids are content hashes

This matters because stacking several frames in one document puts duplicate ids in one DOM.

- All deduplicated defs (glyphs, clip paths, gradients, patterns) get ids of the form
  *kind char* + hex of `hash128(key)`, from the `Deduplicator` in
  `crates/typst-svg/src/lib.rs` (`DedupId(char, u128)`).

- A glyph's id does not depend on its fill, which is an attribute of the `<use>` element.
  The letter `A` at 11 pt has one id in black, in red and under a gradient, and another id
  each at 22 pt and in bold. This is what lets a morph match a glyph whose colour changes
  (*Resolved Design Decisions*).

- Equal ids therefore always mean equal content. Browsers resolve `<use xlink:href="#g..">`
  to the first matching id in the document. For a glyph definition that is harmless,
  and it is why stacking frames does not corrupt glyph rendering.
  It is harmless for glyph definitions only, as the next entry of this list says.

- **A gradient, a clip path or a tiling is not drawn when its first definition is in a
  subtree that is not laid out.**
  A reference such as `fill="url(#id)"` resolves to the first element of that id in the
  document, which sits in the earliest slide that defines it, and that slide is `display: none`
  unless it is one of the two slides the runtime lays out.
  Neither chromium 151 nor firefox 153 resolves a reference into a subtree that is not laid
  out, so the fill is dropped and the clip is not applied.
  A `<use>` of a glyph `<symbol>` in the same subtree is drawn, which is why text stays intact
  on a slide that has lost its fills, and why the entry above was first judged harmless,
  because it was measured on glyphs, and on frames that were all displayed.
  Measured on a deck of three slides that each hold the same gradient rectangle and the same
  clipped box, and on a deck of three slides with the gradient background recipe:

  | Position, and how it was reached                  | chromium 151           | firefox 153            |
  | ------------------------------------------------- | ---------------------- | ---------------------- |
  | slide 1, first paint                              | drawn                  | drawn                  |
  | slide 2, step from slide 1 (slide 1 is leaving)   | drawn                  | drawn                  |
  | slide 3, step from slide 2                        | missing                | missing                |
  | slide 3, after a reload                           | missing                | missing                |
  | background recipe, centre pixel of slides 1, 2, 3 | gradient, white, white | gradient, white, white |
  | the same recipe after hoisting the paint servers  | gradient on all three  | gradient on all three  |

  Forcing `display: block` on slide 1 makes slide 3 draw correctly, which shows that the cause
  is the hidden subtree and not the id.
  The slide being left stays `display: block` until the next step, so the same slide is drawn
  after one step and missing after another,
  and a reload by `typst watch` lands in the state where the problem shows.
  A subtree hidden with `visibility` is laid out, so a gradient defined in it resolves.
  A clip path or a tiling defined in it is empty instead, because its children inherit the
  visibility, so the clip hides the whole box and the tile draws nothing.
  Typst writes the definitions of a frame in a `<defs>` that is a child of the frame's root
  `<svg>`, so no group that Animo scopes with `visibility` contains one.

- **Hoisting the definitions into an `<svg>` that is laid out repairs this.**
  A copy of the first element of each id, in a `width="0" height="0"` `<svg>` with
  `position: absolute` that is the first child of `body`, is the first match of every id and
  is laid out, so every slide draws.
  The holder must not be `display: none`, which would make it the first match and drop the
  fill again.
  The runtime builds it once at load, before it reads a slide,
  and removes the ids of the originals, for the reason the next entry of this list gives.
  On a page of sixty slides it took at most 3.4 ms in chromium 151 and 5 ms in firefox 153,
  where firefox rounds its timer to a millisecond.
  Webkit was not run for the table.
  The probe runs in webkit wherever webkit can be launched, which is in continuous integration.

- **In webkit, a definition that stops being laid out drops every reference to its id,
  although the holder still defines the id and is laid out.**
  The references resolve to nothing until a definition of the id is laid out again.
  Chromium 151 and firefox 153 look the id up again and find the holder.
  What was measured fits a single registration per id, which the definition laid out last
  takes over and which is removed when any definition of the id stops being laid out.
  The webkit source was not read to confirm it.
  On a deck of three slides that each hold the same gradient background, gradient rectangle
  and clipped box, with the holder in place and the originals keeping their ids,
  playwright's webkit 26.5 drew slide 1, the step to slide 2, the step to slide 3
  and the step back to slide 2.
  The step back to slide 1 lays slide 1 out and hides slide 3,
  which comes later in the document, and slide 1 then drew neither the gradient nor the clip.
  Every later step drew none of them either.
  A forward step hides a slide that comes earlier than the one it lays out.
  A page with the holder, one laid out duplicate and one reference reproduces it:
  hiding the duplicate drops the gradient, the clip path and the tiling of the reference
  in webkit, and in neither of the other engines.
  Removing the id of the duplicate instead of hiding it drops nothing, before or after the
  duplicate is laid out, so the holder must be the only element that keeps the id.
  With the ids of the originals removed, the deck draws all three on every step of the route.
  Webkit was measured in the `mcr.microsoft.com/playwright/python:v1.62.0-noble` container,
  because no webkit build runs on every contributor's distribution.

- Equal ids also mean that the duplication is pure redundancy,
  so hoisting shared defs into one document-level `<svg>` would be sound.
  The entry after this one describes what came of that.

- **Gzip does not recover that redundancy**, so the redundancy is real on the wire and not
  only in memory. Deflate's window is 32 KiB and no setting raises it, while an epoch frame
  carrying a heading and a single sentence is already 45 KiB, and a frame carrying a whole
  slide is several times that. A definition repeated in the next frame is therefore always
  further back than the window, whatever sits between the two, so it is stored again in
  full. Measured on `examples/tour.typ` as it stood on 2026-09-15: dropping every repeated
  definition takes the page from 1340 KiB to 845 KiB and the gzipped page from 268 KiB to
  145 KiB, a saving of 46% on what is actually transferred.
  Compression and hoisting are therefore worth a factor of five and a further factor of two,
  and neither substitutes for the other.
  The deck has grown since the same measurement was first taken,
  when it came to 44% of a 222 KiB page,
  so the fraction remains valid rather than the absolute sizes.

## Hoisting shared `<defs>`: sound in the browser, out of reach in typst

This entry is the other half of the entry above,
measured when the optimisation was about to be built.
The mechanism works, but the markup is out of reach,
so the saving a deck actually gets is decided by a third fact,
which is the scope of typst's deduplicator.

- **A `<use>` resolves a definition that lives in an earlier inline `<svg>`.** Measured on
  real output rather than on handwritten markup: two stacked frames of one paragraph, the
  second of them the one that is shown, with every repeated definition dropped from the
  page. The raster is identical to the page that carried the repeats, in chromium 151 and
  firefox 153, so the frame that lost its definitions is drawing out of the frame above it.
  Webkit runs the same probe where it can be launched, which is continuous integration
  and the platforms that carry its libraries.

- **A package never holds the markup a frame became.** `html.frame` has one field, `body`,
  and its value is content.
  The SVG is produced when the document is encoded, by
  `write_frame` in `crates/typst-html/src/encode.rs`, which calls `typst_svg::svg_in_html`
  once per frame, each call with a separate `Deduplicator`. The `html` module holds `elem`,
  `frame` and the tag helpers, and nothing that writes markup, while a text node is escaped,
  so markup cannot be handed in as a string either. The raw-text exceptions are `<style>`
  and `<script>`, which is how Animo's stylesheet and runtime reach the page and is no help
  here, because a definition has to be an SVG element.
  A second compile does not help either,
  because `read()` can take the first pass's HTML back in, but nothing can emit it.
  The document-level `<svg>` therefore cannot be written from inside typst 0.15.0,
  whatever it would be worth.

- **The deduplicator's scope is the frame, not the rendering, and that is reachable.**
  Three renderings of one paragraph in three frames define every glyph three times.
  The same three renderings `#place`d at one point in *one* frame define each glyph once,
  with the same number of `<use>` references, and take the page from 139 KB to 71 KB.
  Each rendering is still a
  labelled group when it is a labelled `box`, so `visibility` scopes one away exactly as a
  frame is scoped away, and `mix-blend-mode: plus-lighter` on two of them at half opacity
  each sums to one opaque rendering.
  The blend works on these groups because they are the outermost groups of one `<svg>`,
  which a region's group is not (see *Crossfading epoch frames*).
  This is what Animo does.

- **What each scope is worth**, measured on 2026-09-15 on this repository's two decks, the
  second of them at twelve slides of three epochs with an overlay carrying a number:

  | Deck    | Page     | Gzipped | One frame per slide | Every repeat dropped |
  | ------- | -------- | ------- | ------------------- | -------------------- |
  | tour    | 1340 KiB | 268 KiB | 245 KiB, 8%         | 145 KiB, 46%         |
  | scaling | 3476 KiB | 639 KiB | 365 KiB, 43%        | 176 KiB, 72%         |

  The last two columns are far apart on the tour and much closer on the controlled deck.
  The reason is the shape of the decks rather than a property of either scope.
  The tour mostly has one epoch per slide, so nearly all of its duplication is across slides,
  where a frame per slide cannot reach it.
  A deck with several epochs a slide is the one the reachable scope is for,
  and it is also the deck the raw figure matters on, since the raw page is what the browser
  holds. `benchmarks/run.py` records both projections, as `hoisted_*` and `merged_*`.

  Animo implemented the reachable scope on 2026-09-15,
  and the result matched the projected column.
  The tour went from
  1340 KiB and 268 KiB gzipped to 1231 KiB and 245 KiB, which is the projection to the
  byte, and its frames from 19 to 15, one per slide. On the controlled deck, with both arms
  compiled from one working tree so that only the merge differs,
  the saving grows with the number of epochs per slide,
  because that is the duplication the merge removes.
  The gzipped page stays at 180 KiB at one epoch per slide,
  and goes from 345 to 220 KiB at two, 673 to 297 at four, and 1328 to 445 at eight.
  `merged_*` therefore now equals the page itself,
  and `merging_saves_gzipped` is zero on every variant.
  A reading that is not zero means that the epochs of a slide ended up in separate frames
  again.

## CSS animation of typst SVG groups

Measured in chromium on real typst output, on a labelled group that carries this typst
`transform="translate(0 28.346456693)"`:

| Applied CSS                                                         | Result                                                                          |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `opacity: 0.35`                                                     | works; typst emits no group-level opacity or style, so opacity is entirely free |
| `translate: 50px 0`                                                 | composes, so the element moves and typst's `transform` attribute stays intact   |
| `transform: translate(50px,0)`                                      | **clobbers** typst's translate (y jumped 49.2 → 8.0, losing the offset)         |
| `scale: 2` (default `transform-box: view-box`)                      | scales about the SVG viewBox origin, displacing the element (y 49.2 → 90.5)     |
| `scale: 2` + `transform-box: fill-box` + `transform-origin: center` | scales about the centre of the element, in place                                |
| all three together                                                  | compose correctly                                                               |
| `transform-box: fill-box` + `transform-origin: center`, alone       | **displaces** a group that carries a `matrix(1 0 0 -1 ..)` written by typst     |

Mid-flight interpolation, sampled deterministically through the Web Animations API,
confirms genuine smoothness and that the transform typst writes survives the animation:

```
t=0.00  x=8.0   w=82.5   opacity=0
t=0.50  x=23.8  w=123.7  opacity=0.5
t=1.00  x=39.5  w=164.9  opacity=1
typst transform attr survived animation: translate(0 28.346456693)
```

The last row of the table is a trap, and it was found while writing a deck rather than by a
probe.
`transform-box` and `transform-origin` do not apply only to the CSS transform properties.
They set the reference frame of the element's whole transform,
including the `transform` attribute that typst wrote on it.
A translate does not depend on an origin and is unaffected,
which is why the two declarations look harmless.
A reflection does depend on the origin,
and typst writes `matrix(1 0 0 -1 x y)` on every glyph run it emits.
Wherever the two declarations land on a group that typst positioned,
that group's content therefore moves by twice the distance from the group's origin to the
centre of its fill box. Nothing errors, no transform property is set at all,
and the displacement differs per run, because each run has a different fill box.

Consequently, Animo uses the individual `translate`/`scale` properties
and never the `transform` shorthand.
It sets `transform-box: fill-box` for scaling, and only on an element that Animo built as a
slot.
A stray `transform` in user CSS will silently break positioning, and so will a
stylesheet rule broad enough to reach a group typst positioned.

Firefox 153 agrees on every row of the table, including that `fill-box` is what makes a
scale happen in place.
Firefox resolves the fill box itself slightly differently.
The centre it scales about sits about **0.7 CSS pixels** from the centre that `getBBox`
reports, so doubling an 11-pixel line moves the line by that much,
while chromium moves it by under a tenth of a pixel.
That is invisible in a transition, and it is why the probe for this row allows a
pixel rather than half of one.

CSS lengths inside a group are in **user units (pt), scaled by the SVG's rendered size**.
At the test slide scale, 50 user units measure 72.7 px.
A move expressed in typst lengths therefore stays the same fraction of the slide
at any screen size, for free.

Two further measurements, on chromium 151 and firefox 153, answer what a transform *looks*
like rather than where it lands:

- **A scaled glyph is drawn afresh, not stretched.** The antialiasing band around the ink of a
  line of text, per unit of ink, is 0.20 at scale 1, 0.10 at scale 2 and 0.05 at scale 4.
  The ink grows with the square of the factor, while the edge grows with the factor,
  which is the signature of a glyph outline rasterised at the size it ends up at.
  A picture of the glyph, stretched, would keep the ratio constant.
  Both engines agree to a hundredth.
  Text under a `scale` therefore stays as sharp as text at its unscaled size,
  and strokes scale geometrically with it.
- **A value under a running animation rasterises as the same value in a style declaration**,
  bit for bit, over a whole 1280 by 720 window.
  This makes the end of a transition invisible.
  A step writes its display state as inline style and animates from the old values to it.
  At the end, the animation stops applying and the style takes over,
  and nothing about the picture changes at that moment.
  This was measured with an animation that holds one value from beginning to end,
  so that nothing but the path through the engine differs.

## A keyframe property that does not change suppresses the ones that do

Measured on chromium 151, firefox 153 and playwright's webkit 26.5, on a deck whose reveal
refused to fade.

An effect that animates `opacity` from 0 to 1 alongside a `translate` or a `scale` that is
equal at both ends is not drawn while it runs in chromium. The element stays exactly as it
was for the whole duration and appears in one frame at the end, when the animation is removed
and the style underneath it takes over. Firefox and webkit draw every row below.

| Keyframes of one effect                         | Drawn while running |
| ----------------------------------------------- | ------------------- |
| `opacity` alone                                 | yes                 |
| `opacity` with a `translate` equal at both ends | no                  |
| `opacity` with a `scale` equal at both ends     | no                  |
| `opacity` with a `translate` that changes       | yes                 |
| `opacity` with a `scale` that changes           | yes                 |

Nothing in the DOM shows the problem.
Every value the animation computes is correct at every moment,
and `getComputedStyle` interpolates exactly as it should,
so the state model and every assertion about it are unaffected, and only the drawing is missing.
Anything that makes the page draw brings the drawing back,
including a `requestAnimationFrame` loop and a screenshot.
`page.screenshot` and `Page.captureScreenshot` therefore cannot see the problem at all,
while a recorded video can.
That is also what makes it look like a timing or engine problem rather than a keyframe problem.

Animo therefore animates only the properties that a step changes.

## The document timeline is not a clock

Measured on chromium 151, firefox 153 and playwright's webkit 26.5, while making a step
animate after a pause.

`document.timeline.currentTime` is the time of the last frame the browser drew, and a browser
with nothing to draw draws nothing.
Read inside a key handler, firefox reports a time 442 ms old after a 250 ms pause,
and 3181 ms old after a 3 s pause, which is the pause itself.
Chromium refreshes the time on a read from outside a frame,
and never lags by more than one frame.
Webkit reads a lag of exactly zero, after a 3 s pause as much as after a 500 ms one.
A timeline that stands still between frames is what the specification describes,
since it says the time is updated once per frame.
Firefox therefore follows the specification, and the other two engines are the exception.

Giving that time to an animation as its `startTime` therefore starts the animation as far
into its duration as the page stood still. With a step of 400 ms, anything longer than
that is over before it is first drawn. What a presenter sees is a deck that animates while it
is being clicked through and jumps whenever a slide has been talked over first.

None of this is visible until a frame is drawn, because an animation measures its current
time against the same timeline.
Immediately after being given a start time, it reports zero,
and only the next frame shows where it really is.
A test that reads any sooner sees nothing wrong.

The runtime therefore sets no start time at all.
Animations created in one task are pending until the next frame,
and are then all started with that frame's time.
That gives the step a shared clock without setting a start time explicitly.

## A delayed effect does not hold its first keyframe unless it is told to

Measured on chromium 151 and firefox 153, while making one operation of a step arrive late.

An effect with a delay has a phase before it runs, and what the element shows during that
phase is decided by the fill mode alone.
Measured on an element whose own style says `opacity: 1`,
animating from `0` to `1` over 1000 ms after a delay of 500 ms,
read a quarter of the way into the delay:

| Fill mode   | Computed opacity during the delay |
| ----------- | --------------------------------- |
| `none`      | `1`, which is the element's style |
| `backwards` | `0`, the first keyframe           |
| `both`      | `0`, the first keyframe           |

Both engines agree, and the values are the two ends of the animation,
so neither answer can be arrived at by accident.

This makes `fill: none` wrong for a runtime that writes the state it is arriving at
as inline style before it creates the animation.
Animo writes the state first, so that the inline style is the state
and the animation is only how the element gets there.
With `fill: none`, the element would jump to the state the step is going to reach,
wait there for the delay, and then jump back to the start to animate forwards.

`fill: backwards` can be written on every effect and not only on the delayed ones,
because an effect that fills backwards is not in effect once it has finished,
so its animation leaves `document.getAnimations()` exactly as one that fills nothing does.
That is what keeps "is anything still in flight" a question the page can answer.

## A faked clock drives a timer without touching the document timeline

Measured with playwright 1.62 on chromium 151 and firefox 153,
while making a deck that plays itself testable.

A `wait:` is a `setTimeout` in the runtime, and a `setTimeout` is exactly what the browser
harness cannot scrub.
An animation can be paused and told where it is, while a timer can only fire.
The clock that Playwright installs drives a timer instead, and leaves the motion alone.

- **Installed and then paused, the clock stops.**
  `clock.install()` alone leaves timers firing in real time.
  `clock.pause_at(..)` after it stops them,
  and a page left alone for 1.3 s then fires none of its 1 s timers.
- **A timer of zero length gets past the pause while the page is loading.** On a page
  reached by navigation, a `setTimeout(.., 0)` armed by a script in the document fires
  within a few hundred milliseconds of real time although the clock is stopped,
  while the same page's timers of 1 ms, 5 ms and 1 s do not,
  and neither does a zero-length timer armed once the page has settled.
  The same page loaded with `set_content` holds all four.
  A test may therefore reach the far side of a zero-length gap,
  but may not expect such a gap to stay pending.
  On a loaded machine, a key pressed soon after the deck is opened lands inside that window,
  which makes the test flaky rather than wrong. A timing test states
  where the deck rests and drives it there with `run_for`.
- **`run_for` follows a chain of timers**, including the ones a fired timer sets, which is
  the shape autoplay has.
  `fast_forward` does not, because it fires each due timer at most once,
  so a page that arms its next timer as it steps advances exactly one place,
  however far the clock is jumped.
- **The document timeline is not faked.** An animation created while the clock stands
  still reports 17 ms after the clock is moved ten seconds, and 383 ms (chromium) or
  416 ms (firefox) after 400 ms of real time have passed.
  The motion of a timed step is therefore real motion, and is still read by scrubbing it.
- **`requestAnimationFrame` is faked along with the timers**, and stops firing while the
  clock is paused, so a frame cannot be waited for on such a page.
  The Playwright methods `wait_for_function` and `wait_for_timeout` are unaffected,
  because neither runs on the clock of the page.

## Styling from CSS: what is and is not reachable

Measured on a labelled group whose glyphs carry typst's `fill="#000000"` presentation
attributes:

- A rule on the group's **descendants** wins without `!important`:
  `[data-typst-label="x"] use { fill: rgb(0,128,0) }` gives a computed fill of
  `rgb(0, 128, 0)`. Any CSS declaration outranks a presentation attribute.
- A rule on the **group itself** does not reach the glyphs: the computed fill stays
  `rgb(0, 0, 0)`, because the presentation attribute on the glyphs beats an inherited value.
- `fill` interpolates smoothly: driving it with a paused Web Animations API animation gives
  `rgb(128, 0, 0)` at the midpoint of a black-to-red transition.

A colour-only primitive is therefore possible, and must target descendants explicitly.
Anything beyond fill (weight, size, spacing, strokes, images) is out of reach of CSS,
and has to go through a re-rendered epoch.
This puts `apply` in the structural class, and leaves a colour-only primitive for a later
release.

## Cross-frame geometry is readable, so morphing is possible

With two epoch frames in the DOM and both laid out, a label that moves because of reflow
*inside* a region reports both of its geometries to JavaScript: `x=39.49` in the outgoing
frame and `x=523.87` in the incoming one, at identical size. A FLIP-style morph between epochs
is therefore implementable without any help from typst.

Two transform slots are therefore needed, since CSS gives each element only one `translate` and
one `scale`, and nesting supplies the second. `#box(box[Hello world])#label("outer")` emits
`<g transform="translate(..)" data-typst-label="outer"><g>`: the inner group carries **no**
transform. A single `#box[..]` instead emits `<g label><g transform="matrix(..)">`,
whose child is content-dependent and therefore not a slot to rely on.
`tag` therefore wraps its body in a nested box,
which makes `[data-typst-label="x"] > g` a reliable second slot.

**How that geometry is read matters.** `getBoundingClientRect()` on a labelled group
gives the tight box in chromium 151 and a box inflated to roughly the width of the whole
frame in firefox 153, which paints its ink outside the viewBox because typst writes
`overflow: visible` on the `<svg>`. On the same group chromium reported `19.57 x 13.86`
and firefox `358 x 13.90`.
What both engines agree on exactly is `getBBox()`,
in the user units of the group, which are typst points.
Mapping its corners through `getScreenCTM()` puts it back in CSS pixels,
and the two engines then agree to **0.02 CSS pixels** on an untransformed group,
and to **0.7** on one under a CSS scale.
A FLIP morph, and every test that reads a tag's geometry,
therefore uses `getBBox` and the CTM, and never `getBoundingClientRect`.

The measurement decides which slot takes which class of animation.
A FLIP delta is read in the frame's coordinates,
so it must be applied above anything that already transforms the element.
The labelled outer group is the boundary slot, and the inner group is the continuous one
(*Architecture* rule 4).
The alternative leaves both classes on the labelled group and composes them numerically.
It also works, but it obliges the runtime to know the current value of every continuous
property in both frames before it can write a FLIP transform,
which is state the stacked-frame design otherwise never has to keep.

## A morph keeps the `plus-lighter` sum

Measured on two renderings of one frame summed under `plus-lighter`, as a crossfade sums them:
`Hello world` and `Oh, Hello world` at 30 pt, whose ten shared letters are 51.3 pt apart.
The outgoing copy of each shared letter is translated from its place to the place of the
incoming copy, and the incoming copy from the outgoing place to its place, while the outgoing
rendering fades out and the incoming one in, all with one linear timing.
The reference is one opaque copy of each letter at the same point of the route.

| Engine       | Largest difference at 0, 25, 50, 75 and 100 % | Ink pixels above 2/255 at 50 % |
| ------------ | --------------------------------------------- | ------------------------------ |
| chromium 151 | 0, 1, 1, 1, 0                                 | 0 of 2015                      |
| firefox 153  | 10, 8, 6, 8, 0                                | 75 of 1924                     |
| webkit 26.5  | 0, 21, 59, 1, 0                               | 10 of 1944                     |

The differences are out of 255.
The morph therefore needs no change of the blend, no clone of an element and no opacity of its
own.
A plain opacity crossfade of the same pair, without `plus-lighter`, differs by more than
32/255.

**The firefox difference does not come from the sum.**
It is present at the start of the step, where only the outgoing copy is visible,
and also with no animation at all.
One letter at one position on the screen rasterises differently in firefox 153
when it reaches that position through a CSS `translate` than through its `x` attribute,
by 10/255 on 184 of 1909 ink pixels.
The same comparison on a deck scaled to a 1280 pixel window gave 22/255.
A morph shows the outgoing copy reached one way and the incoming copy the other,
and the difference is gone at the end of the step, where only the incoming copy is left at
its place.
`will-change: transform` and `will-change: translate` on the letters leave the difference
unchanged.
Webkit 26.5 draws the two placements alike. Chromium 151 does on some loads of the page and
differs by 50/255 on a dozen pixels on others.

**The webkit difference** is on the antialiased corners of a letter's stem, at the edge of the
letter's box, on no more than a dozen pixels, while the two copies are moving. It was not
traced further.

**`getScreenCTM()` includes the `translate` of the element itself.**
This holds in all three engines, on a `<use>` and on a `<g>`,
for an inline `translate` and for an animated one,
and in a rendering that is `visibility: hidden`.
The morph reads the displayed place of an outgoing element through `getScreenCTM()`,
and subtracts the running morph translations to find where an incoming element is laid out.

**A stroke and a raster image sum like a letter.**
The same comparison on a rectangle with a 1.5 pt stroke and no fill, and on a raster image of
30 by 15 pixels drawn at 60 pt wide, each moved by 127.3 pt and 31.7 pt so that both copies are
resampled on the way, at the midpoint of the step:

| Engine       | Stroke, largest difference and pixels above 2/255 | Image, the same  |
| ------------ | ------------------------------------------------- | ---------------- |
| chromium 151 | 1/255, 0 of 785                                   | 2/255, 0 of 3945 |
| firefox 153  | 1/255, 0 of 744                                   | 2/255, 0 of 3741 |
| webkit 26.5  | 1/255, 0 of 744                                   | 1/255, 0 of 3741 |

The antialiasing along both edges of a stroke and the smoothing of a resampled image do not
show in the sum, so a morph of a shape or an image needs nothing a morph of a letter does not.

## Typst writes a shape from a local origin

This entry records what a morph compares when it pairs two shapes or two images,
in the SVG that typst 0.15.0 writes for an `html.frame`.

- Every shape is a `<path>` whose `d` starts at `M 0 0`, and its place is a
  `transform="translate(..)"` on the path or on a group around it.
  Two copies of a shape at two places therefore have one `d`, as two copies of a letter have
  one `href`.
  A rectangle is `M 0 0v 28.35h 28.35v -28.35Z`, a circle four relative cubic Béziers after an
  `m` that end at its start without a `Z`, a line `M 0 0h 28.35`, and a regular polygon an `m`
  followed by `l` and `h` segments.
- The bar of a fraction is a stroked path `M 0 0h 5.819` beside the glyphs of the fraction,
  so a numerator that grows gives the bar another `d`.
- The paint is in attributes beside the `d`: `fill`, `fill-rule`, `stroke`, `stroke-width`,
  `stroke-linecap`, `stroke-linejoin` and `stroke-miterlimit`.
  Recolouring a shape changes `fill` or `stroke` and leaves the `d` alone.
  The `fill-rule` of the shapes that typst writes is `nonzero`, and a `curve` with
  `fill-rule: "even-odd"` writes `evenodd`.
- An image is an `<image xlink:href="data:image/png;base64,.." width=".." height=".." preserveAspectRatio="none"/>` without `x` and `y`, so its place is the transform above it.
- A clipped box is a `<g transform="translate(..)" clip-path="url(#c..)">` that holds what it
  clips, and the `<path>` of the clip path is in the user space of that group.
- A gradient fill is `fill="url(#r..)"`, a `linearGradient` in `userSpaceOnUse` whose
  `gradientTransform` scales it to the size of the shape.

## The `d` of a path interpolates between paths of one structure

Measured by animating the CSS `d` property of one path from its data to that of another
with the Web Animations API, on the paths typst 0.15.0 writes, paused at fixed moments.

- **Support.** `CSS.supports('d', 'path("M 0 0")')` is true in chromium 151 and firefox 153
  and false in webkit 26.5. Webkit ignores a `d` keyframe without an error,
  `getComputedStyle(path).d` is `undefined` there, and a `stroke-width` beside it still
  animates.
- **Same commands.** Two paths with the same command letters in the same order interpolate
  number by number, with the relative commands typst writes as they are, and a relative path
  against an absolute one of the same commands as well. Mid-flight both engines compute an
  absolute path, and at rest chromium computes the absolute form while firefox keeps the
  letters of the attribute.
  The rounded rectangle typst writes starts with `m 0 r`, and at a quarter of the step from
  a radius of 2 to one of 8 that pair is `0 3.5`.
- **Different commands.** A rectangle against a rectangle with rounded corners shows the
  first path until the middle of the step and the second after it.
- **Structure in typst's output.** Typst leaves out a segment of zero length, so a rounded
  rectangle whose straight sides have no length, a pill or a rounded square of half its size
  as radius, has fewer commands than one whose sides have a length, and a rectangle of zero
  width has no `h`. A rectangle without rounded corners runs `v h v Z` from its corner, and
  one with rounded corners starts on its left side with `m 0 r` and runs the other way round.
  A filled shape with a stroke on only some sides writes its fill as another sequence.
  A shape with a fill and a stroke and rounded corners is written as two paths,
  a fill whose radius is inset by half the stroke width and an open stroke path that starts
  on its top side.
- **Geometry.** `getBBox()` follows the animated `d`: the box of a rectangle halfway from
  20 × 10 to 40 × 30 is 30 × 20.
- **The sum.** Two copies of a rounded rectangle that resize together from one geometry to
  another, while one travels from its place to the other's and the other comes the opposite
  way, under `plus-lighter` and a crossfade, differ from one opaque copy with the geometry
  and the place they show by at most 2/255 at the midpoint, in chromium and firefox.

A resize is therefore possible exactly for the paths whose commands agree,
and needs no rewriting of a path in the two engines that animate `d`.

## A `translate` carries an element's clip and gradient, not an ancestor's clip

Measured by moving one element of a frame by a whole number of CSS pixels with a CSS
`translate` and comparing what is drawn at the new place with what was drawn at the old one,
with the paint servers and clip paths moved into another `<svg>`, as the runtime hoists them.
The results are the same in chromium 151, firefox 153 and webkit 26.5.

- **A group carries the clip of its content.** A clipped box translated on the group that holds its
  `clip-path` arrives with the same edges, to within 2/255. The clip path is in the group's
  user space, and the `translate` changes that space.
- **A clip above the moved element stays where it is.** Translating what a clipped box holds,
  and not the box, moves the content out of the clip, which hides the part that has left it.
  The same content drawn without the clip does reach below it.
- **A gradient moves with its shape.** A rectangle with a gradient fill translated on its own
  `<path>` arrives with the same colours, to within 2/255, also when the gradient is defined
  in another `<svg>`. `userSpaceOnUse` is the user space of the element that references the
  gradient, which the `translate` moves.

A morph therefore moves a shape together with its gradient,
and a tag together with the clips inside it.
A match whose two elements sit under clips at two places
would be cut off at an edge that its partner does not have.

## `hide()` cannot be undone in the browser

Typst's `hide()` lays content out but emits **nothing** to draw: the labelled group is
present but empty (0 glyphs versus 9 for the visible equivalent).
CSS can therefore never reveal it.
In the HTML output, initially-hidden elements must be rendered normally
and hidden with CSS `opacity: 0`.
Only the paged outputs may use `hide()`.

`remove` and the removed initial state behave differently, because they are a *content state*.
A content state is resolved by typst when the epoch is rendered,
so it needs no browser support and cannot be undone within an epoch.
Undoing it starts a new epoch by construction.

## A counter reads the same everywhere a slide lays content out

Measured on typst 0.15.0, in both targets.

A counter read with `get()` gives the same value inside an `html.frame` as outside one,
because a frame is a container and not a document,
so nothing about a counter is reset at its edge. `final()`
resolves in the HTML target as well, inside a frame included, and it resolves before the counter
reaches its last value, which is the position a slide reads it from.

A slide number can therefore be a plain counter.
Its value is the same in every rendering of its slide,
so it needs no view, no provider and no entry in the plan.
It also reads the same in a slide's body as in a background or an overlay,
which in the HTML target are three separate frames.

A counter read *inside* `measure` resolves at the enclosing context's location, which is the
same rule *Providing a value down the tree* records for a state.
For a slide number, that is what is wanted, since the value is constant over the slide.
It is also exactly why a value that has to vary per epoch cannot be carried this way.

## A panic that depends on `query` can be swallowed

Measured on typst 0.15.0, while building a check that two sites of one tag name agree.

A value read with `query` is read once per introspection pass, so a check on such a value
is a check on one pass and not on the document. If that check panics, the panic may never
be reported.
The pass that panics produces nothing, so the next pass queries a different document and does
not panic, and the two alternate until the iteration limit.
What surfaces is `document did not converge within five attempts` plus a warning that an
element count did not stabilise, pointing at the `query` and saying nothing about the
panic. The compilation succeeds.

A panic in a document that *does* converge is reported normally, so this is not about
panics inside `context` blocks in general.
It is about panics whose own effect changes what the next pass sees,
which applies to every check on content that Animo itself emits.

**A check placed apart from what it checks is reported.**
The next pass succeeds because the panic empties the block it is raised in.
A check in a separate context block, emitting nothing
that it reads, changes nothing by failing, and typst keeps only the errors of the pass it ends
on (`crates/typst/src/lib.rs`, where a pass's diagnostics are kept only when it is the last).
A value that is missing in an early pass is therefore forgotten,
and one that is missing for good fails the last pass and is reported normally,
with no convergence warning.

A guard that merely waits for a marker from a separate block is not enough
when the check sits in the block that holds what it checks.
Such a guard was tried first.
A tag nested inside another tag is reported a pass after the marker of the slide,
so the check failed in that pass, the panic emptied the slide,
and the site could never appear again, so a valid deck was refused.
Measured on Animo's refusal of a `pan(relto:)` to a tag the slide does not have, in the HTML
target and in both paged modes, on the second slide of a three-slide deck, and on a nested tag,
and on its refusal of an anchor read from inside a tag the timeline moves or scales, which reads
a nested site the same way.
It was first measured while trying to build a refusal of two sites of one name that disagreed
about a `hidden:` argument of `tag`. Animo no longer has that argument, nor that check, because
a tag's initial state is read from its timeline.
A diagnostic that depends on `query` is therefore either a value that Animo resolves,
or a refusal raised in a block that emits nothing it reads.

## Introspection: positions

- In **paged** output, positions are available and useful: `query(<tag>)` plus
  `location().position()` returns real coordinates, including for tagged content **inside
  math**.
  The position of an element is not always its corner, though,
  which is why `pan(relto:)` reads a marker instead (see the next entry).
- In **HTML** output, positions cannot be read:
  `here().position()` and `location().position()` return `(page: 1, x: 0pt, y: 0pt)`,
  *even inside `html.frame`*.
  This was verified geometrically by driving a rectangle's width from `here().position().y`,
  which came out zero-width against a 1 cm control. `query` itself does see inside frames.
- `measure()` **does** work in HTML output and returns real sizes, in paged layout (above).

The HTML output therefore cannot rely on typst coordinates at all.
It relies on the layout that the browser makes of the frame SVG,
which is why per-element animation is done with CSS rather than with typst-computed offsets,
and why regions are sized by `measure` rather than placed by coordinates.

## Introspection: the corner of an element, in both targets

Measured on typst 0.15.0, chromium 151 and firefox 153,
while resolving `pan(relto:)`, which needs the
top-left corner of a tag's wrapper in both targets.

- **A box on a line is located at the line's baseline, not at its corner.** Typst's inline layout
  (`crates/typst-layout/src/inline/line.rs`, `Item::Tag`) records an element as a zero-size frame
  on the baseline, so `location().position()` of a labelled box in a paragraph, in math or in a
  list item is one box height below its corner: 7.24 pt for a phrase, 12 pt for a 12 pt box,
  7.51 pt for `$y^2$`. It holds in the middle of a line, at the start of a paragraph and at the
  start of the page flow alike. The same box as the only content of a `place` is located at its
  corner.
  The position of an element therefore does not say where the element starts.
  No correction by its height recovers the corner either,
  since whether a correction applies depends on what the box sits in.
- **A marker placed at `top + left` inside the box is located at the box's corner**, wherever the
  box sits, and at a negative coordinate when its container is off the page.
  The marker takes no room,
  because a page rasterises identically with and without such markers at 144 ppi.
- **That corner is the origin of the box's labelled group** in the SVG of an `html.frame`, as
  `group.ownerSVGElement.getScreenCTM().inverse().multiply(group.getScreenCTM())` reads it, to
  0.01 pt in both engines. The group's bounding box is the extent of its ink instead, which is
  a different rectangle.

Animo therefore reads a `relto` anchor from such a marker on paper and from the group's origin
in the browser, and the two agree (see *Resolved Design Decisions*).

## Media elements in the HTML output

Measured in chromium on real typst HTML output, for a narration feature that a later release
could add.

- `html.elem("audio", ..)` works as a **sibling of `html.frame`** inside the slide container. It
  must be wrapped in a block-level element, for which a `div` with `display: contents`
  suffices, because `audio` is phrasing content and typst otherwise wraps it in a `<p>`.
- A clip embedded as a `data:` URI decodes fully: `readyState = 4` and `duration = 8.0065s` for an
  8 s Opus file, matching the source exactly.
  The browser can therefore supply the timing that typst cannot.
- **Autoplay of audible media is blocked until a user gesture**: `play()` rejects with
  `NotAllowedError: play() failed because the user didn't interact with the document`. A
  self-playing deck therefore needs one click to start, which a presentation has anyway.
- **Typst exposes no base64 to scripts.** `to_base64_url` exists only on the Rust side, for images
  (`crates/typst-svg/src/image.rs`), so embedding requires an encoder written in typst.
  Writing such an encoder has two traps:
  - `while` is capped at 10 000 iterations (`MAX_ITERATIONS`, `crates/typst-eval/src/flow.rs`), so
    the loop must be a `for` over a `range`.
  - The natural implementation, one array element per output character, costs about 119 MB of RSS
    per MB of input. Joining in blocks of a few thousand characters keeps memory flat: 4 MB encoded
    in 8.37 s at 46 MB RSS, i.e. **~2.1 s/MB, linear in size and constant in memory**.
- **The encoding is memoised across recompiles.** Under `typst watch`, a 4 MB payload cost 8.11 s
  on the first compile and 6.6 / 11.2 / 18.8 ms on the next three,
  including edits that shift every span in the file.
  The cost is per watch session and per cold compile, not per edit,
  which is what makes embedding-by-default tolerable while authoring.

## Live preview: typst serves and reloads the HTML itself

`typst watch` with HTML output starts a small HTTP server and injects a live-reload script into
the response it serves. Verified against the typst 0.15.0 binary and the checkout
(`crates/typst-kit/src/server.rs`):

- the flags are `--port` (default: the first free port in the range 3000-3005), `--no-serve` and
  `--no-reload`;

- the injected script is a single line, placed before `</body>` of the *served* response only, so
  the file written to disk never contains it:

  ```js
  new EventSource("/__events").addEventListener("reload", () => location.reload())
  ```

- the document is served from memory, and every successful recompile pushes a `reload` event to
  all connected browsers.

Because the reload is a plain `location.reload()`, the URL survives it, fragment included. A deck
whose subslide state lives in `location.hash` therefore comes back on the same subslide after
every recompile.
The built-in server is therefore sufficient for authoring,
which is why Animo ships no reload machinery.

## Wrapping a tag site: what it changes and what it does not

A page was rasterised at 144 ppi with and without a wrapper around one element, at 11 pt text,
and the rasters compared pixel by pixel.

| Tagged body                 | `box(box(x))` | `block(block(x))` | `block(width: 100%)`, twice |
| --------------------------- | ------------- | ----------------- | --------------------------- |
| markup list, grid, table    | identical     | identical         | identical                   |
| a paragraph that wraps      | identical     | identical         | identical                   |
| `figure`, `$ .. $`, `align` | left-aligned  | left-aligned      | identical                   |
| `= Heading`                 | shifts        | shifts            | shifts                      |

For content that already sits between paragraph breaks, a `box` and a `block` render
**identically**.
What decides the rendering is whether the wrapper hugs or fills,
rather than whether it is inline or block.
A wrapper at `width: auto` hugs, which left-aligns anything the container was centring,
and `block(width: 100%)` reproduces the original.

A `heading` shifts under *every* wrapper, by about 5 pt.
A heading carries block spacing above and below it
(1.8em above and 0.75em below at level 1, `typst-library/src/model/heading.rs`).
With a wrapper, that spacing sits at the wrapper's edge and is trimmed there,
and the wrapper contributes the generic 1.2em instead.
Neither `heading.above` nor `block.spacing` is readable from a `context` block, while
`text.size`, `par.spacing` and `heading.numbering` are, so Animo cannot copy the value it would
have to restore.
Tagging the heading's text rather than the heading is the way around this, and it is exact.
`= #tag("t")[A heading]` rasterises identically to `= A heading` at 144 ppi,
with zero pixels differing over the page.
The wrapper is then inside the heading, so nothing sits at the edge where the spacing lives.

A tagged inline phrase stops breaking across lines, so its paragraph can reflow.
This effect is inherent, because a group that CSS can translate cannot be split over two lines.

## Inline versus block, decided by measurement

```typ
let nothing = box(width: 0pt, height: 0pt)
let is-block = measure([#nothing#body#nothing]).height > measure(body).height
```

Block-level content pushes the two neighbours onto separate lines,
while inline content does not.
Over 31 constructs the separation was **exactly 0.0 pt** for every inline case and **at least
12 pt** for every block-level one, so the comparison needs no tolerance.
It needs no available width either,
because an unbounded `measure` resolves a `100%` width to zero rather than to infinity,
and every verdict was the same as with a width given.

The measurement sees what inspection cannot.
A `context` block reports the block-ness of whatever it produces.
The one blind spot of the measurement is content that is itself several paragraphs,
which measures as inline because the neighbours merge into the first and the last paragraph
instead of being pushed off.
A scan for a `parbreak` in the sequence of the body covers that case.

Inspection was recorded as well, because it is what a reader expects to reach for first:

- a markup list or enum is a **`sequence` of `item`**, not a `list`; `list.item`, `enum.item` and
  `terms.item` all report as `item`;
- `#text(red)[..]` and a `#set` block are both `styled`, with the real element at `.child`;
- `image`, `rect`, `circle`, `line`, `stack`, `grid`, `columns`, `place`, and also `move`, `scale`
  and `layout`, are block-level;
- `box`, `hide`, `footnote`, `metadata`, inline math and inline raw are inline;
- `context` has no fields at all, so inspection stops there.

The set of element functions is closed, because a package cannot define one, but it is only
closed per typst release and it does not cover `context`. That is why Animo measures.

## Providing a value down the tree: a show rule reaches into `measure`, a state does not

`state.get()` inside `measure(..)` resolves at the location of the **enclosing** context block,
not at a position inside the measured content. A caller therefore cannot set a state, measure,
set it again and measure again, because both measurements see the same value.
A state is therefore ruled out as the channel for anything a region varies while it sizes its
footprint.

A marker plus a show rule does work:

```typ
#let ask(f) = context [#metadata(f)<animo-ask>]
#let provide(value, body) = {
  show <animo-ask>: it => (it.value)(value)
  body
}
```

As measured, two `measure` calls in one context block, with different values provided,
give different results. Providers nest and the innermost wins. The rule fires on a marker produced
inside a `context` block, and on a marker inside the content that another marker produced, so
tags may be nested.
The label of the marker does not leak,
so a tag built this way emits exactly one `data-typst-label`, which is the label of the tag.

The mechanism also works where a region needs it.
A region that receives its body as opaque content and
measures it inside `layout(size => ..)` once per epoch, providing a copy of the view with only the
epoch changed, gets a different height per epoch (27.68, 56.45 and 27.68 pt for a short line, a
wrapping replacement and a short line again) and one footprint in all three renderings.
The tags in the body resolve their content behind nested `context` reads,
including a tag inside a tag, a tag removed in one epoch and a region inside a region,
in the paged and the HTML target alike, with no convergence warning in either.

The channel is also **layout-neutral to the pixel**, which is what lets a tag that emits no
wrapper hand its body back untouched. A body routed through `context`, `metadata` and the show
rule, with no wrapper around it, rasterises identically to the bare body at 144 ppi,
with zero pixels differing.
This was measured with a heading between two paragraphs,
which is the case where a wrapper would show,
since a wrapper trims the block spacing of the heading at its edge.

One thing does not work.
A marker that no provider replaced is **not** distinguishable afterwards,
because `query(<animo-ask>)` returns replaced and unreplaced markers alike.
A tag outside any slide therefore has to be diagnosed at the tag site,
from a state that `slide` sets around its body, and not by a sweep at the end of the document.

## A cetz draw command is a value, not content

Measured against cetz 0.5.2 on typst 0.15.0, while settling whether raw draw commands can be
tagged. This is what decides that they are refused.

- A draw command is an **array of closures**: `draw.grid((0,0), (4,2))` is an `array` whose
  every element is a `function`, and so is `draw.stroke(red)`, so a command that changes the
  draw state and one that emits geometry have the same shape and neither is a special case of
  the other. The array is built where it is written, by ordinary evaluation, before
  `cetz.canvas` is called.
- A canvas body **cannot hold content at all**. A `context` block, or any other content, beside
  a draw command fails with `cannot join array with content`.
  No marker can therefore sit in the stream,
  and a `region` there is the same type error rather than merely useless.
- What a canvas *does* lay out as content, a `content()` element, is reached by a show rule
  installed **outside** the canvas: a labelled box produced by such a rule inside `content()`
  emits its group in the SVG. That is why a tag on a cetz `content()` element resolves its
  content for the epoch exactly as a tag anywhere else does.

Together, these findings show that the channel of the previous finding cannot reach a draw
command, and that no other channel can either.
Varying the array per epoch would mean re-evaluating the block that built it,
which only a body that is a function of the subslide can do. `sanor` has exactly that
body, which is how `test/draw.typ` reaches a tagged `draw.grid(..)`.

## What a container resolves from its direct children

A grid, a table, a list, an enum and a terms list read their direct children and keep the ones that
are `cell` or `item` elements. Every other child becomes the body of a cell or an item with
default settings, so the element the author wrote is never consulted. Measured on typst 0.15.0,
with a `grid.cell(fill: yellow)` as the child:

| What sits between the container and the child    | Fill |
| ------------------------------------------------ | ---- |
| nothing, the cell is the argument                | kept |
| a label, `[#grid.cell(..)[x]<l>]`                | kept |
| a `context` block                                | lost |
| a `box`                                          | lost |
| a `styled`, from `text(red, ..)` or a `set` rule | lost |

The label row shows that the loss is caused by the intervening element,
rather than by touching the cell at all.
The `styled` row is the one that is easily guessed wrong.
Typst does not look through `styled` here, so a package must not look through it either,
and `peel` from `wrap.typ` is the wrong tool on this path.

The loss differs per container, and `colspan` goes the way `fill` does:

| Child        | What a `context` block around it costs                         |
| ------------ | -------------------------------------------------------------- |
| `grid.cell`  | `fill`, `colspan`, `rowspan`, `align` and `stroke` are dropped |
| `table.cell` | the same settings are dropped                                  |
| `list.item`  | becomes a nested list under the item above it                  |
| `enum.item`  | becomes a nested enum under the item above it                  |
| `terms.item` | fails to compile, with `expected term item or array`           |

An explicit number survives into the nested enum rather than being dropped.
`enum(enum.item(7)[a], context enum.item(9)[b])` renders `7. a` and then `8.` holding a nested
`9. b`, where the direct form renders `7. a` and `9. b`.
The enclosing enum gives the item that holds the nested one the next number in its count,
so the loss is the item's place and not its number.

**A cell's fill is painted by the container, not by the cell.** In the SVG of a one-cell grid
holding a labelled box, the fill path is a sibling emitted *before* the labelled group, and the
group holds only the glyphs:

```
<path fill="#ffdc00" ... transform="translate(2 2)" d="M 0 0v 17.238h 222.771653543v -17.238Z "/>
<g transform="translate(7 7)" data-typst-label="probe">
  <g transform="matrix(1 0 0 -1 0 7.238)">   <- glyphs only
```

No arrangement of a tag, and no reconstruction of the cell,
therefore puts a cell's fill inside the group the browser addresses.
This decides for the refusal in *Tags* rather than a silent rebuild.
Rebuilding the cell around the site restores the fill in the rendering,
and leaves `move`, `scale`, `pan`, `reveal` and `hide` reaching only the cell's content.

Detection has to compare element functions. `grid.cell` and `table.cell` both `repr` as `cell`,
and `list.item`, `enum.item` and `terms.item` all as `item`, while `==` tells every pair apart.
`fields()` reports only the fields that were set, and a label adds a `label` key, so a cell that
carries nothing but its body is recognised by its key set being `("body",)` once `label` is
dropped.

## Transforms between a tag's slots are layout-neutral

`box(move(dx: .., dy: .., ..))`, `box(scale(.., reflow: false, ..))` and `box(hide(..))` measure
identically to `box(..)`, in width, in height and in their effect on the line around them, even
though `move` and `scale` are themselves block-level elements. The same holds for
`block(width: 100%, move(..))` against `block(width: 100%, ..)`.

This is what lets the static presentation apply a state's display state with typst's own elements
without disturbing the layout, and it is what makes "nothing moves between states except what the
timeline moves" an invariant rather than an assumption.
A tag site emits the same structure in every state and in both targets,
and only the parameters inside it change.

**The measurement is of the size a slot takes, and it says nothing about where the content inside
it lands.** A `move` is laid out as an inline element, so a block-level payload inside one is laid
out in a paragraph rather than as a block, and it is aligned to the paragraph's start instead of
filling the container. Measured on typst 0.15.0 at 144 ppi, over the centred bodies of *Wrapping a
tag site*, against the page that holds the body with no wrapper at all:

| Nesting                                                  | Renders          |
| -------------------------------------------------------- | ---------------- |
| `block(width: 100%, block(width: 100%, move(scale(x))))` | left-aligned     |
| `block(width: 100%, move(scale(block(width: 100%, x))))` | identical, tol 1 |

The display state therefore goes **around** the inner slot rather than inside it.
The filling block that
*Wrapping a tag site* calls for then sits inside the `move` and fills the paragraph the `move`
opened.

**A rendering that carries a display state is layout-neutral only inside a slot.** The outer slot
holds a `move`, which is block-level and therefore a separate block, so the size that slot takes
is the same either way. The extent of a rendering measured on its own differs. `measure` reports a
height and no baseline, so a descent is read off a line that holds the content beside a zero-width
pole taller than it, and a block-level body pushes that pole onto a separate line.
Measured on typst 0.15.0, over the word `hidden` at 11 pt:

| Measured                   | Ascent   | Descent  |
| -------------------------- | -------- | -------- |
| `box(move(scale(box(x))))` | 7.24 pt  | 0 pt     |
| `move(scale(box(x)))`      | -13.2 pt | 20.44 pt |

The height is the same either way, so a footprint over renderings that all lay something out is
unaffected.
An epoch that lays nothing out has an extent of zeroes.
The largest ascent is then zero, while the largest descent is still a line,
so the footprint is a line taller than the content it holds,
and the rendering inside it is lowered by the same amount.
`inline-extent` therefore measures every rendering inside a box.

## Introspection: the fields of a nested structure, and one occurrence per page

`query` hands back the element it found, and its fields are readable all the way down, so a
structure that a package emitted can be walked from the label that names it:

| Expression                   | Is                                  |
| ---------------------------- | ----------------------------------- |
| `query(label(name)).first()` | the labelled outer `box` or `block` |
| `.body`                      | whatever that wrapper holds         |
| `.body.body`                 | one level further, and so on        |
| `.func() == hide`            | how the leaf kind is recognised     |

Two field values are worth recording, because both are the kind of thing that is guessed wrong
once. A `scale` element reports `x` and `y` as **ratios** and has no `factor` field, so a factor
of 2 reads back as `200%`. An unset `stroke` on a `box` reads back as an **empty dictionary** of
sides, `(:)`, rather than as `none` or `auto`.

`query` returns one occurrence of an element **per page** it was laid out on, in document order.
Content bound once and placed on several pages is therefore several elements to `query`, not one.

Together, these facts let a tier-1 test assert the display state that a tag site actually
applied, with nothing exported.
In the presentation mode, where each state is a page,
occurrence *i* of a tag in a one-slide document is its rendering in state *i*,
and `move`'s `dx`, `scale`'s `x` and the presence of a `hide` say what that state did to it.

## The head of a page that a package builds itself

Measured on typst 0.15.0.

- A document that builds no `html` element gets a head from typst. It has `lang` from
  `set text(lang: .., region: ..)`, written as `nl-BE`, a `<title>` holding the plain text of
  `document(title:)`, and `<meta>` elements for the description and the authors. Typst 0.15.0
  names the latter `authors`, where HTML defines `author`.
- A document whose only element is an `html` element is taken as it is. Typst adds neither the
  title nor the language.
- A package reads both in a context, as `document.title`, `document.author`, `text.lang` and
  `text.region`.
- `html.title` refuses content with markup in it, with the message
  `HTML raw text element cannot have non-text children`, so a title made of content has to be
  reduced to its text first.
- A `set document` rule is refused when a show rule has put the document in an element
  (`document set rules are not allowed inside of containers`). A show rule that returns the
  document as it is, or in a context block, leaves the rule at the top level. In the HTML target
  the deck's show rule builds the page as elements, so a `set document` there has to come before
  it.

## Other verified behaviour

- `target()` returns `"html"` or `"paged"`, which is the clean way to branch. The
  `dictionary(std).at("html", default: none)` idiom in `slipst` is a compatibility hack for
  older typst versions and is not needed here.
- Inside an `html.frame`, `target()` returns `"paged"` in a document compiled to HTML, nested
  containers included. A slide lays its body and both layers out inside frames, so content
  written there cannot learn from `target()` that the document is compiled to HTML. A state
  updated outside the frame reads the same inside it, which is how `output-type()` answers there.
- `set page(...)` is **ignored** in HTML export at document level (typst warns) and is an
  error inside `html.frame`. Slide size, background colour and background image must be
  emitted as CSS for the HTML target, and the slide itself is a sized `block`.
- HTML export still requires `--features html` in typst 0.15.0 and prints an
  "under active development and incomplete" warning.
- `html.elem` takes its attributes as a dictionary in the `attrs:` argument.
  `html.div(..)` and friends do not accept `attrs:`,
  so Animo should use `html.elem` for anything with data attributes.
- Multi-page SVG export fails without a page-number template (`{p}`/`{0p}`) in the output
  path.
- A document that lays nothing out is **not refused**: typst 0.15.0 compiles it to one blank
  page at the default page size, A4.
  A handout whose every state gave up its page would therefore produce a blank page
  at a size the deck never mentioned, rather than an error.
  Animo counts the pages its slides contribute and refuses that deck itself.
- A code block joins array-returning calls, so `animation: { sub(..) sub(..) }` yields a
  list of subslides with no side effects and no accumulator. An empty `sub()` yields an empty
  subslide. A code block that joins **nothing** yields `none` rather than an empty array, so
  `{ }` and a block whose every `sub` sits behind a false condition are timelines with no
  subslides, and the resolver has to accept `none` as one.
- The cetz-style block-scoped import works as intended: inside
  `{ import anim: * ... }` the primitives win, while `move`, `scale` and `hide`
  outside the block remain the typst built-ins.
- A star import re-exports submodule bindings, so a single
  `#import "@preview/animo:0.1.1": *` provides `slide`, `tag`, `region`, `sub` *and* the
  `anim` module (`anim` reports as a `module`).
  Three usage forms all work:
  `import anim: *` inside the animation block,
  a named import (`#import "@preview/animo:0.1.1": sub, tag, anim`),
  and fully-qualified calls (`anim.reveal("a")`) with no inner import at all.
  Verified with a local two-file module, which resolves identically to a package
  entrypoint.
- **Footgun:** because `import ...: *` silently falls through to the standard library for
  any name the module does not define, a mistyped or unsupported primitive does not error.
  `rotate("b", 45deg)` inside the animation block quietly calls `std.rotate` and returns
  *content*, surfacing later as a confusing "does not have field" error. `sub()` must
  therefore validate that every operation it receives is an Animo operation descriptor and
  panic with a clear message otherwise.
- Labels inside math need care: `#box[b] <bb>` with a space is parsed as literal math
  content (it renders as `<bb>`), whereas `#box(body)#label(name)` attaches correctly.
- SVG paints in document order, and `z-index` does not apply to SVG children in shipping
  browsers. Stacking order is therefore fixed at compile time.
  This is accepted, because animations that change the z-order are out of scope
  and can be simulated without reordering.
  The renderings of an epoch stack are groups inside one SVG, so they paint in document order
  as well.
  That order does not matter, because at rest only one rendering is visible,
  and during a crossfade `plus-lighter` adds the renderings, which gives the same sum in any
  order.
  The slide containers and the layers of a slide are *HTML* elements,
  which are positioned with no `z-index` and therefore also paint in document order.
- `animo` is unused on Typst Universe (`packages/preview/animo` returns 404).
