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

The design of Animo depends on many behaviours of typst 0.15.0 and of the browsers it targets.
*Findings* records each of these behaviours, as verified by experiment.
See [Where the Specification Lives](development.md#where-the-specification-lives)
for where to find *Findings*.
A new release of typst or of a browser could change any of these behaviours.

A **probe** asserts such a behaviour itself, rather than a feature that happens to depend on it.
The difference shows when a test fails.
Suppose that a new typst release stops emitting `data-typst-label` for labelled blocks.
A feature test then reports that reveal animations are broken,
while a probe reports that typst no longer emits the attribute.
The first failure leads to debugging Animo, and the second leads to the release notes of typst.

A probe therefore has these properties:

- it asserts one entry of *Findings*, and names that entry in its module docstring;
- it is **independent of every Animo feature**, and imports nothing from `src/`;
- where its claim is a comparison, it states why the comparison is not vacuous.
  The check that the comparison is not vacuous is often a separate probe.

Probes live in `probes/` and run in the same three tiers as the feature tests,
through the same fixtures.
See [Testing](testing.md) for the tiers.

```bash
pytest probes             # all of them, against the pinned typst
pytest probes -m browser  # the ones that need a browser, in every engine available
```

A separate workflow also runs the probes every week against the **newest** typst release.
This workflow blocks no pull request, and reports its results in the summary of the run.

## Failing Probes

A failing probe indicates that a documented behaviour of typst or a browser has changed,
and the weekly workflow exists to detect such changes.
Never fix a failing probe by relaxing its assertion.
Take these steps instead.

1. Decide whether the finding was wrong when it was written,
   or whether a newer release has changed the behaviour.
1. Edit the entry in *Findings* to say what holds now, and on which release it was observed.
   A finding is a claim about a point in time, and it is written as one.
1. Update the probe in the same commit.
   When the behaviour that the probe guarded is gone,
   delete the probe together with its finding, rather than leaving the probe skipped.
1. Check what else depended on the finding.
   Every entry in *Findings* supports some part of the design,
   and the design document says which part.

## New Findings and Their Probes

Work on the design or the implementation sometimes depends on a behaviour of typst
or of a browser that *Findings* does not record yet.
That behaviour becomes a new finding, and gets a probe in the following steps.

1. Add the finding to *Findings*,
   with the measured numbers and the release on which they were observed.
1. Write the probe in the module that covers that part of the design,
   or in a new `probes/test_<topic>.py` for a new topic.
   The module docstring names the finding,
   and the docstring of the test says what would break without the behaviour.
1. Build the mechanism by hand, without Animo.
   For example, a probe for the region footprint rule calls `layout` and `measure` itself,
   so that a failure cannot come from a bug in Animo.
1. Add a row to the table in [Probe Modules](#probe-modules).

Two rules of thumb apply.
Prefer an assertion inside the document (`#assert`) over one in Python,
because a failing `#assert` points at the line where the behaviour differs.
Also prefer comparing two values from the same test
over comparing one value with a hardcoded number.
A hardcoded number also records details that the finding is not about,
such as the metrics of the fonts that typst embeds.
The probe then fails when such a detail changes, even though the finding still holds.
For example, the probe that checks whether `measure` gives the same size in both targets
takes the size from the HTML compilation and passes it to the paged compilation
through `--input`.
A typst release with different font metrics changes the size in both targets alike,
so this probe fails only when the two targets disagree.

## Answers per Engine

Several probes hold a table with one expected answer per engine,
because the three engines do not always agree.
Every entry of such a table has to come from a run in the engine that the entry names.
An entry copied from another table or from another engine is an assumption
that looks like a measurement.
With such an entry, a browser probe can pass while the behaviour it guards is absent.

The risk is largest for webkit,
because webkit runs only in a container outside macOS and the debian family.
See [Which Engines Run Where](testing.md#which-engines-run-where).
Measure in webkit before adding a webkit entry to a table:

```bash
pytest --browser webkit
```

Until that measurement exists, the table says that the webkit entry is unmeasured,
and the probe asserts only what was measured.
For an unmeasured engine, a probe may accept either of two answers,
as long as it names the answer for each engine that was measured,
because that is still a claim based on measurements.
An invented number is not such a claim.

## Observations That Cannot Be Probed

An observation that no probe can assert does not belong in *Findings*,
because nothing would notice when a release of typst or of a browser changes it.
A measured cost, such as the time a deck takes to compile or to paint,
belongs in `benchmarks/` and in [Performance](performance.md).
A fact about the source code or the history of typst can appear in an entry only as background.
The probe of that entry asserts the behaviour that follows from the fact.

## Probe Modules

The table lists the probe module for each entry in *Findings*.

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
