// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// How a step crosses a boundary, of an epoch inside a slide and of a slide inside the deck.
//
// A slide is one `html.frame` holding one rendering per content state, stacked at one
// point, of which one is shown at a time. A step that stays inside an epoch touches only
// the display state of the rendering it is already showing. A step that crosses a boundary
// hands over the regions whose content changed, which is what `transitions` below does,
// and leaves everything else alone, because the two renderings are pixel-identical outside
// those regions.
//
// A slide boundary is the same mechanism one container out, and it is the whole container
// that crosses, because two slides share nothing to hold still. Two slides are laid out
// while they cross and no more: laying every slide of a deck out for the whole session
// costs a long deck seconds of first paint, which is paid at every reload of the live
// preview. See *Findings*.

/**
 * How a step carries a region from the outgoing epoch rendering to the incoming one.
 *
 * One entry per transition, and the plan names the one each region takes: a region record of
 * a boundary has an optional `transition`, the name of an entry here, and an optional
 * `args`, which is handed to the transition as part of the record. A region with no
 * `transition` crossfades, so a plan that names none is the plan of a deck in which every
 * boundary crossfades.
 *
 * `planEpoch` has already planned the state at rest of every rendering and of every region
 * group in it when a transition runs: the rendering being entered shown and opaque, every
 * other rendering hidden, and every region opaque in the rendering being entered and
 * transparent in the others. A transition plans effects for what it carries in place of
 * those, and an effect it plans replaces the one at rest for the same element and property.
 *
 * Each transition is handed the effects of the step being planned, the slide, the epoch a step
 * leaves and the one it enters, the records of the regions it carries, how the step moves
 * and how long it lasts when it is running backwards, and takes what it needs of that: the
 * crossfade below needs no `from`, where a morph would read the outgoing rendering's
 * geometry. It runs in the phase that reads and writes nothing, so any geometry it reads is
 * the geometry of the page before the step.
 *
 * A transition plans the state it is arriving at and animates from what the element was
 * showing into it, exactly as a display state is planned, so an interrupted boundary
 * continues from where it is and stepping backwards undoes it.
 */
const transitions = {
  /**
   * Crossfade the regions the boundary redraws, and nothing else.
   *
   * The incoming rendering is shown whole and at once, which is invisible because the
   * renderings are pixel-identical everywhere but in those regions. Every other rendering
   * is hidden, and only the regions it is handing over take their visibility back, so it
   * paints nowhere else and the containment is exact rather than blended to within a
   * rounding error. The halves of one region add to one through the `plus-lighter` the
   * stylesheet puts on the renderings.
   *
   * Every rendering that is not the one being entered hands the region over, and not only
   * the one the step is leaving. A boundary crossed while an earlier one is still running
   * finds two of them painting the region, which is what a long `duration:` on a `replace`
   * makes easy to reach and what a `wait:` shorter than a step or a presenter clicking
   * twice reaches as well. Fading all of them out on the new boundary's clock is what
   * keeps the sum at one: the outgoing renderings leave under one easing while the
   * incoming one arrives under its complement, whatever they were showing when it began.
   * A rendering no boundary is crossing is at zero already, so planning it changes nothing.
   *
   * A boundary that bounds its change in no region hands the whole rendering over instead,
   * and the two renderings crossfade as they are. Nothing outside the changed area is still
   * in that case, so there is nothing to contain the blend to.
   */
  crossfade(effects, slide, { to, regions, options, mirror }) {
    // An entry with no group of its own names the rendering itself, which is what a change
    // that no region bounds redraws: a `wrap: none` tag outside any region has no box to
    // confine the change to. The rendering then hands its own ink over as a region hands
    // its own, and every region in it stays opaque, because each rendering is a complete
    // picture and the crossfade is between the two of them.
    const whole = regions.find((region) => region.group === null);
    slide.renderings.forEach((rendering, epoch) => {
      const active = epoch === to;
      if (whole !== undefined) {
        // A rendering hands its own ink over only if it is showing any: the one being left,
        // and any that a boundary this one interrupted is still fading out. One that is
        // showing none has nothing to hand over and stays hidden where it is.
        const leaving =
          !active && getComputedStyle(rendering.element).visibility === "visible";
        if (active || leaving) {
          plan(
            effects,
            rendering.element,
            { visibility: "visible", opacity: active ? "1" : "0" },
            { opacity: scheduled(options, whole.timing, mirror) },
          );
        }
        for (const group of rendering.regions) {
          plan(effects, group, { opacity: "1" });
        }
        return;
      }
      for (const group of rendering.regions) {
        const carried = regions.find((region) => region.group === group.dataset.typstLabel);
        if (carried === undefined) {
          continue;
        }
        // A rendering that hands a region over is opaque, and paints through the
        // visibility that region takes back while the rest of it stays hidden.
        if (!active) {
          plan(effects, rendering.element, { opacity: "1" });
          plan(effects, group, { visibility: "visible" });
        }
        // A delayed region crossfades late and a long one crossfades slowly, which is what
        // holds the boundary open: an outgoing rendering keeps the visibility of the
        // regions it is handing over, so it paints them for the whole of the delay and the
        // whole of the duration.
        plan(
          effects,
          group,
          { opacity: active ? "1" : "0" },
          { opacity: scheduled(options, carried.timing, mirror) },
        );
      }
    });
  },
  /**
   * Crossfade the regions the boundary redraws, and carry what the two versions of each
   * share from its old place to its new one, which `morphRegions` plans.
   */
  morph(effects, slide, context) {
    transitions.crossfade(effects, slide, context);
    morphRegions(effects, slide, context);
  },
};

