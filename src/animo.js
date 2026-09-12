// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The animo presentation runtime.
//
// It keeps one position, `<slide>.<state>`, and four things in step with it:
// which slide container is shown, the display state of that slide's tags, the URL
// fragment, and the `data-animo` attribute of the root element. The fragment is what
// makes a position addressable, which a deep link, a test and the reload of `typst watch`
// all need; the attribute is what lets a reader of the DOM see the position the runtime
// actually reached.
//
// A step within a slide animates; everything else snaps. Restoring a position therefore
// snaps to it rather than animating into it, and so does arriving on a new slide.
// The fragment is written with `replaceState`, so stepping leaves no history behind.
//
// Motion is driven by the Web Animations API rather than by CSS transitions.
// Each step writes the state's display state as inline style on the tag's inner group and
// animates from what the element was showing to that, so the style is the state and the
// animation is only how it got there: a step interrupted halfway continues from where it
// is, stepping backwards lands on exactly the geometry the earlier state had, and a
// deep link needs no transition to suppress.
//
// When a step starts an animation it never says when it began.
// Every animation of one step is created in one task, so they are all pending until the
// same frame and all take that frame's time: the step shares one clock by construction,
// which is the clock an epoch crossfade joins.
// Naming that clock is what has to be avoided. `document.timeline.currentTime` is the
// time of the last frame the browser drew, and firefox 153 draws no frames at all while
// the page sits still, so on a deck being read rather than clicked through it lags by as
// long as the reader paused, and an animation told it began then is already over.
// See *Findings*.

/** One slide of the deck, as the runtime needs it, read from the DOM once. */
function readSlide(element) {
  const plan = JSON.parse(element.dataset.animoPlan || '{"states":[]}');
  // Every occurrence of a tag name, in every epoch frame of this slide: continuous state
  // belongs to the slide and not to the frame that happens to be showing.
  const slots = new Map();
  for (const group of element.querySelectorAll("[data-typst-label]")) {
    const slot = group.querySelector(":scope > g");
    if (slot === null) {
      continue;
    }
    const name = group.dataset.typstLabel;
    const found = slots.get(name);
    if (found === undefined) {
      slots.set(name, [slot]);
    } else {
      found.push(slot);
    }
  }
  return {
    element,
    slots,
    states: plan.states ?? [],
    count: Math.max(1, Number(element.dataset.animoStates ?? 1)),
  };
}

const deck = new Map(
  Array.from(document.querySelectorAll("[data-animo-slide]"), (element) => [
    Number(element.dataset.animoSlide),
    readSlide(element),
  ]),
);
const last = deck.size;

/** How many states a slide has, which is one more than its number of subslide steps. */
function count(number) {
  return deck.get(number)?.count ?? 1;
}

/** Read the position from the URL fragment, falling back to the first slide. */
function parseHash() {
  const found = /^(\d+)\.(\d+)$/.exec(location.hash.slice(1));
  if (found === null) {
    return { slide: 1, state: 0 };
  }
  return { slide: Number(found[1]), state: Number(found[2]) };
}

/** Bring a position inside the deck, so that a hand-written fragment cannot leave it. */
function clamp(position) {
  const slide = Math.min(Math.max(position.slide, 1), last);
  return { slide, state: Math.min(Math.max(position.state, 0), count(slide) - 1) };
}

/** A CSS time as a number of milliseconds, or zero when it is not one. */
function milliseconds(value) {
  const found = /^\s*(-?[\d.]+)(ms|s)\s*$/.exec(value);
  if (found === null) {
    return 0;
  }
  return Number(found[1]) * (found[2] === "s" ? 1000 : 1);
}

/**
 * How a step moves, read from the stylesheet at every step, or `null` when it snaps.
 *
 * The values live in CSS rather than in this file so that a deck can restate them and a
 * reader who asked for less motion gets a duration of zero from a media query.
 */
function timing() {
  const style = getComputedStyle(document.documentElement);
  const duration = milliseconds(style.getPropertyValue("--animo-duration"));
  if (!(duration > 0)) {
    return null;
  }
  // An easing the stylesheet does not state is no easing at all.
  const easing = style.getPropertyValue("--animo-easing").trim() || "linear";
  return { duration, easing, fill: "none" };
}

