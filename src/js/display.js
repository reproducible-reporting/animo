// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// What a state of a slide looks like on the page: where each position puts what it addresses,
// the CSS of a tag's display state and of a pan, the anchors a position is relative to, and
// `planState`, which plans one state of a slide on its canvas and on every tag it addresses.

/** The canvas origin, which is the anchor a position with no `relto` is measured from. */
const ORIGIN = { x: 0, y: 0 };

/**
 * Where one position puts what it addresses, in typst points.
 *
 * `anchor(relto) + offset - anchor(self)`, where the anchor of `null` is the canvas origin.
 * `self` is the moved tag, or `null` for the viewport, which is anchored at the origin too.
 * A pair whose anchor is the tag's own name is therefore the identity, which is what a tag
 * the timeline never moved carries, and it needs no anchor to resolve.
 *
 * An anchor the page does not have leaves the offset alone, which can only happen on a page
 * edited by hand: typst refuses a timeline relative to a tag its slide does not have.
 */
function resolvePosition(slide, position, self) {
  const own = self === null ? null : (slide.anchors.get(self) ?? null);
  const along = (which) => {
    const axis = position?.[which];
    if (axis === undefined) {
      return 0;
    }
    if (axis.relto === self) {
      return axis.offset;
    }
    const target = axis.relto === null ? ORIGIN : (slide.anchors.get(axis.relto) ?? null);
    if (target === null || (self !== null && own === null)) {
      return axis.offset;
    }
    return target[which] + axis.offset - (self === null ? 0 : own[which]);
  };
  return { x: along("x"), y: along("y") };
}

/**
 * The CSS of one tag's display state.
 *
 * Only the individual transform properties, never the `transform` shorthand: it would
 * clobber the positioning typst wrote on the labelled group that holds this one.
 * A length inside a frame's SVG is a user unit, which is a typst point, so a move stays
 * the same fraction of the slide at any window size without the runtime measuring one.
 *
 * One `scale` value rather than two while the two axes agree, because a property whose
 * keyframes are equal at both ends stops the browser from drawing the ones beside it
 * (see *Findings*), and the engines do not compute `1 1` to the same string, so a tag at
 * rest would otherwise look like a tag that changed.
 */
function declarations(slide, name, display) {
  const { x, y } = resolvePosition(slide, display, name);
  const factors = display.scale;
  return {
    opacity: display.hidden ? "0" : "1",
    translate: `${x}px ${y}px`,
    scale: factors.x === factors.y ? String(factors.x) : `${factors.x} ${factors.y}`,
  };
}

/**
 * The declarations that centre the transforms of one slot on the element's own box.
 *
 * Without this a `scale` grows the element about the origin of the whole frame and moves it
 * far across the slide. Both declarations are planned here, on the one element the runtime
 * transforms, and never as a rule in the stylesheet: they re-anchor the element's own
 * `transform` attribute as much as the properties beside it, so a selector broad enough to
 * reach a group typst positioned displaces it, silently and with no transform property set
 * at all. A labelled group is not always a tag site, because a region's footprint carries
 * a label too, and its children are the region's content. See *Findings*.
 */
const CENTRED = { "transform-box": "fill-box", "transform-origin": "center" };

/**
 * The tags whose anchor this slide's plan asks for, as a set of names.
 *
 * A position is `anchor(relto) + offset - anchor(self)`, so a pair naming the tag's own
 * anchor asks for nothing: the two terms cancel whatever that anchor is. Every state of a
 * plan holds every addressed tag, so a slide of tags that merely appear asks for none.
 */
function wantedAnchors(slide) {
  const names = new Set();
  const wanted = (position, self) => {
    for (const axis of [position?.x, position?.y]) {
      if (axis === undefined || axis.relto === self) {
        continue;
      }
      for (const name of [axis.relto, self]) {
        if (name !== null) {
          names.add(name);
        }
      }
    }
  };
  for (const state of slide.states) {
    wanted(state.pan, null);
    for (const [name, display] of Object.entries(state.tags ?? {})) {
      wanted(display, name);
    }
  }
  return names;
}

/**
 * Where the first site of every tag the plan asks about sits on the canvas, in points.
 *
 * The anchor is the origin of the tag's labelled group, which is the top-left corner of the
 * wrapper typst laid out, and not the box of its ink: that is the corner the paged outputs
 * read as well, so the two targets resolve the same quantity rather than two neighbours.
 * It is mapped into the user space of the frame, whose units are typst points and whose
 * origin is the canvas origin, so the pan of the canvas cancels out of it.
 *
 * The first site is the first occurrence in document order, which is in the first epoch
 * rendering that lays the tag out, since the renderings are placed in epoch order.
 *
 * It has to be read while the slide has a layout and before the runtime has written a
 * display state on it, because a tag around the anchor would otherwise move it by
 * whatever state that happens to be.
 */
