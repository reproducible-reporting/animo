// SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
// SPDX-License-Identifier: Apache-2.0

// The morph, which crosses an epoch boundary the way the crossfade does and also carries what
// the outgoing and the incoming region share from its old place to its new one.
//
// A match is a pair of elements, one in each region, that show the same ink.
// The outgoing element is translated from its own place to the place of the incoming one, and
// the incoming element from the place of the outgoing one to its own, so the two are at one
// position at every moment. The crossfade puts them at `1 - t` and `t`, and the
// `plus-lighter` on the renderings adds the two to one opaque element on the path, so the
// morph needs no opacity of its own and clones nothing. See *Findings*.
//
// The translations are routes and never states. They are animations over a `translate` whose
// inline style stays at rest, so a slide at rest carries none, and the geometry a later step
// reads is the layout's own once they are over. Until then, `slide.morphed` holds every
// element a morph is still moving, which is what a later step needs to know to read the
// layout under them and to settle them.

/**
 * The largest number of differences between the glyphs of two regions for which the glyphs
 * are matched.
 *
 * The diff takes time in proportion to the number of glyphs times the number of
 * differences, and a region beyond the bound crossfades its glyphs, which is always correct.
 * See *Performance* for the measurement the number comes from.
 */
const MORPH_DIFFERENCES = 400;

/** A distance, in CSS pixels, below which a match has not moved. */
const MORPH_STILL = 0.01;

/** No `translate`, as a keyframe states it. */
const AT_REST = "0px 0px";

/** The elements that draw ink of their own, which are the candidates of a match below tags. */
const INK = new Set(["use", "path", "image"]);

/**
 * The elements whose content is never drawn where it sits: definitions, the paths of a clip
 * and the outlines of a glyph. The walk for ink does not enter them, wherever typst puts them.
 */
const NOT_INK = new Set([
  "clipPath",
  "defs",
  "filter",
  "linearGradient",
  "marker",
  "mask",
  "pattern",
  "radialGradient",
  "symbol",
]);

/**
 * The attributes of a `<path>` that shape its ink, apart from its `d`.
 *
 * The stroke width is among them because a route does not scale a stroke. The colours are not,
 * because two copies of different colours sum to their interpolation (see *Findings*). Neither
 * is `fill-rule`, which typst writes as `nonzero` on every path.
 */
const PATH_SHAPE = [
  "stroke-width",
  "stroke-linecap",
  "stroke-linejoin",
  "stroke-miterlimit",
  "stroke-dasharray",
  "stroke-dashoffset",
];

/**
 * Plan the translations of the matches in an epoch stack a morph carries.
 *
 * The crossfade of the same stack is planned beside this, and nothing here touches an
 * opacity. The two renderings of the stack are the outgoing and the incoming region.
 */
function morphStack(effects, slide, { stack, from, to, record, options, mirror }) {
  const outgoing = stack.renderings[from];
  const incoming = stack.renderings[to];
  const timing = scheduled(options, record.timing, mirror);
  if (outgoing === undefined || incoming === undefined || timing === null) {
    return;
  }
  // The screen matrix of every parent read so far, because the glyphs of a run share one.
  const screen = new Map();
  const pairs = matches(slide, outgoing, incoming, new Set(record.names), screen);
  const routes = rigid(
    pairs.map((pair) => measured(slide, pair, screen)),
    slide.morphed,
  );
  for (const match of routes) {
    carry(effects, slide, match, timing, { stack, from, to, screen });
  }
}

/**
 * Whether a labelled group moves as one when a morph matches it.
 *
 * A tag and a named region do, and so does the rendering of one state of a `per-subslide`,
 * which is the same in both regions. An unnamed region is a box around content and not a
 * thing of its own, so what it holds is matched in its place.
 */
function movesAsOne(label) {
  return !label.startsWith("animo-") || stackLabel(label)?.kind === "subslide";
}

/**
 * The matches of two renderings of a region, as pairs of an outgoing and an incoming element.
 *
 * First the tag matches: two labelled groups of one name, paired by their index among the
 * groups of that name in document order. A tag the boundary changes is not one, because its
 * content differs, and what it holds is matched in its place. Then the ink matches: the
 * glyphs, paths and images outside every matched group, paired by a longest common
 * subsequence of their keys in document order, so a box beside a word keeps its place among
 * the letters. Every match has the same clips above it in both regions.
 */
