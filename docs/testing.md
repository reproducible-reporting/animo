---
description: >-
  The three tiers of animo's test suite, what belongs in each,
  how to run one tier or one test,
  and the policy on stored reference images.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Testing

Animo has one test runner, `pytest`, and three tiers underneath it.
The weight is deliberately on the cheapest one.

```bash
pytest                        # everything
pytest -m plan                # tier 1 only
pytest -m paged               # tier 2 only
pytest -m browser             # tier 3 only, in every engine available
pytest --browser firefox      # tier 3 in firefox only, the rest unchanged
pytest -k firefox             # only the firefox share of tier 3
pytest probes                 # the behaviour probes, in all three tiers
pytest tests/test_harness.py::test_identical_rasters_compare_identical    # one test
```

The tier markers are not written out by hand.
Each test is marked with the tier of the fixture it asks for,
so a test cannot claim to be in a tier it is not in.

| Tier | Marker    | Fixture | Asserts on                                                   |
| ---- | --------- | ------- | ------------------------------------------------------------ |
| 1    | `plan`    | `typst` | whether a document compiles, and what it says with `#assert` |
| 2    | `paged`   | `paged` | the rasterised presentation and handout outputs              |
| 3    | `browser` | `page`  | the HTML output, in chromium, firefox and webkit             |

`tests/` holds the feature tests and the harness itself.
`probes/` holds one probe per entry in the *Findings* section of the design document;
[Behaviour Probes](probes.md) explains what a probe is and how to add one.
Both directories use the same fixtures,
which live in `tests/harness/` and are imported as `harness` from either.

## Tier 1: Plan Resolution

A document full of `#assert`, compiled and exported nowhere.
This is where per-state content and display state, epoch boundaries, epoch counts
and the footprint chosen for each region are asserted.
The documents are compiled for real, so footprints come from real `layout` and `measure` calls,
but nothing is written out and no raster or PDF is produced.

```python
def test_an_empty_step_changes_nothing(typst):
    typst.ok('#import "/src/lib.typ": *\n#assert.eq(..)\n')
```

A failure quotes the compiler's own diagnostics with the numbered document underneath,
because reading the message without the line it points at is guesswork.

The inverse case matters as much.
A document that *must* fail to compile is asserted on its message,
which is how the `import *` footgun is tested:

```python
def test_a_mistyped_primitive_is_refused(typst):
    typst.fails(body, "is not an animo operation")
```

`typst.fails` with no message asserts only that the compilation failed,
which is almost never what a test means:
a document may fail for a reason that has nothing to do with the claim.

`typst.warns(body, message)` is the third form, for behaviour the compiler
merely complains about, and `html=True` on any of the three
compiles for the HTML target instead of the paged one.

Because `replace` and `apply` carry content and functions,
tier-1 assertions target the *resolved structure*, the tag names, per-state flags,
epoch boundaries and counts, rather than the payloads, which do not compare usefully.

## Tier 2: The Paged Outputs

`typst compile -f png --ppi ..` rasterises the presentation and the handout directly,
so no PDF has to be rendered for an assertion about layout,
and the output mode is selected with `--input animo=..` exactly as an ordinary user would.

```python
def test_a_structural_step_leaves_the_rest_of_the_slide_alone(paged):
    pages = paged.png(body, mode="presentation")
    assert_identical_outside(pages[0], pages[1], band)
```

The default resolution is 72 ppi, which makes one pixel one typst point,
so a box measured in points is a box of the same numbers in the raster.

Every comparison helper reports *where* two rasters differ, not only that they do:

| Helper                                | Says                                                    |
| ------------------------------------- | ------------------------------------------------------- |
| `assert_identical(a, b, tol)`         | they agree everywhere, to within `tol` per channel      |
| `assert_differs(a, b)`                | they disagree somewhere, which proves a change happened |
| `assert_identical_outside(a, b, box)` | they agree everywhere outside `box`                     |
| `difference_box(a, b)`                | the smallest box containing every differing pixel       |
| `difference_report(a, b)`             | how many pixels, by how much, and within which box      |

The third one is the shape the region design is tested with,
and a failure that said only `False` would be unreadable.

The few assertions that are about the PDF *writer* rather than about the layout
render the real PDF with `pdf_pages`, which uses `pypdfium2`,
the same engine chromium renders PDFs with.

## Tier 3: The HTML Output

`playwright` drives the browsers it bundles, which is what keeps the pixels identical
on every machine. `./setup.sh` downloads them into `.venv/playwright`,
and a missing browser is an error rather than a skip:
a suite that is green because a third of it never ran is worse than a red one.

**Every test of this tier runs in chromium, firefox and webkit.**
A deck that only works in one engine is not a presentation format,
and they disagree on more than pixels:
firefox does not implement `calc(<length> / <length>)` at all
and drops the declaration it appears in, silently,
while webkit is the one whose `plus-lighter` crossfade is not pixel-exact.
The engine is a fixture, so a failure names it and `-k firefox` selects one of them.

```bash
pytest -m browser             # every engine this machine can run
pytest --browser firefox      # one of them; repeatable
```

### Which Engines Run Where

The three are not equally available, so the tier treats them differently.

| Engine     | Locally                        | In CI    |
| ---------- | ------------------------------ | -------- |
| `chromium` | required                       | required |
| `firefox`  | required                       | required |
| `webkit`   | where the platform has a build | required |

Chromium and firefox run wherever playwright runs,
so a launch failure there is a broken bootstrap and an error, never a skip.

