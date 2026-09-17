---
description: >-
  How a slide becomes an HTML presentation: the epoch renderings, the five rules the
  browser runtime obeys, the two transform slots of a tag site,
  and where the transition strategy is selected.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Architecture of the HTML Output

How a slide reaches the browser, and what the runtime is allowed to do there.
The specification it follows is *Architecture* in the design document,
and every measurement it cites is an entry of *Findings* with a probe under `probes/`.
[Developing Animo](development.md) says where both documents live.

## What Typst Emits

A slide is one container element carrying its plan as JSON in `data-animo-plan`,
and inside it a `.animo-canvas` element holding **one `html.frame` for the whole slide**,
in which **one rendering per epoch** is placed at one point, in epoch order.
Each rendering is a labelled box, so it becomes a `<g data-typst-label="animo-epoch-N">`
the runtime can show, hide and blend.
One frame and not one per epoch, because typst's deduplicator has the frame for its scope:
the renderings of a slide then define each glyph they share once between them instead of
once each, which takes a deck of several epochs a slide down by about 40% on the wire.
The canvas sits inside the viewport element, which clips it.
The container also carries `data-animo-transition`, which is how the boundary above the
slide is crossed: one value per slide, so it is an attribute rather than an entry in the
plan, for the reason the plan itself is an attribute.

An epoch is a run of consecutive states in which no content changes,
so a slide with no structural operation emits exactly one rendering
and the machinery itself adds no cost.
Every epoch is laid out with every region at its footprint,
so the renderings are interchangeable outside the regions that change.

The plan holds one entry per state, with the display state of every addressed tag,
the pan, and the epoch the state belongs to;
and one entry per epoch, naming the region groups that the boundary into it redraws.

A state also carries the `wait:` before it is entered, the `hold:` before the state after
it is, and the timing of the operations its own subslide performed, and an epoch's region
carries the timing of what changed it, all in seconds.
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
target. The runtime measures the ones the plan names when the slide is first shown and
before it has written anything on it, off the origin of each tag's labelled group, mapped
into the user space of its frame. Typst reads the same corner on paper, off a zero-size
marker each tag site places inside its outer slot, and the two agree to within a thousandth
of a point.

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
it crossfades the two containers, and the subslide state of the slide being entered is in
place before it comes up.

Three things never animate, and all three for the same reason:
the audience has not seen the steps that lead to the state they would animate into.
A deep link, including the one `typst watch` reloads into; the first paint, which is a deep
link to wherever the fragment points; and a jump that is not a step across one boundary,
which `Home` and `End` are.

A reader who has asked their system for reduced motion gets every duration at zero,
which Animo's own stylesheet sets under `prefers-reduced-motion: reduce`.
Those two declarations are `!important`, because the deck writes its own durations into the
same `:root` further down the page and would otherwise outrank them.
A step that lands without motion lands whole, so a `delay:` is dropped with the duration it
was holding an operation back inside, and a `duration:` written in the timeline is zeroed
with it. That last one is why the rule lives in the runtime rather than in the stylesheet:
a media query cannot reach a number written in a typst source.
A `wait:` and a `hold:` are not touched, because zeroing them would run an autoplaying deck
through itself at once.

## The Five Rules

**1. Continuous state is applied to every epoch rendering at once.**
Not only to the one being shown.
Entering an epoch then needs no initialisation,
and a step that both replaces and moves a tag moves it by the same amount in the rendering
it leaves and in the one it arrives at, so the composite stays registered.
An operation on a tag that is absent from a rendering is a no-op there.

**2. The crossfade is scoped to the regions whose content changed.**
Two mechanisms work together, and which of them does what matters:

- `visibility` scopes every epoch rendering the boundary is not entering.
  One rendering is visible at a time and the others are `visibility: hidden`;
  a boundary gives their carried regions their visibility back and nothing else,
  so such a rendering paints in those regions and nowhere else.
  `visibility` rather than `opacity` or `display`, because a descendant can take it back,
  and because the rendering stays laid out and its geometry readable.
  Every rendering that is not the one being entered takes part and not only the one being
  left, because a boundary crossed while an earlier one is still running finds more than
  one of them painting the region; they then all fade out on the new boundary's clock, so
  the region's ink stays at one.
- `mix-blend-mode: plus-lighter` on the *epoch renderings* makes the two halves of a region
  add, inside the `isolation: isolate` on the canvas.
  They are the outermost groups of the slide's one frame, so each adds to ink beside it,
  which is what a blend needs and what is measured.
  It sits there rather than on a region's own group so that one element carries both halves
  of the mechanism, the blend and the `visibility` the boundary scopes with.
  That was once forced rather than chosen: when the renderings were frames of their own, a
  blend on a region's group did not reach the frame below at all.
  How far a group's blend reaches *past* its own frame is not the same in every engine,
  which is why the canvas isolates rather than leaving it to the root of the inline SVG.

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
The epoch renderings sit in the frame the canvas holds, so moving the canvas moves all of
them together and keeps them registered.

## Where the Transition Strategy Is Selected

`transitions` in `src/animo.js` holds one entry per strategy,
and the single `const transition = transitions.crossfade` beside it selects one for every
boundary of every deck.
A strategy is handed the epoch renderings, the epoch the step leaves and the one it
enters, the groups of the regions the boundary redraws, and how the step moves;
an empty list of regions is its instruction to snap,
which is what a deep link, a step inside one epoch, and a reader who asked for less motion
all produce.

