---
description: >-
  Stepping through an HTML deck: the keys, the position in the URL,
  and the live preview loop that typst serves itself.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Presenting

The HTML presentation is one self-contained file.
Open it in a browser, step through it, and close it again:
there is nothing to install and no server to run.

## The Keys

| Key                                                     | Does                |
| ------------------------------------------------------- | ------------------- |
| `→`, `↓`, `Page Down`, `Space`, `Enter`, `n`, any click | one step forward    |
| `←`, `↑`, `Page Up`, `Backspace`, `p`                   | one step backward   |
| `Home`, `End`                                           | the first, the last |

A step is one **subslide**, not one slide:
a slide with three `sub` calls takes four steps to get through.
Stepping past the last subslide of a slide goes to the next slide,
and stepping back before the first one goes to the previous slide's last subslide.
A remote that sends a click or an arrow key therefore works without configuration.

The deck fills the browser window at its own aspect ratio,
and everything inside a slide is measured in typst points at any window size,
because the canvas is *sized* in a unit that follows the window rather than laid out in
pixels. A full-screen browser is the whole of the presentation software.

## The Position Is in the URL

The current position lives in the URL fragment as `#<slide>.<state>`,
counting slides from one and states from zero, so `#3.2` is the third subslide step of
slide 3. It is kept up to date while stepping, and it is read back on load.

Two properties follow from that, and both are deliberate.

Opening a fragment **snaps** to that position instead of animating into it,
so a deep link into the middle of a talk shows the picture and not the transition.

The fragment is written with `history.replaceState`, so stepping leaves no browser history
behind. The back button leaves the deck rather than walking back one subslide at a time.

## Motion

A step animates the tags it changes: see
[what animates and with which defaults](animation.md#in-the-browser).
A reader who has asked their system for reduced motion gets the same steps without motion.

## Live Preview

Typst serves the HTML and reloads the browser itself, so animo ships nothing for this:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

Every successful recompile pushes a reload to the connected browsers.
The reload is a plain `location.reload()`, so the URL survives it, fragment included,
and the deck comes back **on the same subslide**, without replaying its animation.
Editing the slide that is on screen is therefore a loop of two steps, save and look.

The flags of the built-in server are `--port` (the first free port in 3000-3005 by
default), `--no-serve` and `--no-reload`.

## What the Page Carries

Two attributes are worth knowing about when something looks wrong,
because they are what the runtime reads and they can be read in a browser's inspector.

- Every slide container carries `data-animo-slide` and `data-animo-states`,
  its position in the deck and how many states it has.
- It also carries `data-animo-plan`: the resolved display state of every state of that
  slide, as JSON, keyed by tag name. That is the whole of what the browser is told,
  so a step that does not do what the timeline says is either in this attribute or
  in the runtime, and the attribute says which.

The root element carries `data-animo` with the position the runtime has reached,
which is the same value as the fragment.
