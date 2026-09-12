<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 05: HTML Continuous Animation

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Architecture*, especially rules 1, 3 and 4,
*Live preview*, and the findings on `data-typst-label`, on CSS animation of typst SVG groups,
on what CSS can and cannot reach, and on `hide()` being irreversible in the browser.

## Goal

The deck animates.
Stepping through subslides in the browser reveals, hides, moves and scales tagged elements
smoothly, and the state is addressable by URL.

This is the phase where animo's central claim is either true or not.

## Prerequisites

Phases 01 to 04.

## Scope

### In Scope

- **The runtime**: plain JavaScript, inlined with `read()`, plus a stylesheet the same way.
  No node toolchain, because the package is installed from Universe.
  `slipst`'s runtime is roughly 214 lines of TypeScript and 68 lines of CSS,
  which is the order of magnitude to expect.
- **Emitting the plan into the page.**
  The resolved per-state display state has to reach the browser.
  Decide how, and keep it inspectable: a `data-` attribute or a JSON script element
  is easier to debug and to test than generated CSS.
- **Subslide stepping**: forward and backward, keyboard and click,
  with the slide and subslide in `location.hash` and written with `history.replaceState`.
  Restoring from the hash on load must **snap** to the state, not animate into it.
  `typst watch` reloads with `location.reload()`, which keeps the fragment,
  so this is what puts the author back on the same subslide after every recompile.
- **The four primitives in CSS**, following the findings exactly:
  - `reveal` and `hide` animate `opacity` on the tag's **inner** group;
  - `move` animates the CSS `translate` property;
  - `scale` animates the CSS `scale` property, with `transform-box: fill-box`
    and `transform-origin: center`;
  - the `transform` shorthand is never emitted, because it clobbers typst's own positioning.
- **Initially hidden elements are rendered normally and hidden with `opacity: 0`.**
  Typst's `hide()` emits nothing to draw, so CSS can never bring it back.
  Only the paged outputs may use `hide()`.
  This asymmetry between the targets is worth a test of its own.
- **Selectors scoped to the slide container**, so `[data-typst-label="line1"]` in one slide
  cannot reach another, and so one rule reaches every occurrence of a tag within a slide.
- **Applying continuous state to all frames of a slide, not only the visible one.**
  There is one frame per slide until phase 09, so this costs nothing now and is free to get
  right; it is rule 1 of *Architecture* and it is what keeps phase 09 simple.
- Units: CSS lengths inside a group are user units scaled by the SVG's rendered size,
  so a move expressed in typst lengths stays the same fraction of the slide at any window size.
  Verify this holds at two window sizes rather than assuming it.

### Out of Scope

- Epoch frames, crossfades and structural steps: phases 07 and 09.
- `pan`: phase 06.
- Slide-to-slide transitions, permanently for 0.1.0.

## Open Questions in Focus

1. **Is the Web Animations API the right driver, and what are the easing and duration defaults?**
   The design document's open question, and the reason this phase exists as a unit.
   Paused animations with an explicit `currentTime` would give reversible stepping,
   correct snap-to-state on deep links, and a clock that phase 09's crossfades can share.
   CSS transitions handle all three poorly.
   It is also what makes a mid-transition assertion reproducible,
   because a test sets `currentTime` instead of racing a transition.
   Decide it here, with the tests that depend on it,
   and record what backward stepping and deep-linking actually do under the choice.
   Defaults for duration and easing are part of the same decision
   and should be stated in the documentation as values, not as adjectives.
1. **How do CSS-animated typst SVG groups actually look in motion?**
   Also the design document's open question:
   stroke scaling under `scale`, text rendering during transforms,
   and antialiasing seams at subslide boundaries.
   This one is answered by looking, not by asserting.
   Build a small deck that exercises it, look at it, and record what you see in the session log,
   including anything that suggests a default should change,
   for example whether `scale` on text is usable at all.

No other open question from the design document is in scope for this phase.

## Tests

Tier 3 carries this phase, and the tests should be numeric rather than pictorial:

- the geometry of a tagged element at each subslide, read with `getBoundingClientRect`,
  matches what the plan says;
- typst's own `transform` attribute survives every animation, as the findings require;
- mid-flight sampling at a fixed `currentTime` gives the expected interpolated values;
- a deep link lands on the right subslide with the right geometry and without animating;
- an initially hidden element has ink in the DOM and `opacity: 0`,
  which is what distinguishes the HTML path from the paged one;
- stepping backwards returns to exactly the earlier geometry;
- the hash updates without growing the history.

Tier 2 must keep passing unchanged: the paged outputs are not touched by this phase,
and a regression there means the display state was accidentally rewritten.

## Documentation

