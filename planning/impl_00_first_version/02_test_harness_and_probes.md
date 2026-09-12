<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Phase 02: Test Harness and Probes

**Before you start:** read [planning/design.md](../design.md) in full,
then [README.md](README.md) of this directory.
The rules that govern every phase session are in that README:
ask when a significant decision comes up, end with a `## Session Log` section in this file,
and do not commit.

The relevant parts of the design document are *Testing* and *Behaviour probes* under
*Development Infrastructure*, the *Testing strategy* entry under *Resolved Design Decisions*,
and the whole *Findings* section, which is the input to the probes.

## Goal

All three test tiers exist and are exercised, and every finding the design rests on
has a probe that asserts the finding itself.
When typst or chromium changes something underneath animo,
the failure should name the behaviour that broke, not the feature that broke.

Like phase 01, this phase builds machinery whose value only becomes visible later.
The probes are what make it worth doing now anyway:
they are the one thing in this phase that has real content from day one,
and writing them is also how the three tiers get validated against known answers.

## Prerequisites

Phase 01.

## Scope

### In Scope

- **Tier 1, plan resolution.**
  A pytest fixture that compiles a `.typ` document with no output
  and reports failure with the compiler's stderr attached.
  Documents are full of `#assert`; the test asserts that the compile succeeded.
  The inverse case matters as much: a helper for documents that *must* fail to compile,
  asserting on the message, which is how the `import *` footgun gets tested later.
- **Tier 2, paged outputs.**
  `typst compile -f png --ppi ..` straight to rasters, decoded with `Pillow`
  and compared with `numpy`, with `--input animo=presentation` selecting the mode
  exactly as an ordinary user would.
  Plus a `pypdfium2` path for the few assertions that are about the PDF writer
  rather than about the layout.
  Provide comparison helpers that report *where* two rasters differ, not only that they do:
  phases 08 and 09 assert "identical outside this band" repeatedly,
  and a bare boolean makes those failures unreadable.
- **Tier 3, HTML.**
  `playwright` with its bundled chromium.
  Geometry through `page.evaluate`, images through `locator.screenshot(animations="disabled")`.
  The fixtures should already assume what phase 05 will provide:
  a deck whose slide and subslide state is addressable in `location.hash`,
  so tests deep-link instead of clicking their way to a state.
- **The reference image policy, implemented rather than described.**
  Stored images are the exception.
  When one is unavoidable, it is captured as PNG, converted with `Pillow` to lossless WebP,
  and compared on decoded arrays.
  Provide the update path (an environment variable or a pytest flag) in the same commit,
  because a policy without a regeneration command decays into hand-edited binaries.
- **`probes/`, one probe per entry in *Findings*.**
  Each probe asserts the finding, names the finding in its docstring or comment,
  and is independent of any animo feature.
  The findings that need a browser are probes too, in tier 3.
  Findings that are about the typst source tree rather than about observable behaviour
  (for example the single `data-typst-label` emission site) become behavioural probes
  where possible, and are otherwise skipped with a note rather than faked.
- **Continuous integration**, as the design document's table has it,
  minus the release workflow:
  `pytest` on push and pull request against the pinned typst,
  `probes` on a schedule against the newest typst release, non-blocking,
  `zensical` building with `--strict`,
  and `lint` running the Universe package checker through
  `docker run -v .:/data ghcr.io/typst/package-check check`.
  Typst is installed with `typst-community/setup-typst@v5`, pinned to the manifest's `compiler`.
- Fonts: tests and examples compile with `--ignore-system-fonts` and use only embedded fonts,
  so a contributor's machine and CI rasterise identically.

### Out of Scope

- The release workflow and the publishable subtree: phase 13.
- Any animo feature.
- Benchmarks: phase 11.

## Open Questions in Focus

1. **Does the non-blocking newest-typst probe job produce signal or noise?**
   The design document leaves this open deliberately.
   It cannot be answered in one session, but this phase decides the shape that makes
   answering it possible: how a probe failure is reported so that it names the finding,
   whether the job is allowed to fail silently or must open something,
   and how a finding that legitimately changed gets retired.
   A job nobody reads is worse than no job.
1. **How much of the suite genuinely needs stored pixels?**
   The design argues that the two invariants the region design rests on are comparisons
   *within* one page load and need no reference images, and that stored images are brittle.
   Establish concretely, while building the tiers, which assertions can be expressed
   numerically and which cannot, and make the answer visible:
   a test that stores a reference image should have to say why.

No other open question from the design document is in scope for this phase.

## Tests

The probes are the tests of this phase.
They should all pass against the pinned typst 0.15.1, because every one of them
restates something the design document already measured.
A probe that fails is a finding that was wrong, and that is exactly the news worth having early.

Add in addition a small self-test of the harness itself:
a raster comparison that is known to differ and one that is known to be identical,
so that a broken comparison helper cannot pass everything silently.

## Documentation

- `docs/testing.md`: the three tiers, what belongs in each,
  how to run one tier or one test, and the reference image policy including regeneration.
