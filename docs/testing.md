---
description: >-
  The three tiers of Animo's test suite, what belongs in each,
  how to run one tier or one test,
  and the policy on stored reference images.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Testing

Animo has one test runner, `pytest`, and its tests fall into three tiers.
Tier 1 is the cheapest to run,
and a test belongs there whenever tier 1 can express its assertion.

```bash
pytest                        # everything
pytest -m plan                # tier 1 only
pytest -m paged               # tier 2 only
pytest -m browser             # tier 3 only, in every engine available
pytest --browser firefox      # every tier, with tier 3 in firefox only
pytest -k firefox             # only the tier-3 tests that run in firefox
pytest probes                 # the behaviour probes, in all three tiers
pytest tests/test_harness.py::test_identical_rasters_compare_identical    # one test
```

The harness marks each test with the tier of the fixture that the test requests,
so the markers are never written by hand and a test cannot carry the wrong one.

| Tier | Marker    | Fixture | Asserts on                                                   |
| ---- | --------- | ------- | ------------------------------------------------------------ |
| 1    | `plan`    | `typst` | whether a document compiles, and what it says with `#assert` |
| 2    | `paged`   | `paged` | the rasterised static presentation and static handouts       |
| 3    | `browser` | `page`  | the HTML presentation, in chromium, firefox and webkit       |

`tests/` holds the feature tests and the tests of the harness itself.
`probes/` holds the probes that assert the entries of *Findings*.
See [Behaviour Probes](probes.md) for what a probe is and how to add one.
Both directories use the same fixtures,
which live in `tests/harness/` and are imported as `harness` from either directory.

A few tests in each directory compile a document that imports cetz or fletcher,
because Animo supports a tag on a cetz `content()` element and on a fletcher node,
and the label emission of typst is claimed for both of them.
These tests are the only part of the suite that uses the network.
`tests/harness/packages.py` pins the releases of both packages.
When a package cannot be resolved, the test is skipped with the message of the compiler,
because an empty package cache on a machine without network access is not a failure of Animo.

## Tier 1: Plan Resolution

A tier-1 test compiles a document that checks its own results with `#assert`,
and writes no output file.
Tier 1 asserts the content and the display state of each state, the epoch boundaries,
the number of epochs, and the footprint that Animo chooses for each region.
Typst compiles these documents fully, so a footprint comes from real `layout` and `measure` calls,
but the compilation produces no PNG and no PDF.

```python
def test_an_empty_step_changes_nothing(typst):
    typst.ok('#import "/src/lib.typ": *\n#assert.eq(..)\n')
```

When such a test fails, the message quotes the diagnostics of the compiler
above the document with numbered lines,
so that you can see the line that each diagnostic points at.

Some documents have to fail to compile, and a test of such a document asserts the error message.
One example is `sub(rotate("b", 45deg))`.
Animo has no `rotate` primitive, so after `import *` the name `rotate` still refers to typst's
`rotate`, and Animo has to refuse the content that it returns:

```python
def test_a_mistyped_primitive_is_refused(typst):
    typst.fails(body, "is not an animo operation")
```

Without a message, `typst.fails` asserts only that the compilation failed.
That is rarely enough,
because a document can fail for a reason unrelated to the claim of the test.

The third form, `typst.warns(body, message)`, asserts a warning of the compiler.
Each of the three forms accepts `html=True`,
which compiles for the HTML target instead of the paged target.

The primitives `replace` and `apply` carry content and functions,
which cannot be compared in a useful way.
A tier-1 assertion therefore checks the resolved structure of the timeline instead.
This structure consists of the tag names, the flags of each state,
the epoch boundaries and the number of epochs.

## Tier 2: The Paged Outputs

A tier-2 test rasterises the static presentation or the static handouts directly,
with `typst compile -f png --ppi ..`,
so an assertion about layout needs no PDF renderer.
The test selects the output type with `--input animo=..`, as an author would.

```python
def test_a_structural_step_leaves_the_rest_of_the_slide_alone(paged):
    pages = paged.png(body, mode="presentation")
    assert_identical_outside(pages[0], pages[1], band)
```

The default resolution is 72 ppi, at which one pixel is one typst point.
A box measured in points therefore has the same coordinates in pixels.

When a comparison fails, each helper reports where the two rasters differ:

| Helper                                | Says                                                    |
| ------------------------------------- | ------------------------------------------------------- |
| `assert_identical(a, b, tol)`         | they agree everywhere, to within `tol` per channel      |
| `assert_differs(a, b)`                | they disagree somewhere, which proves a change happened |
| `assert_identical_outside(a, b, box)` | they agree everywhere outside `box`                     |
| `difference_box(a, b)`                | the smallest box containing every differing pixel       |
| `difference_report(a, b)`             | how many pixels, by how much, and within which box      |

Tests of regions use `assert_identical_outside`,
which shows where the slide changed outside the region when such a test fails.

A few assertions are about the PDF writer of typst rather than about the layout.
These tests render the real PDF with `pdf_pages`, which uses `pypdfium2`,
the same PDF engine that chromium uses.