- `docs/animation.md` gains the browser half: what animates, how, and with what defaults.
- `docs/presenting.md`: keys, deep links, and the live preview loop with `typst watch`.
- Document the `hide` versus `hidden:` asymmetry between targets explicitly,
  because an author who reads only the paged behaviour will be surprised.

## Definition of Done

- A deck steps through subslides in chromium with smooth motion, forwards and backwards.
- Deep links land on the right state without animating.
- Tier-3 assertions cover geometry, interpolation and navigation.
- All tiers, `pre-commit` and `zensical build --strict` are green.

## Hand-Off

Phase 06 adds the canvas translate on top of this runtime.
Phase 09 adds a second animation class that must share this phase's clock
and must sit in the outer transform slot, above everything this phase writes.
Keep the runtime's structure ready for that: the two slots are already emitted by phase 04,
and this phase must use only the inner one.

## Session Log

### What Was Built

`src/animo.js` is the runtime, 227 lines, and `src/animo.css` 111,
which is `slipst`'s order of magnitude as this file expected.
The runtime keeps one position and four things in step with it:
which slide container is shown, the display state of that slide's tags,
the URL fragment and the `data-animo` attribute.

`src/runtime.typ` is new and is the seam between the resolved plan and the browser.
It holds the JSON the slide emits, and the tag-site report that the JSON needs.
`src/plan.typ` gained the slide's position in the view, `src/tag.typ` emits the report in
the HTML target, and `src/slide.typ` writes the attribute.
The paged path is untouched apart from the view's new entry.

Tests: `tests/test_animation_html.py` (16 tier-3 assertions, run in every engine),
three tier-1 assertions in `tests/test_plan.py` on what reaches the browser,
and three new probes.
`tests/harness/browser.py` gained `styles`, `plan`, `unit`, `press`, `settle` and `scrub`
on `Deck`, which is what lets a test state a moment of a transition rather than race it.
Documentation: the browser half of `docs/animation.md`, a new `docs/presenting.md` in the
`nav`, and `docs/outputs.md` reduced to the command lines, since presenting and the live
preview moved out of it.
`examples/tour.typ` gained a slide that moves, scales and fades a square,
so the four-output build exercises the runtime.

### What Was Decided

Three questions were put to the author and answered:

- **400 ms, `ease-in-out`.** Both are custom properties on `:root`
  (`--animo-duration`, `--animo-easing`), so the values are in the stylesheet rather than
  in the runtime, a deck restates them in CSS without a new `#slide` argument, and
  `prefers-reduced-motion: reduce` sets the duration to zero.
  The runtime reads them at every step, so a change takes effect without a reload,
  and a duration of zero is the same path a deep link takes.
- **The view gained a fifth entry**, the slide's position in the deck.
  A tag needs it to report anything back out of the frame it sits in, because `query` is
  document-wide. The alternative, a second label that the slide restamps with its index,
  was measured to work and was not chosen.
- **`data-animo-plan`, an attribute rather than a `<script>` element.**
  Measured while deciding: typst writes script content raw, so a tag name containing
  `</script` would break the document, while an attribute value is escaped by typst and
  unescaped by the HTML parser. The attribute also shows up beside the slide it belongs to
  in an element inspector.

Decided without asking, because they follow from the phase's own rules:

- **Every state carries every addressed tag**, even the ones it leaves at the identity.
  The browser keeps a display state as inline style until something overwrites it, so a
  state that named only the tags its step changed would leave the previous state's style
  in place, and stepping backwards would not undo what stepping forwards did.
  This was found by stepping back in a real deck, not by reasoning.
- **A step animates, everything else snaps**: a step across a slide boundary, a deep link,
  the first paint and a `hashchange` all land without motion.
- **The style is the state and the animation is only the route.** A step writes the new
  values as inline style on the inner group and animates from what the element was showing
  to them. Reversible stepping, an interrupted step that continues from where it is, and a
  restore that needs no transition to suppress all fall out of that rather than being
  arranged. It also means that an engine which refuses to animate an individual transform
  property would still land on the right state, without motion.

### Open Questions Answered

1. **Is the Web Animations API the right driver, and what are the easing and duration
   defaults?** Yes, and 400 ms with `ease-in-out`, stated in CSS.
   Backward stepping is an ordinary step: state *i* is an absolute set of values, so
   stepping back animates to them and lands on exactly the geometry state *i* had, which
   `test_stepping_back_returns_to_exactly_the_earlier_geometry` asserts with a tolerance of
   zero. Deep-linking snaps, and `document.getAnimations()` is empty when it lands, which
   is asserted rather than described. The shared start time of a step is the clock phase 09
   joins: `render` stamps every animation it starts with one `document.timeline.currentTime`.
