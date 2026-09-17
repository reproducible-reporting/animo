# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The pytest fixtures of the three tiers, loaded as a plugin by the root `conftest.py`.

Which fixture a test asks for is what says which tier it is in,
so the tier markers are assigned from that rather than written out by hand,
where they would drift.
"""

import os
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from .browser import Deck, open_local
from .raster import PagedRunner
from .references import Reference
from .typst import ROOT, TypstRunner

# The browsers that `setup.sh` downloads.
# The path is exported here as well as in `.envrc`,
# so that the suite is green for a contributor who does not use `direnv`.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".venv" / "playwright"))


# The browser engines the HTML tier runs in.
# Three rendering engines rather than one, because a deck that only works in chromium is
# not a presentation format: the CSS animo emits has to be the CSS all of them agree on.
#
# The two required ones run wherever playwright runs, so a launch failure there is a
# broken bootstrap and an error.
# Playwright ships one webkit build, for ubuntu, and it needs libraries that other
# distributions do not carry, so on those it can only run inside a container.
# Asking every contributor for a container to run the test suite is too much, and so is
# letting a whole engine go untested, so webkit is best effort locally and mandatory in
# continuous integration, which is ubuntu and names all three on the command line.
REQUIRED_ENGINES = ("chromium", "firefox")
OPTIONAL_ENGINES = ("webkit",)
ENGINES = REQUIRED_ENGINES + OPTIONAL_ENGINES


def pytest_addoption(parser):
    """Add the regeneration path of the stored reference images and the engine selection."""
    parser.addoption(
        "--update-references",
        action="store_true",
        default=False,
        help="rewrite every stored reference image from the current rendering",
    )
    parser.addoption(
        "--browser",
        action="append",
        default=[],
        choices=ENGINES,
        metavar="ENGINE",
        help=(
            "run the browser tier in this engine only; repeatable, defaults to all of them. "
            "An engine named here is mandatory: it fails rather than skips when it cannot "
            "launch, which is how continuous integration asks for webkit."
        ),
    )


def pytest_generate_tests(metafunc):
    """Run every test of the browser tier once per selected engine.

    The engine is a fixture rather than a loop inside a test, so that a failure names the
    engine it happened in and `-k firefox` selects one of them.
    It is parametrised here rather than on the fixture itself,
    because only a hook can read `--browser` off the command line.
    """
    if "browser_name" in metafunc.fixturenames:
        selected = metafunc.config.getoption("--browser") or list(ENGINES)
        metafunc.parametrize("browser_name", selected, scope="session")


def pytest_collection_modifyitems(items):
    """Mark every test with the tier it runs in, taken from the fixtures it asks for."""
    for item in items:
        names = set(item.fixturenames)
        for fixture, marker in (
            ("browser", "browser"),
            ("paged", "paged"),
            ("typst", "plan"),
        ):
            if fixture in names:
                item.add_marker(marker)
                break


@pytest.fixture
def scratch(request) -> Path:
    """An empty directory, inside the repository, for a document that a test compiles.

    Typst refuses a source file outside its project root,
    so a generated document cannot live in `tmp_path`.
    It is left behind after the run, because a failing compilation is worth looking at.
    The module is part of the path, because two modules may hold a test of the same name,
    and under `pytest-xdist` those two may run at the same time.
    """
    path = ROOT / "tmp" / "pytest" / request.node.path.stem / request.node.name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


@pytest.fixture
def typst(scratch) -> TypstRunner:
    """Tier 1: compile documents that assert about themselves, and export nothing."""
    return TypstRunner(scratch)


@pytest.fixture
def paged(typst) -> PagedRunner:
    """Tier 2: render the presentation and handout outputs and compare them as arrays."""
    return PagedRunner(typst)


@pytest.fixture
def references(request) -> Reference:
    """The stored reference images of the test module, and the update path.

    They live in a `references/` directory beside the module that uses them,
    so that a test and the pixels it stores are read together.
    """
    directory = Path(request.node.fspath).parent / "references"
    return Reference(directory, request.config.getoption("--update-references"))


@pytest.fixture(scope="session")
def playwright_instance():
    """The `playwright` driver process, started once for the whole run."""
    with sync_playwright() as instance:
        yield instance


@pytest.fixture(scope="session")
def browser(playwright_instance, browser_name, request):
    """Tier 3: one of the bundled browsers, launched once per engine for the whole run.

    An engine that has to run and cannot fails rather than skips: `./setup.sh` downloads
    them all, and a suite that is green because its browser tier never ran is the failure
    that rule hides.
    An optional engine that this machine cannot launch skips instead, loudly, naming what
    the platform is missing, because the alternative is asking every contributor for a
    container. Continuous integration names it on the command line, which makes it
    required there, so the engine is never skipped everywhere at once.
    """
    try:
        instance = getattr(playwright_instance, browser_name).launch()
    except PlaywrightError as exc:
        if browser_name in REQUIRED_ENGINES or browser_name in request.config.getoption(
            "--browser"
        ):
            # `./setup.sh` downloads an optional engine only where it has a build,
            # so pointing at it as the remedy would be wrong on the platforms that skip.
            remedy = (
                "`./setup.sh` installs it"
                if browser_name in REQUIRED_ENGINES
                else "`./setup.sh` downloads this engine only where it has a build"
            )
            raise RuntimeError(
                f"{browser_name} could not be launched. {remedy}, and "
                f"`playwright install {browser_name}` with PLAYWRIGHT_BROWSERS_PATH "
                f"pointing at .venv/playwright does it unconditionally.\n{exc}"
            ) from exc
        # Short on purpose: this reason is printed once per test in the tier.
        # `--browser webkit` is the way to see playwright's own diagnosis, because naming
        # the engine makes it required and the branch above reports the failure in full.
        pytest.skip(
            f"{browser_name} cannot be launched on this machine; "
            f"continuous integration covers it. `pytest --browser {browser_name}` says why."
        )
    yield instance
    instance.close()


@pytest.fixture
def page(browser):
    """A fresh browser page, in a context of its own, for one test."""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def open_page(page):
    """Open a file from the working tree in the browser page."""

    def opener(path: Path):
        return open_local(page, path)

    return opener


@pytest.fixture
def deck_at(page):
    """Open a compiled animo presentation and address its subslides by URL."""

    def opener(path: Path) -> Deck:
        open_local(page, path)
        return Deck(page)

    return opener


@pytest.fixture
def timed_deck_at(page):
    """Open a compiled animo presentation with the page's clock stopped.

    A `wait:` is the one timer the runtime sets, and a `setTimeout` is exactly what the
    animation harness cannot scrub, so a test states how much time passes instead of
    racing it: `Deck.run_for` fires the timers that are due and nothing else.
    The clock is installed before the page is loaded, because the runtime arms its first
    timer on the first paint.
    Only `setTimeout` and the clocks beside it are faked; the document timeline is the
    browser's own, so motion still runs in real time and is still scrubbable.
    `requestAnimationFrame` is faked with the timers and stops firing, so `Deck.flight`,
    which waits for a frame, cannot be used on a deck opened here. See *Findings*.
    """

    def opener(path: Path) -> Deck:
        page.clock.install(time=0)
        # A minute ahead of where the clock was installed, because an installed clock is
        # still running and cannot be paused in its own past: the two calls take real
        # milliseconds, and a loaded machine takes more of them.
        # Nothing is loaded yet, so the jump has no timer to fire.
        page.clock.pause_at(60_000)
        open_local(page, path)
        return Deck(page)

    return opener
