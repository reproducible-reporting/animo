#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Measure what an animo deck costs to compile and how much of a page it becomes.

Three decks are measured, for three different reasons.
`examples/tour.typ` is the realistic one: it says what an author of a real deck waits for.
`benchmarks/scaling.typ` is the controlled one: it holds everything constant except one
axis, so that a term of the cost model is the difference between two runs rather than a
guess about where the time went.
`benchmarks/placements.typ` is the one that grows with what the body draws: it says what
the automatic canvas of a slide full of `#place` calls costs, in seconds and in memory.

The result is written as JSON under `results/`, one file per machine, because a number
without a machine is not a measurement.
"""

import argparse
import gzip
import json
import os
import platform
import re
import shutil
import socket
import statistics
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable
from functools import partial
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# The compiler is invoked the way the test suite invokes it: the repository as the typst
# root, the repository-local package directory on `TYPST_PACKAGE_PATH`, and only the fonts
# typst embeds, which is what keeps a rendering identical between two machines.
sys.path.insert(0, str(ROOT / "tests"))
from harness.markup import drop_repeated_defs  # noqa: E402
from harness.typst import compile_typst  # noqa: E402

TOUR = ROOT / "examples" / "tour.typ"
SCALING = HERE / "scaling.typ"
PLACEMENTS = HERE / "placements.typ"

# A line of the tour that a live-preview measurement rewrites, with the round number left
# out, so that the edit is an edit of one slide's ink. The tour is free to change, unlike
# the controlled deck, so this may go missing: the measurement then falls back to appending
# a line, says so in what it records, and picking another line of the tour repairs it.
TOUR_EDIT = "= Disclaimers{}"

# Where the compiled artefacts go. They are measured and thrown away, so they belong in
# the scratch tree rather than beside the recorded numbers.
WORK = ROOT / "tmp" / "benchmarks"

OUTPUTS = {
    "html": {"fmt": "html", "features": ("html",), "sysinp": {}},
    "presentation": {"fmt": "pdf", "features": (), "sysinp": {"animo": "presentation"}},
    "handout": {"fmt": "pdf", "features": (), "sysinp": {}},
}
"""The three output types, as the arguments that select each of them."""

VARIANTS = {
    "base": {},
    "states-4": {"states": "4"},
    "epochs-2": {"epochs": "2"},
    "epochs-4": {"epochs": "4"},
    "epochs-8": {"epochs": "8"},
    "regions-2-epochs-1": {"regions": "2"},
    "regions-2-epochs-4": {"regions": "2", "epochs": "4"},
    "regions-2-epochs-4-sized": {"regions": "2", "epochs": "4", "height": "3cm"},
    "figure-regions-2-epochs-1": {"figure": "on", "regions": "2"},
    "figure-regions-2-epochs-4": {"figure": "on", "regions": "2", "epochs": "4"},
    "figure-regions-2-epochs-4-sized": {
        "figure": "on",
        "regions": "2",
        "epochs": "4",
        "height": "3cm",
    },
    "overlay": {"overlay": "on"},
    "overlay-epochs-4": {"overlay": "on", "epochs": "4"},
    "overlay-states-4-epochs-3": {"overlay": "on", "states": "4", "epochs": "3"},
    "number": {"overlay": "on", "number": "on"},
    "number-states-4": {"overlay": "on", "number": "on", "states": "4"},
    "number-states-4-epochs-3": {
        "overlay": "on",
        "number": "on",
        "states": "4",
        "epochs": "3",
    },
    "realistic": {"states": "4", "epochs": "3", "regions": "2"},
}
"""The points of the controlled deck that are measured, each a set of `--input` knobs.

Every one of them is also compiled with `plain=on`, which is the same content laid out by
typst with animo out of the way, so that every variant carries its own floor.

