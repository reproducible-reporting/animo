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
 * How a step gets from the outgoing epoch rendering to the incoming one.
 *
 * One entry per strategy, and one selection below, because a step does not choose between
 * them. A morph between the two layouts of a region is the intended second entry and needs
 * the same seam, which is what the geometry of both renderings being readable is for.
 *
 * Each strategy is handed the renderings, the epoch a step leaves and the one it enters,
 * the groups of the regions whose content the boundary redraws, how the step moves and how
 * long it lasts when it is running backwards, and takes what it needs of that: the
 * crossfade below needs no `from`, where the morph will read the outgoing rendering's
 * geometry. An empty list of regions tells the strategy to snap, which is what a deep link,
 * a step inside one epoch and a reader who asked for less motion all produce.
 *
 * A strategy writes the state it is arriving at as style and animates from what the
 * element was showing into it, exactly as a display state is written, so an interrupted
 * boundary continues from where it is and stepping backwards undoes it.
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
   * A rendering no boundary is crossing is at zero already, so writing it changes nothing.
   *
   * A boundary that bounds its change in no region hands the whole rendering over instead,
   * and the two renderings crossfade as they are. Nothing outside the changed area is still
   * in that case, so there is nothing to contain the blend to.
   */
  crossfade(slide, { to, regions, options, mirror }) {
    // An entry with no group of its own names the rendering itself, which is what a change
    // that no region bounds redraws: a `wrap: none` tag outside any region has no box to
    // confine the change to. The rendering then hands its own ink over as a region hands
    // its own, and every region in it stays opaque, because each rendering is a complete
    // picture and the crossfade is between the two of them.
    const whole = regions.find((region) => region.group === null);
    slide.renderings.forEach((rendering, epoch) => {
      const active = epoch === to;
      // Whether this rendering hands a region over, which is what it paints through while
      // the rest of it is hidden.
      const handing =
        whole === undefined &&
        !active &&
        rendering.regions.some((group) =>
          regions.some((region) => region.group === group.dataset.typstLabel),
        );
      // A rendering hands its own ink over only if it is showing any: the one being left,
      // and any that a boundary this one interrupted is still fading out. One that is
      // showing none has nothing to hand over and stays hidden where it is.
      const leaving =
        whole !== undefined &&
        !active &&
        getComputedStyle(rendering.element).visibility === "visible";
      const fading = whole !== undefined && (active || leaving);
      rendering.element.style.visibility = active || leaving ? "visible" : "hidden";
      // A rendering is opaque when it is the one being shown, and when it is handing a
      // region over, which it paints through the visibility that region takes back.
      // It is transparent on every other, so that the rendering a whole boundary enters
      // has a state to come up from and the one it leaves has one to go down to: a
      // rendering hidden by its visibility alone has none, and would arrive at once.
      put(
        rendering.element,
        { opacity: active || handing ? "1" : "0" },
        fading ? { opacity: scheduled(options, whole.timing, mirror) } : null,
      );
      for (const group of rendering.regions) {
        const carried =
          whole === undefined
            ? regions.find((region) => region.group === group.dataset.typstLabel)
            : undefined;
        group.style.visibility = carried && !active ? "visible" : "";
        // A delayed region crossfades late and a long one crossfades slowly, which is what
        // holds the boundary open: an outgoing rendering keeps the visibility of the
        // regions it is handing over, so it paints them for the whole of the delay and the
        // whole of the duration.
        const effect = carried
          ? { opacity: scheduled(options, carried.timing, mirror) }
          : null;
        put(group, { opacity: active || whole !== undefined ? "1" : "0" }, effect);
      }
    });
  },
};

/** The strategy every epoch boundary of every deck takes. */
const transition = transitions.crossfade;

