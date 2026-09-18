<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Animo Findings

Verified behaviour of typst 0.15.0, and of the browsers Animo drives,
that [the design](design.md) relies on.
Recorded here so that it does not have to be rediscovered.
Checked against the installed `typst 0.15.0` binary, with chromium 151, firefox 153 and
playwright's webkit 26.5 for the browser measurements. Where the engines differ, the entry
says so, because a deck has to work in all of them.
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
- **Duplicate labels are permitted** and each occurrence gets its own group, which is what
  makes "one tag, several elements" work
  and what makes one CSS rule reach the same tag in every epoch frame of a slide.

Stability: the attribute was added by PR
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

The residual risk is not the attribute but its HTML wrapper: HTML export remains behind
`--features html`, warns that "behaviour may change at any time", and its tracking issue
[#5512](https://github.com/typst/typst/issues/5512) gives no stabilisation timeline.
"Frame API for embedded layout-as-SVG" and "Linking to a label, with derived ID" are
already ticked there, but "Share printing code between SVG and HTML export" is not, so the
SVG-inside-HTML emission path may still be refactored.

## The frame is the smallest unit of DOM addressability

This is what forces "re-render the slide, not the region" and therefore the whole epoch model.

- `html.elem` **inside** `html.frame` is dropped, with the warning "elem may not occur inside
  of a paragraph and was ignored". There is no way to give a sub-area of a frame its own DOM
  node, so a region cannot be its own HTML element inside a slide frame.
- `html.frame` inside `html.frame` compiles without error but contributes no second `<svg>`;
  nesting frames is not a route to independently swappable sub-frames either.
- `set page(..)` inside `html.frame` is an error ("page configuration is not allowed inside of
  containers"), so a slide is a sized `block`, not a page, in the HTML target.
- Positions are dead in HTML output (below), so Animo cannot place per-region frames itself
  either: it does not know where the region is.

Hence the only mechanism available: render the whole slide once per content state, stack the
frames, and swap them.
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

Consequences: `layout` + `measure` per epoch is a sufficient and verified mechanism for
footprints; the region only needs the epochs the slide actually has, so the cost is linear in
epochs rather than combinatorial in tags.

## Regions: an inline footprint has to pin its baseline

Measured on typst 0.15.0, while building the implicit region of an inline tag, over five epochs: a
word, a word at 2em, nothing, two lines, and an equation with a subscript.

- **A box takes its baseline from its content, even at a fixed size.** `box(width: W, height: H, c)`, sized to the per-axis maximum, puts the rest of its line at 17.24, 24.48 or 31.63 pt as
  `c` is a word, a word at 2em or nothing, since a box with no baseline in its content sits on its
  bottom edge. A fixed inline footprint therefore does not hold its line still.
- **A box whose content is placed has no baseline of its own**, so its `baseline` argument
  alone decides where it sits. Placing each epoch at `dy: A - a`, with `A` the tallest ascent and
  `a` the epoch's own, and lowering the box by `baseline: D`, the deepest descent, puts the rest
  of the line and the next paragraph at the same height in every epoch (24.48 and 52.06 pt), the
  empty one included. The epoch with the tallest ascent lays out exactly as its untagged control.
- **`measure` reports no baseline, but the descent is readable**: the height of
  `[#body#box(width: 0pt, height: 10000pt)]` less the pole is the reach below the first baseline.
  Text reaches nothing below it at the default `bottom-edge` (a word and a word at 2em measure
  0 pt), a second line and a subscript do.
- In the SVG of an `html.frame`, the labelled group's first child is still the inner slot, which
  now carries typst's own `transform="translate(0 dy)"`; the CSS `translate` and `scale`
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
- `align(top + left, ..)` left-aligns content under `set align(center)`; `align(top, ..)` does not.
- A counter stepped per region and reset before a rendering numbers nested regions in document
  order, identically in every rendering, in both targets, and a `measure` inside steps nothing.

## Crossfading epoch frames

Stacked in one grid cell (`display: grid`, both children in `grid-row: 1 / grid-column: 1`,
`isolation: isolate` on the parent), at the midpoint of a transition with both frames at
`opacity: 0.5`, compared against the single frame at `opacity: 1`:

| Mid-transition blending        | Max deviation outside the region |
| ------------------------------ | -------------------------------- |
| plain `opacity` crossfade      | 62/255 (text visibly washes out) |
| `mix-blend-mode: plus-lighter` | 1/255 (rounding only)            |

So `plus-lighter` is what makes the containment claim true *during* the transition
and not only at its endpoints. `slipst` uses the same blend mode for its
whole-slip crossfades.

**The sum is exact in all three engines, once the frame is the element that isolates.**
Chromium 151 and firefox 153 add the two half-opacity layers back to one opaque layer bit for
bit. Playwright's webkit 26.5 does not while the isolation sits on an HTML ancestor of the
frame: ten pixels on antialiased glyph edges drift by up to 42/255, measured in a container
on 2026-09-17. With `isolation: isolate` on the frame itself it is rounding only there too.
The entry on where a blend stops, further down, is what that rests on.

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

The first row is the control: `plus-lighter` on a `<g>` is not inert, and a group does add to
ink beside it in its own frame. The second says it did not add the frame below, so a blend on
a region's group degraded to exactly the plain opacity crossfade of the table above.

The third and fourth rows are the same mechanism on two structures, and the engines do not
answer them alike. The blend goes where it does reach, and `visibility` scopes the outgoing
side down to the regions it hands over, which a descendant can take back. On one frame per
epoch, which is the structure a slide had first, webkit leaves the glyph cores of the whole
region at half, across 473 pixels of twelve rows, and the result is the plain opacity
crossfade. On one frame holding a rendering per epoch, which is the structure a slide has,
all three engines sum the halves. Webkit rasterises the blended group into a buffer whose
bounds it rounds, so the bottom row of the region comes back white where the single copy
carries the antialiasing of the glyphs below their baseline: 95 pixels of one row, by up to
128/255. The pixel count is what separates the two, because a wash-out moves the glyph cores
of every row and this moves the edge of one.

So the region-scoped crossfade of *Architecture* is built, the whole-frame fallback is not
needed, and the merged frame is not only a saving on `<defs>`: it is what makes the crossfade
add in webkit at all. The epoch renderings are the outermost groups of one frame, so they are
ink beside each other and the first row is what says the blend reaches. A region's group is
not, which is why the blend stays on the rendering.

The stacking, the grid cell and the isolation are common to all of them, and the isolation is
essential: `plus-lighter` sums inside the isolated group, against a transparent backdrop
rather than against the page. Which element has to carry that isolation is the entry below.

**How far a group's blend reaches past its own frame is not the same in every engine.**
Measured on 2026-09-15 for chromium and firefox and on 2026-09-17 for webkit, on a
handwritten stack rather than on typst's output: one inline SVG on an opaque ground, a dark
red mark inside it and a dark green ground, so that a blend reaching the ground comes back
with green in it.

| What is under the mark's own frame         | chromium 151 | firefox 153  | webkit 26.5 |
| ------------------------------------------ | ------------ | ------------ | ----------- |
| the element the SVG is painted on          | summed in    | out of reach | summed in   |
| an inline SVG stacked below that frame     | summed in    | out of reach | summed in   |
| the page, behind the element that isolates | out of reach | out of reach | summed in   |
| the same page, with `isolation: auto`      | summed in    | out of reach | summed in   |

Firefox stops a group's blend at the root of the inline SVG. Chromium does not, and stops at
the element that carries `isolation: isolate`. An earlier reading of the second row of the
table above took that firefox behaviour for the rule and wrote it down as the reason a
region-scoped blend cannot work; it is not the rule, and the two engines nevertheless agreed
on that row, which is why the design it decided still stands. What makes chromium contain the
blend in typst's own output and not in the handwritten stack was not pinned down, and the
difference is recorded here rather than explained.

**An isolating HTML ancestor does not confine a group's blend in webkit.** The last two rows
are the new ones. Chromium reaches the page when the isolation is taken off and stops at it
when it is written, which is what says the third row is the isolation working rather than a
boundary chromium would have stopped at anyway. Webkit gives the same answer either way: a
blend on a group inside an inline SVG reaches the page whatever an HTML ancestor declares.

The consequence is visible rather than subtle, because `plus-lighter` adds. Black ink adds
nothing to the ground it lands on, so a slide whose epoch renderings blend against the page
renders **blank** in webkit, and it is the ground that shows rather than the text.

**The element that confines it in every engine is the inline SVG that holds the group.**
Measured on 2026-09-17. With `isolation: isolate` on the epoch frame, the blend stops there
in chromium 151, firefox 153 and webkit 26.5 alike. Animo therefore writes the rule on the
frame rather than on the canvas, and the canvas carries no isolation of its own.
Moving it also took webkit's whole-frame midpoint from ten pixels at 42/255 to rounding only,
so the engine-dependent exactness of the first entry above is the ancestor's isolation
failing rather than webkit's arithmetic.

`probes/test_crossfade.py` holds each engine to its own answer, so one that changes its mind
says so by failing rather than by rendering differently.

## Choosing between stacked renderings: `opacity`, not `visibility`

Measured on chromium 151 and firefox 153, while building the subslide numbering.

A value finer than a slide number is rendered once per subslide and one of the renderings is
shown, which is the same trick `hidden:` and `reveal` already use. Which property shows it is
not a free choice, and the constraint comes from the entry above: an epoch frame that is not
being shown is `visibility: hidden`, and a descendant may take that back, which is exactly what
scopes the outgoing frame of a region crossfade.

So `visibility` cannot also select a rendering. With two frames stacked as epoch frames are and
the second hidden, a `visibility: visible` on a group inside that second frame computes to
`visible` and **paints**: the pixel that should show the front frame's red shows the hidden
frame's blue. An `opacity: 1` on the same group computes to `opacity: 1` and
`visibility: hidden`, and the pixel stays red.

`opacity` still selects within the frame that is shown, which is the other half: two groups in
the visible frame, one at `opacity: 0`, leave only the other one's ink.

So a stack of renderings is chosen with `opacity`, and the two properties stay one per job:
`visibility` says which frame the slide is on, `opacity` says which rendering of a stack the
position is on, and neither can undo the other.

## Crossfading two slide containers

Measured on chromium 151 and firefox 153, for the slide boundary under *Architecture*.
The case above is two inline SVGs inside the canvas, which carries no ground of its own.
A slide boundary is two HTML elements that each carry an opaque background,
stacked in one grid cell of the deck, which is the element that centres a slide on a surround.

| Midpoint of a boundary between two opaque grounds | Deviation from their average |
| ------------------------------------------------- | ---------------------------- |
| plain `opacity` crossfade                         | 64/255                       |
| `mix-blend-mode: plus-lighter` on the containers  | 0 to 1/255 (rounding only)   |

So the mechanism carries over unchanged, and it carries over for a reason the frame case never
had to state: a plain crossfade handles two opaque grounds incorrectly, since each is
composited over what is behind it and the surround shows through the half-transparent pair.
One slide blended against the transparent backdrop of the isolated deck is that slide, to
within the same rounding, so the blend may sit on every slide rather than be turned on for the
length of a boundary.

**The ground of the isolating element is inside the group it isolates.**
With the surround written on the deck, the element that carries `isolation: isolate`, a white
surround is added to both halves and takes the midpoint 239/255 away from the average of the
two slides; with the same colour written on the page instead, the midpoint is exact.
Black hides the mistake completely, because zero is what adding nothing looks like, which is
why this was found by reasoning rather than by inspection. Animo therefore writes its surround on
`body` and leaves the deck without a background.

## What keeping every slide laid out costs

Measured on chromium 151 through the devtools protocol, on an i7-1260P, while choosing how a
slide that is not being shown is hidden. A crossfade needs both containers laid out, so
`display: none` cannot be what hides the two a boundary involves; the question was whether it
has to hide any of the others.

Every slide laid out for the whole session, against `display: none` on all but the ones in use:

| Deck                                   | First paint    | Layout objects     |
| -------------------------------------- | -------------- | ------------------ |
| the tour, 13 slides, 17 frames, 1.1 MB | 72 to 86 ms    | 531 to 12 043      |
| 60 slides, one epoch each, 5.5 MB      | 0.43 to 0.96 s | 1 361 to 113 482   |
| 60 slides, three epochs each, 19 MB    | 4.2 to 10.2 s  | 5 594 to 1 397 520 |

So it is nearly free on a deck of the tour's size and it doubles the first paint of an ordinary
long one. The cost is paid at every load, and `typst watch` reloads the browser after every
edit that compiles, so it is paid throughout the writing of a deck and not only once at a talk.
Animo lays out two slides and no more: the one being shown, and the one a boundary is crossing
from. Stepping was not measurably affected either way, at 24 to 43 ms per step on every deck
and under both regimes, which shows the cost is layout at load and not interaction.

**`content-visibility: hidden` is not a cheaper `display: none`**, measured on the same three
decks: 0.076, 0.44 and 4.39 s against 0.076, 0.40 and 4.31 s, which is within the noise on the
first and slightly worse on the other two. So there is no third hiding rule to reach for.

**What is left of the first paint is style recalculation and not layout.** With `display: none`
the heaviest deck spends 3.0 s of its 4.3 s recalculating style over 2.07 million DOM nodes and
3 ms laying anything out, so the remaining lever is the number of nodes typst emits rather than
anything the runtime does with them. Dropping the definitions that an earlier epoch frame
already carried, which is what a shared `<defs>` hoisting would do, takes that deck from
4.34 s to **0.55 s** and its nodes from 2.07 million to 407 thousand, and the deck with one epoch a slide from 0.42 s to 0.16 s. Slides 1, 30 and 60 of both
decks render pixel-identically before and after, which shows the deduplicated page is the
same page: typst's def ids are content hashes, so an id that occurs twice is one definition
twice. So the hoisting is worth a factor of eight on the first paint of a deck with structural
subslides, which is a second reason for it beside the factor of two it is worth on the gzipped
page.

This is a cost rather than a behaviour, so it has no probe; `docs/probes.md` records it among
the entries that cannot have one.

## Chromium rasterises a frame differently while an opacity animation runs in it

Measured on chromium 151 and firefox 153, while asserting the containment claim above
*during* a transition rather than at its endpoints.

Chromium promotes a group with a running `opacity` animation to a compositing layer of its
own, and the glyphs of the frame it sits in are then rasterised along a different path. A
raster taken mid-step and one taken at rest therefore differ on antialiased edges, whether or
not anything about the slide actually moved: 10 pixels by up to 22/255 outside a crossfading
region, and up to 79/255 on the glyph edges inside it. Firefox 153 shows none of it. It is not
the blend and not the isolation, which forcing `mix-blend-mode: normal` and `isolation: auto`
both leave unchanged, and a step that animates only `translate` is exact.

What follows for the measurement of a transition, and for the remedy that suggests itself:

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
  and the midpoint raster adds the half unit of its own quantisation.
  The midpoint of a mid-flight comparison is therefore the sum of its two ends to within
  1.5/255, where a comparison of stated opacities is exact to 1/255.
  Measured on 2026-09-17, on the mechanism by hand and in a deck of animo's own.
  The deck came to 1.0/255 on a workstation and to 1.5/255 on a continuous integration runner,
  which takes an end 2/255 from the slide at rest.
  Which way an end rounds differs between machines,
  and an allowance of 1/255 on a mid-flight comparison passes on one machine and fails on
  another.
- `will-change: opacity` on the carried groups removes the difference, because a group that is
  always promoted rasterises the same at rest and in flight. It is not worth it: the promoted
  text then differs from unpromoted text *permanently*, and by more (643 of 3600 ink pixels,
  285 of them by over 16/255), so the remedy is larger and more visible than the problem, which
  lasts 400 ms and moves ten pixels.

## Automatic canvas sizing: `#place` is invisible to `auto`, but visible to a show rule

Measured on typst 0.15.0, for the canvas rule under *Canvas and viewport*.

- **`#place` contributes nothing to automatic sizing.** With `#set page(width: auto, height: auto, margin: 0pt)` and a body of `#place(dx: 8cm, dy: 4cm)[OUT] in-flow`, the page comes out
  `32.285 x 7.238 pt`, which is the size of the in-flow text alone.
  `measure()` agrees: a block with and without the same placement measures
  `32.29pt x 7.24pt` both times. So typst's own `auto`
  machinery cannot size an Animo canvas, because an Animo slide is a 2D canvas built with
  `#place`.

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
  Recorded under *Open Questions*; `canvas:` is the explicit override.

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
  sits, which is the direction the design expects; a nested placement stated as an
  **alignment** is counted from the body box instead, which is *long*, since the body is
  wider than the container the author aligned to.
  And a **ratio-sized body contributes nothing at all**, because the rule measures it
  without a container: `measure(rect(width: 100%, height: 100%))` is `0pt x 0pt` where the
  same rectangle at an absolute size measures what it says. So the union is not exact for
  top-level placements either, only for top-level placements whose body has a size of its
  own.

- **Dropping what cannot be attributed to the body has no mechanism behind it.**
  `layout(size => ..)` is ruled out above for breaking the paragraph. The one candidate
  left is a nesting depth kept in a `state` and stepped by show rules on the containers.
  Measured: it reports a positive depth inside a `box`, inside a grid cell and inside a
  `figure`, and **zero** for a placement inside another placement, which has no container
  in it to step the depth, and which is the shape both real decks beside this repository
  write. It is also blind to what Animo itself wraps content in, since a tag site is a box
  and a region is a block, so every placement inside a tag would read as nested. So the
  approximation stays, and the error is documented in both directions.

## Recording placements: what a `show place:` rule may and may not do

Measured on typst 0.15.0 while building the automatic canvas, which needs the placements as
*data* and not merely as content the rule passes through.

- **A show rule cannot return a value, so the numbers travel as introspection.** The rule
  emits a `metadata` element carrying a label beside the placement it sees, and the union
  is taken from `query`. This works **inside `html.frame`** as well: `query` sees into a
  frame even though positions do not exist there, which is what lets one canvas rule serve
  both targets.
- **A block sized from its own `query` converges.** The canvas depends on the layout of
  the very block it sizes: the first pass records nothing and the block comes out at its
  floor, and typst's introspection loop then runs the document again with the placements
  in reach. It terminates because the body is laid out at a width that does not depend on
  the answer. Measured: a block whose width is the maximum of `200pt` and a placement at
  `dx: 400pt` comes out at 419.4pt in the emitted frame.
- **The recording may not disturb the layout it is watching.** A `context` block holding
  nothing but `metadata` is inline and changes no measurement. `layout(size => ..)` is
  block-level and breaks the paragraph the placement sits in: the same body measures
  `76.89pt` tall without it and `103.29pt` with it.
- **That last point closes the one route to telling a nested placement apart.**
  `layout(size => ..)` inside the rule does report the placement's own containing block
  (`400 x 300pt` at top level, `113.39 x 56.69pt` inside a 4 cm box, `200 x 300pt` in a
  grid column), which would make the automatic union exact. It cannot be used, because
  the price is a body that lays out differently from the one the author wrote. So the
  union stays approximate below the top level, as *Open Questions* has it, and the reason
  is not that typst hides the container but that asking for it costs the layout.
- **A `show place:` rule inside another one does not suppress the rule around it.** Both
  fire, so a rendering cannot decline to be recorded by installing a rule that returns
  its element untouched. This is what animo wants where a rendering is measured rather
  than laid out, since a `metadata` element inside a `measure` never reaches `query` and
  the recording there costs a `context` and a `measure` per placement for nothing.
- **The inner rule runs first, and the outer one is handed what it produced.** A rule
  that attaches a label, `show place: it => [#it<unrecorded>]`, therefore gives the rule
  outside it a placement whose `label` field is that label, which is the channel the two
  rules use instead. A label on a placement changes no layout, so a rendering measures
  the same with it as without it, which is what keeps the footprint a region reserves the
  number its measurement was for.

## A fixed-height container stacks the block-level content that does not fit

Measured on typst 0.15.0, and the reason a slide body is not always laid out at the viewport's inner
height. A container with a fixed height lays its content out in a single region of that height.
What does not fit is neither clipped nor allowed to grow the container, and what becomes of it
depends on what it is.

- **A paragraph runs past the bottom edge.** In a `block(width: 200pt, height: 100pt)` holding
  running text at 10 pt, every line lands where its line spacing puts it and the paragraph
  simply paints outside the container: the end of it sits at `333.58pt`.
- **Every block that does not fit is painted at the bottom edge.** The same container, given
  twenty-four one-line blocks with no spacing between them, lays out sixteen at `6.58pt` apart
  and reports a position of exactly `100pt` for each of the remaining eight, so they arrive as
  a pile, each drawn over the one before it.
- **A `box` container behaves exactly like a `block` one here**, so the kind of container
  makes no difference.

This is easy to miss, because the two halves differ: a slide of running text pans correctly,
while the same slide with its steps in blocks, which is what a multi-paragraph tag site becomes,
comes out as a pile.

Consequence: a body whose flow is taller than the viewport cannot be laid out in a box of the
viewport's inner height, so Animo sizes that box to the flow instead, as *Canvas and viewport*
describes. The height comes from an unbounded measurement of the body, which no `#place`
contributes to, so the box is decided before the canvas and independently of it, and the
introspection that sizes the canvas still terminates.

## `html.frame` sizes its SVG in `em`, as an inline style

Measured on typst 0.15.0. `html.frame` writes `width` and `height` on the `<svg>` as an inline
style in `em`, dividing the frame's size in points by the text size in effect: a 200pt
block is `18.181818182em` at the default 11pt text and `9.090909091em` at 22pt.

Two consequences for the HTML shell. An inline style outranks a stylesheet rule, so a deck
that sizes its frames from CSS renders them at the ratio between the page's font size and
typst's text size, which is 16/11 by default and looks like an 8% scaling bug. And the
frame's own size is not a reliable unit for anything, since it moves with a `set text` the
author is free to write. Animo therefore sizes the canvas element itself and overrides the
frame with `width: 100% !important`.

The SVG also carries `overflow: visible`, so ink outside the frame's viewBox is painted
rather than clipped. The viewport element is what clips a slide.

## Fitting the slide to the browser window

Measured in playwright's chromium 151 and firefox 153.

- **`calc()` does not divide a length by a length in firefox.** `calc(100px / 40px)`
  computes to `2.5` in chromium 151 and in playwright's webkit 26.5, which is what CSS
  Values 4 type checking asks for, so firefox is the outlier rather than chromium the
  exception. Firefox 153 does not parse it: `CSS.supports("scale", "calc(100px / 40px)")`
  is false,
  and the declaration it appears in is dropped whole, with nothing on the console.
  A deck whose fit was written that way rendered unscaled in the top-left corner of the
  window in firefox, at roughly half size, with the content beyond the viewport visible
  because the element that clips had nothing left to clip.
  So the fit may not be expressed as one length over another.
- **A length over a number is portable**, and that is what Animo emits.
  `--animo-unit` is `calc(var(--animo-viewport) / <slide width in points>)`: one typst
  point, as a CSS length, at whatever size the window currently has.
  Every length Animo writes is then that unit times a number computed at compile time,
  and the runtime still never has to measure the window or listen for a resize.
- **Sizing the canvas, rather than scaling it,** is what makes a typst point the unit of
  everything inside it at any window size. This is a change from the first version, which
  scaled the canvas element as a whole, and it is an improvement beyond portability: the
  canvas keeps both its `translate` and its `scale` free, which is what *Architecture*
  rule 5 asks for when it reserves `scale` on that element for a future zoom.
- The two targets then agree to **0.0017 of the slide** on every edge of a placed square,
  comparing a 454-pixel handout raster with a 908-pixel browser screenshot. That is one
  pixel of the coarser raster, which is the floor of the measurement rather than a layout
  difference. Chromium and firefox agree with each other to **0.01 CSS pixel** on the
  canvas box at a 1280 by 720 window.

## SVG `<defs>` ids are content hashes

Relevant because stacking several frames in one document puts duplicate ids in one DOM.

- All deduplicated defs (glyphs, clip paths, gradients, patterns) get ids of the form
  *kind char* + hex of `hash128(key)`, from the `Deduplicator` in
  `crates/typst-svg/src/lib.rs` (`DedupId(char, u128)`).
- Equal ids therefore always mean equal content. Browsers resolve `<use xlink:href="#g..">`
  to the first matching id in the document, which is harmless here, and it is why stacking
  frames does not corrupt glyph rendering.
- It also means the duplication is pure redundancy: hoisting shared defs into one
  document-level `<svg>` would be sound, and the entry after this one is what came of that.
- **Gzip does not recover that redundancy**, so the redundancy is real on the wire and not
  only in memory. Deflate's window is 32 KiB and no setting raises it, while an epoch frame
  carrying a heading and a single sentence is already 45 KiB, and a frame carrying a whole
  slide is several times that. A definition repeated in the next frame is therefore always
  further back than the window, whatever sits between the two, so it is stored again in
  full. Measured on `examples/tour.typ` as it stood on 2026-09-15: dropping every repeated
  definition takes the page from 1340 KiB to 845 KiB and the gzipped page from 268 KiB to
  145 KiB, a saving of 46% on what is actually transferred. So compression and hoisting are
  worth a factor of five and a further factor of two, and neither substitutes for the other.
  The deck has grown since the same measurement was first taken, at 44% of a 222 KiB page,
  so the fraction is the part of this that carries.

## Hoisting shared `<defs>`: sound in the browser, out of reach in typst

The other half of the entry above, measured when the optimisation was scheduled to be built.
The mechanism holds and the markup is unreachable, so the saving a deck actually gets is
decided by a third fact: the scope of typst's deduplicator.

- **A `<use>` resolves a definition that lives in an earlier inline `<svg>`.** Measured on
  real output rather than on handwritten markup: two stacked frames of one paragraph, the
  second of them the one that is shown, with every repeated definition dropped from the
  page. The raster is identical to the page that carried the repeats, in chromium 151 and
  firefox 153, so the frame that lost its definitions is drawing out of the frame above it.
  Webkit runs the same probe where it can be launched, which is continuous integration
  and the platforms that carry its libraries.

- **A package never holds the markup a frame became.** `html.frame` has one field, `body`,
  and its value is content; the SVG is produced when the document is encoded, by
  `write_frame` in `crates/typst-html/src/encode.rs`, which calls `typst_svg::svg_in_html`
  once per frame, each call with a `Deduplicator` of its own. The `html` module holds `elem`,
  `frame` and the tag helpers, and nothing that writes markup, while a text node is escaped,
  so markup cannot be handed in as a string either. The raw-text exceptions are `<style>`
  and `<script>`, which is how Animo's stylesheet and runtime reach the page and is no help
  here, because a definition has to be an SVG element. A second compile does not open the
  door either: `read()` can take the first pass's HTML back in, and nothing can emit it.
  So the document-level `<svg>` cannot be written from inside typst 0.15.0, whatever it
  would be worth.

- **The deduplicator's scope is the frame, not the rendering, and that is reachable.**
  Three renderings of one paragraph in three frames define every glyph three times; the same
  three `#place`d at one point in *one* frame define each of them once, with the same number
  of `<use>` references and 139 KB of page taken to 71 KB. Each rendering is still a
  labelled group when it is a labelled `box`, so `visibility` scopes one away exactly as a
  frame is scoped away, and `mix-blend-mode: plus-lighter` on two of them at half opacity
  each sums to one opaque rendering. The blend works on groups here because the two are the
  outermost groups of one `<svg>`, which is what a region's group is not, under
  *Crossfading epoch frames*. This is what Animo does.

- **What each scope is worth**, measured on 2026-09-15 on this repository's two decks, the
  second of them at twelve slides of three epochs with an overlay carrying a number:

  | Deck    | Page     | Gzipped | One frame per slide | Every repeat dropped |
  | ------- | -------- | ------- | ------------------- | -------------------- |
  | tour    | 1340 KiB | 268 KiB | 245 KiB, 8%         | 145 KiB, 46%         |
  | scaling | 3476 KiB | 639 KiB | 365 KiB, 43%        | 176 KiB, 72%         |

  The last two columns are far apart on the tour and much closer on the controlled deck,
  and the reason
  is the shape of the decks rather than a property of either scope: the tour is mostly one
  epoch a slide, so nearly all of its duplication is across slides, where a frame per slide
  cannot reach it. A deck with several epochs a slide is the one the reachable scope is for,
  and it is also the deck the raw figure matters on, since the raw page is what the browser
  holds. `benchmarks/run.py` records both projections, as `hoisted_*` and `merged_*`.

  Animo implemented the reachable scope on 2026-09-15 and reached that column. The tour went from
  1340 KiB and 268 KiB gzipped to 1231 KiB and 245 KiB, which is the projection to the
  byte, and its frames from 19 to 15, one per slide. On the controlled deck, with both arms
  compiled from one working tree so that only the merge differs, the saving grows with the
  epochs a slide has, which is the duplication it removes: 180 KiB gzipped unchanged at one
  epoch a slide, 345 to 220 at two, 673 to 297 at four, and 1328 to 445 at eight.
  `merged_*` therefore now reads back as the page itself and `merging_saves_gzipped` as
  zero on every variant, and a reading that is not zero is a slide whose epochs ended up in
  frames of their own again.

## CSS animation of typst SVG groups

Measured in chromium on real typst output, on a labelled group that carries typst's own
`transform="translate(0 28.346456693)"`:

| Applied CSS                                                         | Result                                                                          |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `opacity: 0.35`                                                     | works; typst emits no group-level opacity or style, so opacity is entirely free |
| `translate: 50px 0`                                                 | composes, so the element moves and typst's `transform` attribute stays intact   |
| `transform: translate(50px,0)`                                      | **clobbers** typst's translate (y jumped 49.2 → 8.0, losing the offset)         |
| `scale: 2` (default `transform-box: view-box`)                      | scales about the SVG viewBox origin, displacing the element (y 49.2 → 90.5)     |
| `scale: 2` + `transform-box: fill-box` + `transform-origin: center` | scales about the element's own centre, in place                                 |
| all three together                                                  | compose correctly                                                               |
| `transform-box: fill-box` + `transform-origin: center`, alone       | **displaces** a group that carries a `matrix(1 0 0 -1 ..)` of typst's own       |

Mid-flight interpolation, sampled deterministically through the Web Animations API,
confirms genuine smoothness and that typst's own transform survives the animation:

```
t=0.00  x=8.0   w=82.5   opacity=0
t=0.50  x=23.8  w=123.7  opacity=0.5
t=1.00  x=39.5  w=164.9  opacity=1
typst transform attr survived animation: translate(0 28.346456693)
```

The last row is the trap in the row above it, and it was found while writing a deck rather than
by a probe. `transform-box` and `transform-origin` are not declarations *about* the CSS transform
properties: they set the reference frame of the element's whole transform, the `transform`
attribute typst wrote on it included. A translate does not depend on an origin and is
unaffected, which is why the two declarations look free. A reflection is not, and typst
writes `matrix(1 0 0 -1 x y)` on every glyph run it emits, so wherever the two land on a
group typst positioned, that group's content moves by twice the distance from the group's
origin to the centre of its fill box. Nothing errors, no transform property is set at all,
and the displacement differs per run, because each run's fill box is its own.

Consequences: use the individual `translate`/`scale` properties, never the `transform`
shorthand; set `transform-box: fill-box` for scaling, and only on an element Animo built as
a slot. A stray `transform` in user CSS will silently break positioning, and so will a
stylesheet rule broad enough to reach a group typst positioned.

Firefox 153 agrees on every row of the table, including that `fill-box` is what makes a
scale happen in place. It resolves the fill box itself slightly differently: the centre it
scales about sits about **0.7 CSS pixels** from the centre `getBBox` reports, so doubling
an 11-pixel line moves it by that much where chromium moves it by under a tenth of a
pixel. That is invisible in a transition, and it is why the probe for this row allows a
pixel rather than half of one.

Units: CSS lengths inside a group are **user units (pt), scaled by the SVG's rendered
size**.
At the test slide scale, 50 user units measure 72.7 px.
A move expressed in typst lengths therefore stays the same fraction of the slide
at any screen size, for free.

Two further measurements, on chromium 151 and firefox 153, answer what a transform *looks*
like rather than where it lands:

- **A scaled glyph is drawn afresh, not stretched.** The antialiasing band around the ink of a
  line of text, per unit of ink, is 0.20 at scale 1, 0.10 at scale 2 and 0.05 at scale 4: the
  ink grows with the square of the factor while the edge grows with the factor, which is the
  signature of a glyph outline rasterised at the size it ends up at. A picture of the glyph,
  stretched, would keep the ratio constant. Both engines agree to a hundredth. So text under a
  `scale` stays as sharp as text at its own size, and strokes scale geometrically with it.
- **A value under a running animation rasterises as the same value in a style declaration**,
  bit for bit, over a whole 1280 by 720 window. This is what makes the end of a transition
  invisible: a step writes its display state as inline style and animates from the old values
  to it, so at the end the animation stops applying and the style takes over, and nothing about
  the picture changes at that moment. Measured with an animation that holds one value from
  beginning to end, so that nothing but the path through the engine differs.

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

Nothing in the DOM says so. Every value the animation computes is correct at every moment and
`getComputedStyle` interpolates exactly as it should, so the state model and every assertion
about it are unaffected: only the drawing is missing. Anything that makes the page draw brings
it back, including a `requestAnimationFrame` loop and a screenshot, so `page.screenshot` and
`Page.captureScreenshot` cannot see this at all and a recorded video can. That is also what
makes it look like a timing or engine problem rather than a keyframe problem.

So a step animates only the properties it changes.

## The document timeline is not a clock

Measured on chromium 151, firefox 153 and playwright's webkit 26.5, while making a step
animate after a pause.

`document.timeline.currentTime` is the time of the last frame the browser drew, and a browser
with nothing to draw draws nothing. Measured inside a key handler, firefox reports a time 442
ms old after a 250 ms pause and 3181 ms old after a 3 s one, which is the pause itself;
chromium refreshes the time on a read from outside a frame and never lags by more than one,
and webkit reads a lag of exactly zero, after a 3 s pause as much as after a 500 ms one.
Standing still is what the specification describes, since it says the time is updated once
per frame, so firefox is the one that follows it and the other two are the exception.

Giving that time to an animation as its `startTime` therefore starts the animation as far
into its own duration as the page stood still. With a step of 400 ms, anything longer than
that is over before it is first drawn. What a presenter sees is a deck that animates while it
is being clicked through and jumps whenever a slide has been talked over first.

None of this is visible until a frame is drawn, because an animation measures its own current
time against the same timeline: immediately after being stamped it reports zero, and only the
next frame shows where it really is. A test that reads any sooner sees nothing wrong.

So the runtime names no start time at all. Animations created in one task are pending until
the same frame and are then started with that frame's time, which is a shared clock for the
step, arrived at by saying nothing rather than by stamping.

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

This is what makes `fill: none` wrong for a runtime that writes the state it is arriving at
as inline style before it creates the animation, which Animo does
so that the style is the state and the animation only the route to it:
the element would jump to the state the step is going to reach, wait there for the delay,
and then jump back to the start to animate forwards.

`fill: backwards` can be written on every effect and not only on the delayed ones,
because an effect that fills backwards is not in effect once it has finished,
so its animation leaves `document.getAnimations()` exactly as one that fills nothing does.
That is what keeps "is anything still in flight" a question the page can answer.

## A faked clock drives a timer without touching the document timeline

Measured with playwright 1.62 on chromium 151 and firefox 153,
while making a deck that plays itself testable.

A `wait:` is a `setTimeout` in the runtime, and a `setTimeout` is exactly what the browser
harness cannot scrub: an animation can be paused and told where it is, a timer can only
fire. Playwright's own clock is what drives one instead, and it leaves the motion alone.

- **Installed and then paused, the clock stops.** `clock.install()` alone leaves timers
  firing in real time, which is not enough: `clock.pause_at(..)` after it is what stops
  them, and a page left alone for 1.3 s then fires none of its 1 s timers.
- **A timer of zero length gets past the pause while the page is loading.** On a page
  reached by navigation, a `setTimeout(.., 0)` armed by a script in the document fires
  within a few hundred milliseconds of real time although the clock is stopped, where the
  same page's timers of 1 ms, 5 ms and 1 s do not, and where a zero-length one armed once
  the page has settled does not either. The same page loaded with `set_content` holds all
  four. So a test may reach the far side of a zero-length gap and may not expect one to
  stay pending: on a loaded machine a key pressed soon after the deck is opened lands
  inside that window, which is a flaky test rather than a wrong one. A timing test states
  where the deck rests and drives it there with `run_for`.
- **`run_for` follows a chain of timers**, including the ones a fired timer sets, which is
  the shape autoplay has. `fast_forward` does not: it fires each due timer at most once,
  so a page that arms its next timer as it steps advances exactly one place however far
  the clock is jumped.
- **The document timeline is not faked.** An animation created while the clock stands
  still reports 17 ms after the clock is moved ten seconds, and 383 ms (chromium) or
  416 ms (firefox) after 400 ms of real time have passed. So a timed step's motion is real
  motion and is still read by scrubbing it.
- **`requestAnimationFrame` is faked along with the timers**, and stops firing while the
  clock is paused, so a frame cannot be waited for on such a page. Playwright's own
  `wait_for_function` and `wait_for_timeout` are unaffected, because neither runs on the
  page's clock.

## Styling from CSS: what is and is not reachable

Measured on a labelled group whose glyphs carry typst's `fill="#000000"` presentation
attributes:

- A rule on the group's **descendants** wins without `!important`:
  `[data-typst-label="x"] use { fill: rgb(0,128,0) }` gives a computed fill of
  `rgb(0, 128, 0)`. Any CSS declaration outranks a presentation attribute.
- A rule on the **group itself** does not reach the glyphs: the computed fill stays
  `rgb(0, 0, 0)`, because the glyphs' own presentation attribute beats an inherited value.
- `fill` interpolates smoothly: driving it with a paused Web Animations API animation gives
  `rgb(128, 0, 0)` at the midpoint of a black-to-red transition.

So a colour-only primitive is possible and must target descendants explicitly, but anything
beyond fill (weight, size, spacing, strokes, images) is out of CSS's reach and therefore has
to go through a re-rendered epoch. This is what puts `apply` in the structural class and
leaves such a primitive for a later release.

## Cross-frame geometry is readable, so morphing is possible

With two epoch frames in the DOM and both laid out, a label that moves because of reflow
*inside* a region reports both of its geometries to JavaScript: `x=39.49` in the outgoing
frame and `x=523.87` in the incoming one, at identical size. A FLIP-style morph between epochs
is therefore implementable without any help from typst.

Two transform slots are therefore needed, since CSS gives each element only one `translate` and
one `scale`, and nesting supplies the second. `#box(box[Hello world])#label("outer")` emits
`<g transform="translate(..)" data-typst-label="outer"><g>`: the inner group carries **no**
transform of its own. A single `#box[..]` instead emits `<g label><g transform="matrix(..)">`,
whose child is content-dependent and therefore not a slot to rely on. So `tag` wraps its body in
a nested box, which makes `[data-typst-label="x"] > g` a reliable second slot.

**How that geometry is read is not free.** `getBoundingClientRect()` on a labelled group
gives the tight box in chromium 151 and a box inflated to roughly the width of the whole
frame in firefox 153, which paints its ink outside the viewBox because typst writes
`overflow: visible` on the `<svg>`. On the same group chromium reported `19.57 x 13.86`
and firefox `358 x 13.90`. What both engines agree on exactly is `getBBox()`, in the
group's own user units, which are typst points; mapping its corners through
`getScreenCTM()` puts it back in CSS pixels and the two then agree to **0.02 CSS pixels**
on an untransformed group and to **0.7** on one under a CSS scale. So a FLIP morph, and
every test that reads a tag's geometry, uses `getBBox` and the CTM, never
`getBoundingClientRect`.

Which slot takes which class of animation is fixed by the measurement, not by taste: a FLIP delta
is read in the frame's coordinates, so it must be applied above anything that already transforms
the element. The labelled outer group is the boundary slot, the inner group the continuous one
(*Architecture* rule 4).
The alternative leaves both classes on the labelled group and composes them numerically.
It also works, but it obliges the runtime to know the current value of every continuous
property in both frames before it can write a FLIP transform,
which is state the stacked-frame design otherwise never has to keep.

## `hide()` cannot be undone in the browser

Typst's `hide()` lays content out but emits **nothing** to draw: the labelled group is
present but empty (0 glyphs versus 9 for the visible equivalent). So CSS can never reveal
it. In the HTML output, initially-hidden elements must be rendered normally and hidden with
CSS `opacity: 0`; only the paged outputs may use `hide()`.

Note the asymmetry with `remove` and the removed initial state, which are a *content state*:
resolved by typst when the epoch is rendered, so it needs no browser support and cannot be
undone within an epoch.
By construction, undoing it starts a new one.

## A counter reads the same everywhere a slide lays content out

Measured on typst 0.15.0, in both targets.

A counter read with `get()` gives the same value inside an `html.frame` as outside one: a frame
is a container and not a document, so nothing about a counter is reset at its edge. `final()`
resolves in the HTML target as well, inside a frame included, and it resolves before the counter
reaches its own last value, which is the position a slide reads it from.

That is what makes a slide number a counter and nothing more. It is the same in every rendering
of its slide, so it needs no view, no provider and no entry in the plan, and it reads the same
in a slide's body as in a background or an overlay, which in the HTML target are three separate
frames.

A counter read *inside* `measure` resolves at the enclosing context's location, which is the
same rule *Providing a value down the tree* records for a state. For a slide number that is what
is wanted, since the value is constant over the slide, and it is exactly why a value that has to
vary per epoch cannot be carried this way.

## A panic that depends on `query` can be swallowed

Measured on typst 0.15.0, while building a check that two sites of one tag name agree.

A value read with `query` is read once per introspection pass, so a check on such a value
is a check on one pass and not on the document. If that check panics, the panic may never
be reported: the pass that panics produces nothing, the next pass therefore queries a
different document and does not panic, and the two alternate until the iteration limit.
What surfaces is `document did not converge within five attempts` plus a warning that an
element count did not stabilise, pointing at the `query` and saying nothing about the
panic. The compilation succeeds.

A panic in a document that *does* converge is reported normally, so this is not about
panics inside `context` blocks in general. It is about panics whose own effect changes
what the next pass sees, which is what every check on a document Animo also emits amounts
to.

**A check apart from what it checks is reported.** What makes the next pass pass is that the
panic empties the block it is raised in. A check in a context block of its own, emitting nothing
that it reads, changes nothing by failing, and typst keeps only the errors of the pass it ends
on (`crates/typst/src/lib.rs`, where a pass's diagnostics are kept only when it is the last).
So a value that is missing in an early pass is forgotten, and one that is missing for good fails
the last pass and is reported normally, with no convergence warning.

A guard that merely waits for a marker from a separate block is not enough when the check sits
in the block that holds what it checks. It was tried first: a tag nested inside another tag is
reported a pass after the slide's own marker, the check failed in that pass, the panic emptied
the slide, and the site could never appear again, so a valid deck was refused.
Measured on Animo's refusal of a `pan(relto:)` to a tag the slide does not have, in the HTML
target and in both paged modes, on the second slide of a three-slide deck, and on a nested tag,
and on its refusal of an anchor read from inside a tag the timeline moves or scales, which reads
a nested site the same way.
It was first measured while trying to build a refusal of two sites of one name that disagreed
about a `hidden:` argument of `tag`. Animo no longer has that argument, nor that check, because
a tag's initial state is read from its timeline.
So a diagnostic that depends on `query` is either a value Animo resolves or a refusal raised in
a block that emits nothing it reads.

## Introspection: positions

- In **paged** output, positions are available and useful: `query(<tag>)` plus
  `location().position()` returns real coordinates, including for tagged content **inside
  math**. The position of an element is not always its corner, though, which is why
  `pan(relto:)` reads a marker instead of it: see the next entry.
- In **HTML** output, positions are dead: `here().position()` and
  `location().position()` return `(page: 1, x: 0pt, y: 0pt)`,
  *even inside `html.frame`*.
  Verified geometrically, by driving a rectangle's width from `here().position().y`: it
  came out zero-width against a 1 cm control. `query` itself does see inside frames.
- `measure()` **does** work in HTML output and returns real sizes, in paged layout (above).

So the HTML output cannot rely on typst coordinates at all; it relies on the browser's own
layout of the frame SVG, which is why per-element animation is done with CSS rather than
with typst-computed offsets, and why regions are sized by `measure` rather than placed by
coordinates.

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
  corner. So an element's own position does not say where it starts, and no correction by its
  height recovers the corner, since whether one applies depends on what the box sits in.
- **A marker placed at `top + left` inside the box is located at the box's corner**, wherever the
  box sits, and at a negative coordinate when its container is off the page. It takes no room: a
  page rasterises identically with and without such markers at 144 ppi.
- **That corner is the origin of the box's labelled group** in the SVG of an `html.frame`, as
  `group.ownerSVGElement.getScreenCTM().inverse().multiply(group.getScreenCTM())` reads it, to
  0.01 pt in both engines. The group's bounding box is the extent of its ink instead, which is
  a different rectangle.

Consequence: Animo reads a `relto` anchor from such a marker on paper and from the group's origin
in the browser, and the two agree (see *Resolved Design Decisions*).

## Media elements in the HTML output

Measured in chromium on real typst HTML output, for a narration feature that a later release
could add.

- `html.elem("audio", ..)` works as a **sibling of `html.frame`** inside the slide container. It
  must be wrapped in a block-level element, for which a `div` with `display: contents`
  suffices, because `audio` is phrasing content and typst otherwise wraps it in a `<p>`.
- A clip embedded as a `data:` URI decodes fully: `readyState = 4` and `duration = 8.0065s` for an
  8 s Opus file, matching the source exactly. So the browser can supply the timing that typst
  cannot.
- **Autoplay of audible media is blocked until a user gesture**: `play()` rejects with
  `NotAllowedError: play() failed because the user didn't interact with the document`. A
  self-playing deck therefore needs one click to start, which a presentation has anyway.
- **Typst exposes no base64 to scripts.** `to_base64_url` exists only on the Rust side, for images
  (`crates/typst-svg/src/image.rs`), so embedding requires an encoder written in typst. Two traps
  in writing one:
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
every recompile. This is what makes the built-in server sufficient for authoring, and it is why
Animo ships no reload machinery of its own.

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
**identically**. The axis that decides the rendering is not inline versus block but hugging
versus filling: a wrapper at `width: auto` hugs, which left-aligns anything the container was
centring, and `block(width: 100%)` reproduces the original.

A `heading` shifts under *every* wrapper, by about 5 pt. A heading carries its own block spacing
(1.8em above and 0.75em below at level 1, `typst-library/src/model/heading.rs`), that spacing
sits at the wrapper's edge and is trimmed there, and the wrapper contributes the generic 1.2em
instead. Neither `heading.above` nor `block.spacing` is readable from a `context` block, while
`text.size`, `par.spacing` and `heading.numbering` are, so Animo cannot copy the value it would
have to restore. Tagging the heading's text rather than the heading is the way around it,
and it is exact: `= #tag("t")[A heading]` rasterises identically to `= A heading` at 144 ppi,
zero pixels differing over the page. The wrapper is then inside the heading, so nothing sits at
the edge where the spacing lives.

A tagged inline phrase stops breaking across lines, so its paragraph can reflow. That one is
inherent: a group that CSS can translate cannot be split over two lines.

## Inline versus block, decided by measurement

```typ
let nothing = box(width: 0pt, height: 0pt)
let is-block = measure([#nothing#body#nothing]).height > measure(body).height
```

Block-level content pushes the two neighbours onto lines of their own, inline content does not.
Over 31 constructs the separation was **exactly 0.0 pt** for every inline case and **at least
12 pt** for every block-level one, so the comparison needs no tolerance. It needs no available
width either: an unbounded `measure` resolves a `100%` width to zero rather than to infinity, and
every verdict was the same as with a width given.

It sees what inspection cannot. A `context` block reports the block-ness of whatever it
produces. Its one blind spot is content that is itself several paragraphs, which measures as
inline because the neighbours merge into the first and the last paragraph instead of being pushed
off; a scan for a `parbreak` in the body's own sequence covers it.

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
set it again and measure again: both measurements see the same value. That rules the state out as
the channel for anything a region varies while it sizes its footprint.

A marker plus a show rule does work:

```typ
#let ask(f) = context [#metadata(f)<animo-ask>]
#let provide(value, body) = {
  show <animo-ask>: it => (it.value)(value)
  body
}
```

Measured: two `measure` calls in one context block, with different values provided, give
different results. Providers nest and the innermost wins. The rule fires on a marker produced
inside a `context` block, and on a marker inside the content that another marker produced, so
tags may be nested. The marker's own label does not leak: a tag built this way emits exactly one
`data-typst-label`, its own.

It also holds where a region needs it. A region that receives its body as opaque content and
measures it inside `layout(size => ..)` once per epoch, providing a copy of the view with only the
epoch changed, gets a different height per epoch (27.68, 56.45 and 27.68 pt for a short line, a
wrapping replacement and a short line again) and one footprint in all three renderings. The tags
in the body resolve their own content behind nested `context` reads, a tag inside a tag, a tag
removed in one epoch and a region inside a region included, in the paged and the HTML target
alike, with no convergence warning in either.

The channel is also **layout-neutral to the pixel**, which is what lets a tag that emits no
wrapper hand its body back untouched. A body routed through `context`, `metadata` and the show
rule, with no wrapper around it, rasterises identically to the bare body at 144 ppi, zero pixels
differing: measured with a heading between two paragraphs, which is the case a wrapper would
betray, since a wrapper trims the heading's own block spacing at its edge.

One thing does not work. A marker that no provider replaced is **not** distinguishable
afterwards: `query(<animo-ask>)` returns replaced and unreplaced markers alike. So "this tag is
outside any slide" has to be diagnosed at the tag site, from a state that `slide` sets around its
body, and not by a sweep at the end of the document.

## A cetz draw command is a value, not content

Measured against cetz 0.5.2 on typst 0.15.0, while settling whether raw draw commands can be
tagged. This is what decides that they are refused.

- A draw command is an **array of closures**: `draw.grid((0,0), (4,2))` is an `array` whose
  every element is a `function`, and so is `draw.stroke(red)`, so a command that changes the
  draw state and one that emits geometry have the same shape and neither is a special case of
  the other. The array is built where it is written, by ordinary evaluation, before
  `cetz.canvas` is called.
- A canvas body **cannot hold content at all**. A `context` block, or any other content, beside
  a draw command fails with `cannot join array with content`. So no marker can sit in the
  stream, and a `region` there is the same type error rather than merely a useless one.
- What a canvas *does* lay out as content, a `content()` element, is reached by a show rule
  installed **outside** the canvas: a labelled box produced by such a rule inside `content()`
  emits its group in the SVG. That is why a tag on a cetz `content()` element resolves its
  content for the epoch exactly as a tag anywhere else does.

Together these say that the channel of the previous finding cannot reach a draw command, and
that no other channel can either: varying the array per epoch would mean re-evaluating the block
that built it, which only a body that is a function of the subslide can do. `sanor` has exactly that
body, which is how `test/draw.typ` reaches a tagged `draw.grid(..)`.

## Transforms between a tag's slots are layout-neutral

`box(move(dx: .., dy: .., ..))`, `box(scale(.., reflow: false, ..))` and `box(hide(..))` measure
identically to `box(..)`, in width, in height and in their effect on the line around them, even
though `move` and `scale` are themselves block-level elements. The same holds for
`block(width: 100%, move(..))` against `block(width: 100%, ..)`.

This is what lets the static presentation apply a state's display state with typst's own elements
without disturbing the layout, and it is what makes "nothing moves between states except what the
timeline moves" an invariant rather than an assumption. A tag site emits the same structure in every
state and in both targets; only the parameters inside it change.

**The measurement is of the size a slot takes, and it says nothing about where the content inside
it lands.** A `move` is laid out as an inline element, so a block-level payload inside one is laid
out in a paragraph rather than as a block, and it is aligned to the paragraph's start instead of
filling the container. Measured on typst 0.15.0 at 144 ppi, over the centred bodies of *Wrapping a
tag site*, against the page that holds the body with no wrapper at all:

| Nesting                                                  | Renders          |
| -------------------------------------------------------- | ---------------- |
| `block(width: 100%, block(width: 100%, move(scale(x))))` | left-aligned     |
| `block(width: 100%, move(scale(block(width: 100%, x))))` | identical, tol 1 |

So the display state goes **around** the inner slot rather than inside it. The filling block that
*Wrapping a tag site* calls for then sits inside the `move` and fills the paragraph the `move`
opened.

**A rendering that carries a display state is layout-neutral only inside a slot.** The outer slot
holds a `move`, which is block-level and therefore a block of its own, so the size that slot takes
is the same either way. The extent of a rendering measured on its own differs. `measure` reports a
height and no baseline, so a descent is read off a line that holds the content beside a zero-width
pole taller than it, and a block-level body pushes that pole onto a line of its own.
Measured on typst 0.15.0, over the word `hidden` at 11 pt:

| Measured                   | Ascent   | Descent  |
| -------------------------- | -------- | -------- |
| `box(move(scale(box(x))))` | 7.24 pt  | 0 pt     |
| `move(scale(box(x)))`      | -13.2 pt | 20.44 pt |

The height is the same either way, so a footprint over renderings that all lay something out is
unaffected. An epoch that lays nothing out has an extent of zeroes, and the largest ascent is then
zero while the largest descent is still a line, which makes the footprint a line taller than the
content it holds and lowers the rendering inside it by the same amount. So `inline-region`
measures every rendering inside a box.

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

Together these make the display state that a tag site actually applied assertable at tier 1,
with nothing exported: in the presentation mode, where each state is a page, occurrence *i* of a
tag in a one-slide document is its rendering in state *i*, and `move`'s `dx`, `scale`'s `x` and
the presence of a `hide` say what that state did to it.

## Other verified behaviour

- `target()` returns `"html"` or `"paged"`, which is the clean way to branch. The
  `dictionary(std).at("html", default: none)` idiom in `slipst` is a compatibility hack for
  older typst versions and is not needed here.
- `set page(...)` is **ignored** in HTML export at document level (typst warns) and is an
  error inside `html.frame`. Slide size, background colour and background image must be
  emitted as CSS for the HTML target, and the slide itself is a sized `block`.
- HTML export still requires `--features html` in typst 0.15.0 and prints an
  "under active development and incomplete" warning.
- `html.elem` takes its attributes as a dictionary in the `attrs:` argument; `html.div(..)`
  and friends do not accept `attrs:`, so Animo should use `html.elem` for anything with
  data attributes.
- Multi-page SVG export fails without a page-number template (`{p}`/`{0p}`) in the output
  path.
- A document that lays nothing out is **not refused**: typst 0.15.0 compiles it to one blank
  page at its own default size, A4. So a handout whose every state gave up its page produces
  a blank page at a size the deck never mentioned, rather than an error.
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
  `anim` module (`anim` reports as a `module`). Three usage forms all work: `import anim: *`
  inside the animation block, a named import (`#import "@preview/animo:0.1.1": sub, tag, anim`), and fully-qualified calls (`anim.reveal("a")`) with no inner import at all.
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
  browsers. Stacking order is therefore fixed at compile time. This is accepted: z-order
  changing animations are out of scope and can be simulated without reordering. Note that
  epoch frames are stacked as *HTML* elements, where the grid and `opacity` do apply.
- `animo` is unused on Typst Universe (`packages/preview/animo` returns 404).