function matches(slide, outgoing, incoming, changed, screen) {
  const pairs = [];
  const claimed = new Set();
  const clips = new Map();
  const above = (element, region) =>
    clipsAbove(slide, element, { region, laidOut: region === incoming }, clips, screen);
  const candidates = (region) =>
    Array.from(region.querySelectorAll("[data-typst-label]")).filter(
      (group) => movesAsOne(group.dataset.typstLabel) && !changed.has(group.dataset.typstLabel),
    );
  const partners = new Map();
  for (const group of candidates(incoming)) {
    const name = group.dataset.typstLabel;
    if (!partners.has(name)) {
      partners.set(name, []);
    }
    partners.get(name).push(group);
  }
  const seen = new Map();
  // Document order puts a group before the groups inside it, so a group inside a matched
  // one is found to be claimed before it could be matched itself.
  for (const group of candidates(outgoing)) {
    const name = group.dataset.typstLabel;
    const index = seen.get(name) ?? 0;
    seen.set(name, index + 1);
    const partner = partners.get(name)?.[index];
    if (
      partner === undefined ||
      within(group, claimed) ||
      within(partner, claimed) ||
      above(group, outgoing) !== above(partner, incoming)
    ) {
      continue;
    }
    claimed.add(group);
    claimed.add(partner);
    pairs.push([group, partner]);
  }
  const before = ink(outgoing, claimed);
  const after = ink(incoming, claimed);
  // Each key as a small number, so the diff compares numbers and not long strings.
  const numbers = new Map();
  const numbered = (element, region) => {
    const key = `${inkKey(element)}|${above(element, region)}`;
    let number = numbers.get(key);
    if (number === undefined) {
      number = numbers.size;
      numbers.set(key, number);
    }
    return number;
  };
  const common = commonSubsequence(
    before.map((element) => numbered(element, outgoing)),
    after.map((element) => numbered(element, incoming)),
    MORPH_DIFFERENCES,
  );
  for (const [i, j] of common ?? []) {
    pairs.push([before[i], after[j]]);
  }
  return pairs;
}

/** Whether an element is a matched group or sits inside one. */
function within(element, claimed) {
  for (let node = element; node !== null; node = node.parentElement) {
    if (claimed.has(node)) {
      return true;
    }
  }
  return false;
}

/** The glyphs, paths and images of a region in document order, leaving out claimed groups. */
function ink(region, claimed) {
  const found = [];
  const walk = (node) => {
    for (const child of node.children) {
      if (claimed.has(child) || NOT_INK.has(child.localName)) {
        continue;
      }
      if (INK.has(child.localName)) {
        found.push(child);
      } else {
        walk(child);
      }
    }
  };
  walk(region);
  return found;
}

/**
 * What an element draws, as a string that two elements share when they show the same ink.
 *
 * Typst writes a glyph as a `<use>` of a definition named by a hash of its outline, a shape as
 * a `<path>` whose `d` starts at its own origin, and an image as an `<image>` without a
 * position of its own, so in each case the place is in a transform and the key leaves it out.
 * The colours are left out of every key. See *Findings*.
 */
function inkKey(element) {
  if (element.localName === "use") {
    return `g:${element.href.baseVal}`;
  }
  if (element.localName === "image") {
    const size = ["width", "height"].map((name) => element.getAttribute(name));
    return `i:${element.href.baseVal} ${size.join(" ")}`;
  }
  const shape = PATH_SHAPE.map((name) => element.getAttribute(name) ?? "");
  return `p:${element.getAttribute("d")} ${shape.join(" ")}`;
}

/**
 * The clips above an element inside its region, as a string, with the place of each on the
 * screen.
 *
 * A `translate` carries a clip on the element itself but not the clip of an ancestor, which
 * stays where it is and cuts a moving element off at its edge (see *Findings*). Two copies
 * under two clips would then not sum to one opaque element, so a match needs the same clips
 * at the same places on both sides. A clip is named by its `clip-path`, whose id is a hash of
 * the clip's path. An element of the incoming region is placed as it is laid out, which leaves
 * out a morph translation that is still running above the clip.
 */
