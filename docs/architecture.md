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

The HTML presentation is one self-contained file,
and its script is the browser runtime of Animo.
This page describes how that runtime is built:
the elements and attributes it finds on the page, the files it is written in,
and the controller that turns input into steps and announces them as events.
What the runtime does in a step, and why,
is specified in the *Architecture* section of the design document,
which is the reference for any change in behaviour.
[Developing Animo](development.md) says where the design document lives.

## The Page

The slides are the children of one stage element, which is the only child of the deck element,
so the page is `.animo-deck > .animo-stage > .animo-slide`.
A slide container holds up to three elements in this order:
`.animo-background`, `.animo-canvas` and `.animo-overlay`.
The canvas is always there, and holds one `html.frame` with the whole body of the slide.
A content background or a content overlay is a frame in its own element.
A color background is a declaration on the slide container,
and a color overlay is a declaration on the `.animo-overlay` element.

The runtime reads a few attributes, which can also be read back in a browser's inspector
to diagnose a step that does not do what the timeline says.

- Every slide container carries `data-animo-slide` and `data-animo-states`,
  which are its position in the deck and how many states it has.
- Every slide container also carries `data-animo-plan`,
  which holds the resolved display state of every state of that slide as JSON.
  This attribute is the whole of what the browser is told about the timeline,
  so a wrong step is either in this attribute or in the runtime, and the attribute shows
  which.
- Every slide container carries `data-animo-transition`, which is how the boundary into it is
  crossed, and `data-animo-transition-args` with the parameters of that transition
  when it has any.
- The deck element carries `data-animo-config`, the settings of the deck as JSON,
  which the runtime reads once at load.
  Its one setting is `transition`, the transition of every slide whose `init` names none.
- The root element carries `lang`, and the head a `<title>`, from `set text(lang: ..)` and
  `set document(title: ..)`, as typst writes them into a head it builds itself.

The runtime writes these attributes while the deck is shown.

- The root element carries `data-animo` with the position the runtime has reached,
  which is the same value as the fragment,
  `data-animo-mode` with the name of the active mode,
  and `data-animo-paused` while the clock of the deck is stopped.
- The slide that is shown carries `data-animo-current`,
  and the slide a boundary is crossing from carries `data-animo-leaving` and `inert`.

## The Files of the Runtime

The HTML output is one self-contained file, so its script cannot import its parts.
The runtime is the files under `src/js`, which `src/deck.typ` reads in a stated order
and joins into the one `<script type="module">` of the page.
The files share one module scope.
Function declarations are hoisted, so a function may call one from any file at any time.
A top level `const` is initialised when the script reaches its file,
so a file may use one at load time only if it comes after the file that defines it.
Only `boot.js` calls into the other files at load time, and it is the last one.

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

Each part of the design has one place in these files.

- **Stacks.**
  `src/stack.typ` builds the epoch stacks and the subslide stacks,
  and `src/region.typ` and `src/tag.typ` place an epoch stack when their view asks for one.
  In the browser, `readStacks` finds every stack of a slide by the labels of its renderings,
  and `stackKinds` says how each kind of stack is planned for a state.
- **The two phases of a step.**
  `plan` in `effects.js` records an effect per element and property and writes nothing,
  and `apply` writes the styles of the step and creates its animations.
  `PROPERTIES` lists the properties whose unset value the engine reports as a keyword,
  such as `none` for `translate`, with the value that keyword stands for.
- **Epoch boundaries.**
  `planBoundary` finds the stacks that a step carries,
  and gives each the record of the first tag that the boundary changes in it,
  together with `names`, which lists every tag that the step changes in the stack.
  `differs` compares the renderings of a stack on the two sides of a boundary.
  `planEpoch` then plans every epoch stack,
  and hands each carried stack to the entry of `transitions` that its record names,
  which is `crossfade` when the record names none.
- **Slide boundaries.**
  `slideTransitions` holds one entry per transition of a slide boundary,
  which gives the display state of the owner and of the other slide at both ends.
  It is a separate table from `transitions`,
  because a slide transition is handed two containers rather than the renderings of a region.
- **The morph.**
  `morphStack` in `morph.js` adds the matches to the crossfade of a stack.
  The ink is paired by `commonSubsequence` over the keys that `inkKey` and `clipsAbove` write,
  and gives up above `MORPH_DIFFERENCES` differences.
  The resizes, from `resizes` with `pathStructure`, `labelsAbove` and `sameFrame`,
  and the shape morphs, from `shapeMorphs`, run only where `RESIZES` says the engine animates
  `d`.
  `alignPaths` in `paths.js` reads no DOM, so its tests run on numbers.
  `slide.morphed` holds every element that a morph is still moving,
  and `settleMorphs` reads it at every step, before any transition plans.
- **Shared definitions.**
  `hoistPaintServers` in `boot.js` copies the definitions that slides share into one `<svg>`
  before the first slide is read.

## The Controller and Its Events

`controller.js` holds every piece of state that the runtime keeps between two inputs:
the position, the direction of travel, the pending step, the reasons the clock is stopped,
and the active mode.
`show` is the only function that writes the position.

The controller announces what happened as events on the root element,
after the DOM, the fragment, the `data-animo` attribute and the clock have been written.
A listener therefore finds the page in the state the event describes.
The events bubble, so a listener on the root element, the document or the window receives them.

| Event            | Detail                 | Sent                                                                               |
| ---------------- | ---------------------- | ---------------------------------------------------------------------------------- |
| `animo:leave`    | `{slide}`              | when a position is on another slide than the previous one, with the previous slide |
| `animo:enter`    | `{slide}`              | in the same case, and for the first position, with the slide entered               |
| `animo:position` | `{from, to, animated}` | after every position that is shown                                                 |
| `animo:mode`     | `{from, to}`           | when the active mode changes, with names as values                                 |

A position is `{slide, state}`.
For a change of slide the events come in the order `leave`, `enter`, `position`.
The first position of the page enters its slide and leaves none, and its `from` is `null`.
The mode the page starts in is announced in the same way, with a `from` of `null`.
`animated` is true when the position was reached by a step and the deck lets motion run.
It is false for a deep link, `Home` and `End`, for a cut, and for a reader who asked for
less motion.
A join, which is a gap of zero, is two steps made by the clock, and each is announced.

Input is read in a **mode**, which is `{name, keymap, pointer}`.
The keymap maps `event.key` to an intent, and the pointer table maps the type of a pointer
event to one.
The intents are `next`, `previous`, `first`, `last` and `toggle-pause`,
and the controller offers each of them as one entry of `intents`.
The one mode is `present`, and `Space` in it is `toggle-pause` while the deck has a clock
to pause and `next` otherwise.
The root element carries the name of the active mode as `data-animo-mode`.

The clock is stopped while a set of **hold reasons** is not empty.
The pause key holds `user`.
Backward travel that runs out of deck holds `travel`, which the next forward step releases.
The pause key releases both, and it holds `user` when neither is held.

The runtime acts only on what belongs to the deck, in these places.

- Only the current slide takes pointer events.
  The slide a boundary is crossing from stays laid out so that stepping back finds it laid out,
  and it is `inert` for as long as it is the slide being left.
- A key press or a click whose target is inside an element with the attribute
  `data-animo-control` does not step the deck.
- The pause key pauses and resumes the animations that the runtime created,
  which carry the id `animo`, and leaves every other animation of the page running.
