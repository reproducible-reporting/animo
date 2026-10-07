# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""Tier 3: the effects of a step, planned and applied, on a page with no deck in it.

The runtime is loaded as a classic script without `boot.js`, so its functions are globals of
the page and nothing is shown, and each test hands them elements of its own.
That reaches what a deck cannot show yet:
a property no primitive animates, a transition no deck names,
and the order of the two phases of a step.
"""

import pytest
from harness import ROOT
from test_runtime_files import joined

# The runtime without the file that boots it, joined as `deck.typ` joins it.
ENGINE = "\n".join(
    (ROOT / "src" / "js" / f"{name}.js").read_text() for name in joined() if name != "boot"
)

# How long an effect of these tests takes, in milliseconds, and how it moves.
# Linear, so that the moment sampled is the fraction of the effect it looks like.
TIMING = "{ duration: 1000, easing: 'linear', fill: 'none' }"


@pytest.fixture
def engine(page):
    """A page holding one SVG rectangle and the runtime, which shows nothing by itself."""
    page.set_content(
        "<!DOCTYPE html><html><body>"
        '<div class="animo-deck" data-animo-config=\'{"probe": [1, 2]}\'></div>'
        '<svg width="100" height="100"><rect id="r" width="100" height="100" '
        'style="fill: rgb(255, 0, 0); clip-path: inset(0%)"/></svg>'
        "</body></html>"
    )
    page.add_script_tag(content=ENGINE)
    return page


def channels(color: str) -> list[int]:
    """The channels of a computed `rgb(..)` colour."""
    return [int(part) for part in color.removeprefix("rgb(").removesuffix(")").split(",")]


def test_a_property_outside_the_table_is_read_as_the_engine_reports_it(engine):
    """A transition can animate a property the effects file does not know."""
    shown = engine.evaluate(
        "() => showing(document.getElementById('r'), ['fill', 'clip-path', 'translate'])"
    )
    assert channels(shown["fill"]) == [255, 0, 0]
    assert shown["clip-path"] == "inset(0%)"
    # A property in the table reads as its value at rest rather than as the engine's keyword.
    assert shown["translate"] == "0px 0px"


def test_an_effect_animates_a_property_outside_the_table(engine):
    """`fill` and `clip-path` move with the code that moves `opacity`, unchanged.

    Both are timed alike, so they are one animation, and the one animation is sampled
    halfway, which is where a keyframe that names its property wrongly shows nothing.
    """
    found = engine.evaluate(
        f"""() => {{
            const rect = document.getElementById('r');
            const effects = new Map();
            const to = {{ fill: 'rgb(0, 0, 255)', 'clip-path': 'inset(20%)' }};
            plan(effects, rect, to, {{ fill: {TIMING}, 'clip-path': {TIMING} }});
            apply(effects);
            const animations = rect.getAnimations();
            for (const animation of animations) {{
                animation.pause();
                animation.currentTime = 500;
            }}
            const computed = getComputedStyle(rect);
            return {{
                count: animations.length,
                id: animations[0].id,
                fill: computed.fill,
                clip: computed.clipPath,
                written: [rect.style.fill, rect.style.clipPath],
            }};
        }}"""
    )
    assert found["count"] == 1
    assert found["id"] == "animo"
    assert channels(found["fill"]) == pytest.approx([128, 0, 128], abs=2)
    assert found["clip"] == "inset(10%)"
    assert found["written"] == ["rgb(0, 0, 255)", "inset(20%)"]


def test_planning_writes_nothing(engine):
    """Every read of a step comes before every write of it.

    So a transition that reads geometry while the step is planned reads the page as it was
    before the step, whatever was planned ahead of it.
    """
    found = engine.evaluate(
        f"""() => {{
            const rect = document.getElementById('r');
            const effects = new Map();
            plan(effects, rect, {{ translate: '50px 10px' }});
            plan(effects, rect, {{ opacity: '0' }}, {{ opacity: {TIMING} }});
            const planned = [rect.style.translate, rect.style.opacity, rect.getAnimations().length];
            apply(effects);
            return {{
                planned,
                applied: [rect.style.translate, rect.style.opacity, rect.getAnimations().length],
            }};
        }}"""
    )
    assert found["planned"] == ["", "", 0]
    assert found["applied"] == ["50px 10px", "0", 1]


def test_a_later_effect_on_an_element_and_property_replaces_the_earlier(engine):
    """Which is how a transition puts what it carries in place of the state at rest."""
    found = engine.evaluate(
        f"""() => {{
            const rect = document.getElementById('r');
            const effects = new Map();
            plan(effects, rect, {{ opacity: '0' }});
            plan(effects, rect, {{ opacity: '0.5' }}, {{ opacity: {TIMING} }});
            apply(effects);
            return [rect.style.opacity, rect.getAnimations().length];
        }}"""
    )
    assert found == ["0.5", 1]


# A slide of two epoch renderings, each holding the groups of two regions, as `readSlide`
# would build it from a deck, for the epoch boundary below.
SLIDE = """
const svg = document.querySelector('svg');
const renderings = [0, 1].map(() => {
    const rendering = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    const regions = ['a', 'b'].map((name) => {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.dataset.typstLabel = name;
        rendering.append(group);
        return group;
    });
    svg.append(rendering);
    return { element: rendering, regions };
});
const slide = {
    renderings,
    states: [{ epoch: 0 }, { epoch: 1 }],
    epochs: [[], [
        { group: 'a', transition: 'probe', args: { side: 'left' } },
        { group: 'b' },
    ]],
    morphed: new Map(),
};
"""


def test_each_region_of_a_boundary_is_carried_by_the_transition_it_names(engine):
    """One boundary may carry one region with one transition and another with another.

    The transition named `probe` exists only on this page.
    It is handed the record of its own region, `args` included, and plans nothing, so that
    region keeps its state at rest.
    The region that names no transition is crossfaded.
    """
    found = engine.evaluate(
        f"""() => {{
            {SLIDE}
            const seen = [];
            transitions.probe = (effects, slide, {{ regions }}) => seen.push(regions);
            const effects = new Map();
            planEpoch(effects, slide, 1, 0, {TIMING}, null);
            const timed = (rendering, region) =>
                effects.get(renderings[rendering].regions[region]).get('opacity').timing !== null;
            return {{
                seen,
                a: [timed(0, 0), timed(1, 0)],
                b: [timed(0, 1), timed(1, 1)],
            }};
        }}"""
    )
    assert found["seen"] == [[{"group": "a", "transition": "probe", "args": {"side": "left"}}]]
    assert found["a"] == [False, False]
    assert found["b"] == [True, True]


def test_a_region_that_names_a_transition_the_runtime_lacks_is_crossfaded(engine):
    """Typst refuses an unknown name, so this is a page edited by hand, and it still works."""
    found = engine.evaluate(
        f"""() => {{
            {SLIDE}
            slide.epochs[1][0].transition = 'nothing-by-this-name';
            const effects = new Map();
            planEpoch(effects, slide, 1, 0, {TIMING}, null);
            return effects.get(renderings[1].regions[0]).get('opacity').timing !== null;
        }}"""
    )
    assert found is True


def test_the_runtime_reads_the_settings_of_the_deck_once(engine):
    """The settings travel as one JSON attribute on the deck element."""
    assert engine.evaluate("() => config") == {"probe": [1, 2]}


def test_a_deck_element_without_settings_has_none(page):
    """A page with no deck element, or an empty attribute, reads as an empty object."""
    page.set_content("<!DOCTYPE html><html><body></body></html>")
    page.add_script_tag(content=ENGINE)
    assert page.evaluate("() => config") == {}