## Tier 3: The HTML Output

Tier 3 uses `playwright` to drive the browsers that the pinned playwright release bundles,
so a page renders to the same pixels on every machine.
`./setup.sh` downloads these browsers into `.venv/playwright`.

**Every test of this tier runs in chromium, firefox and webkit.**
A deck has to work in all three engines, and the engines differ in more than pixels.
For example, firefox does not implement `calc(<length> / <length>)`
and silently drops any declaration that contains it,
while webkit draws a group beside a hidden sibling differently from a lone group.
The engine is a parameter of a fixture, so the name of a failing test includes the engine,
and `-k firefox` selects the tests that run in firefox.

### Which Engines Run Where

The three engines are not available on every machine, so tier 3 treats them differently:

| Engine     | Locally                        | In CI    |
| ---------- | ------------------------------ | -------- |
| `chromium` | required                       | required |
| `firefox`  | required                       | required |
| `webkit`   | where the platform has a build | required |

Chromium and firefox run wherever playwright runs.
A failure to launch either of them means that the setup is broken,
so the test reports an error rather than a skip,
because a suite that passes while a third of its tests are skipped
does not show whether those tests would pass.

Playwright builds webkit for linux against the system libraries of debian and ubuntu,
so on any other linux distribution webkit runs only inside a container.
Requiring a container from every contributor would be too demanding,
and leaving webkit out would lose coverage.
The webkit tests are therefore skipped, with a reason, on a machine that cannot run webkit.
They are required in continuous integration, which runs on ubuntu.

**`./setup.sh` downloads webkit only where webkit can run,** because the download is 300 MB.
That is macOS and the debian family.
The script decides this before downloading,
from `uname` and from the `ID` and `ID_LIKE` fields of `/etc/os-release`.
The script ends by printing which engines run on your machine.
Where webkit cannot run, the line for webkit reads `no build for this platform`.

**Naming an engine with `--browser` makes it required.**
`pytest --browser webkit` reports an error with the diagnosis of playwright
where the suite would otherwise skip webkit.
The workflows of continuous integration name all three engines in this way:

```bash
pytest --browser chromium --browser firefox --browser webkit
```

As a result, the suite passes in continuous integration only when every engine has run.

The error depends on why webkit is unavailable.
On debian or ubuntu without the required system packages,
playwright prints a box that lists the missing libraries,
and `playwright install-deps webkit` installs them.
On a platform where `./setup.sh` skipped webkit, the error is `Executable doesn't exist`,
because there is no local build to launch.
To see the actual launch error there, run `playwright install webkit` first.

To run webkit by hand where there is no build for it,
mount the working tree into an ubuntu container at the same absolute path,
because the virtual environment holds absolute symlinks:

```bash
podman run --rm --security-opt label=disable \
  -v "$PWD":"$PWD" -w "$PWD" \
  -e PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright \
  -e TYPST_PACKAGE_PATH="$PWD/.typst-packages" \
  ubuntu:24.04 bash -c '
    apt-get update -qq
    .venv/bin/python -m playwright install --with-deps webkit
    .venv/bin/python -m pytest -m browser --browser webkit'
```

The container installs the browsers under `/tmp/playwright` rather than in `.venv/playwright`.
The download is then discarded together with the container,
and the working tree holds no webkit build that the host cannot launch.
As a consequence, each run downloads webkit again.
The container also needs a typst binary on its `PATH`.
The typst binary of the host does not work there if it needs a newer glibc than the image has.

### Geometry Instead of Pixels

A test compares geometry rather than pixels wherever geometry can express the same claim,
because a change in how glyphs are rasterised moves pixels but leaves coordinates alone.

```python
def test_a_tag_outside_a_region_does_not_move_between_epochs(open_page, page):
    deck = deck_of(open_page, page).goto(slide=3, state=1)
    first, second = deck.rects("caption")
    assert first.approx(second)
```

The harness reads geometry with `getBBox()` and `getScreenCTM()`.
It avoids `getBoundingClientRect()`, because the engines return different boxes for it.
On a labelled group, chromium reports the tight box,
while firefox reports a box about as wide as the whole frame.
All geometry is read through one JavaScript expression, `harness.MEASURE`,
which both `Deck.rects` in the tests and `measuring.rects` in the probes use.

### Deep Links

A test opens a deck directly at a state through a deep link,
instead of stepping through the deck to reach that state.
Deep links rely on a contract with the runtime, which `harness.browser.Deck` documents:

- the current position is kept in `location.hash` in the form `#<slide>.<state>`,
  which the runtime restores on load and follows on `hashchange`,
  and the runtime *snaps* into the restored state instead of animating into it;
- the root element mirrors the position that the runtime actually reached
  in its `data-animo` attribute, so that a test can wait for the snap instead of racing it;
- every slide container carries `data-animo-slide="<slide>"`,
  which scopes a tag name to one slide.

`tests/documents/stand_in_deck.html` implements these three items of the contract
and nothing else.
The tests of the harness run against this file,
so they exercise the fixtures and the contract without compiling a deck.

