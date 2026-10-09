---
description: >-
  How a slide becomes an HTML presentation: the epoch stacks, the five rules the
  browser runtime obeys, the two transform slots of a tag site,
  where the transition of a boundary is selected, the two phases of a step,
  and how the runtime is divided into files, a controller and events.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Architecture of the HTML Output

How a slide reaches the browser, and what the runtime is allowed to do there.
This page follows the *Architecture* section of the design document,
and every measurement cited here is an entry of *Findings* with a probe under `probes/`.
[Developing Animo](development.md) says where both documents live.

## What Typst Emits

The slides are the children of one stage element, which is the only child of the deck element,
so the page is `.animo-deck > .animo-stage > .animo-slide`.
The deck fills the window and centres the stage.
The stage is as large as the window allows at the deck's aspect ratio.
The stage clips its content and is an isolated stacking context.
A slide is one container element in the stage, as large as the stage,
and the container carries the plan of the slide as JSON in `data-animo-plan`.
Inside the container, a `.animo-canvas` element holds **one `html.frame` for the whole slide**,
in which the body is laid out **once**.
Every region whose content changes, explicit or the implicit one of a tag, holds
**one rendering of its body per epoch**, placed at one point of its footprint in epoch order.
Each rendering is a labelled block, so it becomes a `<g data-typst-label="animo-epoch-N">`
the runtime can show, hide and blend.
Only a region that sits in no other region does this.
A region inside the rendering of another region is already laid out once per rendering,
so the inner region lays out the epoch of that rendering.
A slide has one frame rather than one per region, because the scope of typst's deduplicator
is the frame.
The renderings of a slide then define each glyph they share once between them instead of
once each.
The slide container clips the canvas.
The container also carries `data-animo-transition`, which is how the boundary above the
slide is crossed, as the slide's `init` says.
The transition is one value per slide, so it is an attribute of the container,
like the plan itself, rather than an entry in the plan.

The renderings of a region are one kind of **stack**.
A stack is a set of renderings placed at one point, of which the runtime shows one at a time.
Every rendering of a stack is labelled `animo-<kind>-<index>`,
and the renderings of one stack are the children of one group.
The kind says what the index counts.
The renderings of a region are its `epoch` stack,
and every `per-subslide` is a `subslide` stack with one rendering per state of the slide.
`src/stack.typ` builds both kinds, and `src/region.typ` and `src/tag.typ` place an epoch stack
when the view they are handed asks for one, which only the HTML target does.
`readStacks` in `src/js/stacks.js` finds every stack of a slide by its labels,
and `stackKinds` plans each stack for a state by its kind.
An epoch stack is planned by `planBoundary` and `planEpoch` and the transitions of its
boundaries, and a subslide stack snaps to the rendering of the state and hides the others.

An epoch is a run of consecutive states in which no content changes,
so a slide with no structural operation holds no epoch stack
and the machinery itself adds no cost.
A region reserves the same footprint in every epoch,
so what is around it is laid out once for all of them.

A region inside an epoch stack is laid out once per rendering,
and still gets the same number as on paper, where only one rendering is laid out.
Such a region counts on a second counter, which every rendering sets back to zero.
Its number is the number of the region holding the stack plus the value of that second counter.
Every update of either counter is a constant or a step,
so the numbers settle in one pass of layout however many regions a slide has.

The plan holds one entry per state, with the display state of every addressed tag,
the pan, the epoch the state belongs to,
and the `handout` flag as the paged outputs resolve it;
and one entry per epoch, naming in `changed` the tags that the boundary into it changes.
Each name carries the name of the `transition` its operations named, which is left out
for `auto`, so a deck that names none carries none.
A record also carries `args` when the transition has parameters,
which the runtime hands to the transition with the record.
The runtime finds the stacks a boundary crosses by itself:
a stack holds the group of every tag laid out in it,
and its region's own label when the region is a tag.
A `wrap: none` tag becomes no group, so an epoch entry also holds `regions`,
which names such a tag by the label of the group of the region that holds its stack.
Typst derives `regions` from the membership reports that every tag site and region writes,
and leaves `regions` out when every changed tag has a group.

