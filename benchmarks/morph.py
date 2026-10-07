#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Measure what a morph costs in the browser, which is where its cost is paid.

Two things are measured, in every engine `setup.sh` installs.
The step: a slide whose paragraph of about 500 or about 3000 letters reflows when a clause
is inserted at its start, so that nearly every letter moves. The time is that of the key
press, which plans and applies the whole step in one task, and the frames that follow say
whether the browser keeps up with the animations it was given.
The diff: `commonSubsequence` from `src/js/morph.js` on two lists of 3000 glyph names that
differ in a growing number of places, which is what the bound `MORPH_DIFFERENCES` is read
from.

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

# The slide, with a paragraph of `words` words of typst's own placeholder text, which is the
# same on every machine, and a clause inserted at its start by a morph.
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
    const glyphs = document.querySelectorAll(
        '[data-typst-label="animo-epoch-0"] use').length;
    return {took, animations, frames, glyphs};
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


def main() -> None:
    """Measure, print, and write the result."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, help="where to write the result as JSON")
    parser.add_argument("--repeat", type=int, default=5, help="runs per measurement")
    parser.add_argument("--engine", action="append", help="limit to these engines")
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    decks = {}
    for name, (words, size) in PARAGRAPHS.items():
        source = WORK / f"morph-{words}.typ"
        source.write_text(DECK.format(words=words, size=size))
        target = source.with_suffix(".html")
        outcome = compile_typst(source, target, fmt="html", features=("html",))
        assert outcome.ok, outcome
        decks[name] = target
    script = (ROOT / "src" / "js" / "morph.js").read_text()
    result = {"environment": environment(), "engines": {}}
    with sync_playwright() as playwright:
        for engine in args.engine or ("chromium", "firefox", "webkit"):
            try:
                browser = getattr(playwright, engine).launch()
            except Exception as exc:  # noqa: BLE001
                print(f"{engine}: cannot be launched here ({type(exc).__name__})")
                continue
            own = {"version": browser.version, "steps": {}, "diff": {}}
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
            browser.close()
            result["engines"][engine] = own
    if args.output is not None:
        args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