function measureAnchors(slide) {
  const anchors = new Map();
  for (const name of wantedAnchors(slide)) {
    const group = slide.slots.get(name)?.[0]?.parentNode;
    if (group === undefined) {
      // Typst refuses a timeline relative to a tag its slide does not have, so this is a
      // page edited by hand, and the position resolves as if nothing were relative to a tag.
      anchors.set(name, null);
      continue;
    }
    const frame = group.ownerSVGElement.getScreenCTM().inverse();
    const corner = frame.multiply(group.getScreenCTM());
    anchors.set(name, { x: corner.e, y: corner.f });
  }
  return anchors;
}

/** A percentage of `full` that covers `length`, without the `-0` a zero pan would give. */
function percent(length, full) {
  return full > 0 ? (100 * length) / full || 0 : 0;
}

/**
 * The CSS of one state's pan, which is a `translate` on the canvas.
 *
 * A percentage, because a translate in percent is a fraction of the canvas's own box, which
 * follows the window as the canvas does, and it animates in every engine: a length written
 * as a multiple of `--animo-unit` would have to put a custom property into a keyframe.
 */
function viewport(slide, state) {
  const at = resolvePosition(slide, state.pan, null);
  // A `relto` puts the named tag where the body of a fresh slide starts, which is the
  // deck's margin in from the canvas origin. An axis measured from the origin itself is
  // already the position of the viewport.
  const along = (which) =>
    state.pan?.[which]?.relto == null ? at[which] : at[which] - slide.margin;
  const x = percent(-along("x"), slide.size.width);
  const y = percent(-along("y"), slide.size.height);
  return { translate: `${x}% ${y}%` };
}

/**
 * Plan one state of a slide on its canvas, on its stacks, and on every occurrence of every
 * tag it addresses.
 *
 * The pan goes on the canvas and never on the frame inside it: the epoch renderings are
 * stacked in that frame, so moving the canvas moves them all and keeps them registered.
 * The canvas is an HTML element, so its `translate` composes with nothing typst wrote.
 *
 * Continuous state is written on every occurrence in every rendering and not only in the
 * one being shown, so that entering an epoch needs no initialisation and a step that both
 * replaces and moves a tag moves it by the same amount in the rendering it leaves and in
 * the one it arrives at.
 *
 * Every effect of the step, the boundary's included, is planned into `effects`, and the
 * caller applies them in one task, so none of the animations is told when it began and the
 * browser starts them all on the same frame.
 *
 * `step` is the state whose own operations are being walked, which is the higher of the
 * two a step runs between, forwards and backwards alike: one step is one schedule, and a
 * backward step is that schedule mirrored rather than a schedule of its own. A backward
 * step that walked over a join runs between states that are not neighbours, and the
 * schedules of the steps it walked over go with them: what the audience saw across a join
 * was one motion redirected before it arrived, which neither schedule replayed on its own
 * reproduces, so the way back is one motion too.
 *
 * `reverse` says which way that schedule is read. Every effect of a backward step is
 * mirrored about the length of the step it undoes, so the operation that arrived last is
 * the one that leaves first, and the step ends where the earlier state began.
 */
function planState(
  effects,
  slide,
  index,
  options,
  { from = null, step = index, reverse = false } = {},
) {
  const state = slide?.states[index];
  if (state === undefined) {
    return;
  }
  const timings = slide.states[step]?.timing ?? {};
  const mirror =
    reverse && options !== null ? span(slide.states[step]?.span, options) : null;
  if (slide.canvas !== null && slide.size !== null) {
    plan(effects, slide.canvas, viewport(slide, state), options === null
      ? null
      : { translate: scheduled(options, timings.pan, mirror) });
  }
  for (const [name, display] of Object.entries(state.tags ?? {})) {
    const own = timings.tags?.[name] ?? {};
    const timed =
      options === null
        ? null
        : {
            opacity: scheduled(options, own.opacity, mirror),
            translate: scheduled(options, own.translate, mirror),
            scale: scheduled(options, own.scale, mirror),
          };
    for (const element of slide.slots.get(name) ?? []) {
      plan(effects, element, CENTRED);
      plan(effects, element, declarations(slide, name, display), timed);
    }
  }
  planStacks(effects, slide, { index, from, options, mirror });
  slide.shown = index;
}
