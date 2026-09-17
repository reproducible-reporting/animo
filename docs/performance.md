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

The example deck for this page is
[`tour.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/tour.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/tour.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/tour-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/tour-handouts.pdf)).
It is the deck on which the numbers below were measured.

The cost of Animo is that it asks typst to lay out a slide more than once.

In summary, an ordinary deck costs about twice as much as a plain typst deck,
and the live preview loop is an order of magnitude cheaper than a cold compile,
so a deck remains comfortable to write.
The most expensive construct is a
[cetz canvas inside a region](regions.md#where-a-region-cannot-go).

## What Is Rendered, and How Often

| Output type         | Renderings per slide                                  |
| ------------------- | ----------------------------------------------------- |
| HTML presentation   | one per [epoch](structural.md#epochs)                 |
| Static presentation | one per state                                         |
| Static handouts     | one per state whose `handout` flag resolved to `true` |

A `background:` or an `overlay:` that is content is rendered **once** beside these,
whatever the output type and however many epochs the slide has.

On top of that, **every region lays its body out once per epoch to measure it**,
so that it can reserve the largest.
A region with an explicit `height` measures nothing,
and a slide with one epoch measures nothing either.

Two limits on this count keep the cost affordable:

- it is not per state. A run of `reveal`, `move` and `scale` operations shares one rendering,
  so a slide with eight continuous subslides and no content change is exactly as cheap in the
  browser as a slide with none;
- it is not a product over tags. Regions nest as fixed footprints rather than as states,
  so four tags over three epochs cost three renderings each and not eighty-one.

## The Measured Numbers

[`examples/tour.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/tour.typ)
is the deck these numbers were measured on.
It stood at 16 slides, 48 states and 20 epoch renderings when they were taken,
on a 12th Gen Intel Core i7-1260P with typst 0.15.1 in September 2026.

| What                         | Measured                 |
| ---------------------------- | ------------------------ |
| HTML presentation            | 0.37 s                   |
| Static presentation          | 0.44 s                   |
| Static handout               | 0.34 s                   |
| HTML page                    | 1.37 MB, 262 KiB gzipped |
| One edit under `typst watch` | 36 ms                    |

The terms behind those totals, each measured as the difference between two decks that
differ in one thing only:

| Term                                    | Cost                              |
| --------------------------------------- | --------------------------------- |
| one more epoch on one slide, in HTML    | 5 ms, 35 KiB raw, 3 KiB gzipped   |
| one region measuring one epoch of prose | 1.3 ms                            |
| one region measuring one epoch of cetz  | 8.4 ms                            |
| one content layer on one slide, in HTML | 19 KiB raw, 5 KiB gzipped, 0.8 ms |

And the same content laid out by plain typst, one page per slide, as a factor:

| Deck                                                 | Against plain typst |
| ---------------------------------------------------- | ------------------- |
| no structural subslides                              | 2.1                 |
| four continuous subslides per slide                  | 2.6                 |
| two to eight epochs per slide                        | 2.4 to 2.8          |
| two regions, three epochs, four continuous subslides | 5.9                 |
| two regions of cetz canvas, four epochs              | 13.8                |

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
On the tour, an edit to one slide recompiles in **36 ms** against **0.41 s** cold,
and on a deck with regions, epochs and continuous subslides throughout,
in 59 ms against 0.69 s.

This is the number that decides whether a deck is comfortable to write.
Keep the preview running while you write:

```bash
typst watch --format html --features html --open talk.typ talk.html
```

## What Costs, and What to Do About It

**A structural operation costs a whole rendering, a continuous one costs none.**
`replace`, `remove`, `apply` and `reset` each start a new epoch, which is a fresh layout of
the slide and a fresh rendering in the page.
`reveal`, `hide`, `move` and `scale` are applied by the browser to a rendering that already
exists. So where either would do, prefer the continuous one:

```typst
sub(hide("caveat"))    // no extra rendering
sub(remove("caveat"))  // a whole rendering, and a crossfade
```