// The three properties the runtime writes, and the only ones it reads back.
// Never the `transform` shorthand: it would clobber the positioning typst wrote on the
// labelled group that holds this one.
const PROPERTIES = ["opacity", "translate", "scale"];

/**
 * The CSS of one tag's display state.
 *
 * A length inside a frame's SVG is a user unit, which is a typst point, so a move stays
 * the same fraction of the slide at any window size without the runtime measuring one.
 */
function declarations(display) {
  return {
    opacity: display.hidden ? "0" : "1",
    translate: `${display.x}px ${display.y}px`,
    scale: String(display.scale),
  };
}

/** What an element is showing right now, in the same shape as `declarations`. */
function showing(element) {
  const computed = getComputedStyle(element);
  return {
    opacity: computed.opacity,
    translate: computed.translate === "none" ? "0px 0px" : computed.translate,
    scale: computed.scale === "none" ? "1" : computed.scale,
  };
}

/** Put a display state on one element, animating into it unless the step snaps. */
function put(element, to, options) {
  const from = options === null ? null : showing(element);
  for (const animation of element.getAnimations()) {
    animation.cancel();
  }
  Object.assign(element.style, to);
  if (from === null) {
    return;
  }
  // What the element now computes, rather than what was just written: an engine
  // normalises what it computes, and chromium 151 gives back `0px` for the `0px 0px` of
  // a tag at rest, so comparing the two spellings finds a difference where there is none.
  const into = showing(element);
  // Only the properties this step actually changes. A property that holds still in the
  // keyframes is not free: in chromium 151 a `translate` or `scale` that is equal at both
  // ends stops the browser from drawing the `opacity` beside it, and the element stays as
  // it was until the step ends and jumps. Measured; see *Findings*.
  const changed = PROPERTIES.filter((name) => from[name] !== into[name]);
  if (changed.length === 0) {
    return;
  }
  const only = (values) => Object.fromEntries(changed.map((name) => [name, values[name]]));
  element.animate([only(from), only(into)], options);
}

/** Put one state of a slide on every occurrence of every tag the plan addresses. */
function render(slide, index, options) {
  const state = slide?.states[index];
  if (state === undefined) {
    return;
  }
  for (const [name, display] of Object.entries(state.tags ?? {})) {
    for (const element of slide.slots.get(name) ?? []) {
      put(element, declarations(display), options);
    }
  }
}

let current = { slide: 1, state: 0 };

/** Show a position, and publish it in the fragment and on the root element. */
function show(position, animate = false) {
  const wanted = clamp(position);
  // Arriving on another slide snaps: a transition between slides is not animo's to make,
  // and the geometry an animation would start from belongs to a slide nobody is watching.
  const moving = animate && wanted.slide === current.slide;
  current = wanted;
  for (const [number, slide] of deck) {
    slide.element.toggleAttribute("data-animo-current", number === current.slide);
  }
  render(deck.get(current.slide), current.state, moving ? timing() : null);
  const hash = `#${current.slide}.${current.state}`;
  if (location.hash !== hash) {
    history.replaceState(null, "", hash);
  }
  document.documentElement.dataset.animo = `${current.slide}.${current.state}`;
}

/** Step one position forward or backward, crossing slide boundaries. */
function step(delta) {
  const state = current.state + delta;
  if (state >= 0 && state < count(current.slide)) {
    show({ slide: current.slide, state }, true);
  } else if (delta > 0 && current.slide < last) {
    show({ slide: current.slide + 1, state: 0 });
  } else if (delta < 0 && current.slide > 1) {
    const slide = current.slide - 1;
    show({ slide, state: count(slide) - 1 });
  }
}

const forward = new Set(["ArrowRight", "ArrowDown", "PageDown", " ", "Enter", "n"]);
const backward = new Set(["ArrowLeft", "ArrowUp", "PageUp", "Backspace", "p"]);

addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey) {
    return;
  }
  if (forward.has(event.key)) {
    step(1);
  } else if (backward.has(event.key)) {
    step(-1);
  } else if (event.key === "Home") {
    show({ slide: 1, state: 0 });
  } else if (event.key === "End") {
    show({ slide: last, state: count(last) - 1 });
  } else {
    return;
  }
  event.preventDefault();
});

addEventListener("click", () => step(1));

// A fragment written from outside, by a deep link or by the back button.
addEventListener("hashchange", () => show(parseHash()));

show(parseHash());