The two variants at `states-4-epochs-3` are a pair: they differ in the `number` knob alone,
at a point where a deck really has several subslides and several epochs, which is what makes
their difference the cost of a number rather than the cost of a layer.
"""

PLACEMENT_VARIANTS = {
    "no-pan": {},
    "pan": {"pan": "on"},
    "pan-canvas": {"pan": "on", "canvas": "stated"},
    "pan-image": {"pan": "on", "marks": "image"},
}
"""The four shapes of the placement deck, each a set of `--input` knobs.

The first two differ in whether the timeline pans, which is what makes animo compute the
canvas, and the last two are the two ways out of that cost: a canvas that is stated, and
the same marks drawn as one element instead of one each.
"""

PLACEMENT_POINTS = 10000
"""Marks on the slide of the placement deck.

It is a scatter plot of a size an author really writes, and large enough that the union of
the placements is a term of the compile time rather than noise in it.
"""

PLACEMENT_STATES = 20
"""States of that one slide, which is what the static presentation renders a page each of."""

# What an epoch sweep is fitted over. These are the variants that differ in `epochs` and in
# nothing else, which is what makes the difference between them a per-epoch cost.
EPOCH_SWEEP = ("base", "epochs-2", "epochs-4", "epochs-8")


def run_timed(once: Callable[[], object], repeat: int) -> dict:
    """Time a call, discarding a warm-up run, and report the spread.

    Parameters
    ----------
    once
        Performs one run, and raises when it fails.
    repeat
        How many timed runs to take after the warm-up.

    Returns
    -------
    timing
        The minimum, the median and every sample, in seconds.
        The minimum is the number to compare across machines: it is the run least disturbed
        by whatever else the machine was doing.
    """
    samples = []
    for i in range(repeat + 1):
        start = time.perf_counter()
        once()
        elapsed = time.perf_counter() - start
        if i > 0:
            samples.append(elapsed)
    return {
        "min": round(min(samples), 4),
        "median": round(statistics.median(samples), 4),
        "samples": [round(s, 4) for s in samples],
    }


def compile_once(source: Path, output: Path, kind: str, inputs: dict[str, str]):
    """Compile one deck to one output type, through the harness, and fail loudly."""
    spec = OUTPUTS[kind]
    return compile_typst(
        source,
        output,
        fmt=spec["fmt"],
        features=spec["features"],
        sysinp={**spec["sysinp"], **inputs},
    ).check()


CANVAS = re.compile(r'<div class="animo-canvas".*?</div>', re.S)
"""The frame of one slide, the element its epoch renderings are laid out in.

The canvas element holds nothing but that frame, so the first `</div>` after it is its own.
"""

EPOCH = re.compile(r'data-typst-label="animo-epoch-\d+"')
"""One epoch rendering of a slide, which is a labelled group inside the slide's frame."""


def defs_share(markup: str) -> dict:
    """How much of an HTML page is definitions, how much repeats, and what dropping it saves.

    Typst's def ids are content hashes, so an id that occurs in two frames is the same
    definition twice, and a browser resolves `<use>` to the first match in the document.
    The repetition is therefore pure redundancy, and two of the numbers below are what
    removing it in two different scopes would leave.

    The pages are built here and gzipped, because that is the only honest way to answer
    whether gzip is enough: a deck is served compressed, so what a saving is worth is the
    difference between two *compressed* sizes and not between two raw ones. Dropping the
    repeats rather than moving them to a document-level `<svg>` gives the same byte count
    and needs no shell to be written.

    `hoisted_*` is every repeat in the document dropped, which no compile of one source
    file can reach: a package never holds the markup a frame became (see *Findings*).
    `merged_*` is the reachable scope, the repeats inside one slide's canvas. Animo lays
    the epoch renderings of a slide out in one frame, so typst's own deduplicator has
    already removed them and this reads back as the page itself; it is kept because a
    number that stops moving is what says the scope is exhausted.

    Returns
    -------
    share
        The page size, the bytes inside `<defs>`, the bytes of the definitions whose id had
        already been seen, and the size of the two deduplicated pages, raw and gzipped.
    """
    hoisted, weights = drop_repeated_defs(markup)
    merged = CANVAS.sub(lambda block: drop_repeated_defs(block.group(0))[0], markup)
    return {
        "page_bytes": len(markup.encode()),
        **weights,
        "hoisted_bytes": len(hoisted.encode()),
        "hoisted_gzip_bytes": len(gzip.compress(hoisted.encode(), 9)),
        "merged_bytes": len(merged.encode()),
        "merged_gzip_bytes": len(gzip.compress(merged.encode(), 9)),
    }