A state also carries the `wait:` before it is entered, the `hold:` before the next state is
entered, and the timing of the operations its own subslide performed.
A name in an epoch's `changed` carries the timing of the operation that changed the tag.
All of these are in seconds.
None of them can be resolved anywhere but at the moment the step runs.
Both gap numbers travel rather than one resolved number per gap, because the gap across a
slide boundary is timed by two slides and the runtime is the first place that sees both
sides of it.
Each is left out when it says nothing, so a deck that times nothing carries no timing at
all, and a missing record reads as "starts with its step".
A per-operation timing is a record rather than a bare number, because that is the shape
the Web Animations API takes.

A tag's display state holds its visibility, one factor per axis, and its **position**,
which is an anchor and an offset per axis rather than a displacement:

```json
{
  "hidden": false,
  "x": {
    "relto": "node",
    "offset": 14.17
  },
  "y": {
    "relto": null,
    "offset": 0
  },
  "scale": {
    "x": 2,
    "y": 1
  }
}
```

The runtime resolves it as `anchor(relto) + offset - anchor(self)`, where the anchor of
`null` is the canvas origin, so a pair naming the tag's own name is the identity and needs
no anchor at all. The pan travels the same way, with the canvas origin for its own anchor.
The offsets are in typst points, which are the user units of a frame's SVG.

The anchors themselves cannot travel, because a tag's position does not exist in the HTML
target.
The runtime measures the anchors that the plan names when the slide is first shown,
before the runtime has written anything on the slide.
It reads each anchor off the origin of the tag's labelled group,
mapped into the user space of the frame.
Typst reads the same corner on paper, off a zero-size marker that each tag site places inside
its outer slot.
The two measurements agree to within a thousandth of a point.

## What a Step Animates

Stepping to the next subslide animates every tag the step changed,
from what it was showing to what the new state says, and stepping back animates it back.

| Primitive        | What the browser animates                                |
| ---------------- | -------------------------------------------------------- |
| `reveal`, `hide` | `opacity` between 0 and 1                                |
| `move`           | the CSS `translate` property                             |
| `scale`          | the CSS `scale` property, about the element's own centre |
| `pan`            | the CSS `translate` property of the canvas               |

A step across a slide boundary animates too, but it moves nothing:
it crossfades the two containers.
The slide being entered is already in its subslide state when it comes into view.

A deep link, the first paint and a jump that is not a step across one boundary never animate,
because the audience has not seen the steps that lead to the state they would animate into.
A deep link includes the one that `typst watch` reloads into.
The first paint is a deep link to wherever the fragment points.
`Home` and `End` are jumps.

The deck's `primitive-duration:` and `transition-duration:` are defaults,
which a `duration:` written in the timeline overrides, also when the default is zero.
A reader who has asked their system for reduced motion therefore needs a signal of their own,
because a media query cannot reach a number written in a typst source.
Animo's own stylesheet sets `--animo-motion: none` under `prefers-reduced-motion: reduce`,
and the runtime snaps every step while it is set.
The declaration is `!important`, because a stylesheet added to the page comes after Animo's
own stylesheet and would otherwise outrank the declaration.
A step that lands without motion lands whole,
so the `delay:` and the `duration:` of every operation are ignored.
A `wait:` and a `hold:` are not touched, because zeroing them would run an autoplaying deck
through itself at once.

## The Five Rules

**1. Continuous state is applied to every rendering of every stack at once.**
The hidden renderings receive it as well as the one being shown.
Entering an epoch then needs no initialisation,
and a step that both replaces and moves a tag moves it by the same amount in the rendering
it leaves and in the one it arrives at, so the composite stays registered.
An operation on a tag that is absent from a rendering is a no-op there.

**2. The crossfade is scoped to the regions whose content changed.**
Only the epoch stacks of those regions animate, and every other stack takes the rendering of
the epoch being entered at once, which is the same picture.
Two things make the containment exact:

- A stack holds nothing but its region.
  Its renderings are the region's body laid out once per epoch,
  so the outgoing rendering has no ink outside the region's footprint.
  A rendering that is not being shown is `visibility: hidden` rather than `display: none`,
  so that it stays laid out and its geometry stays readable.
  A boundary crossed while an earlier boundary is still running finds more than one rendering
  painting the region.
  Every rendering that is still painting therefore takes part, not only the one being left,
  and they all fade out on the new boundary's clock, so the region's ink stays at one.
