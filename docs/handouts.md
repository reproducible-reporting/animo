---
description: >-
  Which states of a slide the static handouts keep,
  why a slide may need a page for a state other than its final state,
  and how a deck marks the states that the handout keeps.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: Apache-2.0
-->

# Handouts

The example deck for this page is
[`handouts.typ`](https://github.com/reproducible-reporting/animo/blob/main/examples/handouts.typ)
([HTML](https://reproducible-reporting.github.io/animo/examples/handouts.html){ target="\_blank" rel="noopener" },
[PDF presentation](https://reproducible-reporting.github.io/animo/examples/handouts-presentation.pdf),
[PDF handouts](https://reproducible-reporting.github.io/animo/examples/handouts-handouts.pdf)).
It shows the default handout page of a slide (its final state),
slides that need extra handout pages because some content is not visible in their final state,
and a slide left out of the handout.

By default, the static handouts have **one page per slide**,
and that page shows the final state of the slide.
When the timeline of a slide only adds content, this one page is enough,
because the final state shows everything the audience saw.
When the timeline takes content away, that content is not visible in the final state.
The handout then shows that content only if it has an extra page
for an earlier state in which the content is visible.

## The `handout` Flag

The `handout:` argument of `init` and `sub` decides whether the handout has a page for a state.
It takes three values:

- `handout: auto`, the default, gives a page to the state only when it is the **final state**.
- `handout: true` gives a page to the state, also when it is not the final state.
- `handout: false` gives no page to the state, also when it is the final state.

Each `sub` call creates one subslide,
which is the state of the slide after the operations of that call are applied.
The `handout:` argument of a `sub` call applies to the subslide that this call creates.
The initial state of a slide is not created by a `sub` call,
so its `handout:` argument is passed to `init`:

```typst
#slide(animation: {
  import anim: *
  init(handout: true)
  sub(handout: true, replace("step")[$(a + b)(a + b)$])
  sub(replace("step")[$a^2 + 2 a b + b^2$])
})[
  #tag("step", wrap: block)[$(a + b)^2$]
]
```

The handout has three pages for this slide, one for each form of the expression.

To keep content that a `sub` call takes away, set `handout: true` on the previous `sub` call,
because the subslide that the previous call creates still shows the content.
When the first `sub` call takes the content away, set `handout: true` on `init` instead,
because the content is then visible only in the initial state.

## Content Missing from the Final State

Content that an earlier state shows can be missing from the final state
when the timeline uses one of these primitives:

| Primitive           | Content missing from the final state                            |
| ------------------- | --------------------------------------------------------------- |
| `hide`              | the content it hides, whose room stays empty                    |
| `remove`, `replace` | the content they remove or replace, which is no longer laid out |
| `pan`               | everything that lies outside the viewport after the pan         |
| `move`, `scale`     | the content they carry beyond the edge of the viewport          |

A handout page shows the same part of the canvas as the static presentation shows for that state,
because Animo clips both to the viewport.
When a slide starts with an overview and then pans away without returning to the overview,
`init(handout: true)` adds a page with the overview to the handout.

Animo cannot warn you about a slide whose content is missing from the handout,
because typst offers no way for a package to emit a warning.

## Content Filled In by the Timeline

The initial state of a slide can also need a handout page.
Some slides start with hidden or removed content and show it later with `reveal` or `reset`.
At the end of the timeline, that content is visible,
so the default page does not show the slide as it started.
An example is an exercise with a blank in a sentence, which a later subslide fills in.
The blank is the [room reserved](structural.md#box-reserved-by-a-changing-tag)
by a tag whose content changes.
`init(handout: true)` adds a page for the initial state of such a slide.

Such a slide can also set `handout: false` on its last `sub` call,
which removes the page for the final state.
A reader of the handout then sees the exercise without its solution:

```typst
#slide(animation: {
  import anim: *
  init(handout: true)
  sub(handout: false, reset("blank"))
})[
  The timeline of a slide is an #tag("blank")[argument] of `#slide`.
]
```

## Slides Left Out of the Handout

A slide without `sub` calls has only one state, which is both its initial and its final state.
`init(handout: false)` therefore leaves that slide out of the handout.
This is useful for a slide that has no purpose on paper,
such as a slide that announces a live demonstration.

When no state in the whole deck has a handout page, the handout would have no pages at all.
Animo stops the compilation with an error in that case,
because typst would otherwise produce a single blank page.

## Numbers in a Handout

A handout page shows the number of the **subslide on that page**,
not the position of the page within the handout.
For example, when the handout has a page for the third of three subslides of a slide,
that page shows "3 of 3", even if it is the seventh page of the handout.
A reader who wrote down a number during the talk can then find the page with that number.
See [Numbering](numbering.md) for the functions that write such a number.

## Marking the Subslides a Handout Keeps

The [subslide info](reference.md#per-subslide) has a `handout` key,
which is `true` when the handout has a page for that subslide.
The `handout:` arguments of `init` and `sub` decide the value of this key.
The `handout` key has the same value in all three output types,
so a presentation can mark the subslides that the audience will also find in the handout.
In the handout itself, every page would carry the mark,
so the example below uses [`output-type()`](outputs.md#content-per-output-type)
to leave the mark out of the handout:

```typst
#let handout-mark = place(top + right, per-subslide(it => context {
  if it.handout and output-type() != "handout" { circle(radius: 3pt, fill: gray) }
}))
```

Put a mark like this in the [overlay](slides.md#backgrounds-and-overlays) of a wrapper
around `#slide`.
The example deck does this with a badge beside the state number.