def structure(markup: str) -> dict:
    """The rendering counts of an HTML deck, read back out of the page it produced.

    This is the cost model itself: one rendering per epoch, and the states the plan
    carries. It depends on the deck and not on the machine, which is why the test suite
    asserts it and this file only records it.

    An epoch rendering is a labelled group inside the slide's canvas element, and every
    rendering of a slide sits in the one frame there. Counting the labels rather than the
    frames is what keeps this a reading of the cost model rather than of the markup the
    renderings happen to be written in.
    """
    slides = re.findall(r'data-animo-slide="(\d+)" data-animo-states="(\d+)"', markup)
    epochs = [len(EPOCH.findall(block)) for block in CANVAS.findall(markup)]
    return {
        "slides": len(slides),
        "states": sum(int(states) for _, states in slides),
        "epochs": sum(epochs),
    }


def measure_outputs(source: Path, stem: str, inputs: dict[str, str], kinds, repeat: int) -> dict:
    """Compile one deck to several output types and record the time and the size of each."""
    WORK.mkdir(parents=True, exist_ok=True)
    measured = {}
    for kind in kinds:
        suffix = ".html" if kind == "html" else ".pdf"
        output = WORK / f"{stem}-{kind}{suffix}"
        entry = run_timed(partial(compile_once, source, output, kind, inputs), repeat)
        entry["bytes"] = output.stat().st_size
        if kind == "html":
            markup = output.read_text()
            entry["gzip_bytes"] = len(gzip.compress(markup.encode(), 9))
            entry.update(structure(markup))
            entry.update(defs_share(markup))
        measured[kind] = entry
    return measured


def compile_rusage(source: Path, output: Path, kind: str, inputs: dict[str, str]) -> int:
    """Compile one deck the way `compile_typst` does, and report the compiler's peak memory.

    The compiler is run here rather than through the harness because the harness reports
    what typst wrote and not what the process used, and peak memory is half of what a
    placement-heavy slide costs.
    The flags are the harness's own: the repository as the typst root, the repository-local
    package directory on `TYPST_PACKAGE_PATH`, and only the fonts typst embeds.

    Returns
    -------
    maxrss
        The peak resident set size of the compiler, in kibibytes, which is the unit linux
        reports it in.
    """
    spec = OUTPUTS[kind]
    argv = ["typst", "compile", "--root", str(ROOT), "--ignore-system-fonts"]
    argv += ["--format", spec["fmt"]]
    for feature in spec["features"]:
        argv += ["--features", feature]
    for key, value in {**spec["sysinp"], **inputs}.items():
        argv += ["--input", f"{key}={value}"]
    argv += [str(source), str(output)]

    env = dict(os.environ)
    env["TYPST_PACKAGE_PATH"] = str(ROOT / ".typst-packages")
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)
    stderr = proc.stderr.read().decode(errors="replace")
    # `wait4` reports the resource usage of this child alone, where `getrusage` would report
    # the largest of every compile the run has made so far.
    _, status, usage = os.wait4(proc.pid, 0)
    proc.returncode = os.waitstatus_to_exitcode(status)
    proc.stderr.close()
    if proc.returncode != 0:
        raise AssertionError(f"typst compile failed with {proc.returncode}:\n{stderr}")
    return usage.ru_maxrss