1. **How do CSS-animated typst SVG groups look in motion?** Well enough that no default
   changes, and the reason is measurable rather than impressionistic:
   - a scaled glyph is **drawn afresh at the size it ends up at**, so text at 200% is as
     sharp as text at its own size. The antialiasing band per unit of ink is 0.20 at scale
     1, 0.10 at scale 2 and 0.05 at scale 4, in chromium 151 and firefox 153 alike: ink
     grows with the square of the factor and the edge with the factor. A stretched picture
     of a glyph would hold that ratio constant. So `scale` on text is usable, which this
     phase file asked about explicitly.
   - strokes scale geometrically with the element, which is what a figure wants;
   - **there is no seam at the end of a step.** A value under a running animation
     rasterises bit for bit as the same value in a style declaration, over a whole 1280 by
     720 window, so the hand-off from the animation to the inline style is invisible.
   - what still has to be understood rather than accepted is that a `scale` is about the
     element's own centre and nothing reflows around it, so a doubled paragraph overlaps
     its neighbours. That is the design, and `examples/tour.typ` now says so on the slide.

### New Findings

- **A panic that depends on `query` can be swallowed.** This is the expensive one.
  A value read with `query` is read once per introspection pass, so a check on it is a
  check on one pass. If the check panics, the pass produces nothing, the next pass queries
  a different document and does not panic, and the two alternate until the iteration limit.
  What surfaces is `document did not converge within five attempts` and a warning that an
  element count did not stabilise, pointing at the `query`, with nothing about the panic.
  The compilation succeeds. A panic in a document that *does* converge is reported
  normally, so this is not about panics in `context` blocks in general.
  Found while building a check that two sites of one tag name agree about `hidden:`.
  Recorded in *Findings* with `probes/test_convergence.py`, which also probes the
  converging control so that the claim stays about convergence.
  **Consequence for later phases:** a diagnostic that can only be made from `query` has to
  be a value animo resolves, never a refusal. Phases 07 and 08 will want to check things
  across a slide; this is the constraint they run into.
- **A scaled glyph is redrawn, not stretched**, and **a running animation rasterises as the
  equivalent style declaration**, both above, both probed in
  `probes/test_css_transforms.py`.
- A `metadata` marker is layout-neutral **wherever it sits**: before, after or inside a
  block-level tag site, a body with one measures exactly as the body without one.
  This extends the existing *Providing a value down the tree* finding, which measured the
  replaced marker rather than a marker emitted beside a wrapper. It is what lets a tag site
  report itself without disturbing the layout it is reporting on.

### What Changed in the Design Document

Nothing measured contradicts it. Four places were brought in sync, and the author chose
the option that required the first one:

1. *Scoping*: a view has **five** entries, the new one being the slide's position,
   with the reason it exists.
1. *Architecture*: two paragraphs after the five rules, on how the plan reaches the browser
   (`data-animo-plan`, why an attribute, why every state holds every tag, where the
   `hidden:` fallback is taken) and on the Web Animations API being the driver, with the
   defaults and where they live.
1. *Open Questions*: the two this phase carried were removed and answered under
   *Resolved Design Decisions*.
1. *Findings*: the new entry on the swallowed panic; two measurements added to *CSS
   animation of typst SVG groups*; the union rule for `hidden:` added to *Tags*.

### What a Follow-Up Phase Should Know

- **The runtime writes only `opacity`, `translate` and `scale`, and only on the inner
  group**, as this file asks. The labelled outer group is untouched and is free for the
  epoch crossfade. `.animo-canvas [data-typst-label] > g` carries `transform-box: fill-box`
  and `transform-origin: center` once, in the stylesheet, rather than per animated element.
- **The seam for a second animation class** is `render` in `animo.js`, which puts one state
  on every slot of every tag the plan addresses. What phase 09 adds has to be started in
  the same task and must not be given a start time of its own: that is exactly what gives
  a step one clock, and naming the clock is what broke firefox (see the follow-up below).
- **`readSlide` indexes every occurrence of every tag name in the whole slide**, across
  frames, so applying a state to all frames of a slide is already what the runtime does.
  With one frame per slide it cannot be observed yet; the test that comes closest is the
  one with a tag at two sites.
- **Two sites of one name that disagree about `hidden:` are the one place the four outputs
  differ.** The browser hides both, the paged outputs honour each site. It is not refused,
  because refusing it means panicking on a queried value, which is the finding above.
- **A length in a display state is resolved to points at the slide**, not at the tag site,
  so a timeline written in `em` resolves against the text size in effect where `#slide` is
  called, while the paged outputs resolve it at the tag site. Nothing in the tests or the
  examples uses `em` there; a phase that cares should either resolve it at the tag site or
  refuse a relative length in `move`.
- **Webkit was not exercised locally.** Playwright builds it for ubuntu only and this
  machine is fedora, so the whole browser tier skipped it, as `setup.sh` says it will.
  Continuous integration names all three engines and is what will first run this runtime in
  webkit. The residual risk is whether webkit animates the individual `translate` and
  `scale` properties through the Web Animations API; if it does not, the states are still
  right, because the inline style is written before the animation is started.
