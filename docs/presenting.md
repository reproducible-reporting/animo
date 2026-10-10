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
Its HTML version lets you try the keys on this page,
and its slide *Timer controls (in HTML)* plays part of itself.

The HTML presentation is one self-contained file.
Presenting it needs no installation and no server.
To present, open the file in a browser and switch the browser to full screen,
with `F11`, or with `Cmd+Ctrl+F` on macOS.

## The Keys

| Key                                                     | Action                   |
| ------------------------------------------------------- | ------------------------ |
| `→`, `↓`, `Page Down`, `Space`, `Enter`, `n`, any click | one step forward         |
| `←`, `↑`, `Page Up`, `Backspace`, `p`                   | one step backward        |
| `Home`                                                  | go to the first subslide |
| `End`                                                   | go to the last subslide  |
| `Space`, while a deck is playing itself or stopped      | stop or start the deck   |

Each step goes to the next **subslide**.
A slide with three `sub` calls has four subslides,
because the initial state of the slide comes before the first `sub`.
Going from the previous slide to the last of these four subslides therefore takes four steps.
One step forward from the last subslide of a slide enters the next slide.
One step back from the first subslide of a slide returns to the last subslide of the previous slide.
Because a click and the arrow keys both step through the deck,
a presentation remote that sends either one works without configuration.

The deck is as large as the browser window allows at the aspect ratio of the deck.
All lengths inside a slide scale with the deck.
For example, `move("a", dx: 2cm)` moves the element by one eighth of the slide width
in a deck that is 16cm wide, whatever the size of the window.

## A Deck That Plays Itself

A `wait:` or a `hold:` on a subslide sets a timer on a [gap](continuous.md#timing)
between two subslides.
When the timer runs out, the deck goes to the next subslide without a key press.
Timers already run on the first subslide that the browser shows.
The presenter keeps full control of such a deck:

- **A forward step cancels the pending timer.**
  When the gap after the new subslide has a `wait:` or a `hold:`, its timer starts.
  The presenter can therefore step ahead of a timer at any moment,
  and the deck never advances twice because a timer ran out just after a key press.
- **A backward step skips the subslides that the deck passes through without stopping.**
  A gap of zero seconds is written as `hold: 0`, or as `wait: 0` on the next subslide.
  The deck leaves the subslide before such a gap at the moment it arrives there,
  so the audience never sees that subslide at rest.
  One step forward runs straight through such subslides,
  and one step back skips them in the same way.
  This also holds when the gap of zero lies between two slides.
  A skipped subslide can still be opened with a [deep link](#the-position-is-in-the-url),
  or reached by stepping forward while the deck is stopped.
  Only a gap of exactly zero is skipped,
  so a backward step does land on a subslide with `hold: 0.001`.
- **A backward step also makes the deck play itself backwards.**
  The deck then goes back through the gaps that have a timer, one gap at a time.
  Each gap lasts as long in both directions,
  so the deck plays a run of timed gaps backwards as it played them forwards.
  The deck stops at the subslide that the presenter's last forward step brought up,
  because the gap before that subslide waits for the presenter.
  A run of timed gaps therefore takes one press back, just as it took one press forward.
  Pressing a backward key while the deck plays backwards goes back one more step.
  In a deck where every gap has a timer, playing backwards stops at the first subslide of the deck.
  The deck stops there because there is no earlier subslide,
  and because the timer of the gap after the first subslide would otherwise carry the deck
  forward again.
  A forward step or `Space` makes the deck play itself again.
- **`Space` stops and starts the deck**, the way it stops and starts a video.
  Stopping the deck freezes both the pending timer and any animation that is running.
  When the deck starts again, the timer continues with the time it had left,
  and the deck continues in the direction it was going.
  While the deck is neither playing itself nor stopped,
  `Space` steps forward, so a remote that sends `Space` also works.
  A deck stopped with `Space` stays stopped while the presenter steps through it.
- **A deep link starts the timer of the gap after the subslide it opens.**
  A deck opened from a link with a fragment (the part of the URL after `#`)
  therefore plays itself from that subslide onwards.

The fragment records the position in the deck and not whether the deck was stopped.
A deck that is reloaded or opened from a link therefore plays itself again,
also when the presenter had stopped it with `Space`.

## The Position Is in the URL

The URL of the deck ends in a fragment of the form `#<slide>.<state>`,
which records the current position.
Slides are numbered from one and the subslides within a slide from zero,
so `#3.2` is the third subslide of slide 3.
Animo updates the fragment at every step,
and opens the deck at the position in the fragment when the page loads.

A link with a fragment opens the deck directly at that position, without any animation.
The deck is then said to **snap** to that position.
A deep link into the middle of a talk therefore shows the subslide at rest,
without the motion that leads up to it.
The deck also snaps when the browser first shows it, when the presenter presses `Home` or `End`,
and on any other jump that is not a step.

Animo writes the fragment with `history.replaceState`,
which adds no entry to the browser history.
The back button of the browser therefore leaves the deck,
instead of going back one subslide at a time.

## Motion

Three arguments of the show rule (the `#show: animo.with(..)` line of the deck)
set the duration and the easing of the motion in the deck:

| Argument              | Default         | Applies to                     |
| --------------------- | --------------- | ------------------------------ |
| `primitive-duration`  | `0.4`           | each animation primitive       |
| `transition-duration` | `0.4`           | the transition into each slide |
| `easing`              | `"ease-in-out"` | both                           |

Both durations are numbers of seconds, like every other time in a deck.
`easing` takes one of the names `"linear"`, `"ease"`, `"ease-in"`, `"ease-out"` and
`"ease-in-out"`, which [Reference](reference.md#animo) also lists.
Animo refuses any other name with a compile error.

`primitive-duration` is the duration of every animation primitive without a `duration:` argument.
Changing `primitive-duration` in the show rule therefore changes the tempo of the whole deck.
A primitive with a `duration:` argument keeps that duration.
A step lasts until the last of its primitives has finished,
counting the `delay:` of each primitive.

`transition-duration` is the duration of the transition into a slide,
unless the [`init`](slides.md#slide-transitions) call of that slide has a `duration:` argument.
The time a slide stays on screen depends on when the presenter steps on,
and on the `wait:` and `hold:` arguments in its timeline.

A duration of zero makes the motion jump to its end without animating.
Both durations in the show rule are defaults,
so a primitive or an `init` call with a `duration:` argument still animates.
For example, the following show rule gives a deck hard cuts between slides,
while the primitives inside each slide still animate:

```typst
#show: animo.with(transition-duration: 0)
```

In that deck, a slide whose `init` names a transition, such as `anim.push()`,
is also entered with a hard cut, unless the `init` call has a `duration:` argument as well.
See [Default Transition of the Deck](slides.md#default-transition-of-the-deck) for an example.

Some readers set their operating system or browser to ask for reduced motion.
For such a reader, the deck shows no motion at all,
whatever durations the deck, its primitives and its `init` calls set.
Every step then snaps into place, as a deep link does.

## Live Preview

For a live preview while you edit, `typst watch` serves the HTML presentation
and reloads the page in the browser after each change.
Animo therefore provides no separate tool for this:

```bash
typst watch --format html --features html --open talk.typ
```

After each successful compilation, typst tells every connected browser to reload the page.
The browser reloads with `location.reload()`, which keeps the URL, including the fragment.
The deck therefore comes back **on the same subslide**, and snaps there without an animation.
After you save the file, the browser shows the edited subslide without any key press.
