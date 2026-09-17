---
description: >-
  What a behaviour probe is, why it is separate from a feature test,
  how to add one when a new finding is measured,
  and which finding each probe module asserts.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Behaviour Probes

Animo rests on some twenty verified behaviours of typst 0.15.1 and of the browsers it
targets. They are recorded in *Findings*, the document beside the design that
[Developing Animo](development.md) points at, and any of them could change under the
package.

A **probe** asserts such a behaviour itself, rather than a feature that happens to depend on it.
The difference is what a failure says.
When typst 0.16 lands and `data-typst-label` stops being emitted for labelled blocks,
a feature test says that reveal animations are broken;
a probe says that the emission rule changed.
The first leads to debugging Animo, the second to the release notes.

So a probe:

- asserts one entry of *Findings*, and names that entry in its module docstring;
- is **independent of every Animo feature**, and imports nothing from `src/`;
- states, where the claim is a comparison, why the comparison is not vacuous,
  which is a probe of its own often enough to be worth the habit.

Probes live in `probes/` and run in the same three tiers as the feature tests,
through the same fixtures. See [Testing](testing.md) for the tiers.

```bash
pytest probes             # all of them, against the pinned typst
pytest probes -m browser  # the ones that need a browser, in every engine available
```

They also run in a workflow of their own, weekly, against the **newest** typst release.
That job is non-blocking for pull requests and reports into the run summary.

## When a Probe Fails

A failing probe indicates that a documented behaviour of typst or a browser has changed,
which is what the weekly job is meant to detect.
It is never fixed by relaxing the probe.

1. Decide whether the finding was wrong when it was written,
   or whether it has legitimately changed in a newer release.
1. Edit the entry in *Findings* to say what now holds,
   and say on which release it was observed.
   A finding is a point-in-time claim, and it is written as one.
1. Update the probe in the same commit, or retire it when the behaviour it guarded is gone.
   A retired probe is deleted together with its finding, not left skipped.
1. Check what else rested on it.
   Every entry in *Findings* supports some part of the design,
   and the design document says which part.

## Adding a Probe

A new finding arises whenever work on the design or the implementation
meets a behaviour of typst or of a browser that *Findings* does not already record.
Turning one into a probe is the same four steps every time.

1. Add the finding to *Findings*,
   with the numbers and the release it was observed on.
1. Write the probe in the module that covers that part of the design,
   or a new `probes/test_<topic>.py` when it is a new topic.
   The module docstring names the finding; the test docstring says what would break without it.
1. Build the mechanism by hand, without Animo.
   A probe for the region footprint rule writes `layout` and `measure` itself,
   so that a failure cannot be an Animo bug.
1. Add the row to the table below.

Two rules of thumb are worth stating.
Prefer an assertion inside the document (`#assert`) over one in Python,
because it fails where the behaviour is.
Also prefer a cross-check within one run over a hardcoded number:
the probe for `measure` agreeing between the two targets takes the number out of the HTML
compilation and hands it to the paged one through `--input`,
so a change in font metrics cannot make it pass for the wrong reason.

## An Engine Answer Comes From That Engine

Several probes tabulate an answer per engine, because the three do not always agree.
Every entry of such a table has to come from a run in the engine it names.
An entry carried over from another table, or from another engine, states an assumption
in the shape of a measurement, and the probe then passes without asserting anything.
A per-engine allowance that no run produced is the one way a browser probe can be green
while the behaviour it guards is absent.

Webkit is where this matters. Chromium and firefox run wherever playwright runs, and webkit
needs a container outside macOS and the debian family, so it is the engine a table is
tempted to fill in from elsewhere. See [Development Environment](environment.md) for which
engines run where, and measure in webkit before a table gains a webkit entry:

```bash
pytest --browser webkit
```

Until that measurement exists, the probe says so in the table and asserts only what it has
grounds for. Accepting either of two answers from an engine, and naming the answer for the
engines that were measured, is a claim; an invented number is not.

## Findings That Cannot Be Probed

Some entries are not observable behaviour, and they are recorded as such rather than faked.

- **The single `data-typst-label` emission site in `typst-svg`.**
  A fact about the source tree rather than about the binary.
  Its consequence is probed instead:
  a label on a `rect` or on a text span emits nothing.