- `docs/probes.md` or a section of the same page: what a probe is,
  why it is separate from a feature test, and how to add one when a new finding is measured.
  Phases 03 to 13 all end with a session log that may contain new findings,
  so this page is the instruction for turning those into probes.

## Definition of Done

- `pytest` runs all three tiers and is green, with the browser tier actually launching chromium.
- Every entry in the design document's *Findings* section has a probe,
  or a recorded reason why it cannot have one.
- The four workflows exist and pass on a pull request.
- `pre-commit run --all-files` and `zensical build --strict` are green.

## Hand-Off

Every later phase writes tests through these fixtures and adds probes for what it measures.
Phase 05 depends on the tier-3 fixture assuming hash-addressable state,
and phases 08 and 09 depend on the raster comparison reporting the location of differences.

## Session Log

### What Was Built

The harness lives in `tests/harness/` and is imported as `harness` from both `tests/`
and `probes/`, through `pythonpath = ["tests"]` in `pyproject.toml`.
It is five modules: `typst` (the subprocess layer and the tier-1 runner, grown out of
phase 01's `helpers.py`), `raster` (tier 2 and the comparison helpers), `browser` (tier 3
and the deck abstraction), `references` (the stored-image policy), and `fixtures`
(the pytest plugin, loaded from a new root `conftest.py`, which is the only place
`pytest_plugins` may be declared).

`testpaths` is `tests, probes`, so one `pytest` runs both.
81 probes and 33 tests, with two probes skipped for recorded reasons.
The four workflows are under `.github/workflows/`.
`docs/testing.md` and `docs/probes.md` are new pages in the `nav`.

### Decisions

**Asked, and answered by the author.**

1. *Chromium is installed by `setup.sh` into `.venv/playwright`, and a missing browser is
   an error rather than a skip.* `.envrc` exports the same path, the fixtures default to it,
   and the workflows set it explicitly, so one rule locates the browser everywhere.
   The alternative, skipping, was rejected on the same ground the phase file gives:
   a suite that is green because a third of it never ran is worse than a red one.
1. *The scheduled newest-typst job writes its failing probes into the GitHub step summary
   and is allowed to stay red.* Nothing is opened and nothing is filed.
   The summary carries the instruction as well as the failures: a probe failure is a
   *finding* that changed, the design document is edited first, and the probe is updated or
   retired in the same commit, never relaxed.
   `docs/probes.md` has the same four steps under *When a Probe Fails*.
1. *cetz and fletcher are probed now*, pinned in `probes/packages.py`, skipping with the
   compiler's own message when the package does not resolve.
   Typst downloads them from Universe on first use, which is the only thing in the suite
   that reaches the network.

**Taken in the session.**

- **The tier markers are derived, not written.**
  `plan`, `paged` and `browser` are assigned in `pytest_collection_modifyitems` from the
  fixture a test asks for, at the priority browser > paged > plan.
  A hand-written marker would drift from the fixture within two phases.
- **The tier-1 runner compiles to `-`,** so a document that only has to compile writes
  nothing at all. A failure quotes the compiler's diagnostics with the numbered source
  underneath, because reading the message without the line it points at is guesswork.
  `fails(source, message)` asserts on the message: a document may fail for a reason that
  has nothing to do with the claim, and a bare `fails` would pass in that case.
- **The tier-3 contract is three lines, not two.** The phase file asks for hash-addressable
  state; a slide scope turned out to be needed as well, because a tag name means nothing
  outside its slide and `querySelectorAll` over the document finds the tag in every other
  slide too, at zero size. The contract phase 05 has to implement is in
  `harness.browser.Deck`: `location.hash` is `#<slide>.<state>`, restored by snapping;
  the reached position is mirrored in `data-animo` on the root element so a test waits
  instead of racing; every slide container carries `data-animo-slide="<slide>"`.
  `tests/documents/stand_in_deck.html` implements exactly those three lines and nothing
  else, so the fixtures and the contract are both exercised before the runtime exists.
  `harness.browser.state_hash` is the single place the format is spelled out.
- **Probes never import animo.** `probes/` has its own small support modules:
  `htmldoc` builds the stacked-frame documents, `svgtools` parses the emitted SVG as XML
  rather than with a regular expression, `measuring` reads geometry out of a page without
  the deck abstraction, and `packages` pins the two Universe releases.
- **`--update-references` is a pytest flag**, and `Reference.check` takes a required
  `reason` argument, so a stored image has to justify itself in the call that stores it.

### Open Questions in Focus

**Does the non-blocking newest-typst probe job produce signal or noise?**
Not answerable in one session, as the phase file says.
What is decided is the shape that makes answering it possible.
Every probe module names the *Findings* section it asserts in its docstring, and every
test docstring says what breaks without it, so a failure in the summary names the finding.
The job fails rather than passing silently, and the summary tells the reader what a failure
means and what to do with it. A probe is never relaxed to make the job green;
either the finding is corrected in the design document, or the probe is retired with it.

**How much of the suite genuinely needs stored pixels?**
None of it, so far, and the answer is visible: there is no `references/` directory in the
repository and `tests/test_harness.py` asserts that there is not.
Everything asserted about a rendering in this phase is a comparison within one run: two
epochs of the same slide against each other, a band that may change against a background
that may not, a blended midpoint against a single frame.
The policy and its regeneration command exist for the case that has not turned up yet.

