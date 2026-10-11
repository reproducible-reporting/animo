---
description: >-
  What a slide costs to compile in each output type, which authoring choices are expensive,
  how heavy the HTML deck is on the wire, and the measured numbers behind all of it.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Performance

The demo deck for this page is
[`tour.typ`](https://github.com/reproducible-reporting/animo/blob/main/demos/tour.typ)
([HTML](https://reproducible-reporting.github.io/animo/demos/tour.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/demos/tour-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/demos/tour-handouts.pdf)).
It is the deck on which the numbers below were measured.

The cost of Animo is that it asks typst to lay out a slide more than once.

In summary, an ordinary deck costs about twice as much as a plain typst deck,
and the live preview loop is an order of magnitude cheaper than a cold compile,
so a deck remains comfortable to write.
The most expensive construct is a
[cetz canvas inside a region](regions.md#where-a-region-cannot-go).

## What Is Rendered, and How Often

| Output type         | Renderings per slide                                                |
| ------------------- | ------------------------------------------------------------------- |
| HTML presentation   | one, plus one per [epoch](structural.md#epochs) per changing region |
| Static presentation | one per state                                                       |
| Static handouts     | one per state whose `handout` flag resolved to `true`               |

A `background:` or an `overlay:` that is content is rendered **once** beside these,
whatever the output type and however many epochs the slide has.

On top of that, **every region lays its body out once per epoch to measure it**,
so that the region can reserve the largest of those layouts.
A region with an explicit `height` measures nothing,
and a slide with one epoch measures nothing either.

Two limits on this count keep the cost affordable:

- The count does not grow per state.
  A run of `reveal`, `move` and `scale` operations shares one rendering,
  so a slide with eight continuous subslides and no content change is exactly as cheap in the
  browser as a slide with none;
- The count is not a product over tags.
  Regions nest as fixed footprints rather than as states,
  so four tags over three epochs cost three renderings each and not eighty-one.

## The Measured Numbers

[`demos/tour.typ`](https://github.com/reproducible-reporting/animo/blob/main/demos/tour.typ)
is the deck these numbers were measured on.
When the numbers were taken, the deck had 17 slides, 61 states,
and 17 renderings of the regions whose content changes.
They were measured on an Intel Core i7-4790 at 3.6 GHz with typst 0.15.0 in October 2026.

The compiler is the release `setup.sh` installs.
For linux that is the static musl binary typst publishes,
and typst publishes no build against glibc for linux.
A glibc build of the same release compiles these decks 1.2 to 2.4 times faster,
with the widest difference on the paged outputs and on the placement deck below.
The seconds here are therefore what a contributor who ran `setup.sh` measures,
and a reader whose typst came from a distribution or from `cargo` sees smaller ones.
The factors are unaffected,
because the plain typst deck they divide by is compiled by the same binary.

| What                         | Measured                 |
| ---------------------------- | ------------------------ |
| HTML presentation            | 0.83 s                   |
| Static presentation          | 1.37 s                   |
| Static handout               | 0.82 s                   |
| HTML page                    | 1.57 MB, 312 KiB gzipped |
| One edit under `typst watch` | 88 ms                    |

The terms behind those totals, each measured as the difference between two decks that
differ in one thing only:

| Term                                    | Cost                                  |
| --------------------------------------- | ------------------------------------- |
| one more epoch on one slide, in HTML    | 2.5 ms, 19 KiB raw, 0.5 KiB gzipped   |
| one region measuring one epoch of prose | 2.6 ms                                |
| one region measuring one epoch of cetz  | 19.3 ms                               |
| one content layer on one slide, in HTML | 19 KiB raw, 5 KiB gzipped, under 1 ms |

And the same content laid out by plain typst, one page per slide, as a factor:

| Deck                                                 | Against plain typst |
| ---------------------------------------------------- | ------------------- |
| no structural subslides                              | 2.1                 |
| four continuous subslides per slide                  | 3.0                 |
| two to eight epochs per slide                        | 2.5 to 3.3          |
| two regions, three epochs, four continuous subslides | 6.6                 |
| two regions of cetz canvas, four epochs              | 17.3                |

Your own numbers take one command to measure, and land in
[`benchmarks/results/`](https://github.com/reproducible-reporting/animo/tree/main/benchmarks):

```bash
./benchmarks/run.py --output benchmarks/results/$(hostname).json
```

Run it on a quiet machine.
Seconds measured while another process is using the processor are not meaningful.

## The Live Preview Compared to a Cold Compile

Typst memoises across recompiles inside one `typst watch` process,
so an edit only pays for what it actually changed.
On the tour, an edit to one slide recompiles in **88 ms** against **0.83 s** cold.

This is the number that decides whether a deck is comfortable to write.
Keep the preview running while you write:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

## What Costs, and What to Do About It

**A structural operation costs a rendering of every region, a continuous one costs none.**
`replace`, `remove`, `apply` and `reset` each start a new epoch, which is a fresh layout of
every region whose content changes on the slide and a fresh rendering of it in the page.
What lies outside the regions is laid out once, whatever the epochs.
`reveal`, `hide`, `move` and `scale` are applied by the browser to a rendering that already
exists. So where either would do, prefer the continuous one:

```typst
sub(hide("caveat"))    // no extra rendering
sub(remove("caveat"))  // a rendering of the tag's region, and a crossfade
```

Outside a region the two even look the same,
because the [box reserved by a changing tag](structural.md#box-reserved-by-a-changing-tag)
holds its largest state either way. There, `remove` costs a rendering without any benefit.

**A region measures every epoch, so regions and epochs multiply.**
Two regions over four epochs is eight measurements per rendering of the slide, not two.
The cost grows linearly with each of the two, which keeps it affordable,
but it is the product of the two.

**Give a region a `height` when you know it.**
A region with an explicit height measures nothing at all.
On a deck of twelve slides with two regions over four epochs,
giving the regions a height brought the HTML output from 0.94 s down to 0.56 s.
The measurements were about two fifths of the cost of that deck.
The drawback is that a state taller than the height is clipped.

**A cetz canvas inside a region is the expensive case.**
The region lays the canvas out afresh for every epoch, and cetz layout is not cheap:
19.3 ms per measurement against 2.6 ms for the same shape holding prose, seven times more.
A deck of twelve such slides over four epochs took 4.9 s to compile against 0.15 s for the
same drawings as plain typst.
There are two ways to avoid this cost: leave the canvas outside a region, where a tagged
`content()` element reserves the room of its widest epoch; or give the region a `height`,
which skips the measuring and keeps the reflow. The same deck then took 2.0 s rather than 4.9 s.

**A body full of `#place` calls costs only on a slide that pans.**
The [automatic canvas](viewport.md#how-large-the-canvas-is) is the union of the body
and everything placed on it,
and Animo computes it by measuring every placement in the body.
That is the one part of laying out a slide whose cost grows with how much the body draws,
and a scatter of data points written as one `#place` can therefore cause performance issues.
Animo computes the union only on a slide whose timeline holds a `pan`,
because `pan` is the only thing that reads the canvas
and the viewport clips whatever falls outside it in every output type.
A slide that does not pan is drawn identically whatever canvas it is given,
so it pays nothing.

Measured on one slide of 10 000 placements over 20 states,
as a static presentation, with typst 0.15.0:

| Slide                              |   Time | Peak memory |
| ---------------------------------- | -----: | ----------: |
| no `pan` in the timeline           | 3.39 s |      767 MB |
| a `pan` in the timeline            | 4.26 s |      950 MB |
| a `pan`, and an explicit `canvas:` | 3.43 s |      766 MB |
| the same marks as one `image`      | 0.94 s |      113 MB |

**State the `canvas:` of a placement-heavy slide that pans.**
A stated canvas leaves Animo nothing to compute,
so the slide pays what a slide that does not pan pays.
The size is yours to get right, and
[How Large the Canvas Is](viewport.md#how-large-the-canvas-is) says what Animo would have
counted.

**Draw many small marks as one image rather than as one `#place` each.**
Ten thousand placements are ten thousand elements for typst to lay out,
whichever canvas they end up on.
That cost is in every row of the table above, and no canvas rule reaches it.
An SVG built as a string and handed to `image` is a single element:

```typst
#let scatter(points) = {
  let marks = points.map(((x, y)) => {
    "<circle cx=\"" + str(x) + "\" cy=\"" + str(y) + "\" r=\"0.5\" fill=\"blue\"/>"
  })
  image(
    bytes(
      "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 150 150\">"
        + marks.join("")
        + "</svg>",
    ),
    format: "svg",
    width: 15cm,
  )
}

#slide[#scatter(csv("points.csv", row-type: dictionary).map(row => (
  float(row.x),
  float(row.y),
)))]
```

The mapping from data coordinates to the `viewBox` is yours to write,
where `#place` resolves typst lengths for you.
In exchange the marks become one element,
which is what the last row of the table above measures.

**Continuous subslides are nearly free in HTML, but not in the paged outputs.**
The static presentation renders one page per state, so eight continuous subslides on a slide
are eight pages there and one rendering in the browser.
That is a reason to use `handout: false` where it applies, not to avoid subslides.

## What a Content Layer Costs

A `background:` or an `overlay:` that is content is one more inline SVG per slide.
A color is one CSS declaration, with no measurable cost.

Measured on the controlled deck of twelve slides, with an overlay of one line of 9 pt text
and a rule, which is typical of a running title or a talk name:
**19.4 KiB per slide raw and 5.0 to 5.1 KiB compressed, the same at one epoch and at four**,
and under 1 ms of compile time per slide,
which is below what this benchmark resolves.

Unlike a region, a layer costs page weight rather than seconds.
That weight is the weight of what the layer holds,
so a full-page image in a background costs the weight of that image, once per slide.
Use a color where a color suffices.

## What a Number Costs

A [`per-subslide`](numbering.md) holds one rendering per subslide, of which the browser
shows one, so `per-subslide` is the only construct whose cost grows with a slide's *states*.

Measured on the controlled deck at its realistic point, twelve slides of seven subslides
over three epochs, with a slide number and a subslide number in the overlay:

| What         | Without a number | With a number | Growth |
| ------------ | ---------------- | ------------- | ------ |
| HTML page    | 1927 KiB         | 2048 KiB      | 6%     |
| gzipped      | 300 KiB          | 326 KiB       | 8%     |
| compile time | 0.39 s           | 0.42 s        | 6%     |

Put the number in the **overlay** and not in the body.
An overlay is one rendering per slide where a region is one rendering per epoch,
so the same stack in a region is its epoch count times the numbers above.

## What a Transition Costs in the Browser

A [morph](morphs.md) costs nothing at compile time,
because the browser matches the two versions of a region when the step runs,
and a crossfade costs nothing there either.
Their cost is in the browser, at the key press and in the frames of the motion,
and it grows with the number of letters and shapes that move or fade.

Measured with `benchmarks/morph.py` on a slide whose paragraph reflows behind a clause
inserted at its start, so that nearly every letter moves,
on the same paragraph crossfaded with the clause at its start and at its end,
and on a slide whose cetz plot of 1000 equal marks changes its axis range,
so that every mark moves,
in chromium 153 and firefox 155 at a window of 1280 by 720 pixels,
on an Intel Core i7-4790 in October 2026:

| Step                                             | Animations | Key press, chromium and firefox | Frame, chromium and firefox |
| ------------------------------------------------ | ---------- | ------------------------------- | --------------------------- |
| morph of 464 letters                             | 473        | 40 ms and 53 ms                 | 17 ms and 17 ms             |
| morph of 2827 letters                            | 2845       | 168 ms and 231 ms               | 56 ms and 16 ms             |
| crossfade of 2827 letters, every line changes    | 198        | 47 ms and 78 ms                 | 17 ms and 17 ms             |
| crossfade of 2827 letters, the last line changes | 18         | 47 ms and 80 ms                 | 17 ms and 17 ms             |
| morph of 1000 marks                              | 1005       | 70 ms and 120 ms                | 30 ms and 17 ms             |

The frame is the median interval between two frames during the motion,
so about 17 ms is the full rate of the display.
Firefox reports whole milliseconds, which is 16 or 17 ms at that rate.
A paragraph of a few hundred letters therefore morphs smoothly in both engines,
and a slide of several thousand moving letters moves at about 18 frames a second in chromium.

A transition draws the ink that both versions of a region share once:
a morph moves one copy of each letter it matches,
and a crossfade shows the unchanged letters of the region once, where they are.
A crossfade therefore starts one animation per line it fades rather than one per letter,
and its key press is spent mostly on finding the letters that did not change.

**A blend on a region is slow in firefox.**
Two versions of a region could also be summed with `mix-blend-mode: plus-lighter`,
which slide crossfades use.
`benchmarks/morph.py` measures every step above a second time under a stylesheet that blends
the region's renderings and isolates their container.
In firefox 155, that stylesheet takes the frame of the morph of 2827 letters from 16 ms to
80 ms, the frame of the crossfade from 17 ms to 50 ms when every line changes
and to 33 ms when the last line changes,
and the frame of the plot from 17 ms to 24 ms, while chromium 153 draws the same frames
either way.
A browser test cannot hold an engine to such a number reliably,
so this measurement lives here rather than among the probes of *Findings*.
Animo therefore hands a region over with opacity alone.
The version of the region drawn below the other stays opaque, the one above fades in or out,
and the ink the two share is drawn once.

Matching the letters is the smaller part.
The diff of two lists of 3000 letters takes about 10 ms at 400 differences,
which is the bound above which a region's letters are crossfaded instead,
and about 50 to 60 ms at 1600.

A shape morph adds the alignment of its two outlines to the key press,
which `benchmarks/morph.py` measures on two closed outlines that share no vertex.
The alignment takes 4 ms in both engines for 100 segments each,
and 8 ms in chromium and 11 ms in firefox for 1000 segments each.
A tag holds one shape morph, so a step pays this once per tag that changes its shape.

## Page Weight

The HTML deck is one self-contained file: a stylesheet, a runtime, and one inline SVG per
slide, holding the body once and one rendering per epoch of every region whose content
changes.
The file grows with epochs and with the size of the regions that change, and not with states.

The tour is 1.57 MB, which gzip takes to **312 KiB**, a factor of five.
Every extra epoch on a slide adds about 19 KiB, or half a KiB once compressed,
so a deck twice the size of the tour arrives in about 0.6 MB.

**Serve the file with compression.**
Every static host and every HTTP server does this by default,
and it is the difference between 312 KiB and one and a half megabytes.
The uncompressed figure matters only for memory in the browser.

About half of the page is glyph definitions,
and Animo lays every rendering of a slide out in one frame
so that the renderings of a slide share one set of them.

## Where These Numbers Come From

[`benchmarks/`](https://github.com/reproducible-reporting/animo/tree/main/benchmarks)
holds three decks.
The tour is the realistic one and shows what an author waits for.
`scaling.typ` is the controlled one: it holds everything constant except one axis,
so that each term above is the difference between two runs rather than an estimate.
Every variant is also compiled with the timeline removed and Animo out of the way,
which is the plain-typst floor the factors divide by.
`placements.typ` is the slide of ten thousand marks the table of placements is measured on,
in the four shapes that table compares.
It is the one deck whose peak memory is recorded beside its seconds.

The rendering counts are asserted rather than measured, in the test suite,
so a change that made Animo render more fails a test rather than a benchmark.
