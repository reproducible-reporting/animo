// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The animo presentation runtime.
//
// It keeps one position, `<slide>.<state>`, and three things in step with it:
// which slide container is shown, the URL fragment, and the `data-animo` attribute of the
// root element. The fragment is what makes a position addressable, which a deep link,
// a test and the reload of `typst watch` all need; the attribute is what lets a reader of
// the DOM see the position the runtime actually reached.
//
// Restoring a position snaps to it rather than animating into it, and the fragment is
// written with `replaceState`, so stepping through a deck leaves no history behind.

const slides = Array.from(document.querySelectorAll("[data-animo-slide]"));
const states = new Map(
  slides.map((slide) => [
    Number(slide.dataset.animoSlide),
    Math.max(1, Number(slide.dataset.animoStates ?? 1)),
  ]),
);
const last = slides.length;

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
  const count = states.get(slide) ?? 1;
  return { slide, state: Math.min(Math.max(position.state, 0), count - 1) };
}

let current = { slide: 1, state: 0 };

/** Show a position, and publish it in the fragment and on the root element. */
function show(position) {
  current = clamp(position);
  for (const slide of slides) {
    const shown = Number(slide.dataset.animoSlide) === current.slide;
    slide.toggleAttribute("data-animo-current", shown);
  }
  const hash = `#${current.slide}.${current.state}`;
  if (location.hash !== hash) {
    history.replaceState(null, "", hash);
  }
  document.documentElement.dataset.animo = `${current.slide}.${current.state}`;
}

/** Step one position forward or backward, crossing slide boundaries. */
function step(delta) {
  const count = states.get(current.slide) ?? 1;
  const state = current.state + delta;
  if (state >= 0 && state < count) {
    show({ slide: current.slide, state });
  } else if (delta > 0 && current.slide < last) {
    show({ slide: current.slide + 1, state: 0 });
  } else if (delta < 0 && current.slide > 1) {
    const slide = current.slide - 1;
    show({ slide, state: (states.get(slide) ?? 1) - 1 });
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
    show({ slide: last, state: (states.get(last) ?? 1) - 1 });
  } else {
    return;
  }
  event.preventDefault();
});

addEventListener("click", () => step(1));

// A fragment written from outside, by a deep link or by the back button.
addEventListener("hashchange", () => show(parseHash()));

show(parseHash());
