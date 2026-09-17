<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Benchmarks

What an Animo deck costs to compile, and how much of a web page it becomes.

Animo exists partly because the packages it means to replace are slow,
so the claim that Animo is faster has to be supported by measurements.
The numbers this directory produces are quoted in
[docs/performance.md](../docs/performance.md).

## Running It

```bash
./benchmarks/run.py --output benchmarks/results/$(hostname).json
```

It is intentionally a script rather than a build target.
It takes a few minutes and writes a different file every time,
because seconds are not reproducible,
so a target that ran by default would leave the working tree dirty after every build.
In addition, `src/` is one of its inputs, so a target that ran by default would run during
ordinary work on the package and record numbers taken while something else had the machine.
A measurement is only meaningful when it is requested explicitly, on an otherwise idle machine.

While changing the script itself, a shorter run into a scratch file is what to use:

```bash
./benchmarks/run.py --repeat 3 --output tmp/try.json
```

## What Is Measured

Three decks are measured, for three different reasons.

[`examples/tour.typ`](../examples/tour.typ) is the **realistic** one.
It is the deck the manual embeds, so it says what an author of a real deck waits for,
and it is the only deck here whose content is free to change.

[`scaling.typ`](scaling.typ) is the **controlled** one.
It holds everything constant except one axis at a time,
so that a term of the cost model is the difference between two runs
rather than a guess about where the time went:

| Difference                                                | Isolates                                      |
| --------------------------------------------------------- | --------------------------------------------- |
| a variant against its own `plain=on` run                  | what Animo's machinery costs over plain typst |
| the slope over `base`, `epochs-2`, `epochs-4`, `epochs-8` | one epoch, in seconds and in bytes            |
| `regions-2-epochs-4` minus the same run `-sized`          | one region measuring one epoch of prose       |
| `figure-regions-2-epochs-4` minus the same run `-sized`   | one region measuring one epoch of cetz canvas |
| `number-states-4-epochs-3` minus the same run without it  | a subslide number, where a deck has subslides |

Both measuring terms are read off the **handout**, which renders every slide exactly once
whatever its epochs, so the two runs of a pair differ in their measuring and not in how many
times the slide itself is laid out.
A region with a given `height` measures nothing, which is what the `-sized` half of each pair
is for, and the divisors come from the knobs rather than from a count written out by hand.

`scaling.typ` is meant to stay as it is.
A number measured on it is comparable only when the deck it was measured on is unchanged,
so the tour deck covers realism and this one covers stability.

Each variant is also compiled with `plain=on`,
which lays the same content out with Animo out of the way:
`tag` and `region` become the plainest containers that hold the same ink,
and the timeline is not built at all.
The content itself is written once, as a function of those two containers,
so the Animo run and the plain run cannot drift apart.

[`placements.typ`](placements.typ) is the one that **grows with what the body draws**.
The canvas of a slide is the union of its body and of every `#place`d element on it,
and Animo computes that union only on a slide whose timeline pans.
The deck is one slide of ten thousand marks over twenty states,
in the four shapes that say what the union costs and what avoids it:

| Variant      | Differs in                                                                   |
| ------------ | ---------------------------------------------------------------------------- |
| `no-pan`     | the timeline moves a tag rather than the viewport                            |
| `pan`        | the timeline pans, which is what reads the canvas                            |
| `pan-canvas` | the slide states its `canvas:`, leaving nothing to be summed                 |
| `pan-image`  | the same marks are drawn as one SVG element rather than as one `#place` each |

It is measured as a static presentation, which renders every state,
and it is the one deck whose **peak memory** is recorded beside its seconds.
The compiler is run directly rather than through the test harness there,
because the harness reports what typst wrote and not what the process used.

Beside the cold compiles, the script measures the **live preview loop**:
how long `typst watch` takes to recompile after an edit.
A release build is compiled once, while a deck being written is recompiled
after every edit that lands, and typst memoises across recompiles inside one `watch`
process, so the cold compile time does not describe what writing a deck feels like.

## The Results

One JSON file per machine under `results/`, committed.
A number is only interpretable together with the machine it was measured on,
so each file records the CPU, the core count, the platform,
the typst release, the Animo version and the commit it was measured at.

The rendering counts the seconds are divided by are *not* recorded as a claim here.
They follow from the timeline alone and are the same on every machine,
so they are asserted in `tests/test_cost_model.py` instead,
which is also what compiles the decks in this directory
so that a change to the package fails in the test suite
rather than only when somebody next runs the benchmarks.