Playwright builds one webkit for linux, against the libraries debian and ubuntu carry,
so on any other distribution it runs only inside a container.
Asking every contributor for a container is too much
and dropping a whole engine is too little,
so webkit skips where it cannot run, says so, and is required in CI, which is ubuntu.

**Where webkit cannot run, `./setup.sh` does not download it at all.**
It is a 300 MB download that could never launch,
so the engine list is decided before the download rather than after,
from `uname` and the `ID` and `ID_LIKE` fields of `/etc/os-release`.
The script ends by printing which engines run on your machine, and webkit reads as
`no build for this platform` there rather than as an installed browser that will not start.

**Naming an engine makes it required.**
`pytest --browser webkit` turns the skip into an error carrying playwright's own
diagnosis, and it is how the workflows ask for all three at once:

```bash
pytest --browser chromium --browser firefox --browser webkit
```

So the engine can never be skipped everywhere at once and leave the suite green.

What that error says depends on why the engine is unavailable.
On debian or ubuntu without the system packages, it is playwright's missing-library box,
and `playwright install-deps webkit` is the fix.
On a platform `./setup.sh` skipped, it is `Executable doesn't exist`,
because there is no local build to launch:
run `playwright install webkit` first if you want the launch error itself.

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

The browsers go to a path inside the container, not to `.venv/playwright`,
so the download leaves with the container and the working tree keeps no build
that the host cannot launch.
The cost is that each run downloads webkit again.
A typst binary has to be on the container's path as well,
and the one on the host will not do if its glibc is newer than the image's.

Geometry is preferred over pixels wherever it can say the same thing,
because a number survives a glyph rasterisation change and a screenshot does not.

```python
def test_a_tag_outside_a_region_does_not_move_between_epochs(open_page, page):
    deck = deck_of(open_page, page).goto(slide=3, state=1)
    first, second = deck.rects("caption")
    assert first.approx(second)
```

That geometry is read with `getBBox()` and `getScreenCTM()`, never with
`getBoundingClientRect()`, which is not the same box in every engine:
on a labelled group chromium reports the tight box and firefox one inflated
to roughly the width of the whole frame.
`harness.MEASURE` is the one expression that does it, and both `Deck.rects`
and the probes' own `measuring.rects` go through it.

Tests deep-link to a state instead of clicking their way to it.
That is a contract with the runtime, spelled out in `harness.browser.Deck`:

- the current position lives in `location.hash` as `#<slide>.<state>`,
  is restored on load and followed on `hashchange`,
  and the restore *snaps* rather than animating into the state;
- the position actually reached is mirrored in the `data-animo` attribute of the root element,
  so that a test waits for the snap instead of racing it;
- every slide container carries `data-animo-slide="<slide>"`,
  which is what scopes a tag name to one slide.

Until the runtime exists, `tests/documents/stand_in_deck.html` implements exactly those three
lines and nothing else, so that the fixtures and the contract are both exercised.

Two invariants are cheap to check here and worth checking directly,
because they are what the region design rests on:
the bounding box of every label *outside* a region is identical in all epoch frames of a slide,
and the rendering is pixel-identical outside the region between epochs,
including mid-crossfade.
Both are comparisons *within* one page load, so they need no stored reference images.

## Stored Reference Images

Stored pixels are the exception, and there are none in this repository yet.
Almost everything worth asserting about a rendering is a comparison within one run:
two epochs of the same slide, the same label in two frames,
a band that may change against a background that may not.
Those are unaffected by a glyph rasterisation change in a new typst release; a stored image is not.

When a picture really is the only statement that can be made, the `references` fixture stores one,
beside the module that uses it, and it has to say why:

```python
def test_something_only_a_picture_can_state(references, paged):
    references.check(
        "name",
        paged.png(body)[0],
        reason="why no comparison within this run can express it",
    )
```

The image is captured as PNG, converted with `Pillow` to **lossless** WebP,
and compared on decoded arrays, so the storage format never enters an assertion.
WebP defaults to lossy, in `Pillow` as in `playwright`'s own `type="webp"`,
which is why the conversion is explicit.

Regenerating them is one command:

```bash
pytest --update-references
```

A reference that does not exist yet is written on the first run and the test fails,
with that command in the message, so a new reference is reviewed before it is trusted.

## Fonts and Reproducibility

Every compilation goes through the same helper and passes `--ignore-system-fonts`,
so tests and examples use only the fonts typst embeds.
No font files are vendored: they would collide with the 1 MB limit of
`check-added-large-files` for no gain.

A generated document has to be written inside the repository,
because typst refuses a source file outside its project root.
The `scratch` fixture is that directory, under `tmp/pytest/<test name>/`.
It is emptied when the test starts and left behind when it ends,
because a failed compilation is worth looking at.

## Continuous Integration

| Workflow   | Trigger          | Does                                                           |
| ---------- | ---------------- | -------------------------------------------------------------- |
| `pytest`   | push to main, PR | the three tiers and the probes, against the pinned typst,      |
|            |                  | with tier 3 in all three engines                               |
| `probes`   | weekly schedule  | the probes against the newest typst release, non-blocking      |
| `zensical` | push to main, PR | builds the site with `--strict`, deploys to Pages on main only |
| `lint`     | push to main, PR | runs the Universe package checker over the package             |

Typst is installed with `typst-community/setup-typst`, pinned to the `compiler` field
of `typst.toml` by Snipwise, except in the `probes` workflow, where the newest release
is the point.
The package checker runs as a container rather than through its own GitHub Action,
because that action expects credentials for a GitHub App that a personal repository does not have.
