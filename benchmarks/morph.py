#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Measure what a morph costs in the browser, which is where its cost is paid.

The following is measured in every engine `setup.sh` installs.

- The step is measured on a slide whose paragraph of about 500 or about 3000 letters
  reflows when a clause is inserted at its start, so that nearly every letter moves,
  and on a slide whose cetz plot of 1000 marks changes its axis range,
  so that every mark moves.
  The time is that of the key press, which plans and applies the whole step in one task,
  and the frames that follow say whether the browser keeps up with the animations it was
  given.
- The diff is `commonSubsequence` from `src/js/morph.js`, run on two lists of 3000 glyph
  names that differ in a growing number of places.
  The bound `MORPH_DIFFERENCES` is read from this measurement.
- The alignment is `alignPaths` from `src/js/paths.js`, run on two closed paths of 100 and
  of 1000 segments each.
  This is what a shape morph adds to the step for each pair it carries.

The result is printed, and written as JSON when `--output` names a file.
"""

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(HERE))
from harness.typst import compile_typst  # noqa: E402
from run import environment  # noqa: E402

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".venv" / "playwright"))
from playwright.sync_api import sync_playwright  # noqa: E402

WORK = ROOT / "tmp" / "benchmarks"

# The slide, with a paragraph of `words` words of the `lorem` placeholder text of typst,
# which is the same on every machine, and a clause inserted at its start by a morph.
DECK = """\
#import "@preview/animo:0.1.1": *
#show: animo
#slide(animation: {{
  import anim: *
  sub(replace("ins", transition: morph())[An inserted clause shifts all that follows.])
}})[
  #set text(size: {size}pt)
  #set par(justify: true)
  #region[#tag("ins", wrap: none)[] #lorem({words})]
]
"""

# The paragraphs measured, as a name, a number of words and a text size that keeps the
# paragraph on the slide.
PARAGRAPHS = {"500 letters": (80, 11), "3000 letters": (480, 4.5)}

# The slide with a plot of 1000 equal marks at places spread by two modular sequences, whose
# axis range grows by a quarter, which moves every mark towards the origin.
PLOT = """\
#import "@preview/animo:0.1.1": *
#import "@preview/cetz:0.5.2"
#show: animo
#let marks(range) = cetz.canvas({
  import cetz.draw: *
  line((0, 0), (10, 0))
  line((0, 0), (0, 6))
  for i in array.range(1000) {
    let x = calc.rem(i * 37, 1000) / 1000
    let y = calc.rem(i * 61 + 17, 997) / 997
    circle((x * 10 / range, y * 6 / range), radius: 0.04, fill: blue, stroke: none)
  }
})
#slide(animation: {
  import anim: *
  sub(replace("plot", transition: morph())[#marks(1.25)])
})[
  #region[#tag("plot")[#marks(1)]]
]
"""

# Plan and apply the step, as a key press does, and report how long it took, how many
# animations it started, and the intervals of the frames drawn during the 400 ms after it.
STEP = """async () => {
    const start = performance.now();
    dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowRight"}));
    const took = performance.now() - start;
    const animations = document.getAnimations().length;
    const frames = [];
    let last = performance.now();
    while (performance.now() - start < took + 400) {
        await new Promise((done) => requestAnimationFrame(done));
        const now = performance.now();
        frames.push(now - last);
        last = now;
    }
    const count = (selector) => document.querySelectorAll(
        `[data-typst-label="animo-epoch-0"] ${selector}`).length;
    return {took, animations, frames, glyphs: count("use"), paths: count("path")};
}"""

# The diff alone, on two lists of `n` names in which `changes` of the first list's names are
# replaced at evenly spread places, which is two differences each, a deletion and an insertion.
DIFF = """([source, n, changes, repeat]) => {
    const commonSubsequence = new Function(`${source}; return commonSubsequence;`)();
    const a = Array.from({length: n}, (_, i) => `g${i % 53}`);
    const b = a.slice();
    for (let k = 0; k < changes; k++) {
        b[Math.floor((k + 0.5) * n / changes)] = `x${k}`;
    }
    const times = [];
    let found = null;
    for (let r = 0; r < repeat; r++) {
        const start = performance.now();
        found = commonSubsequence(a, b, 100000);
        times.push(performance.now() - start);
    }
    return {times, common: found.length};
}"""

CHANGES = (25, 50, 100, 200, 400, 800)

# The alignment alone, on a polygon of `n` corners on a wavy circle and a circle of `n` cubic
# Béziers turned against it, so that the two share no vertex and every segment is cut.
ALIGN = """([source, n, repeat]) => {
    const alignPaths = new Function(`${source}; return alignPaths;`)();
    const pair = (x, y) => `${x.toFixed(3)} ${y.toFixed(3)}`;
    const point = (angle, radius) =>
        pair(100 + radius * Math.cos(angle), 100 + radius * Math.sin(angle));
    const corners = Array.from({length: n}, (_, i) => {
        const angle = (2 * Math.PI * i) / n;
        return point(angle, 80 + 8 * Math.sin(7 * angle));
    });
    const lines = corners.slice(1).map((corner) => `L ${corner}`);
    const polygon = `M ${corners[0]} ${lines.join(" ")} Z`;
    const arcs = Array.from({length: n}, (_, i) => {
        const [from, to] = [i, i + 1].map((k) => (2 * Math.PI * (k + 0.37)) / n);
        const handle = (4 / 3) * Math.tan((to - from) / 4) * 60;
        const control = (angle, sign) => {
            const [x, y] = [100 + 60 * Math.cos(angle), 100 + 60 * Math.sin(angle)];
            return pair(x - sign * handle * Math.sin(angle), y + sign * handle * Math.cos(angle));
        };
        return `C ${control(from, 1)} ${control(to, -1)} ${point(to, 60)}`;
    });
    const circle = `M ${point((2 * Math.PI * 0.37) / n, 60)} ${arcs.join(" ")} Z`;
    const times = [];
    let found = null;
    for (let r = 0; r < repeat; r++) {
        const start = performance.now();
        found = alignPaths(polygon, circle);
        times.push(performance.now() - start);
    }
    return {times, segments: found[0].split("C").length - 1};
}"""

SEGMENTS = (100, 1000)


def main() -> None:
    """Measure, print, and write the result."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, help="where to write the result as JSON")
    parser.add_argument("--repeat", type=int, default=5, help="runs per measurement")
    parser.add_argument("--engine", action="append", help="limit to these engines")
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    sources = {
        name: (f"morph-{words}", DECK.format(words=words, size=size))
        for name, (words, size) in PARAGRAPHS.items()
    }
    sources["1000 marks"] = ("morph-plot", PLOT)
    decks = {}
    for name, (stem, text) in sources.items():
        source = WORK / f"{stem}.typ"
        source.write_text(text)
        target = source.with_suffix(".html")
        outcome = compile_typst(source, target, fmt="html", features=("html",))
        assert outcome.ok, outcome
        decks[name] = target
    script = (ROOT / "src" / "js" / "morph.js").read_text()
    paths = (ROOT / "src" / "js" / "paths.js").read_text()
    result = {"environment": environment(), "engines": {}}
    with sync_playwright() as playwright:
        for engine in args.engine or ("chromium", "firefox", "webkit"):
            try:
                browser = getattr(playwright, engine).launch()
            except Exception as exc:  # noqa: BLE001
                print(f"{engine}: cannot be launched here ({type(exc).__name__})")
                continue
            own = {"version": browser.version, "steps": {}, "diff": {}, "align": {}}
            for name, deck in decks.items():
                runs = []
                for _ in range(args.repeat):
                    page = browser.new_page(viewport={"width": 1280, "height": 720})
                    page.goto(deck.resolve().as_uri())
                    page.wait_for_function("() => document.documentElement.dataset.animo")
                    runs.append(page.evaluate(STEP))
                    page.close()
                frames = [frame for run in runs for frame in run["frames"][1:]]
                own["steps"][name] = {
                    "glyphs": runs[0]["glyphs"],
                    "paths": runs[0]["paths"],
                    "animations": runs[0]["animations"],
                    "step_ms": statistics.median(run["took"] for run in runs),
                    "frame_ms_median": statistics.median(frames),
                    "frame_ms_max": max(frames),
                }
                print(engine, name, own["steps"][name])
            page = browser.new_page()
            for changes in CHANGES:
                found = page.evaluate(DIFF, [script, 3000, changes, args.repeat])
                own["diff"][changes] = statistics.median(found["times"])
                took = own["diff"][changes]
                print(engine, f"diff of 3000 names, {2 * changes} differences: {took:.1f} ms")
            for segments in SEGMENTS:
                found = page.evaluate(ALIGN, [paths, segments, args.repeat])
                own["align"][segments] = statistics.median(found["times"])
                took = own["align"][segments]
                pieces = found["segments"]
                print(engine, f"alignment of {segments} segments into {pieces}: {took:.1f} ms")
            browser.close()
            result["engines"][engine] = own
    if args.output is not None:
        args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