def measure_placements(repeat: int) -> dict:
    """What a slide of many placed marks costs, in seconds and in peak memory.

    The static presentation is the output measured, so that every state of the slide is
    rendered and the cost is the one an author pays for the whole slide.
    """

    def sample(peaks: list[int], output: Path, knobs: dict[str, str]) -> None:
        """Compile once and keep the peak memory, so that `run_timed` times the call."""
        peaks.append(compile_rusage(PLACEMENTS, output, "presentation", knobs))

    WORK.mkdir(parents=True, exist_ok=True)
    measured = {}
    for name, inputs in PLACEMENT_VARIANTS.items():
        knobs = {"points": str(PLACEMENT_POINTS), "states": str(PLACEMENT_STATES), **inputs}
        output = WORK / f"placements-{name}.pdf"
        peaks: list[int] = []
        entry = run_timed(partial(sample, peaks, output, knobs), repeat)
        # The first peak belongs to the warm-up run that `run_timed` discards.
        entry["peak_kib"] = max(peaks[1:])
        entry["bytes"] = output.stat().st_size
        measured[name] = entry
    return measured


COMPILED = re.compile(r"compiled (?:with warnings )?in ([0-9.]+)\s*(ms|s)\b")
FAILED = re.compile(r"compiled with errors\b")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def measure_watch(
    source: Path,
    name: str,
    template: str | None,
    rounds: int,
    inputs: dict[str, str] | None = None,
) -> dict:
    """How long `typst watch` takes to recompile after an edit, which is the authoring loop.

    A release build is compiled once; a deck being written is recompiled after every
    keystroke that lands, and typst memoises across recompiles inside one `watch` process.
    So the cold compile time is the wrong number for authorability and this is the right one.

    Parameters
    ----------
    source
        The deck to watch. It is copied into the scratch tree first, because the edits are
        real edits and must not touch the working tree.
    name
        A name for the copy, which is also what the reported entry is keyed by.
    template
        A line of the deck with the round number left out, such as `'#let x = "{}"'`.
        The deck has to hold that line with a zero in it, and every round rewrites it with
        the round's own number, so that every edit is a different edit and a real one.
        `None` appends a line instead, which changes the source without changing anything
        the document lays out, and so measures the floor rather than an edit.
    rounds
        How many edits to make. The first compile is the cold one and is reported apart.
    inputs
        The knobs the deck is watched with, so that the loop is measured on the same deck
        the cold compiles were measured on.

    Returns
    -------
    timing
        The cold compile, the incremental recompiles, and which kind of edit was made.
    """
    work = WORK / "watch" / name
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    deck = work / "deck.typ"
    deck.write_text(source.read_text())

    env = dict(os.environ)
    env["TYPST_PACKAGE_PATH"] = str(ROOT / ".typst-packages")
    argv = [
        "typst", "watch", "--root", str(ROOT), "--ignore-system-fonts",
        "--no-serve", "--features", "html", "--format", "html",
    ]  # fmt: skip
    for key, value in (inputs or {}).items():
        argv += ["--input", f"{key}={value}"]
    argv += [str(deck), str(work / "deck.html")]
    proc = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True, bufsize=1
    )
    # Round zero is the deck as it is written, so its marker is the template with
    # nothing in the slot, and every later round puts its own number there.
    marker = None if template is None else template.format("")
    if marker is not None and marker not in deck.read_text():
        print(
            f"{source.name} no longer holds {marker!r}; measuring an append instead",
            file=sys.stderr,
        )
        marker, template = None, None
    try:
        seconds = []
        for round_ in range(rounds + 1):
            if round_ > 0:
                # The edit has to arrive after the previous compile is reported, or the
                # watcher coalesces the two and the measurement times both at once.
                time.sleep(0.3)
                text = deck.read_text()
                if marker is None:
                    deck.write_text(f"{text}\n// edit {round_}\n")
                else:
                    edited = text.replace(marker, template.format(round_), 1)
                    if edited == text:
                        raise RuntimeError(f"{source.name} no longer holds {marker!r} to edit")
                    deck.write_text(edited)
                    marker = template.format(round_)
            seconds.append(await_compile(proc))
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    return {
        "edit": "append" if template is None else "one-slide",
        "cold": round(seconds[0], 4),
        "incremental_min": round(min(seconds[1:]), 4),
        "incremental_median": round(statistics.median(seconds[1:]), 4),
        "incremental_samples": [round(s, 4) for s in seconds[1:]],
    }