function clipsAbove(slide, element, side, clips, screen) {
  const parent = element.parentElement;
  if (parent === null || parent === side.region) {
    return "";
  }
  let found = clips.get(parent);
  if (found === undefined) {
    found = clipsAbove(slide, parent, side, clips, screen);
    const clip = parent.getAttribute("clip-path");
    if (clip !== null) {
      const { a, b, c, d, e, f } = matrixOf(parent, screen);
      const shift = side.laidOut ? running(slide, parent, screen) : { x: 0, y: 0 };
      const place = [a, b, c, d, e - shift.x, f - shift.y]
        .map((value) => value.toFixed(2))
        .join(" ");
      found = `${found}${clip} ${place};`;
    }
    clips.set(parent, found);
  }
  return found;
}

/**
 * A longest common subsequence of two lists of strings, as pairs of indices, or `null` when
 * the lists differ in more than `limit` places.
 *
 * The diff of the Myers kind, which walks the edit graph one difference at a time and so
 * takes time in proportion to the length of the lists times the number of differences. The
 * common head and tail are paired first, because an edit of a paragraph leaves most of it on
 * either side of the change.
 */
function commonSubsequence(a, b, limit) {
  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) {
    head += 1;
  }
  let tail = 0;
  while (
    tail < a.length - head &&
    tail < b.length - head &&
    a[a.length - 1 - tail] === b[b.length - 1 - tail]
  ) {
    tail += 1;
  }
  const middle = shortestEdit(
    a.slice(head, a.length - tail),
    b.slice(head, b.length - tail),
    limit,
  );
  if (middle === null) {
    return null;
  }
  const pairs = [];
  for (let k = 0; k < head; k += 1) {
    pairs.push([k, k]);
  }
  for (const [i, j] of middle) {
    pairs.push([head + i, head + j]);
  }
  for (let k = tail; k > 0; k -= 1) {
    pairs.push([a.length - k, b.length - k]);
  }
  return pairs;
}

/**
 * The common elements along a shortest edit of `a` into `b`, as pairs of indices in order, or
 * `null` when the edit needs more than `limit` insertions and deletions.
 *
 * `furthest[k]` is how far along `a` the walk got on diagonal `k = x - y`, and one copy of it
 * is kept per number of differences, which is what the walk back reads.
 */
function shortestEdit(a, b, limit) {
  const n = a.length;
  const m = b.length;
  const most = Math.min(n + m, limit);
  const offset = most + 1;
  const furthest = new Int32Array(2 * most + 3);
  const trace = [];
  for (let d = 0; d <= most; d += 1) {
    trace.push(furthest.slice());
    for (let k = -d; k <= d; k += 2) {
      const down = k === -d || (k !== d && furthest[offset + k - 1] < furthest[offset + k + 1]);
      let x = down ? furthest[offset + k + 1] : furthest[offset + k - 1] + 1;
      let y = x - k;
      while (x < n && y < m && a[x] === b[y]) {
        x += 1;
        y += 1;
      }
      furthest[offset + k] = x;
      if (x >= n && y >= m) {
        return walkBack(trace, offset, n, m);
      }
    }
  }
  return null;
}

/** The diagonal steps of the edit `shortestEdit` found, from its end back to its start. */
function walkBack(trace, offset, n, m) {
  const pairs = [];
  let x = n;
  let y = m;
  for (let d = trace.length - 1; d >= 0; d -= 1) {
    const furthest = trace[d];
    const k = x - y;
    const down = k === -d || (k !== d && furthest[offset + k - 1] < furthest[offset + k + 1]);
    const previous = down ? k + 1 : k - 1;
    const px = furthest[offset + previous];
    const py = px - previous;
    while (x > px && y > py) {
      x -= 1;
      y -= 1;
      pairs.push([x, y]);
    }
    x = px;
    y = py;
  }
  return pairs.reverse();
}

/**
 * A match with the distance it travels on the screen: from where the outgoing element is
 * displayed to where the incoming element is laid out.
 *
 * Both are what the page shows before the step, so a morph that interrupts another starts
 * from where the other one had got to. An incoming element is laid out where it is displayed
 * less the morph translations still running on it and above it, which the step is about to
 * end.
 */
function measured(slide, [outgoing, incoming], screen) {
  const start = origin(slide, outgoing, screen);
  const end = origin(slide, incoming, screen);
  const shift = running(slide, incoming, screen);
  return {
    outgoing,
    incoming,
    delta: { x: end.x - shift.x - start.x, y: end.y - shift.y - start.y },
  };
}

