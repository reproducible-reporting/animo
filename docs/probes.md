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

Animo rests on some twenty verified behaviours of typst 0.15.1 and of chromium.
They are recorded in the *Findings* section of
[the design document](https://github.com/reproducible-reporting/animo/blob/main/planning/design.md),
and any of them could change under the package.

A **probe** asserts such a behaviour itself, rather than a feature that happens to depend on it.
The difference is what a failure says.
When typst 0.16 lands and `data-typst-label` stops being emitted for labelled blocks,
a feature test says that reveal animations are broken;
a probe says that the emission rule changed.
The first sends you debugging animo, the second sends you to the release notes.

So a probe:

- asserts one entry of *Findings*, and names that entry in its module docstring;
- is **independent of every animo feature**, and imports nothing from `src/`;
- states, where the claim is a comparison, why the comparison is not vacuous,
  which is a probe of its own often enough to be worth the habit.

Probes live in `probes/` and run in the same three tiers as the feature tests,
through the same fixtures. See [Testing](testing.md) for the tiers.

```bash
pytest probes             # all of them, against the pinned typst
pytest probes -m browser  # the ones that need chromium
```

They also run in a workflow of their own, weekly, against the **newest** typst release.
That job is non-blocking for pull requests and reports into the run summary.

## When a Probe Fails

A failing probe is a finding that changed, and that is the news the job exists to deliver.
It is never fixed by relaxing the probe.

1. Decide whether the finding was wrong when it was written,
   or whether it has legitimately changed in a newer release.
1. Edit the *Findings* entry in the design document to say what now holds,
   and say on which release it was observed.
   A finding is a point-in-time claim, and it is written as one.
1. Update the probe in the same commit, or retire it when the behaviour it guarded is gone.
   A retired probe is deleted together with its finding, not left skipped.
1. Check what else rested on it.
   Every entry in *Findings* is load-bearing for something,
   and the design document says for what.

## Adding a Probe

Phases 03 to 13 each end with a session log that may contain new findings.
Turning one into a probe is the same four steps every time.

1. Add the finding to the *Findings* section of the design document,
   with the numbers and the release it was observed on.
1. Write the probe in the module that covers that part of the design,
   or a new `probes/test_<topic>.py` when it is a new topic.
   The module docstring names the finding; the test docstring says what would break without it.
1. Build the mechanism by hand, without animo.
   A probe for the region footprint rule writes `layout` and `measure` itself,
   so that a failure cannot be an animo bug.
1. Add the row to the table below.

Two rules of thumb are worth stating.
Prefer an assertion inside the document (`#assert`) over one in Python,
because it fails where the behaviour is.
And prefer a cross-check within one run over a hardcoded number:
the probe for `measure` agreeing between the two targets takes the number out of the HTML
compilation and hands it to the paged one through `--input`,
so a change in font metrics cannot make it pass for the wrong reason.

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
- **`animo` being unused on Typst Universe.**
  It needs the network and a third party's repository,
  and the answer only matters once, at submission time, where the release path checks it.

The two skips are real skips, reported by `pytest -rs`,
so they stay visible instead of quietly disappearing.

## The Map

Every entry in *Findings* has a probe module, or a row in the table above.

| Finding                                                  | Module                   |
| -------------------------------------------------------- | ------------------------ |
| Element identity in the output: `data-typst-label`       | `test_labels.py`         |
| The frame is the smallest unit of DOM addressability     | `test_frames.py`         |
| Regions: fixed footprints across epochs                  | `test_regions.py`        |
| Crossfading epoch frames                                 | `test_crossfade.py`      |
| Automatic canvas sizing: `#place` and `show place:`      | `test_canvas.py`         |
| Recording placements: what a `show place:` rule may do   | `test_place_rule.py`     |
| SVG `<defs>` ids are content hashes                      | `test_defs.py`           |
| CSS animation of typst SVG groups                        | `test_css_transforms.py` |
| Styling from CSS: what is and is not reachable           | `test_css_styling.py`    |
| Cross-frame geometry, and the two nested transform slots | `test_slots.py`          |
| `hide()` cannot be undone in the browser                 | `test_hide.py`           |
| Introspection: positions                                 | `test_introspection.py`  |
| Media elements in the HTML output                        | `test_media.py`          |
| Live preview: typst serves and reloads the HTML itself   | `test_watch.py`          |
| Other verified behaviour                                 | `test_misc.py`           |

Two probes in `test_labels.py` import a package from Typst Universe,
because the label emission is claimed for a cetz `content()` element and a fletcher node.
They skip with the compiler's own explanation when the package does not resolve,
since a cold package cache without a network connection is an accident of the machine
and not a behaviour of typst.
The releases they import are pinned in `probes/packages.py`.