- **Page weight**, for phase 11: the seven-slide `examples/tour.typ` is 387.8 kB, 82.0 kB
  gzipped, of which the runtime is 11.5 kB and the plan attributes 1.6 kB, or 0.41% of the
  page. The plan is not what will make a deck heavy; the glyph `<defs>` are.

### Follow-Up: Firefox Stepped Without Animating

Reported after the phase was closed, by stepping through `examples/tour.typ` by hand:
firefox jumped from state to state instead of animating, except when the deck was clicked
through quickly, and chromium was reported as showing no fade on one reveal.

The cause is one line. `render` ended by stamping every animation it had started with
`document.timeline.currentTime`, which is the time of the last frame the browser drew.
Firefox 153 draws no frames while a page stands still, so on a deck that is being talked
over rather than clicked through, that time is as old as the pause: measured inside a key
handler it lagged 442 ms after a 250 ms pause and 3181 ms after a 3 s one, against at most
16 ms in chromium 151. An animation told it began that long ago is over before it is drawn.
The fix is to stamp nothing. Animations created in one task are pending until the same
frame and are all started with that frame's time, which was measured to be identical in
both engines, so the step keeps the one shared clock it was stamped for, correctly.

Two things in the same function changed with it. The animation now runs to the value the
element computes after the style has been written rather than to the declaration that was
written, because chromium normalises `translate: 0px 0px` to `0px` and comparing the two
spellings found a difference in every tag a step leaves alone and animated it from itself
to itself. And `put` no longer reports what it started, since there is nothing left to do
with the list.

Chromium turned out to be right all along: traced in the reporter's own binary, headed, the
revealed sentence's ink ramps over the full 400 ms. What was reported as a missing fade is
a 400 ms ease-in-out on one line of text, which reads as an appearance next to the 2 cm
translation it is being compared with.

The finding is *The document timeline is not a clock*, with `probes/test_timeline_clock.py`
for the behaviour and `test_a_step_taken_after_a_pause_starts_at_its_beginning` for animo's
use of it. Both halves of that test matter: the pause has to be longer than a frame, and
the animation has to be read after a frame has been drawn, because an animation measures
its own current time against the same frozen timeline and reports zero until it thaws. The
test fails on firefox with the old runtime, 519 ms into a step it has just begun, and
passes on chromium, which is why the phase's own tests did not catch this: they either
assert the state a step lands in, which the inline style holds whatever the animation does,
or they pause the animation and set its current time by hand, which replaces the clock the
bug was in.

### Follow-Up: Chromium Revealed Without Fading

Reported after the firefox fix above, from the same deck: the reveal on slide 6 stayed
invisible for the whole step and appeared in one frame at the end, while every other step
animated. It is a second, unrelated bug in the same function, and it was in animo's code.

`put` wrote all three properties into the keyframes of every step, including the ones the
step left where they were. In chromium 151 an effect that animates `opacity` beside a
`translate` or a `scale` that is equal at both ends is not drawn at all while it runs.
Measured on the same element of the same page: `opacity` alone is drawn in seven of the
video's frames, `opacity` with a standing `translate` or `scale` in none, and `opacity`
beside a `translate` or `scale` that really changes in six or seven again. The fix is to
put only the properties the step changes into the keyframes, which is what it should have
been doing anyway.

The reason this took a long time is worth recording, because it will happen again. Every
instrument that pokes the page hides the failure: `page.screenshot`, CDP's
`Page.captureScreenshot` and even a bare `requestAnimationFrame` loop each make the browser
draw, and the fade is then perfect. Three separate measurements said the fade was fine, and
all three were vacuous. `Page.captureScreenshot` with `fromSurface: false` is worse than
vacuous: it draws the content ignoring opacity, reporting full ink for an element that is
hidden. What finally worked was recording a video through playwright and reading the frames
back, which is the browser drawing of its own accord, and which discriminated immediately:
the reveal showed no intermediate frame while the very next step in the same recording
showed ten.

So the probe for this finding records a video, and `imageio-ffmpeg` is now a test
dependency for that one purpose (author's decision, asked). The tier-3 guard is
`test_a_step_animates_only_the_properties_it_changes`, which asserts the keyframes rather
than the pixels, because the pixels cannot be asserted from inside the harness.

Two notes for later phases. An epoch crossfade will animate `opacity` on the labelled outer
group at the same time as a step animates `translate` on the inner one; those are separate
effects on separate elements, so this finding does not bite there, but anything that puts
two properties in one effect has to filter them the same way. And the `hidden:` fallback is
unaffected: the state model, the plan and every computed value were right throughout, which
is exactly why nothing in the DOM could show the problem.