- `mix-blend-mode: plus-lighter` on the renderings makes the two halves add, and
  `isolation: isolate` on the group that holds them keeps the sum inside the stack.
  Without the isolation, chromium 151 and webkit 26.5 add the two halves to the ink under the
  region as well, and black text takes the colour of what is behind it.
  The frame isolates too, which keeps the blend off the page behind the slide.

A stack crosses a boundary when the boundary changes a tag it holds,
or a tag without a group that the plan places in its region.
A stack also crosses a boundary when its renderings on the two sides of the boundary differ.
The function `differs` detects that once, by comparing their children,
and such a stack takes the deck's own timing.

**3. Only the individual transform properties, never the `transform` shorthand**,
which would clobber the positioning typst wrote into the SVG.

**4. Continuous state and boundary state get separate nested slots.**
Every tag site emits a labelled outer group with an unlabelled inner group inside it.
Continuous primitives address the inner group (`[data-typst-label="x"] > g`);
anything belonging to an epoch boundary addresses the labelled outer group.
CSS gives an element one `translate` and one `scale`, so the split is what keeps the two
classes of effect from overwriting each other.
The order follows from how a boundary effect is measured:
it is measured in the frame's own coordinates
and has to sit above the continuous transforms rather than inside them.

**5. `pan` belongs to the canvas element, not to what is inside it.**
The body and its stacks sit in the frame the canvas holds, so moving the canvas moves all of
them together and keeps them registered.

## Where the Transition of an Epoch Boundary Is Selected

`transitions` in `src/js/boundaries.js` holds one entry per transition of an epoch boundary,
and the record of each stack a boundary crosses names the entry that carries it.
A record that names none takes `crossfade`.
The author names a transition with the `transition:` argument of a structural operation,
so one boundary may carry one region with one transition and another region with another.
Typst refuses a transition that is not in `region-transitions` in `src/transition.typ`.
It also refuses two operations that change one region at one boundary and name two different
transitions.
Here a region means the outermost region, because the outermost region holds the stack.

`planBoundary` runs once per slide and step, before any stack is planned.
It finds the stacks that the step carries.
Each such stack gets the record of the first tag that the boundary changes in the stack,
together with `names`, which lists every tag that the step changes in the stack.
It then settles what an earlier morph is still moving, as the next section says.
`planEpoch` then plans every epoch stack for every transition alike.
The rendering of the state being shown is visible and opaque,
and every other rendering is hidden and transparent.
A stack the step carries is handed to the transition its record names,
together with the epoch the step leaves and the one it enters, and how the step moves.
A step that crosses no boundary carries no stack,
which is what a deep link, a step inside one epoch, and a reader who asked for less motion
all produce.

A transition plans the state it is arriving at for the elements it carries,
in place of their state at rest,
and animates from what the element was showing into it,
exactly as a display state is planned.
An interrupted boundary therefore continues from where it is,
and a backward step lands on the earlier rendering exactly.
A transition runs while the step is planned and nothing has been written,
so the geometry it reads is the geometry of the page before the step.

## The Morph

`morph` in `transitions` plans the crossfade of its stack and then calls `morphStack` in
`src/js/morph.js`, which adds a `translate` animation to each **match** in the two renderings
the step runs between.
A match is a pair of elements, one in the outgoing region and one in the incoming one.
Tags come first: two labelled groups of one name, paired by index in document order,
and translated on their outer slot.
A tag whose name is among the `names` of the stack's record is one the boundary changes,
and neither that tag nor a group that holds it is matched as a whole.
Then the ink is matched.
The ink is every `<use>`, `<path>` and `<image>` element outside every matched group,
in document order and outside every `<defs>`, `<clipPath>` and glyph `<symbol>`.
The ink is paired by `commonSubsequence`, a diff of the Myers kind over one key per element.
`inkKey` writes the key from what the element draws apart from its place and its colour.
For a glyph that is the `href`.
For a path it is the `d` and the stroke attributes other than the colour,
because typst writes every shape from its own origin and puts its place in a `transform`.
For an image it is the `href`, the `width` and the `height`.
`clipsAbove` appends the clips between the element and its region, each with its place on
the screen, so that a match never moves under a clip that is in another place in the other
region.
The same rule applies to a tag match.
Each distinct key is replaced by a small integer before the diff, which then compares
numbers.
Above `MORPH_DIFFERENCES` differences the diff gives up and the ink is crossfaded.
The glyphs of one text run that all travel the same distance are carried by one animation
on the run instead of one each.

