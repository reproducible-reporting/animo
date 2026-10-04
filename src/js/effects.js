// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// How an element is put into a display state: the timing a step takes from the stylesheet and
// from its operations, and the one function that writes a state and animates into it.
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
// same frame and all take that frame's time, which gives the step one clock by
// construction, and that clock is the one an epoch crossfade joins.
// `document.timeline.currentTime` is the time of the last frame the browser drew, and
// firefox 153 draws no frames at all while the page sits still, so on a deck being read
// rather than clicked through it lags by as long as the reader paused, and an animation
// told it began then is already over.
// See *Findings*.

/** The `id` of every animation the runtime creates, which is how it tells them from others. */
const ANIMATION_ID = "animo";

/**
 * Whether the runtime created an animation.
 *
 * The document may hold animations of the author's own, from a stylesheet or a script,
 * and what the runtime does to the animations of the page, such as pausing them, is done
 * to its own only.
 */
function ours(animation) {
  return animation.id === ANIMATION_ID;
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
 * The values live in CSS rather than in this file: the deck writes its `primitive-duration:`,
 * `transition-duration:` and `easing:` arguments there, and a reader who asked for less motion
 * gets a duration of zero from the media query that outranks them.
 * `property` is which duration is wanted: a primitive within a slide and a slide boundary
 * have one each, so a deck of hard cuts between slides keeps the motion inside them.
 * A duration of zero and a `transition: none` therefore reach the same `null`, which is
 * the one path that has no animation in it at all.
 */
function timing(property = "--animo-primitive-duration") {
  const style = getComputedStyle(document.documentElement);
  const duration = milliseconds(style.getPropertyValue(property));
  if (!(duration > 0)) {
    return null;
  }
  // An easing the stylesheet does not state is no easing at all.
  const easing = style.getPropertyValue("--animo-easing").trim() || "linear";
  return { duration, easing, fill: "none" };
}

/**
 * The options of one effect: the deck's own, held back and stretched by its operation's.
 *
 * A delay becomes the effect's delay and a duration the effect's duration, rather than a
 * timer of its own, which is what keeps the step's one clock: every animation of a step is
 * still created in one task and measured from the same instant.
 * A duration the operation does not state is the deck's own, `--animo-primitive-duration`,
 * so that a change of the deck's tempo reaches every operation that said nothing
 * and leaves the ones that did alone.
 *
 * Only a delay needs `fill: backwards`. The display state is written as inline style before
 * the animation is created, so an effect that does not hold its first keyframe while it
 * waits shows the state it is going to reach and then jumps back to where it started.
 *
 * A step that snaps stays snapped, delays and durations alike: `options` is `null` when the
 * deck's duration is zero, which is what a reader who asked for less motion, a deep link
 * and the first paint all get. A `duration:` that an operation states is covered by the
 * same rule and by no second one, because a media query cannot reach a number written in a
 * typst source.
 *
 * `mirror` is how long the step lasts, and it turns the schedule around.
 * A backward step is the forward one played from the other end, so an operation that ran
 * from `delay` to `delay + duration` runs from `mirror - delay - duration` instead and
 * takes exactly as long.
 * The last thing to arrive is then the first to leave, so a backward step undoes a forward
 * one in time as well as in geometry. It is `null` for a step that plays forwards.
 */
function scheduled(options, timing, mirror = null) {
  if (options === null) {
    return null;
  }
  const duration =
    timing?.duration === undefined ? options.duration : timing.duration * 1000;
  const own = duration === options.duration ? options : { ...options, duration };
  const stated = (timing?.delay ?? 0) * 1000;
  const delay = mirror === null ? stated : mirror - stated - duration;
  return delay > 0 ? { ...own, delay, fill: "backwards" } : own;
}

/**
 * How long one step lasts, in milliseconds, which is what a backward step mirrors about.
 *
 * The step ends when the last of its operations does, so this is the largest
 * `delay + duration` over all of them. The resolver could only add up the operations that
 * stated a duration, because the one an operation does not state lives in the stylesheet,
 * so it hands over the two halves and they are added here: `stated` is the largest end it
 * could compute, and `unstated` the largest delay of the operations whose duration is the
 * deck's own.
 *
 * A step that states no timing at all carries no span, and lasts exactly one step of the
 * deck, which is what every operation of it takes.
 */
function span(record, options) {
  // A step that carries no record is one whose every operation starts with it and takes the
  // deck's own step, which is an unstated delay of zero, so that is what stands in for it.
  // An absent `unstated` beside a `stated` is the other case and adds nothing, because the
  // step holds no operation whose duration the stylesheet owns.
  const { stated, unstated } = record ?? { unstated: 0 };
  return Math.max(
    stated === undefined ? 0 : stated * 1000,
    unstated === undefined ? 0 : unstated * 1000 + options.duration,
  );
}

/** What an element is showing right now, for the properties named, as `declarations` has it. */
function showing(element, names) {
  const computed = getComputedStyle(element);
  const read = {
    opacity: () => computed.opacity,
    translate: () => (computed.translate === "none" ? "0px 0px" : computed.translate),
    scale: () => (computed.scale === "none" ? "1" : computed.scale),
  };
  return Object.fromEntries(names.map((name) => [name, read[name]()]));
}

/**
 * Put a display state on one element, animating into it unless the step snaps.
 *
 * `options` is `null` for a step that snaps, and otherwise one options object per property
 * of `to`, because two operations of one step may start at different moments and an effect
 * has one delay.
 */
function put(element, to, options) {
  const names = Object.keys(to);
  const from = options === null ? null : showing(element, names);
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
  const into = showing(element, names);
  // Only the properties this step actually changes, because in chromium 151 a `translate`
  // or `scale` that is equal at both ends stops the browser from drawing the `opacity`
  // beside it, and the element stays as it was until the step ends and then jumps.
  // Measured; see *Findings*.
  const changed = names.filter((name) => from[name] !== into[name]);
  // One effect per group of properties that are timed alike, so that a step whose
  // operations are timed alike, which is every step that says nothing about timing, is
  // still one effect on this element.
  const groups = new Map();
  for (const name of changed) {
    const found = groups.get(JSON.stringify(options[name]));
    if (found === undefined) {
      groups.set(JSON.stringify(options[name]), { timing: options[name], names: [name] });
    } else {
      found.names.push(name);
    }
  }
  for (const group of groups.values()) {
    const only = (values) =>
      Object.fromEntries(group.names.map((name) => [name, values[name]]));
    element.animate([only(from), only(into)], { ...group.timing, id: ANIMATION_ID });
  }
}