/** The morph translations still running on an element and above it, on the screen. */
function running(slide, element, screen) {
  const total = { x: 0, y: 0 };
  for (const node of morphedChain(slide, element)) {
    const offset = onScreen(node, translation(node), screen);
    total.x += offset.x;
    total.y += offset.y;
  }
  return total;
}

/**
 * Where an element puts its origin on the screen, in CSS pixels.
 *
 * `getScreenCTM()` includes the element's own `translate` in all three engines, and the `x`
 * and `y` of a `<use>` are an offset inside it. See *Findings*.
 * A glyph, a path or an image that no morph is moving has no `translate`, so its matrix is its
 * parent's followed by its own `transform` attribute, and the glyphs of a run share the
 * parent's.
 */
function origin(slide, element, screen) {
  const x = element.x?.baseVal?.value ?? 0;
  let point = new DOMPoint(x, element.y?.baseVal?.value ?? 0);
  if (INK.has(element.localName) && !slide.morphed.has(element)) {
    const own = element.transform.baseVal.consolidate();
    if (own !== null) {
      point = point.matrixTransform(own.matrix);
    }
    point = point.matrixTransform(matrixOf(element.parentNode, screen));
  } else {
    point = point.matrixTransform(element.getScreenCTM());
  }
  return { x: point.x, y: point.y };
}

/** The screen matrix of an element, read once per step. */
function matrixOf(element, screen) {
  let found = screen.get(element);
  if (found === undefined) {
    found = element.getScreenCTM();
    screen.set(element, found);
  }
  return found;
}

/** The element and its ancestors that a morph is still moving, up to its rendering. */
function morphedChain(slide, element) {
  const found = [];
  for (let node = element; node !== null; node = node.parentElement) {
    if (slide.morphed.has(node)) {
      found.push(node);
    }
    if (stackLabel(node.dataset?.typstLabel)?.kind === "epoch") {
      break;
    }
  }
  return found;
}

/** The `translate` an element computes, which is the one a running animation gives it. */
function translation(element) {
  const value = getComputedStyle(element).translate;
  if (value === "none" || value === "") {
    return { x: 0, y: 0 };
  }
  const [x = 0, y = 0] = value.split(/\s+/).map(Number.parseFloat);
  return { x, y };
}

/**
 * A `translate` of an element as a distance on the screen.
 *
 * A `translate` acts in the user space of the element's parent, which for a glyph is a run
 * that typst has flipped upside down, so the distance goes through the parent's matrix and
 * not through the element's own.
 */
function onScreen(element, { x, y }, screen) {
  const point = new DOMPoint(x, y, 0, 0).matrixTransform(matrixOf(element.parentNode, screen));
  return { x: point.x, y: point.y };
}

/** A distance on the screen as a `translate` of an element, which `onScreen` undoes. */
function inParent(element, { x, y }, screen) {
  const point = new DOMPoint(x, y, 0, 0).matrixTransform(
    matrixOf(element.parentNode, screen).inverse(),
  );
  return { x: point.x, y: point.y };
}

/** A `translate` as CSS, rounded to a ten thousandth of a pixel. */
function px({ x, y }) {
  const round = (value) => Math.round(value * 10000) / 10000 || 0;
  return `${round(x)}px ${round(y)}px`;
}

/**
 * Replace the glyph matches of a run of text that moves as one by one match of the two runs.
 *
 * Typst draws a run of text as a group of `<use>` elements, so a run whose every glyph is
 * matched to every glyph of one other run, at one distance, can be carried with one
 * animation instead of one per glyph. A run with a glyph a morph is still moving keeps its
 * matches, because the glyph's own translation would be added to the run's.
 */