Then come the resizes, in an engine for which `CSS.supports` accepts `d` (`RESIZES`).
`resizes` takes the paths the ink diff left over between two consecutive ink matches, which
form a hunk, and pairs them by a second `commonSubsequence` per hunk over a structure key.
`pathStructure` writes that key from the command letters of the `d`, the count of its
numbers and the stroke attributes other than the width, and `matches` appends the clips
and `labelsAbove`, the labels of the groups between the path and its region.
`sameFrame` drops a pair whose two user spaces differ in more than a translation.

Last come the shape morphs, in the same engines.
`shapeMorphs` takes the paths left over after the resizes and assigns each to the tag it
belongs to, which is the nearest labelled group above it that is not Animo's own,
or the tag around the region when the region is a tag's implicit one.
A tag whose name is among the `names` of the record and that holds exactly one such path in
each region pairs the two, whatever their structure, under the same clips and `sameFrame`.

The distance of a match is measured on the screen, from where the outgoing element is
displayed to where the incoming one is laid out, and mapped into the user space of each
element's parent through the inverse of the parent's `getScreenCTM()`.
Both renderings stay laid out under `visibility`, so the outgoing geometry can be read.
The outgoing element animates from what it shows to the incoming place, with an `end` of its
own in the effect, and the incoming element from the outgoing place to rest.
Neither is written as inline style, so the slide at rest carries no morph translation.
A resize adds `d` and `stroke-width` to the same two effects:
both paths go from the geometry the outgoing path shows to the `d` and stroke width of the
incoming one, which `reshaped` writes as their common `end`.
Typst writes every path from its own origin, so the two `d` are in comparable user spaces,
the two paths have one geometry at every moment, and the `translate` keeps them at one place.
Neither property is written as inline style either.
When the two `d` have different commands, as for a shape morph, `alignPaths` in
`src/js/paths.js` rewrites both into one structure of absolute cubic Béziers first.
It pairs the subpaths by length and gives a subpath without a partner a point to grow from.
It closes an open subpath against a closed one, with a line when the path is filled and by
running back along itself when it is not.
It runs two closed subpaths the same way round and starts the second where the squared
distance its points travel is least.
Then it cuts both at the vertices of both, by their fraction of the length.
`paths.js` reads no DOM, so its tests run on numbers.
The opacity is the crossfade's own, which `plus-lighter` sums to one opaque element on the
route (see *Findings*).

`slide.morphed` holds every element a morph is still moving, with the epoch of its rendering,
the stack that holds it, where its route ends and, for a resize or a shape morph, where its
`d` and stroke width end.
`settleMorphs` reads `slide.morphed` at every step, before any transition plans.
A translation in a stack that the step carries again runs on to its end on the new boundary's
clock, unless the translation is in the rendering being entered.
Every other translation snaps to rest.
A resize runs on or snaps with its translation, and a later match of a path that is still
being resized starts from the geometry it shows.
The measurement of an incoming element subtracts the translations that are still running on
it and above it, which `getScreenCTM()` includes.

## Where the Slide Boundary Is Selected

`slideTransitions` in `src/js/boundaries.js` plays the same role for slide containers.
It is a table of its own rather than an entry in `transitions`,
because the two tables are handed different things.
A transition of an epoch boundary gets the renderings of one region,
inside a slide that it holds still.
A transition of a slide boundary gets two containers and has nothing to hold still,
since two slides share nothing, so the whole container is the unit.

The slide that owns a boundary is the one with the higher number,
which is the slide a forward step enters,
and its `data-animo-transition` chooses the transition in both directions.
Typst states every parameter of the transition,
and the parameters travel as JSON in `data-animo-transition-args`,
together with the `duration` that the slide's `init` stated.
`auto` resolves to the transition in the `data-animo-config` of the deck element,
and a `duration` beside `auto` applies to that transition.

A slide transition is a function of the owner and of a progress `p`,
which is 0 where the owner has not arrived and 1 where it has.
Each entry of `slideTransitions` gives the display state of the owner and of the other slide
at the two ends, and the runtime animates each container from what it is showing to the end
the step heads for.
A forward step heads for 1 and a backward step for 0,
so the backward step is the forward one played from the other end and needs no direction.
A slide that had no layout before the step starts at the far end instead,
which for a push is outside the stage.
The owner comes later in the document, so it is in front in both directions.