Outside a region the two even look the same, because the
[tag's own box](structural.md#a-changing-tag-keeps-its-own-box) reserves its largest state
either way. There, `remove` costs a rendering without any benefit.

**A region measures every epoch, so regions and epochs multiply.**
Two regions over four epochs is eight measurements per rendering of the slide, not two.
It is linear in each, which keeps it affordable, but the cost is the product of the two.

**Give a region a `height` when you know it.**
A region with an explicit height measures nothing at all.
On a deck of twelve slides with two regions over four epochs,
that is 0.82 s against 0.43 s for the HTML output: nearly half the cost of the deck.
The drawback is that a state taller than the height is clipped.

**A cetz canvas inside a region is the expensive case.**
The region lays the canvas out afresh for every epoch, and cetz layout is not cheap:
8.4 ms per measurement against 1.3 ms for the same shape holding prose, six times more.
A deck of twelve such slides over four epochs took 4.3 s to compile against 0.08 s for the
same drawings as plain typst.
There are two ways to avoid this cost: leave the canvas outside a region, where a tagged
`content()` element reserves the room of its widest epoch; or give the region a `height`,
which skips the measuring and keeps the reflow. The same deck then took 1.1 s rather than 4.3 s.

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
as a static presentation, with typst 0.15.1:

| Slide                              |   Time | Peak memory |
| ---------------------------------- | -----: | ----------: |
| no `pan` in the timeline           | 1.30 s |      992 MB |
| a `pan` in the timeline            | 1.75 s |     1202 MB |
| a `pan`, and an explicit `canvas:` | 1.37 s |      991 MB |
| the same marks as one `image`      | 0.57 s |      128 MB |

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
A colour is not: it is one CSS declaration, with no measurable cost.

Measured on the controlled deck of twelve slides, with an overlay of one line of 9 pt text
and a rule, which is typical of a running title or a talk name:
**19.4 KiB per slide raw and 5.1 KiB compressed, the same at one epoch and at four**,
and 0.8 ms of compile time per slide, which is the smallest difference this benchmark
resolves.

A layer costs page weight rather than seconds, unlike a region,
and its cost is the weight of what it holds:
a full-page image in a background costs the weight of that image, once per slide.
Use a colour where a colour suffices.

## What a Number Costs

A [`per-subslide`](numbering.md) holds one rendering per subslide, of which the browser
shows one, so it is the only construct whose cost grows with a slide's *states*.

Measured on the controlled deck at its realistic point, twelve slides of seven subslides
over three epochs, with a slide number and a subslide number in the overlay:

| What         | Without a number | With a number | Growth |
| ------------ | ---------------- | ------------- | ------ |
| HTML page    | 2393 KiB         | 2515 KiB      | 5%     |
| gzipped      | 341 KiB          | 366 KiB       | 7%     |
| compile time | 0.29 s           | 0.31 s        | 5%     |

Put it in the **overlay** and not in the body.
An overlay is one rendering per slide where the body is one rendering per epoch,
so the same stack in the body is its epoch count times the numbers above.

## Page Weight

The HTML deck is one self-contained file: a stylesheet, a runtime, and one inline SVG per
slide, holding one rendering per epoch. It grows with epochs and not with states.

The tour is 1.37 MB, which gzip takes to **262 KiB**, a factor of five.
Every extra epoch on a slide adds about 35 KiB, or 3 KiB once compressed,
so a deck twice the size of the tour arrives in about half a megabyte.

**Serve the file with compression.**
Every static host and every HTTP server does this by default,
and it is the difference between 262 KiB and a megabyte.
The uncompressed figure matters only for memory in the browser.

Most of the page is glyph definitions, and Animo lays every epoch of a slide out in one
frame so that the renderings of a slide share one set of them.
The saving grows with the epochs a slide has: none at one epoch, 36% of the
compressed page at two, and 66% at eight.

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