### New Findings

**One contradicts the design document, and it is the reason to read this section.**

- **Labels inside math.** *Findings* says: "`#box[b] <bb>` with a space is parsed as literal
  math content (it renders as `<bb>`), whereas `#box(body)#label(name)` attaches correctly."
  The second half does not hold inside math.
  Measured on typst 0.15.1: in `$ a + #box(box[b])#label("v") = c $` no group is emitted,
  no error or warning is raised, and the label renders as visible math content `<v>`,
  which is the same failure mode the first half describes.
  Three forms were tried; the two that work both attach the label inside a *markup* block:
  `$ a + #[#box[b]#label("v")] = c $`, and a helper
  `#let tagged(name, body) = [#box(body)#label(name)]` called from math.
  So the design's conclusion is safe, because `tag` is such a helper, but its stated reason
  is wrong, and anyone writing `#box(..)#label(..)` inline in an equation loses the tag
  silently. **Should `planning/design.md` be updated?**
  The angle-bracket half also has a detail worth adding: `<v4>` inside math fails with
  "unknown variable: v4" unless the name happens to be a math binding, which `bb` is,
  so the "renders as `<bb>`" case is the lucky one rather than the general one.
  Probed both ways in `probes/test_labels.py`.

**The rest confirm or refine.**

- The `show place:` table reproduces exactly, to the pt: `0% + 141.73pt`, `50% + 0pt`,
  and the nested placement reporting `0% + 28.35pt` against its own container.
- The crossfade numbers reproduce in playwright's chromium: a plain opacity crossfade of two
  identical layers deviates by about 64/255 outside the region (0.75A + 0.25W over white),
  `plus-lighter` by at most 1/255.
- `measure` agrees between the two targets, checked by taking the number out of the HTML
  compilation and handing it to the paged one through `--input`, so nothing is hardcoded.
- **Playwright's headless chromium does not apply chromium's autoplay gate.**
  Measured with playwright 1.62 and its bundled headless chromium 151: `play()` resolves
  without a user gesture over `file://` and over `http://`, with playwright's own
  `--autoplay-policy=no-user-gesture-required` removed and the gesture requirement asked for
  explicitly. So the *Media elements* finding about `NotAllowedError` cannot be probed under
  this browser, and the probe skips with that measurement in its docstring rather than
  asserting the opposite.
- **Typst's named colours are not the pure ones.** `red` is `#ff4136` and `blue` is
  `#0074d9`, which is a trap for any raster assertion that compares a channel against 255
  or 0. Tests use `rgb("#ff0000")` instead.
- **`{0p}` pads to the page count, not to a fixed width.** A two-page document writes
  `page-1.png` and `page-2.png`, so the pages have to be sorted numerically and not by name.
- **`1 + none` is legal**: `none` is the additive identity in typst, so it is not a usable
  example of a failing expression.
- `html.elem("style", ..)` emits its text unescaped and lands in `<body>`,
  which is enough for the probes and will be enough for the runtime.
- The nested-box slot structure reproduces exactly:
  `#box(box[..])#label("x")` gives `<g transform data-typst-label="x"><g>` with an
  untransformed inner group, and a single `#box[..]` gives a child that carries
  `transform="matrix(..)"`.

### Incidental Repairs

- `docs/environment.md` had lost its YAML front matter to `mdformat` at some point before
  this phase; it was mangled into a thematic break and a heading. Restored, and `mdformat`
  leaves it alone now, as it does the front matter of `docs/index.md`.
- `.gitignore` ignores `*.html`, which would have swallowed the stand-in deck.
  An exception for `tests/documents/*.html` was added next to the rule.

### What a Follow-Up Phase Should Know

- **Phase 05** implements the three-line contract in `harness.browser.Deck`, and should run
  the tier-3 self-tests in `tests/test_harness.py` against a real deck as well as against
  the stand-in, rather than replacing the stand-in.
- **Phases 08 and 09** have `assert_identical_outside(first, second, box)` and
  `difference_report`, which name the differing pixels, their maximum deviation and their
  bounding box. `Box` is in pixel coordinates with exclusive upper bounds, and
  `PagedRunner.png` renders at 72 ppi by default, so one pixel is one typst point.
- **Phase 11** inherits three items this phase declined to probe because they are
  benchmarks: the base64 encoder's time and memory per megabyte, the memoisation of that
  encoding across recompiles, and anything about compile time or page weight.
- **Every phase** adds its findings to `planning/design.md` and a probe to `probes/`,
  and adds the row to the map in `docs/probes.md`. The instruction is on that page.
- `ruff` is configured in `pyproject.toml` but is not a `pre-commit` hook, so nothing runs
  it. All Python written in this phase is `ruff check` and `ruff format` clean, by hand.
  Wiring the hook is phase 01's business and was left alone.
- The four workflows are written but **not verified**: nothing in this session can run
  GitHub Actions, so the *Definition of Done* item "the four workflows exist and pass on a
  pull request" is half met. The first pull request is where they are proven.