The crossfade animates `opacity` on the two containers,
through the `mix-blend-mode: plus-lighter` the stylesheet puts on every slide,
inside the `isolation: isolate` on the stage.
The background of the element that isolates a blend is inside the group it isolates.
A surround written on the stage would therefore be summed into both slides,
so the surround sits on `body` instead.

A push and a cover animate `translate` and a wipe animates an `inset` as `clip-path`.
These three overlap two opaque slides, which would add to a third colour under
`plus-lighter`, so they set `mix-blend-mode: normal` on both containers for the boundary.
The blend stays until the deck moves again,
because the slide being left is still laid out under the owner when a cover or a wipe ends.
A single slide renders the same under either blend.
The stage clips a slide that a push moved out of it.

**Two slides are laid out at a time and no more**:
the one being shown, and the one a boundary is crossing from.
`display: none` on the rest keeps a long deck cheap to open.
Laying every slide out for the whole session doubled the first paint of a sixty-slide deck,
as measured.
For the same reason, the anchors of a slide are measured when the slide is first shown.
That is the moment the slide is first laid out,
and it comes before the runtime has written anything on the slide.

A gradient, a clip path, a tiling, a mask and a filter are referenced through ids that typst
derives from their content, and a reference resolves to the first definition in the document,
which may sit in a slide that is `display: none`.
At load the runtime therefore copies the first definition of each id into a zero size `<svg>`
that is the first child of `body` and stays laid out,
so that every slide draws them whichever slides are laid out.
It then removes the id from every original,
because in webkit a definition that stops being laid out drops every reference to its id,
even while the holder still defines it.

A boundary animates only for a step between neighbouring slides.
A deep link, the first paint, `Home`, `End` and any longer jump snap,
which is the rule the epoch crossfade already uses.
A duration of zero reaches a `null` timing, whatever the transition,
so a cut has no animation in it at all rather than one of zero length.

## One Clock

A step is put on the page in two phases.
The first plans it: `plan` in `src/js/effects.js` records an effect per element and property,
with what the element shows now, what it is to show, and the timing that takes it there,
and nothing is written.
The second, `apply`, writes every style of the step, then reads what the elements compute,
and then creates every animation.
Every read of the step therefore comes before every write of it,
and the engine recalculates style once per step rather than once per element.

Every animation of a step, the boundary's included, is created in that one task,
and none of them is told when it began,
so the browser starts them all on the same frame.
Motion is driven by the Web Animations API rather than by CSS transitions,
so the inline style is the state and the animation is only how it got there.

An effect may name any CSS property.
`PROPERTIES` in `src/js/effects.js` lists the properties whose unset value the engine
reports as a keyword, such as `none` for `translate`, with the value that keyword stands for.
Every other property is read as the engine reports it.
An effect animates only the properties whose value the step changes,
because a `translate` or `scale` that is equal at both ends stops chromium from drawing an
`opacity` animated beside it. See *Findings*.

An operation's `delay:` becomes that animation's own delay rather than a timer of its own,
so the step keeps a single clock when its operations arrive one after another.
A delayed effect fills **backwards**, because the state it is arriving at is already the
element's inline style.
An effect that did not hold its first keyframe while it waits would first show that state,
and then jump back to animate forwards into it. See *Findings*.

A backward step plays the schedule of the forward step it undoes from the other end.
The length of a step is the moment its last operation ends.
An operation that ran from `delay` to `delay + duration` in the forward step
runs from `length - delay - duration` to `length - delay` in the backward step.
The operation that arrived last is therefore the first to leave,
and the backward step takes as long as the forward step did.

Typst cannot compute the length of a step on its own,
because an operation that states no duration takes `--animo-primitive-duration`,
whose value only the stylesheet knows.
Each state in the plan therefore carries a `span` with two numbers.
The number `stated` is the latest end over the operations that stated a duration,
and `unstated` is the latest delay over the operations that did not.
The runtime adds the deck's duration to `unstated`
and takes the larger of the two sums as the length of the step.