A strategy writes the state it is arriving at as inline style
and animates from what the element was showing into it,
exactly as a display state is written.
An interrupted boundary therefore continues from where it is,
and a backward step lands on the earlier rendering exactly.

The seam exists because the crossfade is not the only conceivable strategy.
A **morph** would pair the tags that exist in both epochs, move them to their new places,
and crossfade only the rest;
it is why both renderings stay laid out and readable rather than being hidden with
`display`.

## Where the Slide Boundary Is Selected

`slideTransitions` in `src/animo.js` is the same seam one container out,
and a table of its own rather than an entry in the one above,
because the two are handed different things.
An epoch strategy gets the renderings of one slide and the regions a boundary carries
across, which is what it holds still.
A slide strategy gets two containers and has nothing to hold still,
since two slides share nothing, so the whole container is the unit.

The crossfade there animates `opacity` on the two containers,
through the `mix-blend-mode: plus-lighter` the stylesheet puts on every slide,
inside the `isolation: isolate` on the deck.
A plain crossfade handles two opaque grounds incorrectly,
and the surround therefore sits on `body` rather than on the deck:
the ground of the element that isolates a blend is inside the group it isolates,
so a surround written there would be summed into both slides.

**Two slides are laid out at a time and no more**:
the one being shown, and the one a boundary is crossing from.
`display: none` on the rest keeps a long deck cheap to open, which was measured:
laying every slide out for the whole session doubled the first paint of a sixty-slide deck.
That is also why a slide's anchors are still measured on its first showing,
which is the moment it is first laid out and is still before anything has been written on it.

A boundary animates only for a step between neighbouring slides.
A deep link, the first paint, `Home`, `End` and any longer jump snap,
which is the rule the epoch crossfade already uses.
`transition: none` and a duration of zero reach the same `null` timing,
so a cut has no animation in it at all rather than one of zero length.

## One Clock

Every animation of a step, the boundary's included, is created in one task,
and none of them is told when it began,
so the browser starts them all on the same frame.
Motion is driven by the Web Animations API rather than by CSS transitions,
so the inline style is the state and the animation is only how it got there.

An operation's `delay:` becomes that animation's own delay rather than a timer of its own,
which keeps the single clock when a step's operations arrive in an order.
A delayed effect fills **backwards**, because the state it is arriving at is already the
element's inline style: an effect that did not hold its first keyframe while it waits would
show that state, and then jump back to animate forwards into it. See *Findings*.

A backward step is the same schedule mirrored: each operation is turned around about the
length of the step it undoes, so the last operation to arrive is the first to leave and the
step ends where the earlier state began.
The length of a step is what the plan carries the two extra numbers for, since an operation
that stated no duration takes one that only the stylesheet knows.

The one timer the runtime does set is a gap's `wait:` or `hold:`.
It is armed whenever a position is entered, whatever entered it, and cleared whenever
another one is, so a presenter stepping by hand never races a clock that is still counting.
A backward step arms the same gap the other way, so a deck travels back over the gaps it
travelled forward over and comes to rest where it would wait for the presenter.
It is also the one step that can land further back than one state, since a gap of zero is a
join the deck ran through and a backward step walks back over the whole of it.
A join that ran out of a slide leaves the slide such a step walks back into below its own
last state, and that is the only case where the slide being entered moves rather than snaps:
it takes `--animo-primitive-duration` while the boundary takes `--animo-transition-duration`,
both started on one frame, which is how the forward join ran them.
A `setTimeout` rather than an animation of zero size, because *Findings* records that the
document timeline is not a clock, and a deck waiting out a long step is a page with
nothing to draw.

A test asserts about a moment of a step by pausing what is in flight and setting its time,
rather than by racing it.
When it does, **every raster it compares has to be taken with the step in flight**,
the ones standing for the endpoints included:
chromium 151 rasterises glyphs differently while an `opacity` animation runs in their frame,
so a raster taken at rest and one taken mid-step come off two different rendering paths.

## What the Page Carries

A few attributes are what the runtime reads, and they can be read back in a browser's
inspector, which is how a step that does not do what the timeline says is diagnosed.

- Every slide container carries `data-animo-slide` and `data-animo-states`,
  its position in the deck and how many states it has,
  and `data-animo-transition`, which is how the boundary above it is crossed.
- It also carries `data-animo-plan`, the resolved display state of every state of that
  slide as JSON, keyed by tag name. That is the whole of what the browser is told,
  so a wrong step is either in this attribute or in the runtime, and the attribute says
  which.
- The root element carries `data-animo` with the position the runtime has reached,
  which is the same value as the fragment,
  and `data-animo-paused` while the deck's own clock is stopped.

## Where the Page Weight Goes

The HTML deck is one self-contained file, and most of it is glyph definitions.
Typst defines a glyph once per frame that uses it, so a deck that wrote a frame per epoch
would define the glyphs of a slide once per epoch of that slide.
One frame per slide lets typst's own deduplicator reach them.

Measured on the controlled benchmark deck of twelve slides,
against the same deck written as a frame per epoch:

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
A package cannot write that markup: `html.frame` is content until the document is encoded,
and every text node is escaped, so the document-level `<svg>` cannot be written from inside
a typst compile at all. *Findings* records the measurement.

A content layer is the clearest case of what is left, because a deck gives every slide the
same one. On the controlled deck the twelve overlay frames are byte-identical, 78% of each
is definitions, and hoisting those would take the 233 KiB they weigh to 66 KiB.
It is also the case no scope inside a slide reaches, since the twelve frames sit in twelve
slides.

None of this is urgent: a deck that transfers 245 KiB is a small web page.
