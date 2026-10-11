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

Animo rests on some twenty verified behaviours of typst 0.15.0 and of the browsers it
targets.
These behaviours are recorded in *Findings*,
which is the document beside the design that [Developing Animo](development.md) points at.
Any of them could change under the package.

A **probe** asserts such a behaviour itself, rather than a feature that happens to depend on it.
The difference is what a failure says.
When typst 0.16 lands and `data-typst-label` stops being emitted for labelled blocks,
a feature test says that reveal animations are broken;
a probe says that the emission rule changed.
The first leads to debugging Animo, the second to the release notes.

So a probe:

- asserts one entry of *Findings*, and names that entry in its module docstring;
- is **independent of every Animo feature**, and imports nothing from `src/`;
- states, where the claim is a comparison, why the comparison is not vacuous.
  That check is often enough a separate probe to be worth the habit.

Probes live in `probes/` and run in the same three tiers as the feature tests,
through the same fixtures. See [Testing](testing.md) for the tiers.

```bash
pytest probes             # all of them, against the pinned typst
pytest probes -m browser  # the ones that need a browser, in every engine available
```

They also run in a separate workflow, weekly, against the **newest** typst release.
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
1. Check what else rested on the finding.
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
Also prefer a cross-check within one run over a hardcoded number.
For example, the probe for `measure` agreeing between the two targets
takes the number out of the HTML compilation and hands it to the paged one through `--input`,
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

## Observations That Cannot Be Probed

An observation that no probe can assert does not belong in *Findings*,
because nothing would notice when a release of typst or of a browser changes it.
A measured cost, such as the time a deck takes to compile or to paint,
belongs in `benchmarks/` and in [Performance](performance.md).
A fact about the source tree or the history of typst is at most background to an entry,
and that entry is probed through the behaviour that follows from the fact.

## The Map

Every entry in *Findings* has a probe module.

| Finding                                                                               | Module                                         |
| ------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Element Identity in the Output: `data-typst-label`                                    | `test_labels.py`                               |
| The Frame Is the Smallest Unit of DOM Addressability                                  | `test_frames.py`                               |
| Regions: Fixed Footprints across Epochs                                               | `test_regions.py`                              |
| Regions: An Inline Footprint Has to Pin Its Baseline                                  | `test_baselines.py`                            |
| Regions: What a Region Learns from Its Container                                      | `test_region_containers.py`                    |
| Crossfading Two Renderings                                                            | `test_crossfade.py`                            |
| Isolating the Container of a Nested Stack                                             | `test_crossfade.py`                            |
| Choosing between Stacked Renderings: `opacity`, Not `visibility`                      | `test_stacked_renderings.py`                   |
| Crossfading Two Slide Containers                                                      | `test_slide_crossfade.py`                      |
| Chromium Rasterises a Frame Differently While an Opacity Animation Runs in It         | `test_slide_crossfade.py`                      |
| A Blended or Isolated Group at Rest                                                   | `test_layers_at_rest.py`                       |
| Automatic Canvas Sizing: `#place` Is Invisible to `auto`, but Visible to a Show Rule  | `test_canvas.py`                               |
| Recording Placements: What a `show place:` Rule May and May Not Do                    | `test_place_rule.py`                           |
| A Fixed-Height Container Stacks the Block-Level Content That Does Not Fit             | `test_overflow.py`                             |
| `html.frame` Sizes Its SVG in `em`, as an Inline Style                                | `test_place_rule.py`                           |
| Fitting the Slide to the Browser Window                                               | `test_fitting.py`                              |
| SVG `<defs>` Ids Are Content Hashes                                                   | `test_defs.py`, `test_hidden_defs.py`          |
| Hoisting Shared `<defs>`: Sound in the Browser, Out of Reach in Typst                 | `test_hoisting.py`                             |
| CSS Animation of Typst SVG Groups                                                     | `test_css_transforms.py`                       |
| The Centre a Scale Is About                                                           | `test_scale_origin.py`                         |
| A Keyframe Property That Does Not Change Suppresses the Ones That Do                  | `test_frame_drawing.py`                        |
| A Discrete Keyframe Equal at Both Ends Holds Its Value for the Whole Effect           | `test_discrete_keyframes.py`                   |
| The Document Timeline Is Not a Clock                                                  | `test_timeline_clock.py`                       |
| A Delayed Effect Does Not Hold Its First Keyframe Unless It Is Told To                | `test_delayed_effects.py`                      |
| A Faked Clock Drives a Timer without Touching the Document Timeline                   | `test_fake_clock.py`                           |
| Styling from CSS: What Is and Is Not Reachable                                        | `test_css_styling.py`                          |
| Cross-Frame Geometry Is Readable, so Morphing Is Possible                             | `test_slots.py`                                |
| A Morph Keeps the `plus-lighter` Sum                                                  | `test_morph_sum.py`, `test_morph_shape_sum.py` |
| Typst Writes a Shape from a Local Origin                                              | `test_shape_output.py`                         |
| The `d` of a Path Interpolates between Paths of One Structure                         | `test_path_interpolation.py`                   |
| A `translate` Carries an Element's Clip and Gradient, Not an Ancestor's Clip          | `test_translated_paint.py`                     |
| `hide()` Cannot Be Undone in the Browser                                              | `test_hide.py`                                 |
| A Counter Reads the Same Everywhere a Slide Lays Content Out                          | `test_counters.py`                             |
| A Panic That Depends on `query` Can Be Swallowed                                      | `test_convergence.py`                          |
| Nested Context Blocks Can Cost a Pass of Layout per Level                             | `test_nesting_depth.py`                        |
| Introspection: Positions                                                              | `test_introspection.py`                        |
| Introspection: The Corner of an Element, in Both Targets                              | `test_anchors.py`                              |
| Media Elements in the HTML Output                                                     | `test_media.py`                                |
| Live Preview: Typst Serves and Reloads the HTML Itself                                | `test_watch.py`                                |
| Wrapping a Tag Site: What It Changes and What It Does Not                             | `test_wrapping.py`                             |
| Inline versus Block, Decided by Measurement                                           | `test_levels.py`                               |
| Providing a Value down the Tree: A Show Rule Reaches into `measure`, a State Does Not | `test_providing.py`                            |
| A Cetz Draw Command Is a Value, Not Content                                           | `test_draw_commands.py`                        |
| What a Container Resolves from Its Direct Children                                    | `test_container_children.py`                   |
| Transforms between a Tag's Slots Are Layout-Neutral                                   | `test_paged_transforms.py`                     |
| Introspection: The Fields of a Nested Structure, and One Occurrence per Page          | `test_element_fields.py`                       |
| The Head of a Page That a Package Builds Itself                                       | `test_document_head.py`                        |
| Other Verified Behaviour                                                              | `test_misc.py`                                 |

A few probes, and a few feature tests, import a package from Typst Universe:
the label emission is claimed for a cetz `content()` element and a fletcher node,
and so is the tag site of each of them.
They skip with the explanation that the compiler gives when the package does not resolve,
since a cold package cache without a network connection is an accident of the machine
and not a behaviour of typst or of Animo.
The releases they import are pinned in `tests/harness/packages.py`,
which both directories reach through the shared harness.