The one timer the runtime does set is a gap's `wait:` or `hold:`.
This timer is armed whenever a position is entered, whatever entered it,
and cleared whenever another position is entered,
so a presenter stepping by hand never races a clock that is still counting.
A backward step arms the same gap the other way, so a deck travels back over the gaps it
travelled forward over and comes to rest where it would wait for the presenter.
It is also the one step that can land further back than one state, since a gap of zero is a
join the deck ran through and a backward step walks back over the whole of it.
When a join ran out of a slide, a backward step over that join walks back into the slide
at a state before its last one.
That is the only case where the slide being entered moves rather than snaps.
The slide takes `--animo-primitive-duration` while the boundary takes the duration of the
slide's `init`, both started on one frame, as the forward join ran them.
The timer is a `setTimeout` rather than an animation of zero size,
because the document timeline is not a clock, as *Findings* records,
and a deck waiting out a long step is a page with nothing to draw.

A test asserts about a moment of a step by pausing what is in flight and setting its time,
rather than by racing it.
When it does, **every raster it compares has to be taken with the step in flight**,
including the rasters that stand for the endpoints.
Chromium 151 rasterises glyphs differently while an `opacity` animation runs in their frame,
so a raster taken at rest and one taken mid-step come off two different rendering paths.

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

## What the Page Carries

The runtime reads a few attributes, which can also be read back in a browser's inspector
to diagnose a step that does not do what the timeline says.

- Every slide container carries `data-animo-slide` and `data-animo-states`,
  its position in the deck and how many states it has,
  and `data-animo-transition`, which is how the boundary above it is crossed.
- Every slide container also carries `data-animo-plan`,
  which holds the resolved display state of every state of that slide as JSON, keyed by tag name.
  This attribute is the whole of what the browser is told,
  so a wrong step is either in this attribute or in the runtime, and the attribute shows
  which.
- The deck element carries `data-animo-config`, the settings of the deck as JSON,
  which the runtime reads once at load.
  No setting exists yet, so its value is `{}`.
- The root element carries `lang`, and the head a `<title>`, from `set text(lang: ..)` and
  `set document(title: ..)`, as typst writes them into a head it builds itself.
- The root element carries `data-animo` with the position the runtime has reached,
  which is the same value as the fragment,
  `data-animo-mode` with the name of the active mode,
  and `data-animo-paused` while the deck's own clock is stopped.
- The slide that is shown carries `data-animo-current`,
  and the slide a boundary is crossing from carries `data-animo-leaving` and `inert`.

## Where the Page Weight Goes

The HTML deck is one self-contained file, and most of it is glyph definitions.
Typst defines a glyph once per frame that uses it, so a deck that wrote a frame per epoch
would define the glyphs of a slide once per epoch of that slide.
One frame per slide lets typst's own deduplicator reach them.

Measured on the controlled benchmark deck of twelve slides, laid out as one rendering of the
whole slide per epoch, against the same deck written as a frame per epoch:

| Epochs per slide | A frame each     | One frame per slide | Saved |
| ---------------- | ---------------- | ------------------- | ----- |
| 1                | 180 KiB gzipped  | 180 KiB gzipped     | none  |
| 2                | 345 KiB gzipped  | 220 KiB gzipped     | 36%   |
| 4                | 673 KiB gzipped  | 297 KiB gzipped     | 56%   |
| 8                | 1328 KiB gzipped | 445 KiB gzipped     | 66%   |

A slide with one epoch has nothing to share, so both layouts weigh the same.
On the tour, which is mostly one epoch a slide, the whole deck gains 9%.

What is left is the duplication **across** slides, which Animo cannot reach.
On the tour, definitions are still 53% of the page and 31% of the page is definitions that
appeared in an earlier slide. Typst's definition ids are content hashes, so those repeats
are genuinely the same bytes, and hoisting them into one document-level `<svg>` would be
sound and would save a further **41% of the gzipped page**,
because gzip's window is smaller than one slide's frame.
A package cannot write that markup.
An `html.frame` is content until the document is encoded, and every text node is escaped,
so the document-level `<svg>` cannot be written from inside a typst compile at all.
*Findings* records the measurement.

A content layer is the clearest case of what is left, because a deck gives every slide the
same one. On the controlled deck the twelve overlay frames are byte-identical, 78% of each
is definitions, and hoisting those would take the 233 KiB they weigh to 66 KiB.
No scope inside a slide reaches this duplication, since the twelve frames sit in twelve
slides.

None of this is urgent, because a deck that transfers 245 KiB is a small web page.
