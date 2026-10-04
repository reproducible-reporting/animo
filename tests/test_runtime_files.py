# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: Apache-2.0
"""The files of the browser runtime, which `deck.typ` joins into the one script of a page.

These tests read the sources and need no browser.
What the joined script does is asserted in `test_runtime_html.py`,
and a file that was left out of the join or joined in an order that cannot work
shows there as a deck that does not run, which is a poor way to be told about a typo.
"""

import re

from harness import ROOT

JS = ROOT / "src" / "js"


def joined() -> list[str]:
    """The names `deck.typ` joins, in the order it joins them."""
    source = (ROOT / "src" / "deck.typ").read_text()
    block = re.search(r"#let runtime-files = \((.*?)\)", source, re.DOTALL)
    assert block is not None, "deck.typ no longer names the files of the runtime"
    return re.findall(r'"([^"]+)"', block.group(1))


def test_every_file_of_the_runtime_is_joined_and_every_joined_file_exists():
    """A file that is not named is never sent to the browser, and a name without a file fails."""
    assert sorted(joined()) == sorted(path.stem for path in JS.glob("*.js"))


def test_no_file_is_joined_twice():
    """Two copies of a file declare every name in it twice, which is a syntax error."""
    names = joined()
    assert len(names) == len(set(names))


def test_the_file_that_calls_into_the_others_at_load_comes_last():
    """A file may use at load time only what an earlier file defines, and `boot.js` uses all."""
    assert joined()[-1] == "boot"


def test_the_controller_is_the_only_file_with_a_module_level_variable():
    """State kept between two inputs has one owner, so that one file says what it is.

    A `const` is a binding that never changes, and a `let` is one that does, which is what
    the controller keeps.
    """
    offenders = [
        path.name
        for path in sorted(JS.glob("*.js"))
        if path.name != "controller.js" and re.search(r"^(let|var) ", path.read_text(), re.M)
    ]
    assert offenders == []