function rigid(measuredPairs, morphed) {
  const result = [];
  let start = 0;
  while (start < measuredPairs.length) {
    const first = measuredPairs[start];
    const before = first.outgoing.parentElement;
    const after = first.incoming.parentElement;
    let end = start;
    while (
      end < measuredPairs.length &&
      measuredPairs[end].outgoing.parentElement === before &&
      measuredPairs[end].incoming.parentElement === after
    ) {
      end += 1;
    }
    const run = measuredPairs.slice(start, end);
    const whole =
      run.length === before.childElementCount &&
      run.length === after.childElementCount &&
      !isSlot(before) &&
      !isSlot(after) &&
      run.every(
        (pair) =>
          pair.outgoing.localName === "use" &&
          Math.hypot(pair.delta.x - first.delta.x, pair.delta.y - first.delta.y) < MORPH_STILL &&
          !morphed.has(pair.outgoing) &&
          !morphed.has(pair.incoming),
      );
    if (whole) {
      result.push({ outgoing: before, incoming: after, delta: first.delta });
    } else {
      result.push(...run);
    }
    start = end;
  }
  return result;
}

/** Whether a group is one of the two slots of a tag site, which hold other translations. */
function isSlot(group) {
  return group.hasAttribute("data-typst-label") || group.parentElement.hasAttribute("data-typst-label");
}

/**
 * Plan the two translations of one match, and remember the elements as moving.
 *
 * The outgoing element goes from what it shows to the place of the incoming one. A morph still
 * moving one of its ancestors goes on moving it in this step, to where `settleMorphs` sends it,
 * so the route of the outgoing element leaves out what that ancestor still travels, and the
 * two arrive together. The incoming element comes from the place of the outgoing one.
 *
 * A match that has not moved and that no morph is moving needs no animation.
 */
function carry(effects, slide, { outgoing, incoming, delta }, timing, where) {
  const { stack, from, to, screen } = where;
  const { morphed } = slide;
  if (
    Math.hypot(delta.x, delta.y) < MORPH_STILL &&
    !morphed.has(outgoing) &&
    !morphed.has(incoming)
  ) {
    return;
  }
  const travel = { ...delta };
  for (const node of morphedChain(slide, outgoing.parentElement)) {
    const now = onScreen(node, translation(node), screen);
    const heading = morphed.get(node).heading;
    const then = heading === null ? { x: 0, y: 0 } : onScreen(node, parsed(heading), screen);
    travel.x += now.x - then.x;
    travel.y += now.y - then.y;
  }
  const own = morphed.has(outgoing) ? translation(outgoing) : { x: 0, y: 0 };
  const step = inParent(outgoing, travel, screen);
  const end = px({ x: own.x + step.x, y: own.y + step.y });
  plan(
    effects,
    outgoing,
    { translate: "" },
    { translate: timing },
    { start: { translate: px(own) }, end: { translate: end } },
  );
  const back = inParent(incoming, { x: -delta.x, y: -delta.y }, screen);
  plan(
    effects,
    incoming,
    { translate: "" },
    { translate: timing },
    { start: { translate: px(back) }, end: { translate: AT_REST } },
  );
  morphed.set(outgoing, { epoch: from, stack, end, heading: end });
  morphed.set(incoming, { epoch: to, stack, end: null, heading: null });
}

/** A `translate` as `px` writes it, back as a distance. */
function parsed(value) {
  const [x = 0, y = 0] = value.split(/\s+/).map(Number.parseFloat);
  return { x, y };
}

/**
 * Plan every translation an earlier morph left running on a slide, before a step.
 *
 * A translation in a stack the step carries again runs on to where it was going, on the
 * clock of the new boundary, so it ends as the stack's new crossfade ends rather than in the
 * middle of it. The exception is an element of the rendering being entered, which this step
 * shows as it is laid out: its translation snaps to rest, and a morph of this step that
 * matches it again gives it a route of its own. Every other translation snaps to rest, as the
 * crossfade of a stack the step does not carry does.
 *
 * `carried` is the record of every stack the step carries, by stack.
 * `heading` records where each element is going in this step, which `carry` reads for the
 * ancestors of what it matches.
 */
function settleMorphs(effects, slide, to, carried, options, mirror) {
  for (const [element, record] of slide.morphed) {
    if (!element.getAnimations().some(ours)) {
      slide.morphed.delete(element);
      continue;
    }
    const own = record.epoch === to ? undefined : carried.get(record.stack);
    const timing = own === undefined ? null : scheduled(options, own.timing, mirror);
    if (timing === null) {
      plan(effects, element, { translate: "" });
      record.heading = null;
      continue;
    }
    plan(
      effects,
      element,
      { translate: "" },
      { translate: timing },
      { end: record.end === null ? null : { translate: record.end } },
    );
    record.heading = record.end;
  }
}