/** The transition a region takes when its record names none, which is every ordinary one. */
const defaultTransition = "crossfade";

/**
 * The transition of an epoch boundary by the name a region record carries.
 *
 * A name typst does not know is refused at compile time, so nothing unknown arrives, and a
 * record that names none takes the default.
 */
function transitionOf(name) {
  return transitions[name] ?? transitions[defaultTransition];
}

/**
 * How a step gets from one slide to the next.
 *
 * A table of its own rather than an entry in the one above, because the two are handed
 * different things and neither could use the other's. An epoch transition is given the
 * renderings of one slide and the regions a boundary carries across, which it holds
 * still; a slide transition is given two containers and has nothing to hold still, since
 * the two slides share nothing. One table would take the union of both and every entry
 * would ignore half of it.
 *
 * A slide transition is a function of the boundary's owner, the slide with the higher
 * number, and of a progress `p` that is 0 where the owner is not there yet and 1 where it
 * is. `at(p, args)` gives the display state of the owner and of the other slide at one of
 * those two ends, and `planSlides` animates from what each container is showing into the
 * end a step is heading for. A forward step heads for 1 and a backward step for 0, so a
 * backward step is the forward one played from the other end and needs no direction of its
 * own. The owner comes later in the document, so it is in front in both directions.
 *
 * `blend` is the `mix-blend-mode` both containers take for the boundary, and the empty
 * string leaves the stylesheet's `plus-lighter`. Two slides that overlap while both are
 * opaque have to cover rather than add, because two opaque grounds of different colours sum
 * to a third colour. A crossfade is the one transition that wants them to add.
 *
 * A `direction` is the direction of travel on a forward step, which typst writes as `ltr`,
 * `rtl`, `ttb` or `btt`. Typst states every parameter, its defaults included, so the
 * runtime holds no defaults of its own.
 */
const slideTransitions = {
  /**
   * Fade the owner in over the other slide, which fades out.
   *
   * The two add to exactly one opaque slide at every moment through the `plus-lighter` the
   * stylesheet puts on every slide, so nothing dips halfway through, which two slides of
   * different background colours would otherwise do badly.
   */
  crossfade: {
    blend: "",
    at: (p) => ({ owner: { opacity: String(p) }, other: { opacity: String(1 - p) } }),
  },
  /** Move the owner in from one edge while it moves the other slide out at the opposite one. */
  push: {
    blend: "normal",
    at: (p, { direction }) => ({
      owner: { opacity: "1", translate: travelled(direction, p - 1) },
      other: { opacity: "1", translate: travelled(direction, p) },
    }),
  },
  /** Move the owner in from one edge over the other slide, which stays where it is. */
  cover: {
    blend: "normal",
    at: (p, { direction }) => ({
      owner: { opacity: "1", translate: travelled(direction, p - 1) },
      other: { opacity: "1" },
    }),
  },
  /**
   * Reveal the owner over the other slide behind an edge that travels across the stage.
   *
   * The clip is an `inset` whose one side shrinks from the whole stage to nothing, and the
   * other three sides stay at zero, so the two ends of the boundary interpolate.
   */
  wipe: {
    blend: "normal",
    at: (p, { direction }) => ({
      owner: { opacity: "1", "clip-path": hidden(direction, 1 - p) },
      other: { opacity: "1" },
    }),
  },
};

/** The way each direction travels, as a fraction of the stage along each axis. */
const TRAVEL = {
  ltr: { x: 1, y: 0 },
  rtl: { x: -1, y: 0 },
  ttb: { x: 0, y: 1 },
  btt: { x: 0, y: -1 },
};