def await_compile(proc: subprocess.Popen, timeout: float = 120.0) -> float:
    """Read the watcher's output until it reports a compile, and return how long it took.

    The time comes from typst rather than from a clock here, because only typst knows when
    it noticed the edit, and the delay between writing a file and the watcher waking up is
    not part of what is being measured.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if line == "":
            raise RuntimeError("typst watch stopped before reporting a compile")
        clean = ANSI.sub("", line)
        if FAILED.search(clean):
            # An edit that does not compile is a broken measurement, and waiting out the
            # timeout for a compile that will never be reported hides which edit broke it.
            raise RuntimeError(f"typst watch reported a failed compile: {clean.strip()}")
        match = COMPILED.search(clean)
        if match is not None:
            value = float(match.group(1))
            return value / 1000 if match.group(2) == "ms" else value
    raise RuntimeError("typst watch did not report a compile in time")


def slope(points: list[tuple[float, float]]) -> float:
    """The least-squares slope of `y` against `x`, which is what a per-epoch cost is."""
    n = len(points)
    mx = sum(x for x, _ in points) / n
    my = sum(y for _, y in points) / n
    num = sum((x - mx) * (y - my) for x, y in points)
    den = sum((x - mx) ** 2 for x, _ in points)
    return num / den


def knob(name: str, key: str, default: str) -> int:
    """One knob of a variant, as a number."""
    return int(VARIANTS[name].get(key, default))


def measurements(name: str, slides: int) -> int:
    """How often a region lays its body out to measure it, over one rendering of every slide.

    A region measures once per epoch, and two things take that cost away: a height that is
    given, since there is then nothing to choose between, and a slide with one epoch, whose
    only rendering takes the height it takes. Regions nest as footprints rather than as
    states, so this is a product and never a power.

    The handout is the output this divides, because it renders every slide exactly once
    whatever its epochs, so the count is the whole of what the two variants differ in.
    """
    if "height" in VARIANTS[name] or knob(name, "epochs", "1") == 1:
        return 0
    return slides * knob(name, "regions", "0") * knob(name, "epochs", "1")


def derive(scaling: dict) -> dict:
    """The numbers the open questions are answered with, computed from the raw ones.

    Every one of them is a difference or a slope between variants that differ in one knob,
    so each says what that knob costs and nothing else. The divisors come from the knobs
    rather than from a count written out here, so a variant that is retuned cannot leave a
    stale one behind.
    """
    slides = scaling["base"]["html"]["slides"]

    def sweep(field: str) -> list[tuple[float, float]]:
        return [(knob(n, "epochs", "1"), scaling[n]["html"][field]) for n in EPOCH_SWEEP]

    def per_measurement(measuring: str, given: str) -> float:
        """What one region measuring one epoch costs, as the difference the height makes.

        The handout is what this is read off: it renders one page per slide whatever the
        epochs, so the two variants differ in their measuring and not in how many times the
        slide itself is laid out.
        """
        delta = scaling[measuring]["handout"]["min"] - scaling[given]["handout"]["min"]
        return delta / (measurements(measuring, slides) - measurements(given, slides))

    return {
        "overhead_factor": {
            name: round(entry["handout"]["min"] / entry["plain"]["min"], 2)
            for name, entry in scaling.items()
        },
        # The sweep holds `regions` at zero, so the changing tag is its own implicit region
        # and one more epoch is one more frame plus one more measurement of that region.
        "seconds_per_epoch_per_slide": round(slope(sweep("min")) / slides, 4),
        "seconds_per_region_measurement": round(
            per_measurement("regions-2-epochs-4", "regions-2-epochs-4-sized"), 5
        ),
        "seconds_per_canvas_measurement": round(
            per_measurement("figure-regions-2-epochs-4", "figure-regions-2-epochs-4-sized"), 5
        ),
        "bytes_per_epoch_per_slide": round(slope(sweep("bytes")) / slides),
        "gzip_bytes_per_epoch_per_slide": round(slope(sweep("gzip_bytes")) / slides),
        "gzip_ratio": {
            name: round(entry["html"]["bytes"] / entry["html"]["gzip_bytes"], 2)
            for name, entry in scaling.items()
        },
        # What hoisting the shared definitions would save on the wire, which is the
        # question gzip is asked to answer. A ratio that stays flat as the epochs multiply
        # is gzip failing to reach the duplication rather than there being none.
        "hoisting_saves_gzipped": {
            name: round(1 - entry["html"]["hoisted_gzip_bytes"] / entry["html"]["gzip_bytes"], 3)
            for name, entry in scaling.items()
        },
        # And how much is left inside one slide's frame, which is the scope animo already
        # exhausts by laying every epoch rendering of a slide out in one of them. It reads
        # as nothing, and a reading that is not nothing is a slide whose renderings ended
        # up in frames of their own again.
        "merging_saves_gzipped": {
            name: round(1 - entry["html"]["merged_gzip_bytes"] / entry["html"]["gzip_bytes"], 3)
            for name, entry in scaling.items()
        },
    }


def typst_build(binary: Path) -> str:
    """Which build of the release the compiler on `PATH` is.

    Typst publishes a static musl binary for linux and nothing linked against glibc,
    and a glibc build of the same release compiles the benchmark decks
    1.2 to 2.4 times faster,
    so the release alone does not say what a recorded second was measured on.

    Parameters
    ----------
    binary
        The compiler that was run, as `shutil.which` resolved it.

    Returns
    -------
    build
        The libc the binary is linked against, with its version where there is one.
    """
    libc, version = platform.libc_ver(executable=str(binary))
    if libc:
        return f"{libc} {version}".strip()
    if b"-linux-musl" in binary.read_bytes():
        return "musl"
    return "unknown"


def environment() -> dict:
    """What the numbers were measured on, which is half of what a measurement is."""
    cpu = platform.processor()
    model = Path("/proc/cpuinfo")
    if model.is_file():
        for line in model.read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    with open(ROOT / "typst.toml", "rb") as fh:
        package = tomllib.load(fh)["package"]
    typst = subprocess.run(["typst", "--version"], capture_output=True, text=True, check=True)
    binary = Path(shutil.which("typst"))
    commit = subprocess.run(
        ["git", "-C", str(ROOT), "describe", "--always", "--dirty"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "host": socket.gethostname(),
        "cpu": cpu,
        "cores": os.cpu_count(),
        "platform": platform.platform(),
        "typst": typst.stdout.strip(),
        "typst_libc": typst_build(binary),
        "animo": package["version"],
        "commit": commit.stdout.strip() or "unknown",
        "measured": time.strftime("%Y-%m-%d %H:%M:%S%z"),
    }


def main():
    """Measure both decks and write the result."""
    args = parse_args()
    result = {
        "environment": environment(),
        "settings": {
            "repeat": args.repeat,
            "placement_points": PLACEMENT_POINTS,
            "placement_states": PLACEMENT_STATES,
        },
    }

    tour = measure_outputs(TOUR, "tour", {}, OUTPUTS, args.repeat)
    tour["watch"] = measure_watch(TOUR, "tour", TOUR_EDIT, args.watch_rounds)
    result["tour"] = tour

    scaling = {}
    for name, inputs in VARIANTS.items():
        entry = measure_outputs(SCALING, name, inputs, OUTPUTS, args.repeat)
        floor = measure_outputs(
            SCALING, f"{name}-plain", {**inputs, "plain": "on"}, ("handout",), args.repeat
        )
        entry["plain"] = floor["handout"]
        scaling[name] = entry
    scaling["realistic"]["watch"] = measure_watch(
        SCALING,
        "realistic",
        '#let revision = "{}"',
        args.watch_rounds,
        VARIANTS["realistic"],
    )
    result["scaling"] = scaling
    result["derived"] = derive(scaling)
    result["placements"] = measure_placements(args.repeat)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(summary(result))


def summary(result: dict) -> str:
    """A short human-readable account of a result, for the terminal and for a session log."""
    lines = [
        f"{result['environment']['cpu']}, {result['environment']['typst']} "
        f"linked against {result['environment']['typst_libc']}",
        "",
    ]
    tour = result["tour"]
    lines.append(
        f"tour.typ: {tour['html']['slides']} slides, {tour['html']['states']} states, "
        f"{tour['html']['epochs']} epochs"
    )
    for kind in OUTPUTS:
        entry = tour[kind]
        size = f", {entry['bytes'] / 1e6:.2f} MB" if kind == "html" else ""
        gzip_size = f" ({entry['gzip_bytes'] / 1e6:.2f} MB gzipped)" if kind == "html" else ""
        lines.append(f"  {kind:<13} {entry['min']:6.2f} s{size}{gzip_size}")
    lines.append(
        f"  watch          {tour['watch']['incremental_median'] * 1000:6.0f} ms per edit "
        f"({tour['watch']['edit']}), {tour['watch']['cold']:.2f} s cold"
    )
    lines += ["", f"{'variant':<28}{'html':>8}{'pres':>8}{'hand':>8}{'plain':>8}{'factor':>8}"]
    for name, entry in result["scaling"].items():
        lines.append(
            f"{name:<28}{entry['html']['min']:8.2f}{entry['presentation']['min']:8.2f}"
            f"{entry['handout']['min']:8.2f}{entry['plain']['min']:8.2f}"
            f"{result['derived']['overhead_factor'][name]:8.1f}"
        )
    lines += [
        "",
        f"placements: {PLACEMENT_POINTS} marks over {PLACEMENT_STATES} states, "
        "as a static presentation",
    ]
    for name, entry in result["placements"].items():
        lines.append(f"  {name:<26}{entry['min']:8.2f} s{entry['peak_kib'] / 1024:8.0f} MB")

    derived = result["derived"]
    lines += [
        "",
        f"per epoch, per slide: {derived['seconds_per_epoch_per_slide'] * 1000:.0f} ms, "
        f"{derived['bytes_per_epoch_per_slide'] / 1024:.0f} KiB "
        f"({derived['gzip_bytes_per_epoch_per_slide'] / 1024:.0f} KiB gzipped)",
        f"per region measurement: {derived['seconds_per_region_measurement'] * 1000:.1f} ms "
        f"of prose, {derived['seconds_per_canvas_measurement'] * 1000:.1f} ms of cetz canvas",
        f"gzip: {tour['html']['bytes'] / tour['html']['gzip_bytes']:.1f}x on the tour, "
        f"leaving {1 - tour['html']['hoisted_gzip_bytes'] / tour['html']['gzip_bytes']:.0%} "
        "that hoisting the shared defs would still save, "
        f"{1 - tour['html']['merged_gzip_bytes'] / tour['html']['gzip_bytes']:.0%} of it "
        "within one slide",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "results" / f"{socket.gethostname()}.json",
        help="where the measurement is written; defaults to results/<host>.json",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=5,
        help="timed runs per measurement, after a warm-up run that is discarded",
    )
    parser.add_argument(
        "--watch-rounds",
        type=int,
        default=5,
        help="edits to make in the live-preview measurement",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
