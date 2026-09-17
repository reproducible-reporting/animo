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

- **A forward step cancels the pending timer** and starts a new one from the state it lands
  on, so stepping ahead of the clock is never a race with it.
- **A backward step lands on the nearest earlier state the deck rests at.**
  A `hold: 0`, or a `wait: 0` on the step after, is a join rather than a stop:
  nobody sees that state at rest, so one press forward runs through the whole join and one
  press back comes back over the whole of it, a slide boundary included.
  A state inside a run stays reachable by a [deep link](#the-position-is-in-the-url) and by
  stepping forward while the clock is stopped, and writing `hold: 0.001` instead of
  `hold: 0` says that the state before it is a stop after all.
- **A backward step also turns the clock around.**
  The deck then plays itself backwards over the gaps it played itself forwards over,
  and it comes to rest at the state the presenter last pressed a key at,
  so a run of timed gaps costs one press back as it costs one press forward.
  One gap times the step in both directions,
  so a state inside such a run is shown for as long on the way back as on the way out,
  and a backward key pressed during the travel is one more step back.
  A deck that times every one of its gaps travels back to its first state.
  The travel stops there, because nothing earlier is there to travel to
  and the gap that state carries would carry the deck forward again.
  A forward step puts that clock back in motion, and so does `Space`.
- **`Space` stops and starts the deck**, the way it stops and starts a video.
  It stops the motion in flight where it is as well as the clock,
  resuming picks the wait up where it was left rather than restarting it,
  and the deck carries on the way it was going.
  It is also the forward key on a deck that has no clock to stop,
  so a remote that sends `Space` still works.
  A deck stopped with `Space` stays stopped while the presenter steps through it,
  so stepping through a paused deck does not start its clock again.
- **A deep link starts its own timer from where it lands**,
  so a fragment into an autoplaying deck resumes the playback from there.

The URL does not carry whether the deck is paused: the fragment holds the
position only, so a deck restored from a fragment comes back running.

## The Position Is in the URL

The current position lives in the URL fragment as `#<slide>.<state>`,
counting slides from one and states from zero,
so `#3.2` is the third subslide of slide 3.
It is kept up to date while stepping, and it is read back on load.

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

`transition-duration` is how long the crossfade into a slide takes,
and is spent only at a boundary whose [`transition:`](slides.md#slide-transitions) is not `none`.
How long a slide stands is decided by the presenter and by the timeline.

A duration of zero means that kind of motion lands without animating,
so hard cuts between slides, with the subslides still moving, are written as:

```typst
#show: animo.with(transition-duration: 0)
```

## Live Preview

Typst serves the HTML and reloads the browser itself, so Animo ships nothing for this:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

Every successful recompile pushes a reload to the connected browsers.
The reload is a plain `location.reload()`, so the URL survives it, fragment included,
and the deck comes back **on the same subslide**, without replaying its animation.
Editing the slide that is on screen is therefore a loop of two steps, save and look.