### Timed Decks

A deck with a `wait:` or a `hold:` advances by itself,
and a test of such a deck controls the time instead of waiting for it.
The runtime implements `wait:` and `hold:` with `setTimeout`,
which pausing an animation does not affect.
The `timed_deck_at` fixture therefore installs the fake clock of playwright
before the deck is loaded, and `Deck.run_for` advances that clock by a given time.
The fake clock leaves the document timeline untouched,
so the motion that a timed step starts still runs in real time,
and the test reads that motion by setting the `currentTime` of the animation.
The runtime therefore needs no hook for tests.

### Invariants of Regions

The design of regions rests on two invariants, and tier 3 checks both of them directly:

- every labelled element outside a region is laid out once,
  and every rendering in the epoch stack of a region starts at the same corner;
- outside a region, the slide is identical pixel for pixel in every epoch,
  also halfway through a crossfade.

Both checks compare two renderings within one page load, so they need no stored reference images.

## Stored Reference Images

A test uses a stored reference image only as an exception,
and the repository contains none at the moment.
Almost every useful assertion about a rendering compares two renderings from the same run,
such as two epochs of the same slide, the same label in two frames,
or a band that may change against a background that may not.
A change in glyph rasterisation in a new typst release affects both sides of such a comparison
equally, but it breaks a comparison against a stored image.

When only a picture can express a claim,
the `references` fixture stores a reference image beside the test module,
and the test has to give the reason:

```python
def test_something_only_a_picture_can_state(references, paged):
    references.check(
        "name",
        paged.png(body)[0],
        reason="why no comparison within this run can express it",
    )
```

The fixture captures the image as PNG, converts it with `Pillow` to **lossless** WebP,
and compares the decoded pixel arrays, so the file format has no effect on the assertion.
Both `Pillow` and the `type="webp"` option of `playwright` default to lossy WebP,
so the fixture requests lossless compression explicitly.

To regenerate the stored reference images, run:

```bash
pytest --update-references
```

When a reference image does not exist yet, the first run writes it and the test fails,
with this command in the message,
so that someone reviews a new reference image before a test relies on it.

## Fonts and Reproducibility

Every compilation goes through one helper, which passes `--ignore-system-fonts`,
so tests and demo decks use only the fonts that typst embeds.
The repository contains no font files,
because the embedded fonts suffice and a font file would exceed the 1 MB limit of the
`check-added-large-files` hook.

A generated document has to be written inside the repository,
because typst refuses a source file outside its project root.
The `scratch` fixture provides such a directory, `tmp/pytest/<test name>/`.
The fixture empties the directory when the test starts and keeps it after the test ends,
so that you can inspect the files of a failed compilation.

## Continuous Integration

| Workflow   | Trigger                    | Does                                                                                      |
| ---------- | -------------------------- | ----------------------------------------------------------------------------------------- |
| `pytest`   | push to main, PR           | runs the three tiers and the probes against the pinned typst, tier 3 in all three engines |
| `probes`   | weekly schedule            | runs the probes against the newest typst release, without blocking anything               |
| `zensical` | push to main, PR, tag `v*` | compiles the demo decks, builds the site with `--strict`, and deploys it for a tag only   |
| `release`  | push to main, PR, tag `v*` | builds and checks the publishable subtree, and publishes a GitHub release for a tag       |

The `pre-commit` hooks run on [pre-commit.ci](https://pre-commit.ci/) rather than in a workflow,
because that service pushes the fixes that the formatting hooks make
instead of failing a pull request with a diff.
Every hook except `typstyle` and `uv-lock` runs there, so `reuse` and `snipwise check` gate a merge.

The workflows install typst with `typst-community/setup-typst`.
Snipwise pins the release to the `compiler` field of `typst.toml` in every workflow
except `probes`, which tests the newest release.

The `release` workflow checks the subtree with the Universe package checker.
The checker runs as a container rather than through its GitHub Action,
because the action expects credentials for a GitHub App, which a personal repository does not have.
The checker reads the subtree that would be submitted to `typst/packages`,
which consists of the tracked files minus the `exclude` list of the manifest.
`tools/build_package.py` writes this subtree first, and the checker reads the copy.
The checker does not compile anything,
so the workflow also compiles `demos/hello.typ` to HTML and PDF with the subtree as the package.
This compilation fails when the subtree is missing a file that the package reads,
such as a script of the runtime.

The `release` workflow ends with the subtree as an artefact.
A maintainer copies the subtree into a sparse checkout of `typst/packages`
and opens the pull request by hand, because a submission cannot be taken back.
Every step up to the artefact also runs on a push to main
and on a pull request that changes a file of the published subtree,
so a tag only runs steps that have already passed on the same content.
A push to main or a pull request publishes nothing.
Two steps run only for a tag.
The first compares the tag with the `version` field of `typst.toml`
and fails the workflow when the two disagree.
The second creates the GitHub release.
The workflow reads the version from the manifest and the tag, so it takes no version as input.
