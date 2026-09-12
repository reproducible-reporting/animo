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

# The chromium that `setup.sh` downloads.
# It is exported here as well as in `.envrc`,
# so that the suite is green for a contributor who does not use `direnv`.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".venv" / "playwright"))


def pytest_addoption(parser):
    """Add the regeneration path of the stored reference images."""
    parser.addoption(
        "--update-references",
        action="store_true",
        default=False,
        help="rewrite every stored reference image from the current rendering",
    )


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
    """
    path = ROOT / "tmp" / "pytest" / request.node.name
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
def browser(playwright_instance):
    """Tier 3: the bundled chromium, launched once for the whole run.

    A missing browser fails rather than skips.
    `./setup.sh` downloads it, and a suite that is green because its browser tier
    never ran is the failure this hides.
    """
    try:
        instance = playwright_instance.chromium.launch()
    except PlaywrightError as exc:
        raise RuntimeError(
            "chromium is not installed for playwright. "
            "Run `./setup.sh`, or `playwright install chromium` with "
            "PLAYWRIGHT_BROWSERS_PATH pointing at .venv/playwright."
        ) from exc
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