/**
 * A `translate` that has carried a container `fraction` of the stage along a direction.
 *
 * A percentage of a container's own box is a fraction of the stage, because a slide fills
 * it, so a pushed slide keeps its place at any window size without the runtime measuring
 * one.
 *
 * No travel is the empty string, which is the slide at rest, rather than a translate of
 * zero. An engine computes the two to different strings, so the next boundary would find a
 * difference where there is none and animate a property that does not change, which in
 * chromium 151 stops the `opacity` beside it from being drawn. See *Findings*.
 */
function travelled(direction, fraction) {
  const { x, y } = TRAVEL[direction];
  return fraction === 0 ? "" : `${100 * x * fraction || 0}% ${100 * y * fraction || 0}%`;
}

/**
 * A `clip-path` that hides the part of a container that an edge travelling along a
 * direction has not reached, which is `fraction` of the stage.
 *
 * The side clipped is the one the edge travels towards. The sides follow the order of
 * `inset`: top, right, bottom, left. Nothing hidden is the slide at rest, for the reason
 * `travelled` gives.
 */
function hidden(direction, fraction) {
  if (fraction === 0) {
    return "";
  }
  const side = { ltr: 1, rtl: 3, ttb: 2, btt: 0 }[direction];
  const sides = [0, 0, 0, 0];
  sides[side] = 100 * fraction;
  return `inset(${sides.map((value) => `${value}%`).join(" ")})`;
}

/** The transition a boundary takes when neither its slide nor the deck names one. */
const defaultSlideTransition = "crossfade";

/**
 * The transition the boundary above one slide takes, as `{name, args}`, or `null` for a
 * slide the deck does not have.
 *
 * `auto` resolves here rather than in typst, to the deck's own transition, which the deck
 * states in its configuration and which is the crossfade on a page that states none.
 * A `duration` the slide's `init` states travels in `args` either way, because it belongs
 * to the slide rather than to the transition.
 * A name or a parameter typst does not know is refused at compile time, so nothing unknown
 * arrives.
 */
function slideTransitionOf(number) {
  const slide = deck.get(number);
  if (slide === undefined) {
    return null;
  }
  if (slide.transition.name !== "auto") {
    return slide.transition;
  }
  const { name = defaultSlideTransition, ...args } = config.transition ?? {};
  return { name, args: { ...args, ...slide.transition.args } };
}

/**
 * How a boundary that takes a transition is crossed, or `null` when it cuts.
 *
 * The deck's `--animo-transition-duration` is the default of a slide whose `init` states no
 * `duration`, and one it states overrides it, also when the deck's is zero, which is how a
 * deck of hard cuts pushes one slide in. A duration of zero is a cut, whatever the
 * transition. A reader who asked for less motion gets a cut everywhere, because `timing`
 * reads `--animo-motion` first.
 */
function boundaryTiming(transition) {
  if (transition === null) {
    return null;
  }
  const own = timing("--animo-transition-duration");
  if (own === null) {
    return null;
  }
  const { duration } = transition.args;
  const options = duration === undefined ? own : { ...own, duration: duration * 1000 };
  return options.duration > 0 ? options : null;
}

/**
 * Plan every slide container of the deck, and the boundary a step crosses between two.
 *
 * Every slide is planned at rest first: the slide being shown opaque, every other one
 * transparent, and none of them moved, clipped or blended by a transition. A slide that
 * becomes the one being entered therefore always starts from a state this function wrote.
 * The two slides a boundary crosses are then planned by its transition, in place of their
 * state at rest, and the properties of theirs that their transition does not name move to
 * rest on the boundary's clock. That is what takes a slide that a push left half way out of
 * the stage back into it when a crossfade interrupts the push.
 *
 * `options` is how the boundary moves, or `null` when it snaps, which is what a cut, a
 * duration of zero, a deep link and any jump between slides that are not neighbours all
 * produce. A boundary that snaps leaves both slides at rest.
 *
 * Each container animates from what it is showing, so an interrupted boundary continues
 * from where it is and stepping back undoes it. The exception is a slide in `fresh`, which
 * had no layout before this step and shows nothing worth continuing from: it starts at the
 * far end of the transition instead, which for a push is outside the stage.
 *
 * The transition's blend stays on the two slides after the boundary has been crossed, for as
 * long as the slide being left keeps its layout. A slide that a cover or a wipe has covered
 * is still laid out under the owner, and under `plus-lighter` the two would add.
 */
