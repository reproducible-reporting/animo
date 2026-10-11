---
description: >-
  How the browser runtime of the HTML presentation is built: the elements and attributes of
  the page, the files of the runtime and where each part of the design lives in them,
  and the controller with the events it announces and the input it reads.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# The Browser Runtime

The HTML presentation is a single self-contained file,
and its script is the browser runtime of Animo.
This page describes how that runtime is built:
the elements and attributes it finds on the page, the files it is written in,
and the controller that turns input into steps and announces them as events.
The *Architecture* section of the design document specifies what the runtime does in a step,
and why.
See [Where the Specification Lives](development.md#where-the-specification-lives)
for where to find the design document.

## The Page

The page nests three kinds of element, as `.animo-deck > .animo-stage > .animo-slide`.
The deck element has one child, the stage element,
and every slide container is a child of the stage element.
A slide container holds up to three elements in this order:
`.animo-background`, `.animo-canvas` and `.animo-overlay`.
The canvas is always present, and holds one `html.frame` that contains the whole body of the slide.
A background or an overlay made of content is a frame inside
`.animo-background` or `.animo-overlay`.
A color background is a declaration on the slide container,
and a color overlay is a declaration on the `.animo-overlay` element.

The runtime reads the attributes below.
When a step does not do what the timeline says,
inspect these attributes in the developer tools of the browser.

- Every slide container carries `data-animo-slide`, which holds the position of the slide
  in the deck, and `data-animo-states`, which holds the number of states of the slide.
- Every slide container also carries `data-animo-plan`,
  which holds the resolved display state of every state of that slide as JSON.
  The browser receives no other information about the timeline.
  When a step goes wrong, this attribute therefore shows whether typst resolved a wrong plan
  or the runtime applied a correct plan wrongly.
- Every slide container carries `data-animo-transition`,
  which names the transition at the slide boundary that leads into this slide.
  When that transition has parameters, `data-animo-transition-args` holds them.
- The deck element carries `data-animo-config`, which holds the settings of the deck as JSON.
  The runtime reads this attribute once, at load.
  The setting `transition` is the transition of every slide whose `init` names no transition.
- The root element carries `lang`, and the head carries a `<title>`.
  They come from `set text(lang: ..)` and `set document(title: ..)`,
  in the same way as in a page whose head typst builds.

The runtime writes the attributes below while it shows the deck.

- `data-animo` on the root element holds the position that the runtime has reached,
  in the same form as the fragment of the URL.
- `data-animo-mode` on the root element holds the name of the active mode.
- `data-animo-paused` is present on the root element while the clock of the deck is stopped.
- `data-animo-current` marks the slide that is shown.
- `data-animo-leaving` and `inert` mark the slide that a slide transition is leaving.

## The Files of the Runtime

Because the HTML output is a single self-contained file,
its script cannot import modules from other files.
The runtime is written as the files under `src/js`.
`src/deck.typ` reads these files in a fixed order
and joins them into the single `<script type="module">` of the page.
The files therefore share one module scope.
Function declarations are hoisted,
so a function in one file can call a function declared in any other file.
A top-level `const` is initialised only when the script reaches the file that declares it,
so code that runs at load time can use a `const` only from its own file or from an earlier file.
`boot.js` is the last file, and the only file that calls into the other files at load time.

| File            | Holds                                                                        |
| --------------- | ---------------------------------------------------------------------------- |
| `slides.js`     | `config`, `readSlide`, the registry of slides, `count`, `clamp`, `parseHash` |
| `stacks.js`     | the kinds of stack, `readStacks`, `planStacks` and the subslide stack        |
| `effects.js`    | `timing`, `scheduled`, `span`, `showing`, `plan` and `apply`                 |
| `display.js`    | positions and anchors, the CSS of a display state and a pan, `planState`     |
| `boundaries.js` | the transitions of both boundaries, `planBoundary` and `planEpoch`           |
| `paths.js`      | `alignPaths`, which rewrites two paths into one structure                    |
| `morph.js`      | the matches of a morph, their routes, and `settleMorphs`                     |
| `controller.js` | the position, `show`, `step`, `jump`, and the clock with its pause           |
| `input.js`      | key, pointer and hash events, turned into intents by the active mode         |
| `boot.js`       | preparing the page, reading the slides and the first `jump`                  |

Each part of the design is implemented in one place, as listed below.

- **Stacks.**
  `src/stack.typ` builds the epoch stacks and the subslide stacks,
  and `src/region.typ` and `src/tag.typ` place an epoch stack when their view asks for one.
  In the browser, `readStacks` finds every stack of a slide by the labels of its renderings.
  `stackKinds` defines, for each kind of stack, how the runtime plans that stack for a state.
- **The two phases of a step.**
  `plan` in `effects.js` records one effect per element and property,
  and writes nothing to the page.
  `apply` then writes the styles of the step and creates its animations.
  `PROPERTIES` lists the properties whose unset value the browser reports as a keyword,
  such as `none` for `translate`, together with the value that this keyword stands for.
- **Epoch boundaries.**
  `planBoundary` finds the stacks that a step carries.
  It gives each of these stacks the record of the first tag that the boundary changes in it,
  together with `names`, the list of every tag that the step changes in the stack.
  `differs` compares the renderings of a stack on the two sides of a boundary.
  `planEpoch` then plans every epoch stack.
  It hands each carried stack to the entry of `transitions` that the record of the stack names,
  or to `crossfade` when the record names no transition.
- **The hand-over.**
  `handOver` plans how every transition hands a region from one rendering to the other.
  The rendering that comes first in the document is drawn below the other and stays opaque,
  and the rendering above fades in or out.
  A transition gives `handOver` the pairs of elements that draw the same ink at one place:
  `inPlace` finds them for a crossfade, by comparing attributes, and the morph has its matches.
  `handOver` hides the copy above of every identical pair, so the shared ink is drawn once,
  and fades the ink of the rendering below that has no partner.
  `gathered` hides or fades a group as one when all its children are hidden or faded.
  `settleHandOvers` takes what an earlier hand-over hid or faded back to rest at every step.
  No rendering blends and no stack isolates, because firefox draws every frame of a
  transition several times more slowly then (see [Performance](performance.md)).
- **Slide boundaries.**
  `slideTransitions` holds one entry per slide transition.
  Each entry gives the display state of the slide that owns the transition
  and of the other slide, at the start and at the end of the transition.
  `slideTransitions` is a separate table from `transitions`,
  because a slide transition receives two slide containers rather than the renderings of a region.
- **The morph.**
  `morphStack` in `morph.js` plans the routes of the matches of a morph, and hands them to
  `handOver`.
  `commonSubsequence` pairs the drawn elements (the ink) of the two renderings,
  using the keys that `inkKey` and `clipsAbove` compute.
  `commonSubsequence` gives up when the renderings have more than `MORPH_DIFFERENCES` differences.
  `resizes` finds the paths that a morph resizes, with the help of `pathStructure`,
  `labelsAbove` and `sameFrame`, and `shapeMorphs` finds the shapes that a morph turns into
  another shape.
  Both kinds of morph run only in an engine that animates `d`, which `RESIZES` records.
  `alignPaths` in `paths.js` reads nothing from the DOM, so its tests work on numbers only.
  `slide.morphed` holds every element that a morph is still moving.
  At every step, `settleMorphs` reads `slide.morphed` before any transition is planned.
  A copy that `handOver` hides takes no route, and `slide.standIns` records the copy below
  that shows it, which `displayed` reads when a later step starts a route from it.
- **Shared definitions.**
  `hoistPaintServers` in `boot.js` copies the SVG definitions that several slides share,
  such as gradients and patterns, into one `<svg>` before the first slide is read.

## The Controller and Its Events

`controller.js` holds every piece of state that the runtime keeps between two inputs:
the position, the direction of travel, the pending step, the reasons the clock is stopped,
and the active mode.
`show` is the only function that writes the position.

The controller announces each change as an event on the root element.
It dispatches the event only after it has updated the DOM, the fragment,
the `data-animo` attribute and the clock,
so a listener finds the page in the state that the event describes.
The events bubble, so a listener on the root element, on the document or on the window
receives them.

| Event            | Detail                 | Dispatched                                                                 |
| ---------------- | ---------------------- | -------------------------------------------------------------------------- |
| `animo:leave`    | `{slide}`              | when the new position is on another slide; `slide` is the previous slide   |
| `animo:enter`    | `{slide}`              | in the same case, and for the first position; `slide` is the slide entered |
| `animo:position` | `{from, to, animated}` | after every position that is shown                                         |
| `animo:mode`     | `{from, to}`           | when the active mode changes; `from` and `to` are the names of the modes   |

A position is `{slide, state}`.
For a change of slide, the events come in the order `leave`, `enter`, `position`.
For the first position of the page, the controller dispatches `animo:enter` and
`animo:position` without an `animo:leave`, and `from` is `null`.
The controller also announces the mode that the page starts in, with a `from` of `null`.
`animated` is true when a step reached the position and the deck lets its motion run.
`animated` is false for a deep link, for `Home` and `End`, for a cut,
and for a viewer who asked for reduced motion.
A join (a gap of zero) consists of two steps that the clock makes,
and the controller announces each of them.

The runtime reads input according to the active **mode**, an object `{name, keymap, pointer}`.
`keymap` maps `event.key` to an intent,
and `pointer` maps the type of a pointer event to an intent.
The intents are `next`, `previous`, `first`, `last` and `toggle-pause`,
and the controller implements each intent as one entry of its `intents` table.
The only mode is `present`.
In `present`, `Space` means `toggle-pause` while the deck has a clock to pause,
and `next` otherwise.

The clock of the deck is stopped while at least one **hold reason** is held.
The pause key holds the reason `user`.
Backward travel that comes to rest at the first state of the deck holds the reason `travel`,
and the next forward step releases it.
When either reason is held, the pause key releases both.
When neither reason is held, the pause key holds `user`.

The runtime confines its effects to the deck in the following ways.

- Only the current slide receives pointer events.
  The slide that a slide transition is leaving stays laid out,
  so that a step back finds it laid out,
  and that slide is `inert` for as long as the transition leaves it.
- A key press or a click whose target is inside an element with the attribute
  `data-animo-control` does not step the deck.
- The pause key pauses and resumes only the animations that the runtime created,
  which carry the id `animo`.
  Every other animation on the page keeps running.