/**
 * How a step gets from one slide to the next.
 *
 * A table of its own rather than an entry in the one above, because the two are handed
 * different things and neither could use the other's. An epoch strategy is given the
 * renderings of one slide and the regions a boundary carries across, which it holds
 * still; a slide strategy is given two containers and has nothing to hold still, since
 * the two slides share nothing. One table would take the union of both and every entry
 * would ignore half of it. The seam is the same one, and richer slide transitions than a
 * crossfade and a cut are a second entry here, as the morph is a second entry above.
 *
 * `options` is how the boundary moves, or `null` when it snaps, which is what a cut, a
 * duration of zero, a deep link and any jump between slides that are not neighbours all
 * produce.
 */
const slideTransitions = {
  /**
   * Crossfade the two whole containers, and hand every other slide's opacity to zero.
   *
   * The slide being entered animates up from zero and the one being left down to it,
   * both through the `plus-lighter` the stylesheet puts on every slide, so the two add
   * to exactly one opaque slide at every moment and nothing dips halfway through, which
   * two slides of different background colours would otherwise do badly.
   * Every other slide is snapped to zero rather than left alone: that is what a slide
   * carries when it becomes the one being entered, so a boundary always has an opacity
   * to animate up from, and it is what cancels an animation left in flight on a slide
   * the deck has stepped past.
   */
  crossfade(shown, leaving, options) {
    for (const [number, slide] of deck) {
      const active = number === shown;
      const crossing = active || number === leaving;
      put(slide.element, { opacity: active ? "1" : "0" }, crossing ? { opacity: options } : null);
    }
  },
};

/** The strategy a boundary takes when its slide says `auto`, which is every ordinary one. */
const defaultSlideTransition = "crossfade";

/**
 * The strategy one boundary takes, by the name its slide carries.
 *
 * `auto` resolves here rather than in typst, so that the deck's own strategy is one
 * constant and a slide that named nothing follows it.
 * `none` resolves here too, and to the same entry: a cut still writes what the two
 * containers are showing, and what makes it a cut is the `null` timing `boundaryTiming`
 * hands it. So only a name of a strategy overrides the default, which is why the lookup
 * falls through rather than branching on the two literals.
 * A name typst does not know is refused at compile time, so nothing unknown arrives.
 */
function slideTransitionOf(name) {
  return slideTransitions[name] ?? slideTransitions[defaultSlideTransition];
}

/**
 * How the boundary above one slide is crossed, or `null` when it cuts.
 *
 * The slide named is the one a forward step enters, and its setting is what both
 * directions take, so stepping back over a boundary undoes exactly what stepping forward
 * over it did.
 */
function boundaryTiming(number) {
  const name = deck.get(number)?.transition;
  return name !== undefined && name !== "none" ? timing("--animo-transition-duration") : null;
}

/**
 * Show the epoch rendering that a state belongs to.
 *
 * A step that stays inside one epoch still writes this, because the rendering it is
 * showing is already the right one and writing the state it is in changes nothing.
 * A step that animates hands over every boundary between the two epochs, which is one for
 * an ordinary step and several for a backward step that walked over a join. A step that
 * snaps hands over none, which is what a deep link and a clamped fragment get.
 *
 * A step over more than one boundary drops the timings of the operations that opened them,
 * as it drops the schedules of the steps it walked over: those steps are ones the deck ran
 * through, and the one clock left is this step's own. A region that two of the boundaries
 * redraw is therefore carried once and by whichever entry is found first, since the two
 * say the same thing once their timings are gone.
 */
function putEpoch(slide, index, from, options, mirror) {
  const to = slide.states[index]?.epoch ?? 0;
  const crossed = [];
  if (options !== null && from !== null) {
    for (let epoch = Math.min(from, to) + 1; epoch <= Math.max(from, to); epoch += 1) {
      crossed.push(...(slide.epochs[epoch] ?? []));
    }
  }
  const regions = Math.abs(to - from) > 1 ? crossed.map(({ group }) => ({ group })) : crossed;
  transition(slide, { from, to, regions, options, mirror });
}

/**
 * Show the rendering that belongs to a state, out of the stack that holds one per state.
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
function putSubslides(slide, index) {
  slide.subslides.forEach((groups, state) => {
    for (const group of groups) {
      group.style.opacity = state === index ? "1" : "0";
    }
  });
}
