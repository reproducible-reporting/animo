---
description: >-
  Stepping through an HTML deck: the keys, a deck that plays itself,
  the position in the URL, the motion properties, and the live preview loop.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Presenting

The example deck for this page is
[`tour.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/tour.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/tour.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/tour-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/tour-handouts.pdf)).
It is a deck to step through.

The HTML presentation is one self-contained file.
Open it in a browser, step through it, and close it again:
there is nothing to install and no server to run.
A full-screen browser is all the presentation software you need:
open the URL, press `F11` or `Cmd+Ctrl+F`, and you're ready to go.

## The Keys

| Key                                                     | Does                    |
| ------------------------------------------------------- | ----------------------- |
| `→`, `↓`, `Page Down`, `Space`, `Enter`, `n`, any click | one step forward        |
| `←`, `↑`, `Page Up`, `Backspace`, `p`                   | one step backward       |
| `Home`, `End`                                           | the first, the last     |
| `Space`, while a deck is playing itself or paused       | stop and start the deck |

A step goes to the next **subslide**, not to the next slide:
a slide with three `sub` calls takes four steps to get through.
Stepping past the last subslide of a slide goes to the next slide,
and stepping back before the first one goes to the previous slide's last subslide.
A remote that sends a click or an arrow key therefore works without configuration.

The deck fills the browser window at its own aspect ratio,
and a length inside a slide stays a typst length at any window size:
`move("a", dx: 2cm)` moves the element two centimetres of the slide.

## A Deck That Plays Itself

A deck whose gaps state a [`wait:` or a `hold:`](continuous.md#timing) advances on its own,
from the first paint onwards.
Even then, the presenter can fully control the deck:

- **A forward step cancels the pending timer** and starts a new timer from the state it lands
  on, so stepping ahead of the clock is never a race against the clock.
- **A backward step lands on the nearest earlier state the deck rests at.**
  A `hold: 0`, or a `wait: 0` on the next subslide, joins two states without a stop.
  Nobody sees the first of the two at rest,
  so one press forward runs through the whole join and one press back returns over all of it,
  also across a slide boundary.
  A state inside a join stays reachable by a [deep link](#the-position-is-in-the-url) and by
  stepping forward while the clock is stopped.
  Writing `hold: 0.001` instead of `hold: 0` makes the deck stop at that state after all.
- **A backward step also turns the clock around.**
  The deck then plays itself backwards over the gaps that it played forwards,
  and comes to rest at the state where the presenter last pressed a key.
  A run of timed gaps therefore takes one press back, just as it took one press forward.
  Each gap lasts as long in both directions,
  so a state inside such a run is shown as long on the way back as on the way forward.
  A backward key pressed while the deck travels back is one more step back.
  A deck that times every one of its gaps travels back to its first state and stops there,
  because there is no earlier state and the gap of the first state would carry the deck
  forward again.
  A forward step or `Space` starts the clock again.
- **`Space` stops and starts the deck**, the way it stops and starts a video.
  Stopping freezes both the clock and any motion in flight.
  Resuming continues the pending wait instead of restarting it,
  and the deck carries on in the direction it was going.
  On a deck that has no clock to stop, `Space` is a forward key,
  so a remote that sends `Space` still works.
  A deck stopped with `Space` stays stopped while the presenter steps through it,
  so stepping through a paused deck does not start its clock again.
- **A deep link starts its own timer from where it lands**,
  so a fragment into an autoplaying deck resumes the playback from there.

The URL fragment holds only the position and not whether the deck is paused,
so a deck restored from a fragment comes back running.

## The Position Is in the URL

The current position lives in the URL fragment as `#<slide>.<state>`,
counting slides from one and states from zero,
so `#3.2` is the third subslide of slide 3.
The fragment is kept up to date while stepping, and read back on load.

Opening a fragment **snaps** to that position instead of animating into it,
so a deep link into the middle of a talk shows the picture and not the transition.
The same holds for the first paint, for `Home` and `End`, and for any jump that is not a
step between two neighbouring states.

The fragment is written with `history.replaceState`, so stepping leaves no browser history
behind. The back button leaves the deck rather than walking back one subslide at a time.

## Motion

Three arguments of the deck's show rule say how long the deck's motion takes:

| Argument              | Default         | Times                              |
| --------------------- | --------------- | ---------------------------------- |
| `primitive-duration`  | `0.4`           | one animation primitive            |
| `transition-duration` | `0.4`           | the transition into the next slide |
| `easing`              | `"ease-in-out"` | both                               |

Both durations are numbers of seconds, like every other time in a deck,
and `easing` is one of `"linear"`, `"ease"`, `"ease-in"`, `"ease-out"` and `"ease-in-out"`,
listed in [Reference](reference.md#animo).
A name outside that list is refused when the deck is compiled.

`primitive-duration` is the duration of any animation primitive that states no `duration:` of
its own, so restating it in the show rule changes the tempo of the whole deck
and leaves the primitives that stated a duration alone.
A step lasts as long as its slowest primitive, and a `delay:` pushes that out further.

`transition-duration` is how long the transition into a slide takes.
A slide whose [`init`](slides.md#slide-transitions) states a `duration:` of its own takes that
instead.
How long a slide stands is decided by the presenter and by the timeline.

Both durations are defaults.
A duration of zero means that kind of motion lands without animating,
unless a primitive or an `init` states a duration of its own,
so hard cuts between slides, with the subslides still moving, are written as:

```typst
#show: animo.with(transition-duration: 0)
```

A slide of that deck that names a transition in its `init` and states no `duration:` is
entered with a cut, and [Slide Transitions](slides.md#the-decks-own-transition) shows how to
push one slide in anyway.

A reader whose browser asks for reduced motion gets no motion at all,
whatever the deck, a primitive or an `init` states.
Every step then snaps into place, as a deep link does.

## Live Preview

Typst serves the HTML and reloads the browser itself, so Animo ships nothing for this:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

Every successful recompile pushes a reload to the connected browsers.
The reload is a plain `location.reload()`, so the URL survives it, fragment included,
and the deck comes back **on the same subslide**, without replaying its animation.
Editing the slide that is on screen is therefore a loop of two steps, save and look.