- **The stability history of the attribute**, its pull request and changelog entry.
  A fact about the project's history.
- **Autoplay blocked until a user gesture.**
  Playwright's headless chromium does not apply chromium's gate,
  over `file://` or over `http://`, with the relaxing flag removed and the gate asked for.
  A probe here would assert the opposite of the finding.
  Skipped, with the measurement that shows why.
- **The base64 encoder's memory and time per megabyte**,
  and the memoisation of the encoding across recompiles.
  Both are benchmarks rather than behaviours, and belong in `benchmarks/`.
- **What keeping every slide laid out costs.**
  The measurement that decided how a slide the runtime is not using is hidden.
  It is a cost rather than a behaviour, and a probe on it would assert a wall clock.
- **`animo` being unused on Typst Universe.**
  It needs the network and a third party's repository,
  and the answer only matters once, at submission time, where the release path checks it.

The two skips are real skips, reported by `pytest -rs`,
so they stay visible instead of quietly disappearing.

## The Map

Every entry in *Findings* has a probe module, or a row in the table above.

| Finding                                                      | Module                       |
| ------------------------------------------------------------ | ---------------------------- |
| Element identity in the output: `data-typst-label`           | `test_labels.py`             |
| The frame is the smallest unit of DOM addressability         | `test_frames.py`             |
| Regions: fixed footprints across epochs                      | `test_regions.py`            |
| Regions: an inline footprint has to pin its baseline         | `test_baselines.py`          |
| Regions: what a region learns from its container             | `test_region_containers.py`  |
| Crossfading epoch frames                                     | `test_crossfade.py`          |
| Crossfading two slide containers                             | `test_slide_crossfade.py`    |
| Choosing between stacked renderings: opacity, not visibility | `test_stacked_renderings.py` |
| Automatic canvas sizing: `#place` and `show place:`          | `test_canvas.py`             |
| Recording placements: what a `show place:` rule may do       | `test_place_rule.py`         |
| A fixed-height container stacks what does not fit            | `test_overflow.py`           |
| Fitting the slide to the browser window                      | `test_fitting.py`            |
| SVG `<defs>` ids are content hashes                          | `test_defs.py`               |
| Hoisting shared `<defs>`: sound in the browser, not in typst | `test_hoisting.py`           |
| CSS animation of typst SVG groups                            | `test_css_transforms.py`     |
| A keyframe property that does not change suppresses others   | `test_frame_drawing.py`      |
| A delayed effect does not hold its first keyframe            | `test_delayed_effects.py`    |
| The document timeline is not a clock                         | `test_timeline_clock.py`     |
| A faked clock drives a timer, not the document timeline      | `test_fake_clock.py`         |
| Styling from CSS: what is and is not reachable               | `test_css_styling.py`        |
| Cross-frame geometry, and the two nested transform slots     | `test_slots.py`              |
| `hide()` cannot be undone in the browser                     | `test_hide.py`               |
| A panic that depends on `query` can be swallowed             | `test_convergence.py`        |
| Introspection: positions                                     | `test_introspection.py`      |
| Introspection: the corner of an element, in both targets     | `test_anchors.py`            |
| Introspection: the fields of a nested structure              | `test_element_fields.py`     |
| Media elements in the HTML output                            | `test_media.py`              |
| Live preview: typst serves and reloads the HTML itself       | `test_watch.py`              |
| Wrapping a tag site: what it changes and what it does not    | `test_wrapping.py`           |
| A cetz draw command is a value, not content                  | `test_draw_commands.py`      |
| Inline versus block, decided by measurement                  | `test_levels.py`             |
| Providing a value down the tree                              | `test_providing.py`          |
| A counter reads the same everywhere a slide lays out         | `test_counters.py`           |
| Transforms between a tag's slots are layout-neutral          | `test_paged_transforms.py`   |
| Other verified behaviour                                     | `test_misc.py`               |

A few probes, and a few feature tests, import a package from Typst Universe:
the label emission is claimed for a cetz `content()` element and a fletcher node,
and so is the tag site of each of them.
They skip with the compiler's own explanation when the package does not resolve,
since a cold package cache without a network connection is an accident of the machine
and not a behaviour of typst or of Animo.
The releases they import are pinned in `tests/harness/packages.py`,
which both directories reach through the shared harness.
