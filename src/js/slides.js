// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The slides of the deck as the runtime needs them: what is read from the DOM once, the
// registry that holds it, and the arithmetic on positions that depends on the shape of the
// deck and on nothing that is on screen.
//
// The runtime is the files of `src/js`, joined in the order `deck.typ` names into the one
// script of the page, so they share one module scope and none of them imports another.
// A function declaration is hoisted and may be called from any file at any time.
// A top level `const` is initialised when its own file is reached, so a value is only
// usable while the script loads by a file that comes after the one that defines it.
// Only `boot.js` calls into the other files while the script loads, and `input.js` registers
// its listeners then.

/** One slide of the deck, as the runtime needs it, read from the DOM once. */
function readSlide(element) {
  const plan = JSON.parse(element.dataset.animoPlan || '{"states":[]}');
  // Every occurrence of a tag name, in every epoch rendering of this slide, because
  // continuous state belongs to the slide and not to the rendering that is showing.
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
  // What each boundary redraws, by epoch, where epoch i holds the groups that the step
  // into it changes, each with the timing of the operations that changed it.
  // The first epoch begins no boundary.
  const epochs = (plan.epochs ?? [{}]).map((epoch) => epoch.regions ?? []);
  const carried = new Set(epochs.flat().map((region) => region.group));
  const stacks = readStacks(element);
  // The region groups a boundary may carry, in every rendering of an epoch stack, by epoch.
  // A group is looked up once here rather than per step, and by its own label, because a
  // label is a tag name and a name is whatever the author wrote.
  for (const stack of stacks) {
    if (stack.kind === "epoch") {
      stack.regions = stack.renderings.map((rendering) =>
        Array.from(rendering.querySelectorAll("[data-typst-label]")).filter((group) =>
          carried.has(group.dataset.typstLabel),
        ),
      );
    }
  }
  return {
    element,
    canvas: element.querySelector(":scope > .animo-canvas"),
    slots,
    // Every stack of the slide: the stack of its epoch renderings, and a stack for every
    // `per-subslide` in every epoch rendering and layer that lays it out.
    // A stack is looked up once here rather than per step, as the tag slots above are.
    stacks,
    epochs,
    states: plan.states ?? [],
    count: Math.max(1, Number(element.dataset.animoStates ?? 1)),
    // How the boundary above this slide is crossed: the name of a transition, or `auto` for
    // the deck's own, and its parameters with the duration the slide's `init` stated.
    // It is the setting of the slide a forward step enters and is used in both directions.
    transition: {
      name: element.dataset.animoTransition ?? "auto",
      args: JSON.parse(element.dataset.animoTransitionArgs || "{}"),
    },
    margin: plan.margin ?? 0,
    size: plan.canvas ?? null,
    // Where the tags the plan is relative to sit, measured when the slide is first shown.
    anchors: null,
    // The elements a morph is still moving, each with the epoch of its rendering, the label of
    // the region that holds it and where its route ends, which `morph.js` keeps.
    morphed: new Map(),
    // Which state this slide is showing, or `null` while it has never been rendered.
    // Its own rather than the deck's position, because a backward step that walks back
    // over a join leaves one slide and rewinds another, and the state it rewinds from is
    // the one this slide was left at.
    shown: null,
  };
}

/**
 * The settings of the deck, as the `data-animo-config` attribute of the deck element states
 * them, read once.
 *
 * The durations and the easing are custom properties on `:root` instead, because a media
 * query for a reader who asked for less motion has to reach them.
 */
const config = JSON.parse(document.querySelector(".animo-deck")?.dataset.animoConfig || "{}");

/** The slides of the deck by number, which `boot.js` fills once the page has loaded. */
const deck = new Map();

/** The number of the last slide, which is also how many there are. */
function lastSlide() {
  return deck.size;
}

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
  const slide = Math.min(Math.max(position.slide, 1), lastSlide());
  return { slide, state: Math.min(Math.max(position.state, 0), count(slide) - 1) };
}