function planSlides(effects, shown, leaving, options, transition, fresh) {
  for (const [number, slide] of deck) {
    const rest = { opacity: number === shown ? "1" : "0", translate: "", "clip-path": "" };
    const crossing = options !== null && (number === shown || number === leaving);
    plan(effects, slide.element, rest, crossing ? timed(rest, options) : null);
    // A blend is not animated, because no value between two of them exists.
    plan(effects, slide.element, { "mix-blend-mode": "" });
  }
  if (options === null || leaving === null) {
    return;
  }
  const entry = slideTransitions[transition.name] ?? slideTransitions[defaultSlideTransition];
  const { args } = transition;
  const owner = Math.max(shown, leaving);
  const p = shown === owner ? 1 : 0;
  const end = entry.at(p, args);
  const start = entry.at(1 - p, args);
  for (const [number, role] of [
    [owner, "owner"],
    [Math.min(shown, leaving), "other"],
  ]) {
    const element = deck.get(number).element;
    plan(effects, element, end[role], timed(end[role], options), {
      start: fresh.has(number) ? start[role] : null,
    });
    plan(effects, element, { "mix-blend-mode": entry.blend });
  }
}

/** One options object per property of a display state, which is what `plan` takes. */
function timed(state, options) {
  return Object.fromEntries(Object.keys(state).map((property) => [property, options]));
}

/**
 * Plan the epoch rendering that a state belongs to, and the regions its boundaries carry.
 *
 * Which rendering is shown is decided here, for every transition alike: the one the state
 * belongs to is shown and opaque, every other one is hidden and transparent, and every
 * region group is opaque in the rendering being shown and transparent in the others.
 * That is the state at rest, and the regions a boundary carries are then planned by the
 * transition each names, in place of their state at rest. One boundary may therefore carry
 * one region with one transition and another region with another.
 *
 * A step that stays inside one epoch still plans this, because the rendering it is
 * showing is already the right one and writing the state it is in changes nothing.
 * A step that animates hands over every boundary between the two epochs, which is one for
 * an ordinary step and several for a backward step that walked over a join. A step that
 * snaps hands over none, which is what a deep link and a clamped fragment get.
 *
 * A step over more than one boundary drops the timings of the operations that opened them,
 * as it drops the schedules of the steps it walked over: those steps are ones the deck ran
 * through, and the one clock left is this step's own. A region that two of the boundaries
 * redraw is carried once, by the first record found for it.
 *
 * A record with no group stands for the whole rendering, which holds every region, so a
 * step that carries one carries nothing else.
 */
function planEpoch(effects, slide, index, from, options, mirror) {
  const to = slide.states[index]?.epoch ?? 0;
  slide.renderings.forEach((rendering, epoch) => {
    const active = epoch === to;
    plan(effects, rendering.element, {
      visibility: active ? "visible" : "hidden",
      opacity: active ? "1" : "0",
    });
    for (const group of rendering.regions) {
      plan(effects, group, { visibility: "", opacity: active ? "1" : "0" });
    }
  });
  const crossed = [];
  if (options !== null && from !== null) {
    for (let epoch = Math.min(from, to) + 1; epoch <= Math.max(from, to); epoch += 1) {
      crossed.push(...(slide.epochs[epoch] ?? []));
    }
  }
  const walked = Math.abs(to - from) > 1;
  const records = [];
  for (const record of crossed) {
    if (!records.some((other) => other.group === record.group)) {
      const { timing, ...untimed } = record;
      records.push(walked ? untimed : record);
    }
  }
  const whole = records.find((record) => record.group === null);
  const carried = whole === undefined ? records : [whole];
  // Before the transitions, so that a morph of this step that matches an element again plans
  // its route in place of where an earlier morph was taking it.
  settleMorphs(effects, slide, to, carried, options, mirror);
  const named = new Map();
  for (const record of carried) {
    const name = record.transition ?? defaultTransition;
    named.set(name, [...(named.get(name) ?? []), record]);
  }
  for (const [name, regions] of named) {
    transitionOf(name)(effects, slide, { from, to, regions, options, mirror });
  }
}

/**
 * Plan the rendering that belongs to a state, out of the stack that holds one per state.
 *
 * This is how a value finer than a slide number reaches the page at all.
 * One epoch rendering covers a run of states, so typst renders every value and the choice
 * is made here.
 *
 * It snaps rather than animating, in a step that animates as much as in one that does not.
 * A number is read rather than watched, and two numbers crossfading into each other are
 * two numbers neither of which can be read; the stylesheet's `plus-lighter` would make
 * them add rather than cover as well.
 */
function planSubslides(effects, slide, index) {
  slide.subslides.forEach((groups, state) => {
    for (const group of groups) {
      plan(effects, group, { opacity: state === index ? "1" : "0" });
    }
  });
}
