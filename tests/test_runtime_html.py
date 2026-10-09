# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the controller of the runtime, its events, and what input reaches.

The runtime is one script made of several files, so the first test loads a deck and asks the
console whether the files were joined in an order that works.
The rest is what the controller promises to the code around it:
the events that say the position changed and what the page looks like when they arrive,
the rule that only the current slide takes the pointer,
and the two places where the runtime has to leave something alone,
which are a control and an animation that the runtime did not start.
"""

import pytest
from decks import deck
from harness import Deck, TypstRunner

# Records every event of the runtime, from before the runtime runs.
#
# A listener on the document rather than on the root element, because the document exists
# when an init script runs and the events bubble up to it.
# Each record carries what the page looks like at the moment the event arrives, which is
# what a listener of `animo:position` is promised to see written already.
RECORDER = """
{
    window.animoEvents = [];
    for (const type of ["animo:mode", "animo:leave", "animo:enter", "animo:position"]) {
        document.addEventListener(type, (event) => {
            const current = document.querySelector("[data-animo-current]");
            window.animoEvents.push({
                type,
                detail: event.detail,
                hash: location.hash,
                attribute: document.documentElement.dataset.animo ?? null,
                current: current === null ? null : current.dataset.animoSlide,
            });
        });
    }
}
"""

THREE = deck("slide[One]", "slide[Two]", "slide[Three]")


def recorded(page) -> list[dict]:
    """The events recorded so far."""
    return page.evaluate("() => window.animoEvents")


def forget(page) -> None:
    """Drop the events recorded so far, so that a test reads only what its next action causes."""
    page.evaluate("() => { window.animoEvents.length = 0 }")


def summary(events: list[dict]) -> list[tuple]:
    """The type of each event, and its detail where that is what a test asserts."""
    return [(event["type"].removeprefix("animo:"), event["detail"]) for event in events]


def at(slide: int, state: int) -> dict:
    """A position, as an event detail spells it."""
    return {"slide": slide, "state": state}


# The files of the runtime.


def test_the_page_loads_and_runs_without_a_script_error(page, deck_at, typst: TypstRunner):
    """The runtime is several files in one scope, and a file that needs another too early throws.

    A top level `const` is initialised when its file is reached, so an order that lets a
    file use one defined later fails at load and leaves a deck that shows nothing.
    Nothing on the console, a deck that reached its first position and a deck that steps
    are what an order that works looks like.
    """
    problems = []
    page.on("pageerror", lambda error: problems.append(str(error)))
    page.on(
        "console",
        lambda message: problems.append(message.text) if message.type == "error" else None,
    )
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    assert presentation.position == (1, 0)
    presentation.press("ArrowRight").goto(3).press("ArrowLeft")
    assert presentation.position == (2, 0)
    assert problems == []


def test_the_root_element_names_the_mode(deck_at, typst: TypstRunner):
    """Beside the position and the pause, so that a stylesheet can depend on the mode."""
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    assert presentation.page.evaluate("() => document.documentElement.dataset.animoMode") == (
        "present"
    )


# The events.


def test_the_first_position_enters_its_slide_and_leaves_none(page, deck_at, typst: TypstRunner):
    """What a listener sees of a page that has just loaded, a mode first and a position last."""
    page.add_init_script(RECORDER)
    deck_at(typst.html(THREE, name="three.html"))
    assert summary(recorded(page)) == [
        ("mode", {"from": None, "to": "present"}),
        ("enter", {"slide": 1}),
        ("position", {"from": None, "to": at(1, 0), "animated": False}),
    ]


def test_a_step_inside_a_slide_is_a_position_and_nothing_else(page, deck_at, typst: TypstRunner):
    """No slide is entered or left, so neither event is sent."""
    page.add_init_script(RECORDER)
    source = deck(
        'slide(animation: { import anim: *\n  sub(hide("a")) })[#tag("a")[Text]]',
        "slide[Two]",
    )
    presentation: Deck = deck_at(typst.html(source, name="inside.html"))
    forget(page)
    presentation.press("ArrowRight")
    assert summary(recorded(page)) == [
        ("position", {"from": at(1, 0), "to": at(1, 1), "animated": True}),
    ]


def test_a_step_across_a_boundary_leaves_one_slide_and_enters_the_next(
    page, deck_at, typst: TypstRunner
):
    """Leave comes first, then enter, then the position, in both directions.

    The boundary is crossed in the same step in both, so `animated` is true in both.
    """
    page.add_init_script(RECORDER)
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    forget(page)
    presentation.press("ArrowRight")
    assert summary(recorded(page)) == [
        ("leave", {"slide": 1}),
        ("enter", {"slide": 2}),
        ("position", {"from": at(1, 0), "to": at(2, 0), "animated": True}),
    ]
    forget(page)
    presentation.press("ArrowLeft")
    assert summary(recorded(page)) == [
        ("leave", {"slide": 2}),
        ("enter", {"slide": 1}),
        ("position", {"from": at(2, 0), "to": at(1, 0), "animated": True}),
    ]


def test_a_cut_is_a_step_that_is_not_animated(page, deck_at, typst: TypstRunner):
    """`animated` says that motion was let run, and a cut lets none run."""
    page.add_init_script(RECORDER)
    source = deck("slide[One]", "slide(animation: anim.init(duration: 0))[Two]")
    presentation: Deck = deck_at(typst.html(source, name="cut.html"))
    forget(page)
    presentation.press("ArrowRight")
    events = recorded(page)
    assert [event["type"] for event in events] == [
        "animo:leave",
        "animo:enter",
        "animo:position",
    ]
    assert events[-1]["detail"]["animated"] is False


def test_a_deep_link_leaves_and_enters_without_animating(page, deck_at, typst: TypstRunner):
    """A jump lands rather than arrives, over as many slides as it likes."""
    page.add_init_script(RECORDER)
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    forget(page)
    presentation.goto(3)
    assert summary(recorded(page)) == [
        ("leave", {"slide": 1}),
        ("enter", {"slide": 3}),
        ("position", {"from": at(1, 0), "to": at(3, 0), "animated": False}),
    ]


def test_a_join_is_two_positions_with_a_boundary_between(page, timed_deck_at, typst: TypstRunner):
    """A gap of zero carries the deck over on the clock, and each position is announced.

    Firefox runs a timer of zero length during the load of the page and chromium waits for
    the clock to be advanced, so the test reads the events once the clock has been advanced
    and states all of them.
    """
    page.add_init_script(RECORDER)
    source = deck("slide(animation: anim.init(hold: 0))[One]", "slide[Two]")
    presentation: Deck = timed_deck_at(typst.html(source, name="join.html"))
    presentation.run_for(1)
    assert summary(recorded(page)) == [
        ("mode", {"from": None, "to": "present"}),
        ("enter", {"slide": 1}),
        ("position", {"from": None, "to": at(1, 0), "animated": False}),
        ("leave", {"slide": 1}),
        ("enter", {"slide": 2}),
        ("position", {"from": at(1, 0), "to": at(2, 0), "animated": True}),
    ]


def test_a_listener_finds_the_page_already_updated(page, deck_at, typst: TypstRunner):
    """Every event of a step arrives after the DOM and the fragment are written.

    That includes `animo:leave`, which is sent after the step has been made rather than
    before, so a listener of any of them finds the position the step reached.
    """
    page.add_init_script(RECORDER)
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    forget(page)
    presentation.press("ArrowRight")
    events = recorded(page)
    assert len(events) == 3
    for event in events:
        assert event["hash"] == "#2.0"
        assert event["attribute"] == "2.0"
        assert event["current"] == "2"


# Where the pointer goes.


HIT = """() => {
    const hit = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
    return hit.closest("[data-animo-slide]").dataset.animoSlide;
}"""

SLIDES = """() => Object.fromEntries(
    Array.from(document.querySelectorAll("[data-animo-slide]"), (slide) => [
        slide.dataset.animoSlide,
        {
            display: getComputedStyle(slide).display,
            pointerEvents: getComputedStyle(slide).pointerEvents,
            inert: slide.hasAttribute("inert"),
            leaving: slide.hasAttribute("data-animo-leaving"),
        },
    ])
)"""


def test_the_slide_being_left_takes_no_pointer_events(page, deck_at, typst: TypstRunner):
    """A slide stays laid out for as long as the deck stays put, so that stepping back over
    the boundary needs no layout, and it comes later in the document after a step back.

    It would be on top of the slide being shown, at opacity zero, and take every event that
    a control or a link in that slide should get.
    """
    presentation: Deck = deck_at(typst.html(THREE, name="three.html")).goto(2)
    presentation.press("ArrowLeft")
    presentation.settle()
    slides = page.evaluate(SLIDES)
    assert slides["2"] == {
        "display": "block",
        "pointerEvents": "none",
        "inert": True,
        "leaving": True,
    }, "the slide being left was not left laid out, so this test is not about a slide on top"
    assert slides["1"]["pointerEvents"] == "auto"
    assert page.evaluate(HIT) == "1"
    presentation.press("ArrowRight")
    presentation.settle()
    assert page.evaluate(HIT) == "2"
    slides = page.evaluate(SLIDES)
    assert slides["1"]["inert"] is True
    assert slides["2"]["inert"] is False


def test_no_slide_is_inert_once_the_deck_has_landed(page, deck_at, typst: TypstRunner):
    """A slide is inert while it is on screen only to be crossed from, and no longer."""
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    presentation.press("ArrowRight")
    assert page.evaluate(SLIDES)["1"]["inert"] is True
    presentation.goto(3)
    assert [slide["inert"] for slide in page.evaluate(SLIDES).values()] == [False] * 3


CONTROL = """() => {
    const control = document.createElement("button");
    control.dataset.animoControl = "";
    control.id = "control";
    control.style.cssText = "position: fixed; top: 0; right: 0; z-index: 1";
    control.innerHTML = "<span>control</span>";
    document.querySelector(".animo-deck").append(control);
}"""


def test_an_event_inside_a_control_does_not_step_the_deck(page, deck_at, typst: TypstRunner):
    """A control handles the input it receives, whether the event hits it or one of its children.

    The click on the stage at the end is what shows the same deck does step on an event
    that is not in a control, so the rest is not a deck that ignores everything.
    """
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    page.evaluate(CONTROL)
    page.locator("#control span").click()
    assert presentation.position == (1, 0), "a click on a child of a control stepped the deck"
    page.locator("#control").focus()
    presentation.press("ArrowRight").press("Enter").press(" ")
    assert presentation.position == (1, 0), "a key pressed on a control stepped the deck"
    page.locator(".animo-stage").click()
    assert presentation.position == (2, 0)


# The pause key and animations that are not the runtime's.


SLOW = ":root { --animo-primitive-duration: 1000ms; --animo-easing: linear }"

# A CSS animation and a scripted one, each on an element of the page that the runtime knows
# nothing about, and both far longer than the test.
AUTHOR = """
@keyframes drift { to { opacity: 0.5 } }
#author { animation: drift 100s linear infinite }
"""

ADD_AUTHOR = """() => {
    const element = document.createElement("div");
    element.id = "author";
    document.body.append(element);
    element.animate({ opacity: [1, 0.5] }, { duration: 100000, id: "scripted" });
}"""

PLAY_STATES = """() => document.getAnimations().map(
    (animation) => [animation.id || animation.animationName, animation.playState]
)"""


def play_states(page) -> dict[str, set[str]]:
    """The play states of the animations of the page, by the name each goes by.

    The animations of the runtime go by their `id`,
    and an animation with none goes by the name of its CSS animation.
    """
    found: dict[str, set[str]] = {}
    for name, state in page.evaluate(PLAY_STATES):
        found.setdefault(name, set()).add(state)
    return found


def test_pausing_leaves_a_css_animation_of_the_page_alone(page, deck_at, typst: TypstRunner):
    """The pause key stops the animations the runtime created and no others.

    The runtime recognises the animations it started by the `id` it gives them,
    and the page here holds one made by a stylesheet and one made by a script.
    """
    line = '#tag("a", wrap: block)[A line that starts out hidden.]'
    animation = '{ import anim: *\n  sub(reveal("a"))\n  sub(wait: 10) }'
    source = deck(f"slide(animation: {animation})[\n  {line}\n]")
    presentation: Deck = deck_at(typst.html(source, name="author.html"))
    page.add_style_tag(content=SLOW + AUTHOR)
    page.evaluate(ADD_AUTHOR)
    presentation.press("ArrowRight")
    presentation.press(" ")
    assert presentation.paused
    paused = play_states(page)
    assert "animo" in paused, "the step had already ended when the deck was paused"
    assert paused["animo"] == {"paused"}
    assert paused["drift"] == {"running"}, "pausing stopped a CSS animation of the page"
    assert paused["scripted"] == {"running"}, "pausing stopped a scripted animation of the page"
    presentation.press(" ")
    assert not presentation.paused
    resumed = play_states(page)
    assert "paused" not in resumed.get("animo", set()), "the runtime's animations stayed paused"
    assert resumed["drift"] == {"running"}
    assert resumed["scripted"] == {"running"}


@pytest.mark.parametrize("key", ["ArrowRight", " ", "Enter", "n"])
def test_the_keys_of_the_present_mode_still_step_forward(deck_at, typst: TypstRunner, key):
    """The key sets of the mode are the ones the runtime has always had."""
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    presentation.press(key)
    assert presentation.position == (2, 0)


@pytest.mark.parametrize("key", ["ArrowLeft", "Backspace", "p"])
def test_the_keys_of_the_present_mode_still_step_backward(deck_at, typst: TypstRunner, key):
    """A deck that waits for the presenter has no clock, so these only step."""
    presentation: Deck = deck_at(typst.html(THREE, name="three.html")).goto(2)
    presentation.press(key)
    assert presentation.position == (1, 0)


def test_home_and_end_jump_to_the_ends_of_the_deck(deck_at, typst: TypstRunner):
    """Both land rather than animate, and both are the first and the last position."""
    presentation: Deck = deck_at(typst.html(THREE, name="three.html"))
    presentation.press("End")
    assert presentation.position == (3, 0)
    presentation.press("Home")
    assert presentation.position == (1, 0)
